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

def calculate_area(points):
  """
  Calculates the surface area of a 3D mesh defined by a list of vertices.

  Args:
    points: A NumPy array of shape (n, 3) where n is the number of vertices, 
            representing the (x, y, z) coordinates of each vertex.

  Returns:
    The surface area of the mesh.
  """

  # Create a list of triangles by connecting adjacent vertices
  triangles = []
  for i in range(len(points) - 2):
    triangles.append([points[i], points[i+1], points[i+2]])

  # Calculate the area of each triangle using Heron's formula
  total_area = 0
  for triangle in triangles:
    a = np.linalg.norm(triangle[1] - triangle[0])
    b = np.linalg.norm(triangle[2] - triangle[1])
    c = np.linalg.norm(triangle[0] - triangle[2])
    s = (a + b + c) / 2
    area = np.sqrt(s * (s - a) * (s - b) * (s - c))
    total_area += area

  return total_area

# Replace for the paths of the pelvis and femur meshes
pelvis_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\acetabulum_l.stl'
femur_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\femoral_head_l.stl'

# Paths to save the figures
current_path = os.path.dirname(os.path.abspath(__file__))
figures_path = os.path.join(os.path.dirname(femur_path), 'figures')
if os.path.exists(figures_path) == False:
    os.mkdir(figures_path)

# Load the meshes
pelvis = trimesh.load(pelvis_path)
femur = trimesh.load(femur_path)

threshold_list = [3, 5, 10, 15]
for threshold in threshold_list:
    
    # calculate the distance between the meshes
    distance_femur = pelvis.nearest.on_surface(femur.vertices)
    distance_pelvis = femur.nearest.on_surface(pelvis.vertices)

    # get logical array of the distances
    is_covered_femur = distance_femur[1] < threshold
    
    # calculate the area of the covered faces
    covered_area = calculate_area(femur.vertices[is_covered_femur])

    # if distance is bigger than the threshold, the distance is set to 0
    distance_femur[1][distance_femur[1] >= threshold] = 0
    distance_pelvis[1][distance_pelvis[1] >= threshold] = 0
    
    # plot the meshes with the distance color map
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    plt.subplots_adjust(top=1.0, bottom=0.0, left=0.0, right=1.0, hspace=0.0, wspace=0.0)
    ax.scatter(femur.vertices[:,0], femur.vertices[:,1], femur.vertices[:,2],c='grey', s=1, alpha=0.1) # plot all the points in grey
    ax.view_init(elev=45, azim=-36, roll=0) # set the view to front
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    plt.subplots_adjust(top=1.0, bottom=0.0, left=0.0, right=1.0, hspace=0.0, wspace=0.0)
    ax.scatter(femur.vertices[:,0], femur.vertices[:,1], femur.vertices[:,2],c='grey', s=1, alpha=0.1) # plot all the points in grey
    ax.view_init(elev=0, azim=45, roll=0) # set the view to side
    
    plt.show()
    
    ax.scatter(pelvis.vertices[:,0], pelvis.vertices[:,1], pelvis.vertices[:,2],c='grey', s=1, alpha=0.1) 
    
    ax.scatter(femur.vertices[is_covered_femur,0], femur.vertices[is_covered_femur,1], femur.vertices[is_covered_femur,2],c='red') # plot the points that are below the threshold in red
    
   
    
    plt.show()

    plt.title(f"Threshold: {threshold}")
    
    # add text with covered area to the top right corner outside the plot
    import pdb; pdb.set_trace()
    plt.text(1, 1, f'Covered Area: {covered_area:.2f}', ha='right', va='top', transform=ax.transAxes)
    
    # save the figure
    save_path = os.path.join(figures_path, f"distance_{threshold}.png")
    plt.savefig(save_path)
    
    print(f"Threshold: {threshold} - Covered Area: {covered_area:.2f}")
    print(f"Figure saved at: {save_path}")

