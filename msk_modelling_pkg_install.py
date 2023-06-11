# create virtual environment and add the needed packages
# python -m venv .\virtual_env
# cd .\Python_environments\virtual_env\Scripts\  
# .\activate
# data_science_installpkg.py

import subprocess
import sys
import pkg_resources
import os

def install_opensim(VERSION=4.3):

    osimIntallDirectory= r'C:\OpenSim VERSION\sdk\Python'.replace("VERSION", str(VERSION))
    os.chdir(osimIntallDirectory)
    subprocess.run(['python', '.\setup_win_python38.py'], check=True) # Run setup script
    output = subprocess.run(['python', '-m', 'pip', 'install', '.'], check=True) # Install the package

    print(output.stderr())

    sys.executable
    # run in terminal 
    # cd 'C:\OpenSim 4.3\sdk\Python\
    # python .\setup_win_python38.py
    # python -m pip install .

Packages = ['numpy','c3d','opensim','pyc3dserver','requests','bs4','pandas','selenium','webdriver-manager','matplotlib','docx',
        'autopep8','tk','jupyter','scipy', 'xmltodict','tkfilebrowser','customtkinter','screeninfo']

installed_packages = pkg_resources.working_set
installed_packages_list = sorted(['%s==%s' % (i.key, i.version) for i in installed_packages])


for pkg in Packages:
    if any(pkg in s for s in installed_packages_list):
        # print(pkg + ' already installed')
        msg = 'all good'
    else:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
        except:
            install_opensim(version=4.3)
            
        
#install opensim 

