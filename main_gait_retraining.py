import msk_modelling_pkg_install
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import scipy
from opensim import C3DFileAdapter
import opensim as osim
import numpy as np
import os
import bops
import shutil

# define paths
dir_path = os.path.dirname(os.path.realpath(__file__))
session_folder =  os.path.join(dir_path,'ExampleData\s001\session1')
c3dfilepath = os.path.join(session_folder,'sprint_1.c3d')

# convert c3d to .trc (markers) and .mot (forces)
bops.c3d_osim_export(c3dfilepath)

# define EMG label names
emg_labels = ['Voltage.EMG01_r_gastro', 'Voltage.EMG02_r_soleus',
 'Voltage.EMG03_r_rect_fem', 'Voltage.EMG04_r_tfl',
 'Voltage.EMG05_r_semimemb', 'Voltage.EMG06_l_gastro',
 'Voltage.EMG07_l_soleus', 'Voltage.EMG08_l_rect_fem', 'Voltage.EMG09_l_tfl',
 'Voltage.EMG10_l_semimemb']

# save EMG analog data as csv file
bops.c3d_emg_export(c3dfilepath,emg_labels)

bops.add_each_c3d_to_own_folder(session_folder)