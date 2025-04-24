import os
import h5py
import numpy as np
import pandas as pd
import json
import seaborn as sns
from scipy.stats import sem

MODULE_DIR = os.path.dirname(__file__)


def create_template_hdf5_file():
    # Create a new HDF5 file as example
    file_path = os.path.join(MODULE_DIR, "project_data.h5")
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
                    
                    # Simulated dataset for 10 muscles with 100 time points
                    data = np.random.rand(100, 10)  # Example: 100 time points, 10 muscles
                    dataset = trial_group.create_dataset("muscle_forces", data=data)
                    dataset.attrs["columns"] = [f"muscle_{i}" for i in range(1, 11)]  # Example muscle names
                    
                    dataset.attrs["description"] = f"Subject {subject_id}, Session {session_id}, Trial {trial_id}"
                    dataset.attrs["units"] = "N"  # Example units
                    dataset.attrs["time"] = np.arange(0, 100)  # Example time points
                    dataset.attrs["sampling_rate"] = 100  # Example sampling rate
                    

    print(f"HDF5 file saved at {file_path}")
    
def load_hdf5_file(file_path):
    """
    Load an HDF5 file and convert its structure into a dictionary of DataFrames.
    
    structured_data = load_hdf5_file("project_data.h5")
    
    """
    
    
    
    # Load the HDF5 file and convert its structure into a dictionary of DataFrames
    with h5py.File(file_path, "r") as h5file:
        print("Converting HDF5 file structure to DataFrames...")

        h5_dict = {}

        def extract_data(name, obj):
            if isinstance(obj, h5py.Dataset):
                # Convert datasets to DataFrames
                group_path = "/".join(name.split("/")[:-1])
                if group_path not in h5_dict:
                    h5_dict[group_path] = []
                h5_dict[group_path].append({
                    "name": name.split("/")[-1],
                    "data": obj[()],
                    "attrs": dict(obj.attrs)
                })

        h5file.visititems(extract_data)

        # Convert the collected data into DataFrames
        structured_data = {}
        for group, datasets in h5_dict.items():
            rows = []
            for dataset in datasets:
                rows.append({
                    "dataset_name": dataset["name"],
                    "data": dataset["data"],
                    **dataset["attrs"]
                })
            structured_data[group] = pd.DataFrame(rows)

    # Example: Accessing structured data
    # for group, df in structured_data.items():
    #     print(f"Group: {group}")
    #     print(df.head())
    return structured_data

def load_json_file(json_file_path):
    """
    Load a JSON file and convert its structure into a dictionary.
    
    Args:
        json_file_path (str): Path to the JSON file.
        
    Returns:
        dict: Dictionary containing the data from the JSON file.
    """
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)
    
    return data

def load_mot_file(mot_file_path):
    """
    Load a .mot file and convert its structure into a dictionary.
    
    Args:
        mot_file_path (str): Path to the .mot file.
        
    Returns:
        dict: Dictionary containing the data from the .mot file.
    """
    
    # Read the .mot file and extract the data
    with open(mot_file_path, "r") as mot_file:
        lines = mot_file.readlines()
    
    # Find the endheader line and extract the data from there
    endheader_index = lines.index("endheader\n")
    
    # Load the data into a DataFrame, skipping the header lines
    data = pd.read_csv(mot_file_path, delim_whitespace='\t', skiprows=endheader_index + 1)
    
    return data

def create_osim_trial_json_file(trial_folder):
    """
    Create a JSON file for a given trial folder.
    
    Args:
        trial_folder (str): Path to the trial folder.
        trial_name (str): Name of the trial.
    """
    # Create a dictionary to hold the data
    data = {
        "trial_folder": trial_folder,
        "markers": os.path.join(trial_folder, "markers.mot"),
        'ground_reaction_forces': os.path.join(trial_folder, "ground_reaction_forces.mot"),
        'joint_angles': os.path.join(trial_folder, "joint_angles.mot"),
        "joint_moments": os.path.join(trial_folder, "joint_moments.sto"),
        'emg_processed': os.path.join(trial_folder, "emg.mot"),
        'muscle_forces': os.path.join(trial_folder, "muscle_forces.sto"),
        'joint_reaction_loads': os.path.join(trial_folder, "joint_reaction_loads.sto"),
    }
    
    # Save the data as a JSON file
    json_file_path = os.path.join(trial_folder, f"settings.json")
    with open(json_file_path, "w") as json_file:
        json.dump(data, json_file)
    
    print(f"JSON file created at {json_file_path}")
    
    # Return the path to the created JSON file
    trial_info = load_json_file(json_file_path)
    
    return json_file_path, trial_info

