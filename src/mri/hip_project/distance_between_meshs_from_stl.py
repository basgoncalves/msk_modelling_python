import os
import trimesh
import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
from scipy.optimize import least_squares
import matplotlib.pyplot as plt
import time

# may need to pip install "pyglet<2", "rtree", "open3d" to run this example

class Project():
    def __init__(self):
        self.current = os.path.dirname(os.path.abspath(__file__))
        self.example_folder = os.path.join(self.current, 'example_stls')
        self.files = os.listdir(self.current)
        self.stl_files = [file for file in self.files if file.endswith('.stl')]
        self.subjects = os.listdir(self.example_folder)
        self.subjects = [subject for subject in self.subjects if os.path.isdir(os.path.join(self.example_folder, subject))]

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

def error_function(params, points, centroid):
    center = params[:3]
    radius = params[3]
    distances = np.linalg.norm(points - center, axis=1) - radius
    return distances

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

def calculate_centroid(mesh):
    
    points = mesh.vertices
    centroid = np.mean(points, axis=0)

    distances = np.linalg.norm(points - centroid, axis=1)
    initial_radius = np.mean(distances)

    return points, centroid, initial_radius

def generate_sphere_points(mesh, num_points=1000):
    
    points, centroid, initial_radius = calculate_centroid(mesh)
    
    # Initial guess for center and radius
    initial_guess = np.append(centroid, initial_radius)

    # Optimization
    result = least_squares(error_function, initial_guess, args=(points, centroid))
    optimal_center = result.x[:3]
    optimal_radius = result.x[3]
    
    phi = np.random.uniform(0, np.pi, num_points)
    theta = np.random.uniform(0, 2 * np.pi, num_points)
    x = optimal_center[0] + optimal_radius * np.sin(phi) * np.cos(theta)
    y = optimal_center[1] + optimal_radius * np.sin(phi) * np.sin(theta)
    z = optimal_center[2] + optimal_radius * np.cos(phi)

    return np.column_stack((x, y, z))

def calculate_covered_area(points, center, radius):
    """
    Calculates the approximate area of the fitted sphere covered by the points.

    This function assumes the points are uniformly distributed on the sphere's
    surface. It calculates the ratio of points within the sphere's radius
    compared to the total number of points and multiplies it by the sphere's
    surface area (4*pi*radius^2).

    Args:
        points: A numpy array of shape (N, 3) representing the mesh points.
        center: A numpy array of shape (3,) representing the sphere's center.
        radius: The radius of the fitted sphere.

    Returns:
        The approximate area of the sphere covered by the points.
    """

    distances = np.linalg.norm(points - center, axis=1)
    num_covered_points = np.count_nonzero(distances <= radius)
    total_points = points.shape[0]

    # Assuming uniform distribution of points on the sphere
    covered_ratio = num_covered_points / total_points
    sphere_area = 4 * np.pi * radius**2
    covered_area = np.round(covered_ratio * sphere_area,1)

    return covered_area

def fit_sphere_and_plot(mesh_path):
    points, centroid, initial_radius = calculate_centroid(mesh_path)
        
    # Initial guess for center and radius
    initial_guess = np.append(centroid, initial_radius)

    # Optimization
    result = least_squares(error_function, initial_guess, args=(points, centroid))
    optimal_center = result.x[:3]
    optimal_radius = result.x[3]

    # Generate sphere points
    sphere_points = generate_sphere_points(optimal_center, optimal_radius)
    
    import pdb; pdb.set_trace()
    # Plotting
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ## Scatter plot
    # ax.scatter(points[:, 0], points[:, 1], points[:, 2], s=1, label='Mesh Points')
    # ax.scatter(sphere_points[:, 0], sphere_points[:, 1], sphere_points[:, 2], s=1, color='r', label='Fitted Sphere')

    # Convert points to surface
    ax.plot_trisurf(points[:, 0], points[:, 1], points[:, 2], color='b', alpha=0.3)
    ax.plot_trisurf(sphere_points[:, 0], sphere_points[:, 1], sphere_points[:, 2], color='r', alpha=0.3)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Calculate covered area
    covered_area = calculate_covered_area(points, optimal_center, optimal_radius)    
    
    # add text for covered area
    ax.text2D(0.95, 0.95, f'Covered Area: {covered_area:.1f} mm^2', transform=ax.transAxes, ha='right', va='top')

    filename_without_extension = os.path.splitext(os.path.basename(mesh_path))[0]
    plt.title(f'Fitted Sphere for {filename_without_extension}')
    
    # save figure
    save_file_path = os.path.join(os.path.dirname(mesh_path), filename_without_extension + '_fitted_sphere.png')
    plt.savefig(save_file_path)
    
    print(f"Approximate covered area of the sphere: {covered_area:.1f} mm^2")
    print(f"Figure saved at: {save_file_path}")

    return covered_area, sphere_points

