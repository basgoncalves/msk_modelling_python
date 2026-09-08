"""The Modenese (2015) muscle-parameter optimiser.

Its own cluster: given a reference model and a target (scaled) model, it
rescales optimal fibre length / tendon slack length so the target reproduces
the reference's normalised operating range.

Split out of the old ``bioscout/utils/openSim.py`` (docs/RESTRUCTURE_PLAN.md,
stage 6) -- the code is unchanged, only its address.
"""
import os
import logging
import warnings
from time import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy import linalg, optimize
import opensim as osim
from bioscout import utils
from bioscout.model.opensim_base import _quiet_model
from bioscout.model.edit.osim_ops import (MAX_EVAL_POINTS, MUSCLE_OPT_MA_TOL,
                                          MUSCLE_OPT_SKIP_COORDS,
                                          sampleMuscleQuantities)


def mean_squared_error(y_true, y_pred, squared=True):
    """Local RMSE/MSE helper (avoids sklearn version differences over the
    removed `squared=` kwarg). Returns RMSE when squared=False."""
    err = float(np.mean((np.asarray(y_true, float) - np.asarray(y_pred, float)) ** 2))
    return err if squared else np.sqrt(err)

def muscle_optimimizer_Modenese2015(osim_model_path=None, save_path=None,
                                    ref_model_path=None, N_eval=10,
                                    log_folder=None):
    """
    Optimize muscle parameters in an OpenSim model using the Modenese 2015 method.

    Args:
        osim_model_path (str): Path to the TARGET (e.g. scaled) .osim model whose
            muscle optimal-fiber-length / tendon-slack-length will be optimised.
        save_path (str, optional): Where to write the optimised model. Defaults to
            '<target>_opt_N<N_eval>.osim'.
        ref_model_path (str, optional): Reference (template/generic) model whose
            muscle operating range is preserved. Defaults to the target model.
        N_eval (int): Sampling points per spanned coordinate (default 10 -> _N10).
        log_folder (str, optional): Folder for the per-muscle optimisation log.
    """
    if osim_model_path is None:
        osim_model_path = input("Path to target model (.osim): ").strip('"')
    if ref_model_path is None:
        ref_model_path = osim_model_path
    if log_folder is None:
        log_folder = os.path.dirname(osim_model_path)

    # The Modenese sampling equilibrates muscles at extreme joint poses, which
    # makes OpenSim emit a flood of "at its minimum fiber length" warnings --
    # this both spams the console and slows the run dramatically (log I/O).
    # Silence the OpenSim logger during optimisation, then restore it.
    try:
        _prev_log_level = osim.Logger.getLevelString()
    except Exception:
        _prev_log_level = "Info"
    try:
        osim.Logger.setLevelString("off")
    except Exception:
        pass
    try:
        osim_model_opt, sims_info = optimMuscleParams(ref_model_path, osim_model_path,
                                                      N_eval, log_folder)
    finally:
        try:
            osim.Logger.setLevelString(_prev_log_level)
        except Exception:
            pass

    if save_path is None:
        save_path = osim_model_path.replace('.osim', f'_opt_N{N_eval}.osim')
    osim_model_opt.printToXML(save_path)
    print(f"Optimized model saved to: {save_path}")
    return save_path

def _apply_muscle_opt_settings():
    """Pull the optimiser's DOF knobs from the project's BatchSettings, once.

    Kept as module globals rather than threaded through four signatures
    because sampleMuscleQuantities is called from two places and is itself
    called per muscle per quantity; a project sets the policy once and every
    call site sees it.
    """
    global MUSCLE_OPT_SKIP_COORDS, MUSCLE_OPT_MA_TOL
    try:
        from bioscout.utils import settings as _st
        _bs = getattr(_st, "BatchSettings", None)
    except Exception:
        _bs = None
    if _bs is None:
        return
    _sk = getattr(_bs, "muscle_opt_skip_coords", None)
    if _sk:
        MUSCLE_OPT_SKIP_COORDS = tuple(_sk)
        print(f"[opt] excluding coordinates from the muscle-optimiser grid: "
              f"{', '.join(MUSCLE_OPT_SKIP_COORDS)}")
    _tol = getattr(_bs, "muscle_opt_ma_tol", None)
    if _tol:
        MUSCLE_OPT_MA_TOL = float(_tol)
        print(f"[opt] moment-arm threshold for 'spanned': {MUSCLE_OPT_MA_TOL*1000:.2f} mm")

