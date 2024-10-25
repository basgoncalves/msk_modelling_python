from msk_modelling_python.src import bops as bp
import numpy as np
import c3d
import pandas as pd

def import_c3d(file_path, marker_names):

    class point_data:
        def __init__(self):
            self.x = []
            self.y = []
            self.z = []
            
    c3d_reader = c3d.Reader(open(file_path, 'rb'))
    labels = [label.replace(' ', '') for label in c3d_reader.point_labels] # make list and remove spaces
    analog_labels = [label.replace(' ', '') for label in c3d_reader.analog_labels]
    c3d_dict = {}
    analog_dict = {}
    for frame_no, points, analog in c3d_reader.read_frames():
        for name in marker_names:
            if name not in c3d_dict:
                c3d_dict[name] = point_data() 
            if name in labels:
                idx = labels.index(name)
                if name not in c3d_dict:
                    c3d_dict[name].x[frame_no] = np.nan
                    c3d_dict[name].y[frame_no] = np.nan
                    c3d_dict[name].z[frame_no] = np.nan

                c3d_dict[name].x.append(points[idx][0])
                c3d_dict[name].y.append(points[idx][1])
                c3d_dict[name].z.append(points[idx][2])

        for i_label, analog_name in enumerate(analog_labels):
            if analog_name not in analog_dict:
                analog_dict[analog_name] = []

            analog_dict[analog_name].append(analog[i_label][0])

    return c3d_dict, analog_dict

def determine_foot_on_plate(markers, forces):
    # Assuming markers is a 3D array (frames, markers, coordinates)
    # and forces is a 3D array (frames, force plates, channels)
    foot_positions = np.mean(markers[:, :3, :], axis=1)  # Average position of each foot's markers
    cop_positions = forces[:, :, :2]  # Center of pressure positions (assuming first 2 channels are CoP X and Y)
    
    foot_on_plate = []
    for foot_pos in foot_positions:
        distances = np.linalg.norm(cop_positions - foot_pos, axis=2)
        foot_on_plate.append(np.argmin(distances, axis=1))
    
    return foot_on_plate


if __name__ == '__main__':
   
    # Example usage
    marker_names = ['RTOE', 'LTOE', 'RHEE', 'LHEE']
    c3d_dict, analog_dict = import_c3d(bp.select_file(), marker_names)
    print(c3d_dict)
    # foot_on_plate = determine_foot_on_plate(c3d_dict,analog_dict)
    # print(foot_on_plate)
