import numpy as np



# Example usage
filename = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\Segmentation_L_femur_mesh.stl'
vertices = load_stl_vertices(filename)

print("Number of vertices:", len(vertices))
print("Example vertex:", vertices)