import os
import glob
import matplotlib.pyplot as plt

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
    id_file_path =
    
