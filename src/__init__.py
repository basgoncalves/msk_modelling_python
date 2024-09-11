import subprocess
import importlib
import os
import time
import unittest
import sys

from . import msk_modelling_pkg_install

import pandas as pd
import ctypes
import numpy as np
import math
import shutil
from xml.etree import ElementTree as ET
import pyc3dserver as c3d
import scipy
import scipy.signal as sig
from scipy.spatial.transform import Rotation
import scipy.integrate as integrate
from pathlib import Path
import warnings
import json
import screeninfo as si
from tqdm import tqdm
import matplotlib.pyplot as plt

import tkinter as tk
from tkinter import messagebox
import tkinter.messagebox as mbox
from tkinter import filedialog
import tkfilebrowser
import customtkinter as ctk

from PIL import ImageTk, Image

from sklearn.preprocessing import MinMaxScaler

try:
    from trc import TRCData
except:
    print('could not import trc package')
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
