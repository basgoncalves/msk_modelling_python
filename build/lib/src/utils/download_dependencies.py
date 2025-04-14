import os
import sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import shutil
import subprocess
import zipfile
import urllib.request
import pkg_resources
import subprocess
from src import add_to_system_path

def download_ceinms():
    url = "https://github.com/CEINMS/CEINMS/archive/refs/heads/master.zip"
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "..", "virtual_environment", "Lib", "site-packages", "ceinms.zip")
    ceinms_folder_path = os.path.join(current_dir, "..", "virtual_environment", "Lib", "site-packages", "CEINMS-master")
    
    if os.path.exists(ceinms_folder_path):
        print("CEINMS master folder already exists.")
        return
    
    try:
        urllib.request.urlretrieve(url, file_path)
    except Exception as e:
        print(f"Error downloading CEINMS: {str(e)}")
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(current_dir, "..", "virtual_environment", "Lib", "site-packages"))
    except Exception as e:
        print(f"Error unzipping CEINMS: {str(e)}")
    
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting CEINMS .zip file: {str(e)}")
    
    print("CEINMS downloaded successfully.")
    print(f"Saved at: {file_path}")

def download_opensim(opensim_path = "C:/OpenSim 4.4"):

    if not os.path.exists(opensim_path):
        try:
            print("OpenSim version 4.4 not found. Downloading...")
            url = "https://github.com/opensim-org/opensim-gui/archive/refs/tags/4.4.tar.gz"  # Replace with the actual download URL
            zip_path = opensim_path + ".tar.gz"
            urllib.request.urlretrieve(url, zip_path)
            print("OpenSim version 4.4 downloaded successfully.")

            shutil.unpack_archive(zip_path, opensim_path)
            
            os.remove(zip_path)
            print("OpenSim installed successfully.")

        except Exception as e:
            print("An error occurred:", str(e))
    else:
        print("OpenSim version 4.4 already exists.")

def dowload_trcdata():
    url = 'https://github.com/hsorby/trc-data-reader.git'

def create_requirements():
    # Get the list of installed packages
    installed_packages = [pkg.key for pkg in pkg_resources.working_set]

    # Get the list of Python files in the current folder
    current_folder = os.path.dirname(os.path.abspath(__file__))
    python_files = [file for file in os.listdir(current_folder) if file.endswith('.py')]

    # Extract the imported modules from each Python file
    imported_modules = set()
    for file in python_files:
        with open(os.path.join(current_folder, file), 'r') as f:  
            lines = f.readlines()
            for line in lines:
                if line.startswith('import') or line.startswith('from'):
                    module = line.split()[1]
                    if module == 'cv2':
                        module = 'opencv-python'
                    elif module == 'PIL':
                        module = 'Pillow'
                    elif module == 'trc':
                        module = 'trc-data-reader'                   
                    imported_modules.add(module)

    # Get the list of standard library modules
    standard_library_modules = sys.modules.keys()

    # Filter out the installed packages from the imported modules
    required_modules = [module for module in imported_modules if module not in installed_packages]
    
    # Remove standard library modules
    required_modules = [module for module in required_modules if module not in standard_library_modules]
    
    # If modules contain '.', remove the '.' and everything after it
    required_modules = [module.split('.')[0] for module in required_modules]
    
    # Remove duplicates
    required_modules = list(set(required_modules))
    
    # Write the required modules to requirements.txt
    requirements_filename = os.path.join(current_folder, 'requirements.txt')
    with open(requirements_filename, 'w') as f:
        for module in required_modules:
            f.write(f"{module}\n")
    
    print('requirements.txt created successfully.')
    print(f"Saved at: {requirements_filename}")
    return requirements_filename

def install_requirements():
    requirements_filename = create_requirements()
    current_folder = os.path.dirname(os.path.abspath(__file__))
    print(current_folder)

    try:
        subprocess.check_call(['pip', 'install', '-r', requirements_filename])
        print('Requirements installed successfully.')
    except subprocess.CalledProcessError as e:
        print('Failed to install requirements.')
        print(e)

def create_virtual_environment(env_path=''):
    
    if not env_path:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'virtual_environment')
    
    try:
        subprocess.check_call(['python', '-m', 'venv', env_path])
        print(f"Virtual environment created successfully at {env_path}.")
    except subprocess.CalledProcessError as e:
        print('Failed to create virtual environment.')
        print(e)
        
    return env_path

def activate_virtual_environment(env_path):
    scripts_path = os.path.join(env_path, 'Scripts')
    os.chdir(scripts_path)
    
    activate_script = os.path.join(scripts_path, 'activate')
    
    if os.path.exists(activate_script):
        try:
            subprocess.check_call(activate_script, shell=True)
            print('Virtual environment activated.')
        except subprocess.CalledProcessError as e:
            print('Failed to activate virtual environment.')
            print(e)
    else:
        print('Virtual environment activation script not found.')

if __name__ == '__main__':
    # download_ceinms()
    # download_opensim()
    create_requirements()
    # add_to_system_path.run()
    # env_path = create_virtual_environment()
    # activate_virtual_environment(env_path)
    print('done.')
