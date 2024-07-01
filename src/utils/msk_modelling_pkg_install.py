# create virtual environment and add the needed packages
# python -m venv .\virtual_env
# cd .\Python_environments\virtual_env\Scripts\  
# .\activate
# data_science_installpkg.py
import subprocess
import sys
import pkg_resources
import os
import importlib

osimVersion = '4.3'
installed_packages = pkg_resources.working_set
installed_packages_list = sorted(['%s==%s' % (i.key, i.version) for i in installed_packages])

def install_pipreqs():
    if not any('pipreqs' in s for s in installed_packages_list):
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pipreqs'])    

def install_opensim(VERSION=4.3):

    osimIntallDirectory= r'C:\OpenSim VERSION\sdk\Python'.replace("VERSION", str(VERSION))
    os.chdir(osimIntallDirectory)

    try:
        if VERSION == 4.3:
            subprocess.run(['python', '.\setup_win_python38.py'], check=True) # Run setup script
        elif VERSION == 3.3:
            subprocess.run(['python', '.\setup.py install'], check=True)
        
        output = subprocess.run(['python', '-m', 'pip', 'install', '.'], check=True) # Install the package

        print(output.stderr())
    except subprocess.CalledProcessError as e:
        print(e)
        print('Error: Could not install OpenSim Python API')

    sys.executable
    # run in terminal 
    # cd 'C:\OpenSim 4.3\sdk\Python\
    # python .\setup_win_python38.py
    # python -m pip install .

def check_python_version(OpensimVersion):
    
    if OpensimVersion in ['4.1', '4.2']:
        if sys.version_info.major != 2 or sys.version_info.minor != 7:
            print("Error: Python version should be 2.7 for OpensimVersion 4.1 or 4.2.")
    
    elif OpensimVersion == '4.3' or OpensimVersion >= '4.3':
        if sys.version_info.major != 3 or sys.version_info.minor != 8:
            print("Error: Python version should be 3.8 for OpensimVersion 4.3 or above.")
    
    elif OpensimVersion == '4.2':
        if sys.version_info.major != 3 or sys.version_info.minor != 7:
            print("Error: Python version should be 3.7 for OpensimVersion 4.2.")
            
    elif  OpensimVersion in ['3.2', '3.3']:
        if sys.version_info.major != 2 or sys.version_info.minor != 7:
            print("Error: Python version should be 2.7 for OpensimVersion 3.2 or 3.3.")            
    
    else:
        print("Invalid OpensimVersion.")
        print('Check opensim-python version compatability in: ')
        print('https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python')

install_pipreqs()

check_python_version(osimVersion)

Packages = ['autopep8','bs4','c3d','docx','jupyter','numpy','opensim','pyc3dserver','requests',
            'pandas','selenium','webdriver-manager','matplotlib',
            'scipy','tk','tkfilebrowser','customtkinter','xmltodict','screeninfo','spm1d','tqdm']

for pkg in Packages:
    if any(pkg in s for s in installed_packages_list):
        # print(pkg + ' already installed')
        msg = 'all good'
    else:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
        except:
            install_opensim(3.3)

if __name__ == '__main__':
    opensimVersion = input('What is your current opensim version: ')
    print(opensimVersion)
    
# END