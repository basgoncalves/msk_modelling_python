import msk_modelling_pkg_install
import bops as bp

# bp.get_project_folder()
# print(bp.dir_bops())
# print(bp.dir_simulations())
# print(bp.get_subject_folders())
# bp.basic_gui()

# bp.export_c3d_multiple(r'C:\Git\research_data\TorsionToolAllModels\simulations\TD01\pre')

i = 0
for subject_folder in bp.get_subject_folders():
    for session in bp.get_subject_sessions(subject_folder):
        session_path = bp.os.path.join(subject_folder,session)           
        for trial_name in bp.get_trial_list(session_path,full_dir = False):
            c3d_data = bp.get_c3d_data(bp.get_trial_dirs(session_path, trial_name)['c3d'])
            
            c3d_data['marker_names']
            
            exit()
            
        
        
    
    
    
    


                              