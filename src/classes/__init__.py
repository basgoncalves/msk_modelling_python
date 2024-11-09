from msk_modelling_python import *
import msk_modelling_python as msk
from msk_modelling_python import osim
import pyperclip
import json
import os
import xml.etree.ElementTree as ET

class mcf: # make coding fancy
    
    def __init__(self):
        pass
            
    header = staticmethod(lambda: pyperclip.copy("#%% #############################################################\n" +
                                                 "#                        Description:                           # \n" +
                                                 "##################################################################"))

# create a class for each option so that we can print the option names
class cmd_function:
    def __init__(self, func):
        self.func = func

    def run(self, *args, **kwargs):
        self.func(*args, **kwargs)

#%% OSIM DATA CLASSES

class SubjectPaths:
    def __init__(self, data_folder,subject_code='default',trial_name='trial1'):

        # main paths
        self.main = data_folder
        self.setup_folder = os.path.join(self.main,'Setups')
        self.setup_ceinms = os.path.join(self.main,'Setups','ceinms')
        self.simulations = os.path.join(self.main,'Simulations')
        self.subject = os.path.join(self.simulations, subject_code)
        
        trial_path = os.path.join(self.subject, trial_name)
        self.trial = TrialPaths(trial_path)
        self.results = os.path.join(self.main, 'results')

class TrialPaths:
    def __init__(self, trial_path = ''):

        if not trial_path: 
            trial_path = msk.bops.select_folder('Select trial folder')
        
        # main paths
        self.path = trial_path
        
        # raw data paths
        self.c3d = os.path.join(self.path, 'c3dfile.c3d')
        self.grf = os.path.join(self.path, 'grf.mot')
        self.markers = os.path.join(self.path, 'marker_experimental.trc')
        self.emg = os.path.join(self.path, 'emg.csv')

        # model paths
        self.model_generic = os.path.join(self.path, 'generic.osim')
        self.model_scaled = os.path.join(self.path, 'scaled.osim')
        self.model_torsion = os.path.join(self.path, 'torsion_scaled.osim')

        # setup files
        self.grf_xml = os.path.join(self.path,'GRF.xml')
        self.setup_ik = os.path.join(self.path, 'setup_ik.xml')
        self.setup_id = os.path.join(self.path, 'setup_id.xml')
        self.setup_so = os.path.join(self.path, 'setup_so.xml')
        self.setup_ma = os.path.join(self.path, 'setup_ma.xml')
        self.setup_jra = os.path.join(self.path, 'setup_jra.xml')
        
        # output paths
        self.ik_output = os.path.join(self.path, 'ik.mot')
        self.id_output = os.path.join(self.path, 'inverse_dynamics.sto')
        self.ma_output_folder = os.path.join(self.path, 'muscle_analysis')

        self.so_output_forces = os.path.join(self.path, 'muscle_forces.sto')
        self.so_output_activations = os.path.join(self.path, 'muscle_activations.sto')
        self.so_actuators = os.path.join(self.path, 'actuators_so.xml')

        self.jra_output = os.path.join(self.path, 'joint_raction_loads.sto')
        
        # CEINMS paths
        current_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ceinms_src = os.path.join(current_folder, 'ceinms2')
        if not os.path.isdir(self.ceinms_src):
            raise Exception('CEINMS source folder not found: {}'.format(self.ceinms_src))

        # subject files (model, excitation generator, calibration setup, trial xml)
        self.uncalibrated_subject = os.path.join(self.path,'ceinms','ceinms_uncalibrated_subject.xml') 
        self.calibrated_subject = os.path.join(self.path,'ceinms','ceinms_calibrated_subject.xml')
        self.ceinms_exc_generator = os.path.join(self.path,'ceinms','ceinms_excitation_generator.xml')
        self.ceinms_calibration_setup = os.path.join(self.path,'ceinms' ,'ceinms_calibration_setup.xml')
        
        # trial files (trial xml, ceinms_exe_setup, ceinms_exe_cfg)
        self.ceinms_trial_exe = os.path.join(self.path,'ceinms_trial.xml')
        self.ceinms_trial_cal = os.path.join(self.path,'ceinms_trial_cal.xml')
        self.ceinms_exe_setup = os.path.join(self.path, 'ceinms_exe_setup.xml')
        self.ceinms_exe_cfg = os.path.join(self.path, 'ceinms_exe_cfg.xml')

        # results folder
        self.ceinms_results = os.path.join(self.path, 'ceinms_results')
        self.ceinms_results_forces = os.path.join(self.ceinms_results,'MuscleForces.sto')
        self.ceinms_results_activations = os.path.join(self.ceinms_results,'Activations.sto')

