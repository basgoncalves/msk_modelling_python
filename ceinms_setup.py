
# to import bops need to deactivate some packages not intalled (offline mode, consider this when packaging)
import subprocess
import os

class subject_paths:
    def __init__(self, data_folder,sibject_code,trial_name):
        self.main = data_folder
        self.subject = os.path.join(self.main, subject_code)
        self.trial = os.path.join(self.subject, trial_name)
        self.emg = os.path.join(self.subject, trial_name, 'emg.mot')
        # CEINMS paths 
        self.ceinms_run_file = r"C:\Git\msk_modelling_matlab\src\Ceinms\CEINMS_2\CEINMS.exe"
        self.ceinms_exc_generator = os.path.join(self.subject,'ceinms','excitation_generator.xml') # excitation generator
        
        self.ceinms_calibration_setup = os.path.join(self.subject,'ceinms' ,'calibration_setup.xml') # calibration setup
        self.ceinms_exe_setup = os.path.join(self.trial, 'ceinms_exe_setup.xml')
        self.ceinms_exe_cfg = os.path.join(self.trial, 'ceinms_exe_cfg.xml')

def isfile(path: str):
    if not os.path.exists(paths.ceinms_exe_setup):
        print('File not found: {}'.format(paths.ceinms_exe_setup))
        return False
    else:
        return True

def run_calibration(paths: type):
    if isfile(paths.ceinms_calibration_setup):
        command = " ".join([paths.ceinms_run_file + " -S", paths.ceinms_calibration_setup])
        print(command)
        proc = subprocess.run(command, shell=True)

def run_execution(paths: type):
    if isfile(paths.ceinms_exe_setup):
        command = " ".join([paths.ceinms_run_file + " -S", paths.ceinms_exe_setup])
        print(command)
        proc = subprocess.run(command, shell=True)
        



## actual code ##

# define paths
data_folder =r'C:\Git\research_documents\Uvienna\Bachelors_thesis_supervision\2023W\ksenija_jancic_spowi\data\Mocap'
subject_code = '037'
trial_name = 'Run_baselineA1'
paths = subject_paths(data_folder,subject_code,trial_name)

# run CEINMS calibration
calibration_setup = r''

# run_calibration(paths)
run_execution(paths)

# END