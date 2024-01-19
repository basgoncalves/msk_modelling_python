
# to import bops need to deactivate some packages not intalled (offline mode, consider this when packaging)
import subprocess
import sys
import os
import time
import datetime
import shutil
import tkinter as tk
import opensim as osim
from tkinter import filedialog
import os
import bops as bp   
import pandas as pd
import xml.etree.ElementTree as ET
from memory_profiler import profile
# import pyomeca as pym

def get_main_path():
    main_path = r'C:\Git\isbs2024\Data'
    if not os.path.isdir(main_path):
        raise Exception('Main folder not found: {}'.format(main_path))
    
    return main_path

class subject_paths:
    def __init__(self, data_folder,subject_code='default',trial_name='trial1'):

        # main paths
        self.main = data_folder
        self.setup_folder = os.path.join(self.main,'Setups')
        self.setup_ceinms = os.path.join(self.main,'Setups','ceinms')
        self.simulations = os.path.join(self.main,'Simulations')
        self.subject = os.path.join(self.simulations, subject_code)
        self.trial = os.path.join(self.subject, trial_name)

        # raw data paths
        self.c3d = os.path.join(self.subject, trial_name, 'c3dfile.c3d')
        self.grf = os.path.join(self.subject, trial_name, 'grf.mot')
        self.markers = os.path.join(self.subject, trial_name, 'markers.trc')
        self.emg = os.path.join(self.subject, trial_name, 'EMG_filtered.sto')

        # model paths
        self.models = os.path.join(self.main, 'Scaled_models')
        self.model_generic = os.path.join(self.models, 'generic_model.osim')
        self.model_scaled = os.path.join(self.models, subject_code + '_scaled.osim')

        # setup files
        self.grf_xml = os.path.join(self.trial,'GRF.xml')
        self.ik_setup = os.path.join(self.trial, 'setup_ik.xml')
        self.id_setup = os.path.join(self.trial, 'setup_id.xml')
        self.ma_setup = os.path.join(self.trial, 'setup_ma.xml')

        # IK paths
        self.ik_output = os.path.join(self.trial, 'IK.mot')
        
        # ID paths
        self.id_output = os.path.join(self.trial, 'inverse_dynamics.sto')
    
        # MA paths 
        self.ma_output_folder = os.path.join(self.trial, 'muscle_analysis')

        # JRA paths
        self.jra_output = os.path.join(self.trial, 'joint_reaction.sto')
        self.jra_setup = os.path.join(self.trial, 'setup_jra.xml')

        # CEINMS paths 
        self.ceinms_src = r"C:\Git\msk_modelling_matlab\src\Ceinms\CEINMS_2"
        if not os.path.isdir(self.ceinms_src):
            raise Exception('CEINMS source folder not found: {}'.format(self.ceinms_src))

        # subject files (model, excitation generator, calibration setup, trial xml)
        self.uncalibrated_subject = os.path.join(self.subject,'ceinms_shared','ceinms_uncalibrated_subject.xml') 
        self.calibrated_subject = os.path.join(self.subject,'ceinms_shared','ceinms_calibrated_subject.xml')
        self.ceinms_exc_generator = os.path.join(self.subject,'ceinms_shared','ceinms_excitation_generator.xml')
        self.ceinms_calibration_setup = os.path.join(self.subject,'ceinms_shared' ,'ceinms_calibration_setup.xml')
        
        # trial files (trial xml, ceinms_exe_setup, ceinms_exe_cfg)
        self.ceinms_trial_exe = os.path.join(self.trial,'ceinms_trial.xml')
        self.ceinms_trial_cal = os.path.join(self.trial,'ceinms_trial_cal.xml')
        self.ceinms_exe_setup = os.path.join(self.trial, 'ceinms_exe_setup.xml')
        self.ceinms_exe_cfg = os.path.join(self.trial, 'ceinms_exe_cfg.xml')

        # results folder
        self.ceinms_results = os.path.join(self.trial, 'ceinms_results')

# Create the GUI window for the application
def create_window(title, geometry='500x500'):
    
    window = tk.Tk()

    # Set the window title
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Calculate the window width and height
    window_width = screen_width // 2
    window_height = screen_height // 2

    # Calculate the x and y coordinates for centering the window
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # Set the window size and position
    window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    return window