def plot_coverage(femur_mesh, pelvis_mesh, threshold, is_covered_femur, covered_area):
    # plot the meshes with the distance color map
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    plt.subplots_adjust(top=1.0, bottom=0.0, left=0.0, right=1.0, hspace=0.0, wspace=0.0)
    ax.scatter(femur_mesh.vertices[:,0], femur_mesh.vertices[:,1], femur_mesh.vertices[:,2],c='grey', s=1, alpha=0.1) # plot all the points in grey    
    ax.scatter(pelvis_mesh.vertices[:,0], pelvis_mesh.vertices[:,1], pelvis_mesh.vertices[:,2],c='grey', s=1, alpha=0.1) 
    
    ax.scatter(femur_mesh.vertices[is_covered_femur,0], femur_mesh.vertices[is_covered_femur,1], femur_mesh.vertices[is_covered_femur,2],c='red') # plot the points that are below the threshold in red
    
    ax.view_init(elev=16, azim=-35, roll=0) # set the view 

    plt.title(f"Threshold: {threshold}")
    
    # add text with covered area to the top right corner outside the plot
    ax.text2D(0.95, 0.95, f'Covered Area: {covered_area:.1f} mm^2', transform=ax.transAxes, ha='right', va='top')
    
    return fig, ax

def fit_sphere_algoritm(femur_mesh, pelvis_mesh, threshold, figures_path):
    """
    
    Similar to the nearest algorithm, the sphere intersection algorithm calculates the distance between two meshes and determines which points are covered by the other mesh.

    Args:
        mesh1: A trimesh object representing the first mesh.
        mesh2: A trimesh object representing the second mesh.
        threshold: The maximum distance threshold for a point to be considered covered.
    
    Returns:
        The covered area of the first mesh.
    """
    start_time = time.time()
    
    # Create a sphere mesh for the femur
    sphere_points_femur = generate_sphere_points(femur_mesh, num_points=1000)
    shere_mesh_femur = trimesh.convex.convex_hull(sphere_points_femur)
    
    # Calculate the distance between the meshes
    distance = shere_mesh_femur.nearest.on_surface(pelvis_mesh.vertices)

    # Get logical array of the distances
    is_covered_femur = distance[1] < threshold


    # Calculate the area of the covered faces
    covered_area = calculate_area(femur_mesh.vertices[is_covered_femur])
    print(f"Threshold: {threshold} - Covered Area: {covered_area:.2f}")
    
    # plot the meshes with the distance color map
    fig, ax = plot_coverage(femur_mesh, pelvis_mesh, threshold, is_covered_femur, covered_area)
    
    # save the figure
    save_path = os.path.join(figures_path, f"distance_{threshold}.png")
    plt.savefig(save_path)
    print(f"Figure saved at: {save_path}")
    
    # print to .csv 
    csv_path = os.path.join(figures_path, f"fit_sphere_algoritm.csv")
    if os.path.exists(csv_path):
        results = pd.read_csv(csv_path)
    else:
        results = pd.DataFrame(columns=['threshold', 'covered_area', 'time'])
    
    time_taken = time.time() - start_time
    results = pd.concat([results, pd.DataFrame([[threshold, covered_area, time_taken]], columns=['threshold', 'covered_area', 'time'])])
    results.to_csv(csv_path, index=False)
    print(f"Results saved at: {csv_path}")
    time.sleep(1)

    
    # Perform the intersection
    # intersection = trimesh.intersections.mesh_multiplane(femur_mesh, pelvis_mesh)
    # intersection_points = intersection[0]

    return covered_area

