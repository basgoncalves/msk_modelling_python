import msk_modelling_pkg_install
from bops import *
import os

####################################################### TESTS ################################################################
def test_import_c3d_data():
    c3dFilePath = get_testing_file_path('c3d')
    print(c3dFilePath)
    print(type(c3dFilePath))
    print(os.path.isfile(c3dFilePath))
    c3d_dict =  import_c3d_data(c3dFilePath = get_testing_file_path('c3d'))
    print(c3d_dict)
    
    return c3d_dict

def test_plot_EMG_data():
    c3dFilePath = get_testing_file_path('c3d')
    c3dFilePath = r'C:\Git\msk_modelling_python\ExampleData\SJ_example\SJ1.c3d'
    print(c3dFilePath)
    file_name = os.path.basename(c3dFilePath).split(".")[0]
    emg_linear_env_df = emg_filter(c3dFilePath)
    # Create a emg plot
    fig, ax = plt.subplots()  # Create a figure containing a single axes.
    ax.plot(emg_linear_env_df)  # Plot some data on the axes.
    plt.title(file_name)
    plt.xlabel("Time")
    plt.ylabel("Volt")
    plt.show()

def test_loop_through_folders():
    for subject_folder in get_subject_folders(get_testing_file_path()):
        for session in get_subject_sessions(subject_folder):
            session_path = os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

                resultsDir = get_trial_list(session_path,full_dir = True)[idx]
                print(resultsDir)

def add_marker_to_trc():
    print('still not finished...')

def test_IK():
    for subject_folder in get_subject_folders(testing_data_dir()):
        for session in get_subject_sessions(subject_folder):
            session_path = os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

                model_path = r'.\test.osim'
                ik_results_file = r'.\test.osim'
                mot_file = r'.\test.osim'
                grf_xml = r'.\test.osim'
                resultsDir = get_trial_list(session_path,full_dir = True)[idx]
                run_IK(model_path, trc_file, resultsDir, marker_weights_path)

def test_ID():

    for subject_folder in get_subject_folders(testing_data_dir()):
        for session in get_subject_sessions(subject_folder):
            session_path = os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

                model_path = r'.\test.osim'
                ik_results_file = r'.\test.osim'
                mot_file = r'.\test.osim'
                grf_xml = r'.\test.osim'
                resultsDir = get_trial_list(session_path,full_dir = True)[idx]
                # run_ID(model_path, ik_results_file, mot_file, grf_xml, resultsDir)
                print(resultsDir)

def test_writeTRC():
    trcFilePath = get_testing_file_path('trc')
    c3dFilePath = get_testing_file_path('c3d')
    writeTRC(c3dFilePath, trcFilePath)

def test_c3d_export():
    print(get_testing_file_path())
    c3dFilePath = get_testing_file_path('c3d')
    c3d_dict = get_c3d_data(c3dFilePath)
    c3d_osim_export(c3dFilePath)
    # data_rotated = rotateAroundAxes(data=c3d_dict, rotations=[], modelMarkers=c3d_dict['Labels'])

def run_all_tests():

    test_loop_through_folders()
    test_writeTRC()
    test_c3d_export()
    add_marker_to_trc()

def plot_so_trial(SoFilePath=''):
    # plot static optimization results one trial
    if not SoFilePath:
        SoFilePath = get_testing_file_path('so')
        print(SoFilePath)
    
    so_force = read_trc_file(SoFilePath[1])
    
    return so_force

################################################################################################################################
test_plot_EMG_data()
# export_c3d_multiple(r'C:\Git\research_data\TorsionToolAllModels\simulations\TD01\pre')
# subjet_select_gui()
# simple_gui()
# complex_gui()
# print(list(get_bops_settings()['subjects'].values()))
# add_markers_to_settings()
# run_all_tests()
# import_c3d_data(get_testing_file_path())