def select_folder():
    root = tk.Tk()
    root.withdraw()

    folder_path = filedialog.askdirectory()
    print("Selected folder:", folder_path)
    return folder_path

def add_button(window, text, command, padx=5, pady=5, x=0, y=0):
    button = tk.Button(window, text=text, command=command)
    button.pack(padx=padx, pady=pady)
    button.place(x=x, y=y)

def isfile(path: str):
    if not os.path.exists(paths.ceinms_exe_setup):
        print('File not found: {}'.format(paths.ceinms_exe_setup))
        return False
    else:
        return True

# Utils
def suppress_output(func):
    def wrapper(*args, **kwargs):
        # Redirect standard output to null device
        with open(os.devnull, 'w') as devnull:
            old_stdout = os.dup(1)
            os.dup2(devnull.fileno(), 1)

            # Call the function
            result = func(*args, **kwargs)

            # Restore standard output
            os.dup2(old_stdout, 1)
            os.close(old_stdout)

        return result

    return wrapper

def print_to_log_file(step = 'analysis',subject=' ',stage = ' '):
    file_path = get_main_path() + r'\log.txt'

    try:
        with open(file_path, 'a') as file:
            current_datetime = datetime.datetime.now()
            if not step:
                log_message = f"\n\n"
            else:
                log_message = f"{step} {subject} {stage} {current_datetime}\n"
            file.write(log_message)
            
    except FileNotFoundError:
        print("File not found.")

def print_terminal_spaced(text = " "):
    print("=============================================")
    print(" ")
    print(" ")
    print(" ")
    print(text)
    time.sleep(1.5)

def raise_exception(error_text = " ", err = " "):
    print_to_log_file(error_text , ' ', ' ') # print to log file
    print_to_log_file(err) # print to log file
    raise Exception (error_text)

# Load/Save data 
def get_emg_labels(sto_file):
    
    @suppress_output
    def load_sto(mot_file):
        return osim.Storage(mot_file)
    
    emg = load_sto(sto_file)
    emg_labels = ''
    for i in range(10000):
        try:
            if emg.getColumnLabels().get(i) == 'time':
                continue
            emg_labels = emg_labels + ' ' + emg.getColumnLabels().get(i)
        except:
            break
    
    return emg_labels

def get_initial_and_last_times(mot_file):
    # Read the .\IK.mot file into a pandas DataFrame
    # @suppress_output
    def load_mot(mot_file):
        return osim.Storage(mot_file)

    motData = load_mot(mot_file)
    # Get initial and final time
    initial_time = motData.getFirstTime()
    final_time = motData.getLastTime()

    return initial_time, final_time
  
# XML edit
def edit_xml_file(xml_file,tag,new_tag_value):

    text_to_print = tag  + ' = ' + str(new_tag_value)
    with open(xml_file, 'r', encoding='utf-8') as file:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    
        for character in root.iter(tag):
            old_value = character.text
            character.text = str(new_tag_value)
    with open(xml_file, 'w', encoding='utf-8') as file:
        tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    try:
        print(text_to_print)
    except:
        pass
    
    return tree

# Opensim functions
def run_scale(model_file, marker_file, output_model_file):
    # Load model and create a ScaleTool
    model = osim.Model(model_file)
    scale_tool = osim.ScaleTool()

    # Set the model for the ScaleTool
    scale_tool.setModel(model)

    # Set the marker data file for the ScaleTool
    scale_tool.setMarkerFileName(marker_file)

    # Set the output model file name
    scale_tool.setOutputModelFileName(output_model_file)

    # Save setup file
    scale_tool.printToXML('setup_scale.xml')

    # Run ScaleTool
    scale_tool.run()

def run_static_optimization(model_file, motion_file, output_motion_file):
    # Load model and create a StaticOptimizationTool
    model = osim.Model(model_file)
    so_tool = osim.StaticOptimization()

    # Set the model for the StaticOptimizationTool
    so_tool.setModel(model)

    # Set the motion data file for the StaticOptimizationTool
    so_tool.setCoordinatesFileName(motion_file)

    # Set the output motion file name
    so_tool.setOutputMotionFileName(output_motion_file)

    # Save setup file
    so_tool.printToXML('setup_so.xml')

    # Run StaticOptimizationTool
    so_tool.run()

