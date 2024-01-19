
# to import bops need to deactivate some packages not intalled (offline mode, consider this when packaging)
import subprocess
import os
import shutil
import tkinter as tk
import opensim as osim
from tkinter import filedialog
import os
import bops as bp   
import pandas as pd
import xml.etree.ElementTree as ET
# import pyomeca as pym

class subject_paths:
    def __init__(self, data_folder,subject_code='default',trial_name='trial1'):

        # main paths
        self.main = data_folder
        self.template_ceinms = os.path.join(self.main,'Setups','ceinms')
        self.subject = os.path.join(self.main, subject_code)
        self.trial = os.path.join(self.subject, trial_name)

        # raw data paths
        self.c3d = os.path.join(self.subject, trial_name, 'c3dfile.c3d')
        self.grf = os.path.join(self.subject, trial_name, 'grf.mot')
        self.markers = os.path.join(self.subject, trial_name, 'markers.trc')
        self.emg = os.path.join(self.subject, trial_name, 'EMG_filtered.sto')

        # model paths
        self.model_generic = os.path.join(self.subject, 'generic_model.osim')
        self.model_scaled = os.path.join(self.subject, 'scaled_model.osim')

        # IK paths
        self.ik_output = os.path.join(self.trial, 'IK.mot')
        self.ik_setup = os.path.join(self.trial, 'setup_ik.xml')

        # ID paths
        self.id_output = os.path.join(self.trial, 'inverse_dynamics.sto')
        self.id_setup = os.path.join(self.trial, 'setup_id.xml')

        # MA paths 
        self.ma_output_folder = os.path.join(self.trial, 'muscle_analysis')
        self.ma_setup = os.path.join(self.trial, 'setup_ma.xml')

        # JRA paths
        self.jra_output = os.path.join(self.trial, 'joint_reaction.sto')
        self.jra_setup = os.path.join(self.trial, 'setup_jra.xml')

        # CEINMS paths 
        self.ceinms_src = r"C:\Git\msk_modelling_matlab\src\Ceinms\CEINMS_2"
        
        self.uncalibrated_subject = os.path.join(self.subject,'ceinms_shared','ceinms_uncalibrated_subject.xml') 
        self.calibrated_subject = os.path.join(self.subject,'ceinms_shared','ceinms_calibrated_subject.xml')

        self.ceinms_exc_generator = os.path.join(self.subject,'ceinms_shared','ceinms_excitation_generator.xml') # excitation generator

        self.ceinms_calibration_setup = os.path.join(self.subject,'ceinms_shared' ,'ceinms_calibration_setup.xml') # calibration setup
        
        self.ceinms_trial_xml = os.path.join(self.trial,'ceinms_trial.xml') # trial xml
        self.ceinms_exe_setup = os.path.join(self.trial, 'ceinms_exe_setup.xml')
        self.ceinms_exe_cfg = os.path.join(self.trial, 'ceinms_exe_cfg.xml')
        self.ceinms_results = os.path.join(self.trial, 'ceinms_results')

# Create the GUI window for the application
def create_window(title, geometry='500x500'):
    
    window = tk.Tk()

    # Set the window title
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate the window width and height
    window_width = screen_width // 2
    window_height = screen_height // 2

    # Calculate the x and y coordinates for centering the window
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # Set the window size and position
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    return window

def select_folder():
    root = tk.Tk()
    root.withdraw()

    folder_path = filedialog.askdirectory()
    print("Selected folder:", folder_path)
    return folder_path

def add_button(window, text, command, padx=5, pady=5, x=0, y=0):
    button = tk.Button(window, text=text, command=command)
    button.pack(padx=padx, pady=pady)
    button.place(x=x, y=y)

def print_text():
    text = entry.get()
    print(text)

def isfile(path: str):
    if not os.path.exists(paths.ceinms_exe_setup):
        print('File not found: {}'.format(paths.ceinms_exe_setup))
        return False
    else:
        return True

#%% functions for GUI
def run_calibration():
    print('run_calibration')
    
#%%
if __name__ == '__main__':

    #%% start GUI
    window = create_window("cereated by BG27")

    folder_path = add_button(window, 'select folder', select_folder, padx=5, pady=5)
    add_button(window, 'run_calibration', run_calibration, padx=15, pady=5,x=0, y=25)
    add_button(window, 'Print', print_text, padx=15, pady=5,x=0, y=50)

    entry = tk.Entry(window)
    entry.pack()

    try:
        window.mainloop()
    except KeyboardInterrupt:
        window.destroy()




    exit()
    c3d_file = r"C:\Users\Bas\ucloud\Shared\Data_CEINMS\simulations\TD10\2023_10_18\cmj01.c3d"
    bp.c3d_osim_export(c3d_file)
    bp.c3d_emg_export(c3d_file)



    

# END OF FILE
