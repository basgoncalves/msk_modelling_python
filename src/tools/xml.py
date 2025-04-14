# XML handling
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
            import opensim as osim
        except:
            pass
        
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

class TestXMLTools(unittest.TestCase):
    def test_load(self):
        
        
        example_file = r"https://github.com/basgoncalves/opensim_tutorial/blob/main/tutorials/repeated_sprinting/Simulations/009/pre/inverseKinematics/RunA1/setup_IK.xml"
        self.assertIsNotNone(XMLTools.load(example_file))
    
    def test_create_ceinms_calibration_setup(self):
        xml_tool = XMLTools()
        tree = xml_tool.ceinms.create_calibration_setup()
        self.assertIsNotNone(tree)
    
    def test_create_ceinms_calibration_cfg(self):
        xml_tool = XMLTools()
        tree = xml_tool.create_ceinms_calibration_cfg()
        self.assertIsNotNone(tree)
    