def convert_c3d_to_opensim(c3d_file, trc_file, mot_file):
    # Load C3D file
    c3d_adapter = osim.C3DFileAdapter()
    c3d_table = c3d_adapter.read(c3d_file)

    # Extract marker data from C3D table
    marker_data = osim.TimeSeriesTableVec3()
    marker_data.setColumnLabels(c3d_table.getColumnLabels())
    for i in range(c3d_table.getNumRows()):
        frame_time = c3d_table.getIndependentColumn()[i]
        markers = osim.StdVectorVec3()
        for j in range(c3d_table.getNumColumns()):
            marker = osim.Vec3(c3d_table.getDependentColumnAtIndex(j)[i])
            markers.append(marker)
        marker_data.appendRow(frame_time, markers)

    # Write TRC file
    trc_adapter = osim.TRCFileAdapter()
    trc_adapter.write(marker_data, trc_file)

    # Write MOT file (empty forces and EMG data)
    mot_table = osim.TimeSeriesTable()
    mot_table.setColumnLabels(c3d_table.getColumnLabels())
    mot_adapter = osim.STOFileAdapter()
    mot_adapter.write(mot_table, mot_file)

def run_inverse_kinematics(model_file, marker_file, output_motion_file):
    # Load model and create an InverseKinematicsTool
    model = osim.Model(model_file)
    ik_tool = osim.InverseKinematicsTool()

    # Set the model for the InverseKinematicsTool
    ik_tool.setModel(model)

    # Set the marker data file for the InverseKinematicsTool
    ik_tool.setMarkerDataFileName(marker_file)

    # Specify output motion file
    ik_tool.setOutputMotionFileName(output_motion_file)

    # Save setup file
    ik_tool.printToXML('setup_ik.xml')

    # Run Inverse Kinematics
    ik_tool.run()

# @profile
def edit_muscle_analysis_setup(ma_setup_path,model_file,initial_time, last_time):
    
    # sys.stdout.flush()
    try:
        print('creating setup files muscle analysis ...')    
    except:
        pass

    edit_xml_file(ma_setup_path,'start_time',initial_time)
    edit_xml_file(ma_setup_path,'initial_time',initial_time)
    edit_xml_file(ma_setup_path,'final_time',last_time)
    edit_xml_file(ma_setup_path,'end_time',last_time)
    edit_xml_file(ma_setup_path,'model_file',model_file)

def run_muscle_analysis(model_file, motion_file, output_folder):
    # Load model and create a MuscleAnalysisTool
    model = osim.Model(model_file)
    ma_tool = osim.MuscleAnalysisTool()

    # Set the model for the MuscleAnalysisTool
    ma_tool.setModel(model)

    # Set the motion data file for the MuscleAnalysisTool
    ma_tool.setCoordinatesFileName(motion_file)

    # Set the output folder for the MuscleAnalysisTool
    ma_tool.setOutputDirectory(output_folder)

    # Save setup file
    ma_tool.printToXML('setup_ma.xml')

    # Run MuscleAnalysisTool
    ma_tool.run()