def optimMuscleParams(osimModel_ref_filepath, osimModel_targ_filepath, N_eval, log_folder):

    # Read the project's DOF policy before any muscle is sampled.
    _apply_muscle_opt_settings()

    # results file identifier
    res_file_id_exp = '_N' + str(N_eval)
    
    # import models
    osimModel_ref = _quiet_model(osimModel_ref_filepath)
    osimModel_targ = _quiet_model(osimModel_targ_filepath)
    
    # models details
    name = Path(osimModel_targ_filepath).stem
    ext = Path(osimModel_targ_filepath).suffix
    
    # assigning new name to the model
    osimModel_opt_name = name + '_opt' + res_file_id_exp + ext
    osimModel_targ.setName(osimModel_opt_name)
    
    # initializing log file
    log_folder = Path(log_folder)
    log_folder.mkdir(parents=True, exist_ok=True)
    log_file_path = log_folder / (name + '_opt' + res_file_id_exp + '.log')
    
    # Check if log file exists and find last processed muscle
    # ROTATE the log before reading it. `processed_muscles` below is a resume
    # feature: any muscle named in this file is SKIPPED. The file is opened in
    # append mode and never cleared, so a log left by an earlier run makes a
    # later run skip almost everything and write a model whose parameters are
    # mostly the UNOPTIMISED scaled ones -- under an `_opt_N10` filename, with
    # no error and in a fraction of the expected time.
    #
    # Observed 2026-08-06: a production run resumed from a 168-entry log,
    # optimised 8 muscles of 80, and produced a scaled_opt_N10.osim that
    # differed from scaled.osim on 8 muscles. CEINMS then ran against it.
    #
    # Resume is worth far less than it was: the sampler is ~10x faster since
    # the muscle downcast fix, so a full pass is minutes. Rotating always means
    # an interrupted run restarts cleanly instead of silently half-finishing.
    if log_file_path.exists() and log_file_path.stat().st_size > 0:
        import time as _t
        _prev = log_file_path.with_suffix('.log.prev_%s' % _t.strftime('%y%m%d_%H%M%S'))
        try:
            log_file_path.rename(_prev)
            print('[muscle-opt] rotated previous log -> %s' % _prev.name)
        except OSError:
            pass

    processed_muscles = set()
    if log_file_path.exists():
        with open(log_file_path, 'r') as f:
            for line in f:
                if 'Calculated optimized muscle parameters for' in line:
                    muscle_name = line.split('Calculated optimized muscle parameters for')[1].split('in')[0].strip()
                    processed_muscles.add(muscle_name)
        print(f'Found {len(processed_muscles)} already processed muscles in log file')
    
    logging.basicConfig(filename=str(log_file_path), filemode='a', format='%(levelname)s:%(message)s', level=logging.INFO)
        
    # get muscles
    muscles = osimModel_ref.getMuscles()
    muscles_scaled = osimModel_targ.getMuscles()
    
    # initialize with recognizable values
    LmOptLts_opt = -1000*np.ones((muscles.getSize(),2))
    SimInfo = {}
    
    for n_mus in range(0, muscles.getSize()):
        
        # current muscle name (here so that it is possible to choose a single muscle when developing).
        curr_mus_name = muscles.get(n_mus).getName()
        
        # Skip if already processed
        if curr_mus_name in processed_muscles:
            print(f'Skipping muscle {n_mus+1}: {curr_mus_name} (already processed)')
            continue
        
        tic = time()
        print('processing mus ' + str(n_mus+1) + ': ' + curr_mus_name)
        
        # import muscles
        curr_mus = muscles.get(curr_mus_name)
        curr_mus_scaled = muscles_scaled.get(curr_mus_name)
        
        # extracting the muscle parameters from reference model
        LmOptLts = [curr_mus.getOptimalFiberLength(), curr_mus.getTendonSlackLength()]
        PenAngleOpt = curr_mus.getPennationAngleAtOptimalFiberLength()
        Mus_ref = sampleMuscleQuantities(osimModel_ref,curr_mus,'all',N_eval)
        
        # calculating minimum fiber length before having pennation 90 deg
        # acos(0.1) = 1.47 red = 84 degrees, chosen as in OpenSim
        limitPenAngle = np.arccos(0.1)
        # this is the minimum length the fiber can be for geometrical reasons.
        LfibNorm_min = np.sin(PenAngleOpt) / np.sin(limitPenAngle)
        # LfibNorm as calculated above can be shorter than the minimum length
        # at which the fiber can generate force (taken to be 0.5 Zajac 1989)
        if LfibNorm_min < 0.5:
            LfibNorm_min = 0.5
        
        # muscle-tendon paramenters value
        MTL_ref = [musc_param_iter[0] for musc_param_iter in Mus_ref]
        LfibNorm_ref = [musc_param_iter[1] for musc_param_iter in Mus_ref]
        LtenNorm_ref = [musc_param_iter[2]/LmOptLts[1] for musc_param_iter in Mus_ref]
        penAngle_ref = [musc_param_iter[4] for musc_param_iter in Mus_ref]
        # LfibNomrOnTen_ref = LfibNorm_ref.*cos(penAngle_ref)
        LfibNomrOnTen_ref = [(musc_param_iter[1]*np.cos(musc_param_iter[4])) for musc_param_iter in Mus_ref]         
        
        # checking the muscle configuration that do not respect the condition.
        okList = [pos for pos, value in enumerate(LfibNorm_ref) if value > LfibNorm_min]

        # Guard: if too few valid evaluation points remain (< 2 needed to fit the
        # two parameters), the linear system is unsolvable. Keep this muscle's
        # existing (scaled) optimal-fiber / tendon-slack lengths unchanged and
        # move on instead of crashing on empty arrays.
        if len(okList) < 2:
            LmOptLts_opt[n_mus] = [curr_mus_scaled.getOptimalFiberLength(),
                                   curr_mus_scaled.getTendonSlackLength()]
            logging.warning('Only %d valid sample(s) for %s; kept scaled '
                            'parameters (not optimised).'
                            % (len(okList), curr_mus_name))
            continue

        # keeping only acceptable values
        MTL_ref = np.array([MTL_ref[index] for index in okList])
        LfibNorm_ref = np.array([LfibNorm_ref[index] for index in okList])
        LtenNorm_ref = np.array([LtenNorm_ref[index] for index in okList])
        penAngle_ref = np.array([penAngle_ref[index] for index in okList])
        LfibNomrOnTen_ref = np.array([LfibNomrOnTen_ref[index] for index in okList])
        
        # in the target only MTL is needed for all muscles
        MTL_targ = sampleMuscleQuantities(osimModel_targ,curr_mus_scaled,'MTL',N_eval)
        evalTotPoints = len(MTL_targ)
        MTL_targ = np.array([MTL_targ[index] for index in okList])
        evalOkPoints  = len(MTL_targ)
        
        # The problem to be solved is: 
        # [LmNorm*cos(penAngle) LtNorm]*[Lmopt Lts]' = MTL;
        # written as Ax = b or their equivalent (A^T A) x = (A^T b)  
        A = np.array([LfibNomrOnTen_ref , LtenNorm_ref]).T
        b = MTL_targ
        
        # ===== LINSOL =======
        # solving the problem to calculate the muscle param
        try:
            x = linalg.solve(np.dot(A.T , A) , np.dot(A.T , b))
        except (np.linalg.LinAlgError, linalg.LinAlgError, ValueError):
            # normal-equations matrix is (near-)singular for this muscle
            # (e.g. tendon length ~constant over the sampled range). Fall back
            # to a rank-revealing least-squares solve, then to NNLS.
            x, *_ = np.linalg.lstsq(A, b, rcond=None)
            if np.min(x) <= 0:
                x = optimize.nnls(np.dot(A.T , A), np.dot(A.T , b))[0]
            logging.warning('Singular system for %s; used least-squares fallback.'
                            % curr_mus_name)
        LmOptLts_opt[n_mus] = x
        
        # checking the results
        if np.min(x) <= 0:
            # informing the user
            line0 = ' '
            line1 = 'Negative value estimated for muscle parameter of muscle ' + curr_mus_name + '\n'
            line2 = '                         Lm Opt        Lts' + '\n'
            line3 = 'Template model       : ' + str(LmOptLts) + '\n'
            line4 ='Optimized param      : ' + str(LmOptLts_opt[n_mus]) + '\n'
            
            # ===== IMPLEMENTING CORRECTIONS IF ESTIMATION IS NOT CORRECT =======
            x = optimize.nnls(np.dot(A.T , A) , np.dot(A.T , b))
            x = x[0]
            LmOptLts_opt[n_mus] = x
            line5 = 'Opt params (optimize.nnls): ' + str(LmOptLts_opt[n_mus])
            
            logging.info(line0 + line1 + line2 + line3 + line4 + line5 + '\n')
            # In our tests, if something goes wrong is generally tendon slack 
            # length becoming negative or zero because tendon length doesn't change
            # throughout the range of motion, so lowering the rank of A.
            if np.min(x) <= 0:
                # analyzes of Lten behaviour
                Lten_ref = [musc_param_iter[2] for musc_param_iter in Mus_ref]
                Lten_ref = np.array([Lten_ref[index] for index in okList])
                if (np.max(Lten_ref) - np.min(Lten_ref)) < 0.0001:
                    logging.warning(' Tendon length not changing throughout range of motion')
                
                # calculating proportion of tendon and fiber
                Lten_fraction = Lten_ref/MTL_ref
                Lten_targ = Lten_fraction*MTL_targ
                
                # first round: optimizing Lopt maintaing the proportion of
                # tendon as in the reference model
                A1 = np.array([LfibNomrOnTen_ref , LtenNorm_ref*0]).T
                b1 = MTL_targ - Lten_targ
                x1 = optimize.nnls(np.dot(A1.T , A1) , np.dot(A1.T , b1))
                x[0] = x1[0][0]
                
                # second round: using the optimized Lopt to recalculate Lts
                A2 = np.array([LfibNomrOnTen_ref*0 , LtenNorm_ref]).T
                b2 = MTL_targ - np.dot(A1,x1[0])
                x2 = optimize.nnls(np.dot(A2.T , A2) , np.dot(A2.T , b2))
                x[1] = x2[0][1]
                
                LmOptLts_opt[n_mus] = x
            
        
        # Here tests about/against optimizers were implemented
        
        # calculating the error (mean squared errors)
        fval = mean_squared_error(b, np.dot(A,x), squared=False)
        
        # update muscles from scaled model
        curr_mus_scaled.setOptimalFiberLength(LmOptLts_opt[n_mus][0])
        curr_mus_scaled.setTendonSlackLength(LmOptLts_opt[n_mus][1])
        
        # PRINT LOGS
        toc = time() - tic
        line0 = ' '
        line1 = 'Calculated optimized muscle parameters for ' + curr_mus.getName() + ' in ' +  str(toc) + ' seconds.' + '\n'
        line2 = '                         Lm Opt        Lts' + '\n'
        line3 = 'Template model       : ' + str(LmOptLts) + '\n'
        line4 = 'Optimized param      : ' + str(LmOptLts_opt[n_mus]) + '\n'
        line5 = 'Nr of eval points    : ' + str(evalOkPoints) + '/' + str(evalTotPoints) + ' used' + '\n'
        line6 = 'fval                 : ' + str(fval) + '\n'
        line7 = 'var from template [%]: ' + str(100*(np.abs(LmOptLts - LmOptLts_opt[n_mus])) / LmOptLts) + '%' + '\n'
        
        logging.info(line0 + line1 + line2 + line3 + line4 + line5 + line6 + line7 + '\n')
              
        # SIMULATION INFO AND RESULTS
        
        SimInfo[n_mus] = {}
        SimInfo[n_mus]['colheader'] = curr_mus.getName()
        SimInfo[n_mus]['LmOptLts_ref'] = LmOptLts
        SimInfo[n_mus]['LmOptLts_opt'] = LmOptLts_opt[n_mus]
        SimInfo[n_mus]['varPercLmOptLts'] = 100*(np.abs(LmOptLts - LmOptLts_opt[n_mus])) / LmOptLts
        SimInfo[n_mus]['sampledEvalPoints'] = evalOkPoints
        SimInfo[n_mus]['sampledEvalPoints'] = evalTotPoints
        SimInfo[n_mus]['fval'] = fval
    
    # assigning optimized model as output
    osimModel_opt = osimModel_targ
            
    return osimModel_opt, SimInfo

