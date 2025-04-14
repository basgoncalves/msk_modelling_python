# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021):
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

__testing__ = False

import os
import json
import time
import unittest
import numpy as np
import pandas as pd
import c3d
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import math

try:
    import opensim as osim
except:
    print('OpenSim not installed.')
    osim = None

BOPS_PATH = os.path.dirname(os.path.realpath(__file__))

def about():
    '''
    Function to print the version of the package and the authors
    '''
    print('BOPSpy - Batch OpenSim Processing Scripts Python')
    print('Authors: Basilio Goncalves')
    print('ispired by BOPS: MATALB DOI: 10.1080/10255842.2020.1867978 - https://pubmed.ncbi.nlm.nih.gov/33427495/')
    print('Python version by Bas Goncalves')

def greet():
    print("Are you ready to run openSim?!")
 
def is_setup_file(file_path, type = 'OpenSimDocument', print_output=False):
    '''
    Function to check if a file is an OpenSim setup file. 
    The function reads the file and checks if the type is present in the file.
    
    '''
    is_setup = False
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if type in line:
                    is_setup = True
                    break
                
                #if is last line and no match, return false
                if line == None:
                    is_setup = False
                    
    except Exception as e:
        print(f"Error reading file: {e}")
    
    if print_output and is_setup:
        print(f"{file_path} is a setup file")
    elif print_output and not is_setup:
        print(f"{file_path} is not a setup file")
        
    return is_setup  

def check_file_path(filepath, prompt = 'Select file'):
    if not filepath:
        root = tk.Tk(); root.withdraw()
        filepath = filedialog.askopenfilename(title=prompt)
        
        root.destroy()
        
    return filepath

# XML handling
class log:
    def error(error_message):
        try:
            with open(os.path.join(BOPS_PATH,"error_log.txt"), 'a') as file:
                date = time.strftime("%Y-%m-%d %H:%M:%S")
                file.write(f"{date}: {error_message}\n")
        except:
            print("Error: Could not log the error")
            return

class reader: 
    '''
    Class to store data from different file types
    
    Usage: 
    c3d_data = msk.bops.reader.c3d(filepath) # read c3d file and return data as a dictionary    
    json_data = msk.bops.reader.json(filepath) # read json file and return data as a dictionary
    
    '''
    def c3d(filepath=None):
        ''''
        Function to read a c3d file and return the data as a dictionary
        '''
        filepath = check_file_path(filepath, prompt = 'select your .c3d file')
        
        try:
            data = c3d.Reader(open(filepath, 'rb'))
            return data
        
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
                      
    def json(filepath=None):
        
        filepath = check_file_path(filepath, prompt = 'select your .json file')
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        return data
    
    def mot(filepath= None):
        '''
        Function to read a .mot file and return the data as a dictionary (should work for .sto files too)
        
        data = msk.bops.reader.mot(filepath)
        '''
        filepath = check_file_path(filepath, prompt = 'select your .mot or .sto file')
        # find the line containins "endheader"
        with open(filepath, 'r') as file:
            line_count = 0
            for line in file:
                line_count += 1
                if 'endheader' in line:
                    break
        
        # if not found, return None
        if not line:
            print('endheader not found')
            return None
        
        try:
            data = pd.read_csv(filepath, sep='\t', skiprows=line_count)
        except Exception as e:
            print('Error reading file: ' + str(e))
        
        return data
    
    def file(filepath):
        
        filepath = check_file_path(filepath, prompt = 'select your file')
        data=[]
        try:
            with open(filepath, 'r') as file:
                for line in file:
                    data.append(line)
                    
        except Exception as e:
            print(f"Error reading file: {e}")
        
        return data

    def project_settings(settings_file_json):    
        '''
        open the json file and check if all the necessary variables are present
        valid_vars = ['project_folder','subjects','emg_labels','analog_labels','filters']
        
        '''
        
        valid_vars = ['project_folder','subjects','emg_labels','analog_labels','filters']
        
        
        # Open settings file
        try:
            with open(settings_file_json, 'r') as f:
                settings = json.load(f)
        except:
            print('Error loading settings file')  
            
                        
        # Check if contains all the necessary variables
        try:
            for var in valid_vars:
                if var not in settings:
                    settings[var] = None
                    print(f'{var} not in settings. File might be corrupted.')
            
            # look for subjects in the simulations folder and update list
            if settings['project_folder']:
                settings['subjects'] = get_subject_folders(settings['project_folder'])
                
        except Exception as e:
            print('Error checking settings variables')
            
        
        # save the json file path
        try:
            settings['jsonfile'] = settings_file_json
            settings.pop('jsonfile', None)
        except:
            print('Error saving json file path')

