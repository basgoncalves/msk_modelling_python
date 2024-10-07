import sys
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
import pandas as pd

#%% Description
# This module contains a set o utility functions that can be run from the command line
# The functions are defined as classes so that we can print the names of the functions
# and run from the command line
#
# To modify functions or add new functions, create the function under section"Functions to be turned into Options"
# and add create an Option class for the function
#
# Usage:
# python utils.py <function_name>
# eg python utils.py speed_test


#%% Start
# create a class for each option so that we can print the option names
class Option:
    def __init__(self, func):
        self.func = func

    def run(self):
        self.func()

#%% Functions to be turned into Options
def speed_test():
    import speedtest
    
    print("Running speed test ...")
    
    speed_test = speedtest.Speedtest()

    download_speed = round(speed_test.download()/1e6)
    print("Your Download speed is", download_speed,'Mb') 

    upload_speed = round(speed_test.upload()/1e6)
    print("Your Upload speed is", upload_speed,'Mb')

def get_current_dir():
    print("for .py")
    print("dir_path = os.path.dirname(os.path.realpath(__file__))")
    print("for ipynb")
    print("dir_path = os.getcwd()")

def python_path():
    print(sys.executable)

def print_python_libs():
    print(os.path.join(os.path.dirname(sys.executable),'Lib','site-packages'))

def files_above_100mb():
    
    current_path = os.getcwd()

    # User select the folder of the volume you want to convert folders
    target_path = askdirectory(initialdir=current_path)

    size_bytes = pd.DataFrame(columns=["file", "size"])
    count = -1

    for root, dirs, files in os.walk(target_path):
        for filename in files:
            full_path = os.path.join(root, filename)
            if os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                size_in_mb = round(size / (1024 * 1024), 2)
                if size_in_mb > 100:
                    count += 1
                    # Remove common part of target_path from full_path
                    relative_path = os.path.relpath(full_path, target_path)
                    size_bytes.loc[count] = [relative_path, size_in_mb]

    # Display the resulting DataFrame
    print(size_bytes)

def create_template():
    import os

    def create_folder(directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            else:
                print(f"Folder {directory} already exists.")
                return directory
        except OSError:
            print ('Error: Creating directory. ' +  directory)

    def create_file(path):
        with open(path, 'w') as f:
            pass


    # Define the name of the directory to be created
    base_dir = input("Enter the name of the directory to be created: ")

    if not os.path.exists(os.path.dirname(base_dir)):
        print(f"Error: {base_dir} does not exists")
        exit()
    
    elif base_dir == '.':        
        module_name = input("Enter the name of the module: ")
        base_dir = os.getcwd() + '/' + module_name
        if os.path.exists(base_dir):
            print(f"Error: {base_dir} already exists")
            exit()

        print(f"Creating directory ... \n {base_dir}")

    else:
        print(f"Creating directory ... \n {base_dir}")

    # Create directories
    try:
        create_folder(f'{base_dir}')
        create_folder(f'{base_dir}/tests')
        create_folder(f'{base_dir}/docs')
    except Exception as e:
        print ('Error: Creating directory. ' +  base_dir)
        print(e)
        exit()  


    # Create files
    try:    
        create_file(f'{base_dir}/__init__.py')
        create_file(f'{base_dir}/module.py')
        create_file(f'{base_dir}/utils.py')
        create_file(f'{base_dir}/tests/__init__.py')
        create_file(f'{base_dir}/tests/test_module.py')
        create_file(f'{base_dir}/docs/index.md')
        create_file(f'{base_dir}/docs/module.md')
        create_file(f'{base_dir}/.gitignore')
        create_file(f'{base_dir}/setup.py')
        create_file(f'{base_dir}/README.md')
    except Exception as e:
        print ('Error: Creating file. ' +  base_dir)
        print(e)
        exit()

#%% print names (NOT AN OPTION)
def print_option_names():
    options = [name for name in globals() if isinstance(globals()[name], Option)]
    for option in options:
        print(option)

#%% Errors
def print_error_message():
    print("please select one of the following options:")
    print_option_names()
    print("eg usage: utils.py speet_test")

#%% Main function to select option to run if the script is executed
def select_option_to_run():
    # Check if the number of command line arguments is not equal to 2
    if len(sys.argv) != 2:
        print_error_message()
        sys.exit(1)

    # Get the command line argument
    option = sys.argv[1]

    # Check the value of the command line argument
    if option == "python_path":
        python_path.run()

    elif option == "python_libs":
        print_python_libs.run()

    elif option == "speed_test":
        speed_test.run()

    elif option == "get_current_dir":
        get_current_dir.run()

    elif option == "files_above_100mb":
        files_above_100mb.run()

    else:
        # Invalid command line argument
        print_error_message()
        sys.exit(1)

#%% Convert functions to options
python_path = Option(python_path)
speed_test = Option(speed_test)
get_current_dir = Option(get_current_dir)
files_above_100mb = Option(files_above_100mb)
create_template = Option(create_template)

#%% Run if the script is executed
if __name__ == "__main__":
    select_option_to_run()