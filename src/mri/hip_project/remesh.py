import pymeshlab as ml
import os 
import tkinter as tk
from tkinter import filedialog
import pandas as pd
import time


def remesh_stl_file(stl_path="", new_stl_path="", resampling_cell_size=0.499923):

    if stl_path == "":
        stl_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])
    
    if os.path.exists(stl_path) == False:
        raise FileNotFoundError("STL file does not exist")
    
    # copy uniform resampling code 
    ms = ml.MeshSet()
    ms.load_new_mesh(stl_path)
    ms.generate_resampled_uniform_mesh(cellsize = ml.PercentageValue(resampling_cell_size))

    ms.save_current_mesh(new_stl_path)
    print("Uniform resampling done")
    print("New STL file saved at: ", new_stl_path)

def create_new_folder_names(stl_path):
    if stl_path.lower().__contains__("cartilage"):
        raise ValueError("STL file contains cartilage (edit the code in line 35 to fix)")
    
    elif any(substring in stl_path.lower() for substring in ["femur_l", "l_femur"]):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "femoral_head_l.stl" 
    elif any(substring in stl_path.lower() for substring in ["femur_r", "r_femur"]):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "femoral_head_r.stl"
    elif any(substring in stl_path.lower() for substring in ["pelvis_r", "r_pelvis"]):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "acetabulum_r.stl"
    elif any(substring in stl_path.lower() for substring in ["pelvis_l", "l_pelvis"]):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "acetabulum_l.stl"
    else:
        raise ValueError("STL file does not contain femur or pelvis")
    
    return new_stl_path
    
def select_multiple_folders():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

def ask_to_continue(mode):
    
    print("Mode: ", mode)
    
    answer = input("Do you want to continue? Y (or other) / N   " )
    if answer.lower() == "n":
        # print in red and exit 
        print("\033[91mStopped by the user\033[0m")
        exit()
    else:
        return True
    
def run(subjects_to_run, mode, replace, resampling_cell_size):
    
    if mode == "manual":
        file_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])
        new_file_path = create_new_folder_names(file_path)
        remesh_stl_file(stl_path=file_path, new_stl_path=new_file_path)
    
    # Select multiple folders and run the remeshing
    elif mode == "semi-auto" or mode == "batch":
        
        subjects_folder = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage'
    
        if not os.path.exists(subjects_folder):
            raise FileNotFoundError("Subjects folder does not exist")
        
        # Create a dataframe with all the subjects, paths, and files
        paths = pd.DataFrame(columns=["Subject", "Path", "Files"])
        
        for subject_id in os.listdir(subjects_folder):
            if subject_id not in subjects_to_run and subjects_to_run != []:
                continue
            elif os.path.isdir(os.path.join(subjects_folder, subject_id)) == False:
                continue
            
            main_folder = fr"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\{subject_id}\Meshlab_BG"
            dir_list = os.listdir(main_folder)
            dir_list = [file for file in dir_list if file.endswith(".stl") and "Segmentation" in file]
            #make the list vertical
            dir_list = [file for file in dir_list if file.endswith(".stl") and "Segmentation" in file]
            
            paths = pd.concat([paths, pd.DataFrame([{"Subject": subject_id, "Path": main_folder, "Files": dir_list}])], ignore_index=True)
        print(paths)
        
        ask_to_continue(mode)
        
        for i, subject_id in enumerate(paths["Subject"]):
            for file in paths["Files"][0]:
                
                file_path = os.path.join(paths["Path"][i], file)
                print("File path: ", file_path)

                ## Ask the user if they want to remesh the file 
                if mode == "semi-auto":
                    answer = input("Do you want to remesh the file: " + file + "? Y(default) / N   " )
                    if answer.lower() == "n":
                        continue
                
                # Remesh the file
                try:
                    new_file_path = create_new_folder_names(file_path)
                    if os.path.exists(new_file_path) and replace == False:
                        print("New file already exists: " + new_file_path)
                        continue
                        
                    remesh_stl_file(stl_path=file_path, new_stl_path=new_file_path, resampling_cell_size=resampling_cell_size)
                    print("\n")
                except Exception as e:
                    print("Error: ", e)
                    continue
            
            
            print("\n")
            print("Finished remeshing subject: ", subject_id)
            time.sleep(1)
    else:
        print("Mode not recognized")



if __name__ == "__main__":
    # example 
    
    print("Remeshing STL file in this code:")
    print('Rules for remeshing:')
    print('1. The STL file should contain either femur or pelvis')
    print('2. The STL file name should not contain "cartilage"')
    print('3. The new STL file will be saved in the same folder as the original file')
    print('4. The new STL file will be named as "femoral_head_l.stl", "femoral_head_r.stl", "acetabulum_l.stl" or "acetabulum_r.stl"')
    print('5. The new STL file will be saved only if it does not already exist')
    print('6. The new STL file will be saved with uniform resampling')
    print('7. The new STL file will be saved with a cell size of 0.499923')
    
    print("To change the naming rules, edit function 'create_new_folder_names'")
    
    print("Change the mode to 'manual', 'semi-auto' or 'batch' in the code to run the remeshing")

    subjects_to_run = []
    mode = "batch" # "manual", "semi-auto" or "batch"
    replace = False
    resampling_cell_size = 0.499923
    
    run(subjects_to_run, mode, replace, resampling_cell_size)
    
    