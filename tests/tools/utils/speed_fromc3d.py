import pandas as pd
import msk_modelling_python.src.bops as bp
import os 
from trc import TRCData

def calculate_diff(lst):
    diff_list = [lst[i] - lst[i - 1] for i in range(1, len(lst))]
    return diff_list

def calculate_marker_speed(filename):
    
    # Load TRC file as a dataframe
    c3d_data = bp.import_c3d_to_dict(filename)
    
    Time = pd.DataFrame(c3d_data['TimeStamps'])
    
    indice_RASI = [i for i, marker in enumerate(c3d_data['MarkerNames']) if 'RASI' in marker]
    RASI = [c3d_data['Data'][index] for index in indice_RASI]
    
    indice_LASI = [i for i, marker in enumerate(c3d_data['MarkerNames']) if 'LASI' in marker]
    LASI = [c3d_data['Data'][index] for index in indice_LASI]
    
    for i in [0,1,2]:
        LASI_i = pd.DataFrame([row[i] for row in LASI[0]])
        RASI_i = pd.DataFrame([row[i] for row in RASI[0]])
        speed_LASI = LASI_i.diff()/1000 / Time.diff()
        speed_RASI = RASI_i.diff()/1000 / Time.diff()

        # Calculate average d_LASI and d_RASI
        averageSpeedLASI = speed_LASI.mean()
        averageSpeedRASI = speed_RASI.mean()

        # Calculate the mean of the two averages
        mean_derivative = (averageSpeedLASI + averageSpeedRASI) / 2
        mean_derivative = round(mean_derivative.item(),2)
        if abs(mean_derivative) > 0.7:
            print(f"Mean speed column {i+1} (LASI & RASI)= {mean_derivative} m/s")

folder_name = r'C:\Git\research_data\torsion_deformities_healthy_kinematics\simulations\TD07\pre'

# Loop through all subfolders
for root, subdirs, files in os.walk(folder_name):
   for file in files:
        if file.endswith('.c3d'):
            print('values for' + root + '\\' + file)
            filename = os.path.join(root,file)
            calculate_marker_speed(filename)
        else:
            continue