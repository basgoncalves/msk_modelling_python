import os
import shutil
import zipfile
import os
import urllib.request
import pkg_resources

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

def download_opensim():
    opensim_path = "C:/OpenSim 4.4"  # Updated OpenSim path

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
                    imported_modules.add(module)

    # Filter out the installed packages from the imported modules
    required_modules = [module for module in imported_modules if module not in installed_packages]

    # Write the required modules to requirements.txt
    with open('requirements.txt', 'w') as f:
        for module in required_modules:
            f.write(f"{module}\n")
    
    print('requirements.txt created successfully.')


if __name__ == '__main__':
    download_ceinms()
    download_opensim()
    create_requirements()