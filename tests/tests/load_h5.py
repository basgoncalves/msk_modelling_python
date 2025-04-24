import os
import h5py
import pandas as pd
import h5py
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
hdf5_file_path = os.path.join(current_dir, 'project_data.h5')
subject_id = "subject_1"
session_id = "session_1"
task_id = "trial_1"
dataset_name = "muscle_forces"

with h5py.File(hdf5_file_path, 'r') as hf:
    if subject_id in hf and session_id in hf[subject_id] and task_id in hf[subject_id][session_id] and dataset_name in hf[subject_id][session_id][task_id]:
        dataset = hf[subject_id][session_id][task_id][dataset_name]
        data = dataset[:]  # Load the numerical data
        columns = dataset.attrs['columns']  # Get the column names attribute
        df = pd.DataFrame(data, columns=columns)
        print(df.head()) # Display the DataFrame with headers
    else:
        print("Dataset not found in the HDF5 file.")
