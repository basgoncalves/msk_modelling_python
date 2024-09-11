import pymeshlab as ml
import os 
import trimesh
from tkinter import filedialog

def remesh_stl_file(stl_path=""):

    if stl_path == "":
        stl_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])

    if not os.path.exists(stl_path):
        print("STL file does not exist")
        exit()
    elif stl_path.__contains__("femur_l"):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "femoral_head_l.stl" 
    elif stl_path.__contains__("femur_r"):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "femoral_head_r.stl"
    elif stl_path.__contains__("pelvis_r"):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "acetabulum_r.stl"
    elif stl_path.__contains__("pelvis_l"):
        new_stl_path = os.path.dirname(stl_path) + os.sep + "acetabulum_l.stl"
    else:
        print("STL file does not contain femur or pelvis")
        exit()

    # copy uniform resampling code 
    ms = ml.MeshSet()
    ms.load_new_mesh(stl_path)
    ms.generate_resampled_uniform_mesh(cellsize = ml.PercentageValue(0.499923))

    ms.save_current_mesh(new_stl_path)
    print("Uniform resampling done")
    print("New STL file saved at: ", new_stl_path)


if __name__ == "__main__":
    # example stl_path = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\024\Segmentation_bg_femur_l.stl"
    
    remesh_stl_file()