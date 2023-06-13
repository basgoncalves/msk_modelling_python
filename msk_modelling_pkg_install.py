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
    else:
        print("Invalid OpensimVersion.")

# Example usage
check_python_version('4.3')


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
            install_opensim(4.3)
            
        

# import all pakages needed
import os
import sys
import subprocess
import unittest
import numpy as np
import pandas as pd
import math
import shutil
from xml.etree import ElementTree as ET
import pyc3dserver as c3d
import scipy
import scipy.signal as sig
from scipy.spatial.transform import Rotation
from pathlib import Path
import warnings
import json
from tkinter import messagebox
import tkinter.messagebox as mbox
from tkinter import filedialog
import tkinter
import tkfilebrowser
import customtkinter as ctk
import screeninfo as si
from tqdm import tqdm
import matplotlib.pyplot as plt
import tkinter as tk
from PIL import ImageTk, Image
try:
    import opensim as osim
except:
    print('=============================================================================================')
    print('could not import opensim')
    print('Check if __init__.py has "." before packages (e.g. "from .simbody" instead of "from simbody")')
    pythonPath = os.path.dirname(sys.executable)
    initPath = os.path.join(pythonPath,'lib\site-packages\opensim\__init__.py')
    print('init path is: ', initPath)    
    print('=============================================================================================')



# END