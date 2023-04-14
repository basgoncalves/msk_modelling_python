# python version of Batch Opensim Processing Software
import time
start = time.time()
import os
import shutil
import opensim as osim
from xml.etree import ElementTree as ET
import numpy as np
import pyc3dserver as c3d
import pandas as pd
import scipy.signal as sig
import warnings
import json
from tkinter import filedialog
from tkinter import *
import tkfilebrowser
from pathlib import Path



check_project_folder()

end = time.time()
print(end - start)