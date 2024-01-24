from bops import *
import ceinms_setup as cs
import plotting as pltc
from sklearn.preprocessing import MinMaxScaler
import bops as bp

class steps:
    def __init__(self, moment_errors = True, compare_forces_ceinms_so = True, activation_errors = True, muscle_work = True, compare_forces_torsion = True,
                 muscle_work_torsion = True, ik_and_id = True, muscle_work_so = True):
        
        self.moment_errors= moment_errors
        self.compare_forces_ceinms_so = compare_forces_ceinms_so
        self.activation_errors = activation_errors
        self.muscle_work = muscle_work
        self.compare_forces_torsion= compare_forces_torsion
        self.muscle_work_torsion = muscle_work_torsion
        self.ik_and_id = ik_and_id
        self.muscle_work_so = muscle_work_so

    def to_dict(self):
        return self.__dict__


# %%
project_folder=r'C:\Git\isbs2024\Data'
project_settings = bp.create_project_settings(project_folder)

data_folder = cs.get_main_path()
subject_list = project_settings['subject_list']
# subject_list = ['Athlete_06_torsion','Athlete_14_torsion','Athlete_20_torsion','Athlete_22_torsion','Athlete_25_torsion','Athlete_26_torsion']
# subject_list = ['Athlete_22_torsion','Athlete_25_torsion','Athlete_26_torsion']
subject_list = ['Athlete_03','Athlete_03_torsion']
trial_list = ['sq_70','sq_90']


# option [moment_errors, compare_forces_ceinms, activation_errors, muscle_work]
steps_to_plot = steps(moment_errors = False, compare_forces_ceinms_so = False, 
                      activation_errors = False, muscle_work = False, compare_forces_torsion = True,
                      muscle_work_torsion= True, ik_and_id = False, muscle_work_so = True)


cs.print_terminal_spaced(' ')
print('subject list: ')
print(subject_list)
print('trial list: ')
print(trial_list)
print('steps to plot: ')
print(steps_to_plot.to_dict())
print(' ')


bp.ask_to_continue()