def plot_optimization_results(intial_model_path, optimised_model_path):

    base_model = _quiet_model(intial_model_path)
    optimized_model = _quiet_model(optimised_model_path)
    
    muscles = base_model.getMuscles()
    n_muscles = muscles.getSize()
    
    params = ['optimal_fiber_length', 'tendon_slack_length', 'pennation_angle_at_optimal']
    fig, axes = plt.subplots(len(params), 1, figsize=(8, 12))
    
    for ax, param in zip(axes, params):
        ax.set_title(param.replace('_', ' ').title())
        ax.set_xlabel('Muscle Index')
        ax.set_ylabel(param.replace('_', ' ').title())
        for i in range(n_muscles):
            muscle = muscles.get(i)
            muscle_name = muscle.getName()
            base_muscle = base_model.getMuscles().get(muscle_name)
            optim_muscle = optimized_model.getMuscles().get(muscle_name)
            if param == 'optimal_fiber_length':
                base_value = base_muscle.getOptimalFiberLength()
                optim_value = optim_muscle.getOptimalFiberLength()
            elif param == 'tendon_slack_length':
                base_value = base_muscle.getTendonSlackLength()
                optim_value = optim_muscle.getTendonSlackLength()
            elif param == 'pennation_angle_at_optimal':
                base_value = base_muscle.getPennationAngleAtOptimalFiberLength()
                optim_value = optim_muscle.getPennationAngleAtOptimalFiberLength()
            
            # bar plot
            ax.bar(i - 0.2, base_value, width=0.4, label='Base' if i == 0 else "", color='b')
            ax.bar(i + 0.2, optim_value, width=0.4, label='Optimized' if i == 0 else "", color='r')

            # setting x-ticks
            ax.set_xticks(range(n_muscles))
            ax.set_xticklabels([muscles.get(i).getName() for i in range(n_muscles)], rotation=90, size=6)

        ax.legend()    
    plt.tight_layout()
    
    save_path = optimised_model_path.replace('.osim', '_muscle_params.png')
    plt.savefig(save_path)
    print(f'Optimization results plot saved to {save_path}')


    def main(osim_model_ref_filepath=None, osim_model_targ_filepath=None):
        # ========= USER SETTINGS =======
        # model files with paths
        if osim_model_ref_filepath is None:
            osim_model_ref_filepath = input("Please provide the path to the reference model: ").strip('"')
        if osim_model_targ_filepath is None:
            osim_model_targ_filepath = input("Please provide the path to the target model: ").strip('"')
        optimized_model_folder = os.path.dirname(osim_model_targ_filepath)
        
        # evaluations
        n_eval = 10
        # ===============================

        # initializing folders and log file
        log_folder = optimized_model_folder
        
        # checking if results folder exists. If not, create it.
        if not os.path.isdir(optimized_model_folder):
            warnings.warn(f'Folder {optimized_model_folder} does not exist. It will be created.')
            os.makedirs(optimized_model_folder)

        # optimizing target model based on reference model for n_eval points per
        # degree of freedom
        osim_model_opt, sims_info = optimMuscleParams(osim_model_ref_filepath,
                                                        osim_model_targ_filepath,
                                                        n_eval,
                                                        log_folder)

        # printing the optimized model
        output_path = osim_model_targ_filepath.replace('.osim', f'_opt_N{n_eval}.osim')
        osim_model_opt.printToXML(output_path)
        print(f'Optimized model saved to: {output_path}')
        
        # plotting optimization results
        plot_optimization_results(osim_model_targ_filepath, output_path)

    
    model = _quiet_model(intial_model_path)
    state = model.initSystem()

    # Call the Modenese 2015 optimization method
    try:
        main(osim_model_ref_filepath=intial_model_path, osim_model_targ_filepath=optimised_model_path)
        print("Muscle optimization completed successfully.")
    except Exception as e:
        print(f"Error during muscle optimization: {e}")
        return

    # Determine save path
    if save_path is None:
        save_path = intial_model_path.replace('.osim', '_optimized.osim')

    # Save the optimized model
    model.printToXML(save_path)
    print(f"Optimized model saved to: {save_path}")

