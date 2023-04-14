# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021): 
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

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
 
def select_folder(prompt='Please select your folder', staring_path=''):
    if not staring_path: # if empty        
        staring_path = os.getcwd()
        
    Tk().withdraw()                                     
    selected_folder = filedialog.askdirectory(initialdir=staring_path,title=prompt)
    return selected_folder

def select_folder_multiple (prompt='Please select multiple folders', staring_path=''):
    if not staring_path: # if empty        
        staring_path = os.getcwd()
        
    Tk().withdraw()                                     
    folder_list = tkfilebrowser.askopendirnames(initialdir=staring_path,title=prompt)
    return folder_list

def dir_bops():
    return os.path.dirname(os.path.realpath(__file__)) 

def dir_simulations():
    return os.path.join(get_project_folder(),'simulations')

def get_subject_folders():
    return [f.path for f in os.scandir(dir_simulations()) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]

def get_trial_list(session_path=''):
    
    if not session_path:
        session_path = select_folder('Select session folder',dir_simulations())
        
    trial_list = [f.name for f in os.scandir(session_path) if f.is_dir()]
    trial_list = [s for s in trial_list if 'static' not in s]
    return trial_list

def get_bops_settings():
    bops_dir = os.path.dirname(os.path.realpath(__file__)) 
    jsonfile = os.path.join(dir_bops(),'bops_settings.json')
    with open(jsonfile, 'r') as f:
        bops_settings = json.load(f)
    
    return bops_settings
    
def get_project_folder(): 
    
    bops_settings = get_bops_settings()
    project_folder = bops_settings['current_project_folder']
    project_json = os.path.join(project_folder,'settings.json')
    
    if not os.path.isdir(project_folder) or not os.path.isfile(project_json):   # if project folder or project json do not exist, select new project
        project_folder = select_folder('Please select project directory')
        bops_settings['current_project_folder'] = project_folder
        
        jsonpath = Path(dir_bops()) / ("bops_settings.json")
        jsonpath.write_text(json.dumps(bops_settings))
    
    if not os.path.isfile(project_json):                                         # if json does not exist, create one
        create_project_settings(project_folder)
        
    return project_folder

def select_new_project_folder(): 
    
    bops_settings = get_bops_settings()
    project_folder = select_folder('Please select project directory')
    project_json = os.path.join(project_folder,'settings.json')
    bops_settings['current_project_folder'] = project_folder
        
    jsonpath = Path(dir_bops()) / ("bops_settings.json")
    jsonpath.write_text(json.dumps(bops_settings))
    
    if not os.path.isfile(project_json):                                         # if json does not exist, create one
        create_project_settings(project_folder)
        
    return project_folder

def create_project_settings(project_folder=get_project_folder()):      
    project_settings = dict()
    
    project_settings['emg_filter'] = dict()
    project_settings['emg_filter']['band_pass'] = [40,450]
    project_settings['emg_filter']['low_pass'] = [6]
    project_settings['emg_filter']['order'] = [4]
    
    project_settings['emg_labels'] = ['all']
    project_settings['simulations'] = os.path.join(project_folder,'simulations')
    
    
        
    jsonpath = Path(project_folder) / ("settings.json")
    print(jsonpath)
    jsonpath.write_text(json.dumps(project_settings))

def get_project_settings():
    jsonfile = os.path.join(get_project_folder(),'settings.json')
    with open(jsonfile, 'r') as f:
        settings = json.load(f)
    
    return settings
    
def get_c3d_data (c3dfilepath):   
    
    c3d_dict = dict()
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dfilepath)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']

    c3d_dict['analog_rate'] = c3d.get_analog_fps(itf)
    c3d_dict['video_rate'] = c3d.get_video_fps(itf)
    
    
    return c3d_dict

def get_analog_data(c3dfilepath):
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dfilepath)
    analog_dict = c3d.get_dict_analogs(itf)
    analog_df = pd.DataFrame()
    for iLab in analog_dict['LABELS']:
        iData = analog_dict['DATA'][iLab] 
        analog_df[iLab] = iData.tolist()
            
    return analog_df

