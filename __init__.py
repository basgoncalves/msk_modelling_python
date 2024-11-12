

#%% load all the packages needed
import sys
import os
import time

# import src modules first
from msk_modelling_python import src
from msk_modelling_python.src import osim
from msk_modelling_python.src.classes import *
from msk_modelling_python.src.bops import bops 
from msk_modelling_python.src.bops import ceinms
from msk_modelling_python.src.utils import general_utils as ut
import msk_modelling_python.src.plot as plot

# import ui modules (not finished yet...)
from msk_modelling_python import ui


# settings = bops.get_bops_settings()
__version__ = '0.1.6'
__testing__ = True

if __testing__:
    print("msk_modelling_python package loaded.")
    print(f"Version: {__version__}")  
    print("Testing mode is on.")
    print("To turn off testing mode, set __testing__ to False.") 
    
    print("Python version: 3.8.10")
    print("For the latest version, visit " + r'GitHub\basgoncalves\msk_modelling_python')
    


#%% Description
#
# This module is a collection of functions that can be used to run
# update the version of a module, log errors, create folders, and load projects.
   

#%% FUNCTIONS
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
                    file.write(f"__version__ = '{updated_version}'\n")
                else:
                    file.write(line)
    except:
        print("Error: Could not update the version")
        return
    
    ut.pop_warning(f'msk_modelling_python udpated \n old version: {current_version} \n version to {updated_version} \n')
    
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
        project_path = bops.select_folder("Select project folder")
    
    print(bops.get_project_settings(project_path))
    
    return project_path

def mir():
    print("My gf is the best ever!!")


#%% RUN
# run the main code of the module
def run(**kwargs):
    '''
    Run the main code of the module. 
    
    Parameters (optional):
        update_version: function to update the version of the module
        example: boolean to run the example
        
        example:
            import msk_modelling_python as msk
            msk.run(example=True)
        
        
    '''
    print("Running main code from msk_modelling_python")
    
    # argument verification. check if the arguments are valid keep them (if additional arguments are added, update the list below)
    valid_args = ['update_version', 'example']
    
    for key in kwargs:
        if key not in valid_args: # check if the argument is valid or delete it
            print(f"Invalid argument: {key}")
            kwargs.pop(key) # delete the argument from the dictionary
    
    if kwargs == {}:
        ut.pop_warning("No valid arguments passed. Please pass the arguments as keyword arguments.")
    
    # arguments handling / implementation of command arguments
    for key in kwargs:
        print(f"Argument: {key} = {kwargs[key]}")
        
        if key == 'example' and kwargs[key] == True:
            print("Running example...")
            gui = ui.run_example()
        
        elif key == 'update_version' and kwargs[key] == True:
                print("Updating version...")
                update_version(3, msk, invert=False)
                print(f"New version: {msk.__version__}") 
        
            
    # implement version update if needed
    

#%% END