import pandas as pd
import bops as bp
import os 
from trc import TRCData

def calculate_diff(lst):
    diff_list = [lst[i] - lst[i - 1] for i in range(1, len(lst))]
    return diff_list

def calculate_marker_speed(folder_name):
    
    # Load TRC file as a dataframe
    trc_file = os.path.join(folder_name,"markers.trc")

    mocap_data = TRCData()
    mocap_data.load(trc_file)

    # Calculate derivatives of columns LASI_2 and RASI_2
    Time = pd.DataFrame(mocap_data['Time'])
    for i in [0,1,2]:
        LASI = pd.DataFrame([row[i] for row in mocap_data['LASI']])
        RASI = pd.DataFrame([row[i] for row in mocap_data['RASI']])
        mocap_data['d_LASI'] = LASI.diff()/1000 / Time.diff()
        mocap_data['d_RASI'] = RASI.diff()/1000 / Time.diff()

        # Calculate average d_LASI and d_RASI
        average_d_LASI = mocap_data['d_LASI'].mean()
        average_d_RASI = mocap_data['d_RASI'].mean()

        # Calculate the mean of the two averages
        mean_derivative = (average_d_LASI + average_d_RASI) / 2
        mean_derivative = round(mean_derivative.item(),2)
        print(f"Mean speed column {i+1} (LASI & RASI)= {mean_derivative} m/s")

folder_name = r'C:\Git\research_data\torsion_deformities_healthy_kinematics\simulations\TD07\pre'

# Loop through all subfolders
for root, subdirs, files in os.walk(folder_name):
    if 'markers.trc' in files:
        print(f"Current folder {root} contains markers.trc file")
        calculate_marker_speed(root)
        
    else:
        continue