def c3d_osim_export(c3dfilepath):
    maindir = os.path.dirname(c3dfilepath)
    
    # import c3d file data to a table
    adapter = osim.C3DFileAdapter()
    tables = adapter.read(c3dfilepath)

    # save marker .mot
    markers = adapter.getMarkersTable(tables)
    markersFlat = markers.flatten()
    markersFilename = os.path.join(maindir,'markers.trc')
    stoAdapter = osim.STOFileAdapter()
    stoAdapter.write(markersFlat, markersFilename)
    
    # save grf .sto
    forces = adapter.getForcesTable(tables)
    forcesFlat = forces.flatten()
    forcesFilename = os.path.join(maindir,'grf.mot')
    stoAdapter = osim.STOFileAdapter()
    stoAdapter.write(forcesFlat, forcesFilename)
    
    # save emg .mot
    analog_df = get_analog_data(c3dfilepath)
    emgFilename = os.path.join(maindir,'emg.mot')
    stoAdapter = osim.STOFileAdapter()
    stoAdapter.write(analog_df, emgFilename)  

def export_c3d_multiple(session_path='',replace=0):
    
    if not session_path:
        session_path = select_folder('Select session folder',dir_simulations())
        
    if not get_trial_list(session_path):        
        add_each_c3d_to_own_folder(session_path)
    
    trial_list = get_trial_list(session_path)
    print(trial_list)
    
    for trial in trial_list:
        trial_folder = os.path.join(session_path, trial)
        c3dpath = os.path.join(trial_folder, 'c3dfile.c3d')
        emgpath = os.path.join(trial_folder, 'emg.csv')
        print(c3dpath)
        if not os.path.isfile(c3dpath):
            try:
                c3d_osim_export(c3dpath)
            except:
                print('could not convert ' + c3dpath + ' to markers and grf') 
        
        # if not os.path.isfile(emgpath):
        #     try: 
        #         c3d_emg_export(c3dpath,emg_labels)
        #     except:
        #         print('could not convert ' + c3dpath + ' to emg.csv') 
     
def c3d_emg_export(c3dfilepath,emg_labels):   
    
    itf = c3d.c3dserver(msg=False)   # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    c3d.open_c3d(itf, c3dfilepath)   # Open a C3D file
    
    # For the information of all analogs(excluding or including forces/moments)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']
    
    # if no emg_labels are given export all analog labels
    if emg_labels == 'all':
        emg_labels = analog_labels
    
    # Initialize the final dataframe
    analog_df = pd.DataFrame()
    
    # Store each of the vectors in dict_analogs as a columns in the final dataframe
    for iLab in analog_labels:
        if iLab in emg_labels:
            iData = dict_analogs['DATA'][iLab] 
            analog_df[iLab] = iData.tolist()
    maindir = os.path.dirname(c3dfilepath)
    
    # Sava data in parent directory
    emg_filename = os.path.join(maindir,'emg.csv')
    analog_df.to_csv(emg_filename, index=False)

def selectOsimVersion():
    osim_folders = [folder for folder in os.listdir('C:/') if 'OpenSim' in folder]
    installed_versions = [folder.replace('OpenSim ', '') for folder in osim_folders]
    msg = 'These OpenSim versions are currently installed in "C:/", please select one'
    indx = inputList(msg, installed_versions)
    osim_version_bops = float(installed_versions[indx])
    
    bops = {
        'osimVersion': osim_version_bops,
        'directories': {
            'setupbopsXML': 'path/to/setupbops.xml'
        },
        'xmlPref': {
            'indent': '  '
        }
    }
    
    xml_write(bops['directories']['setupbopsXML'], bops, 'bops', bops['xmlPref'])
    
def inputList(prompt, options):
    print(prompt)
    for i, option in enumerate(options):
        print(f"{i+1}: {option}")
    while True:
        try:
            choice = int(input("Enter the number of the option you want: "))
            if choice < 1 or choice > len(options):
                raise ValueError()
            return choice-1
        except ValueError:
            print("Invalid choice. Please enter a number between 1 and ", len(options))
            
def xml_write(file, data, root_name, pref):
    root = ET.Element(root_name)
    dict_to_xml(data, root)
    tree = ET.ElementTree(root)
    tree.write(file, xml_declaration=True, encoding='UTF-8', method="xml", short_empty_elements=False, indent=pref['indent'])
    
def dict_to_xml(data, parent):
    for key, value in data.items():
        if isinstance(value, dict):
            dict_to_xml(value, ET.SubElement(parent, key))
        else:
            ET.SubElement(parent, key).text = str(value)

def add_each_c3d_to_own_folder(session_path):
    
    c3d_files = [file for file in os.listdir(session_path) if file.endswith(".c3d")]
    for file in c3d_files:
        fname = file.replace('.c3d', '')
        src = os.path.join(session_path, file)
        dst_folder = os.path.join(session_path, fname)
        
        # create a new folder 
        try: os.mkdir(dst_folder)
        except: 'nothing'
        
        # copy file
        dst = os.path.join(dst_folder, 'c3dfile.c3d')
        shutil.copy(src, dst)

