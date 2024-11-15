#%% basic imports
import os
import sys
import time
import datetime
import ctypes
import shutil
import warnings
import importlib
import subprocess
import pyperclip
import pathlib
import unittest
from pathlib import Path

#%% data strerelization formats
import json
from xml.etree import ElementTree as ET
import pyc3dserver as c3d

#%% Operations
import math
import numpy as np
import pandas as pd
import scipy
import scipy.signal as sig
from scipy.spatial.transform import Rotation
import scipy.integrate as integrate

#%% plotting / UI
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import messagebox
import tkinter.messagebox as mbox
from tkinter import filedialog
import tkfilebrowser
import customtkinter as ctk
import screeninfo as si
from tqdm import tqdm
from PIL import ImageTk, Image

#%% try import opensim
try: 
    from trc import TRCData
except:
    print('Could not load TRDData')

# try import c3d
try:
    import c3d
except:
    print('Could not load c3d')
    class c3d:
        pass

#%% modules withing
from msk_modelling_python.src.bops import bops
from msk_modelling_python.src.bops import stats


#%% Test code when file runs
if __name__ == "__main__":
    
    print("Testing msk_modelling_python")
    print(f"Current version: {bops.__version__}")

    stats.test()
    bops.Platypus().run_tests()
    bops.is_setup_file(r"C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\example_data\walking\trial1\setup_id.xml", print_output=True)
    
    