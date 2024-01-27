
from bops import *
import bops as bp
import ceinms_setup as cs
from plotting import plot_ceinms as pltc


def compare_jra_trials_torsion(subject_name,trial_name):
    data_folder = cs.get_main_path()
    paths1 = cs.subject_paths(data_folder, subject_name, trial_name)
    paths2 = cs.subject_paths(data_folder, subject_name + '_torsion' , trial_name)

    jra_of_interest = ['hip_r_on_femur_r_in_femur_r_fx','hip_r_on_femur_r_in_femur_r_fy','hip_r_on_femur_r_in_femur_r_fz','',
                           'walker_knee_r_on_tibia_r_in_tibia_r_fx','walker_knee_r_on_tibia_r_in_tibia_r_fy','walker_knee_r_on_tibia_r_in_tibia_r_fz','',
                           'ankle_r_on_talus_r_in_talus_r_fx','ankle_r_on_talus_r_in_talus_r_fy','ankle_r_on_talus_r_in_talus_r_fz','']

    final_jra_names = ['hip_x','hip_y','hip_z','hip_resultant',
                              'knee_x','knee_y','knee_z','knee_resultant',
                              'ankle_x','ankle_y','ankle_z','ankle_resultant']

    weight = float(bp.get_tag_xml(paths1.model_scaled.replace('.osim', '_scale_setup.xml'), 'mass'))  * 9.81


    # functions to load data and sum 3d vectors
    def replace_name_in_df(df, old_name, new_name):
        df = df.rename(columns={old_name: new_name})
        return df

    def sum3d_vector(df, columns_to_sum = ['x','y','z'], new_column_name = 'sum'):
        # df = {col: [1.0, 2.0, 3.0] for col in columns_to_sum}
        df_cropped = pd.DataFrame(df)
        df[new_column_name] = np.sqrt(df[columns_to_sum[0]]**2 + df[columns_to_sum[1]]**2 + df[columns_to_sum[2]]**2)
        return df

    def sum3d_joint_forces(jra_df,columns_to_compare,final_jra_names):
        
        # rename columns (repalce )
        for i in range(len(columns_to_compare)):

            # if column is in df and not empty
            if columns_to_compare[i] in jra_df.columns and len(columns_to_compare[i])>0:
                print('column found: ', columns_to_compare[i])
                print('renaming to: ', final_jra_names[i])
                jra_df = replace_name_in_df(jra_df, columns_to_compare[i], final_jra_names[i])

            # if is empty
            elif len(columns_to_compare[i]) == 0:
                print('column empty: ', columns_to_compare[i])
                indices = list(np.arange(i - 3, i))
                selected_columns = [final_jra_names[i] for i in indices if final_jra_names[i]]
                jra_df = sum3d_vector(jra_df, columns_to_sum = selected_columns,new_column_name=final_jra_names[i])
       
            else:
                print('column not found: ', columns_to_compare[i])

        return jra_df

    # load data and sum 3d vectors
    try:
        sto_path = paths1.jra_output
        jra_generic = sum3d_joint_forces(
                        bp.normalise_df(
                            bp.import_sto_data(sto_path,['time'] + jra_of_interest),weight),jra_of_interest,final_jra_names)

        sto_path = paths2.jra_output
        jra_torsion = sum3d_joint_forces(
                        bp.normalise_df(
                            bp.import_sto_data(sto_path,['time'] + jra_of_interest),weight),jra_of_interest,final_jra_names) 
    except Exception as e:
        cs.print_terminal_spaced('Error loading jra')
        print(e)
        exit()


    # select only columns of interest
    try: 
        jra_generic[final_jra_names]
    except Exception as e:
        cs.print_terminal_spaced('Error plotting jra')
        print(e)
        exit()
    
    # time normalise data
    jra_generic = bp.time_normalise_df(jra_generic)
    jra_torsion = bp.time_normalise_df(jra_torsion)
    
    # plot
    try:
        title = os.path.basename(sto_path) + ' right leg' + ' ' + subject_name + ' ' + trial_name
        save_path = os.path.join(paths1.results,'jra' , subject_name, trial_name + '.png')

        fig, axs = pltc.compare_two_df(jra_generic,jra_torsion, columns_to_compare=final_jra_names,
                            xlabel='% Squat cycle',ylabel='Force (BW)', legend=['Generic', 'Personalised'],save_path='')
    
        # add title and change figure size
        fig.suptitle(title)
        fig.set_size_inches(10,5)
        bp.save_fig(plt.gcf(), save_path=save_path)
    except Exception as e:
        cs.print_terminal_spaced('Error plotting jra')
        print(e)
        exit()

    # save as .csv
    try:
        jra_generic.to_csv(os.path.join(paths1.results,'jra' , subject_name, 'jra_generic_' + trial_name + '.csv'))
        jra_torsion.to_csv(os.path.join(paths1.results,'jra' , subject_name, 'jra_torsion_' + trial_name + '.csv'))
    except Exception as e:
        cs.print_terminal_spaced('Error saving jra_simple_' + trial_name + '.csv')
        print(e)
        exit()

    print('simple jra saved in: ', os.path.join(paths1.results,'jra' , subject_name + trial_name + '.csv')) 

    return jra_generic, jra_torsion