class osimSetup:
    def __init__(self):
        pass
    
    def print_osim_info():
        print('Osim module version: ' + osim.__version__)
        print('Osim module path: ' + osim.__file__)
        

    def create_analysis_tool(coordinates_file, modelpath, results_directory, force_set_files=None):
        # Get mot data to determine time range
        motData = osim.Storage(coordinates_file)

        # Get initial and final time
        initial_time = motData.getFirstTime()
        final_time = motData.getLastTime()

        # Set the model
        model = osim.Model(modelpath)

        # Create AnalyzeTool
        analyzeTool = osim.AnalyzeTool()
        analyzeTool.setModel(model)
        analyzeTool.setModelFilename(model.getDocumentFileName())

        analyzeTool.setReplaceForceSet(False)
        analyzeTool.setResultsDir(results_directory)
        analyzeTool.setOutputPrecision(8)

        if force_set_files is not None:  # Set actuators file
            forceSet = osim.ArrayStr()
            forceSet.append(force_set_files)
            analyzeTool.setForceSetFiles(forceSet)

        # motData.print('.\states.sto')
        # states = osim.Storage('.\states.sto')
        # analyzeTool.setStatesStorage(states)
        analyzeTool.setInitialTime(initial_time)
        analyzeTool.setFinalTime(final_time)

        analyzeTool.setSolveForEquilibrium(False)
        analyzeTool.setMaximumNumberOfSteps(20000)
        analyzeTool.setMaxDT(1)
        analyzeTool.setMinDT(1e-008)
        analyzeTool.setErrorTolerance(1e-005)

        analyzeTool.setExternalLoadsFileName('.\GRF.xml')
        analyzeTool.setCoordinatesFileName(coordinates_file)
        analyzeTool.setLowpassCutoffFrequency(6)

        return analyzeTool

    def get_muscles_by_group_osim(xml_path, group_names): # olny tested for Catelli model Opensim 3.3
        members_dict = {}

        try:
            with open(xml_path, 'r', encoding='utf-8') as file:
                tree = ET.parse(xml_path)
                root = tree.getroot()
        except Exception as e:
            print('Error parsing xml file: {}'.format(e))
            return members_dict
        
        if group_names == 'all':
            # Find all ObjectGroup names
            group_names = [group.attrib['name'] for group in root.findall(".//ObjectGroup")]


        members_dict['all_selected'] = []
        for group_name in group_names:
            members = []
            for group in root.findall(".//ObjectGroup[@name='{}']".format(group_name)):
                members_str = group.find('members').text
                members.extend(members_str.split())
            
            members_dict[group_name] = members
            members_dict['all_selected'] = members_dict['all_selected'] + members 

        return members_dict

    def increase_max_isometric_force(model_path, factor): # opensim API
        # Load the OpenSim model
        model = osim.Model(model_path)

        # Loop through muscles and update their maximum isometric force
        for muscle in model.getMuscles():
            current_max_force = muscle.getMaxIsometricForce()
            new_max_force = current_max_force * factor
            muscle.setMaxIsometricForce(new_max_force)

        # Save the modified model
        output_model_path = model_path.replace('.osim', f'_increased_force_{factor}.osim')
        model.printToXML(output_model_path)

        print(f'Model with increased forces saved to: {output_model_path}')

    def update_max_isometric_force_xml(xml_file, factor,output_file = ''): # xml
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find all Millard2012EquilibriumMuscle elements
        muscles = root.findall('.//Millard2012EquilibriumMuscle')

        # Update max_isometric_force for each muscle
        n = 0
        for muscle in muscles:
            max_force_element = muscle.find('./max_isometric_force')
            if max_force_element is not None:
                current_max_force = float(max_force_element.text)
                new_max_force = current_max_force * factor
                max_force_element.text = str(new_max_force)
                n = 1
        if n == 0:
            print('No Millard2012EquilibriumMuscle elements found in the XML file.')
            
        # Save the modified XML file
        if not output_file:
            output_xml_file = xml_file.replace('.xml', f'_updated.xml')
        else:
            output_xml_file = output_file
            
        tree.write(output_xml_file)

        print(f'Modified XML saved to: {output_xml_file}')
        
    def reorder_markers(xml_path, order):
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Create a dictionary to store marker elements by name
        # markers_dict = {marker.find('name').text: marker for marker in root.findall('.//Marker')}

        # Create a new MarkerSet element to replace the existing one
        new_marker_set = ET.Element('MarkerSet')
        # Create the 'objects' element
        objects_element = ET.SubElement(new_marker_set, 'objects')    
        groups_element = ET.SubElement(new_marker_set, 'groups')    

        # Add Marker elements to the new MarkerSet in the specified order
        for marker_name in order:
            existing_marker = root.find('.//Marker[@name="' + marker_name + '"]')
            if existing_marker:
                objects_element.append(existing_marker)

        # Replace the existing MarkerSet with the new one
        existing_marker_set = root.find('.//MarkerSet')
        existing_marker_set.clear()
        existing_marker_set.extend(new_marker_set)

        # Save the modified XML back to a file
        tree.write(xml_path)

    def copy_marker_locations(model_path1,model_path2,marker_names='all',marker_common_frame='RASI'):
        '''
        This function copies the location of markers from model2 to model1. 
        The location of the marker in model1 is changed to the location of the marker in model2 
        in the frame of the common marker. 
        The location of the marker in model1 is changed back to the original parent frame. 
        The model with the changed marker locations is saved as a new model.
        '''
        # Load the OpenSim model
        model1 = msk.osim.Model(model_path1)
        model1_version = model1.version
        model1_xml = model1.xml
        model1 = model1.osim_object
        markerset1 = model1.get_MarkerSet()
        state1 = model1.initSystem()

        model2 = osim.Model(model_path2)
        markerset2 = model2.get_MarkerSet()
        state2 = model2.initSystem()
        
        # if marker_names == 'all' then use all markers in model1
        if marker_names == 'all':
            marker_names = [markerset1.get(i).getName() for i in range(markerset1.getSize())]

        if marker_common_frame not in marker_names:
            raise ValueError('The marker_common_frame must be included in marker_names')

        # Loop through muscles and update their maximum isometric force
        for marker_name in marker_names:

            try:
                if markerset1.contains(marker_name):
                    marker1 = dict()
                    marker2 = dict()
                    
                    # get marker objects
                    marker1['marker'] = markerset1.get(marker_name)
                    marker2['marker'] = markerset2.get(marker_name)

                    # get location of markers
                    marker1['location'] = list(marker1['marker'].get_location().to_numpy())           
                    marker2['location'] = list(marker2['marker'].get_location().to_numpy())

                    # get parent frame of markers            
                    marker1['parent_frame'] = marker1['marker'].getParentFrame()
                    marker2['parent_frame'] = marker2['marker'].getParentFrame()

                    # get pelvis frame from marker_common_frame marker
                    marker1['pelvis_frame'] = markerset1.get(marker_common_frame).getParentFrame()
                    marker2['pelvis_frame'] = markerset2.get(marker_common_frame).getParentFrame()
                    
                    # get location of marker 2 in pelvis frame
                    marker2['marker'].changeFramePreserveLocation(state2,marker2['pelvis_frame'])
                    marker2['location_in_pelvis'] = marker2['marker'].get_location()
                    
                    # change location of marker 1 to marker 2 in pelvis frame
                    marker1['marker'].changeFramePreserveLocation(state1,marker1['pelvis_frame'])
                    marker1['marker'].set_location(marker2['location_in_pelvis'])

                    # change marker 1 back to original parent frame
                    marker1['marker'].changeFramePreserveLocation(state1,marker1['parent_frame'])
                    marker1['location'] = list(marker1['marker'].get_location().to_numpy())  

                    # if orginal model is 3.3 change the 
                    if int(model1_version[0]) == 3:
                        model1_xml.getroot().find('.//Marker[@name="' + marker_name + '"]/location').text = ' '.join(map(str, marker1['location']))

                    print(f'Location of marker {marker_name} changed')
            except Exception as e:
                print(f'Error changing location of marker {marker_name}: {e}')


        # Save the modified model
        if int(model1_version[0]) == 3:
            output_model_path = model_path1.replace('.osim', '_new.osim')
            model1_xml.write(model_path1.replace('.osim', '_new.osim'))
            print(f'Model saved to: {model_path1}')
        else:    
            output_model_path = model_path1.replace('.osim', '_new.osim')
            model1.printToXML(output_model_path)
            print(f'Model saved to: {output_model_path}')

    # Operations    
    def sum_body_mass(model_path):
        '''
        This function sums the body mass of the model
        '''
        # Load the OpenSim model
        model = model(model_path)
        mass = 0
        for i in range(model.osim_object.getBodySet().getSize()):
            mass += model.osim_object.getBodySet().get(i).getMass()
        print(f'The total mass of the model is: {mass} kg')
        return mass       