# trial_list = ['sq_90']
for subject_name in subject_list:
    for trial_name in trial_list:

        cs.print_to_log_file(f'Plotting {subject_name} {trial_name}',mode='simple')

        # create subject paths object with all the paths in it 
        paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)
        ceinms_results_torque = os.path.join(paths.ceinms_results,'Torques.sto')
        
        # plot moment errors between inverse dynamics and ceinms
        if steps_to_plot.moment_errors:
            if not os.path.exists(ceinms_results_torque):   
                print(f'No ceinms results found for {subject_name} {trial_name}')
                continue
            else:
                print(f'Plotting {subject_name} {trial_name}')

            id_mom = bp.import_sto_data(paths.id_output)

            # time normalise moments to 101 points
            fs = round(1/(id_mom['time'][1]-id_mom['time'][0]))
            id_mom_normalised = bp.time_normalise_df(id_mom,fs)  
            ceinms_mom_normalised = bp.time_normalise_df(bp.import_sto_data(ceinms_results_torque),fs)

            # remove _moment from column names
            id_mom_normalised.columns = id_mom_normalised.columns.str.replace('_moment', '')

            columns_to_plot = ['hip_flexion_r','hip_flexion_l','hip_adduction_r','hip_adduction_l',
                            'hip_rotation_r','hip_rotation_l','knee_angle_r','knee_angle_l',
                            'ankle_angle_r','ankle_angle_l']
            
            # plot moments comparison between inverse dynamics and ceinms
            save_path = os.path.join(paths.results, 'moment_errors' ,f'{subject_name}_{trial_name}_moments.png')    
            pltc.compare_two_df(id_mom_normalised,ceinms_mom_normalised,columns_to_compare=columns_to_plot,
                        legend=['inverse dynamics', 'ceinms'],ylabel='Moment (Nm)',xlabel='Squat cycle (%)',save_path=save_path)
            
            # plot muscle work between two legs
            df = bp.import_sto_data(paths.ceinms_results_forces)
            df_int = bp.calculate_integral(df)
            df_int.to_csv(paths.ceinms_results_forces.replace('MuscleForces.sto','MuscleWork.csv'), index=False)
            fig = pltc.plot_muscle_work_per_leg(df_int)
            pltc.mmfn()

            save_path = os.path.join(paths.results, 'muscle_work' ,f'{subject_name}_{trial_name}_muscle_work.png')
            bp.save_fig(fig, save_path=save_path)
        
        # plot muscle activations comparison between static_opt and ceinms    
        if steps_to_plot.activation_errors:
            act_ceinms = bp.time_normalise_df(bp.import_sto_data(paths.ceinms_results_activations))
            act_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.so_output_activations))
            act_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.emg))

            # find the muscles-emg pairs from the excitation generator xml file
            excitation_pairs = cs.print_excitation_input_pairs(paths.ceinms_exc_generator)

            # change the column names to match the excitation generator xml file
            cs.print_terminal_spaced('activation errors code not finished yet')
            continue
            raise Exception('change the column names to match the excitation generator xml file')

            muscle_groups = ['hip_flex_r','hip_flex_l','hip_ext_r','hip_ext_l',
                            'hip_add_r','hip_add_l','hip_abd_r','hip_abd_l',
                            'hip_inrot_r','hip_inrot_l','hip_exrot_r','hip_exrot_l',
                            'knee_flex_r','knee_flex_l','knee_ext_r','knee_ext_l',
                            'ankle_df_r','ankle_df_l','ankle_pf_r','ankle_pf']

            for group in muscle_groups:
                print(group)
                columns_to_plot = bp.get_muscles_by_group_osim(paths.model_scaled,[group])
                columns_to_plot = columns_to_plot['all_selected']
                if len(columns_to_plot) < 3 or len(act_static_opt) == 0 or len(act_ceinms) == 0:
                    continue
                
                save_path = os.path.join(paths.results, 'muscle_activation_comparison' ,f'{subject_name}_{trial_name}_{group}.png')  
                print(f'Plotting {group} to {save_path}')

                pltc.compare_two_df(act_static_opt,act_ceinms,columns_to_compare=columns_to_plot,
                                legend=['static opt', 'ceinms'],ylabel='Muscle force (N)',xlabel='Squat cycle (%)',save_path=save_path)

        # plot muscle forces comparison between static_opt and ceinms    
        if steps_to_plot.compare_forces_ceinms_so:  
           
            forces_ceinms = bp.time_normalise_df(bp.import_sto_data(paths.ceinms_results_forces))
            forces_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.so_output_forces))

            muscle_groups = ['hip_flex_r','hip_flex_l','hip_ext_r','hip_ext_l',
                            'hip_add_r','hip_add_l','hip_abd_r','hip_abd_l',
                            'hip_inrot_r','hip_inrot_l','hip_exrot_r','hip_exrot_l',
                            'knee_flex_r','knee_flex_l','knee_ext_r','knee_ext_l',
                            'ankle_df_r','ankle_df_l','ankle_pf_r','ankle_pf']

            for group in muscle_groups:
                print(group)
                columns_to_plot = bp.get_muscles_by_group_osim(paths.model_scaled,[group])
                columns_to_plot = columns_to_plot['all_selected']
                if len(columns_to_plot) < 3 or len(forces_static_opt) == 0 or len(forces_ceinms) == 0:
                    continue
                
                save_path = os.path.join(paths.results, 'muscle_force_comparison' ,subject_name,trial_name,f'{group}.png')  
                print(f'Plotting {group} to {save_path}')

                pltc.compare_two_df(forces_static_opt,forces_ceinms,columns_to_compare=columns_to_plot,
                                legend=['static opt', 'ceinms'],ylabel='Muscle force (N)',xlabel='Squat cycle (%)',save_path=save_path)

        # plot muscle work between two legs
        if steps_to_plot.muscle_work:
            df = bp.import_sto_data(paths.ceinms_results_forces)
            fig = pltc.plot_muscle_work_per_leg(df)

            save_path = os.path.join(paths.results, 'muscle_work_per_leg' ,f'{subject_name}_{trial_name}.png')
            bp.save_fig(fig, save_path=save_path)

        # plot muscle force comparison between generic and torsion
        if steps_to_plot.compare_forces_torsion and not subject_name.endswith('_torsion'):
            subject_torsion = subject_name + '_torsion'
            paths_torsion = cs.subject_paths(data_folder,subject_code=subject_torsion,trial_name=trial_name)
            
            # get muuscle names (list(set()) removes duplicates)
            model_path = paths.model_scaled
            muscles = get_muscles_by_group_osim(model_path,'all')
            groups = list(muscles.keys())
            hip_r = [group for group in groups if group.startswith('hip') and group.endswith('r')]
            muscles_hip_r = list(set([muscle for group in hip_r for muscle in muscles.get(group, [])]))
            
            hip_l = [muscle for muscle in muscles if muscle.startswith('hip') and muscle.endswith('l')]
            muscles_hip_l = list(set([muscle for group in hip_l for muscle in muscles.get(group, [])]))

            knee_r = [muscle for muscle in muscles if muscle.startswith('knee') and muscle.endswith('r')]
            muscles_knee_r = list(set([muscle for group in knee_r for muscle in muscles.get(group, [])]))

            knee_l = [muscle for muscle in muscles if muscle.startswith('knee') and muscle.endswith('l')]
            muscles_knee_l = list(set([muscle for group in knee_l for muscle in muscles.get(group, [])]))

            ankle_r = [muscle for muscle in muscles if muscle.startswith('ankle') and muscle.endswith('r')]
            muscles_ankle_r = list(set([muscle for group in ankle_r for muscle in muscles.get(group, [])]))

            ankle_l = [muscle for muscle in muscles if muscle.startswith('ankle') and muscle.endswith('l')]
            muscles_ankle_l = list(set([muscle for group in ankle_l for muscle in muscles.get(group, [])]))

            # muscles_ext_r = list(set(muscles['hip_ext_r'] + muscles['hip_abd_r'] + muscles['hip_exrot_r'] + muscles['knee_ext_r'] + muscles['ankle_pf_r']))
            # muscles_flex_r = list(set(muscles['hip_flex_r'] + muscles['hip_add_r'] + muscles['hip_inrot_r'] + muscles['knee_flex_r'] + muscles['ankle_df_r']))

            # muscles_ext_l = list(set(muscles['hip_ext_l'] + muscles['hip_abd_l'] + muscles['hip_exrot_l'] + muscles['knee_ext_l'] + muscles['ankle_pf_l']))
            # muscles_flex_l = list(set(muscles['hip_flex_l'] + muscles['hip_add_l'] + muscles['hip_inrot_l'] + muscles['knee_flex_l'] + muscles['ankle_df_l']))

            save_path = os.path.join(paths.results, 'muscle_force_torsion',subject_name,f'{trial_name}.png')
            print(f'Plotting {subject_name} {trial_name} to {save_path}')

            try:
                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces, 
                                    columns_to_compare= muscles_hip_r ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_hip_right.png'))

                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces,
                                    columns_to_compare= muscles_hip_l ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_hip_left.png'))
                
                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces,
                                    columns_to_compare= muscles_knee_r ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_knee_right.png'))
                
                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces,
                                    columns_to_compare= muscles_knee_l ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_knee_left.png'))
                
                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces,
                                    columns_to_compare= muscles_ankle_r ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_ankle_right.png'))
                
                pltc.compare_two_df(paths.so_output_forces,paths_torsion.so_output_forces,
                                    columns_to_compare= muscles_ankle_l ,xlabel='time (s)',
                                ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_ankle_left.png'))
                
            except Exception as e:
                cs.print_to_log_file(f'Error plotting {subject_name} {trial_name} to {save_path}',mode='simple')
                print(e)
               
            
            

        # plot muscle work comparison between generic and torsion
        if steps_to_plot.muscle_work_torsion and not subject_name.endswith('_torsion'):
            paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)   
            scale_settings_path = os.path.join(paths.models, subject_name + '_scaled_scale_setup.xml')
            subject_weight = float(bp.get_tag_xml(scale_settings_path, 'mass')) * 9.81

            # muscle work generic
            if steps_to_plot.muscle_work_so:
                sto_file = paths.so_output_forces
            else:
                sto_file = paths.ceinms_results_forces
            model_path = paths.model_scaled
            muscle_work_generic = bp.sum_muscle_work(model_path, sto_file, body_weight = subject_weight)

            # muscle work torsion
            subject_name_torsion = subject_name + '_torsion'
            paths = cs.subject_paths(data_folder,subject_code=subject_name_torsion,trial_name=trial_name)   
            if steps_to_plot.muscle_work_so:
                sto_file = paths.so_output_forces
            else:
                sto_file = paths.ceinms_results_forces
            model_path = paths.model_scaled
            muscle_work_torsion = bp.sum_muscle_work(model_path, sto_file, body_weight = subject_weight)

            # concat and plot
            muscle_work = pd.concat([muscle_work_generic, muscle_work_torsion], ignore_index=True)

            fig = bp.plot_bar_df(muscle_work)
            plt.legend(['Generic', 'Torsion'])
            plt.ylabel('Muscle work (BW.s)')
            bp.save_fig(fig, save_path=os.path.join(paths.results, 'muscle_work_torsion' ,f'{subject_name}_{trial_name}.png'))

        # plot ik and id comparison between generic and torsion
        if steps_to_plot.ik_and_id and not subject_name.endswith('_torsion'):
            paths_torsion = cs.subject_paths(data_folder, subject_name + '_torsion', trial_name)
            
            # ik
            ik_generic = bp.time_normalise_df(bp.import_sto_data(paths.ik_output))
            ik_torsion = bp.time_normalise_df(bp.import_sto_data(paths_torsion.ik_output))
            dofs = ['hip_flexion_l','hip_flexion_r', 'hip_adduction_l', 'hip_adduction_r', 'hip_rotation_l', 'hip_rotation_r', 'knee_angle_l', 'knee_angle_r', 'ankle_angle_l', 'ankle_angle_r']
            save_path = os.path.join(paths.results, 'ik' ,f'{subject_name}_{trial_name}.png')
            pltc.compare_two_df(ik_generic,ik_torsion, columns_to_compare= dofs ,xlabel='time (s)',
                                ylabel='Angle (deg)', legend=['generic', 'torsion'],save_path=save_path)

            # id
            id_generic = bp.time_normalise_df(bp.import_sto_data(paths.id_output))
            id_torsion = bp.time_normalise_df(bp.import_sto_data(paths_torsion.id_output))
            dofs_moment = ['pelvis_tilt_moment','pelvis_list_moment','pelvis_rotation_moment',
               'pelvis_tx_force','pelvis_ty_force','pelvis_tz_force'] + [dof + '_moment' for dof in dofs]

            save_path = os.path.join(paths.results, 'id' ,f'{subject_name}_{trial_name}.png')
            pltc.compare_two_df(id_generic,id_torsion, columns_to_compare= dofs_moment ,xlabel='time (s)',
                                ylabel='moment (Nm)', legend=['generic', 'torsion'],save_path=save_path)
# END