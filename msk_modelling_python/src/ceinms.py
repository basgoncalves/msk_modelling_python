import os
import pandas as pd
import json
import c3d
import numpy as np
import xml.etree.ElementTree as ET
import xml.dom.minidom
import opensim as osim


MARKERS = "markers_experimental.trc"
GRF = "grf.mot"
EMG = "emg.mot"
IK = "joint_angles.mot"
ID = "joint_moments.sto"
MUSCLE_FORCES = "muscle_forces.sto"
MUSCLE_ACTIVATIONS = "muscle_activations.sto"
JRA = "joint_reaction_loads.sto"
CEINMS = "ceinms"

def import_json(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

class XMLTools:
    """
    A class to load and create XML files for OpenSim and CEINMS.
    usage:
    xml_tool = XMLTools()
    tree = xml_tool.load("example.xml")
    ...
    """
    def __init__(self,xml_file=None):
        try:
            self.tree = ET.parse(xml_file)
        except Exception as e:
            print(f"Error loading XML file: {e}")
            self.tree = None
        
        self.osim_model = None
    
    def load(self, xml_file):
        try:
            self.tree = ET.parse(xml_file)
            return self.tree
        except Exception as e:
            print(f"Error loading XML file: {e}")
            return None
    
    def save_pretty_xml(self, tree, save_path):
            """Saves the XML tree to a file with proper indentation."""
            # Convert to string and format with proper indents
            rough_string = ET.tostring(tree.getroot(), 'utf-8')
            reparsed = xml.dom.minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="   ")

            # Write to file
            with open(save_path, 'w') as file:
                file.write(pretty_xml)
    
    def dir_find_containing(self, var, name_to_find):
        for i in dir(var):
            if i.__contains__(name_to_find):
                print(f"Found {name_to_find} in {var.__class__.__name__}")
                return i
        
        print(f"Could not find {name_to_find} in {var.__class__.__name__}")
        return None
    
    class ceinms: 
        try:
            from msk_modelling_python import osim
        except:
            pass
        
        # Get data from OSIM model / xml
        
        def get_muscles_by_group_osim(self, model_path, group_names = 'all'):
            '''
            Function to get the muscle groups from the model and save them to a csv file. Also returns the muscle groups as a DataFrame.
            
            Example usage:
            model_path = r"C:\Git\research_data\Projects\runbops_FAIS_phd\models\009\009_Rajagopal2015_FAI_originalMass_opt_N10_hans.osim"
            group_names = ['hip_flex_r','hip_add_r','hip_inrot_r']
            muscles = get_muscles_by_group_osim(model_path, group_names)
            
            '''
            # Load the OpenSim model
            model = osim.Model(model_path)
            
            # Get the muscle groups from the model
            force_set = model.getForceSet()
            for i in range(forse_set.getSize()):
                group = force_set.getGroup(i)    
                
                # save place holder XML (at the moment cannot get the groups from the API)
                path = SCRIPT_DIR + '\groups.xml'
                group.printToXML(path)
                       
                # Parse the XML file to get the members of the group            
                root = ET.parse(path).getroot()
                child = root.find('ObjectGroup')
                list_of_members = child.find('members').text.split()
                members= []
                for member in list_of_members:
                            members.append(member.strip())
                
                # Add the group name and its members to the dictionary
                muscle_groups[group.getName()] = members
                
                # Delete xml file
                if os.path.exists(path):
                    os.remove(path)
            
            # Get the muscle groups from the model
            members_dict = self.get_muscle_groups_from_xml(force_set, group_names)
            
            return members_dict
        
        # Create CEINMS xmls
        def create_calibration_setup(self, save_path = None):
            root = ET.Element("ceinmsCalibration")
            
            subject_file = ET.SubElement(root, "subjectFile")
            subject_file.text = ".\\uncalibrated.xml"
            
            excitation_generator_file = ET.SubElement(root, "excitationGeneratorFile")
            excitation_generator_file.text = ".\\excitation_generator.xml"
            
            calibration_file = ET.SubElement(root, "calibrationFile")
            calibration_file.text = ".\\calibration_cfg.xml"
            
            output_subject_file = ET.SubElement(root, "outputSubjectFile")
            output_subject_file.text = ".\\calibratedSubject.xml"
            
            tree = ET.ElementTree(root)
            if save_path is not None:
                XMLTools().save_pretty_xml(tree, save_path)
                
            return tree

        def create_calibration_cfg(self, save_path=None, osimModelFile=None):

            if osimModelFile is not None:
                model = osim.Model(osimModelFile)
                coordinate_set = model.getCoordinateSet()
                muscles = model.getMuscles()
                muscle_groups = []
                for muscle in muscles:
                    muscle_groups.append(muscle.getName())
                    
                dofs = []
                for coordinate in coordinate_set:
                    dofs.append(coordinate.getName())
                
                dofs = ' '.join(dofs)
                
            else:
                print("\033[93mNo OpenSim model file provided. Muscle groups will be from template.\033[0m")
                print("\033[93mDOFs will be added from template\033[0m")
                
                muscle_groups = ["addbrev_r addlong_r addmagDist_r addmagIsch_r addmagMid_r addmagProx_r grac_r",
                    "bflh_r semimem_r semiten_r",
                    "bfsh_r",
                    "glmax1_r glmax2_r glmax3_r",
                    "glmed1_r glmed2_r glmed3_r",
                    "glmin1_r glmin2_r glmin3_r",
                    "sart_r recfem_r tfl_r",
                    "iliacus_r psoas_r",
                    "perbrev_r perlong_r tibant_r tibpost_r",
                    "edl_r ehl_r fdl_r fhl_r",
                    "soleus_r gaslat_r gasmed_r",
                    "vasint_r vaslat_r vasmed_r"]        

                dofs = "hip_flexion_r hip_adduction_r hip_rotation_r knee_angle_r ankle_angle_r"
            
            
            
            root = ET.Element("calibration", attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})
            
            algorithm = ET.SubElement(root, "algorithm")
            simulated_annealing = ET.SubElement(algorithm, "simulatedAnnealing")
            ET.SubElement(simulated_annealing, "noEpsilon").text = "4"
            ET.SubElement(simulated_annealing, "rt").text = "0.3"
            ET.SubElement(simulated_annealing, "T").text = "200000"
            ET.SubElement(simulated_annealing, "NS").text = "15"
            ET.SubElement(simulated_annealing, "NT").text = "5"
            ET.SubElement(simulated_annealing, "epsilon").text = "1.E-5"
            ET.SubElement(simulated_annealing, "maxNoEval").text = "200000"
            
            nms_model = ET.SubElement(root, "NMSmodel")
            model_type = ET.SubElement(nms_model, "type")
            ET.SubElement(model_type, "openLoop")
            tendon = ET.SubElement(nms_model, "tendon")
            ET.SubElement(tendon, "equilibriumElastic")
            activation = ET.SubElement(nms_model, "activation")
            ET.SubElement(activation, "exponential")
            
            calibration_steps = ET.SubElement(root, "calibrationSteps")
            step = ET.SubElement(calibration_steps, "step")
            ET.SubElement(step, "dofs").text = dofs
            
            objective_function = ET.SubElement(step, "objectiveFunction")
            torque_error_normalised = ET.SubElement(objective_function, "torqueErrorNormalised")
            ET.SubElement(torque_error_normalised, "targets").text = "all"
            ET.SubElement(torque_error_normalised, "weight").text = "1"
            ET.SubElement(torque_error_normalised, "exponent").text = "1"
            
            penalty = ET.SubElement(objective_function, "penalty")
            ET.SubElement(penalty, "targets").text = "all"
            ET.SubElement(penalty, "targetsType").text = "normalisedFibreLength"
            ET.SubElement(penalty, "weight").text = "100"
            ET.SubElement(penalty, "exponent").text = "2"
            ET.SubElement(penalty, "range").text = "0.6 1.4"
            
            parameter_set = ET.SubElement(step, "parameterSet")
                    
            parameters = [
                {"name": "c1", "range": "-0.95 -0.05"},
                {"name": "c2", "range": "-0.95 -0.05"},
                {"name": "shapeFactor", "range": "-2.999 -0.001"},
                {"name": "tendonSlackLength", "range": "0.85 1.15", "relative": True},
                {"name": "optimalFibreLength", "range": "0.85 1.15", "relative": True},
                {"name": "strengthCoefficient", "range": "0.8 2", "muscleGroups": muscle_groups}
            ]
            
            for param in parameters:
                parameter = ET.SubElement(parameter_set, "parameter")
                ET.SubElement(parameter, "name").text = param["name"]
                ET.SubElement(parameter, "single")
                if "relative" in param and param["relative"]:
                    relative = ET.SubElement(parameter, "relativeToSubjectValue")
                    ET.SubElement(relative, "range").text = param["range"]
                else:
                    absolute = ET.SubElement(parameter, "absolute")
                    ET.SubElement(absolute, "range").text = param["range"]
                if "muscleGroups" in param:
                    muscle_groups = ET.SubElement(parameter, "muscleGroups")
                    for muscles in param["muscleGroups"]:
                        ET.SubElement(muscle_groups, "muscles").text = muscles
            
            ET.SubElement(root, "trialSet").text = ".\\trial.xml"
            
            tree = ET.ElementTree(root)
            if save_path is not None:
                XMLTools().save_pretty_xml(tree=tree, save_path=save_path)
            
            return tree

        def create_subject_uncalibrated(self, save_path=None, osimModelFile=None):
            if osimModelFile == None:
                print("\033[93mNo OpenSim model not file provided. FAILED!!\033[0m")
                return None
            else:
                try:
                    model = msk.osim.Model(osimModelFile)
                    coordinate_set = model.getCoordinateSet()
                    muscles = model.getMuscles()
                except Exception as e:
                    print(f"Error loading OpenSim model: {e}")
                    return None
                
            root = ET.Element("subject", attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})
            
            mtu_default = ET.SubElement(root, "mtuDefault")
            ET.SubElement(mtu_default, "emDelay").text = "0.015"
            ET.SubElement(mtu_default, "percentageChange").text = "0.15"
            ET.SubElement(mtu_default, "damping").text = "0.1"
            
            curves = [
                {
                    "name": "activeForceLength",
                    "xPoints": "-5 0 0.401 0.402 0.4035 0.52725 0.62875 0.71875 0.86125 1.045 1.2175 1.4387 1.6187 1.62 1.621 2.2 5",
                    "yPoints": "0 0 0 0 0 0.22667 0.63667 0.85667 0.95 0.99333 0.77 0.24667 0 0 0 0 0"
                },
                {
                    "name": "passiveForceLength",
                    "xPoints": "-5 0.998 0.999 1 1.1 1.2 1.3 1.4 1.5 1.6 1.601 1.602 5",
                    "yPoints": "0 0 0 0 0.035 0.12 0.26 0.55 1.17 2 2 2 2"
                },
                {
                    "name": "forceVelocity",
                    "xPoints": "-10 -1 -0.6 -0.3 -0.1 0 0.1 0.3 0.6 0.8 10",
                    "yPoints": "0 0 0.08 0.2 0.55 1 1.4 1.6 1.7 1.75 1.75"
                },
                {
                    "name": "tendonForceStrain",
                    "xPoints": "0 0.001 0.002 0.003 0.004 0.005 0.006 0.007 0.008 0.009 0.01 0.011 0.012 0.013 0.014 0.015 0.016 0.017 0.018 0.019 0.02 0.021 0.022 0.023 0.024 0.025 0.026 0.027 0.028 0.029 0.03 0.031 0.032 0.033 0.034 0.035 0.036 0.037 0.038 0.039 0.04 0.041 0.042 0.043 0.044 0.045 0.046 0.047 0.048 0.049 0.05 0.051 0.052 0.053 0.054 0.055 0.056 0.057 0.058 0.059 0.06 0.061 0.062 0.063 0.064 0.065 0.066 0.067 0.068 0.069 0.07 0.071 0.072 0.073 0.074 0.075 0.076 0.077 0.078 0.079 0.08 0.081 0.082 0.083 0.084 0.085 0.086 0.087 0.088 0.089 0.09 0.091 0.092 0.093 0.094 0.095 0.096 0.097 0.098 0.099 0.1",
                    "yPoints": "0 0.0012652 0.0073169 0.016319 0.026613 0.037604 0.049078 0.060973 0.073315 0.086183 0.099678 0.11386 0.12864 0.14386 0.15928 0.17477 0.19041 0.20658 0.22365 0.24179 0.26094 0.28089 0.30148 0.32254 0.34399 0.36576 0.38783 0.41019 0.43287 0.45591 0.4794 0.50344 0.52818 0.55376 0.58022 0.60747 0.63525 0.66327 0.69133 0.71939 0.74745 0.77551 0.80357 0.83163 0.85969 0.88776 0.91582 0.94388 0.97194 1 1.0281 1.0561 1.0842 1.1122 1.1403 1.1684 1.1964 1.2245 1.2526 1.2806 1.3087 1.3367 1.3648 1.3929 1.4209 1.449 1.477 1.5051 1.5332 1.5612 1.5893 1.6173 1.6454 1.6735 1.7015 1.7296 1.7577 1.7857 1.8138 1.8418 1.8699 1.898 1.926 1.9541 1.9821 2.0102 2.0383 2.0663 2.0944 2.1224 2.1505 2.1786 2.2066 2.2347 2.2628 2.2908 2.3189 2.3469 2.375 2.4031 2.4311"
                }
            ]
            
            for curve in curves:
                curve_element = ET.SubElement(mtu_default, "curve")
                ET.SubElement(curve_element, "name").text = curve["name"]
                ET.SubElement(curve_element, "xPoints").text = curve["xPoints"]
                ET.SubElement(curve_element, "yPoints").text = curve["yPoints"]
            
            mtu_set = ET.SubElement(root, "mtuSet")
            
            try:
                mtus = []
                for muscle in muscles:
                    mtu = {
                        "name": muscle.getName(),
                        "c1": "-0.5",
                        "c2": "-0.5",
                        "shapeFactor": "0.1",
                        "optimalFibreLength": muscle.getOptimalFiberLength(),
                        "pennationAngle": muscle.getPennationAngleAtOptimalFiberLength(),
                        "tendonSlackLength": muscle.getTendonSlackLength(),
                        "tendonSlackLength": muscle.getTendonSlackLength(),
                        "maxIsometricForce": muscle.getMaxIsometricForce(),
                        "strengthCoefficient": "1"
                        }
                    mtus.append(mtu)
            except Exception as e:
                print(f"Error adding opensim muscles: {e}")
                return None
                            
            for mtu in mtus:
                mtu_element = ET.SubElement(mtu_set, "mtu")
                ET.SubElement(mtu_element, "name").text = mtu["name"]
                ET.SubElement(mtu_element, "c1").text = mtu["c1"]
                ET.SubElement(mtu_element, "c2").text = mtu["c2"]
                ET.SubElement(mtu_element, "shapeFactor").text = mtu["shapeFactor"]
                ET.SubElement(mtu_element, "optimalFibreLength").text = mtu["optimalFibreLength"]
                ET.SubElement(mtu_element, "pennationAngle").text = mtu["pennationAngle"]
                ET.SubElement(mtu_element, "tendonSlackLength").text = mtu["tendonSlackLength"]
                ET.SubElement(mtu_element, "maxIsometricForce").text = mtu["maxIsometricForce"]
                ET.SubElement(mtu_element, "strengthCoefficient").text = mtu["strengthCoefficient"]
            
            
            
            dof_set = ET.SubElement(root, "dofSet")
            
            import pdb; pdb.set_trace()
            dofs = []
            for coordinate in coordinate_set:
                dof = {
                    "name": coordinate.getName(),
                    "mtuNameSet": "addbrev_r addlong_r addmagDist_r addmagIsch_r addmagMid_r addmagProx_r grac_r"
                }
                dofs.append(dof)
            dofs = [
                {"name": "hip_flexion_r", "mtuNameSet": "addbrev_r addlong_r addmagDist_r addmagIsch_r addmagMid_r addmagProx_r bflh_r glmax1_r glmax2_r glmax3_r glmed1_r glmed2_r glmed3_r glmin1_r glmin2_r glmin3_r grac_r iliacus_r piri_r psoas_r recfem_r sart_r semimem_r semiten_r tfl_r"},
                {"name": "hip_adduction_r", "mtuNameSet": "addbrev_r addlong_r addmagDist_r addmagIsch_r addmagMid_r addmagProx_r bflh_r glmax1_r glmax2_r glmax3_r glmed1_r glmed2_r glmed3_r glmin1_r glmin2_r glmin3_r grac_r iliacus_r piri_r psoas_r recfem_r sart_r semimem_r semiten_r tfl_r"},
                # Add other DOFs here...
            ]
            
            for dof in dofs:
                dof_element = ET.SubElement(dof_set, "dof")
                ET.SubElement(dof_element, "name").text = dof["name"]
                ET.SubElement(dof_element, "mtuNameSet").text = dof["mtuNameSet"]
            
            calibration_info = ET.SubElement(root, "calibrationInfo")
            uncalibrated = ET.SubElement(calibration_info, "uncalibrated")
            ET.SubElement(uncalibrated, "subjectID").text = "9"
            ET.SubElement(uncalibrated, "additionalInfo").text = "TendonSlackLength and OptimalFibreLength scaled with Winby-Modenese"
            
            ET.SubElement(root, "contactModelFile").text = ".\\contact_model.xml"
            ET.SubElement(root, "opensimModelFile").text = "..\\rajagopal_scaled.osim"
            
            tree = ET.ElementTree(root)
            if save_path is not None:
                self.save_pretty_xml(tree, save_path)
            
            return tree