def optimize_moment_arms(ref_model_path=None, target_model_path=None):
    '''Optimize muscle parameters in the target model to match the moment arms of the reference model.
    
    NOT FINNISED!!!
    
    '''

    if ref_model_path is None:
        ref_model_path = input("Enter the path to the reference .osim model file: ").strip('"')
    if target_model_path is None:
        target_model_path = input("Enter the path to the target .osim model file: ").strip('"')

    ref_model = _quiet_model(ref_model_path)
    target_model = _quiet_model(target_model_path)
    optimized_model = _quiet_model(target_model_path)

    def compute_moment_arms(model):
        state = model.initSystem()
        model.realizePosition(state)
        moment_arms = {}
        for i in range(model.getMuscles().getSize()):
            muscle = model.getMuscles().get(i)
            muscle_name = muscle.getName()
            moment_arms[muscle_name] = {}
            for j in range(model.getCoordinateSet().getSize()):
                coord = model.getCoordinateSet().get(j)
                coord_name = coord.getName()
                moment_arms[muscle_name][coord_name] = muscle.computeMomentArm(state, coord)
        return moment_arms
    
    def optimize_moment_arm(muscle_name, coord_name, ref_arm, target_arm):
        # Placeholder for optimization logic
        # In a real implementation, this would adjust muscle parameters in the target model to minimize the difference in moment arms
        optimized_arm = target_arm
        return optimized_arm
    
    ref_moment_arms = compute_moment_arms(ref_model)
    target_moment_arms = compute_moment_arms(target_model)

    for muscle_name in ref_moment_arms.keys():
        if muscle_name in target_moment_arms:
            for coord_name in ref_moment_arms[muscle_name].keys():
                if coord_name in target_moment_arms[muscle_name]:
                    ref_arm = ref_moment_arms[muscle_name][coord_name]
                    target_arm = target_moment_arms[muscle_name][coord_name]
                    if abs(ref_arm - target_arm) > 0.01:  # Threshold for optimization
                        print(f"Optimizing {muscle_name} for {coord_name}: Ref={ref_arm:.4f}, Target={target_arm:.4f}")
                        optimized_arm = optimize_moment_arm(muscle_name, coord_name, ref_arm, target_arm)



    # save the optimized model
    optimized_model_path = target_model_path.replace('.osim', '_optimized.osim')
    optimized_model.printToXML(optimized_model_path)
    print(f"Optimized model saved to: {optimized_model_path}")


    # Compare moment arms and plot results
    model1 = _quiet_model(ref_model_path)
    model2 = _quiet_model(target_model_path)
    model3 = _quiet_model(optimized_model_path)

    optimized_arms = compute_moment_arms(model3)


    n_muscles = len(ref_moment_arms)
    n_cols = 5
    n_rows = (n_muscles + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 6, n_rows * 3))
    axes = axes.flatten() if n_muscles > 1 else [axes]
    for idx, muscle_name in enumerate(ref_moment_arms.keys()):
        ax = axes[idx]
        ref_arms = list(ref_moment_arms[muscle_name].values())
        target_arms = list(target_moment_arms[muscle_name].values())
        optimized_arms_values = list(optimized_arms[muscle_name].values())
        
        coords = list(ref_moment_arms[muscle_name].keys())
        
        ax.plot(coords, ref_arms, 'o-', label='Reference')
        ax.plot(coords, target_arms, 'x-', label='Target')
        ax.plot(coords, optimized_arms_values, 's-', label='Optimized')
        
        ax.set_title(muscle_name)
        ax.set_ylabel('Moment Arm (m)')
        ax.tick_params(axis='x', rotation=45)
    
    utils.mmfn(fig, n_cols=n_cols, n_rows=n_rows)
    plt.tight_layout()

    save_path = target_model_path.replace('.osim', '_moment_arms_comparison.png')
    plt.savefig(save_path)
    print(f"Moment arms comparison plot saved to: {save_path}")

    # make a spider plot for each coordinate with the moment arms of all muscles and save the figure
    n_coords = ref_model.getCoordinateSet().getSize()
    n_cols = 3
    n_rows = (n_coords + n_cols - 1) // n_cols
    fig, ax = plt.subplots(n_rows, n_cols, figsize=(n_cols * 6, n_rows * 6), subplot_kw=dict(projection='polar'))
    ax = ax.flatten() if n_coords > 1 else [ax]
    for i in range(n_coords):
        coord = ref_model.getCoordinateSet().get(i)
        coord_name = coord.getName()
        ax_coord = ax[i]
        ref_arms = [ref_moment_arms[muscle_name][coord_name] for muscle_name in ref_moment_arms.keys()]
        target_arms = [target_moment_arms[muscle_name][coord_name] for muscle_name in target_moment_arms.keys()]
        optimized_arms_values = [optimized_arms[muscle_name][coord_name] for muscle_name in optimized_arms.keys()]
        
        muscles = list(ref_moment_arms.keys())
        angles = np.linspace(0, 2 * np.pi, len(muscles), endpoint=False).tolist()
        angles += angles[:1]
        
        ax_coord.plot(angles, ref_arms + [ref_arms[0]], 'o-', label='Reference')
        ax_coord.plot(angles, target_arms + [target_arms[0]], 'x-', label='Target')
        ax_coord.plot(angles, optimized_arms_values + [optimized_arms_values[0]], 's-', label='Optimized')
        
        ax_coord.set_title(coord_name)
        ax_coord.set_xticks(angles[:-1])
        ax_coord.set_xticklabels(muscles, rotation=90, size=8)

    save_path = target_model_path.replace('.osim', '_moment_arms_comparison_spider.png')
    plt.savefig(save_path)
    print(f"Moment arms comparison spider plot saved to: {save_path}")
