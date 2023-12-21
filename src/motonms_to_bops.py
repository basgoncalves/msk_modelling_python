import os
# input_data_folder = input("Enter the path to the InputData folder: ")
# elaborated_data_folder = input("Enter the path to the ElaboratedData folder: ")

input_data_folder = r'D:\3-PhD\Data\MocapData\InputData'

session_name = 'pre'

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
        
    # Check if the subject folder exists
    if os.path.isdir(session_path):
        pass
    else:
        session_path = None
        
    return session_path 
        

for folder_name in os.listdir(input_data_folder):
    folder_path = os.path.join(input_data_folder, folder_name)
    
    session_path = check_session_exists(folder_path,session_name)
    
    if session_path:
        print(session_path)
        



