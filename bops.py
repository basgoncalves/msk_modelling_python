# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021):
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

import sys
import os
import subprocess
src_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'src')
sys.path.append(src_path)
import msk_modelling_pkg_install
# import all pakages needed
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


def select_folder(prompt='Please select your folder', staring_path=''):
    if not staring_path: # if empty
        staring_path = os.getcwd()

    tkinter().withdraw()
    selected_folder = filedialog.askdirectory(initialdir=staring_path,title=prompt)
    return selected_folder

def select_folder_multiple (prompt='Please select multiple folders', staring_path=''):
    if not staring_path: # if empty
        staring_path = os.getcwd()

    tkinter().withdraw()
    folder_list = tkfilebrowser.askopendirnames(initialdir=staring_path,title=prompt)
    return folder_list

def select_subjects():
   subject_names = get_subject_names()

def get_dir_bops():
    return os.path.dirname(os.path.realpath(__file__))

def get_dir_simulations():
    return os.path.join(get_project_folder(),'simulations')

def get_subject_folders(dir_simulations = ''):
    if dir_simulations:
        return [f.path for f in os.scandir(dir_simulations) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]
    else:
        return [f.path for f in os.scandir(get_dir_simulations()) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]

def get_subject_names():
    subject_names = []
    for i_folder in get_subject_folders():
        subject_names.append(os.path.basename(os.path.normpath(i_folder)))
    return subject_names

def get_subjects_selected():
    return list(get_bops_settings()['subjects'].values())

def get_subject_sessions(subject_folder):
    return [f.path for f in os.scandir(subject_folder) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]

def get_trial_list(sessionPath='',full_dir=False):

    if not sessionPath:
        sessionPath = select_folder('Select session folder',get_dir_simulations())

    trial_list = [f.name for f in os.scandir(sessionPath) if f.is_dir()]

    if full_dir:
        trial_list = [sessionPath + '\\' + str(element) for element in trial_list]

    return trial_list

def get_bops_settings():
    bops_dir = os.path.dirname(os.path.realpath(__file__))
    jsonfile = os.path.join(get_dir_bops(),'bops_settings.json')
    with open(jsonfile, 'r') as f:
        bops_settings = json.load(f)

    return bops_settings

def save_bops_settings(settings):
    jsonpath = Path(get_dir_bops()) / ("bops_settings.json")
    jsonpath.write_text(json.dumps(settings,indent=2))

def get_project_folder():

    bops_settings = get_bops_settings()
    project_folder = bops_settings['current_project_folder']
    project_json = os.path.join(project_folder,'settings.json')

    if not os.path.isdir(project_folder) or not os.path.isfile(project_json):   # if project folder or project json do not exist, select new project
        project_folder = select_folder('Please select project directory')
        bops_settings['current_project_folder'] = project_folder

        jsonpath = Path(get_dir_bops()) / ("bops_settings.json")
        jsonpath.write_text(json.dumps(bops_settings))

    if not os.path.isfile(project_json):                                         # if json does not exist, create one
        create_project_settings(project_folder)

    return project_folder

def get_project_settings():
    jsonfile = os.path.join(get_project_folder(),'settings.json')
    with open(jsonfile, 'r') as f:
        settings = json.load(f)

    return settings

def get_trial_dirs(sessionPath, trial_name):

    dirs = dict()
    dirs['c3d'] = os.path.join(sessionPath,trial_name,'c3dfile.c3d')
    dirs['grf'] = os.path.join(sessionPath,trial_name,'grf.mot')
    dirs['emg'] = os.path.join(sessionPath,trial_name,'emg.csv')
    dirs['inverse_kinematics'] = os.path.join(sessionPath,trial_name,'ik.mot')
    dirs['inverse_dynamics'] = os.path.join(sessionPath,trial_name,'inverse_dynamics.sto')
    dirs['static_op_force'] = os.path.join(sessionPath,trial_name,'_StaticOptimization_force.sto')
    dirs['static_op_activation'] = os.path.join(sessionPath,trial_name,'_StaticOptimization_activation.sto')
    dirs['jra'] = os.path.join(sessionPath,trial_name,'_joint reaction analysis_ReactionLoads.sto')

    # if full_dir:
    #     dirs.values() = [sessionPath + str(element) for element in dirs.values()]
    return dirs

def select_new_project_folder():

    bops_settings = get_bops_settings()
    project_folder = select_folder('Please select project directory')
    project_json = os.path.join(project_folder,'settings.json')
    bops_settings['current_project_folder'] = project_folder

    jsonpath = Path(get_dir_bops()) / ("bops_settings.json")
    jsonpath.write_text(json.dumps(bops_settings))

    if not os.path.isfile(project_json):                                         # if json does not exist, create one
        create_project_settings(project_folder)

    return project_folder

