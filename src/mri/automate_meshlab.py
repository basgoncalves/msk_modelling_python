import pymeshlab as ml
import os 
import trimesh
from tkinter import filedialog
import time

def remesh_stl_file(stl_path=""):

    if stl_path == "":
        stl_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])
    
    if os.path.exists(stl_path) == False:
        raise FileNotFoundError("STL file does not exist")
    
    if stl_path.lower().__contains__("cartilage"):
        raise ValueError("STL file contains cartilage")
    
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

    # copy uniform resampling code 
    ms = ml.MeshSet()
    ms.load_new_mesh(stl_path)
    ms.generate_resampled_uniform_mesh(cellsize = ml.PercentageValue(0.499923))

    ms.save_current_mesh(new_stl_path)
    print("Uniform resampling done")
    print("New STL file saved at: ", new_stl_path)


if __name__ == "__main__":
    # example 
    
    main_folder = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\079\Meshlab_BG"
    
    dir_list = os.listdir(main_folder)
    
    # select only stl files thet contain "Segmentation"
    dir_list = [file for file in dir_list if file.endswith(".stl") and "Segmentation" in file]
    
    print(dir_list)
    print("\n")
    
    for file in dir_list:
        
        answer = input("Do you want to remesh the file: " + file + "? Y(default) / N   " )
        if answer.lower() == "n":
            continue
        
        try:
            stl_path = os.path.join(main_folder, file)
            remesh_stl_file(stl_path=stl_path)
            print("\n")
        except Exception as e:
            print("Error: ", e)
            continue