class File:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.extension = os.path.splitext(path)[1]
        
        if not os.path.isfile(path):
            print(f"\033[93mFile not found: {path}\033[0m")
            return        
        
        try:
            endheader_line = self.find_file_endheader_line(path)
        except:
            print(f"Error finding endheader line for file: {path}")
            endheader_line = 0
        # Read file based on extension
        try:
            if self.extension == '.csv':
                self.data = pd.read_csv(path)
            elif self.extension == '.json':
                self.data = import_json(path)
            elif self.extension == '.xml':
                self.data = XMLTools.load(path)
            else:
                try:
                    self.data = pd.read_csv(path, sep="\t", skiprows=endheader_line)
                except:
                    self.data = None
                    
            # add time range for the data
            try:
                self.time_range = [self.data['time'].iloc[0], self.data['time'].iloc[-1]]
                try:
                    self.time_range = [self.data['Time'].iloc[0], self.data['Time'].iloc[-1]]
                except:
                    pass
            except:
                self.time_range = None
        
        except Exception as e:
            print(f"Error reading file: {path}")
            print(e)
            self.data = None
            self.time_range = None
    def find_file_endheader_line(self, path):
        with open(path, 'r') as file:
            for i, line in enumerate(file):
                if 'endheader' in line:
                    return i + 1
        return 0    
    
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
        self.name = os.path.basename(self.path)
        self.subject = os.path.basename(os.path.dirname(self.path))
        self.c3d = os.path.join(os.path.dirname(self.path), self.name + '.c3d')
        self.markers = File(os.path.join(self.path, MARKERS))
        self.grf = File(os.path.join(self.path, GRF))
        self.emg_csv = File(os.path.join(self.path, EMG.replace('mot','csv')))
        self.emg = File(os.path.join(self.path,EMG))
        self.ik = File(os.path.join(self.path,IK))
        self.id = File(os.path.join(self.path,ID))
        self.so_force = File(os.path.join(self.path, MUSCLE_FORCES))
        self.so_activation = File(os.path.join(self.path, MUSCLE_ACTIVATIONS))
        self.jra = File(os.path.join(self.path,JRA))
        
        # load muscle analysis files
        self.ma_targets = ['_MomentArm_', '_Length.sto']
        self.ma_files = []
        try:
            files = os.listdir(os.path.join(self.path, 'Results_SO_and_MA'))
            for file in files:
                if file.__contains__(self.ma_targets[0]) or file.__contains__(self.ma_targets[1]):
                    self.ma_files.append(File(os.path.join(self.path, 'Results_SO_and_MA', file)))
        except:
            self.ma_files = None
                    
        # settings files
        self.grf_xml = File(os.path.join(self.path,'GRF_Setup.xml'))
        self.actuators_so = File(os.path.join(self.path,'actuators_SO.xml'))
        
        self.settings_json = File(os.path.join(self.path,'settings.json'))
        
        # CEINMS files
        self.ceinms_cal_setup = File(os.path.join(self.path,'ceinms','calibrationSetup.xml'))
        self.ceinms_cal_cfg = File(os.path.join(self.path,'ceinms','calibrationCfg.xml'))
        self.ceinms_trial = File(os.path.join(self.path,'ceinms','trial.xml'))
        self.ceinms_uncalibrated_subject = File(os.path.join(self.path,'ceinms','uncalibratedSubject.xml'))
        self.ceinms_excitation_generator = File(os.path.join(self.path,'ceinms','excitationGenerator.xml'))
        self.ceinms_execution_setup = File(os.path.join(self.path, 'ceinms', 'executionSetup.xml'))
        self.ceinms_execution_cfg = File(os.path.join(self.path, 'ceinms', 'executionCfg.xml'))
                              
    def check_files(self):
        '''
        Output: True if all files exist, False if any file is missing
        '''
        files = self.__dict__.values()
        all_files_exist = True
        for file in files:
            try:
                if not os.path.isfile(file):
                    print('File not found: ' + file)
                    all_files_exist = False
            except:
                pass
        return all_files_exist
    
    def header_mot(self,df,name):

            num_rows = len(df)
            num_cols = len(df.columns) 
            inital_time = df['Time'].iloc[0]
            final_time = df['Time'].iloc[-1]
            df_range = f'{inital_time}  {final_time}'


            return f'name {name}\n datacolumns {num_cols}\n datarows {num_rows}\n range {df_range} \n endheader'
        
    def csv_to_mot(self):
        
        emg_data = msk.bops.pd.read_csv(self.emg_csv)

        fs = int(1/(emg_data['time'][1] - emg_data['time'][0]))

        time = emg_data['time']

        # start time from new time point
        start_time = time.iloc[0]
        end_time = time.iloc[-1] - time.iloc[0] + start_time

        num_samples = len(emg_data)
        #num_samples = int((end_time - start_time) / (1/fs))
        new_time = np.linspace(start_time, end_time, num_samples)

        emg_data['time'] = new_time

        # Define a new file path 
        new_file_path = os.path.join(self.emg_csv.replace('.csv', '.mot'))

        # Save the modified DataFrame
        emg_data.to_csv(new_file_path, index=False)  # index=False prevents adding an extra index column

        # save to mot
        header = self.header_mot(emg_data, "processed_emg_signals")

        mot_path = new_file_path.replace('.csv','.mot')
        with open(mot_path, 'w') as f:
            f.write(header + '\n')  
            # print column names 
            f.write('\t'.join(map(str, emg_data.columns)) + '\n')
            for index, row in emg_data.iterrows():
                f.write('\t'.join(map(str, row.values)) + '\n')  
        
        print(f"File saved: {mot_path}")

    def create_settings_json(self, overwrite=False):
        if os.path.isfile(self.settings_json) and not overwrite:
            print('settings.json already exists')
            return
        
        settings_dict = self.__dict__
        msk.bops.save_json_file(settings_dict, self.settings_json)
        print('trial settings.json created in ' + self.path)
    
    def exportC3D(self):
        msk.bops.c3d_osim_export(self.og_c3d) 

    def change_grf_xml_path(self):

        try:
            self.tree = ET.parse(self.grf_xml.path)
            self.root = self.tree.getroot()
            self.root.find('.//datafile').text = self.grf.path
            
            self.tree.write(self.grf_xml.path)
            
            print(f"GRF file path updated in {self.grf_xml.path}")
        except Exception as e:
            print(f"Error loading XML file: {e}")
            return None

    def save_json_file(self, data, jsonFilePath):
        data = data.__dict__

        with open(jsonFilePath, 'w') as f:
            msk.bops.json.dump(data, f, indent=4)

        json_data = import_json(jsonFilePath)
        return json_data
    
    def to_json(self):
        msk.bops.save_json_file(self.__dict__, jsonFilePath = self.settings_json)
        print('settings.json created in ' + self.settings_json)
    
    def run_IK(osim_modelPath, trc_file, resultsDir):
        '''
        Function to run Inverse Kinematics using the OpenSim API.
        
        Inputs:
                osim_modelPath(str): path to the OpenSim model file
                trc_file(str): path to the TRC file
                resultsDir(str): path to the directory where the results will be saved
        '''

        # Load the TRC file
        import pdb; pdb.set_trace()
        tuple_data = msk.bops.import_trc_file(trc_file)
        df = pd.DataFrame.from_records(tuple_data, columns=[x[0] for x in tuple_data])
        column_names = [x[0] for x in tuple_data]
        if len(set(column_names)) != len(column_names):
            print("Error: Duplicate column names found.")
        # Load the model
        osimModel = osim.Model(osim_modelPath)                              
        state = osimModel.initSystem()

        # Define the time range for the analysis
        
        initialTime = msk.TRCData.getIndependentColumn()
        finalTime = msk.TRCData.getLastTime()

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

    def run_ID(self, osim_modelPath, coordinates_file, external_loads_file, output_file, LowpassCutoffFrequency=6, run_tool=True):
        
        try: 
            model = osim.Model(osim_modelPath)
        except Exception as e:
            print(f"Error loading model: {osim_modelPath}")
            print(e)
            return
        
        results_folder = os.path.dirname(output_file)
        
        # Setup for excluding muscles from ID
        exclude = osim.ArrayStr()
        exclude.append("Muscles")
        # Setup for setting time range
        IKData = osim.Storage(coordinates_file)

        # Create inverse dynamics tool, set parameters and run
        id_tool = osim.InverseDynamicsTool()
        id_tool.setModel(model)
        id_tool.setCoordinatesFileName(coordinates_file)
        id_tool.setExternalLoadsFileName(external_loads_file)
        id_tool.setOutputGenForceFileName(output_file)
        id_tool.setLowpassCutoffFrequency(LowpassCutoffFrequency)
        id_tool.setStartTime(IKData.getFirstTime())
        id_tool.setEndTime(IKData.getLastTime())
        id_tool.setExcludedForces(exclude)
        id_tool.setResultsDir(results_folder)
        id_tool.printToXML(os.path.join(results_folder, "setup_ID.xml"))
        
        if run_tool:
            id_tool.run()
    

    # CREATE CEINMS XML files
    def create_calibration_setup(self, save_path = None):
            root = ET.Element("ceinmsCalibration")
            
            subject_file = ET.SubElement(root, "subjectFile")
            subject_file.text = ".\\uncalibratedSubject.xml"
            
            excitation_generator_file = ET.SubElement(root, "excitationGeneratorFile")
            excitation_generator_file.text = ".\\excitationGenerator.xml"
            
            calibration_file = ET.SubElement(root, "calibrationFile")
            calibration_file.text = ".\\calibrationCfg.xml"
            
            output_subject_file = ET.SubElement(root, "outputSubjectFile")
            output_subject_file.text = ".\\calibratedSubject.xml"
            
            tree = ET.ElementTree(root)
            if save_path is not None:
                save_pretty_xml(tree, save_path)
                print(f"XML file created at: {save_path}")
                
            return tree

    def create_calibration_cfg(self, save_path=None, osimModelFile=None, leg='r'):

        if leg not in ['r', 'l']:
            raise ValueError("Leg must be 'r' or 'l'")

        
                
        dofs = [f"hip_flexion_{leg}", f"knee_angle_{leg}", f"ankle_angle_{leg}"]

        # muscle_groups = [
        #     f"addbrev_{leg} addlong_{leg} addmagDist_{leg} addmagIsch_{leg} addmagMid_{leg} addmagProx_{leg} grac_{leg}",
        #     f"bflh_{leg} semimem_{leg} semiten_{leg}",
        #     f"bfsh_{leg}",
        #     f"glmax1_{leg} glmax2_{leg} glmax3_{leg}",
        #     f"glmed1_{leg} glmed2_{leg} glmed3_{leg}",
        #     f"glmin1_{leg} glmin2_{leg} glmin3_{leg}",
        #     f"sart_{leg} recfem_{leg} tfl_{leg}",
        #     f"iliacus_{leg} psoas_{leg}",
        #     f"perbrev_{leg} perlong_{leg} tibant_{leg} tibpost_{leg}",
        #     f"edl_{leg} ehl_{leg} fdl_{leg} fhl_{leg}",
        #     f"soleus_{leg} gaslat_{leg} gasmed_{leg}",
        #     f"vasint_{leg} vaslat_{leg} vasmed_{leg}",
        #     f"quad_fem_{leg} gem_{leg} peri_{leg} per_tert_{leg} ercspn_{leg} intobl_{leg} extobl_{leg}"
        # ]  
    

        root = ET.Element("calibration", attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})
        
        algorithm = ET.SubElement(root, "algorithm")
        simulated_annealing = ET.SubElement(algorithm, "simulatedAnnealing")
        ET.SubElement(simulated_annealing, "noEpsilon").text = "4"
        ET.SubElement(simulated_annealing, "rt").text = "0.3"
        ET.SubElement(simulated_annealing, "T").text = "200000"
        ET.SubElement(simulated_annealing, "NS").text = "15"
        ET.SubElement(simulated_annealing, "NT").text = "5"
        ET.SubElement(simulated_annealing, "epsilon").text = "1.E-5"
        ET.SubElement(simulated_annealing, "maxNoEval").text = "200000"
        
        nms_model = ET.SubElement(root, "NMSmodel")
        model_type = ET.SubElement(nms_model, "type")
        ET.SubElement(model_type, "openLoop")
        tendon = ET.SubElement(nms_model, "tendon")
        ET.SubElement(tendon, "equilibriumElastic")
        activation = ET.SubElement(nms_model, "activation")
        ET.SubElement(activation, "exponential")
        
        calibration_steps = ET.SubElement(root, "calibrationSteps")
        step = ET.SubElement(calibration_steps, "step")
        ET.SubElement(step, "dofs").text = " ".join(dofs)
        
        objective_function = ET.SubElement(step, "objectiveFunction")
        torque_error_normalised = ET.SubElement(objective_function, "torqueErrorNormalised")
        ET.SubElement(torque_error_normalised, "targets").text = "all"
        ET.SubElement(torque_error_normalised, "weight").text = "1"
        ET.SubElement(torque_error_normalised, "exponent").text = "1"
        
        penalty = ET.SubElement(objective_function, "penalty")
        ET.SubElement(penalty, "targets").text = "all"
        ET.SubElement(penalty, "targetsType").text = "normalisedFibreLength"
        ET.SubElement(penalty, "weight").text = "100"
        ET.SubElement(penalty, "exponent").text = "2"
        ET.SubElement(penalty, "range").text = "0.6 1.4"
        
        parameter_set = ET.SubElement(step, "parameterSet")
            
        parameters = [
            {"name": "c1", "range": "-0.95 -0.05"},
            {"name": "c2", "range": "-0.95 -0.05"},
            {"name": "shapeFactor", "range": "-2.999 -0.001"},
            {"name": "tendonSlackLength", "range": "0.85 1.15", "relative": True},
            {"name": "optimalFibreLength", "range": "0.85 1.15", "relative": True},
            {"name": "strengthCoefficient", "range": "0.8 2"}
        ]
        
        for param in parameters:
            parameter = ET.SubElement(parameter_set, "parameter")
            ET.SubElement(parameter, "name").text = param["name"]
            
            # Check if this parameter has a muscle group
            if "muscleGroups" in param:
                muscle_groups = ET.SubElement(parameter, "muscleGroups")
                for muscle in param["muscleGroups"]:
                    ET.SubElement(muscle_groups, "muscles").text = muscle
            else:
                # If no muscle group, assume it's a single muscle parameter
                ET.SubElement(parameter, "single")


            if "relative" in param and param["relative"]:
                relative = ET.SubElement(parameter, "relativeToSubjectValue")
                ET.SubElement(relative, "range").text = param["range"]
            else:
                absolute = ET.SubElement(parameter, "absolute")
                ET.SubElement(absolute, "range").text = param["range"]
           
        
        ET.SubElement(root, "trialSet").text = ".\\trial.xml"
        
        tree = ET.ElementTree(root)
        if save_path is not None:
            save_pretty_xml(tree, save_path)
            print(f"XML file created at: {save_path}")
        
        return tree

    def create_ceinms_trial_xml(self, savepath = None):
        root = ET.Element("inputData")

        muscle_tendon_length_file = ET.SubElement(root, "muscleTendonLengthFile")
        muscle_tendon_length_file.text = f"../Results_SO_and_MA/MuscleAnalysis_Length.sto"

        excitations_file = ET.SubElement(root, "excitationsFile")
        excitations_file.text = "../processed_emg_signals.mot"

        moment_arms_files = ET.SubElement(root, "momentArmsFiles")
        moment_arms_file_ankle_l = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="ankle_angle_l")
        moment_arms_file_ankle_l.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_ankle_angle_l.sto"
        moment_arms_file_ankle_r = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="ankle_angle_r")
        moment_arms_file_ankle_r.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_ankle_angle_r.sto"
        moment_arms_file_hip_adduction_l = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_adduction_l")
        moment_arms_file_hip_adduction_l.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_adduction_l.sto"
        moment_arms_file_hip_adduction_r = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_adduction_r")
        moment_arms_file_hip_adduction_r.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_adduction_r.sto"
        moment_arms_file_hip_flexion_l = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_flexion_l")
        moment_arms_file_hip_flexion_l.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_flexion_l.sto"
        moment_arms_file_hip_flexion_r = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_flexion_r")
        moment_arms_file_hip_flexion_r.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_flexion_r.sto"
        moment_arms_file_hip_rotation_l = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_rotation_l")
        moment_arms_file_hip_rotation_l.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_rotation_l.sto"
        moment_arms_file_hip_rotation_r = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="hip_rotation_r")
        moment_arms_file_hip_rotation_r.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_hip_rotation_r.sto"
        moment_arms_file_knee_l = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="knee_angle_l")
        moment_arms_file_knee_l.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_knee_angle_l.sto"
        moment_arms_file_knee_r = ET.SubElement(moment_arms_files, "momentArmsFile", dofName="knee_angle_r")
        moment_arms_file_knee_r.text = "../Results_SO_and_MA/MuscleAnalysis_MomentArm_knee_angle_r.sto"

        external_torques_file = ET.SubElement(root, "externalTorquesFile")
        external_torques_file.text = "../inverse_dynamics.sto"

        external_loads_file = ET.SubElement(root, "externalLoadsFile")
        external_loads_file.text = "../GRF_Setup.xml"

        motion_file = ET.SubElement(root, "motionFile")
        motion_file.text = "../Visual3d_SIMM_input.mot"

        start_stop_time = ET.SubElement(root, "startStopTime")

        inverse_dynamics_file = os.path.join(self.path, 'inverse_dynamics.sto')
        if os.path.isfile(inverse_dynamics_file):
            with open(inverse_dynamics_file, 'r') as f:
                lines = f.readlines()

            # Find where the header ends
            for i, line in enumerate(lines):
                if line.strip() == 'endheader':
                    header_end_index = i
                    break
            else:
                print("Error: 'endheader' not found in file.")
                header_end_index = None

            if header_end_index is not None:
                # Read data into pandas
                from io import StringIO
                data_str = ''.join(lines[header_end_index + 1:])  # includes column names and data
                df = pd.read_csv(StringIO(data_str), delim_whitespace=True)

                if 'time' in df.columns:
                    start_time = df['time'].iloc[0]
                    end_time = df['time'].iloc[-1]
                    start_stop_time.text = f"{start_time} {end_time}"
                else:
                    print("Error: 'time' column not found in inverse_dynamics.sto")
        else:
            print("Error: File inverse_dynamics.sto not found")

        tree = ET.ElementTree(root)
        if savepath is not None:
            save_pretty_xml(tree, savepath)
            print(f"XML file created at: {savepath}")

    def create_subject_uncalibrated(self, save_path=None, osimModelFile=None, leg='r'):
        if osimModelFile == None:
            print("\033[93mNo OpenSim model not file provided. FAILED!!\033[0m")
            return None
        else:
            try:
                model = osim.Model(osimModelFile)
                coordinate_set = model.getCoordinateSet()
                muscles = model.getMuscles() # ForceSet
            except Exception as e:
                print(f"Error loading OpenSim model: {e}")
                return None
        
        osim_model_file_name = os.path.basename(osimModelFile) 
        root = ET.Element("subject", attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})
        
        mtu_default = ET.SubElement(root, "mtuDefault")
        ET.SubElement(mtu_default, "emDelay").text = "0.015"
        ET.SubElement(mtu_default, "percentageChange").text = "0.15"
        ET.SubElement(mtu_default, "damping").text = "0.1"
        
        curves = [
            {
                "name": "activeForceLength",
                "xPoints": "-5 0 0.401 0.402 0.4035 0.52725 0.62875 0.71875 0.86125 1.045 1.2175 1.4387 1.6187 1.62 1.621 2.2 5",
                "yPoints": "0 0 0 0 0 0.22667 0.63667 0.85667 0.95 0.99333 0.77 0.24667 0 0 0 0 0"
            },
            {
                "name": "passiveForceLength",
                "xPoints": "-5 0.998 0.999 1 1.1 1.2 1.3 1.4 1.5 1.6 1.601 1.602 5",
                "yPoints": "0 0 0 0 0.035 0.12 0.26 0.55 1.17 2 2 2 2"
            },
            {
                "name": "forceVelocity",
                "xPoints": "-10 -1 -0.6 -0.3 -0.1 0 0.1 0.3 0.6 0.8 10",
                "yPoints": "0 0 0.08 0.2 0.55 1 1.4 1.6 1.7 1.75 1.75"
            },
            {
                "name": "tendonForceStrain",
                "xPoints": "0 0.001 0.002 0.003 0.004 0.005 0.006 0.007 0.008 0.009 0.01 0.011 0.012 0.013 0.014 0.015 0.016 0.017 0.018 0.019 0.02 0.021 0.022 0.023 0.024 0.025 0.026 0.027 0.028 0.029 0.03 0.031 0.032 0.033 0.034 0.035 0.036 0.037 0.038 0.039 0.04 0.041 0.042 0.043 0.044 0.045 0.046 0.047 0.048 0.049 0.05 0.051 0.052 0.053 0.054 0.055 0.056 0.057 0.058 0.059 0.06 0.061 0.062 0.063 0.064 0.065 0.066 0.067 0.068 0.069 0.07 0.071 0.072 0.073 0.074 0.075 0.076 0.077 0.078 0.079 0.08 0.081 0.082 0.083 0.084 0.085 0.086 0.087 0.088 0.089 0.09 0.091 0.092 0.093 0.094 0.095 0.096 0.097 0.098 0.099 0.1",
                "yPoints": "0 0.0012652 0.0073169 0.016319 0.026613 0.037604 0.049078 0.060973 0.073315 0.086183 0.099678 0.11386 0.12864 0.14386 0.15928 0.17477 0.19041 0.20658 0.22365 0.24179 0.26094 0.28089 0.30148 0.32254 0.34399 0.36576 0.38783 0.41019 0.43287 0.45591 0.4794 0.50344 0.52818 0.55376 0.58022 0.60747 0.63525 0.66327 0.69133 0.71939 0.74745 0.77551 0.80357 0.83163 0.85969 0.88776 0.91582 0.94388 0.97194 1 1.0281 1.0561 1.0842 1.1122 1.1403 1.1684 1.1964 1.2245 1.2526 1.2806 1.3087 1.3367 1.3648 1.3929 1.4209 1.449 1.477 1.5051 1.5332 1.5612 1.5893 1.6173 1.6454 1.6735 1.7015 1.7296 1.7577 1.7857 1.8138 1.8418 1.8699 1.898 1.926 1.9541 1.9821 2.0102 2.0383 2.0663 2.0944 2.1224 2.1505 2.1786 2.2066 2.2347 2.2628 2.2908 2.3189 2.3469 2.375 2.4031 2.4311"
            }
        ]
        
        for curve in curves:
            curve_element = ET.SubElement(mtu_default, "curve")
            ET.SubElement(curve_element, "name").text = curve["name"]
            ET.SubElement(curve_element, "xPoints").text = curve["xPoints"]
            ET.SubElement(curve_element, "yPoints").text = curve["yPoints"]
        
        mtu_set = ET.SubElement(root, "mtuSet")
        try:
            mtus = []
            for muscle in muscles:
                if self.subject.startswith('PC'):
                    ofl = muscle.getOptimalFiberLength() * 0.7  # Adjust for CP children Rabbi, M. F. et al. -2024- Biomech. Model. Mechanobiol. 23, 1077–1090
                else:
                    ofl = muscle.getOptimalFiberLength()

                mtu = {
                    "name": muscle.getName(),
                    "c1": "-0.5",
                    "c2": "-0.5",
                    "shapeFactor": "0.1",
                    "optimalFibreLength": str(ofl),
                    "pennationAngle": str(muscle.getPennationAngleAtOptimalFiberLength()),
                    "tendonSlackLength": str(muscle.getTendonSlackLength()),
                    "maxIsometricForce": str(muscle.getMaxIsometricForce()),
                    "strengthCoefficient": "1"
                }
                mtus.append(mtu)
        except Exception as e:
            print(f"Error adding OpenSim muscles: {e}")
            return None
                        
        for mtu in mtus:
            mtu_element = ET.SubElement(mtu_set, "mtu")
            ET.SubElement(mtu_element, "name").text = mtu["name"]
            ET.SubElement(mtu_element, "c1").text = mtu["c1"]
            ET.SubElement(mtu_element, "c2").text = mtu["c2"]
            ET.SubElement(mtu_element, "shapeFactor").text = mtu["shapeFactor"]
            ET.SubElement(mtu_element, "optimalFibreLength").text = mtu["optimalFibreLength"]
            ET.SubElement(mtu_element, "pennationAngle").text = mtu["pennationAngle"]
            ET.SubElement(mtu_element, "tendonSlackLength").text = mtu["tendonSlackLength"]
            ET.SubElement(mtu_element, "maxIsometricForce").text = mtu["maxIsometricForce"]
            ET.SubElement(mtu_element, "strengthCoefficient").text = mtu["strengthCoefficient"]
        
        
        
        dof_set = ET.SubElement(root, "dofSet")

        dofs = [
            {"name": f"hip_adduction_{leg}", 
             "mtuNameSet": f"add_brev_{leg} add_long_{leg} add_mag1_{leg} add_mag2_{leg} add_mag3_{leg} bifemlh_{leg} grac_{leg} pect_{leg} semimem_{leg} semiten_{leg}"},
            {"name": f"hip_rotation_{leg}", 
             "mtuNameSet": f"glut_med1_{leg} glut_min1_{leg} iliacus_{leg} psoas_{leg} tfl_{leg} gem_{leg} glut_med3_{leg} glut_min3_{leg} peri_{leg} quad_fem_{leg}"},
            {"name": f"hip_flexion_{leg}", 
             "mtuNameSet": f"add_brev_{leg} add_long_{leg} glut_med1_{leg} glut_min1_{leg} grac_{leg} iliacus_{leg} pect_{leg} psoas_{leg} rect_fem_{leg} sar_{leg} tfl_{leg}"},
            {"name": f"knee_angle_{leg}", 
             "mtuNameSet": f"bifemlh_{leg} bifemsh_{leg} grac_{leg} lat_gas_{leg} med_gas_{leg} sar_{leg} semimem_{leg} semiten_{leg} rect_fem_{leg} vas_int_{leg} vas_lat_{leg} vas_med_{leg}"},
            {"name": f"ankle_angle_{leg}", 
             "mtuNameSet": f"ext_dig_{leg} ext_hal_{leg} per_tert_{leg} tib_ant_{leg} flex_dig_{leg} flex_hal_{leg} lat_gas_{leg} med_gas_{leg} per_brev_{leg} per_long_{leg} soleus_{leg} tib_post_{leg}"}
        ]

        for dof in dofs:
            dof_element = ET.SubElement(dof_set, "dof")
            ET.SubElement(dof_element, "name").text = dof["name"]
            ET.SubElement(dof_element, "mtuNameSet").text = dof["mtuNameSet"]
       
        
        calibration_info = ET.SubElement(root, "calibrationInfo")
        uncalibrated = ET.SubElement(calibration_info, "uncalibrated")
        ET.SubElement(uncalibrated, "subjectID").text = osim_model_file_name
        ET.SubElement(uncalibrated, "additionalInfo").text = "TendonSlackLength and OptimalFibreLength scaled with Winby-Modenese"
        
        ET.SubElement(root, "opensimModelFile").text = "..\\..\\" + osim_model_file_name
        
        tree = ET.ElementTree(root)
        if save_path is not None:
            save_pretty_xml(tree, save_path)
            print(f"XML file created at: {save_path}")
        
        return tree

    def create_excitation_generator(self, save_path=None, leg='r', input_signals=None):
        if leg not in ['l', 'r']:
            raise ValueError("Leg must be 'l' or 'r'")

        # Define the input signals and excitations
        input_signals = ['GLTMED', 'RF', 'ADDLONG', 'ST', 'TA', 'GM']
        excitations = [
            'add_brev', 'add_long', 'bifemlh', 'bifemsh', 'ext_dig', 'ext_hal', 
            'flex_dig', 'flex_hal', 'lat_gas', 'med_gas', 'glut_max1', 'glut_max2', 
            'glut_max3', 'glut_med1', 'glut_med2', 'glut_med3', 'glut_min1', 
            'glut_min2', 'glut_min3', 'grac', 'iliacus', 'per_brev', 'per_long', 
            'psoas', 'rect_fem', 'sar', 'semimem', 'semiten', 'soleus', 'tfl', 
            'tib_ant', 'tib_post', 'vas_int', 'vas_lat', 'vas_med', 'add_mag1', 
            'add_mag2', 'add_mag3', 'pect', 'quad_fem', 'gem', 'peri', 'per_tert', 
            'ercspn', 'intobl', 'extobl'
        ]
        # Define the correct mapping of muscles to EMG signals
        muscle_to_signal = {
            "add_brev": "ADDLONG",
            "add_long": "ADDLONG",
            "grac": "ADDLONG",
            "bifemlh": "ST",
            "bifemsh": "ST",
            "semimem": "ST",
            "semiten": "ST",
            "ext_dig": "TA",
            "ext_hal": "TA",
            "tib_ant": "TA",
            "lat_gas": "GM",
            "med_gas": "GM",
            "soleus": "GM",
            "glut_max1": "GLTMED",
            "glut_max2": "GLTMED",
            "glut_max3": "GLTMED",
            "glut_med1": "GLTMED",
            "glut_med2": "GLTMED",
            "glut_med3": "GLTMED",
            "glut_min1": "GLTMED",
            "glut_min2": "GLTMED",
            "glut_min3": "GLTMED",
            "rect_fem": "RF",
        }
        # Create the root element
        root = ET.Element('excitationGenerator', {
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'xsi:noNamespaceSchemaLocation': 'excitationGenerator.xsd'
        })

        # Create the inputSignals element (Only include signals for the selected leg)
        input_signals_element = ET.SubElement(root, 'inputSignals', {'type': 'EMG'})
        input_signals_element.text = ' '.join([f'{leg.upper()}{signal}' for signal in input_signals])

        # Create the mapping element
        mapping_element = ET.SubElement(root, 'mapping')

        # Add excitations to the mapping element
        for excitation in excitations:
            excitation_element = ET.SubElement(mapping_element, 'excitation', {'id': f'{excitation}_{leg}'})
            if excitation in muscle_to_signal:
                input_element = ET.SubElement(excitation_element, 'input')
                input_element.set('weight', '1')
                input_element.text = f"{leg.upper()}{muscle_to_signal[excitation]}"

        # Add left leg muscles without assigning any input
        if leg == 'r':
            for excitation in excitations:
                ET.SubElement(mapping_element, 'excitation', {'id': f'{excitation}_l'})
        elif leg == 'l':
            for excitation in excitations:
                ET.SubElement(mapping_element, 'excitation', {'id': f'{excitation}_r'})

        # Create the tree and write to file
        tree = ET.ElementTree(root)
        if save_path is not None:    
            save_pretty_xml(tree, save_path)
            print(f"XML file created at: {save_path}")

    def create_execution_setup(self, save_path=None):
        root = ET.Element("ceinms")

        subject_file = ET.SubElement(root, "subjectFile")
        subject_file.text = ".\\calibratedSubject.xml"

        input_data_file = ET.SubElement(root, "inputDataFile")
        input_data_file.text = ".\\trial.xml"

        execution_file = ET.SubElement(root, "executionFile")
        execution_file.text = ".\\executionCfg.xml"

        excitation_generator_file = ET.SubElement(root, "excitationGeneratorFile")
        excitation_generator_file.text = ".\\excitationGenerator.xml"

        output_directory = ET.SubElement(root, "outputDirectory")
        output_directory.text = ".\\execution"

        tree = ET.ElementTree(root)
        if save_path is not None:
            save_pretty_xml(tree, save_path)
            print(f"Execution setup file created at: {save_path}")

        return tree

    def create_execution_cfg(self,save_path=None,leg='r'):
        root = ET.Element("execution", attrib={"xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"})

        nms_model = ET.SubElement(root, "NMSmodel")
        model_type = ET.SubElement(nms_model, "type")
        hybrid = ET.SubElement(model_type, "hybrid")

        ET.SubElement(hybrid, "alpha").text = "1"
        ET.SubElement(hybrid, "beta").text = "5"
        ET.SubElement(hybrid, "gamma").text = "10"
        ET.SubElement(hybrid, "dofSet").text = " ".join([f"hip_flexion_{leg}", f"knee_angle_{leg}", f"ankle_angle_{leg}"])
        ET.SubElement(hybrid, "synthMTUs").text = f"flex_dig_{leg} flex_hal_{leg} iliacus_{leg} per_brev_{leg} per_long_{leg} psoas_{leg} sar_{leg} tfl_{leg} tib_post_{leg} add_mag1_{leg} add_mag2_{leg} add_mag3_{leg} quad_fem_{leg} gem_{leg} peri_{leg} per_tert_{leg} ercspn_{leg} intobl_{leg} extobl_{leg} pect_{leg} vas_int_{leg} vas_lat_{leg} vas_med_{leg}"
        ET.SubElement(hybrid, "adjustMTUs").text = f"add_brev_{leg} add_long_{leg} bifemlh_{leg} bifemsh_{leg} ext_dig_{leg} ext_hal_{leg} lat_gas_{leg} med_gas_{leg} glut_max1_{leg} glut_max2_{leg} glut_max3_{leg} glut_med1_{leg} glut_med2_{leg} glut_med3_{leg} glut_min1_{leg} glut_min2_{leg} glut_min3_{leg} grac_{leg} semimem_{leg} semiten_{leg} soleus_{leg} tib_ant_{leg}  rect_fem_{leg}"

        algorithm = ET.SubElement(hybrid, "algorithm")
        simulated_annealing = ET.SubElement(algorithm, "simulatedAnnealing")
        ET.SubElement(simulated_annealing, "noEpsilon").text = "4"
        ET.SubElement(simulated_annealing, "rt").text = "0.3"
        ET.SubElement(simulated_annealing, "T").text = "20000"
        ET.SubElement(simulated_annealing, "NS").text = "15"
        ET.SubElement(simulated_annealing, "NT").text = "5"
        ET.SubElement(simulated_annealing, "epsilon").text = "0.001"
        ET.SubElement(simulated_annealing, "maxNoEval").text = "200000"

        tendon = ET.SubElement(nms_model, "tendon")
        equilibrium_elastic = ET.SubElement(tendon, "equilibriumElastic")
        ET.SubElement(equilibrium_elastic, "tolerance").text = "1e-09"

        activation = ET.SubElement(nms_model, "activation")
        ET.SubElement(activation, "exponential")

        tree = ET.ElementTree(root)
        if save_path is not None:
            save_pretty_xml(tree, save_path)
            print(f"Execution configuration file created at: {save_path}")

        return tree

    def create_ceinms_files(self, osim_model_path = None, leg=None, input_signals = None):
        
        if not osim_model_path:
            print("No OpenSim model file provided.")
            return
        
        if not input_signals:
            print("No input signals provided.")
            return

        if not leg:
            print("No leg provided.")
            return
        
        # Calibration Setup
        # savepath = self.ceinms_cal_setup.path
        # self.create_calibration_setup(savepath)

        # # Calibration Configuration
        # savepath = self.ceinms_cal_cfg.path
        # self.create_calibration_cfg(savepath, osimModelFile=osim_model_path,leg=leg)

        # # Trial
        # savepath = self.ceinms_trial.path
        # self.create_ceinms_trial_xml(savepath)

        # Uncalibrated Model 
        # savepath = self.ceinms_uncalibrated_subject.path
        # self.create_subject_uncalibrated(save_path=savepath,osimModelFile=osim_model_path, leg=leg)

        # Excitation Generator
        # savepath = self.ceinms_excitation_generator.path
        # self.create_excitation_generator(save_path=savepath, leg=leg, input_signals=input_signals)

        # Execution Setup
        # savepath = self.ceinms_execution_setup.path
        # self.create_execution_setup(save_path=savepath)

        # Execution Configuration
        savepath = self.ceinms_execution_cfg.path
        self.create_execution_cfg(save_path=savepath,leg=leg)

