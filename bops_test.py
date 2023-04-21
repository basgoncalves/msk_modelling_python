import msk_modelling_pkg_install
import bops as bp
from bops import *
import os

####################################################### TESTS ################################################################
def test_loop_through_folders():
    for subject_folder in bp.get_subject_folders(bp.get_testing_file_path()):
        for session in bp.get_subject_sessions(subject_folder):
            session_path = bp.os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(bp.get_trial_list(session_path,full_dir = False)):

                resultsDir = bp.get_trial_list(session_path,full_dir = True)[idx]
                print(resultsDir)

def add_marker_to_trc():
    print('still not finished...')

def test_IK():
    for subject_folder in bp.get_subject_folders(testing_data_dir()):
        for session in bp.get_subject_sessions(subject_folder):
            session_path = bp.os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(bp.get_trial_list(session_path,full_dir = False)):

                model_path = r'.\test.osim'
                ik_results_file = r'.\test.osim'
                mot_file = r'.\test.osim'
                grf_xml = r'.\test.osim'
                resultsDir = bp.get_trial_list(session_path,full_dir = True)[idx]
                bp.run_IK(model_path, trc_file, resultsDir, marker_weights_path)

def test_ID():

    for subject_folder in bp.get_subject_folders(testing_data_dir()):
        for session in bp.get_subject_sessions(subject_folder):
            session_path = bp.os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(bp.get_trial_list(session_path,full_dir = False)):

                model_path = r'.\test.osim'
                ik_results_file = r'.\test.osim'
                mot_file = r'.\test.osim'
                grf_xml = r'.\test.osim'
                resultsDir = bp.get_trial_list(session_path,full_dir = True)[idx]
                # bp.run_ID(model_path, ik_results_file, mot_file, grf_xml, resultsDir)
                print(resultsDir)

def test_writeTRC():
    trcFilePath = bp.get_testing_file_path('trc')
    c3dFilePath = bp.get_testing_file_path('c3d')
    writeTRC(c3dFilePath, trcFilePath)

def test_c3d_export():
    print(bp.get_testing_file_path())
    c3dFilePath = bp.get_testing_file_path('c3d')
    c3d_dict = bp.get_c3d_data(c3dFilePath)
    bp.c3d_osim_export(c3dFilePath)
    # data_rotated = bp.rotateAroundAxes(data=c3d_dict, rotations=[], modelMarkers=c3d_dict['Labels'])

def run_all_tests():

    test_loop_through_folders()
    test_writeTRC()
    test_c3d_export()
    add_marker_to_trc()


def plot_so_trial(SoFilePath=''):
    # plot static optimization results one trial
    if not SoFilePath:
        SoFilePath = bp.get_testing_file_path('so')
        print(SoFilePath)
    
    so_force = bp.read_trc_file(SoFilePath[1])
    
    return so_force

################################################################################################################################

# bp.export_c3d_multiple(r'C:\Git\research_data\TorsionToolAllModels\simulations\TD01\pre')
# bp.subjet_select_gui()
# bp.simple_gui()
# bp.complex_gui()
# print(list(bp.get_bops_settings()['subjects'].values()))
# bp.add_markers_to_settings()
# run_all_tests()

plot_so_trial()

bp.add_each_c3d_to_own_folder