# CEINMS functions
def copy_template_files_ceinms(paths: type,replace = False):
    try:
        print('copying ceinms template files ...')
    except:
        pass
    any_file_copied = False # flag to check if any file was copied
    ceinms_shared_folder = os.path.join(paths.subject,'ceinms_shared')

    # copy ceinms_shared folder
    if not os.path.isdir(ceinms_shared_folder) or replace:
        src = os.path.join(paths.setup_ceinms,'ceinms_shared')
        dst = os.path.join(paths.subject,'ceinms_shared')
        shutil.copytree(src, dst)
        print('ceinms shared folder copied to ' + paths.subject)
        any_file_copied = True 

    # copy ceinms_exe_cfg.xml if it does not exist
    if not os.path.isfile(os.path.join(paths.trial,'ceinms_exe_cfg.xml')) or replace:
        src = (os.path.join(paths.setup_ceinms,'ceinms_exe_cfg.xml'))
        dst = (os.path.join(paths.trial,'ceinms_exe_cfg.xml'))
        shutil.copy(src, dst) 
        print('ceinms exe cfg copied to ' + paths.trial)
        any_file_copied = True

    # copy ceinms_exe_setup.xml if it does not exist
    if not os.path.isfile(os.path.join(paths.trial,'ceinms_exe_setup.xml')) or replace:
        src = (os.path.join(paths.setup_ceinms,'ceinms_exe_setup.xml'))
        dst = (os.path.join(paths.trial,'ceinms_exe_setup.xml'))
        shutil.copy(src, dst) 
        print('ceinms exe setup copied to ' + paths.trial)
        any_file_copied = True

    # copy ceinms_trial.xml if it does not exist    
    if not os.path.isfile(os.path.join(paths.trial,'ceinms_trial.xml')) or replace:
        src = (os.path.join(paths.setup_ceinms,'ceinms_trial.xml'))
        dst = (os.path.join(paths.trial,'ceinms_trial.xml'))
        shutil.copy(src, dst) 
        print('ceinms trial xml copied to ' + paths.trial) 
        any_file_copied = True

    if not os.path.isfile(os.path.join(paths.trial,'ceinms_trial_cal.xml')) or replace:

        src = (os.path.join(paths.setup_ceinms,'ceinms_trial_cal.xml'))
        dst = (os.path.join(paths.trial,'ceinms_trial_cal.xml'))
        shutil.copy(src, dst)
        print('ceinms trial calibratioon xml copied to ' + paths.trial) 
        any_file_copied = True

    if any_file_copied:
        print('all files copied')
    else:
        print('files already in the folder')

def remove_missing_emgs_from_excitation_generator(input_file_path, sto_file):
    labels = get_emg_labels(sto_file).split()
    # Load the XML file
    tree = ET.parse(input_file_path)
    root = tree.getroot()

    # Loop through all excitation tags
    for excitation in root.findall('.//excitation'):
        # Check if the input value is labels
        input_tag = excitation.find('./input')
        if input_tag is not None and input_tag.text not in labels:
            # If not, remove the input tag
            excitation.remove(input_tag)

    tree.write(input_file_path, encoding='utf-8', xml_declaration=True)

def run_calibration(paths: type):
    if isfile(paths.ceinms_calibration_setup):
        os.chdir(os.path.dirname(paths.ceinms_calibration_setup))
        command = " ".join([paths.ceinms_src + "\CEINMScalibrate.exe -S", paths.ceinms_calibration_setup])
        print(command)
        proc = subprocess.run(command, shell=True)

def run_execution(paths: type):
    if isfile(paths.ceinms_exe_setup):
        try:
            os.mkdir(paths.ceinms_results)
        except:
            pass
        os.chdir(paths.ceinms_results)
        command = " ".join([paths.ceinms_src + "\CEINMS.exe -S", paths.ceinms_exe_setup])
        print(command)
        proc = subprocess.run(command, shell=True)

def run_full_pipeline():
    pass