class openSim:
    def __init__(self, legs = ['r', 'l'], subjects =['PC002','PC003','PC006', 'PC013', 'TD006', 'TD013', 'TD017', 'TD021', 'TD023', 'TD026'], trials_to_load = ['trial1','trial2','trial3','normal1', 'normal2', 'normal3', 'crouch1', 'crouch2', 'crouch3'], trial_number = 1):
        try:
            self.code_path = os.path.dirname(__file__)
        except:
            self.code_path = os.getcwd()
        
        self.simulations_path = os.path.join(os.path.dirname(self.code_path), 'Simulations')
        self.subjects = {}
        
        for subject in subjects:
            self.subjects[subject] = {}
            self.subjects[subject]['model'] = os.path.join(self.simulations_path, subject, subject + '_scaled.osim')
            for leg in legs: 
                for trial in trials_to_load:            
                    self.trial_path = os.path.join(self.simulations_path, subject, f'{trial}_{leg}{trial_number}')
                    try:
                        trial = Trial(self.trial_path)
                        self.subjects[subject][trial.name] = trial 
                    except Exception as e:
                        self.subjects[subject][trial] =  None
                        # print(f"Error loading trial: {self.trial_path}")
                        # print(e)
            
        
        self.ik_columns = ["hip_flexion_leg", "hip_adduction_leg", "hip_rotation_leg", "knee_angle_leg", "ankle_angle_leg"]
        self.id_columns = ["hip_flexion_leg" + "_moment", "hip_adduction_leg" + "_moment", "hip_rotation_leg" + "_moment", "knee_angle_leg" + "_moment", "ankle_angle_leg" + "_moment"]
        self.force_columns = ["add_long_leg", "rect_fem_leg", "med_gas_leg", "semiten_leg","tib_ant_leg"]


        self.titles = ["Hip Flexion", "Hip Adduction", "Hip Rotation", "Knee Flexion", "Ankle Plantarflexion"]
        self.titles_muscles = ["Adductor Longus", "Rectus Femoris", "Medial Gastrocnemius", "Semitendinosus", "Tibialis Anterior"]

    # Time Normalisation Function 
    def time_normalised_df(self, df, fs=None):
        if not isinstance(df, pd.DataFrame):
            raise Exception('Input must be a pandas DataFrame')
        
        if not fs:
            try:
                fs = 1 / (df['time'][1] - df['time'][0])  # Ensure correct time column
            except KeyError:
                raise Exception('Input DataFrame must contain a column named "time"')
            
        normalised_df = pd.DataFrame(columns=df.columns)

        for column in df.columns:
            if column == 'time':  # Skip time column
                continue	
            normalised_df[column] = msk.np.zeros(101)

            currentData = df[column].dropna()  # Remove NaN values

            timeTrial = msk.np.linspace(0, len(currentData) / fs, len(currentData))  # Original time points
            Tnorm = msk.np.linspace(0, timeTrial[-1], 101)  # Normalize to 101 points

            normalised_df[column] = msk.np.interp(Tnorm, timeTrial, currentData)  # Interpolate

        return normalised_df

    def plot_single_trial(self, show = False):
        #Read .mot files
        with open(self.mot_file, "r") as file:
            lines = file.readlines()

        # Find the line where actual data starts (usually after 'endheader')
        for i, line in enumerate(lines):
            if "endheader" in line:
                start_row = i + 1  # Data starts after this line
                break
        else:
            start_row = 0  # If 'endheader' is not found, assume no header

        # Load data using Pandas
        self.df_ik = pd.read_csv(self.mot_file, delim_whitespace=True, start_row=start_row)
        self.df_id = pd.read_csv(self.id_file, sep="\t", start_row=6)
        self.df_force = pd.read_csv(self.force_file, sep="\t", start_row=14)

        # Apply normalisation to both IK (angles) and ID (moments) data
        self.df_ik_normalized = self.time_normalised_df(df=self.df_ik)
        self.df_id_normalized = self.time_normalised_df(df=self.df_id)
        self.df_force_normalized = self.time_normalised_df(df=self.df_force)

        # Ensure time is normalized to 101 points
        time_normalized = msk.np.linspace(0, 100, 101)  
 
        # select the specified columns         
        self.ik_data = self.df_ik_normalized[self.ik_columns]
        self.id_data = self.df_id_normalized[self.id_columns]
        self.force_data = self.df_force_normalized[self.force_columns]
            
        # Define the layout 
        fig, axes = plt.subplots(2, 5, figsize=(15, 4)) 

        #Plot IK (angles)
        for i, col in enumerate(self.ik_columns):
            ax = axes[0,i]
            ax.plot(time_normalized, self.ik_data[col], color='red')  # Main curve
            ax.set_title(self.titles[i])
            if i == 0:
                ax.set_ylabel("Angle (deg)")
            ax.grid(True)

        #Plot ID (moments)
        for i, col in enumerate(self.id_columns):
            ax = axes[1,i]
            ax.plot(time_normalized, self.id_data[col], color='blue')  # Main curve
            ax.set_title(self.titles[i])
            if i == 0:
                ax.set_ylabel("Moment (Nm)")
            ax.set_xlabel("% Gait Cycle")
            ax.grid(True)

        plt.tight_layout()


        # PLOT MUSCLE FORCES 
        fig, axes = plt.subplots(nrows=1, ncols=5, figsize=(15, 4), sharex=True)

        for i, col in enumerate(self.force_columns):
            ax = axes[i]
            ax.plot(time_normalized, self.force_data[col], color='green')
            ax.set_title(self.titles_muscles[i])
            if i == 0:
                ax.set_ylabel("Force (N)")
            ax.set_xlabel("% Gait Cycle")
            ax.grid(True)

        plt.tight_layout()
        
        if show:
            plt.show()

    def plot_multiple_trials(self, show=False):
        self.df_ik_list = []  # Store loaded DataFrames
        
        for subject in self.subjects:
            for trial in self.subjects[subject]:
                trial_obj = self.subjects[subject][trial]
                if trial_obj:
                    self.df_ik_list.append(trial_obj.ik.data)
                    
        for file in self.mot_files:  # Loop through each file
            with open(file, "r") as f:
                lines = f.readlines()

            # Load data using Pandas
            df = pd.read_csv(file, delim_whitespace=True, skiprows=5)
            self.df_ik_list.append(df)

        # Normalize all loaded IK data
        self.df_ik_normalized_list = []  # Store normalized DataFrames

        for df in self.df_ik_list:  # Loop through each loaded DataFrame
            df_normalized = self.time_normalised_df(df=df)  # Apply normalization
            self.df_ik_normalized_list.append(df_normalized)  # Store normalized DataFrame

        # Ensure time is normalized to 101 points
        time_normalized = msk.np.linspace(0, 100, 101)

        # Select the specified columns from normalized data
        self.ik_data_list = []  # Store DataFrames with only the required columns

        for df_normalized in self.df_ik_normalized_list:  # Loop through each normalized DataFrame
            if set(self.ik_columns).issubset(df_normalized.columns):  # Check if columns exist
                self.ik_data_list.append(df_normalized[self.ik_columns])  # Select only specified columns
            else:
                print("Warning: Some specified columns are missing in a file.")

        # Plot mean and sd
        # Check if IK data exists
        if not self.ik_data_list:
            print("No IK data available to plot!")
        else:
            # Convert list of DataFrames to a single NumPy array
            combined_df = np.array([df.values for df in self.ik_data_list])  # Shape: (num_trials, num_timepoints, num_columns)

            # Check if data is properly structured
            if combined_df.shape[0] < 2:
                print("Not enough trials to calculate mean and standard deviation!")
            else:
                # Compute Mean and Standard Deviation
                mean_values = np.mean(combined_df, axis=0)
                std_values = np.std(combined_df, axis=0)

                # Normalize time from 0 to 100% Gait Cycle
                time_values = np.linspace(0, 100, combined_df.shape[1])

                # Create a shared figure for all subplots
                fig, axes = plt.subplots(nrows=1, ncols=len(self.ik_columns), figsize=(20, 5), sharex=True)

                if len(self.ik_columns) == 1:
                    axes = [axes]  # If only one column, ensure it's iterable

                for i, col in enumerate(self.ik_columns):
                    ax = axes[i]

                    # Plot mean line
                    ax.plot(time_values, mean_values[:, i], color='red', label="Mean", linewidth=2)

                    # Shade the standard deviation range
                    ax.fill_between(time_values, mean_values[:, i] - std_values[:, i],
                                    mean_values[:, i] + std_values[:, i], color='red', alpha=0.2, label="SD Range")

                    # Formatting
                    ax.set_title(col)
                    ax.set_xlabel("Gait Cycle (%)")
                    ax.set_xlim(0, 100)  # X-axis from 0% to 100% of the gait cycle
                    ax.grid(True)

                    # Set Y-label only for the first subplot
                    if i == 0:
                        ax.set_ylabel("Angle (Degrees)")
                        ax.legend()


                plt.tight_layout()

                if show:
                    plt.show()

