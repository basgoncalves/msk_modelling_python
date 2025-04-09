import os
import h5py
import numpy as np

parent_dir = os.path.dirname(__file__)

# Create a new HDF5 file
file_path = os.path.join(parent_dir, "project_data.h5")
with h5py.File(file_path, "w") as h5file:
    # Add multiple subjects
    for subject_id in range(1, 4):  # Example: 3 subjects
        subject_group = h5file.create_group(f"subject_{subject_id}")
        
        # Add sessions for each subject
        for session_id in range(1, 3):  # Example: 2 sessions per subject
            session_group = subject_group.create_group(f"session_{session_id}")
            
            # Add trials for each session
            for trial_id in range(1, 4):  # Example: 3 trials per session
                trial_group = session_group.create_group(f"trial_{trial_id}")
                
                # Add some example data to each trial
                trial_group.create_dataset("data", data=np.random.rand(100))
                trial_group.attrs["description"] = f"Subject {subject_id}, Session {session_id}, Trial {trial_id}"

print(f"HDF5 file saved at {file_path}")