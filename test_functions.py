from ceinms_setup import *
import ceinms_setup as cs   
import bops as bp
import plotting as pltc

data_folder = cs.get_main_path()
subject_name = 'Athlete_03'
trial_name = 'sq_70'
paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)   

# plot muscle forces comparison between static_opt and ceinms
forces_ceinms = bp.time_normalise_df(bp.import_sto_data(paths.ceinms_results_forces))
forces_static_opt = bp.time_normalise_df(bp.import_sto_data(paths.so_output_forces))
columns_to_plot = forces_ceinms.columns.difference(['time'])

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

print('Done')

# END 