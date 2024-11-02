from msk_modelling_python import bp
from msk_modelling_python import cs

class steps:
    def __init__(self, moment_errors = True, compare_forces_ceinms_so = True, activation_errors = True, muscle_work = True, 
                 compare_forces_torsion = True, muscle_work_torsion = True, activation_torsion = True,
                 ik_and_id = True, muscle_work_so = True, joint_reaction_forces = True):
        
        self.moment_errors= moment_errors
        self.compare_forces_ceinms_so = compare_forces_ceinms_so
        self.activation_errors = activation_errors
        self.muscle_work = muscle_work
        self.compare_forces_torsion= compare_forces_torsion
        self.muscle_work_torsion = muscle_work_torsion
        self.ik_and_id = ik_and_id
        self.muscle_work_so = muscle_work_so
        self.activation_torsion = activation_torsion
        self.joint_reaction_forces = joint_reaction_forces

    def to_dict(self):
        return self.__dict__


def muscle_groups(paths):
    model_path = paths.model_scaled
    muscles = bp.get_muscles_by_group_osim(model_path,'all')
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

    return muscles_hip_r, muscles_hip_l, muscles_knee_r, muscles_knee_l, muscles_ankle_r, muscles_ankle_l

# use this function to get the personalised label for the plots and tables in the results
# it will return the personalised label and the title for the plot based on the subject name
def get_personlised_label(subject_name):
    if subject_name == 'Athlete_03':
        perosnalised_label = 'Personalised (AVA = {0}-{1} NSA = {2}-{3})'.format(4.4,4.7,130.5,130.3)
        personlised_title = 'Athlete 01'

    elif subject_name == 'Athlete_06':
        perosnalised_label = 'Personalised (AVA = {0}-{1} NSA = {2}-{3})'.format(2,3.5,132,129.9)
        personlised_title = 'Athlete 02'
    
    elif subject_name == 'Athlete_14':
        perosnalised_label = 'Personalised (AVA = {0}-{1} NSA = {2}-{3})'.format(8.3,12.7,130.3,132.2)
        personlised_title = 'Athlete 03'

    elif subject_name == 'Athlete_22':
        perosnalised_label = 'Personalised (AVA = {0}-{1} NSA = {2}-{3})'.format(23.1,28.1,129.1,130.9)
        personlised_title = 'Athlete 05'

    elif subject_name == 'Athlete_25':
        pass

    else:
        return 'Personalised'
    
    return perosnalised_label, personlised_title

def compare_jra_trials_torsion(subject_name,trial_name):
    data_folder = cs.get_main_path()
    paths1 = cs.subject_paths(data_folder, subject_name, trial_name)
    paths2 = cs.subject_paths(data_folder, subject_name + '_torsion' , trial_name)

    jra_of_interest = ['hip_r_on_femur_r_in_femur_r_fx','hip_r_on_femur_r_in_femur_r_fy','hip_r_on_femur_r_in_femur_r_fz','',
                           'walker_knee_r_on_tibia_r_in_tibia_r_fx','walker_knee_r_on_tibia_r_in_tibia_r_fy','walker_knee_r_on_tibia_r_in_tibia_r_fz','',
                           'ankle_r_on_talus_r_in_talus_r_fx','ankle_r_on_talus_r_in_talus_r_fy','ankle_r_on_talus_r_in_talus_r_fz','',
                           'hip_l_on_femur_l_in_femur_l_fx','hip_l_on_femur_l_in_femur_l_fy','hip_l_on_femur_l_in_femur_l_fz','',
                           'walker_knee_l_on_tibia_l_in_tibia_l_fx','walker_knee_l_on_tibia_l_in_tibia_l_fy','walker_knee_l_on_tibia_l_in_tibia_l_fz','',
                           'ankle_l_on_talus_l_in_talus_l_fx','ankle_l_on_talus_l_in_talus_l_fy','ankle_l_on_talus_l_in_talus_l_fz','']

    final_jra_names = ['hip_r_x','hip_r_y','hip_r_z','hip_r_resultant',
                                'knee_r_x','knee_r_y','knee_r_z','knee_r_resultant',
                                'ankle_r_x','ankle_r_y','ankle_r_z','ankle_r_resultant',
                                'hip_l_x','hip_l_y','hip_l_z','hip_l_resultant',
                                'knee_l_x','knee_l_y','knee_l_z','knee_l_resultant',
                                'ankle_l_x','ankle_l_y','ankle_l_z','ankle_l_resultant']
                              
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

    perosnalised_label, personlised_title = get_personlised_label(subject_name)
    plt.legend(['Generic',perosnalised_label])
    plt.title(personlised_title)

    plt.gca().xaxis.set_ticklabels(['hip_r', 'knee_r', 'ankle_r', 'hip_l', 'knee_l', 'ankle_l']) 
    plt.tight_layout()
    
    bp.save_fig(plt.gcf(),os.path.join(paths.results,'jra' , subject_name, trial_name + '_summary_forces.png'))
    plt.close()

    

    pass