class TrialSimple:
    def __init__(self,path):
        self.path = path    
        if not os.path.isfile(path):
            print(f"Error not found: {path}")
            
        else:
            print(f"Loading: {path}")
            
            if path.__contains__('angles.csv'):
                self.angles = msk.bops.import_file(path)
                
            elif path.__contains__('muscle_forces.sto'):
                new_path = path.replace('.sto','.csv')
                msk.bops.shutil.copy(path,new_path)
                self.muscleForces = msk.bops.import_file(new_path)
                # remove time offset and time normalise
                self.muscleForces['time'] = self.muscleForces['time'] - self.muscleForces['time'][0]
                muscleForces_timeNorm = msk.bops.time_normalise_df(self.muscleForces)
                muscleForces_timeNorm.to_csv(new_path.replace('.csv','_normalised.csv'), index=False)
                
            elif path.__contains__('muscle_forces.csv'):
                self.muscleForces = msk.bops.import_file(path)
                
            elif path.__contains__('joint_loads.csv'):
                self.jointLoads = msk.bops.import_file(path)

class Task:
    # For each task, create a class that contains the Trial objects
    # check example folder structure: C:\Project\Subject\Task\Trial
    def __init__(self, taskPath):
        self.path = taskPath
        self.folders = os.listdir(taskPath)
        
        for folder in self.folders:
            folderPath = os.path.join(taskPath, folder)
            self.__dict__[folder] = msk.Trial(folderPath)
            self.trials = self.__dict__.keys()
            
class SubjectSimple:
    # For each subject, create a class that contains the Task objects
    # check example folder structure: C:\Project\Subject\Task\Trial
    def __init__(self, path):
        self.path = path
        self.tasks = os.listdir(path)
        
        for task in self.tasks:
            taskPath = os.path.join(path, task)
            if os.path.isdir(taskPath):
                self.__dict__[task] = msk.Task(taskPath)
        
class Project:
    # For each project, create a class that contains the Subject objects
    # check example folder structure: C:\Project\Subject\Task\Trial
    def __init__(self, projectPath):
        self.path = projectPath
        self.dataPath = os.path.join(projectPath, 'Data')
        
        msk.bops.create_folder(self.dataPath)
        
        self.subjects = []
        
        for subject in os.listdir(self.dataPath):
            subjectPath = os.path.join(self.dataPath, subject)
            if os.path.isdir(subjectPath):
                self.__dict__[subject] = msk.Subject(subjectPath)    
                self.subjects.append(subject)
    

def isTrial(var):
    return isinstance(var, msk.Trial)

def isTask(var):
    return isinstance(var, msk.Task)

def isSubject(var):
    return isinstance(var, msk.Subject)

def isProject(var):
    return isinstance(var, msk.Project)
    
        
#%% END