if __name__ == '__main__':
    data_folder = get_main_path()
    subject_list = ['Athlete_03','Athlete_06','Athlete_14','Athlete_20','Athlete_22','Athlete_25','Athlete_26']
    subject_list = ['Athlete_03_torsion']
    
    trial_list = ['sq_70', 'sq_90']
    trial_list = ['sq_90']
    for subject_name in subject_list:
        for trial_name in trial_list:
            
            # create subject paths object with all the paths in it 
            paths = subject_paths(data_folder,subject_code=subject_name,trial_name=trial_name)
            # paths.model_scaled = os.path.join(data_folder,'Scaled_models\{i}_scaled.osim'.format(i=subject_name))
              
            if not os.path.isdir(paths.trial):
                raise Exception('Trial folder not found: {}'.format(paths.trial))

            if not os.path.isfile(paths.model_scaled):
                raise Exception('Scaled model not found: {}'.format(paths.model_scaled))

            print_terminal_spaced('Running pipeline for ' + subject_name + ' ' + trial_name)

            print_to_log_file('')
            print_to_log_file('Running pipeline for ',subject_name + ' ' + trial_name, 'start') # log file

            # edit xml files 
            relative_path_grf = os.path.relpath(paths.grf, os.path.dirname(paths.grf_xml))
            edit_xml_file(paths.grf_xml,'datafile',relative_path_grf)

            for i in range(50):
                # find time range for the trial 
                try:
                    print_to_log_file('getting times from IK.mot  ... ', ' ', 'start') # log file
                    initial_time, last_time = get_initial_and_last_times(paths.ik_output)
                    print_to_log_file('done!', ' ', ' ') # log file
                except Exception as e:
                    print_to_log_file('stop for error ...' , ' ', ' ') # log file
                    print_to_log_file(e)
                    raise Exception('Get initial and last times failed for ' + subject_name + ' ' + trial_name)
            
            
                # edit muscle analysis setup files
                try:
                    print_to_log_file('muscle analysis setup  ... ', ' ', 'start') # log file
                    template_ma_setup = os.path.join(paths.setup_folder,'setup_ma.xml')
                    shutil.copy(template_ma_setup, paths.ma_setup)
                    edit_muscle_analysis_setup(paths.ma_setup,paths.model_scaled,initial_time, last_time)
                    print_to_log_file('done! ', ' ', ' ') # log file
                except Exception as e:
                    print_to_log_file('stop for error ...' , ' ', ' ') # log file
                    print_to_log_file(e)
                    raise Exception('Muscle analysis setup failed for ' + subject_name + ' ' + trial_name)
                
            exit()
            try:
                # (NOT WORKING YET)run_muscle_analysis(paths.ma_setup) use xml setup files for now
                print_to_log_file('muscle analysis run ... ', ' ', 'start') # log file
                length_sto_file = os.path.join(paths.ma_output_folder,'_MuscleAnalysis_Length.sto')
                if not os.path.isfile(length_sto_file):
                    analyzeTool_MA = osim.AnalyzeTool(paths.ma_setup)
                    analyzeTool_MA.run()
                    
                    print_to_log_file('done! ',' ', ' ') # log file
                else:
                    print('Muscle analysis already in the folder for ' + subject_name + ' ' + trial_name)
                    print_to_log_file('Muscle analysis already exists. Continue... ',' ', ' ') # log file
            except Exception as e:
                print_to_log_file('stop for error ...' , ' ', ' ') # log file
                print_to_log_file(e)
                raise Exception('Muscle analysis failed for ' + subject_name + ' ' + trial_name)


            # edit ceinms files
            try:
                print_to_log_file('ceinms setup ',' ', 'start') # log file

                copy_template_files_ceinms(paths, replace=False)

                time_range_execution = (str(initial_time) + ' ' + str(last_time)) 
                time_range_calibration = (str(initial_time) + ' ' + str(initial_time+1))
                remove_missing_emgs_from_excitation_generator(paths.ceinms_exc_generator, paths.emg)
                edit_xml_file(paths.ceinms_exc_generator,'inputSignals',get_emg_labels(paths.emg)) 
                edit_xml_file(paths.ceinms_trial_exe,'startStopTime',time_range_execution)
                edit_xml_file(paths.ceinms_trial_cal,'startStopTime',time_range_calibration)
                edit_xml_file(paths.uncalibrated_subject,'opensimModelFile',paths.model_scaled)
                
                sys.stdout.flush()
                print('ceinms files edited for ' + subject_name + ' ' + trial_name)

                print_to_log_file(' done! ', ' ' , ' ') # log file
            except Exception as e:
                print_to_log_file('stop for error ...' , ' ', ' ') # log file
                print_to_log_file(e)
                raise Exception('Error creating ceinsm setup files failed for ' + subject_name + ' ' + trial_name)    
            
            # run CEINMS calibration only for sq_70
            if trial_name == 'sq_70' and not os.path.isfile(paths.calibrated_subject):
                try:
                    print_to_log_file('ceinms calibration ... ',' ', ' start') # log file
                    
                    run_calibration(paths)

                    print_to_log_file('done! ',' ', ' ') # log file
                except Exception as e:
                    error_text = 'CEINMS calibration failed for ' + subject_name + ' ' + trial_name
                    print_to_log_file(error_text , ' ', ' ') # log file
                    raise Exception (error_text)
            
            # run CEINMS execution
            try:
                print_to_log_file('ceinms execution ... ',' ', 'start') # log file
                run_execution(paths)
                print_to_log_file('done! ', ' ', ' ') # log file
            except Exception as e:
                raise_exception('CEINMS execution failed for ' + subject_name + ' ' + trial_name,e)      
                
        # end trial loop
        
    # end subject loop
    