import scipy.io
import opensim as osim
from bops import *
import bops as bp
import ceinms_setup as cs
import plotting as plt
from bops import save_fig
import numpy as np

def get_matlab_data(mat_file_path):
    # Load the .mat file
    data = scipy.io.loadmat(mat_file_path)

    # Do further processing with the loaded data
    # ...

    return data
    # Specify the path to the .mat file
    mat_file_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_90\settings.mat"

    # Load the .mat file
    data = scipy.io.loadmat(mat_file_path)


    print(type(data))
    print(data.keys())
    print(type(data['cycle'][0][0][0][0]))
    print((data['cycle'][0][0][0][0]))
    print(len(data['cycle'][0][0][0][0]))
    print(type(data['duration'][0]))
    print((data['duration'][0]))
    print((data['firstFrame'][0]))
    # ...

    # Do further processing with the loaded data
    # ...

def plot_coordinates_api(model_file_path, ik_file_path,leg = 'l'):

    def get_model_coord(model, coord_name):
        try:
            index = model.getCoordinateSet().getIndex(coord_name)
            coord = model.updCoordinateSet().get(index)
        except:
            index = None
            coord = None
            print(f'Coordinate {coord_name} not found in model')
        
        return index, coord

    # Load motions and model
    motion = osim.Storage(ik_file_path)
    model = osim.Model(model_file_path)

    # Initialize system and state
    model.initSystem()
    state = model.initSystem()

    # coordinate names
    index, coord = get_model_coord(model, 'hip_flexion_' + leg)
    coor_name = motion.getColumnLabels().get(index+1)

    if coor_name != 'hip_flexion_' + leg:
        raise ValueError('Coordinate indexes do not match between model and ik file. Check if the IK file was ran with the same model.')
    
    angle_to_plot = []
    time = []
    # compute angles
    for i in range(0, motion.getSize()):
        angle = motion.getStateVector(i).getData().get(index) # / 180 * np.pi
        
        angle_to_plot.append(angle)
        time.append(motion.getStateVector(i).getTime())
        # Update the state with the joint angle
        coordSet = model.updCoordinateSet()
        coordSet.get(index).setValue(state, angle)

    plt.figure()
    plt.plot(angle_to_plot)
    plt.ylabel('Hip flexion angle (deg)')
    plt.xlabel('Time (s)')
    plt.title('Hip flexion angle ' + ik_file_path)
    plt.show()

def compare_ceinms_models(model_path1,model_path2):
    pass

def test_error_momArmsCheck():
    time_vector = np.linspace(0, 1, 101)
    # dy = np.diff(np.random(10, size=(101,1)))
    discontinuity_indices = np.where(np.abs(time_vector) > 90)
    # discontinuity_indices = [0,3]
    time_discontinuity = []
    time_discontinuity.append(time_vector[([0,2])])
    print(time_discontinuity)

def plot_sto_file(file_path, columns_to_plot = 'all', timeNorm = False):
    # Load the .mat file
    data = bp.import_sto_data(file_path)
    
    if timeNorm:
        data = bp.normalize_time(data)

    if columns_to_plot == 'all':
        columns_to_plot = data.columns
    
    ncols, nrows = bp.calculate_axes_number(len(columns_to_plot))
    

# END