import os
import trimesh
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import colors
from trimesh import proximity
import pandas as pd
# import Seaborn as sns 
# may need to pip install "pyglet<2", "rtree", "open3d" to run this example

class Mesh():
    def __init__(self, path = None):
        self.path = path
        if path == None:
            self.Trimesh = None
        else:
            print('Loading mesh from: ', path)
            self.Trimesh = trimesh.load(path)
            self.vertices = self.Trimesh.vertices
    
    def show_3d_mesh(self):
        if os.path.exists(self.path) == False:
            raise FileNotFoundError("STL file does not exist")
        self.Trimesh.show()
        
    def centroid(self):
        return np.mean(self.vertices, axis=0)
    
    def split_mesh(self, n_chunks):
        chunk_size = len(self.vertices) // n_chunks
        mesh_list = []
        # Split the vertices into chunks
        for i in range(0, len(self.vertices), chunk_size):

            # Check if the chunk size is bigger than the remaining vertices
            if i+chunk_size > len(self.vertices):
                chunk_size = len(self.vertices) - i
            
            # Create a new mesh with the chunk
            try:
                new_mesh = Mesh()
                chunk_vertices = self.vertices[i:i + chunk_size]
                chunk_faces = self.Trimesh.faces[np.all(np.isin(self.Trimesh.faces, np.arange(i, i + chunk_size)), axis=1)]
                chunk_faces -= i  # Adjust face indices to match the chunk vertices
                new_mesh.Trimesh = trimesh.Trimesh(vertices=chunk_vertices, faces=chunk_faces)
                new_mesh.vertices = new_mesh.Trimesh.vertices
                mesh_list.append(new_mesh)
            except Exception as e:
                print(f'Error in chunk {i}')
                print(e)
                import pdb; pdb.set_trace()   
                
        return mesh_list
    
    def add_to_current_plot(self, color='b'):
        
        # check if there is a current figure
        if plt.fignum_exists(1) == False:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
        else:
            fig = plt.gcf()
        
        # activate the current figure
        ax = plt.gca()
        ax.scatter(self.vertices[:, 0], self.vertices[:, 1], self.vertices[:, 2], c=color)
        
    def distance_to_point(self, mesh):
        return np.linalg.norm(self.centroid() - mesh.centroid())

def print_loading_bar(current, total):
    percentage = (current / total) * 100
    bar_length = 30
    block = int(round(bar_length * current / total))
    bar = "#" * block + "-" * (bar_length - block)
    print(f'Loading: [{bar}] {percentage:.2f}% ({current}/{total})')

def save_3d_plot(fig, path):
    if os.path.exists(path):
        answer = input(f"File {path} already exists. Press Enter to overwrite (N to cancel)").lower()
        if answer == 'n':
            return
    # save front view
    fig.savefig(path)
    
    # save side view
    ax.view_init(elev=0, azim=90)
    fig.savefig(path.replace('.png', '_side.png'))
    
    # save top view
    ax.view_init(elev=90, azim=0)
    fig.savefig(path.replace('.png', '_top.png'))
    
    # save isometric view
    ax.view_init(elev=30, azim=30)
    fig.savefig(path.replace('.png', '_iso.png'))
    

# Replace for the paths of the pelvis and femur meshes
pelvis_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\acetabulum_l.stl'
femur_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\femoral_head_l.stl'

n_chunks = 10
threshold_centroids = 90 

# Paths to save the figures
current_path = os.path.dirname(os.path.abspath(__file__))
figures_path = os.path.join(current_path, 'figures')
if os.path.exists(figures_path) == False:
    os.mkdir(figures_path)

# Load the meshes
pelvis = Mesh(pelvis_path)
femur = Mesh(femur_path)

pelvis = trimesh.load(pelvis_path)
femur = trimesh.load(femur_path)

distance = proximity.signed_distance(pelvis, femur.vertices)

# calculate the distance between the meshes
distance_femur = pelvis.nearest.on_surface(femur.vertices)
distance_pelvis = femur.nearest.on_surface(pelvis.vertices)

# make all distances smaller than the threshold red
distance_femur[2][distance_femur[2] < threshold_centroids] = 1
distance_pelvis[2][distance_pelvis[2] < threshold_centroids] = 1

# make all distances bigger than the threshold gray
distance_femur[2][distance_femur[2] >= threshold_centroids] = 0
distance_pelvis[2][distance_pelvis[2] >= threshold_centroids] = 0

import pdb; pdb.set_trace()
# plot the distance
fig = plt.figure()
ax = plt.subplot(111, projection='3d')
ax.scatter(femur.vertices[:,0], femur.vertices[:,1], femur.vertices[:,2],c=distance_femur[2], cmap='Reds')
ax.scatter(pelvis.vertices[:,0], pelvis.vertices[:,1], pelvis.vertices[:,2],c=distance_pelvis[2])
# add colorbar
norm = colors.Normalize(vmin=distance.min(), vmax=distance.max())
sm = plt.cm.ScalarMappable(cmap='Reds', norm=norm)

plt.show()

distance_save_path = os.path.join(current_path, 'distance.csv')
pd.DataFrame(distance[2]).to_csv(distance_save_path)
