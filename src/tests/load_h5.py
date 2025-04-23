import os
import h5py
import pandas as pd

def load_mot_to_h5(mot_file_path, h5_file_path, dataset_name="emg_data"):
    """
    Loads data from a .mot file into an HDF5 file.

    Args:
        mot_file_path (str): The full path to the .mot file.
        h5_file_path (str): The full path to the HDF5 file to be created or appended to.
        dataset_name (str): The name of the dataset to be created within the HDF5 file.
                             It will be placed in a group structure derived from the
                             .mot file path (e.g., /009/pre/sprint_1/).
    """
    try:
        # Load the .mot file using pandas
        with open(mot_file_path, 'r') as f:
           lines = f.readlines()
        endheader_index = lines.index("endheader\n")
        
        data = pd.read_csv(mot_file, sep='\t', skiprows=endheader_index + 1)
    except Exception as e:
        print(f"Error reading .mot file: {e}")
        return
    
    try:
        data.to_hdf(h5_file_path, key=dataset_name, mode='a', append=True)
    except Exception as e:
        print(f"Error saving h5 file: {e}")
        return
# Example usage:
mot_file = r"C:\Git\research_data\Projects\runbops_FAIS_phd\simulations\009\pre\sprint_1\emg.mot"
h5_file = mot_file.replace('.mot', '.h5')
load_mot_to_h5(mot_file, h5_file, dataset_name="emg")