def create_project_settings(project_folder=''):

    if not project_folder:
        project_folder = get_project_folder()

    project_settings = dict()

    project_settings['emg_filter'] = dict()
    project_settings['emg_filter']['band_pass'] = [40,450]
    project_settings['emg_filter']['low_pass'] = [6]
    project_settings['emg_filter']['order'] = [4]

    project_settings['emg_labels'] = ['all']
    project_settings['simulations'] = os.path.join(project_folder,'simulations')

    jsonpath = Path(project_folder) / ("settings.json")
    jsonpath.write_text(json.dumps(project_settings))

#########################################################  C3D processing  ############################################################
def import_c3d_data (c3dFilePath):

    c3d_dict = dict()
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)

    c3d_dict['DataRate'] = c3d.get_video_fps(itf)
    c3d_dict['CameraRate'] = c3d.get_video_fps(itf)
    c3d_dict["OrigDataRate"] = c3d.get_video_fps(itf)
    c3d_dict["OrigAnalogRate"] = c3d.get_analog_fps(itf)
    c3d_dict["OrigDataStartFrame"] = 0
    c3d_dict["OrigDataLAstFrame"] = c3d.get_last_frame(itf)

    c3d_dict["NumFrames"] = c3d.get_num_frames(itf)
    c3d_dict["OrigNumFrames"] = c3d.get_num_frames(itf)

    c3d_dict['MarkerNames'] = c3d.get_marker_names(itf)
    c3d_dict['NumMarkers'] = len(c3d_dict['MarkerNames'] )

    c3d_dict['Labels'] = c3d.get_marker_names(itf)

    c3d_dict['Timestamps'] = c3d.get_video_times(itf)

    c3d_data = c3d.get_dict_markers(itf)
    my_dict = c3d_data['DATA']['POS']
    c3d_dict["Data"] = np.empty(shape=(c3d_dict["NumMarkers"], c3d_dict["NumFrames"], 3), dtype=np.float32)
    for i, label in enumerate(my_dict):
        c3d_dict["Data"][i] = my_dict[label]

    return c3d_dict

def get_analog_data(c3dFilePath):
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)
    analog_dict = c3d.get_dict_analogs(itf)
    analog_df = pd.DataFrame()
    for iLab in analog_dict['LABELS']:
        iData = analog_dict['DATA'][iLab]
        analog_df[iLab] = iData.tolist()

    return analog_df

def c3d_osim_export(c3dFilePath):
    maindir = os.path.dirname(c3dFilePath)

    # import c3d file data to a table
    adapter = osim.C3DFileAdapter()
    tables = adapter.read(c3dFilePath)

    # save marker .mot
    try:
        markers = adapter.getMarkersTable(tables)
        markersFlat = markers.flatten()
        markersFilename = os.path.join(maindir,'markers.trc')
        stoAdapter = osim.STOFileAdapter()
        stoAdapter.write(markersFlat, markersFilename)
    except:
        print(c3dFilePath + ' could not export markers.trc')

    # save grf .sto
    try:
        forces = adapter.getForcesTable(tables)
        forcesFlat = forces.flatten()
        forcesFilename = os.path.join(maindir,'grf.mot')
        stoAdapter = osim.STOFileAdapter()
        stoAdapter.write(forcesFlat, forcesFilename)
    except:
        print(c3dFilePath + 'could not export grf.mot')

    # save emg.csv
    try:
       c3d_emg_export(c3dFilePath)
    except:
        print(c3dFilePath + 'could not export emg.mot')

def c3d_osim_export_multiple(sessionPath='',replace=0):

    if not sessionPath:
        sessionPath = select_folder('Select session folder',get_dir_simulations())

    if not get_trial_list(sessionPath):
        add_each_c3d_to_own_folder(sessionPath)

    trial_list = get_trial_list(sessionPath)
    print('c3d convert ' + sessionPath)
    for trial in trial_list:
        trial_folder = os.path.join(sessionPath, trial)
        c3dpath = os.path.join(trial_folder, 'c3dfile.c3d')
        trcpath = os.path.join(trial_folder, 'markers.trc')
        motpath = os.path.join(trial_folder, 'grf.sto')

        if not os.path.isfile(c3dpath) or not os.path.isfile(trcpath) or not os.path.isfile(motpath):
            try:
                c3d_osim_export(c3dpath)
                print(trial + 'c3d exported')
            except:
                print('could not convert ' + trial + ' to markers, grf, or emg')

        # if not os.path.isfile(emgpath):
        #     try:
        #         c3d_emg_export(c3dpath,emg_labels)
        #     except:
        #         print('could not convert ' + c3dpath + ' to emg.csv')

def c3d_emg_export(c3dFilePath,emg_labels='all'):

    itf = c3d.c3dserver(msg=False)   # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    c3d.open_c3d(itf, c3dFilePath)   # Open a C3D file

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
    maindir = os.path.dirname(c3dFilePath)

    # Sava data in parent directory
    emg_filename = os.path.join(maindir,'emg.csv')
    analog_df.to_csv(emg_filename, index=False)

