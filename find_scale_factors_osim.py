import numpy as np
import opensim
import math
import os
import pandas as pd

osim_model1 = r"C:\Git\isbs2024\Data\Scaled_models\baseModel_upperBody2segments.osim"
osim_model2 = r"C:\Git\isbs2024\Data\Scaled_models\Athlete_06_scaled.osim"

# Load the OpenSim models
model1 = opensim.Model(osim_model1)
model2 = opensim.Model(osim_model2)

# Get the number of bodies (segments) in the models
num_bodies1 = model1.getBodySet().getSize()
num_bodies2 = model2.getBodySet().getSize()

# Get the number of joints in the models
joint_set1 = model1.getJointSet()
num_joints1 = joint_set1.getSize()

# Compare the segment lengths


# for i in range(num_bodies1):
#     body1 = model1.getBodySet().get(i)
#     body_name = body1.getName()
#     body2 = model2.getBodySet().get(body_name)    

#     methods_body1 = dir(body1)
#     for method in methods_body1:
#         # print(method)
#         pass

#     inertia_data = body1.get_inertia()
#     mass = body1.get_mass()
#     centre_of_mass = body1.get_mass_center()

#     # Pad the inertia_data with zeros to make it a 1x9 array
#     inertia_data_padded = inertia_data + [0, 0, 0]

#     # Reshape the inertia data into a 3x3 matrix
#     inertia_matrix = np.array(inertia_data_padded).reshape((3, 3))

#     # Calculate the size (length) based on the moment of inertia tensor and mass distribution
#     length_squared = np.trace(inertia_matrix) / mass

#     # Take the square root to get the length
#     length = np.sqrt(length_squared)

#     print("Length:", length)


#     # Use the PhysicalOffsetFrame to get the length
#     length = 1
#     print(length)
#     break
    
#     length1 = body1.get_mass_center()
#     length2 = body2.get_mass_center()
#     print(f"Segment {i+1}: Length in model 1 = {length1}, Length in model 2 = {length2}")
#     exit()


def calculate_3d_distance(vector1, vector2):
    x1, y1, z1 = vector1
    x2, y2, z2 = vector2
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
    return distance

def clear_terminal(mode = 'cls'):
    if mode == 'cls':
        os.system('cls' if os.name == 'nt' else 'clear')
    else:
        print('\n'*3)
    exit()

def calculate_scale_factor(model1,model2,marker_name1,marker_name2):
    
    # Get the distance between the markers in the original model
    state = model1.initSystem()
    marker1 = model1.getMarkerSet().get(marker_name1).getLocationInGround(state).to_numpy()
    marker2 = model1.getMarkerSet().get(marker_name2).getLocationInGround(state).to_numpy()
    distance_model1 = calculate_3d_distance(marker1, marker2)


    # Get the distance between the markers in the second model
    state = model2.initSystem()
    marker1 = model2.getMarkerSet().get(marker_name1).getLocationInGround(state).to_numpy()
    marker2 = model2.getMarkerSet().get(marker_name2).getLocationInGround(state).to_numpy()
    distance_model2 = calculate_3d_distance(marker1, marker2)

    # Calculate the scale factor
    scale_factor = distance_model1 / distance_model2
    return scale_factor

# Add a marker to the model
scale_factor = calculate_scale_factor(model1,model2,'RASI','LASI')
print(scale_factor)



# Need to fix the rest since the scaled model does not have some of the markera (e.g. RHJC RKNJC) to calculate the scale factors using markers
clear_terminal(0)

marker = opensim.Marker()
marker.setName('RHJC')
marker.set_location(opensim.Vec3(0,0,0))
print(type(marker))
clear_terminal(0)
model2.addMarker(marker)
print(type(model2))
marker1 = model2.initSystem()
clear_terminal(0)
scale_factor = calculate_scale_factor(model1,model2,'RHJC','RKNEL')
print(scale_factor)