def export_c3d(c3dFilePath):
    analog_file_path = os.path.join(os.path.dirname(c3dFilePath),'analog.csv')
    
    # if the file already exists, return the file
    if os.path.isfile(analog_file_path):
        df = pd.read_csv(analog_file_path)
        return df
    
    print('Exporting analog data to csv ...')
    
    # read c3d file
    reader = c3d.Reader(open(c3dFilePath, 'rb'))

    # get analog labels, trimmed and replace '.' with '_'
    analog_labels = reader.analog_labels
    analog_labels = [label.strip() for label in analog_labels]
    analog_labels = [label.replace('.', '_') for label in analog_labels]

    # get analog labels, trimmed and replace '.' with '_'
    first_frame = reader.first_frame
    num_frames = reader.frame_count
    fs = reader.analog_rate

    # add time to dataframe
    initial_time = first_frame / fs
    final_time = (first_frame + num_frames-1) / fs
    time = np.arange(first_frame / fs, final_time, 1 / fs) 

    df = pd.DataFrame(index=range(num_frames),columns=analog_labels)
    df['time'] = time
    
    # move time to first column
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]    
    
    # loop through frames and add analog data to dataframe
    for i_frame, points, analog in reader.read_frames():
        
        # get row number and print loading bar
        i_row = i_frame - reader.first_frame
        # msk.ut.print_loading_bar(i_row/num_frames)
        
        # convert analog data to list
        analog_list  = analog.data.tolist()
        
        # loop through analog channels and add to dataframe
        for i_channel in range(len(analog_list)):
            channel_name = analog_labels[i_channel]
            
            # add channel to dataframe
            df.loc[i_row, channel_name] = analog[i_channel][0]
    
    # save emg data to csv   
    df.to_csv(analog_file_path)
    print('analog.csv exported to ' + analog_file_path)  
    
    return df