class write:
    def json(data, file_path=None):
        if not file_path:
            file_path = filedialog.asksaveasfilename(defaultextension=".json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error writing JSON file: {e}")
            
    def mot(data, file_path=None):
        if not file_path:
            file_path = filedialog.asksaveasfilename(defaultextension=".mot")
        
        try:
            data.to_csv(file_path, sep='\t', index=False)
        except Exception as e:
            print(f"Error writing MOT file: {e}")
            
    def xml(data, file_path=None):
        if not file_path:
            file_path = filedialog.asksaveasfilename(defaultextension=".xml")
        
        try:
            with open(file_path, 'w') as f:
                f.write(data)
        except Exception as e:
            print(f"Error writing XML file: {e}")
               
class convert:
    def c3d_to_osim(file_path=None):
        
        if not file_path:
            file_path = filedialog.askopenfilename()
            
        print('Converting c3d to osim...')
        
        print('NOT FINISHED...')


class create:
    def grf_xml(grf_mot_path, save_path, nforceplates=3):
        try:
            with open(save_path, 'w') as file:
                file.write('<?xml version="1.0"?>\n')
                file.write('<OpenSimDocument Version="30000">\n')
                file.write('  <Model>\n')
                file.write('    <ForceSet>\n')
                
                for i in range(nforceplates):
                    file.write(f'      <GroundReactionForcePlate{i+1}>\n')
                    file.write(f'        <File>{grf_mot_path}</File>\n')
                    file.write('      </GroundReactionForcePlate>\n')
                
                file.write('    </ForceSet>\n')
                file.write('  </Model>\n')
                file.write('</OpenSimDocument>')
        except Exception as e:
            print(f"Error creating XML file: {e}")
            return
    
    def grf_mot(grf_path, save_path, headerlines=6):
        try:
            grf_data = pd.read_csv(grf_path, sep='\t', skiprows=headerlines)
            grf_data.to_csv(save_path, sep='\t', index=False)
        except Exception as e:
            print(f"Error reading or writing GRF file: {e}")
            return
    
        
class run:
    def __init__(self):
        pass
    
    def c3d_to_trc(c3d_file, trc_file, headerlines=6):
        try:
            c3d_data = c3d.Reader(open(c3d_file, 'rb'))
        except Exception as e:
            print(f"Error reading c3d file: {e}")
            return
        
        try:
            with open(trc_file, 'w') as file:
                file.write("PathFileType\t4\t(X/Y/Z)\t" + c3d_file + "\n")
                file.write("DataRate\t" + str(c3d_data['parameters']['POINT']['DATA_RATE']) + "\n")
                file.write("Frame#\tTime\tX1\tY1\tZ1\n")
                
                for i in range(c3d_data['parameters']['POINT']['NANALOG']):
                    file.write(str(i) + "\t" + str(c3d_data['parameters']['POINT']['DATA'][i]) + "\n")
        except Exception as e:
            print(f"Error writing trc file: {e}")
            return
    
    def inverse_kinematics(model_path, marker_path, output_folder, setup_template_path):
        try:
            print('Running inverse kinematics ...')
            
            
        except Exception as e:
            print(f"Error running inverse kinematics: {e}")
    
    
    def ceinms_calibration(xml_setup_file=None):
        '''
        msk.bops.run.ceinms_calibration(xml_setup_file)
        
        
        '''
        
        if xml_setup_file is None:
            print('Please provide the path to the xml setup file for calibration')
            return
        elif not os.path.isfile(xml_setup_file):
            print('The path provided does not exist')
            return
        
        try:        
            ceinms_install_path = os.path.join(BOPS_PATH, 'src', 'ceinms2', 'src')
            command = " ".join([ceinms_install_path + "\CEINMScalibrate.exe -S", xml_setup_file])
            print(command)
            # result = subprocess.run(command, capture_output=True, text=True, check=True)
            result = None
            return result
        except Exception as e:
            print(e)
            return None
    