def calculate_vector_angles(df, timeNorm = True):
    
    col_names = df.columns

    # Create a defaultdict to store the groups
    grouped_cols = dict()

    # Group the names based on the common part
    for name in col_names:
        common_part = name.split('_')[0]  # Extract the common part (e.g., 'hip', 'knee', 'ankle')
        if common_part not in grouped_cols:
            grouped_cols[common_part] = []
    
        # Append the name to the list
        grouped_cols[common_part].append(name)

    angles = pd.DataFrame()
    for group in grouped_cols:

        if len(grouped_cols[group]) < 3:
            continue

        x = df[grouped_cols[group][0]]
        y = df[grouped_cols[group][1]]
        z = df[grouped_cols[group][2]]

        # Calculate the magnitude of the vector
        magnitude = np.sqrt(x**2 + y**2 + z**2)
        
        # Calculate angles with respect to coordinate axes
        theta_x = np.arccos(x / magnitude)
        theta_y = np.arccos(y / magnitude)
        theta_z = np.arccos(z / magnitude)
        
        # Convert angles to degrees
        theta_x_deg = np.degrees(theta_x)
        theta_y_deg = np.degrees(theta_y)
        theta_z_deg = np.degrees(theta_z)
        
        # Add thetas to angles dataframe
        angles[group + '_theta_x'] = theta_x_deg
        angles[group + '_theta_y'] = theta_y_deg
        angles[group + '_theta_z'] = theta_z_deg
    

    # time normalise data
    if timeNorm:
        fs = round(1/(df['time'].iloc[1] - df['time'].iloc[0]))
        bp.time_normalise_df(angles,fs)

    return angles