def result_summary(subject_list, trial_list, data_folder):

    labels = ['Athlete_03', 'Athlete_06', 'Athlete_14', 'Athlete_20', 'Athlete_22', 'Athlete_25', 'Athlete_26']
    labels_2 = ['Athlete_01', 'Athlete_02', 'Athlete_03', 'Athlete_04','Athlete_05','Athlete_06','Athlete_07']
    perosnalised_label = []
    for idx,label in enumerate(labels):
        if label in subject_list:
            perosnalised_label.append(get_personlised_label(labels[idx])[0].replace('Personalised',labels_2[idx]))
                        
    
    muscle_work_diff = pd.DataFrame()
    jrl_diff = pd.DataFrame()
    jra = dict()
    jra['subject_list'] = []
    # gather muscle work and joint contact force difference for all atheltes
    for subject_name in subject_list:

        jra['subject_list'].append(subject_name)
        for trial_name in trial_list:
            
            if subject_name.endswith('_torsion'):
                continue

            if trial_name not in jra:
                jra[trial_name] = {}

            paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)
            try:
                muscle_work_per_subject = pd.read_csv(os.path.join(paths.results, 'muscle_work_torsion' ,f'{subject_name}_{trial_name}.csv'),index_col=0)
                create_summary_table(subject_name,trial_name)
                joint_forces_per_subject = pd.read_csv(os.path.join(paths.results, 'jra', subject_name, f'{trial_name}_summary.csv'), index_col=0)

                jra_time_series = pd.read_csv(os.path.join(paths.results, 'jra', subject_name, f'jra_generic_{trial_name}.csv'), index_col=0)
                jra_time_series_torsion = pd.read_csv(os.path.join(paths.results, 'jra', subject_name, f'jra_torsion_{trial_name}.csv'), index_col=0)
                
                # Iterate through the columns of the DataFrame
                for col in jra_time_series.columns:
                    # Skip columns with 'time' in the name
                    if 'time' in col:
                        continue
                    
                    # Check if the column is not already in the dictionary
                    if col not in jra[trial_name]:
                        # Create a new DataFrame with the current column
                        jra[trial_name][col] = pd.DataFrame({col: jra_time_series[col]})
                        jra[trial_name][col + '_torsion'] = pd.DataFrame({col: jra_time_series_torsion[col]})
                        jra[trial_name][col + '_difference'] = pd.DataFrame({col: jra_time_series[col]})
                    else:
                        # If the column already exists, update its values
                        jra[trial_name][col] = pd.concat([jra[trial_name][col], jra_time_series[col]], axis=1)
                        jra[trial_name][col + '_torsion'] = pd.concat([jra[trial_name][col + '_torsion'], jra_time_series[col]], axis=1)
                        jra[trial_name][col + '_difference'] = pd.concat([jra[trial_name][col + '_difference'], (jra_time_series[col] - jra_time_series_torsion[col])])
            
            except Exception as e:
                bp.print_terminal_spaced(f'Error loading files for {subject_name} {trial_name}')
                print(e)
                continue

            # work torsion(second row) - generic(first row)
            diff = (muscle_work_per_subject.iloc[1] - muscle_work_per_subject.iloc[0])/muscle_work_per_subject.iloc[0] * 100
            diff = muscle_work_per_subject.iloc[1] - muscle_work_per_subject.iloc[0]
            muscle_work_diff[subject_name] = diff

            resultant_rows = joint_forces_per_subject[joint_forces_per_subject['joint'].str.contains('_resultant')]
            diff_jrl = (resultant_rows['max_torsion']-resultant_rows['max_generic'])
            jrl_diff[subject_name] = diff_jrl
            joints = resultant_rows['joint'].to_list()
              
    # transpose and remove unnamed columns
    muscle_work_diff_short = muscle_work_diff
    unnamed_cols = muscle_work_diff_short.filter(regex='Unnamed').columns
    muscle_work_diff_short = muscle_work_diff_short.drop(unnamed_cols, axis=1)

    jrl_diff = jrl_diff.drop(jrl_diff.filter(regex='Unnamed').columns, axis=1)
    jrl_diff.to_csv(os.path.join(paths.results, 'jra' ,'summary_differences.csv'))

    # plot muscle work difference bar chart
    try:
        plt.rcParams['font.size'] = 15
        ax = muscle_work_diff_short.plot(kind='bar', figsize=(8, 6), colormap='viridis', width=0.75, fontsize=12)
        plt.xticks(rotation=45)
        plt.legend(perosnalised_label, loc = 'upper right', bbox_to_anchor=(1, 1))
        plt.ylabel('Δ Muscle work from generic (J/BW)')
        # plt.title('Muscle work difference between generic and torsion')
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.subplots_adjust(bottom=0.16)
       
        
        bp.save_fig(plt.gcf(), save_path=os.path.join(paths.results, 'muscle_work_torsion' ,'summary_differences.png'))
        
        muscle_work_diff.to_csv(os.path.join(paths.results, 'muscle_work_torsion' ,'summary_differences.csv'))
    except Exception as e:
        print('Failed to plot muscle work difference bar chart')
        print(e)

    # plot joint resultant forces difference bar chart
    try:
        ax = jrl_diff.plot(kind='bar', figsize=(10, 6), colormap='viridis', width=0.75)
        plt.ylabel('Δ Peak joint forces from generic (BW)')
        plt.legend(perosnalised_label)
        plt.legend('')
        plt.gca().set_xticklabels(['right hip','right knee','right ankle','left hip','left knee','left ankle'], rotation=45)
        # plt.title('Peak joint resultant forces difference between generic and torsion')
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.subplots_adjust(bottom=0.16)
        bp.save_fig(plt.gcf(), save_path=os.path.join(paths.results, 'jra' ,'summary_differences.png'))
        print(f'Plot saved in {os.path.join(paths.results, "jra" ,"summary_differences.png")}')
    except Exception as e:
        print('Failed to plot joint resultant forces difference bar chart')
        print(e)
    
    # plot muscle work difference spider chart
    try:
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, polar=True)
        ax.set_title('Muscle work difference between generic and peronalied model')
        angles = np.linspace(0, 2*np.pi, len(muscle_work_diff_short.columns), endpoint=False)
        ax.set_thetagrids(np.degrees(angles), labels=muscle_work_diff_short.columns)
        ax.set_theta_offset(np.pi/2)
        ax.set_theta_direction(-1)
        ax.set_rgrids(np.arange(0, 100, 10), labels=np.arange(0, 100, 10))
        
        lines = []
        for i, subject_name in enumerate(muscle_work_diff_short.index):
            line, = ax.plot(angles, muscle_work_diff_short.iloc[i])
            lines.append(line)
            ax.fill(angles, muscle_work_diff_short.iloc[i], alpha=0.1)
        
        plt.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.2)
        ax.legend(lines,perosnalised_label, loc='center', frameon=False,bbox_to_anchor=(0.5, -0.2))

        # Assuming you want to save the figure
        save_path = os.path.join(paths.results, 'muscle_work_torsion', 'summary_differences_spider.png')
        bp.save_fig(fig, save_path=save_path)
        print(f'Plot saved in {save_path}')
    except Exception as e:
        print('Failed to plot muscle work difference spider chart \n')
        print(e)
    
    # combine jra and muscle work difference
    try:
        # Create a new figure with a new set of Axes
        fig = plt.figure(figsize=(15, 6))
        ax = fig.add_subplot(121)
        ax_work = muscle_work_diff_short.plot(kind='bar',ax=plt.gca(),colormap='viridis')
        ax_work.set_title('A', loc='left',x=-0.01, y=1.05)
        ax_work.set_xticklabels(ax.get_xticklabels(), rotation=45)
        ax_work.set_ylabel(u'Δ muscle work differences [torsion - generic] (J/BW)')
        ax_work.spines['top'].set_visible(False)
        ax_work.spines['right'].set_visible(False)
        ax_work.legend('')
               
        
        # add subplot joint contact forces
        ax = fig.add_subplot(122)
        ax = jrl_diff.plot(kind='bar',ax=plt.gca(),colormap='viridis')
        ax.set_title('B', loc='left',x=-0.01, y=1.05)
        ax.set_ylabel(u'Δ peak joint contact forces [torsion - generic] (BW)')
        ax.set_xticklabels(['right hip','right knee','right ankle','left hip','left knee','left ankle'], rotation=45)
        ax.legend(perosnalised_label, loc='center', frameon=False,bbox_to_anchor=(0.75, 0.9))    

        plt.subplots_adjust(left=0.12, right=0.9, top=0.8, bottom=0.15)

        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        
        # save figure
        save_path = os.path.join(paths.results, 'summary_muscle_work_jra_differences.png')
        bp.save_fig(fig, save_path=save_path)   
    except Exception as e:
        print('Failed to combine jra and muscle work difference')
        print(e)


    # sumary table for joint reaction forces
    try:
        diff = pd.read_csv(os.path.join(paths.results, 'jra' ,'summary_differences.csv'), index_col=0)
        
        print('summary table for joint reaction forces')
        for col in diff.columns:
            print(col)
            print('hips {0} {1}'.format(diff[col].iloc[0],diff[col].iloc[3]))
            print('knees {0} {1}'.format(diff[col].iloc[1],diff[col].iloc[4]))
            print('ankles {0} {1}'.format(diff[col].iloc[2],diff[col].iloc[5]))

        pass
    except Exception as e:
        print('Failed to create summary table for joint reaction forces')
        print(e)

    exit()
    # plot summary joint reaction forces time series
    try:
        print_terminal_spaced('Plotting summary joint reaction forces time not finished yet. Exiting...')
        exit()

        for trial_name in jra:
            if trial_name == 'subject_list':
                continue
            for col in jra[trial_name]:
                if 'time' in col:
                    continue

                fig = plt.figure()
                plt.plot(jra[trial_name][col])
                plt.plot(jra[trial_name][col + '_torsion'])

                df1 = pd.DataFrame(jra[trial_name][col])
                df2 = pd.DataFrame(jra[trial_name][col + '_torsion'])

                fig, axs = pltc.compare_two_df(df1, df2, columns_to_compare='all',
                            xlabel='% Squat cycle',ylabel='Force (BW)', legend='',save_path='')
                fig.set_size_inches(10,5)
                legend = plt.legend(loc='upper right', frameon=False)
                save_path = os.path.join(paths.results,'jra' , trial_name + '_' + col + '_summary.png')
                bp.save_fig(plt.gcf(), save_path=save_path)
                plt.close()
    except Exception as e:
        print('Failed to plot summary joint reaction forces time series')
        print(e)
    # END