def osim_to_hdf5(simulation_dir, subjects = 'all', sessions='all', tasks='all'):
    '''
    convert osim simulation data to hdf5 format
    simulation_dir: str, path to the simulation data directory
    '''
    # 1. Check if the directory exists
    if not os.path.exists(simulation_dir):
        raise FileNotFoundError(f"The directory {simulation_dir} does not exist.")
    
    # 2. Check if the directory is empty and if subjects inputed exists
    if subjects == 'all':
        subjects = os.listdir(simulation_dir)
    else:
        subjects = subjects
    
    if len(subjects) == 0:
        raise FileNotFoundError(f"The directory {simulation_dir} is empty.")
        
    # 3. check if the subjects exist 
    for subject in subjects:
        if not os.path.exists(os.path.join(simulation_dir, subject)):
            print(f"Warning: Subject {subject} does not exist in the directory {simulation_dir}.")
            
    # 4. Initialize the HDF5 file and start importing by looping through the subjects
    hdf5_file_path = os.path.join(simulation_dir, "project_data.h5")
    with h5py.File(hdf5_file_path, "w") as h5file:
        for subject in subjects:
            subject_group = h5file.create_group(subject)
            
            if not os.path.isdir(os.path.join(simulation_dir, subject)):
                print(f"Warning: Subject {subject} is not a directory in {simulation_dir}.")
                continue
            
            try:
                sessions = os.listdir(os.path.join(simulation_dir, subject)) 
            except:
                print(f"Warning: The directory {os.path.join(simulation_dir, subject)} does not exist.")
                continue
            
            if len(sessions) == 0:
                print(f"Warning: The directory {os.path.join(simulation_dir, subject)} is empty.")
            
            # if sessions == 'all' use all the folders in the subject directory
            if sessions == 'all':
                sessions = os.listdir(os.path.join(simulation_dir, subject))
            else:
                sessions = sessions
            
            # Loop through the sessions and check if they exist    
            for session in sessions:
                # check if the session exists
                if not os.path.exists(os.path.join(simulation_dir, subject, session)):
                    print(f"Warning: Session {session} does not exist in the directory {os.path.join(simulation_dir, subject)}.")
                    continue
                
                session_group = subject_group.create_group(session)

                tasks = os.listdir(os.path.join(simulation_dir, subject, session)) 
                                
                if len(tasks) == 0:
                    print(f"Warning: The directory {os.path.join(simulation_dir, subject, session)} is empty.")
                
                # is tasks == 'all' use all the folders in the session directory
                if tasks == 'all': 
                    tasks = os.listdir(os.path.join(simulation_dir, subject, session))
                else: 
                    tasks = tasks
                     
                # Loop through the tasks and load the data   
                for task in tasks:
                    
                    task_dir = os.path.join(simulation_dir, subject, session, task)
                    # check if the tasks exist 
                    if not os.path.isdir(task_dir):
                        print(f"Warning: Task {task} does not exist in the directory {os.path.join(simulation_dir, subject, session)}.")
                        continue        
                                    
                    task_group = session_group.create_group(task)
                    
                    # Loop through the files and add them to the HDF5 file
                    try:
                        files = os.listdir(task_dir) 
                    except FileNotFoundError:
                        print(f"Warning: The directory {os.path.join(simulation_dir, subject, session, task)} does not exist.")
                        continue    
                    
                    # Check if the files exist and if they are empty
                    try: 
                        trial_info = load_json_file(os.path.join(task_dir, "settings.json"))
                        
                    except FileNotFoundError:
                        create_osim_trial_json_file(task_dir)
                        trial_info = load_json_file(os.path.join(task_dir, "settings.json"))
                    
                    # Check if the file exists in the trial_info dictionary
                    if trial_info.items() == []:
                        print(f"Warning: The directory {os.path.join(simulation_dir, subject, session, task)} is empty.")
                        continue
                    
                    # Loop through the files in the trial and add them to the HDF5 file
                    for file in files:
                        
                        file_path = os.path.join(simulation_dir, subject, session, task, file)
                        file_exist = False

                        # Check if the file exists in the trial_info dictionary
                        for key,val in trial_info.items():
                            if file in val:
                                file_exist = True
                                break
                        
                        # Try loading the file and adding it to the HDF5 file    
                        if file_exist:
                            try:
                                data = load_mot_file(file_path)
                                # breakpoint()   
                                # Create a dataset in the HDF5 file for each file
                                dataset_name = os.path.splitext(file)[0]  # Remove the file extension
                                dataset = task_group.create_dataset(dataset_name, data=data)
                                dataset.attrs.update({"columns": data.columns.to_list()})
                                print(f"File {file_path} loaded successfully.")
                                     
                            except Exception as e:
                                print(f"Error loading file {file_path}")
                                
        # Save the HDF5 file
        h5file.close()
        print(f"HDF5 file saved at {hdf5_file_path}")

