import os
import opensim as osim
from pathlib import Path
import xml.etree as ET

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = Path(MODULE_DIR) / 'example_data'
SPRINT_DIR = Path(DATA_DIR) / 'running' / 'Athlete1' / 'session1' / 'sprint_1'

CEINMS_DIR = os.path.join(MODULE_DIR, 'ceinms')

files = {'uncalibrated': 'uncalibratedSubject.xml',
         'calibrated': 'calibratedSubject.xml',
         'cal_cfg': 'calibrationCfg.xml',
         'cal_setup': 'calibrationSetup.xml',}

