import numpy as np
import opensim
import os
import pandas as pd
import xml.etree.ElementTree as ET

# XML edit
def edit_xml_file(xml_file,tag,new_tag_value):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for character in root.iter(tag):
        print('old value ' + tag  + ' = ' + character.text)
        character.text = str(new_tag_value)
    
    tree.write(xml_file, encoding='utf-8', xml_declaration=True)

    for character in root.iter(tag):
        print('new value ' + tag  + ' = ' + character.text)
    
    return tree

data_folder = r"C:\Git\isbs2024\Data"

osim_model_scaled =os.path.join(data_folder,'Scaled_models\Alex\Athlete_26_scaled.osim')
base_name_with_extension = os.path.basename(osim_model_scaled)
athlete_name, file_extension = os.path.splitext(base_name_with_extension)

# Load the OpenSim models
model = opensim.Model(osim_model_scaled)
body_set = model.get_BodySet()
scale_factors = dict()

# Get the scale factors for each body
no_geometry_bodies = ['Abdomen', 'Abd_L_L1','Abd_L_L2','Abd_L_L3','Abd_L_L4','Abd_L_L5',
                       'Abd_R_L1','Abd_R_L2','Abd_R_L3','Abd_R_L4','Abd_R_L5']
for i in range(body_set.getSize()):
    body = body_set.get(i)
    if body.getName() in no_geometry_bodies:
        continue
    else:
        print(body.getName())
        scale_factors[body.getName().lower()] = body.get_attached_geometry(0).get_scale_factors().to_numpy()

# create np array of scale factors for lumbar and thoracic segments
lumbar_thoracicic_segments = np.array([np.array(scale_factors['lumbar1']),
    np.array(scale_factors['lumbar2']), np.array(scale_factors['lumbar3']), np.array(scale_factors['lumbar4']), np.array(scale_factors['lumbar5']),
    np.array(scale_factors['thoracic1']), np.array(scale_factors['thoracic2']), np.array(scale_factors['thoracic3']), np.array(scale_factors['thoracic4']),
    np.array(scale_factors['thoracic5']), np.array(scale_factors['thoracic6']), np.array(scale_factors['thoracic7']), np.array(scale_factors['thoracic8']),
    np.array(scale_factors['thoracic9']), np.array(scale_factors['thoracic10']), np.array(scale_factors['thoracic11']), np.array(scale_factors['thoracic12'])])

# Calculate scale factors for the torso as mean from lumbar and thoracic segments
mean_torso = np.mean(lumbar_thoracicic_segments, axis=0)
scale_factors['torso'] = mean_torso
df = pd.DataFrame(scale_factors)
df.to_csv(os.path.join(data_folder,r'Scaled_models\scale_factors.csv'))

# initialise the model to get the mass
state = model.initSystem()
mass = model.getTotalMass(state)

# edit the scale file with mass and name 
xml_file = os.path.join(data_folder,r'Setups\setup_scale_manual.xml')
tree = edit_xml_file(xml_file,'mass',mass)
root = tree.getroot()
element_to_change = root.find(".//ScaleTool[@name='Catelli_high_hip_flexion']") # Change the name 
element_to_change.set('name', athlete_name)

# add scale fators to each element with the same name as the segment

for scale_elem in root.findall(".//Scale"):
    segment = scale_elem.find("segment").text.strip()
    print(str(scale_factors[segment]))
    scale_elem.find("scales").text = str(scale_factors[segment])

# write the xml file
new_xml_file = os.path.join(data_folder,r'Scaled_models\{i}_scale_setup.xml'.format(i=athlete_name))
tree.write(new_xml_file, encoding='utf-8', xml_declaration=True)
