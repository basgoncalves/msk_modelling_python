import msk_modelling_pkg_install
import bops as bp
import os


# bp.export_c3d_multiple(r'C:\Git\research_data\TorsionToolAllModels\simulations\TD01\pre')
# bp.subjet_select_gui()
# bp.simple_gui()
# bp.complex_gui()
# print(list(bp.get_bops_settings()['subjects'].values()))
# bp.add_markers_to_settings()

def testing_data_dir():
    bops_dir = bp.get_dir_bops()
    dir_simulations =  os.path.join(bops_dir, 'ExampleData\simulations')
    
    return dir_simulations

def test_loop_through_folders():       
    for subject_folder in bp.get_subject_folders(testing_data_dir()):
        for session in bp.get_subject_sessions(subject_folder):
            session_path = bp.os.path.join(subject_folder,session)           
            for idx, trial_name in enumerate(bp.get_trial_list(session_path,full_dir = False)):

                resultsDir = bp.get_trial_list(session_path,full_dir = True)[idx]
                print(resultsDir)

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

test_loop_through_folders()