def export_analog(c3dFilePath=None, columns_to_mot='all'):
    if not c3dFilePath:
        print('C3D file path not provided')
        return
    
    reader = c3d.Reader(open(c3dFilePath, 'rb'))

    # get analog labels, trimmed and replace '.' with '_'
    analog_labels = reader.analog_labels
    analog_labels = [label.strip() for label in analog_labels]
    analog_labels = [label.replace('.', '_') for label in analog_labels]
    
    # remove those not in columns_to_mot (fix: use column names to filter and get indices)
    if columns_to_mot != 'all':
        indices = [i for i, label in enumerate(analog_labels) if label in columns_to_mot]
        analog_labels = [analog_labels[i] for i in indices]
    else:
        indices = list(range(len(analog_labels)))
        columns_to_mot = analog_labels

    # get analog labels, trimmed and replace '.' with '_'
    fs = reader.analog_rate

    # add time to dataframe
    marker_fs = reader.point_rate  # This is the actual frame rate for kinematics
   

    first_time = reader.first_frame / marker_fs
    final_time = (reader.first_frame + reader.frame_count - 1) / marker_fs
    time = msk.np.arange(first_time, final_time + 1 / marker_fs, 1 / marker_fs)
  
    num_frames = len(time)
    df = pd.DataFrame(index=range(num_frames), columns=analog_labels)
    df['time'] = time

    # move time to first column
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols] 

    # loop through frames and add analog data to dataframe
    for i_frame, points, analog in reader.read_frames():
        
        # get row number and print loading bar
        i_row = i_frame - reader.first_frame
        # msk.ut.print_loading_bar(i_row/num_frames)
        
        # loop through selected analog channels and add to dataframe (fix: iterate over filtered indices)
        for idx, i_channel in enumerate(indices):
            channel_name = analog_labels[idx]
            df.loc[i_row, channel_name] = analog[i_channel][0]
    
    # remove rows with NaN values
    df = df.dropna()
    
    # save emg data to csv
    analog_csv_path = c3dFilePath.replace('.c3d', '_analog.csv')
    df.to_csv(analog_csv_path, index=False)
    
    # save to mot
    # self.csv_to_mot()
    
    return analog_csv_path

