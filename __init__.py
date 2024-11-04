

__version__ = '0.1.4'
__testing__ = True

if __testing__:
    print("msk_modelling_python package loaded.")
    print(f"Version: {__version__}")  
    print("Testing mode is on.")
    print("To turn off testing mode, set __testing__ to False.") 
    
    print("Python version: 3.8.10")
    print("For the latest version, visit " + r'GitHub\basgoncalves\msk_modelling_python')
    

#%% load all the packages needed
import sys
import os
from . import src
from .src.classes import *
from .src.bops import bops as bp
from .src.bops import ceinms_setup as cs
from .src.utils import general_utils as ut
from . import ui




#%% ###########################################################################
#                        Description:                                         # 
###############################################################################
def update_version(level=3, module=__file__, invert=False):
    # Get the current version of the module and the path to the module
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
    new_version = current_version    
    version_parts = list(map(int, new_version.split('.')))
    if invert:
        version_parts[level - 1] -= 1
    else:
        version_parts[level - 1] += 1

    # Reset the parts of the version that come after the incremented part
    for i in range(level, len(version_parts)):
        version_parts[i] = 0

    # Join the version parts back into a string
    new_version = '.'.join(map(str, version_parts))
    
    # Read the current module file
    try:
        with open(module_path, 'r') as file:
            lines = file.readlines()
    except:
        print("Error: Could not open the file")
        print(module_path)
        return
    
    # Update the version in the file    
    try:
        with open(module_path, 'w') as file:
            for line in lines:
                if line.startswith('__version__'):
                    file.write(f"__version__ = '{new_version}'\n")
                else:
                    file.write(line)
    except:
        print("Error: Could not update the version")
        return
    
    print(f'Updated version to {new_version}')


def log_error(error_message, error_log_path=''):
    if not error_log_path:
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        error_log_path = os.path.join(current_file_path,"error_log.txt")
    
    try:
        with open(error_log_path, 'a') as file:
            file.write(error_message + '\n')
    except:
        print("Error: Could not log the error")
        return
            
def create_folder(folder_path): 
    ut.create_folder(folder_path)

def load_project(project_path=''):
    if not project_path:
        project_path = bp.select_folder("Select project folder")
    
    print(bp.get_project_settings(project_path))
    
    return project_path

def mir():
    print("My gf is the best ever!!")



#%% END