def emg_filter(c3dfilepath, band_lowcut=30, band_highcut=400, lowcut=6, order=4):
    # save max emg values
    c3d_dict = get_c3d_data (c3dfilepath)
    fs = c3d_dict['analog_rate']
    if fs < band_highcut * 2:
        band_highcut = fs / 2        
        warnings.warn("High pass frequency was too high. Using 1/2 *  sampling frequnecy instead")
        
    analog_df = get_analog_data(c3dfilepath)
    emg_data_filtered = emg_filter(analog_df, fs, band_lowcut, band_highcut, lowcut, order)
  
    max_emg_list = []
    for col in emg_data_filtered.columns:
            max_rolling_average = np.max(pd.Series(emg_data_filtered[col]).rolling(200, min_periods=1).mean())
            max_emg_list.append(max_rolling_average)
            
    nyq = 0.5 * fs
    normal_cutoff  = lowcut / nyq
    b_low, a_low = sig.butter(order, normal_cutoff, btype='low',analog=False)
    
    low = band_lowcut / nyq
    high = band_highcut / nyq
    b_band, a_band = sig.butter(order, [low, high], btype='band')
    
    for col in df.columns:
        raw_emg_signal = df[col]
        bandpass_signal = sig.filtfilt(b_band, a_band, raw_emg_signal)        
        detrend_signal = sig.detrend(bandpass_signal, type='linear')
        rectified_signal = np.abs(detrend_signal)
        linear_envelope = sig.filtfilt(b_low, a_low, rectified_signal)
        df[col] = linear_envelope
        
    return df

def torsion_tool(): # to complete...
   a=2 
    
def selec_analog_labels (c3dfilepath):   
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dfilepath)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']

    print(analog_labels)
    print(type(analog_labels))
        
def run_IK(model_path, trc_file, resultsDir, marker_weights_path):
    # Load the TRC file
    trc = osim.TimeSeriesTableMotion().loadTRC(trc_file)

    # Load the model
    osimModel = osim.Model(model_path)
    state = osimModel.initSystem()

    # Define the time range for the analysis
    initialTime = trc.getStartTime()
    finalTime = trc.getLastTime()

    # Create the inverse kinematics tool
    ikTool = osim.InverseKinematicsTool()
    ikTool.setModel(osimModel)
    ikTool.setStartTime(initialTime)
    ikTool.setEndTime(finalTime)
    ikTool.setMarkerDataFileName(trc_file)
    ikTool.setResultsDir(resultsDir)
    ikTool.set_accuracy(1e-6)
    ikTool.setOutputMotionFileName(os.path.join(resultsDir, "ik.mot"))

    # print setup
    ikTool.printToXML(os.path.join(resultsDir, "ik_setup.xml"))

    # Run inverse kinematics
    print("running ik...")
    ikTool.run()

def run_MA(model_path, ik_mot, grf_xml, resultsDir):
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)
    
    # Load the model
    model = osim.Model(model_path)
    model.initSystem()

    # Load the motion data
    motion = osim.Storage(ik_mot)

    # Create a MuscleAnalysis object
    muscleAnalysis = osim.MuscleAnalysis()
    muscleAnalysis.setModel(model)
    muscleAnalysis.setStartTime(motion.getFirstTime())
    muscleAnalysis.setEndTime(motion.getLastTime())

    # Create the muscle analysis tool
    maTool = osim.AnalyzeTool()
    maTool.setModel(model)
    maTool.setModelFilename(model_path)
    maTool.setLowpassCutoffFrequency(6)
    maTool.setCoordinatesFileName(ik_mot)
    maTool.setName('Muscle analysis')
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setStartTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.getAnalysisSet().cloneAndAppend(muscleAnalysis)
    maTool.setResultsDir(resultsDir)
    maTool.setInitialTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.setExternalLoadsFileName(grf_xml)
    maTool.setSolveForEquilibrium(False)
    maTool.setReplaceForceSet(False)
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setOutputPrecision(8)
    maTool.setMaxDT(1)
    maTool.setMinDT(1e-008)
    maTool.setErrorTolerance(1e-005)
    maTool.removeControllerSetFromModel()
    maTool.print(join(resultsDir, '..', 'ma_setup.xml'))

    # Reload analysis from xml
    maTool = osim.AnalyzeTool(join(resultsDir, '..', 'ma_setup.xml'))

    # Run the muscle analysis calculation
    maTool.run()



# end 