def rotateAroundAxes(data, rotations, modelMarkers):

    if len(rotations) != len(rotations[0]*2) + 1:
        raise ValueError("Correct format is order of axes followed by two marker specifying each axis")

    for a, axis in enumerate(rotations[0]):

        markerName1 = rotations[1+a*2]
        markerName2 = rotations[1 + a*2 + 1]
        marker1 = data["Labels"].index(markerName1)
        marker2 = data["Labels"].index(markerName2)
        axisIdx = ord(axis) - ord('x')
        if (0<=axisIdx<=2) == False:
            raise ValueError("Axes can only be x y or z")

        origAxis = [0,0,0]
        origAxis[axisIdx] = 1
        if modelMarkers is not None:
            origAxis = modelMarkers[markerName1] - modelMarkers[markerName2]
            origAxis /= scipy.linalg.norm(origAxis)
        rotateAxis = data["Data"][marker1] - data["Data"][marker2]
        rotateAxis /= scipy.linalg.norm(rotateAxis, axis=1, keepdims=True)

        for i, rotAxis in enumerate(rotateAxis):
            angle = np.arccos(np.clip(np.dot(origAxis, rotAxis), -1.0, 1.0))
            r = Rotation.from_euler('y', -angle)
            data["Data"][:,i] = r.apply(data["Data"][:,i])


    return data
########################################################################################################################################

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

def add_each_c3d_to_own_folder(sessionPath):

    c3d_files = [file for file in os.listdir(sessionPath) if file.endswith(".c3d")]
    for file in c3d_files:
        fname = file.replace('.c3d', '')
        src = os.path.join(sessionPath, file)
        dst_folder = os.path.join(sessionPath, fname)

        # create a new folder
        try: os.mkdir(dst_folder)
        except: 'nothing'

        # copy file
        dst = os.path.join(dst_folder, 'c3dfile.c3d')
        shutil.copy(src, dst)

def emg_filter(c3dFilePath, band_lowcut=30, band_highcut=400, lowcut=6, order=4):
    # save max emg values
    c3d_dict = import_c3d_data (c3dFilePath)
    fs = c3d_dict['OrigAnalogRate']
    if fs < band_highcut * 2:
        band_highcut = fs / 2
        warnings.warn("High pass frequency was too high. Using 1/2 *  sampling frequnecy instead")

    analog_df = get_analog_data(c3dFilePath)
    max_emg_list = []
    for col in analog_df.columns:
            max_rolling_average = np.max(pd.Series(analog_df[col]).rolling(200, min_periods=1).mean())
            max_emg_list.append(max_rolling_average)

    nyq = 0.5 * fs
    normal_cutoff  = lowcut / nyq
    b_low, a_low = sig.butter(order, normal_cutoff, btype='low',analog=False)

    low = band_lowcut / nyq
    high = band_highcut / nyq
    b_band, a_band = sig.butter(order, [low, high], btype='band')

    for col in analog_df.columns:
        raw_emg_signal = analog_df[col]
        bandpass_signal = sig.filtfilt(b_band, a_band, raw_emg_signal)
        detrend_signal = sig.detrend(bandpass_signal, type='linear')
        rectified_signal = np.abs(detrend_signal)
        linear_envelope = sig.filtfilt(b_low, a_low, rectified_signal)
        analog_df[col] = linear_envelope

    return analog_df

def torsion_tool(): # to complete...
   a=2

def selec_analog_labels (c3dFilePath):
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']

    print(analog_labels)
    print(type(analog_labels))

def read_trc_file(trcFilePath):
    df = pd.DataFrame(trcFilePath)
    return df

def writeTRC(c3dFilePath, trcFilePath):

    print('writing trc file ...')
    c3d_dict = import_c3d_data (c3dFilePath)

    with open(trcFilePath, 'w') as file:
        # from https://github.com/IISCI/c3d_2_trc/blob/master/extractMarkers.py
        # Write header
        file.write("PathFileType\t4\t(X/Y/Z)\toutput.trc\n")
        file.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        file.write("%d\t%d\t%d\t%d\tmm\t%d\t%d\t%d\n" % (c3d_dict["DataRate"], c3d_dict["CameraRate"], c3d_dict["NumFrames"],
                                                        c3d_dict["NumMarkers"], c3d_dict["OrigDataRate"],
                                                        c3d_dict["OrigDataStartFrame"], c3d_dict["OrigNumFrames"]))

        # Write labels
        file.write("Frame#\tTime\t")
        for i, label in enumerate(c3d_dict["Labels"]):
            if i != 0:
                file.write("\t")
            file.write("\t\t%s" % (label))
        file.write("\n")
        file.write("\t")
        for i in range(len(c3d_dict["Labels"]*3)):
            file.write("\t%c%d" % (chr(ord('X')+(i%3)), math.ceil((i+3)/3)))
        file.write("\n")

        # Write data
        for i in range(len(c3d_dict["Data"][0])):
            file.write("%d\t%f" % (i, c3d_dict["Timestamps"][i]))
            for l in range(len(c3d_dict["Data"])):
                file.write("\t%f\t%f\t%f" % tuple(c3d_dict["Data"][l][i]))
            file.write("\n")

        print('trc file saved')


