import msk_modelling_python as msk
import subprocess
import os

CURRENT_SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
SIMULATION_PATH = os.path.join(os.path.dirname(CURRENT_SCRIPT_PATH), 'Simulations')

def run_calibration(xml_setup_file):    
    
    if not os.path.exists(xml_setup_file):
        print(f"File {xml_setup_file} does not exist.")
        return None
    
    try:        
        ceinms_install_path = os.path.join(msk.__path__[0], 'src', 'ceinms2', 'src')
        command = " ".join([ceinms_install_path + "\CEINMScalibrate.exe -S", xml_setup_file])
        print(command)
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        result = None
        return result
    except Exception as e:
        print(e)
        return None
    
def run_execution(xml_setup_file):
    
    if not os.path.exists(xml_setup_file):
        print(f"File {xml_setup_file} does not exist.")
        return None
    
    try:        
        ceinms_install_path = os.path.join(msk.__path__[0], 'src', 'ceinms2', 'src')
        command = " ".join([ceinms_install_path + "\CEINMS.exe -S", xml_setup_file])
        print(command)
        # result = subprocess.run(command, capture_output=True, text=True, check=True)
        result = None
        return result
    except Exception as e:
        print(e)
        return None
    

if __name__ == '__main__':
    
    SUBJECT = 'TD006'
    TRIAL = 'normal2_l1'
    
    calibration_setup_file = os.path.join(SIMULATION_PATH, SUBJECT, TRIAL, 'ceinms', 'calibrationSetup.xml')
    execution_setup_file = os.path.join(SIMULATION_PATH, SUBJECT, TRIAL, 'ceinms', 'executionSetup.xml')
    if True: run_calibration(calibration_setup_file)
    
    if False: run_execution(execution_setup_file)
    
    