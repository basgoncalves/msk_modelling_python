import msk_modelling_pkg_install
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import bops
import pandas as pd
import numpy as np


######### edit this part only ########
session_dir = r'C:\Git\Uni_teaching\BD2II - Biomechanical Motion Analysis in Practice (2023S)\lab3-EMG' # directory of the folder containing the c3d files
emg_labels = ['EMG Channels.EMG16_left_tens_fasc_lat']                                                  # labels of the EMG channels in the c3d file

fs = 1000.0  # sample rate, Hz
lowcut = 10.0  # lower cut-off frequency, Hz
lowcut_2 = 6.0  # lower cut-off frequency, Hz
highcut = 50.0  # upper cut-off frequency, Hz
order = 4  # filter order

#######################################

if not os.path.isdir(session_dir):
    current_path = os.getcwd()
    Tk().withdraw()                                     
    session_dir = askopenfilename(initialdir=current_path) 

bops.add_each_c3d_to_own_folder(session_dir)

trial_list = [f.name for f in os.scandir(session_dir) if f.is_dir()]
trial_list = [s for s in trial_list if 'static' not in s]
mean_emg = []

for trial in trial_list:
    # file directories
    trial_folder = os.path.join(session_dir, trial)
    
    c3dpath = os.path.join(trial_folder, 'c3dfile.c3d')
    emgpath = os.path.join(trial_folder, 'emg.csv')
    if not os.path.isfile(c3dpath):
        try:
            bops.c3d_osim_export(c3dpath)
        except:
            print('could not convert ' + c3dpath + ' to markers and grf') 
    
    if not os.path.isfile(emgpath):
        try: 
            bops.c3d_emg_export(c3dpath,emg_labels)
        except:
            print('could not convert ' + c3dpath + ' to emg.csv') 
    
    emg_data = pd.read_csv(emgpath, index_col=0)
    emg_data_filtered = bops.emg_filter(emg_data, lowcut, highcut, lowcut_2, fs, order)
    emg_filename = os.path.join(trial_folder,'emg_filtered.csv')
    emg_data_filtered.to_csv(emg_filename)
    
    
    for col in emg_data_filtered.columns:
        max_rolling_average = np.max(pd.Series(emg_data_filtered[col]).rolling(200, min_periods=1).mean())
        mean_emg.append(max_rolling_average)
    

print(mean_emg)
    
    