def header_mot(df,name):

        num_rows = len(df)
        num_cols = len(df.columns) 
        inital_time = df['time'].iloc[0]
        final_time = df['time'].iloc[-1]
        df_range = f'{inital_time}  {final_time}'


        return f'name {name}\nnRows={num_rows}\nnColumns={num_cols}\n \nendheader'

def csv_to_mot(emg_csv, columns = 'all'):
    
    emg_data = msk.bops.pd.read_csv(emg_csv)
    
    try:
        time = emg_data['time']
    except:
        time = emg_data['Time']

    # start time from new time point
    start_time = time.iloc[0]
    end_time = time.iloc[-1]

    num_samples = len(emg_data)
    new_time = np.linspace(start_time, end_time, num_samples)

    # remove columns not in columns_to_mot
    if columns != 'all':
        emg_data = emg_data[columns]

    emg_data['time'] = new_time
    # Ensure 'time' column is the first column
    cols = emg_data.columns.tolist()
    cols.insert(0, cols.pop(cols.index('time')))
    emg_data = emg_data[cols]

    # Define a new file path 
    new_file_path = os.path.join(emg_csv.replace('.csv', '.mot'))

    # Save the modified DataFrame
    emg_data.to_csv(new_file_path, index=False)  # index=False prevents adding an extra index column

    # save to mot
    header = header_mot(emg_data, "processed_emg_signals")

    mot_path = new_file_path.replace('.csv','.mot')
    with open(mot_path, 'w') as f:
        f.write(header + '\n')  
        # print column names 
        f.write('\t'.join(map(str, emg_data.columns)) + '\n')
        for index, row in emg_data.iterrows():
            f.write('\t'.join(map(str, row.values)) + '\n')  
    
    print(f"File saved: {mot_path}")
    
    return mot_path