class settings:
    def __init__():
        pass
            
    def read():
        try:
            return(reader.json(os.path.join(BOPS_PATH,'settings.json')))
        except:
            return(read.file(os.path.join(BOPS_PATH,'settings.json')))
    
    def _list(self):
        settings = read.json(os.path.join(BOPS_PATH,'settings.json'))
        for key in settings:
            print(f'{key}: {settings[key]}')

class Trial:
    '''
    Class to store trial information and file paths, and export files to OpenSim format
    
    Inputs: trial_path (str) - path to the trial folder
    
    Attributes:
    path (str) - path to the trial folder
    name (str) - name of the trial folder
    og_c3d (str) - path to the original c3d file
    c3d (str) - path to the c3d file in the trial folder
    markers (str) - path to the marker trc file
    grf (str) - path to the ground reaction force mot file
    ...
    
    Methods: use dir(Trial) to see all methods
    
    '''
    def __init__(self, trial_path):        
        self.path = trial_path
        self.name = os.path.basename(trial_path)
        self.c3d = os.path.join(os.path.dirname(trial_path), self.name + '.c3d')
        self.markers = os.path.join(trial_path,'markers_experimental.trc')
        self.grf = os.path.join(trial_path,'grf.mot')
        self.emg = os.path.join(trial_path,'emg.csv')
        self.ik = os.path.join(trial_path,'ik.mot')
        self.id = os.path.join(trial_path,'inverse_dynamics.sto')
        self.so_force = os.path.join(trial_path,'static_optimization_force.sto')
        self.so_activation = os.path.join(trial_path,'static_optimization_activation.sto')
        self.jra = os.path.join(trial_path,'joint_reacton_loads.sto')
        self.grf_xml = os.path.join(trial_path,'grf.xml')
        self.settings_json = os.path.join(self.path,'settings.json')
        
        self.files = []
        for file in os.listdir(self.path):
            file_path = os.path.join(self.path, file)
            try:
                file_data = import_file(file_path)
                self.files.append(file_data)
            except:
                file_data = None
                self.files.append(file_data)
  
                
                      
    def check_files(self):
        '''
        Output: True if all files exist, False if any file is missing
        '''
        files = self.__dict__.values()
        all_files_exist = True
        for file in files:
            if not os.path.isfile(file):
                print('File not found: ' + file)
                all_files_exist = False
                
        return all_files_exist
    
    def create_settings_json(self, overwrite=False):
        if os.path.isfile(self.settings_json) and not overwrite:
            print('settings.json already exists')
            return
        
        settings_dict = self.__dict__
        msk.bops.save_json_file(settings_dict, self.settings_json)
        print('trial settings.json created in ' + self.path)
    
    def exportC3D(self):
        msk.bops.c3d_osim_export(self.og_c3d) 

    def create_grf_xml(self):
        osim.create_grf_xml(self.grf, self.grf_xml)

class Subject:
    def __init__(self, subject_json):
        self = reader.json(subject_json)

class Project:
    
    def __init__(self, file_path=None):        
        # load settings
        try:
            if file_path.endswith('.json'):
                self.settings = reader.json(file_path)
            else:
                self.settings = reader.json(os.path.join(file_path,'settings.json'))
        except Exception as e:
            print(f"Error loading project settings: {e}")
            
            
    def start(self, project_folder=''):
    
        if not project_folder:
            settings = settings.read()
        else:
            pass
        
        print('NOT FINISHED....')
                             

#%% ######################################################  General  #####################################################################
