import os
import trimesh

# may need to pip install "pyglet<2"


mesh_path = r"c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\079\Meshlab_BG\acetabulum_l.stl"

if os.path.exists(mesh_path) == False:
    raise FileNotFoundError("STL file does not exist")

# open and viualise the stl file (ask user for 3 clicks for 3 acetabular points)
mesh = trimesh.load(mesh_path)
mesh.show()

# ask user for 3 clicks for 3 acetabular points


# get the 3 points


# calculate the acetabular index