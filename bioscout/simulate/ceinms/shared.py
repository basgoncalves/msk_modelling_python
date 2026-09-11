"""
bioscout.simulate.ceinms — CEINMS (Calibrated EMG-Informed Neuromusculoskeletal
Modelling) helpers: build the excitation generator, subject/calibration/execution
XMLs and input data, run the CEINMS calibration + execution binaries, and plot
the results. Driven by the project settings (EMG->muscle mapping, muscle groups,
calibration parameters) and the per-trial Analyse objects in
:mod:`bioscout.core.analysis`.
"""
import os
import re
import sys
import shutil
import subprocess
import time
from pathlib import Path
import numpy as np
import xml.etree.ElementTree as ET
import opensim as osim
import matplotlib.pyplot as plt
import pandas as pd
import scipy
import zipfile

# The bare `import utils` below resolves through the bioscout PACKAGE folder
# (bioscout/utils/), so that folder is what goes on sys.path.
#
# This block used to insert this file's own folder and its parent: right when
# the module lived at bioscout/ceinms.py, wrong since it moved to
# bioscout/simulate/ceinms/ -- it put bioscout/simulate on sys.path, which
# makes bioscout/simulate/opensim.py importable as a top-level `opensim`. The
# process that did it never noticed (the real OpenSim was already imported),
# but child processes inherit sys.path, so every ProcessPoolExecutor worker's
# first `import opensim` got bioscout's module instead: "module 'opensim' has
# no attribute 'Model'", and parallel JCF contributions never ran on Windows
# (found by the overnight bench, 2026-09-11). Never put a folder that holds an
# opensim.py on sys.path.
_app_dir = str(Path(__file__).resolve().parents[2])        # .../bioscout (the package)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
for _stale in (str(Path(__file__).parent), str(Path(__file__).parent.parent)):
    while _stale in sys.path:           # left by an older copy of this module
        sys.path.remove(_stale)

import utils
# `openSim` is bioscout.simulate.opensim. The bare name resolves only through
# the sys.modules alias core.analysis._force_load_helper registers -- it used
# to fall through to bioscout/simulate on sys.path, the entry removed above.
try:
    import openSim
except ImportError:
    from bioscout.simulate import opensim as openSim
    sys.modules.setdefault("openSim", openSim)

# `settings` is resolved LIVE from sys.modules at attribute-access time rather
# than bound once at import time. Project() loads the project's settings.py and
# registers it as sys.modules["settings"]; but ceinms.py is imported (via
# utils/__init__) BEFORE Project() runs, so a plain `import settings` here would
# freeze onto whatever stale settings.py happened to be on sys.path first
# (e.g. the repo-root template), and never see the project's mapping. The proxy
# below always forwards to the currently-registered project settings module.
class _LiveSettings:
    def __getattr__(self, name):
        mod = sys.modules.get("settings")
        if mod is None:
            import importlib
            mod = importlib.import_module("settings")
        return getattr(mod, name)


settings = _LiveSettings()

# Version is single-sourced from the package so it always matches bioscout.
try:
    from bioscout import __version__
except Exception:
    __version__ = "1.2.20"




_ABG_SUFFIX = re.compile(r"(?:_a-?\d+_b-?\d+_g-?\d+)+$")


def upWorkingDirectory():
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    os.chdir(parent_dir)
    print(f"Changed working directory to: {parent_dir}")


def check_input_times(setupXML_path=None):
    
    def load_file_from_tag(setupXML, tag_name):
        
        original_dir = os.getcwd()
        base_dir = os.path.dirname(setupXML_path)
        os.chdir(base_dir)
        file_tag = setupXML.find(tag_name)
        if file_tag is not None:
            os.chdir(original_dir)
            return utils.load_any_data_file(os.path.join(base_dir, file_tag.text))
        else:
            raise ValueError(f"Tag '{tag_name}' not found in setup XML.")
         
    def is_contained(df1, time_range):
        
        if df1 is None or not isinstance(df1, pd.DataFrame) or 'time' not in df1.columns:
            return False
        
        df1_start = df1['time'].iloc[0]
        df1_end = df1['time'].iloc[-1]
        if df1_start > time_range[0] or df1_end < time_range[1]:
            return False
        return True
    
    os.chdir(os.path.dirname(setupXML_path))
    setupXML = ET.parse(setupXML_path).getroot()
    inputDataPath = setupXML.find('inputDataFile').text 
    inputData = ET.parse(inputDataPath).getroot()
    
    # create output dict to store results logics
    output = {}
    
    # Get startStopTime from inputData -> CEINMS time range
    input_startStop = inputData.find('startStopTime').text.strip().split()
    ceinms_time_range = (float(input_startStop[0]), float(input_startStop[1]))   
    
    muscleTendonLength = load_file_from_tag(inputData, 'muscleTendonLengthFile')
    output['muscleTendonLength'] = is_contained(muscleTendonLength, ceinms_time_range)
    
    excitations = load_file_from_tag(inputData, 'excitationsFile')
    output['excitations'] = is_contained(excitations, ceinms_time_range)
    
    momentArmFiles = inputData.findall('.//momentArmsFile')
    for momentArmFile in momentArmFiles:
        momentArm_path = os.path.join(os.path.join(os.path.dirname(inputDataPath), momentArmFile.text))
        momentArms = utils.load_any_data_file(momentArm_path)
        dofName = momentArmFile.get('dofName')
        output[dofName] = is_contained(momentArms, ceinms_time_range)
        
    externalTorques = load_file_from_tag(inputData, 'externalTorquesFile')
    output['externalTorques'] = is_contained(externalTorques, ceinms_time_range)
    
    motion = load_file_from_tag(inputData, 'motionFile')
    output['motion'] = is_contained(motion, ceinms_time_range)
    
    return output


def abg_base_name(name):
    """Strip any trailing _a<A>_b<B>_g<G> blocks so the base name never nests.

    executable_loop writes its mutated <outputDirectory> back into the setup
    XML, so before this fix every re-run appended another suffix
    (Execution_a10_b1_g1000_a10_b1_g5000_a10_b1_g1 ...).
    """
    return _ABG_SUFFIX.sub("", name or "Execution") or "Execution"


def abg_from_name(name):
    """(alpha, beta, gamma) from the LAST suffix block; tolerates nested names."""
    hits = re.findall(r"_a(-?\d+)_b(-?\d+)_g(-?\d+)", name)
    if not hits:
        return None
    a, b, g = hits[-1]
    return int(a), int(b), int(g)