if __name__ == "__main__":
    project_folder=r'C:\Git\isbs2024\Data'
    project_settings = bp.create_project_settings(project_folder)

    data_folder = cs.get_main_path()
    subject_list = project_settings['subject_list']
    subject_list = ['Athlete_03','Athlete_06','Athlete_22']
    trial_list = ['sq_70','sq_90']

    # option [moment_errors, compare_forces_ceinms, activation_errors, muscle_work]
    steps_to_plot = steps(moment_errors = False, compare_forces_ceinms_so = False, 
                        activation_errors = False, muscle_work = False, compare_forces_torsion = False,
                        ik_and_id = False, muscle_work_torsion= True, muscle_work_so = True, 
                        activation_torsion = False, joint_reaction_forces = True)

    cs.print_terminal_spaced(' ')
    print('subject list: ')
    print(subject_list)
    print('trial list: ')
    print(trial_list)
    print('steps to plot: ')
    print(steps_to_plot.to_dict())
    print(' ')


    # comment out to run the indiviudla steps 
    result_summary(subject_list, trial_list, data_folder)
    exit()
    
    bp.ask_to_continue()

    # plot results per trial 
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
                
                cs.print_to_log_file(f'Moment errors',mode='simple')
    
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

                cs.print_to_log_file(f'Muscle activations ceinms-so',mode='simple')
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
                
                cs.print_to_log_file(f'Muscle forces ceinms-so ',mode='simple')
            # plot muscle work between two legs
            if steps_to_plot.muscle_work:
                df = bp.import_sto_data(paths.ceinms_results_forces)
                fig = pltc.plot_muscle_work_per_leg(df)

                save_path = os.path.join(paths.results, 'muscle_work_per_leg' ,f'{subject_name}_{trial_name}.png')
                bp.save_fig(fig, save_path=save_path)
                cs.print_to_log_file(f'Muscle work between legs',mode='simple')

            # plot muscle force comparison between generic and torsion
            if steps_to_plot.compare_forces_torsion and not subject_name.endswith('_torsion'):
                subject_torsion = subject_name + '_torsion'
                paths_torsion = cs.subject_paths(data_folder,subject_code=subject_torsion,trial_name=trial_name)
                
                # get muuscle names (list(set()) removes duplicates)
                muscles_hip_r, muscles_hip_l, muscles_knee_r, muscles_knee_l, muscles_ankle_r, muscles_ankle_l = muscle_groups(paths)

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
                    
                    cs.print_to_log_file(f'Muscle forces torsion',mode='simple')
                except Exception as e:
                    cs.print_to_log_file(f'Error plotting {subject_name} {trial_name} to {save_path}',mode='simple')
                    print(e)
                    
            # plot muscle activations comparison between generic and torsion                   
            if steps_to_plot.activation_torsion and not subject_name.endswith('_torsion'):
                subject_torsion = subject_name + '_torsion'
                paths_torsion = cs.subject_paths(data_folder,subject_code=subject_torsion,trial_name=trial_name)
                
                # get muuscle names (list(set()) removes duplicates)
                muscles_hip_r, muscles_hip_l, muscles_knee_r, muscles_knee_l, muscles_ankle_r, muscles_ankle_l = muscle_groups(paths)

                save_path = os.path.join(paths.results, 'muscle_activation_torsion',subject_name,f'{trial_name}.png')
                print(f'Plotting {subject_name} {trial_name} to {save_path}')

                try:
                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations, 
                                        columns_to_compare= muscles_hip_r ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_hip_right.png'))

                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations,
                                        columns_to_compare= muscles_hip_l ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_hip_left.png'))
                    
                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations,
                                        columns_to_compare= muscles_knee_r ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_knee_right.png'))
                    
                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations,
                                        columns_to_compare= muscles_knee_l ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_knee_left.png'))
                    
                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations,
                                        columns_to_compare= muscles_ankle_r ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_ankle_right.png'))
                    
                    pltc.compare_two_df(paths.so_output_activations,paths_torsion.so_output_activations,
                                        columns_to_compare= muscles_ankle_l ,xlabel='time (s)',
                                    ylabel='Force (N)', legend=['generic', 'torsion'],save_path=save_path.replace('.png','_ankle_left.png'))
                    
                    cs.print_to_log_file(f'Muscle activations torsion',mode='simple')
                except Exception as e:
                    cs.print_to_log_file(f'Error plotting {subject_name} {trial_name} to {save_path}',mode='simple')
                    print(e)            

            # plot muscle work comparison between generic and torsion
            if steps_to_plot.muscle_work_torsion and not subject_name.endswith('_torsion'):
                
                def calc_muscle_work(paths, subject_weight, steps_to_plot):
                    # muscle work generic
                    if steps_to_plot.muscle_work_so:
                        forces_sto_file = paths.so_output_forces
                    else:
                        forces_sto_file = paths.ceinms_results_forces

                    length_sto_file = os.path.join(paths.ma_output_folder,'_MuscleAnalysis_FiberLength.sto')
                    model_path = paths.model_scaled
                    muscle_work = bp.sum_muscle_work(model_path, forces_sto_file,length_sto_file, body_weight = subject_weight)

                    columns = muscle_work.index.tolist()
                    values = muscle_work.values.reshape(1, -1).tolist()
                    work_df = pd.DataFrame(values,columns=columns)

                    return work_df
                
                paths = cs.subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)   
                scale_settings_path = os.path.join(paths.models, subject_name + '_scaled_scale_setup.xml')
                subject_weight = float(bp.get_tag_xml(scale_settings_path, 'mass')) * 9.81

                # muscle work generic
                muscle_work_generic = calc_muscle_work(paths, subject_weight, steps_to_plot)
                
                # muscle work torsion
                subject_name_torsion = subject_name + '_torsion'
                paths = cs.subject_paths(data_folder,subject_code=subject_name_torsion,trial_name=trial_name)   
                muscle_work_torsion = calc_muscle_work(paths, subject_weight, steps_to_plot)

                # concat and plot
                muscle_work = pd.concat([muscle_work_generic, muscle_work_torsion], ignore_index=False)

                # subject AVA and NSA 
                perosnalised_label,personlised_title =  get_personlised_label(subject_name)
            
                fig = bp.plot_bar_df(muscle_work)
                plt.ylabel(' ')
                plt.legend(['Generic', perosnalised_label])
                plt.ylabel('Muscle work (J/BW)')
                plt.title(personlised_title)
                bp.save_fig(fig, save_path=os.path.join(paths.results, 'muscle_work_torsion' ,f'{subject_name}_{trial_name}.png'))

                # print difference in muscle work between generic and torsion
                muscle_work_difference = muscle_work_generic - muscle_work_torsion
                muscle_work = pd.concat([muscle_work, muscle_work_difference], ignore_index=False)

                muscle_work.to_csv(os.path.join(paths.results, 'muscle_work_torsion' ,f'{subject_name}_{trial_name}.csv'))
                
                cs.print_to_log_file(f'Muscle work torsion',mode='simple')
            
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
                
                cs.print_to_log_file(f'id',mode='simple')

                # id
                id_generic = bp.time_normalise_df(bp.import_sto_data(paths.id_output))
                id_torsion = bp.time_normalise_df(bp.import_sto_data(paths_torsion.id_output))
                dofs_moment = ['pelvis_tilt_moment','pelvis_list_moment','pelvis_rotation_moment',
                'pelvis_tx_force','pelvis_ty_force','pelvis_tz_force'] + [dof + '_moment' for dof in dofs]

                save_path = os.path.join(paths.results, 'id' ,f'{subject_name}_{trial_name}.png')
                pltc.compare_two_df(id_generic,id_torsion, columns_to_compare= dofs_moment ,xlabel='time (s)',
                                    ylabel='moment (Nm)', legend=['generic', 'torsion'],save_path=save_path)
                
                cs.print_to_log_file(f'id',mode='simple')

            # plot jra comparison between generic and torsion
            if steps_to_plot.joint_reaction_forces and not subject_name.endswith('_torsion'):
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
