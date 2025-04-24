import opensim as osim
import pandas as pd
import os
import xml.etree.ElementTree as ET
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_sto_file(file_path):
    """Load a .sto file and return its contents as a DataFrame."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
        
        endheader = lines.index('endheader\n')
    
    # Load the .sto file using pandas
    data = pd.read_csv(file_path, sep='\t', skiprows=endheader+1)
    return data

def sum_muscle_forces_by_group(model_path, forces_file, output_csv):
    # Load the OpenSim model
    model = osim.Model(model_path)

    # Load the muscle forces data
    forces_data = load_sto_file(forces_file)

    # Get the list of muscles in the model
    force_set = model.getForceSet()
    force_set.getGroupNames('rGroupNames')
    for i in range(force_set.getSize()):
        force = force_set.get(i)
        force_set
        print(force.getName())
    
    breakpoint()
    muscle_set = model.getMuscles()
    muscle_groups = {}
    
    # Group muscles by their group name
    for i in range(muscle_set.getSize()):
        muscle = muscle_set.get(i)
        group_name = muscle.getGroupName()
        if group_name not in muscle_groups:
            muscle_groups[group_name] = []
        muscle_groups[group_name].append(muscle.getName())

    # Calculate the sum of muscle forces for each group
    summed_forces = {}
    for group, muscles in muscle_groups.items():
        summed_forces[group] = forces_data[muscles].sum(axis=1)

    # Create a DataFrame to store the summed forces
    summed_forces_df = pd.DataFrame(summed_forces)
    summed_forces_df['time'] = forces_data['time']

    # Save the summed forces to a CSV file
    summed_forces_df.to_csv(output_csv, index=False)

def read_xml_file(file_path):
    """Read an XML file and return its contents."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    root = ET.parse(file_path).getroot()
    
    # Iterate through all child elements in the root and print their members
    members= []
    for child in root:
        if child.find('members') is not None:
            list_of_members = child.find('members').text.split()
            for member in list_of_members:
                members.append(member.strip())
            
    return members
    
# Example usage
model_path = r"C:\Git\research_data\Projects\runbops_FAIS_phd\models\009\009_Rajagopal2015_FAI_originalMass_opt_N10_hans.osim"
forces_file = r"C:\Git\research_data\Projects\runbops_FAIS_phd\simulations\009\pre\sprint_1\muscle_forces.sto"
output_csv = forces_file.replace('.sto', '_summed.csv')

model = osim.Model(model_path)
force_set = model.getForceSet()
muscle_groups = {}
for i in range(force_set.getNumGroups()):
    group = force_set.getGroup(i)    
    path = SCRIPT_DIR + '\groups.xml'
    group.printToXML(path)
    members = read_xml_file(path)
    
    # Add the group name and its members to the dictionary
    muscle_groups[group.getName()] = members
    
    # Delete xml file
    if os.path.exists(path):
        os.remove(path)
    
    

# Print the muscle groups and their members to a CSV file
muscle_groups_df = pd.DataFrame.from_dict(muscle_groups, orient='index').transpose()
muscle_groups_df.to_csv(SCRIPT_DIR + '\muscle_groups.csv', index=False, header=True)