def time_normalised_df(df, fs=None):
    if not isinstance(df, pd.DataFrame):
        raise Exception('Input must be a pandas DataFrame')
    
    if not fs:
        try:
            fs = 1 / (df['time'][1] - df['time'][0])  # Ensure correct time column
        except KeyError:
            raise Exception('Input DataFrame must contain a column named "time"')
        
    normalised_df = pd.DataFrame(columns=df.columns)

    for column in df.columns:
        normalised_df[column] = msk.np.zeros(101)

        currentData = df[column].dropna()  # Remove NaN values

        timeTrial = msk.np.linspace(0, len(currentData) / fs, len(currentData))  # Original time points
        Tnorm = msk.np.linspace(0, timeTrial[-1], 101)  # Normalize to 101 points

        normalised_df[column] = msk.np.interp(Tnorm, timeTrial, currentData)  # Interpolate

    return normalised_df

def save_pretty_xml(tree, save_path):
            """Saves the XML tree to a file with proper indentation."""
            # Convert to string and format with proper indents
            rough_string = ET.tostring(tree.getroot(), 'utf-8')
            reparsed = xml.dom.minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="   ")

            # Write to file
            with open(save_path, 'w') as file:
                file.write(pretty_xml)

def filter_emg(signal, sample_rate=1000, low_pass_cutoff=6):
    """
    Processes EMG signal: clean, rectify, and filter to get the envelope.
    """
    cleaned_signal = nk.emg_clean(signal, sampling_rate=sample_rate, method='biosppy')
    rectified_signal = np.abs(cleaned_signal)
    low_pass = low_pass_cutoff / (sample_rate / 2)
    b, a = sig.butter(4, low_pass, btype='lowpass')
    emg_envelope = np.abs(sig.filtfilt(b, a, rectified_signal))

    return emg_envelope

