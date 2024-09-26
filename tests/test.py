import tkinter as tk
from tkinter import filedialog
from msk_modelling_python.src import bops as bp 
import pandas as pd
from trc import TRCData
import os

main_path = r"C:\Git\research_data\Projects\test_project"
paths = bp.subject_paths(data_folder=main_path, subject_code="P01", session_name= 'pre', trial_name="dynamic04_l")
print('IK output path:')
print(paths.ik_output)
print('Model scaled path:')
print(paths.model_scaled)

mocap_data = TRCData()
mocap_data.load(paths.markers)
m = mocap_data['Markers']
v = list(mocap_data.values())
frame = v[11]
time = v[12]
markers = {'time': time, 'frame': frame}
for i in range(0, len(m)):
    markers[m[i]] = v[i+13]
df = pd.DataFrame.from_dict(markers)



import pdb; pdb.set_trace()
# trc_df.to_csv(paths.ik_output + 'markers.csv', index=False)

# bp.run_IK(osim_modelPath=paths.model_scaled, trc_file=paths.markers, resultsDir=paths.ik_output)