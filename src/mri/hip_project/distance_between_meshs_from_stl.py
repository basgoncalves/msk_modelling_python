import os
import trimesh
import numpy as np
from matplotlib import pyplot as plt
# may need to pip install "pyglet<2" and "rtree" to run this example

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
            
            # Create a new mesh with the chunk
            new_mesh = Mesh()
            import pdb; pdb.set_trace()
            new_mesh.Trimesh = trimesh.Trimesh(vertices=self.vertices[i:i+chunk_size], faces=self.Trimesh.faces)
            mesh_list.append(new_mesh)
        
        return [self.vertices[i:i+chunk_size] for i in range(0, len(self.vertices), chunk_size)]
    
    def distance_to_point(self, mesh):
        return np.linalg.norm(self.centroid() - mesh.centroid())

def print_loading_bar(current, total):
    percentage = (current / total) * 100
    bar_length = 30
    block = int(round(bar_length * current / total))
    bar = "#" * block + "-" * (bar_length - block)
    print(f'Loading: [{bar}] {percentage:.2f}% ({current}/{total})')
    
# Replace for the paths of the pelvis and femur meshes
pelvis_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\Segmentation_r_pelvis.stl'
femur_path = r'c:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\048\Meshlab_BG\coverage_stick_method\Segmentation_r_femur.stl'

n_chunks = 10
threshould = 90

# Paths to save the figures
current_path = os.path.dirname(os.path.abspath(__file__))
figures_path = os.path.join(current_path, 'figures')

# Load the meshes
pelvis = Mesh(pelvis_path)
femur = Mesh(femur_path)

# Calculate the distance between the meshes using the signed distance function from trimesh
print('Calculating distance between meshes ...')


pelvis_chunks = pelvis.split_mesh(n_chunks)
import pdb; pdb.set_trace()
# Print the number of vertices of each mesh
print(f'pelvis vertices: {pelvis.vertices.shape}')
print(f'femur vertices: {femur.vertices.shape}')

# Flatten the vertices to calculate the distances
flattened_pelvis = pelvis.vertices.reshape(-1, 3)
flattened_femur = femur.vertices.reshape(-1, 3)

# Split Pelvis vertices into chunks
chunk_size = len(flattened_pelvis) // n_chunks
chunk_list_pelvis = [flattened_pelvis[i:i+chunk_size] for i in range(0, len(flattened_pelvis), chunk_size)]

# Split Femur vertices into chunks
chunk_size = len(flattened_femur) // n_chunks
chunk_list_femur = [flattened_femur[i:i+chunk_size] for i in range(0, len(flattened_femur), chunk_size)]

# Calculate the mean of each chunk which would be equivalent to the centroid of the chunk (not the mesh)
chunks_femur_centroids = [np.mean(chunk_femur, axis=0) for chunk_femur in chunk_list_femur]
chunk_pelvis_centroids = [np.mean(chunk_pelvis, axis=0) for chunk_pelvis in chunk_list_pelvis]

# Calculate the distances between the chunks
distances_grid = np.zeros((chunk_size, chunk_size))
distance_between_chunks = []

if len(chunks_femur_centroids) != len(chunk_pelvis_centroids):
    raise ValueError("The number of chunks is different between the femur and pelvis")

# Loop through the chunks to calculate the distances between the centroids of the chunks
for i_femur, femur_chunk in enumerate(chunks_femur_centroids):
    print_loading_bar(i_femur, n_chunks)
    mean_distance = []
    for i_pelvis, pelvis_chunk in enumerate(chunk_pelvis_centroids):
        
        # Calculate the distance between the centroids of the chunks
        distance = np.linalg.norm(femur_chunk - pelvis_chunk)
        
        # Save the distance in the grid
        distances_grid[i_femur, i_pelvis] = np.linalg.norm(femur_chunk - pelvis_chunk)
        
        # Save the mean distance between the chunks
        mean_distance.append(distance)
        
    distance_between_chunks.append(min(mean_distance))
    
    if distance_between_chunks[-1] > threshould:
        import pdb; pdb.set_trace()
        print(f'Chunk {i_femur} is above the threshold')
        
    else:
        pelvis.show_3d_mesh()
        import pdb; pdb.set_trace()
        print(f'Chunk {i_femur} is below the threshold')
    



import pdb; pdb.set_trace()

