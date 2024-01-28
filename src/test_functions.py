# %%
from bops import *
import ceinms_setup as cs
import bops as bp
from plotting import plot_ceinms as pltc
import replace_markerset as rm

def example_run_single_file(subject_name = 'Athlete_03', trial_name = 'sq_90'):
    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)

    cs.print_to_log_file('Running pipeline for ',subject_name + ' ' + trial_name, mode='start') # log file
    
    cs.run_jra(paths, rerun = True)
    cs.print_to_log_file('done! ', ' ', ' ') # log file

def plot_single_trial(subject_name = 'Athlete_03', trial_name = 'sq_90', analysis = 'static_optimization'):
    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)
    model_path = paths.model_scaled

    if analysis == 'static_optimization_forces':
        sto_path = paths.so_output_forces
        muscles_r = get_muscles_by_group_osim(model_path,['right_leg'])
        columns_to_plot = muscles_r['all_selected']
        title = os.path.basename(sto_path) + ' right leg'
        save_path = os.path.join(paths.trial,'results' , title + '.png')

    if analysis == 'static_optimization_activations':
        sto_path = paths.so_output_activations
        muscles_r = get_muscles_by_group_osim(model_path,['right_leg'])
        columns_to_plot = muscles_r['all_selected']
        title = os.path.basename(sto_path) + ' right leg'
        save_path = os.path.join(paths.trial,'results' , title + '.png')

    if analysis == 'ik':
        sto_path = paths.ik_output
        columns_to_plot = ['hip_flexion_r','knee_angle_r','ankle_angle_r','hip_flexion_l','knee_angle_l','ankle_angle_l']
        title = os.path.basename(sto_path) + ' right leg'
        save_path = os.path.join(paths.trial,'results' , title + '.png')

    if analysis == 'jra':
        sto_path = paths.jra_output
        print(sto_path)
        columns_to_plot = ['hip_r_on_femur_r_in_femur_r_fx','hip_r_on_femur_r_in_femur_r_fy','hip_r_on_femur_r_in_femur_r_fz',
                           'walker_knee_r_on_tibia_r_in_tibia_r_fx','walker_knee_r_on_tibia_r_in_tibia_r_fy','walker_knee_r_on_tibia_r_in_tibia_r_fz',
                           'ankle_r_on_talus_r_in_talus_r_fx','ankle_r_on_talus_r_in_talus_r_fy','ankle_r_on_talus_r_in_talus_r_fz']

        title = os.path.basename(sto_path) + ' right leg'
        save_path = os.path.join(paths.trial,'results' , title + '.png')
        if subject_name.endswith('_torsion'):
            model_path = paths.model_scaled.replace('_torsion','')
        else:
            model_path = paths.model_scaled

        weight = float(get_tag_xml(model_path.replace('.osim', '_scale_setup.xml'), 'mass'))  * 9.81
        sto_path = bp.normalise_df(bp.import_sto_data(sto_path),weight)

    fig  = plot_line_df(sto_path, sep_subplots = False, columns_to_plot=columns_to_plot,
                    xlabel='Frames',ylabel='Force(BW)', legend='',save_path=save_path, title=title)

    plt.show()

def update_max_isometric_force(subject_name = 'Athlete_03', trial_name = 'sq_90'):
    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)
    model_path = paths.model_scaled

    cs.print_to_log_file('Update model max isom force (x10)',subject_name + ' ' + trial_name, mode='start') # log file
    bp.update_max_isometric_force_xml(model_path,10)
    cs.print_to_log_file('                       done! ', ' ', ' ') # log file

def plot_intercative(df,save_path_html = None):
    import plotly.express as px
    import pandas as pd

    # Create an interactive line plot
    fig = px.line(df, x='time', y=df.columns.difference(['time']).tolist(), labels={'value': 'Y'}, title='Interactive Line Plot')

    # Show the plot
    if save_path_html is not None:
        fig.write_html(save_path_html)
        print('Saved to: ', save_path_html)

# Replace model markerset
# def replace_model_markerset(model_file_path = None, target_model = None, markerset_path = None):

    if model_file_path is None:
        model_file_path = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_22_torsion_scaled_GUI.osim"
        target_model = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_22_scaled.osim"

    if markerset_path is None:
        markerset_path = model_file_path.replace('.osim','_markerset.xml') 
    
    rm.export_markerset_osim(model_file_path, markerset_path, [])
    rm.add_markerset_to_osim(target_model, target_model.replace('.osim','_new.osim'), markerset_path)

# example_run_single_file(subject_name, trial_name)
# plot_single_trial(subject_name, trial_name, analysis = 'jra')

# model_file_path = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_06_torsion_scaled.osim"
# ik_file_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_06_torsion\sq_90\IK.mot"
# checkMuscleMomentArms(model_file_path, ik_file_path, leg = 'l', threshold = 0.005)

# plot_single_trial(subject_name = 'Athlete_06', trial_name = 'sq_70', analysis = 'static_optimization_activations')
# example_run_single_file()
# update_max_isometric_force(subject_name = 'Athlete_22_torsion', trial_name = 'sq_90')

# df = bp.import_sto_data(r'C:\Git\isbs2024\Data\Simulations\Athlete_06\sq_90\EMG_filtered.sto')
# plot_intercative(df, save_path_html = r'C:\Git\isbs2024\Data\Simulations\Athlete_06\sq_90\results\emg_filtered.html')

# replace_model_markerset()

# model = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_22_torsion_scaled.osim"
# ik_file = r"C:\Git\isbs2024\Data\Simulations\Athlete_22_torsion\sq_70\IK.mot"
# bp.checkMuscleMomentArms(model_file_path=model, ik_file_path=ik_file, leg='l', threshold=0.005)





print('Done')

# END