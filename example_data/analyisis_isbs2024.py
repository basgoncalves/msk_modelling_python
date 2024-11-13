# %% use this to test functions before inputing them into bops or other modules
from msk_modelling_python.src.bops import *
import msk_modelling_python.src.ceinms_setup as cs
import msk_modelling_python.src.bops as bp
from msk_modelling_python.src.plot import plot_ceinms as pltc
from msk_modelling_python.src.muscle_modelling import replace_markerset as rm

def example_run_single_file(subject_name = 'Athlete_03', trial_name = 'sq_90'):
    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)

    cs.print_to_log_file('Running pipeline for ',subject_name + ' ' + trial_name, mode='start') # log file
    
    cs.run_so(paths, rerun=True)
    cs.run_jra(paths, rerun = True)
    cs.print_to_log_file('done! ', ' ', ' ') # log file

def plot_single_trial(subject_name = 'Athlete_03', trial_name = 'sq_90', analysis = 'static_optimization'):
    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)
    model_path = paths.model_scaled

    if analysis == 'static_optimization_forces':
        sto_path = paths.so_output_forces
        muscles_r = bp.osimSetup.get_muscles_by_group_osim(model_path,['right_leg'])
        columns_to_plot = muscles_r['all_selected']
        title = os.path.basename(sto_path) + ' right leg'
        save_path = os.path.join(paths.trial,'results' , title + '.png')

    if analysis == 'static_optimization_activations':
        sto_path = paths.so_output_activations
        muscles_r = bp.osimSetup.get_muscles_by_group_osim(model_path,['right_leg'])
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

        weight = float(bp.get_tag_xml(model_path.replace('.osim', '_scale_setup.xml'), 'mass'))  * 9.81
        sto_path = bp.normalise_df(bp.import_sto_data(sto_path),weight)

    fig  = bp.plot_line_df(sto_path, sep_subplots = False, columns_to_plot=columns_to_plot,
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

def copy_marker_locations(osim_path1,osim_path2, marker_names='all'):
    '''Copy the marker locations from one opensim model to another
    osim_path1: str, path to the opensim model to copy from
    osim_path2: str, path to the opensim model to copy to
    marker_names: list, list of marker names to copy'''
    
    # open osim models
    try:
        with open(osim_path1, 'r', encoding='utf-8') as file:
            tree1 = ET.parse(osim_path1)
            root1 = tree1.getroot()
        
        with open(osim_path2, 'r', encoding='utf-8') as file:
            tree2 = ET.parse(osim_path2)
            root2 = tree2.getroot()
    except Exception as e:
        cs.print_terminal_spaced('Error opening input file: {}'.format(e))
        exit()

    # Find the MarkerSet tag
    try:
        marker_set1 = root1.find('.//MarkerSet')
        marker_set2 = root2.find('.//MarkerSet')
    except Exception as e:
        cs.print_terminal_spaced('File does not contain MarkerSet tag: {}'.format(e))
        exit()

    # try copying the marker locations
    try:
        markers1 = marker_set1.findall('.//Marker')
        markers2 = marker_set2.findall('.//Marker')
        if marker_names == 'all':
            marker_names = [marker.get('name') for marker in markers1]
        
        for marker1 in markers1:
            if marker1.get('name') in marker_names:
                marker2 = marker_set2.find('.//Marker[@name="{0}"]'.format(marker1.get('name')))
                if marker2 is None:
                    print(f"Marker '{marker1.get('name')}' not found in '{osim_path2}'")
                    continue

                print(marker1.get('name'))
                
                # find the parent frame depending on the opensim version
                if root1.get('Version') == '40000':
                    marker1_parent = marker1.find('.//socket_parent_frame').text.replace('/bodyset','')
                    marker1_parent = marker1_parent.replace('/','')
                else:
                    marker1_parent = marker1.find('.//body').text

                if root2.get('Version') == '40000':
                    marker2_parent = marker2.find('.//socket_parent_frame').text.replace('/bodyset/','')
                else:
                    marker2_parent = marker2.find('.//body').text

                # if parent frames are the same copy the location
                if marker1_parent == marker2_parent:
                    location_marker1 = marker1.find('.//location').text
                    marker2.find('.//location').text = location_marker1

    except Exception as e:
        cs.print_terminal_spaced('Error copying marker locations: {}'.format(e))
        exit()

    # Write the new tree to the output file
    try:
        tree2.write(osim_path2)
        print(f"MarkerSet copied from '{osim_path2}' to '{osim_path2}'")
    except Exception as e:
        cs.print_terminal_spaced('Error writing output file: {}'.format(e))
        exit()

if __name__ == "__main__":
    
    #%% ISBS2024 data
    # example_run_single_file(subject_name, trial_name)
    # plot_single_trial(subject_name, trial_name, analysis = 'jra')

    # CHECK MUSCLE MOMENT ARMS
    # model_file_path = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_14_torsion_scaled.osim"
    # ik_file_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_14_torsion\sq_70\IK.mot"
    # bp.checkMuscleMomentArms(model_file_path, ik_file_path, leg = 'l', threshold = 0.005)
    # exit()

    ## PLOT SINGLE TRIAL ANALYSIS
    # plot_single_trial(subject_name = 'Athlete_06', trial_name = 'sq_70', analysis = 'static_optimization_activations')
    # example_run_single_file()
        
    # osim_model = bp.select_file()
    # bp.osimSetup.increase_max_isometric_force(osim_model, 10)
    # exit()

    # df = bp.import_sto_data(r'C:\Git\isbs2024\Data\Simulations\Athlete_06\sq_90\EMG_filtered.sto')
    # plot_intercative(df, save_path_html = r'C:\Git\isbs2024\Data\Simulations\Athlete_06\sq_90\results\emg_filtered.html')

    # replace_model_markerset()

    # model = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_22_torsion_scaled.osim"
    # ik_file = r"C:\Git\isbs2024\Data\Simulations\Athlete_22_torsion\sq_70\IK.mot"
    # bp.checkMuscleMomentArms(model_file_path=model, ik_file_path=ik_file, leg='l', threshold=0.005)

    # current process:
    subject_name = 'Athlete_14' # id code
    condition = 'normal' # normal or torsion
    trial_name = 'sq_90' # trial name
    paths = cs.subject_paths(cs.get_main_path(), subject_name, trial_name)
    if condition == 'torsion':
        model_path = paths.model_scaled.replace('_scaled.osim','_torsion_scaled.osim')
        paths = cs.subject_paths(cs.get_main_path(), subject_name + '_torsion', trial_name)
    else:
        model_path = paths.model_scaled
    
    model_path2 = f'C:\Git\isbs2024\Data\Scaled_models\Alex\{subject_name}_scaled.osim'
    marker_names = ['GLAB','RFHD','LFHD','C7','T12','STRN', # upper body
                'RACR','RUAOL','RUA2','RUA3','RCUBL','RCUBM','RLAOL','RLA2','RLA3','RWRU','RWRR', # right arm
                'LACR','LUAOL','LUA2','LUA3','LCUBL','LCUBM','LLAOL','LLA2','LLA3','LWRU','LWRR', # left arm
                'RASI', 'LASI', 'RPSI', 'LPSI', 'SACROL', 'SACR2', 'SACR3' # pelvis
                ]

    orders_markers = ['GLAB','RFHD','LFHD','C7','T12','STRN', # upper body
                'RACR','RUAOL','RUA2','RUA3','RCUBL','RCUBM','RLAOL','RLA2','RLA3','RWRU','RWRR', # right arm
                'LACR','LUAOL','LUA2','LUA3','LCUBL','LCUBM','LLAOL','LLA2','LLA3','LWRU','LWRR', # left arm
                'RASI', 'LASI', 'RPSI', 'LPSI', 'SACROL', 'SACR2', 'SACR3', # pelvis
                'RTHOL', 'RTH2','RTH3','RKNEL', 'RKNEM', 'RSHAOL', 'RSHA2', 'RSHA3','RMALL', 'RMALM','RHEE','RM5','RTOE',# right leg
                'LTHOL', 'LTH2','LTH3','LKNEL', 'LKNEM', 'LSHAOL', 'LSHA2', 'LSHA3','LMALL', 'LMALM','LHEE','LM5','LTOE' # left leg
                ]  

    # bp.osimSetup.copy_marker_locations(model_path,model_path2,marker_names,marker_common_frame='RASI')
    # bp.osimSetup.reorder_markers(model_path, orders_markers)  
    # exit() 
    print('Running pipeline for ',subject_name + ' ' + trial_name)
    print('Model path: ', model_path)
    print('IK output: ', paths.ik_output)
    
    cs.run_inverse_kinematics(model_path, paths.markers,paths.ik_output)
    if condition == 'torsion':
        example_run_single_file(subject_name = subject_name + '_torsion', trial_name = trial_name)
    else:
        example_run_single_file(subject_name = subject_name, trial_name = trial_name)
    
    #%% Marta's data

    # increase max isometric force
    # osim_model = bp.select_file()
    # bp.increase_max_isometric_force(osim_model, 10)

    # run analysis
    # analyzeTool_SO = osim.AnalyzeTool(r"C:\Users\Bas\Desktop\dados_marta\SO\SO_Setup_mvic_2.xml")
    # analyzeTool_SO.run()

    # run cmc
    # cmc = osim.CMCTool(r"C:\Users\Bas\Desktop\dados_marta\CMC_mvic_2\CMC_Setup.xml")
    # cmc.run()   


    # plot activations and forces
    # sto_file = bp.select_file()
    # force_file = r"C:\Users\Bas\Desktop\dados_marta\SO\SO_mvic_2\SO_StaticOptimization_force.sto"
    # activation_file = force_file.replace('force','activation')
    # model_file = r"C:\Users\Bas\Desktop\dados_marta\PC013_scaled_increased_force_5.osim"
    # df = bp.time_normalise_df(bp.import_sto_data(activation_file))
    # muscles_right = bp.get_muscles_by_group_osim(model_file, ['right_leg'])
    # bp.plot_line_df(df, sep_subplots=False, columns_to_plot=muscles_right['all_selected'],
    #                 xlabel='%% Gait cycle', ylabel='Activation (0 to 1)', legend='', save_path=activation_file.replace('.sto','.jpeg'), title='')


    # df = bp.time_normalise_df(bp.import_sto_data(force_file))
    # bp.plot_line_df(df, sep_subplots=False, columns_to_plot=muscles_right['all_selected'],
    #                 xlabel='%% Gait cycle', ylabel='Force (N)', legend='', save_path=force_file.replace('.sto','.jpeg'), title='')





    #%%
    print('Done')

# END