for i, (chunk_pelvis, chunk_femur) in enumerate(zip(chunk_list_pelvis, chunk_list_femur)):
    print_loading_bar(i, n_chunks)
    
    mean_femur_chuck = np.mean(chunk_femur, axis=0)
    mean_pelvis_chuck = np.mean(chunk_pelvis, axis=0)
    mean_distance = np.linalg.norm(mean_femur_chuck - mean_pelvis_chuck)
    ax = plt.figure().add_subplot(111, projection='3d')
    ax.scatter(chunk_pelvis[:, 0], chunk_pelvis[:, 1], chunk_pelvis[:,2], c='b')
    ax.scatter(chunk_femur[:, 0], chunk_femur[:, 1], chunk_femur[:,2], c='r')

    ax.scatter(mean_pelvis_chuck[0], mean_pelvis_chuck[1], mean_pelvis_chuck[2], c='g', s=100)
    ax.scatter(mean_femur_chuck[0], mean_femur_chuck[1], mean_femur_chuck[2], c='y', s=100)

    fig_path = os.path.join(os.path.dirname(pelvis_path), f'chunk_{i}.png')
    plt.savefig(fig_path)

    import pdb; pdb.set_trace()
    
chunk_pelvis = chunk_list_pelvis[0]
chunk_femur = chunk_list_femur[0]






for chunk_pelvis, chunk_femur in zip(chunk_list_pelvis, chunk_list_femur):
    print(f'Processing chunk {chunk_id}')
    chunk_id += 1
    min_distances = np.full(len(chunk_pelvis), np.inf)
    for i in range(0, len(chunk_femur), chunk_size):
        chunk_femur = flattened_femur[i:i+chunk_size]
        dist_matrix = np.linalg.norm(chunk_pelvis[:, None] - chunk_femur, axis=2)
        min_distances = np.minimum(min_distances, dist_matrix.min(axis=1))
        distances[i:i+chunk_size] = min_distances

for i in range(0, len(flattened_pelvis), chunk_size):
    print_loading_bar(i, len(flattened_pelvis))
    chunk_pelvis = flattened_pelvis[i:i+chunk_size]
    chunk_femur = flattened_femur[i:i+chunk_size]

    # plot the chunk
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(chunk_pelvis[:, 0], chunk_pelvis[:, 1], chunk_pelvis[:, 2], color='b')
    ax.scatter(chunk_pelvis[0, 0], chunk_pelvis[0, 1], chunk_pelvis[0, 2], color='r', s=100)
    ax.scatter(chunk_pelvis[-1, 0], chunk_pelvis[-1, 1], chunk_pelvis[-1, 2], color='g', s=100)
    ax.scatter(chunk_pelvis[500, 0], chunk_pelvis[500, 1], chunk_pelvis[500, 2], color='y', s=100)
    
    ax.scatter(chunk_femur[:, 0], chunk_femur[:, 1], chunk_femur[:, 2], color='r')
    ax.scatter(chunk_femur[0, 0], chunk_femur[0, 1], chunk_femur[0, 2], color='b', s=100)
    ax.scatter(chunk_femur[-1, 0], chunk_femur[-1, 1], chunk_femur[-1, 2], color='g', s=100)
    ax.scatter(chunk_femur[500, 0], chunk_femur[500, 1], chunk_femur[500, 2], color='y', s=100)
    plt.show()
    
    # make first element red
    
    
    
    
import pdb; pdb.set_trace()
exit()


flattened_pelvis = pelvis.vertices.reshape(-1, 3)
flattened_femur = femur.vertices.reshape(-1, 3)

# Calculate the distances in chunks to avoid memory issues
chunk_size = 1000
distances = np.zeros(len(flattened_pelvis))

for i in range(0, len(flattened_pelvis), chunk_size):
    print_loading_bar(i, len(flattened_pelvis))
    chunk_pelvis = flattened_pelvis[i:i+chunk_size]
    min_distances = np.full(len(chunk_pelvis), np.inf)
    for j in range(0, len(flattened_femur), chunk_size):
        chunk_femur = flattened_femur[j:j+chunk_size]
        dist_matrix = np.linalg.norm(chunk_pelvis[:, None] - chunk_femur, axis=2)
        min_distances = np.minimum(min_distances, dist_matrix.min(axis=1))
    distances[i:i+chunk_size] = min_distances

# Plot the pelvis with color based on the distance to the femur
pelvis.Trimesh.visual.vertex_colors = trimesh.visual.interpolate(distances, color_map='viridis')
pelvis.show_3d_mesh()
    

