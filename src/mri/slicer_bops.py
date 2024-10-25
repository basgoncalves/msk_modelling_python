import slicer
import msk_modelling_python as msk
import slicer.utils_testing


def open_scene(file_path):
    """
    Opens a .mrb scene file in 3D Slicer.

    Parameters:
    file_path (str): The path to the .mrb file to be opened.
    """
    slicer.util.loadScene(file_path)
    return  scene

# Example usage
if __name__ == "__main__":
    # scene_file_path = msk.ut.select_file()
    scene_file_path = r'"C:\Users\Bas\ucloud\MRI_segmentation_BG\Scenes\009.mrb"'
    scene = open_scene(scene_file_path)
# Python Slicer
# import slicer 
# scene_file_path = r'"C:\Users\Bas\ucloud\MRI_segmentation_BG\Scenes\009.mrb"'
# slicer.util.loadScene(scene_file_path)