import msk_modelling_pkg_install
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import scipy
from opensim import C3DFileAdapter
import opensim as osim
import numpy as np
import os
import bops


# current_path = os.getcwd()
# Tk().withdraw()                                     
# csv_filedir = askopenfilename(initialdir=current_path)    

maindir = r'Z:\EMG_realtime_biofeedback\InputData\s001\2023-01-12'

c3dfilepath = os.path.join(maindir,r'sprint02.c3d')
bops.c3d_to_sto(c3dfilepath)

emg_labels = ['Voltage.EMG01_r_gastro', 'Voltage.EMG02_r_soleus',
 'Voltage.EMG03_r_rect_fem', 'Voltage.EMG04_r_tfl',
 'Voltage.EMG05_r_semimemb', 'Voltage.EMG06_l_gastro',
 'Voltage.EMG07_l_soleus', 'Voltage.EMG08_l_rect_fem', 'Voltage.EMG09_l_tfl',
 'Voltage.EMG10_l_semimemb']

bops.c3d_emg_export(c3dfilepath,emg_labels)