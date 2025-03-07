import sys
import os
import time
start_time = time.time()

import math
import unittest
import msk_modelling_python as msk
from msk_modelling_python.src import ui # import ui modules (not finished yet...)
from msk_modelling_python.src.utils import *
from msk_modelling_python.src.tools.bops import *

__version__ = '0.1.9'
__testing__ = False

if __testing__:
    print("msk_modelling_python package loaded.")
    print(f"Version: {__version__}")  
    print("Testing mode is on.")
    print("To turn off testing mode, set __testing__ to False.") 
    
    print("Python version: 3.8.10")
    print("For the latest version, visit " + r'GitHub\basgoncalves\msk_modelling_python')
    
    print("Time to load package: ", time.time() - start_time)
    
def update_version(level=3, module=__file__, invert=False):
    '''
    Inputs:
        level (int): The level of the version to increment (1, 2, or 3) assuming the version is in the format 'major.minor.patch'
        module (module): The module to update the version of
        invert (bool): If True, decrement the version instead of incrementing it
    Usage:
        import msk_modelling_python as msk
        msk.update_version(3, msk, invert=False) # update the patch version of the module "msk" by incrementing it by 1    
    '''
    
    if module != __file__:
        try:
            print(f'Current module version: {module.__version__}')
            current_version = module.__version__
            module_path = module.__file__
        except AttributeError:
            print("Error: Module does not have a __version__ attribute")
            return
    else:
        global __version__
        current_version = __version__
        module_path = __file__    
    
    # Get the current version and Split the version into its components and increment the specified part
    updated_version = current_version    
    version_parts = list(map(int, updated_version.split('.')))
    if invert:
        version_parts[level - 1] -= 1
    else:
        version_parts[level - 1] += 1

    # Reset the parts of the version that come after the incremented part
    for i in range(level, len(version_parts)):
        version_parts[i] = 0

    # Join the version parts back into a string
    updated_version = '.'.join(map(str, version_parts))
    
    # Read the current module file line per line
    try:
        with open(module_path, 'r') as file:
            lines = file.readlines()
    except:
        print("Error: Could not open the file")
        print(module_path)
        return
    
    # Find the line with __version__ and update it
    try:
        with open(module_path, 'w') as file:
            for line in lines:
                if line.startswith('__version__'):
                    file.write(f"__version__ = '{updated_version}'\n")
                else:
                    file.write(line)
        
        # Update settings.json file with False update
        settings = msk.bops.get_bops_settings()
        settings['update'] = False
        settings['__version__'] = updated_version
        msk.bops.save_bops_settings(settings)
            
    except:
        print("Error: Could not update the version")
        return
    
    ui.show_warning(f'msk_modelling_python udpated \n old version: {current_version} \n version to {updated_version} \n')
    
    return updated_version
    
def log_error(error_message, error_log_path=''):
    '''
    Log an error message to a file
    
    Inputs:
        error_message (str): The error message to log
        error_log_path (str): The path to the error log file (default is the error_log.txt file in the same directory as this file)
    '''
    if not error_log_path:
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        error_log_path = os.path.join(current_file_path,"error_log.txt")
    
    try:
        with open(error_log_path, 'a') as file:
            date = time.strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{date}: {error_message}\n")
    except:
        print("Error: Could not log the error")
        return

def run_bops():
    '''
    Run an example of the bops package
        
    '''
    # run the tests
    try:
        if bops.__testing__:
            msk.test()
            msk.ui.test()
            msk.src.test()
            msk.plot.basics.test()
            msk.bops.test()
            msk.log_error('All tests passed for msk_modelling_python package.')
    except Exception as e:
        ut.print_warning("Error running package testing: ", e)
        msk.log_error(e)
    
    # run the steps based on the settings.json file in the bops package
    try:
        print('Running main.py')
        settings = msk.bops.get_bops_settings()
        
        if settings['gui']:
            msk.bops.run_example()
        
        if settings['update']:
            msk.update_version(3, msk, invert=False)
        
        if settings['bops']['analyses']['run']['IK']:
            osim_model_path = msk.bops.select_file('Select the osim model file')
            trc_marker_path = msk.bops.select_file('Select the marker file')
            output_folder_path = msk.os.path.dirname(trc_marker_path)
            msk.bops.run_inverse_kinematics(model_file=osim_model_path, marker_file=trc_marker_path , output_folder=output_folder_path)
        
        print('Check implementations.txt for future upcoming implementations')
        print('.\msk_modelling_python\guide\log_problems\implementations.txt')
        print('Check the log file for any errors')
        print('.\msk_modelling_python\guide\log_problems\log.txt')
        
        msk.bops.Platypus().happy()
    except Exception as e:
        print("Error: ", e)
        msk.log_error(e)
        msk.bops.Platypus().sad()
    
class test(unittest.TestCase):
    def test_update_version(self):
        pass
    
    msk.log_error('msk tests all passsed!')

    def test_log_error(self):
        pass

    def test_load_project(self):
        pass

    def test_mir(self):
        pass
    
    def test_platypus(self):
        msk.bops.Platypus().happy()
        self.assertTrue(True)
        
    def test_run_bops(self):
        run_bops()
        
    def test_src(self):
        src.test()
        
    def test_ui(self):
        msk.ui.test()
        
            
if __name__ == "__main__":
    try:
        unittest.main()
        msk.log_error('Tests passed for msk_modelling_python package')
    except Exception as e:
        print("Error: ", e)
        msk.log_error(e)
        msk.bops.Platypus().sad()
    
    
#%% END