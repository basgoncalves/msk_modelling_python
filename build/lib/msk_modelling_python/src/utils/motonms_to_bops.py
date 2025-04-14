import os
import shutil
# input_data_folder = input("Enter the path to the InputData folder: ")
# elaborated_data_folder = input("Enter the path to the ElaboratedData folder: ")

# data paths 
input_data_folder = r'D:\3-PhD\Data\MocapData\InputData'
elaborated_data_folder =input_data_folder.replace('InputData','ElaboratedData')
destination_folder = r'C:\Git\research_documents\Uvienna\Bachelors_thesis_supervision\2023W\ksenija_jancic_spowi\data\Mocap'

subject_name = ['009','037']

session_name = 'pre'

trials_to_copy = ['Run_baseline1','Run_baseline2','Run_baselineA1','Run_baselineB1','Run_baselineB1','Run_baselineB2']

def check_session_exists(folder_path,session_name):
    if os.path.isdir(folder_path):
        subject_path = os.path.join(folder_path, session_name)
    else:
        session_path = None

    # Check if the subject folder exists
    subject_path = os.path.join(folder_path, session_name)
    if os.path.isdir(subject_path):
        session_path = os.path.join(folder_path, session_name)
    else:
        session_path = None

    return session_path

def create_folder(folder_path):
    if not os.path.isdir(folder_path):
        os.mkdir(folder_path)

def copy_files_to_destination(session_path, destination_folder, trials_to_copy):
    for train_name in trials_to_copy:
        # create trial paths
        c3d_trial = os.path.join(session_path, train_name + '.c3d')
        ik_trial  = os.path.join(session_path, train_name + '.mot')
        destination_trial = os.path.join(destination_folder, train_name + '.c3d')

        if os.path.isfile(c3d_trial) and not os.path.isfile(destination_trial):
            create_folder(destination_folder)                    
            shutil.copy(c3d_trial, destination_trial) # Copy c3d to new folder
            exit()
            # Copy emg to new folder
            # Copy kinematics to new folder
        

for folder_name in os.listdir(input_data_folder):
    folder_path = os.path.join(input_data_folder, folder_name)

    # create new sessions paths
    session_path = check_session_exists(folder_path,session_name)
    new_session_path = os.path.join(destination_folder, folder_name)

    if session_path and any(name in session_path for name in subject_name):
        print('Copying files for subject {}'.format(folder_name))
        # copy_files_to_destination(session_path,new_session_path,trials_to_copy)
    else:
        print('Session not found for subject {}'.format(folder_name))




