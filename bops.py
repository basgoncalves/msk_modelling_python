import os
import opensim as osim
from xml.etree import ElementTree as ET
import numpy as np
import pyc3dserver as c3d
import pandas as pd


def c3d_to_sto(c3dfilepath):
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
    
def c3d_emg_export(c3dfilepath,emg_labels):   
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver()
    
    # Open a C3D file
    ret = c3d.open_c3d(itf, c3dfilepath)
    
    # For the information of all analogs(excluding or including forces/moments)
    dict_analogs = c3d.get_dict_analogs(itf)
    labels = dict_analogs['LABELS']

    # Initialize the final dataframe
    analog_df = pd.DataFrame()
    
    # Store each of the vectors in dict_analogs as a columns in the final dataframe
    for iLab in labels:
        if iLab in emg_labels:
            iData = dict_analogs['DATA'][iLab] 
            analog_df[iLab] = iData.tolist()
    maindir = os.path.dirname(c3dfilepath)
    
    # Sava data in parent directory
    emg_filename = os.path.join(maindir,r'emg.mot')
    analog_df.to_csv(emg_filename)

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