def compare_jra_angles(subject_name,trial_name):

    paths = cs.subject_paths(cs.get_main_path(), subject_name, trial_name)	
    try:
        jra_generic = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, 'jra_generic_' + trial_name + '.csv'))
        jra_torsion = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, 'jra_torsion_' + trial_name + '.csv'))
    except Exception as e:
        cs.print_terminal_spaced('Error loading jra')
        print(e)
        exit()
    
    try:
        jra_generic_angles = calculate_vector_angles(jra_generic, timeNorm=False)
        jra_torsion_angles = calculate_vector_angles(jra_torsion, timeNorm=False)
    except Exception as e:
        cs.print_terminal_spaced('Error calculating angles')
        print(e)
        exit()

    jra_generic_angles.to_csv(os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles_generic.csv'))
    jra_torsion_angles.to_csv(os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles_torsion.csv'))

    if 'time' in jra_generic_angles.columns:
        jra_generic_angles.drop('time')

    fig, axs = pltc.compare_two_df(jra_generic_angles,jra_torsion_angles, columns_to_compare=jra_generic_angles.columns,
                            xlabel='% Squat cycle',ylabel='Angle (deg)', legend=['Generic', 'Personalised'],save_path='')

    fig.set_size_inches(10,5)
    save_path = os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles.png')
    bp.save_fig(plt.gcf(), save_path=save_path)

    print('results saved in: ', os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles.png'))

def create_summary_table(subject_name,trial_name):

    data_folder = cs.get_main_path()
    paths = cs.subject_paths(data_folder, subject_name, trial_name)

    jra_generic = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, 'jra_generic_' + trial_name + '.csv'))
    jra_torsion = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, 'jra_torsion_' + trial_name + '.csv'))

    jra_generic_angles = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles_generic.csv'))
    jra_torsion_angles = pd.read_csv(os.path.join(paths.results,'jra' , subject_name, trial_name + '_angles_torsion.csv'))

    summary_table = pd.DataFrame(columns=['joint','max_generic','max_torsion','dif_max','min_generic','min_torsion','dif_min','mean_generic','mean_torsion','dif_mean'])

    # summary forces
    for col in jra_generic.columns:
        if 'time' in col:
            continue
        summary_table.loc[len(summary_table)] = [col,
                                                round(jra_generic[col].max(),2),
                                                round(jra_torsion[col].max(),2),
                                                round(jra_generic[col].max() - jra_torsion[col].max(),2),
                                                round(jra_generic[col].min(),2),
                                                round(jra_torsion[col].min(),2),
                                                round(jra_generic[col].min() - jra_torsion[col].min(),2),
                                                round(jra_generic[col].mean(),2),
                                                round(jra_torsion[col].mean(),2),
                                                round(jra_generic[col].mean() - jra_torsion[col].mean(),2)
                                                ]
        
    
    # summary angles
    for col in jra_generic_angles.columns:
        if 'time' in col:
            continue
        summary_table.loc[len(summary_table)] = [col,
                                                round(jra_generic_angles[col].max(),2),
                                                round(jra_torsion_angles[col].max(),2),
                                                round(jra_generic_angles[col].max() - jra_torsion_angles[col].max(),2),
                                                round(jra_generic_angles[col].min(),2),
                                                round(jra_torsion_angles[col].min(),2),
                                                round(jra_generic_angles[col].min() - jra_torsion_angles[col].min(),2),
                                                round(jra_generic_angles[col].mean(),2),
                                                round(jra_torsion_angles[col].mean(),2),
                                                round(jra_generic_angles[col].mean() - jra_torsion_angles[col].mean(),2)
                                                ]


    summary_table.to_csv(os.path.join(paths.results,'jra' , subject_name, trial_name + '_summary.csv'))

    # plot peak resultant forces
    summary_table_forces = summary_table.copy()
    
    summary_table_forces = summary_table.iloc[0:12]
    summary_table_forces = summary_table_forces.set_index('joint')
    summary_table_forces = summary_table_forces[['max_generic','max_torsion']]
    summary_table_forces.columns = ['Generic','Personalised']
    summary_table_forces = summary_table_forces.sort_values(by=['Generic'], ascending=False)

    # only joints _resultant
    summary_table_forces = summary_table[summary_table['joint'].str.contains('_resultant')]

    max_columns = summary_table_forces.filter(like='max') 
    joint_column = summary_table_forces.filter(like='joint')
    summary_table_forces = pd.concat([joint_column,max_columns],axis=1)
    summary_table_forces.drop('dif_max',axis=1,inplace=True)
    summary_table_forces.plot(kind='bar', rot=1, colormap='viridis', figsize=(10,5))
    plt.ylabel('peak joint contact force (BW)')
    plt.title('Peak resultant forces')
    plt.legend(['Generic','Personalised'])

    plt.gca().xaxis.set_ticklabels(['Hip', 'Knee', 'Ankle']) 
    plt.tight_layout()
    
    bp.save_fig(plt.gcf(),os.path.join(paths.results,'jra' , subject_name, trial_name + '_summary_forces.png'))
    plt.close()

    

    pass


data_folder = cs.get_main_path()
project_settings = bp.create_project_settings(data_folder)
subject_list = project_settings['subject_list']
subject_list = subject_list[2:4]
trial_list = ['sq_70','sq_90']

for subject_name in subject_list:
    for trial_name in trial_list:

        if subject_name.endswith('_torsion'):
            continue

        
        cs.print_terminal_spaced('Plotting JRA: ' + subject_name + ' ' + trial_name)
        cs.print_to_log_file('\n Plotting JRA: ' + subject_name + ' ' + trial_name)

        try:
            compare_jra_trials_torsion(subject_name,trial_name)
            cs.print_to_log_file('                compared jra time series ')

            compare_jra_angles(subject_name,trial_name)
            cs.print_to_log_file('                compared jra angles ')

            create_summary_table(subject_name,trial_name)
            cs.print_to_log_file('                summary completed ')
        except Exception as e:
            
            cs.print_to_log_file('Error processing: ' + subject_name + ' ' + trial_name)
            cs.print_to_log_file(str(e))    



