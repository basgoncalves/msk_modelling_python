'''
code to be used to convert the ElaboratedData to the Simulation folder (older vs newer bops format)
'''

import msk_modelling_python as msk


current_base_path = msk.os.path.dirname(__file__)
elab_path = msk.os.path.join(current_base_path, 'MocapData', 'ElaboratedData')
sim_path = msk.os.path.join(current_base_path, 'Simulations')

if msk.os.path.isdir(elab_path) == False:
    print('Error: Could not find ElaboratedData folder')
    raise

subjects = msk.os.listdir(elab_path)
start_subject = 0
for subject in subjects[start_subject:]:
    
    for session in msk.os.listdir(msk.os.path.join(elab_path, subject)):
        ik_folder = msk.os.path.join(elab_path, subject, session, 'inverseKinematics')
        trial_names = msk.os.listdir(ik_folder)
        
        for trial in trial_names:
    
            class ElabTrialFiles():
                '''
                Class to store the paths of the files in the ElaboratedData folder for a given trial (bops format v0.1.1)
                '''
                def __init__(self, elab_path, subject, session, trial):         
                    # names files in ElaboratedData
                    self.trial_folder = elab_path
                    
                    # IK
                    self.ik_folder = msk.os.path.join(self.trial_folder, subject, session, 'inverseKinematics')
                    self.grf_mot = msk.os.path.join(self.ik_folder, trial, trial + '.mot')
                    self.markers_trc = msk.os.path.join(self.ik_folder, trial, trial + '.trc')
                    self.ik_mot = msk.os.path.join(self.ik_folder, trial, 'IK.mot')
                    self.setup_ik = msk.os.path.join(self.ik_folder, trial, 'setup_IK.xml')
                    
                    # ID
                    self.id_folder = msk.os.path.join(self.trial_folder, subject, session, 'inverseDynamics')
                    self.id_sto = msk.os.path.join(self.id_folder, trial, 'inverse_dynamics.sto')
                    self.id_rra_sto = msk.os.path.join(self.id_folder, trial, 'inverse_dynamics_RRA.sto')
                    self.setup_id = msk.os.path.join(self.id_folder, trial, 'setup_ID.xml')
                    self.setup_id_rra = msk.os.path.join(self.id_folder, trial, 'setup_ID_rra.xml')
                    self.external_loads_xml = msk.os.path.join(self.id_folder, trial, 'grf.xml')
                    
                    # RRA
                    self.rra_folder = msk.os.path.join(self.trial_folder , subject, session, 'residualReductionAnalysis')
                    self.setup_rra = msk.os.path.join(self.rra_folder, trial, 'setup_RRA.xml')
                    self.tasks_rra = msk.os.path.join(self.rra_folder, trial, 'tasks_RRA.xml')
                    self.actuators_rra = msk.os.path.join(self.rra_folder, trial, 'actuators_RRA.xml')
                    
                    # MA
                    self.ma_folder = msk.os.path.join(self.trial_folder, subject, session, 'muscleAnalysis')
                    self.setup_ma = msk.os.path.join(self.ma_folder, trial, 'setup', 'setup_MA.xml')
                    
                    #JointReactionAnalysis
                    self.jra_folder = msk.os.path.join(self.trial_folder, subject, session, 'jointReactionAnalysis')
                    self.setup_jra = msk.os.path.join(self.jra_folder, trial, 'setup_JRA.xml')
                    self.jra_loads = msk.os.path.join(self.jra_folder, trial, 'JCF_JointReaction_ReactionLoads.sto')
                    self.muscle_forces = msk.os.path.join(self.jra_folder, trial, 'forcefile.sto')
                    
                    #ceinms
                    self.ceinms_folder = msk.os.path.join(self.trial_folder, subject, session, 'ceinms')
                    self.ceinms_trial_xml = msk.os.path.join(self.ceinms_folder, 'trials', trial + '.xml')
                    self.ceinms_excitation_xml = msk.os.path.join(self.ceinms_folder, 'excitationGenerators', 'excitationGenerator.xml')
                    self.ceinms_exe_cfg = msk.os.path.join(self.ceinms_folder, 'execution', 'Cfg' , 'executionCfg.xml')
                    self.ceinms_exe_setup_xml = msk.os.path.join(self.ceinms_folder, 'execution', 'Setup', trial + '.xml')
                    self.ceinms_simulations_folder = msk.os.path.join(self.ceinms_folder, 'execution', 'simulations', trial)
                    self.ceinms_model_uncalibrated = msk.os.path.join(self.ceinms_folder, 'calibration', 'uncalibrated.xml')
                    self.ceinms_model_calibrated = msk.os.path.join(self.ceinms_folder, 'calibration', 'calibratedSubject.xml')
                    self.ceinms_contact_model = msk.os.path.join(self.ceinms_folder, 'calibration', 'contactModel.xml')
                    self.ceinms_calibration_setup = msk.os.path.join(self.ceinms_folder, 'calibration', 'calibrationSetup.xml')
                    self.ceinms_calibration_cfg = msk.os.path.join(self.ceinms_folder, 'calibration', 'calibrationCfg.xml')
                                
            class SimTrialFiles():
                ''''
                Class to store the paths of the files in the simulation folder for a given trial (new bops format v0.1.7)
                '''
                def __init__(self, sim_path, subject, session, trial):
                    
                    self.trial_folder = msk.os.path.join(sim_path, subject, session, trial)

                    # export from c3d
                    self.grf_mot = msk.os.path.join(self.trial_folder, 'grf.mot')
                    self.markers_trc = msk.os.path.join(self.trial_folder, 'experimental_markers.trc')
                    
                    # setup files
                    self.external_loads_xml = msk.os.path.join(self.trial_folder, 'grf.xml')
                    self.setup_ik = msk.os.path.join(self.trial_folder, 'setup_IK.xml')
                    self.setup_id = msk.os.path.join(self.trial_folder, 'setup_ID.xml')
                    self.setup_id_rra = msk.os.path.join(self.trial_folder, 'setup_ID_rra.xml')
                    self.setup_rra = msk.os.path.join(self.trial_folder, 'setup_RRA.xml')
                    self.setup_ma = msk.os.path.join(self.trial_folder, 'setup_MA.xml')
                    self.setup_jra = msk.os.path.join(self.trial_folder, 'setup_JRA.xml')
                    self.tasks_rra = msk.os.path.join(self.trial_folder, 'tasks_RRA.xml')
                    self.actuators_rra = msk.os.path.join(self.trial_folder, 'actuators_RRA.xml')
                    
                    # results
                    self.ik_mot = msk.os.path.join(self.trial_folder, 'joint_angles.mot')
                    self.id_sto = msk.os.path.join(self.trial_folder, 'joint_moments.sto')
                    self.id_rra_sto = msk.os.path.join(self.trial_folder, 'joint_moments_post_RRA.sto')                    
                    self.jra_loads = msk.os.path.join(self.trial_folder, 'joint_reaction_loads.sto')
                    self.muscle_forces = msk.os.path.join(self.trial_folder, 'muscle_forces.sto')
                    
                    #ceinms
                    self.ceinms_folder = msk.os.path.join(self.trial_folder, 'ceinms')
                    self.ceinms_trial_xml = msk.os.path.join(self.ceinms_folder, 'trials.xml')
                    self.ceinms_excitation_xml = msk.os.path.join(self.ceinms_folder, 'excitationGenerator.xml')
                    self.ceinms_exe_cfg = msk.os.path.join(self.ceinms_folder, 'execution_cfg.xml')
                    self.ceinms_exe_setup_xml = msk.os.path.join(self.ceinms_folder, 'exe_setup.xml')
                    self.ceinms_simulations_folder = msk.os.path.join(self.ceinms_folder, 'execution', 'simulations', trial)
                    self.ceinms_model_uncalibrated = msk.os.path.join(self.ceinms_folder, 'uncalibratedSubject.xml')
                    self.ceinms_model_calibrated = msk.os.path.join(self.ceinms_folder, 'calibratedSubject.xml')
                    self.ceinms_contact_model = msk.os.path.join(self.ceinms_folder, 'contactModel.xml')
                    self.ceinms_calibration_setup = msk.os.path.join(self.ceinms_folder, 'calibrationSetup.xml')
                    self.ceinms_calibration_cfg = msk.os.path.join(self.ceinms_folder, 'calibrationCfg.xml')
                                        
                    
                    
                def combine_setup_files(self):
                    # combine setup files
                    setup_files = [self.setup_ik, self.setup_id, self.setup_id_rra, self.setup_rra, self.setup_ma, self.setup_jra]
                    self.setup_osim = self.setup_ik.replace('setup_IK.xml', 'setup_osim.xml')
                    with open(self.setup_osim, 'w') as outfile:
                        for fname in setup_files:
                            with open(fname) as infile:
                                for line in infile:
                                    outfile.write(line)
                                    
                    return setup_files

            # create objects for ElabTrialFiles and SimSessionFiles
            try:    
                elab_files = ElabTrialFiles(elab_path, subject, session, trial)
                sim_files = SimTrialFiles(sim_path, subject, session, trial)
            except:
                print('Error: Could not create ElabTrialFiles and SimSessionFiles objects')
                raise
                
            # copy files from ElaboratedData to simulations
            try:
                def copy_file_or_folder(origin, destination):
                    try:
                        #if it is a file
                        if msk.os.path.isfile(origin):
                            msk.src.shutil.copy(origin, destination)
                        #if it is a folder
                        elif msk.os.path.isdir(origin):
                            msk.src.shutil.copytree(origin, destination)
                            
                    except:
                        print('Error: Could not copy ' + origin + ' to ' + destination) 
                        raise
                
                # make trial folder
                try: msk.os.makedirs(sim_files.trial_folder)
                except: pass
                
                # setup files
                copy_file_or_folder(elab_files.setup_ik, sim_files.setup_ik)
                copy_file_or_folder(elab_files.setup_id, sim_files.setup_id)
                copy_file_or_folder(elab_files.setup_id_rra, sim_files.setup_id_rra)
                copy_file_or_folder(elab_files.setup_rra, sim_files.setup_rra)
                copy_file_or_folder(elab_files.setup_ma, sim_files.setup_ma)
                copy_file_or_folder(elab_files.setup_jra, sim_files.setup_jra)
                
                #results
                copy_file_or_folder(elab_files.ik_mot, sim_files.ik_mot)
                copy_file_or_folder(elab_files.id_sto, sim_files.id_sto)
                copy_file_or_folder(elab_files.id_rra_sto, sim_files.id_rra_sto)
                copy_file_or_folder(elab_files.jra_loads, sim_files.jra_loads)
                copy_file_or_folder(elab_files.muscle_forces, sim_files.muscle_forces)
                
                #ceinms
                try: msk.os.makedirs(sim_files.ceinms_simulations_folder)
                except: pass
                copy_file_or_folder(elab_files.ceinms_trial_xml, sim_files.ceinms_trial_xml)
                copy_file_or_folder(elab_files.ceinms_excitation_xml, sim_files.ceinms_excitation_xml)
                copy_file_or_folder(elab_files.ceinms_exe_cfg, sim_files.ceinms_exe_cfg)
                copy_file_or_folder(elab_files.ceinms_exe_setup_xml, sim_files.ceinms_exe_setup_xml)
                copy_file_or_folder(elab_files.ceinms_model_uncalibrated, sim_files.ceinms_model_uncalibrated)
                copy_file_or_folder(elab_files.ceinms_model_calibrated, sim_files.ceinms_model_calibrated)
                copy_file_or_folder(elab_files.ceinms_contact_model, sim_files.ceinms_contact_model)
                copy_file_or_folder(elab_files.ceinms_calibration_setup, sim_files.ceinms_calibration_setup)
                copy_file_or_folder(elab_files.ceinms_calibration_cfg, sim_files.ceinms_calibration_cfg)
                
            except Exception as e:
                print('Error: Could not copy setup files on line: ', e)
                raise
                
        print('Finished copying files to trial ' + trial)
    print('Finished copying files to session ' + session)
print('Finished copying files to subject ' + subject)  