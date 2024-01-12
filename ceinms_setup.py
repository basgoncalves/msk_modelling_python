
# to import bops need to deactivate some packages not intalled (offline mode, consider this when packaging)
import subprocess
import os
import tkinter as tk
import opensim
from tkinter import filedialog

class subject_paths:
    def __init__(self, data_folder,subject_code='default',trial_name='trial1'):

        # main paths
        self.main = data_folder
        self.subject = os.path.join(self.main, subject_code)
        self.trial = os.path.join(self.subject, trial_name)

        # raw data paths
        self.c3d = os.path.join(self.subject, trial_name, 'c3dfile.c3d')
        self.grf = os.path.join(self.subject, trial_name, 'grf.mot')
        self.markers = os.path.join(self.subject, trial_name, 'markers.trc')
        self.emg = os.path.join(self.subject, trial_name, 'emg.mot')

        # model paths
        self.model_generic = os.path.join(self.subject, 'generic_model.osim')
        self.model_scaled = os.path.join(self.subject, 'scaled_model.osim')

        # IK paths
        self.ik_output = os.path.join(self.trial, 'ik.mot')
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
        
        self.uncalibrated_subject = os.path.join(self.subject,'ceinms','uncalibrated_subject.xml') 
        
        self.ceinms_exc_generator = os.path.join(self.subject,'ceinms','excitation_generator.xml') # excitation generator

        
        self.ceinms_calibration_setup = os.path.join(self.subject,'ceinms' ,'calibration_setup.xml') # calibration setup
        self.ceinms_exe_setup = os.path.join(self.trial, 'ceinms_exe_setup.xml')
        self.ceinms_exe_cfg = os.path.join(self.trial, 'ceinms_exe_cfg.xml')

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

def isfile(path: str):
    if not os.path.exists(paths.ceinms_exe_setup):
        print('File not found: {}'.format(paths.ceinms_exe_setup))
        return False
    else:
        return True

def run_scale(model_file, marker_file, output_model_file):
    # Load model and create a ScaleTool
    model = opensim.Model(model_file)
    scale_tool = opensim.ScaleTool()

    # Set the model for the ScaleTool
    scale_tool.setModel(model)

    # Set the marker data file for the ScaleTool
    scale_tool.setMarkerFileName(marker_file)

    # Set the output model file name
    scale_tool.setOutputModelFileName(output_model_file)

    # Save setup file
    scale_tool.printToXML('setup_scale.xml')

    # Run ScaleTool
    scale_tool.run()




def run_inverse_kinematics(model_file, marker_file, output_motion_file):
    # Load model and create an InverseKinematicsTool
    model = opensim.Model(model_file)
    ik_tool = opensim.InverseKinematicsTool()

    # Set the model for the InverseKinematicsTool
    ik_tool.setModel(model)

    # Set the marker data file for the InverseKinematicsTool
    ik_tool.setMarkerDataFileName(marker_file)

    # Specify output motion file
    ik_tool.setOutputMotionFileName(output_motion_file)

    # Save setup file
    ik_tool.printToXML('setup_ik.xml')

    # Run Inverse Kinematics
    ik_tool.run()

# CEINMS functions
def edit_xml_file(xml_file: str, old_string: str, new_string: str):
    pass

def run_calibration(paths: type):
    if isfile(paths.ceinms_calibration_setup):
        command = " ".join([paths.ceinms_src + "\CEINMScalibrate.exe -S", paths.ceinms_calibration_setup])
        print(command)
        proc = subprocess.run(command, shell=True)

def run_execution(paths: type):
    if isfile(paths.ceinms_exe_setup):
        command = " ".join([paths.ceinms_src + "\CEINMS.exe -S", paths.ceinms_exe_setup])
        print(command)
        proc = subprocess.run(command, shell=True)
        
def run_full_pipeline():
    # define paths
    data_folder =r'C:\Git\research_documents\Uvienna\Bachelors_thesis_supervision\2023W\ksenija_jancic_spowi\data\Mocap'
    subject_code = '037'
    trial_name = 'Run_baselineA1'
    paths = subject_paths(data_folder,subject_code,trial_name)

    # run opensim inverse kinematics
    try:
        run_inverse_kinematics(paths.model_scaled, paths.markers, paths.ik_output)
    except Exception as e:
        print(e)

# # run CEINMS calibration
# run_calibration(paths)
# run_execution(paths)


if __name__ == '__main__':

    window = create_window("cereated by BG27")

    folder_path = add_button(window, 'select folder', select_folder, padx=5, pady=5)
       
    try:
        window.mainloop()
    except KeyboardInterrupt:
        window.destroy()
    
    
    


# END