def nearest_algorithm(femur_mesh, pelvis_mesh, threshold, figures_path):
    """
    Calculates the distance between two meshes using the nearest algorithm.

    Args:
        mesh1: A trimesh object representing the first mesh.
        mesh2: A trimesh object representing the second mesh.
        threshold: The maximum distance threshold for a point to be considered covered.

    Returns:
        The covered area of the first mesh.
    """
    
    start_time = time.time()
    
    # Calculate the distance between the meshes
    distance = femur_mesh.nearest.on_surface(pelvis_mesh.vertices)

    # Get logical array of the distances
    is_covered_femur = distance[1] < threshold

    # Calculate the area of the covered faces
    covered_area = calculate_area(femur_mesh.vertices[is_covered_femur])
    print(f"Threshold: {threshold} - Covered Area: {covered_area:.2f}")
    
    # plot the meshes with the distance color map
    fig, ax = plot_coverage(femur_mesh, pelvis_mesh, threshold, is_covered_femur, covered_area)
    
    # save the figure
    save_path = os.path.join(figures_path, f"distance_{threshold}.png")
    plt.savefig(save_path)
    print(f"Figure saved at: {save_path}")
    
    # print to .csv 
    csv_path = os.path.join(figures_path, f"nearest_algoritm.csv")
    if os.path.exists(csv_path):
        results = pd.read_csv(csv_path)
    else:
        results = pd.DataFrame(columns=['threshold', 'covered_area', 'time'])
    
    time_taken = time.time() - start_time
    results = pd.concat([results, pd.DataFrame([[threshold, covered_area, time_taken]], columns=['threshold', 'covered_area', 'time'])])
    results.to_csv(csv_path, index=False)
    print(f"Results saved at: {csv_path}")
    time.sleep(1)

    return covered_area

def compare_area_covered_different_thersholds(pelvis_path, femur_path, threshold_list=[5, 10, 15], algorithm='nearest'):
    
    # Paths to save the figures
    figures_path = os.path.join(os.path.dirname(femur_path), 'figures')
    csv_path = os.path.join(figures_path, 'distances.csv')

    if os.path.exists(figures_path) == False:
        os.mkdir(figures_path)
        
    # delete the csv file if it already exists
    if os.path.exists(csv_path):
        os.remove(csv_path)

    # Load the meshes
    print("Loading meshes...")
    pelvis = trimesh.load(pelvis_path)
    femur = trimesh.load(femur_path)
    
    # loop through the thresholds to calculate the covered area
    for threshold in threshold_list:
        
        start_time = time.time()
        
        if algorithm == 'nearest':
            nearest_algorithm(pelvis, femur, threshold, figures_path)
            
        elif algorithm == 'fit_sphere_algoritm':
            fit_sphere_algoritm(pelvis, femur, threshold, figures_path)
            


        
        
        
def plot_summary_results():
    
    paths = Project()
    
    # summarise all results in a single csv file
    sumaary_csv_path = os.path.join(paths.example_folder, 'summary.csv')
    all_results = pd.DataFrame()
    for subject in os.listdir(paths.example_folder):
        csv_path = os.path.join(paths.example_folder, subject, f"figures", f"distances.csv")
        try:
            results = pd.read_csv(csv_path)
            results['subject'] = subject
            all_results = pd.concat([all_results, results])
        except Exception as e:
            print(f"Error: Could not read {csv_path}")
            print(e)
    all_results.to_csv(sumaary_csv_path, index=False)
    
    print(f"Summary results saved at: {sumaary_csv_path}")
    
    # plot the summary results
    
    X = all_results['subject'].unique()
    Y = all_results['covered_area'].groupby(all_results['subject']).mean()
    Y_per_threshold = all_results['covered_area'].groupby([all_results['subject'], all_results['threshold']]).mean()
    
    fig = plt.figure()
    Y_per_threshold.unstack().plot(kind='bar', ax=fig.add_subplot(111))
    
    plt.ylabel('Covered Area (mm^2)')
    plt.xlabel('Subject')
    plt.title('Covered Area by Subject')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    save_file_path = os.path.join(paths.example_folder, 'summary.png')
    plt.savefig(save_file_path)
    plt.show()


if __name__ == "__main__":
    
    ####################################################################################################
    #                                      Edit settings here                                          #
    ####################################################################################################
    skip = False
    legs = ["r", "l"] 
    thresholds = [10, 15]
    skip_subjects = ["009", "010"]
    algorithm = 'fit_sphere_algoritm' # 'nearest' or 'fit_sphere_algoritm'
    
    
    ####################################################################################################
    paths = Project()
    print(paths.subjects)
    
    if skip == False:
        for subject in paths.subjects:
            if subject in skip_subjects:
                continue
            
            for leg in legs:
                pelvis_path = os.path.join(paths.example_folder, subject ,f"acetabulum_{leg}.stl")
                femur_path = os.path.join(paths.example_folder, subject, f"femoral_head_{leg}.stl")
                
                compare_area_covered_different_thersholds(pelvis_path, femur_path, threshold_list=thresholds, algorithm=algorithm)
        

    plot_summary_results()