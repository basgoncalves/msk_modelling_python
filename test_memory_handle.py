from ceinms_setup import *



data_folder = get_main_path()
subject_list = ['Athlete_03','Athlete_06','Athlete_14','Athlete_20','Athlete_22','Athlete_25','Athlete_26']
subject_list = ['Athlete_03_torsion']

trial_list = ['sq_70', 'sq_90']
trial_list = ['sq_90']
for subject_name in subject_list:
    for trial_name in trial_list:
        
        # create subject paths object with all the paths in it 
        paths = subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)
        # paths.model_scaled = os.path.join(data_folder,'Scaled_models\{i}_scaled.osim'.format(i=subject_name))
            
        if not os.path.isdir(paths.trial):
            raise Exception('Trial folder not found: {}'.format(paths.trial))

        if not os.path.isfile(paths.model_scaled):
            raise Exception('Scaled model not found: {}'.format(paths.model_scaled))

        print_terminal_spaced('Running pipeline for ' + subject_name + ' ' + trial_name)

        print_to_log_file('')
        print_to_log_file('Running pipeline for ',subject_name + ' ' + trial_name, 'start') # log file

        # edit xml files 
        relative_path_grf = os.path.relpath(paths.grf, os.path.dirname(paths.grf_xml))
        edit_xml_file(paths.grf_xml,'datafile',relative_path_grf)

        for i in range(50):
            print_terminal_spaced('Loop ' + str(i))
            # find time range for the trial 
            try:
                print_to_log_file('getting times from IK.mot  ... ', ' ', 'start') # log file
                initial_time, last_time = get_initial_and_last_times(paths.ik_output)
                print_to_log_file('done!', ' ', ' ') # log file
            except Exception as e:
                print_to_log_file('stop for error ...' , ' ', ' ') # log file
                print_to_log_file(e)
                raise Exception('Get initial and last times failed for ' + subject_name + ' ' + trial_name)
            
            initial_time = 2.165
            last_time = 6.07
        
            # edit muscle analysis setup files
            try:
                print_to_log_file('muscle analysis setup  ... ', ' ', 'start') # log file
                template_ma_setup = os.path.join(paths.setup_folder,'setup_ma.xml')
                shutil.copy(template_ma_setup, paths.ma_setup)
                edit_muscle_analysis_setup(paths.ma_setup,paths.model_scaled,initial_time, last_time)
                print_to_log_file('done! ', ' ', ' ') # log file
            except Exception as e:
                print_to_log_file('stop for error ...' , ' ', ' ') # log file
                print_to_log_file(e)
                raise Exception('Muscle analysis setup failed for ' + subject_name + ' ' + trial_name)
            
        exit()