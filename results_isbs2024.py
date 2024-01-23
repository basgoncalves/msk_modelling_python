from bops import *
import ceinms_setup as cs
import plotting as pltc
from sklearn.preprocessing import MinMaxScaler
import bops as bp

project_folder=r'C:\Git\isbs2024\Data'
project_settings = bp.create_project_settings(project_folder)

data_folder = cs.get_main_path()
subject_list = project_settings['subject_list']
# subject_list = ['Athlete_06_torsion','Athlete_14_torsion','Athlete_20_torsion','Athlete_22_torsion','Athlete_25_torsion','Athlete_26_torsion']
# subject_list = ['Athlete_22_torsion','Athlete_25_torsion','Athlete_26_torsion']
subject_list = ['Athlete_03','Athlete_03_torsion']
trial_list = ['sq_70', 'sq_90']


steps_to_plot = ['moment_errors','compare_forces_ceinms','activation_errors','muscle_work']
steps_to_plot = steps_to_plot[-2:-1]

# trial_list = ['sq_90']
for subject_name in subject_list:
    for trial_name in trial_list:

        cs.print_to_log_file(f'Plotting {subject_name} {trial_name}',mode='simple')

        # create subject paths object with all the paths in it 
        paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)
        ceinms_results_torque = os.path.join(paths.ceinms_results,'Torques.sto')
        
        # plot moment errors between inverse dynamics and ceinms
        if 'moment_errors' in steps_to_plot:
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
            pltc.save_fig(fig, save_path=save_path)
        
        # plot muscle forces comparison between static_opt and ceinms    
        if 'compare_forces_ceinms' in steps_to_plot:  
           
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
                
                save_path = os.path.join(paths.results, 'muscle_force_comparison' ,f'{subject_name}_{trial_name}_{group}.png')  
                print(f'Plotting {group} to {save_path}')

                pltc.compare_two_df(forces_static_opt,forces_ceinms,columns_to_compare=columns_to_plot,
                                legend=['static opt', 'ceinms'],ylabel='Muscle force (N)',xlabel='Squat cycle (%)',save_path=save_path)

        # plot muscle activations comparison between static_opt and ceinms    
        if 'activation_errors' in steps_to_plot:
            act_ceinms = bp.time_normalise_df(bp.import_sto_data(paths.ceinms_results_activations))
            act_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.so_output_activations))
            act_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.emg))

            # find the muscles-emg pairs from the excitation generator xml file
            cs.print_excitation_input_pairs(paths.ceinms_excitation_generator)

            # change the column names to match the excitation generator xml file
            cs.print_terminal_spaced('activation errors code not finished yet')
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

        # plot muscle work between two legs
        if 'muscle_work' in steps_to_plot:
            df = bp.import_sto_data(paths.ceinms_results_forces)
            fig = pltc.plot_muscle_work_per_leg(df)

            save_path = os.path.join(paths.results, 'muscle_work' ,f'{subject_name}_{trial_name}_muscle_work.png')
            pltc.save_fig(fig, save_path=save_path)

# END