def verify_h5(hdf5_file_path, subject_id='009', session_id='pre', task_id='RunA1'):
    """
    Verify the structure of the HDF5 file and print the column titles of the dataset.
    """
    # Verify the HDF5 file
    with h5py.File(hdf5_file_path, "r") as h5file:
        if subject_id in h5file:
            if session_id in h5file[subject_id]:
                if task_id in h5file[subject_id][session_id]:
                    print(f"Group {subject_id}/{session_id}/{task_id} found.")
                else:
                    print(f"Group {subject_id}/{session_id}/{task_id} not found.")
                    
                if "joint_moments" in h5file[subject_id][session_id][task_id]:
                    dataset = h5file[subject_id][session_id][task_id]["joint_moments"]
                    print(f"Dataset 'joint_moments' found with columns: {dataset.attrs['columns']}")
                else:
                    print(f"Dataset 'joint_moments' not found in {subject_id}/{session_id}/{task_id}.")
            else:
                print(f"Session {session_id} not found for subject {subject_id}.")
        else:
            print(f"Subject {subject_id} not found in the HDF5 file.")
            
def mean_h5_attribute(hdf5_file_path, subject_info_csv, splitby = "Group", categories_to_include = ['FAIS', 'CAM'], attribute = 'joint_moments'):
    """
    Calculate the mean of a specific attribute in the HDF5 file.
    """
    # Load the subject information from the CSV file
    subject_info = pd.read_csv(subject_info_csv)
    
    with h5py.File(hdf5_file_path, "r") as h5file:
        import matplotlib.pyplot as plt

        # Create a directory to save the plots
        plot_dir = os.path.join(os.path.dirname(hdf5_file_path), "plots")
        os.makedirs(plot_dir, exist_ok=True)
                    
        for subject_id in h5file.keys():  # Loop through all subjects
            for session_id in h5file[subject_id].keys():  # Loop through all sessions
                session_data = []
                if subject_id in subject_info["Subject"].values:
                    
                    group = subject_info.loc[subject_info["Subject"] == subject_id, splitby].values[0]
                    if group in categories_to_include:
                        
                        for task_id in h5file[subject_id][session_id].keys():  # Loop through all tasks
                            breakpoint()
                            if attribute in h5file[subject_id][session_id][task_id]:
                                dataset = h5file[subject_id][session_id][task_id][attribute]
                                data = dataset[:]
                                columns = dataset.attrs["columns"]
                                breakpoint()
                                session_data.append({
                                    "subject_id": subject_id,
                                    "group": group,
                                    "task_id": task_id,
                                    "data": data,
                                    "columns": columns
                                })

                # Combine data for plotting
                if session_data:
                    combined_data = []
                    for entry in session_data:
                        for i, column in enumerate(entry["columns"]):
                            combined_data.append({
                                "Group": entry["group"],
                                "Column": column,
                                "Value": np.mean(entry["data"][:, i])
                            })

                    combined_df = pd.DataFrame(combined_data)

                # Plot mean and confidence interval
                plt.figure(figsize=(12, 6))
                sns.lineplot(
                    data=combined_df,
                    x="Column",
                    y="Value",
                    hue="Group",
                    ci="sd",
                    marker="o"
                )
                plt.title(f"Mean and Confidence Interval for Session {session_id}")
                plt.xlabel("Columns")
                plt.ylabel("Mean Value")
                plt.legend(title="Group")
                plt.xticks(rotation=45)
                plt.tight_layout()

                # Save the plot
                plot_path = os.path.join(plot_dir, f"session_{session_id}_mean_ci.png")
                plt.savefig(plot_path)
                plt.close()
                print(f"Plot saved at {plot_path}")

if __name__ == "__main__":
    SIMULATIONS_DIR = r'C:\Git\research_data\Projects\runbops_FAIS_phd\simulations'
    SUBJECT_INFO_CSV = r'C:\Git\research_data\Projects\runbops_FAIS_phd\subject_info.csv'
    TEMPLATE_HDF5 = os.path.join(MODULE_DIR, "project_data.h5")

    if True: create_template_hdf5_file()
    
    if False: structured_data = load_hdf5_file(os.path.join(MODULE_DIR, "project_data.h5"))
    
    if True:     
        osim_to_hdf5(SIMULATIONS_DIR, subjects = 'all', sessions='all', tasks='all')
        # osim_to_hdf5(SIMULATIONS_DIR, subjects = ['009','010'], sessions='all', tasks='all')

    if False:
        hdf5_file_path = os.path.join(SIMULATIONS_DIR, "project_data.h5")
        verify_h5(hdf5_file_path)
        
    if False:
        subject_info = pd.read_csv(SUBJECT_INFO_CSV)
        print(subject_info.head())
        print(subject_info["Group"])
        print(subject_info.columns)
        
    if False:
        hdf5_file_path = os.path.join(SIMULATIONS_DIR, "project_data.h5")
        mean_h5_attribute(hdf5_file_path, SUBJECT_INFO_CSV, splitby = "Group", categories_to_include = ['FAIS', 'FAIM'], attribute = 'joint_moments')