def filter_emg_signals(csv_file, muscles, sample_rate=1000):
    df = pd.read_csv(csv_file)
    filtered_data = {'time': df['time']}  # Add time column
    
    for muscle in muscles:
        if muscle in df.columns:
            filtered_data[muscle] = filter_emg(df[muscle].values, sample_rate)
    
    df_filtered = pd.DataFrame(filtered_data)
    
    filtered_emg_path = csv_file.replace('.csv', '_filtered_emg.csv')
    df_filtered.to_csv(filtered_emg_path, index=False)
    
    return filtered_emg_path

def amplitude_normalise(processed_emg_path):
    emg_data = pd.read_csv(processed_emg_path)
    
    # Separate time and signal
    time = emg_data['time']
    signal_data = emg_data.drop(columns=['time'])
    
    # Avoid divide-by-zero errors
    max_vals = signal_data.max()
    max_vals[max_vals == 0] = 1  # prevent division by zero

    # Normalise each EMG signal
    signal_normalised = signal_data / max_vals

    # Combine back with time
    emg_data_normalised = pd.concat([time, signal_normalised], axis=1)

    # Save the result
    normalised_emg_path = processed_emg_path.replace('.csv', '_normalised.csv')
    emg_data_normalised.to_csv(normalised_emg_path, index=False)
    
    return normalised_emg_path

def filter_force(signal, sample_rate=1000, low_pass_cutoff=20):
    """
    Processes EMG signal: clean, rectify, and filter to get the envelope.
    """
    return nk.signal_filter(signal, sampling_rate=sample_rate, highcut=low_pass_cutoff, method='butter')

def normalize_time_act(df, start_time, duration):
    df_norm = df.copy()
    df_norm['time'] = 100 * (df_norm['time'] - start_time) / duration
    return df_norm  

def find_file_endheader_line(path):
        with open(path, 'r') as file:
            for i, line in enumerate(file):
                if 'endheader' in line:
                    return i + 1
        return 0  


#%% END