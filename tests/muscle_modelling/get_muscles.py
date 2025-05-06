import os
import json
import time
import pandas as pd
import numpy as np
import opensim as osim
import matplotlib.pyplot as plt
import msk_modelling_python as msk
import matplotlib.pyplot as plt 
import xml.etree.ElementTree as ET


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
START_TIME = time.time()
################
def get_muscle_groups(model_path, output_csv=''):
    
    model = osim.Model(model_path)
    model.initSystem()
    breakpoint()
    if not output_csv:
        output_csv = os.path.join(MODULE_DIR, 'muscle_groups.csv')

def get_muscles_by_group_osim(xml_path, group_names='all'): 
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

def get_muscle_per_coordinate(model_path, coordinates = 'all'):
        '''
        This function returns the muscles that are actuating the given coordinates. 
        The function uses the OpenSim API to get the coordinates and the muscles in the model.
        The function returns a dictionary with the coordinates as keys and the muscles as values.
        '''
        # Load the OpenSim model
        model = osim.Model(model_path)
        state = model.initSystem()

        # Get all coordinates in the model
        coordinate_set = model.getCoordinateSet()
          
        if coordinates == 'all':
            coordinates = []
            for i in range(coordinate_set.getSize()):
                coordinates.append(coordinate_set.get(i).getName())
          
        # Get all muscles in the model
        muscle_set = model.getMuscles()
        
        # Create a dictionary to store muscles for each coordinate
        muscles_per_coordinate = {}

        # Loop through each coordinate and find its actuating muscles based on non-zero moment arms
        for i in range(muscle_set.getSize()):
            for coord_name in coordinates:
            
                solver = osim.MomentArmSolver(model)
                muscle = muscle_set.get(i)
                geometry_path = muscle.getGeometryPath()
                coord = coordinate_set.get(coord_name)
                angle = coord.getValue(state)
                coord.setValue(state, angle)
                
                # Compute the moment arm for the muscle at the current coordinate angle
                moment_arm = solver.solve(state,coord, geometry_path)
                
                # Compute the moment arm for the muscle at the maximum coordinate angle
                coord.setValue(state, coord.getRangeMax())
                moment_arm_max = solver.solve(state,coord, geometry_path)
                
                # Compute the moment arm for the muscle at the minimum coordinate angle
                coord.setValue(state, coord.getRangeMin())
                moment_arm_min = solver.solve(state,coord, geometry_path)
                            
                if np.mean([moment_arm, moment_arm_max, moment_arm_min]).round(3) != 0:
                    muscles_per_coordinate[coord_name] = muscle.getName()

            
        return muscles_per_coordinate

if __name__ == "__main__":
    # Define the model path and muscle forces file
    model_path = os.path.join(MODULE_DIR, 'osim_model.osim')
    
    # Call the function to get muscle groups
    # get_muscle_groups(model_path)
    
    members_dict = get_muscles_by_group_osim(model_path)
    print(members_dict)
    
    muscles_coord = get_muscle_per_coordinate(model_path)
    breakpoint()
    
    # Print the elapsed time
    print(f"Elapsed time: {time.time() - START_TIME:.2f} seconds")


#%% END