###############################################  OpenSim (to be complete)  ############################################################
def run_IK(osim_modelPath, trc_file, resultsDir, marker_weights_path):

    trc = osim.TimeSeriesTableMotion().loadTRC(trc_file)                # Load the TRC file
    osimModel = osim.Model(osim_modelPath)                              # Load the model
    state = osimModel.initSystem()

    initialTime = trc.getStartTime()                                    # Define the time range for the analysis
    finalTime = trc.getLastTime()

    ikTool = osim.InverseKinematicsTool()                               # Create the inverse kinematics tool
    ikTool.setModel(osimModel)
    ikTool.setStartTime(initialTime)
    ikTool.setEndTime(finalTime)
    ikTool.setMarkerDataFileName(trc_file)
    ikTool.setResultsDir(resultsDir)
    ikTool.set_accuracy(1e-6)
    ikTool.setOutputMotionFileName(os.path.join(resultsDir, "ik.mot"))

    ikTool.printToXML(os.path.join(resultsDir, "ik_setup.xml"))         # print setup

    print("running ik...")                                              # Run inverse kinematics
    ikTool.run()

def run_ID(osim_modelPath, ik_results_file, mot_file, grf_xml, resultsDir):
    # Load the TRC file
    mot = osim.TimeSeriesTableMotion().loadTRC(mot_file)

    # Load the model
    osimModel = osim.Model(osim_modelPath)
    state = osimModel.initSystem()

    # Define the time range for the analysis
    initialTime = mot.getStartTime()
    finalTime = mot.getLastTime()

    # Create the inverse kinematics tool
    idTool = osim.InverseDynamics()
    idTool.setModel(osimModel)
    idTool.setStartTime(initialTime)
    idTool.setEndTime(finalTime)
    idTool.setCoordinatesFileName(ik_results_file)
    idTool.setExternalLoadsFileName(mot_file)
    idTool.setExternalLoads(grf_xml)
    idTool.setPrintResultFiles(resultsDir)
    idTool.setOutputMotionFileName(os.path.join(resultsDir, "inverse_dynamics.sto"))

    # print setup
    idTool.printToXML(os.path.join(resultsDir, "id_setup.xml"))

    # Run inverse kinematics
    print("running ik...")
    idTool.run()

def run_MA(osim_modelPath, ik_mot, grf_xml, resultsDir):
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)

    # Load the model
    model = osim.Model(osim_modelPath)
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
    maTool.setModelFilename(osim_modelPath)
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
    maTool.print(os.path.join(resultsDir, '..', 'ma_setup.xml'))

    # Reload analysis from xml
    maTool = osim.AnalyzeTool(os.path.join(resultsDir, '..', 'ma_setup.xml'))

    # Run the muscle analysis calculation
    maTool.run()

########################################################################################################################################

###############################################  GUI (to be complete)  #################################################################
def  simple_gui():
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('dark-blue')

    screen_size = si.get_monitors()
    print(screen_size)
    root = ctk.CTk()
    root.geometry('500x350')

    frame = ctk.CTkFrame(root)
    frame.pack(pady=5,padx=5,fill='both',expand=True)

    def exit_application():
        msg_box = messagebox.askquestion('Exit Application', 'Are you sure you want to exit the application?',
                                            icon='warning')
        if msg_box == 'yes':
            root.destroy()
        else:
            messagebox.showinfo('Return', 'You will now return to the application screen')


    button1 = ctk.CTkButton(master = root, text='Exit Application', command=exit_application)
    button1.pack(pady=12,padx=10)

    label = ctk.CTkLabel(master=root, text="Write some text", width=120, height=25, corner_radius=8)
    label.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)

    entry = ctk.CTkEntry(master=root, width=120, height=25,corner_radius=10)
    entry.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)

    text = entry.get()
    print(text)

    root.mainloop()

