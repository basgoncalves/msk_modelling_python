import os
import bops
import pandas as pd

data_dir = r'C:\Git\Uni_teaching\BD2II - Biomechanical Motion Analysis in Practice (2023S)\lab3-EMG'

bops.add_each_c3d_to_own_folder(data_dir)

trial_list = [f.name for f in os.scandir(data_dir) if f.is_dir()]
trial_list = [s for s in trial_list if 'static' not in s]

emg_labels = ['Voltage.EMG01_r_gastro', 'Voltage.EMG02_r_soleus',
 'Voltage.EMG03_r_rect_fem', 'Voltage.EMG04_r_tfl',
 'Voltage.EMG05_r_semimemb', 'Voltage.EMG06_l_gastro',
 'Voltage.EMG07_l_soleus', 'Voltage.EMG08_l_rect_fem', 'Voltage.EMG09_l_tfl',
 'Voltage.EMG10_l_semimemb']

# set filter parameters
fs = 1000.0  # sample rate, Hz
lowcut = 10.0  # lower cut-off frequency, Hz
lowcut_2 = 6.0  # lower cut-off frequency, Hz
highcut = 50.0  # upper cut-off frequency, Hz
order = 4  # filter order

for trial in trial_list:
    # file directories
    trial_folder = os.path.join(data_dir, trial)
    c3dpath = os.path.join(trial_folder, 'c3dfile.c3d')
    emgpath = os.path.join(trial_folder, 'emg.csv')
    bops.c3d_osim_export(c3dpath)
    bops.c3d_emg_export(c3dpath,emg_labels)
    
    emg_data = pd.read_csv(emgpath)
    emg_data_filtered = bops.butter_bandpass(emg_data, lowcut, highcut, fs, order)
    emg_data_filtered = bops.butter_lowpass(emg_data, lowcut_2, fs, order)
    emg_filename = os.path.join(trial_folder,'emg_filtered.csv')
    emg_data_filtered.to_csv(emg_filename)
    
    