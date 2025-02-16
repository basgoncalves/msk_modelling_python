import bops as bp
from bops import *
import matplotlib.pyplot as plt

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
            file_path = bp.get_trial_dirs(session_path, trial_name)['id']
            data = bp.import_file(file_path)
            print(data)
            exit()

def plot_data():
        
    # Define the base directory
    base_dir = "C:/Git/research_data/TorsionToolAllModels/simulations"

    # Loop through all folders inside the base directory
    for folder in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder)
        if not os.path.isdir(folder_path):
            continue

        # Inside each folder, loop through folders in the "pre" directory
        pre_folder_path = os.path.join(folder_path, "pre")
        dynamic_folder_path = os.path.join(pre_folder_path, "dynamic")
        if not os.path.isdir(dynamic_folder_path):
            continue

        # Load data from the "ik.mot" file
        ik_file_path = os.path.join(pre_folder_path, "ik.mot")
        with open(ik_file_path) as f:
            lines = f.readlines()
            headers = lines[6].split("\t")[2:]
            data = {header: [] for header in headers}
            for line in lines[7:]:
                values = line.split("\t")[2:]
                for header, value in zip(headers, values):
                    data[header].append(float(value))

        # Plot the "ik.mot" data
        for header in ["hip_flexion_r", "hip_adduction_r", "hip_rotation_r", "knee_angle_r", "ankle_angle_r"]:
            plt.plot(data["time"], data[header], label=header)
        plt.legend()
        plt.title("IK Data")

        # Load data from the "inverse_dynamics.sto" file
        id_file_path = a
        


        
        
    
    
    
    


                              