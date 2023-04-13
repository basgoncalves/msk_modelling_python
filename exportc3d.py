import msk_modelling_pkg_install
import os
import tkfilebrowser
from tkinter import *
import bops
import pandas as pd
import numpy as np

current_path = os.getcwd()
Tk().withdraw()                                     
subject_folders = tkfilebrowser.askopendirnames(initialdir=current_path,title='Please select subject folders to export .c3d files') 

for subject_dir in subject_folders:
    session_list = [f.name for f in os.scandir(subject_dir) if f.is_dir()]
    for session in session_list:
        session_path = os.path.join(subject_dir, session)
        bops.add_each_c3d_to_own_folder(session_path)
        bops.add_each_c3d_to_own_folder(session_path)
        
######### edit this part only ########
emg_labels = ['EMG Channels.EMG16_left_tens_fasc_lat']                 # labels of the EMG channels in the c3d file
emg_labels = ['Voltage.EMG01_r_gastro']
#######################################

if not os.path.isdir(session_path):
    current_path = os.getcwd()
    Tk().withdraw()                                     
    session_path = askopenfilename(initialdir=current_path) 


trial_list = [f.name for f in os.scandir(session_path) if f.is_dir()]
trial_list = [s for s in trial_list if 'static' not in s]
max_emg_list = []

for trial in trial_list:
    # file directories
    trial_folder = os.path.join(session_path, trial)
    
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
    emg_data_filtered = bops.emg_filter(emg_data, band_pass_low, band_pass_high, low_pass, fs, order)
    emg_filename = os.path.join(trial_folder,'emg_filtered.csv')
    emg_data_filtered.to_csv(emg_filename)
    
    
    for col in emg_data_filtered.columns:
        max_rolling_average = np.max(pd.Series(emg_data_filtered[col]).rolling(200, min_periods=1).mean())
        max_emg_list.append(max_rolling_average)
    

print(max_emg_list)
    
    