def complex_gui():
    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

    class App(ctk.CTk):
        def __init__(self):
            super().__init__()

            # configure window
            self.title("Select subjects")
            self.geometry(f"{1100}x{580}")

            # configure grid layout (4x4)
            self.grid_columnconfigure(1, weight=1)
            self.grid_columnconfigure((2, 3), weight=0)
            self.grid_rowconfigure((0, 1, 2), weight=1)

            # create sidebar frame with widgets
            self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
            self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
            self.sidebar_frame.grid_rowconfigure(4, weight=1)
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="ctk", font=ctk.CTkFont(size=20, weight="bold"))
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
            self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
            self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
            self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, command=self.sidebar_button_event)
            self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)
            self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
            self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
            self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                        command=self.change_appearance_mode_event)
            self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
            self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
            self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
            self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%"],
                                                                command=self.change_scaling_event)
            self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

            # create main entry and button
            self.entry = ctk.CTkEntry(self, placeholder_text="CTkEntry")
            self.entry.grid(row=3, column=1, columnspan=2, padx=(20, 0), pady=(20, 20), sticky="nsew")

            self.main_button_1 = ctk.CTkButton(master=self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
            self.main_button_1.grid(row=3, column=3, padx=(20, 20), pady=(20, 20), sticky="nsew")

            # create textbox
            self.textbox = ctk.CTkTextbox(self, width=250)
            self.textbox.grid(row=0, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")

            # create tabview
            self.tabview = ctk.CTkTabview(self, width=250)
            self.tabview.grid(row=0, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.tabview.add("CTkTabview")
            self.tabview.add("Tab 2")
            self.tabview.add("Tab 3")
            self.tabview.tab("CTkTabview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs
            self.tabview.tab("Tab 2").grid_columnconfigure(0, weight=1)

            self.optionmenu_1 = ctk.CTkOptionMenu(self.tabview.tab("CTkTabview"), dynamic_resizing=False,
                                                            values=["Value 1", "Value 2", "Value Long Long Long"])
            self.optionmenu_1.grid(row=0, column=0, padx=20, pady=(20, 10))
            self.combobox_1 = ctk.CTkComboBox(self.tabview.tab("CTkTabview"),
                                                        values=["Value 1", "Value 2", "Value Long....."])
            self.combobox_1.grid(row=1, column=0, padx=20, pady=(10, 10))
            self.string_input_button = ctk.CTkButton(self.tabview.tab("CTkTabview"), text="Open CTkInputDialog",
                                                            command=self.open_input_dialog_event)
            self.string_input_button.grid(row=2, column=0, padx=20, pady=(10, 10))
            self.label_tab_2 = ctk.CTkLabel(self.tabview.tab("Tab 2"), text="CTkLabel on Tab 2")
            self.label_tab_2.grid(row=0, column=0, padx=20, pady=20)

            # create radiobutton frame
            self.radiobutton_frame = ctk.CTkFrame(self)
            self.radiobutton_frame.grid(row=0, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
            self.radio_var = tkinter.IntVar(value=0)
            self.label_radio_group = ctk.CTkLabel(master=self.radiobutton_frame, text="CTkRadioButton Group:")
            self.label_radio_group.grid(row=0, column=2, columnspan=1, padx=10, pady=10, sticky="")
            self.radio_button_1 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=0)
            self.radio_button_1.grid(row=1, column=2, pady=10, padx=20, sticky="n")
            self.radio_button_2 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=1)
            self.radio_button_2.grid(row=2, column=2, pady=10, padx=20, sticky="n")
            self.radio_button_3 = ctk.CTkRadioButton(master=self.radiobutton_frame, variable=self.radio_var, value=2)
            self.radio_button_3.grid(row=3, column=2, pady=10, padx=20, sticky="n")

            # create slider and progressbar frame
            self.slider_progressbar_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.slider_progressbar_frame.grid(row=1, column=1, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.slider_progressbar_frame.grid_columnconfigure(0, weight=1)
            self.slider_progressbar_frame.grid_rowconfigure(4, weight=1)
            self.seg_button_1 = ctk.CTkSegmentedButton(self.slider_progressbar_frame)
            self.seg_button_1.grid(row=0, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.progressbar_1 = ctk.CTkProgressBar(self.slider_progressbar_frame)
            self.progressbar_1.grid(row=1, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.progressbar_2 = ctk.CTkProgressBar(self.slider_progressbar_frame)
            self.progressbar_2.grid(row=2, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.slider_1 = ctk.CTkSlider(self.slider_progressbar_frame, from_=0, to=1, number_of_steps=4)
            self.slider_1.grid(row=3, column=0, padx=(20, 10), pady=(10, 10), sticky="ew")
            self.slider_2 = ctk.CTkSlider(self.slider_progressbar_frame, orientation="vertical")
            self.slider_2.grid(row=0, column=1, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
            self.progressbar_3 = ctk.CTkProgressBar(self.slider_progressbar_frame, orientation="vertical")
            self.progressbar_3.grid(row=0, column=2, rowspan=5, padx=(10, 20), pady=(10, 10), sticky="ns")

            # create scrollable frame
            self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="CTkScrollableFrame")
            self.scrollable_frame.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
            self.scrollable_frame.grid_columnconfigure(0, weight=1)
            self.scrollable_frame_switches = []
            for i in range(100):
                switch = ctk.CTkSwitch(master=self.scrollable_frame, text=f"CTkSwitch {i}")
                switch.grid(row=i, column=0, padx=10, pady=(0, 20))
                self.scrollable_frame_switches.append(switch)

            # create checkbox and switch frame
            self.checkbox_slider_frame = ctk.CTkFrame(self)
            self.checkbox_slider_frame.grid(row=1, column=3, padx=(20, 20), pady=(20, 0), sticky="nsew")
            self.checkbox_1 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_1.grid(row=1, column=0, pady=(20, 0), padx=20, sticky="n")
            self.checkbox_2 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_2.grid(row=2, column=0, pady=(20, 0), padx=20, sticky="n")
            self.checkbox_3 = ctk.CTkCheckBox(master=self.checkbox_slider_frame)
            self.checkbox_3.grid(row=3, column=0, pady=20, padx=20, sticky="n")

            # set default values
            self.sidebar_button_3.configure(state="disabled", text="Disabled CTkButton")
            self.checkbox_3.configure(state="disabled")
            self.checkbox_1.select()
            self.scrollable_frame_switches[0].select()
            self.scrollable_frame_switches[4].select()
            self.radio_button_3.configure(state="disabled")
            self.appearance_mode_optionemenu.set("Dark")
            self.scaling_optionemenu.set("100%")
            self.optionmenu_1.set("CTkOptionmenu")
            self.combobox_1.set("CTkComboBox")
            self.slider_1.configure(command=self.progressbar_2.set)
            self.slider_2.configure(command=self.progressbar_3.set)
            self.progressbar_1.configure(mode="indeterminnate")
            self.progressbar_1.start()
            self.textbox.insert("0.0", "CTkTextbox\n\n" + "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.\n\n" * 20)
            self.seg_button_1.configure(values=["CTkSegmentedButton", "Value 2", "Value 3"])
            self.seg_button_1.set("Value 2")

        def open_input_dialog_event(self):
            dialog = ctk.CTkInputDialog(text="Type in a number:", title="CTkInputDialog")
            print("CTkInputDialog:", dialog.get_input())

        def change_appearance_mode_event(self, new_appearance_mode: str):
            ctk.set_appearance_mode(new_appearance_mode)

        def change_scaling_event(self, new_scaling: str):
            new_scaling_float = int(new_scaling.replace("%", "")) / 100
            ctk.set_widget_scaling(new_scaling_float)

        def sidebar_button_event(self):
            print("sidebar_button click")

    app = App()
    app.mainloop()

def subjet_select_gui():

    def get_switches_status(switches):
        settings = get_bops_settings()
        settings['subjects'] = dict()
        for i, switch in enumerate(switches):
            settings['subjects'][subject_names[i]] = switch.get()

        save_bops_settings(settings)
        exit()


    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

    screen_size = si.get_monitors()

    root = ctk.CTk()
    root.geometry('500x600')

    frame = ctk.CTkFrame(root)
    frame.pack(pady=5,padx=5,fill='both',expand=True)

    subject_names = get_subject_names()
    # create scrollable frame
    scrollable_frame = ctk.CTkScrollableFrame(frame, label_text="Choose the subjects")
    scrollable_frame.pack(padx=0, pady=0)
    # scrollable_frame.pack_configure(0, weight=1)
    scrollable_frame_switches = []
    switches_gui  = []
    values = []

    for idx, subject in enumerate(subject_names):
        switch = ctk.CTkSwitch(master=scrollable_frame, text=subject)
        switch.pack(padx=0, pady=0)
        switches_gui.append(switch)

        scrollable_frame_switches.append(switch)

    button1 = ctk.CTkButton(master = root, text='Select subjects',
                            command = lambda: get_switches_status(switches_gui))
    button1.pack(pady=12,padx=10)

    root.mainloop()



    # class App(ctk.CTk):
    #     def __init__(self):
    #         super().__init__()

    #         # configure window
    #         self.title("Select subjects")
    #         self.geometry(f"{1100}x{580}")
    #         # # configure grid layout (4x4)
    #         # self.grid_columnconfigure(1, weight=1)
    #         # self.grid_columnconfigure((2, 3), weight=0)
    #         # self.grid_rowconfigure((0, 1, 2), weight=1)
    #         subject_names = get_subject_names()
    #         # create checkbox and switch frame
    #         self.checkbox_slider_frame = ctk.CTkFrame(self)
    #         self.checkbox_slider_frame.grid(row=1, column=1, padx=(20, 20), pady=(20, 0), sticky="nsew")
    #         count = 1
    #         for i in subject_names:
    #             self.checkbox_1 = ctk.CTkCheckBox(master=self.checkbox_slider_frame, text=i)
    #             self.checkbox_1.grid(row=count, column=1, pady=(20, 0), padx=20, sticky="n")
    #             count += 1

    #         # create scrollable frame
    #         self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="CTkScrollableFrame")
    #         self.scrollable_frame.grid(row=1, column=2, padx=(20, 0), pady=(20, 0), sticky="nsew")
    #         self.scrollable_frame.grid_columnconfigure(0, weight=1)
    #         self.scrollable_frame_switches = []
    #         for i in range(100):
    #             switch = ctk.CTkSwitch(master=self.scrollable_frame, text=f"CTkSwitch {i}")
    #             switch.grid(row=i, column=0, padx=10, pady=(0, 20))
    #             self.scrollable_frame_switches.append(switch)

    # app = App()
    # app.mainloop()

########################################################################################################################################



########################################################  Plotting  ####################################################################
def plotBops():
    pass

def show_image(image_path):
    # Create a Tkinter window
    window = tk.Tk()
    # Load the image using PIL
    image = Image.open(image_path)
    # Create a Tkinter PhotoImage from the PIL image
    photo = ImageTk.PhotoImage(image)
    
    # Create a Tkinter label to display the image
    label = tk.Label(window, image=photo)
    label.pack()
    # Run the Tkinter event loop
    window.mainloop()

########################################################################################################################################


######################################################  Error prints  ##################################################################
def exampleFunction():
    pass

########################################################################################################################################


##################################################  CREATE BOPS SETTINGS ###############################################################
def add_markers_to_settings():
    settings = get_bops_settings()
    for subject_folder in get_subject_folders():
        for session in get_subject_sessions(subject_folder):
            sessionPath = os.path.join(subject_folder,session)
            for trial_name in get_trial_list(sessionPath,full_dir = False):

                c3dFilePath = get_trial_dirs(sessionPath, trial_name)['c3d']
                c3d_data = import_c3d_data(c3dFilePath)


                settings['marker_names'] = c3d_data['marker_names']
                break
            break
        break

    save_bops_settings(settings)

def get_testing_file_path(file_type = 'c3d'):
    bops_dir = get_dir_bops()
    dir_simulations =  os.path.join(bops_dir, 'ExampleData\simulations')
    file_path = []
    for subject_folder in get_subject_folders(dir_simulations):
        for session in get_subject_sessions(subject_folder):
            sessionPath = os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(get_trial_list(sessionPath,full_dir = False)):

                resultsDir = get_trial_list(sessionPath,full_dir = True)[idx]
                if file_type.__contains__('c3d'):
                    file_path.append(os.path.join(resultsDir,'c3dfile.c3d'))

                elif file_type.__contains__('trc'):
                    file_path.append(os.path.join(resultsDir,'markers.trc'))

                elif file_type.__contains__('so'):
                    file_path.append(os.path.join(resultsDir,'_StaticOptimization_activation.sto'))
                    file_path.append(os.path.join(resultsDir,'_StaticOptimization_force.sto'))

                break
            break
        break
    file_path = file_path[0] # make it a string instead of a list

    return file_path

def progress_bar():
    total_steps = 5
    with tqdm(total=total_steps, desc="Processing") as pbar:
        pbar.update(1)
########################################################################################################################################






############################################################## OPERATIONS ##############################################################
def calculate_jump_height_impulse(vert_grf,sample_rate):
    
        
    # Check if the variable is a NumPy array
    if isinstance(vert_grf, np.ndarray):
        print("Variable is a NumPy array")
    else:
        print("Variable is not a NumPy array")
    
    time = np.arange(0, len(vert_grf)/sample_rate, 1/sample_rate)

    # Select time interval of interest
    plt.plot(vert_grf)
    x = plt.ginput(n=1, show_clicks=True)
    plt.close()

    baseline = np.mean(vert_grf[:250])
    mass = baseline/gravity
        
    #find zeros on vGRF
    idx_zeros = vert_grf[vert_grf == 0]
    flight_time_sec = len(idx_zeros/sample_rate)/1000
        
    # find the end of jump index = first zero in vert_grf
    take_off_frame = np.where(vert_grf == 0)[0][0] 
        
    # find the start of jump index --> the start value is already in the file
    start_of_jump_frame = int(np.round(x[0][0]))
    
        # Calculate impulse of vertical GRF    
    vgrf_of_interest = vert_grf[start_of_jump_frame:take_off_frame]

    # Create the time vector
    time = np.arange(0, len(vgrf_of_interest)/sample_rate, 1/sample_rate)

    vertical_impulse_bw = mass * gravity * time[-1]
    vertical_impulse_grf = np.trapz(vgrf_of_interest, time)

    # subtract impulse BW
    vertical_impulse_net = vertical_impulse_grf - vertical_impulse_bw


    take_off_velocity = vertical_impulse_net / mass

    # Calculate jump height using impulse-momentum relationship (DOI: 10.1123/jab.27.3.207)
    jump_height = (take_off_velocity / 2 * gravity)
    jump_height = (take_off_velocity**2 / 2 * 9.81) /100   # devie by 100 to convert to m

    # calculate jump height from flight time
    jump_height_flight = 0.5 * 9.81 * (flight_time_sec / 2)**2   

    print('take off velocity = ' , take_off_velocity, 'm/s')
    print('cmj time = ' , time[-1], ' s')
    print('impulse = ', vertical_impulse_net, 'N.s')
    print('impulse jump height = ', jump_height, ' m')
    print('flight time jump height = ', jump_height_flight, ' m')
    
    return jump_height, vertical_impulse_net

def blandAltman(method1=[],method2=[]):
    # Generate example data
    if not method1:
        method1 = np.array([1.2, 2.4, 3.1, 4.5, 5.2, 6.7, 7.3, 8.1, 9.5, 10.2])
        method2 = np.array([1.1, 2.6, 3.3, 4.4, 5.3, 6.5, 7.4, 8.0, 9.4, 10.4])

    # Calculate the mean difference and the limits of agreement
    mean_diff = np.mean(method1 - method2)
    std_diff = np.std(method1 - method2, ddof=1)
    upper_limit = mean_diff + 1.96 * std_diff
    lower_limit = mean_diff - 1.96 * std_diff

    # Plot the Bland-Altman plot
    plt.scatter((method1 + method2) / 2, method1 - method2)
    plt.axhline(mean_diff, color='gray', linestyle='--')
    plt.axhline(upper_limit, color='gray', linestyle='--')
    plt.axhline(lower_limit, color='gray', linestyle='--')
    plt.xlabel('Mean of two methods')
    plt.ylabel('Difference between two methods')
    plt.title('Bland-Altman plot')
    plt.show()

    # Print the results
    print('Mean difference:', mean_diff)
    print('Standard deviation of difference:', std_diff)
    print('Upper limit of agreement:', upper_limit)
    print('Lower limit of agreement:', lower_limit)


########################################################################################################################################





################################################ UTILS

def clear_terminal():
    # Clear terminal command based on the operating system
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For macOS and Linux (posix)
        os.system('clear')

def uni_vie_print():
    print("=============================================")
    print("      DEVELOPED BY BASILIO GONCALVES         ")
    print("            University of Vienna             ")
    print("    Contact: basilio.goncalves@univie.ac.at  ")
    print("=============================================")
                                                                                                            

######################################################### BOPS TESTING #################################################################
def platypus_pic_path(imageType = 'happy'):
    dir_bops = get_dir_bops()
    if imageType == 'happy':
        image_path = os.path.join(dir_bops,'src\platypus.jpg')
    else:
        image_path = os.path.join(dir_bops,'src\platypus_sad.jpg')

def print_happy_platypus():             
    print('all packages are installed and bops is ready to use!!') 
    show_image(platypus_pic_path('happy'))
      
def print_sad_platypus():
    show_image(platypus_pic_path('sad'))

class test_bops(unittest.TestCase):
    
    def test_import_opensim(self):
        print('testing import opensim ... ')
        import opensim as osim
                    
    def test_import_c3d_data(self):
        print('testing import_c3d_data ... ')
        
        c3dFilePath = get_testing_file_path('c3d')       
        
        self.assertEqual(type(c3dFilePath),str)
        self.assertTrue(os.path.isfile(c3dFilePath))        
        
        import_c3d_data(c3dFilePath)
        
        # make sure that import c3d does not work with a string
        with self.assertRaises(Exception):
            import_c3d_data(2)  
        
        
        filtered_emg = emg_filter(c3dFilePath)
        self.assertIs(type(filtered_emg),pd.DataFrame)
    
    def test_loop_through_folders(self):
        print('testing loop through folders ... ')
        for subject_folder in get_subject_folders(get_testing_file_path()):
            for session in get_subject_sessions(subject_folder):
                session_path = os.path.join(subject_folder,session)
                for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

                    resultsDir = get_trial_list(session_path,full_dir = True)[idx]
                    self.assertEqual(resultsDir,str)
                    return
    
    def to_be_finished_test_add_marker_to_trc():
        print('testing add_marker_trc ... ')
    
    def to_be_finished_test_IK():
        print('testing IK ... ')
        for subject_folder in get_subject_folders(testing_data_dir()):
            for session in get_subject_sessions(subject_folder):
                session_path = os.path.join(subject_folder,session)
                for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

                    model_path = r'.\test.osim'
                    ik_results_file = r'.\test.osim'
                    mot_file = r'.\test.osim'
                    grf_xml = r'.\test.osim'
                    resultsDir = get_trial_list(session_path,full_dir = True)[idx]
                    run_IK(model_path, trc_file, resultsDir, marker_weights_path)
    
    def test_writeTRC(self):
        print('testing writeTRC ... ')
        trcFilePath = get_testing_file_path('trc')
        c3dFilePath = get_testing_file_path('c3d')
        writeTRC(c3dFilePath, trcFilePath)
        
    def test_c3d_export(self):
        print('testing c3d_export ... ')
        c3dFilePath = get_testing_file_path('c3d')
        c3d_dict = import_c3d_data(c3dFilePath)
        self.assertEqual(type(c3d_dict),dict)
        c3d_osim_export(c3dFilePath)
        

if __name__ == '__main__':
    
    clear_terminal()
    uni_vie_print()
    
    print('runnung all tests ...')
    output = unittest.main(exit=False)
    if output.result.errors or output.result.failures:
        print_sad_platypus()
    else:
        print('no errors')
        print_happy_platypus()
            

# end