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
        self.log_file = os.path.join(self.current, 'log.txt')
        self.files = os.listdir(self.current)
        self.stl_files = [file for file in self.files if file.endswith('.stl')]
        self.subjects = os.listdir(self.example_folder)
        self.subjects = [subject for subject in self.subjects if os.path.isdir(os.path.join(self.example_folder, subject))]
    
    def remove_all_results(self):
        for subject in self.subjects:
            for leg in ['r', 'l']:
                results_path = os.path.join(self.example_folder, subject, f"hip_{leg}", 'results.csv')
                if os.path.exists(results_path):
                    os.remove(results_path)
                    print(f"Removed: {results_path}")
     
    def get_summary_results(self):
        summary_csv_path = os.path.join(self.example_folder, 'summary.csv')
        if os.path.exists(summary_csv_path) == False:
            return None
        return pd.read_csv(summary_csv_path)
        
    def plot_summary_results(self):

        columns = ['subject','threshold', 'covered_area', 'leg', 'time', 'algorithm']
        # summarise all results in a single csv file
        all_results = pd.DataFrame(columns=columns)
        
        # Loop through all the subjects (i.e. folders in the example folder)
        for subject in self.subjects:            
            for leg in ['r', 'l']: # loop through both legs
                try:
                    results_path = os.path.join(self.example_folder, subject, f"hip_{leg}", 'results.csv')
                    results = pd.read_csv(results_path)
                    results['leg'] = leg
                    all_results = pd.concat([all_results, results])
                except Exception as e:
                    print(f"Error: Could not read {results_path}")
                    print(e)
                     
        # save the summary results to a csv file 
        try:    
            summary_csv_path = os.path.join(self.example_folder, 'summary.csv')            
            all_results.to_csv(summary_csv_path, index=False)
            print(f"Summary results saved at: {summary_csv_path}")
        except Exception as e:
            print(f"Error: Could not save summary results")
            print(e)

        # plot the summary results
        try:
            X = all_results['subject'].unique()
            # one subplot for each algorithm
            fig = plt.figure()
            n_subplots = len(all_results['algorithm'].unique())
            count_subplots = 0
            for algorithm in all_results['algorithm'].unique():
                count_subplots += 1
                algorithm_results = all_results[all_results['algorithm'] == algorithm]
                ax = fig.add_subplot(1,n_subplots,count_subplots)
                Y = algorithm_results['covered_area'].groupby([algorithm_results['subject'], algorithm_results['threshold']]).mean()
                Y.unstack().plot(kind='bar', ax=ax, title=algorithm)
                
                plt.ylabel('Covered Area (mm^2)')
                plt.xlabel('Subject')
                plt.title(algorithm)
                plt.xticks(rotation=45)
                plt.tight_layout()

            save_file_path = os.path.join(self.example_folder, 'summary.png')
            plt.savefig(save_file_path)
            plt.show()     
        except Exception as e:
            print(f"Error: Could not plot summary results")
            print(e)

        # print to log file
        with open(self.log_file, "w") as f:
            f.write(f"Finished plot_summary_results: {time.ctime()}")

    def write_to_log(self, message):
        with open(self.log_file, "w") as f:
            f.write(message)

class Hip():
    def __init__(self, subjectID, pelvis_path, femur_path, leg, threshold_list=[5, 10, 15], replace=False):
        
        try:
            self.start_time = time.time()
            self.subjectID = subjectID
            self.pelvis_path = pelvis_path
            self.femur_path = femur_path
            self.hip_path = os.path.join(os.path.dirname(femur_path), 'hip_' + leg)
            self.results_path = os.path.join(self.hip_path, 'results.csv')
            self.replace = replace
            
            if os.path.exists(self.hip_path) == False:
                os.mkdir(self.hip_path)
            
            # load meshes
            self.pelvis_mesh = trimesh.load(pelvis_path)
            self.femur_mesh = trimesh.load(femur_path)
            
            self.leg = leg
            self.threshold_list = threshold_list
            
            self.pelvis_to_femur_distance = self.pelvis_mesh.nearest.on_surface(self.femur_mesh.vertices)
            
            self.algorithm = None
            self.covered_area = None
            self.time_taken = None
            self.threshold = None
            
            # check time to load
            self.sec_to_load = time.time() - self.start_time
            
        except Exception as e:
            print(f"Error: Could not load meshes")
            print(e)
    
    def save_csv(self):
        
        columns = ['subject','threshold', 'covered_area', 'leg', 'time', 'algorithm']
        if os.path.exists(self.results_path):
            results = pd.read_csv(self.results_path)            
        else:
            results = pd.DataFrame(columns=columns)

        current_results = {'subject': self.subjectID,
                            'threshold': self.threshold, 
                            'covered_area': self.covered_area, 
                            'leg': self.leg, 
                            'time': self.time_taken, 
                            'algorithm': self.algorithm}

        results = pd.concat([results, pd.DataFrame([current_results])], ignore_index=True)
        results.to_csv(self.results_path, index=False)
        print(f"Results saved at: {self.results_path}")
        time.sleep(1)
    
    def save_fig(self, fig, filename):
        
        save_path = os.path.join(self.hip_path, filename)
        if os.path.exists(save_path) and self.replace == False:
            answer = input(f"File {save_path} already exists. Press Enter to overwrite (N to cancel)").lower()
            if answer == 'n':
                return
        fig.savefig(save_path)
        print(f"Figure saved at: {save_path}")
    
    def fit_sphere_algoritm(self, threshold):
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
        self.algorithm = 'fit_sphere_algoritm'

        # Create a sphere mesh for the femur
        sphere_points_femur = generate_sphere_points(self.femur_mesh, num_points=len(self.femur_mesh.vertices)*3)
        shere_mesh_femur = trimesh.convex.convex_hull(sphere_points_femur)

        # Determine the convertion ration between the units of the femur mesh and the sphere mesh
        ratio = np.mean(np.linalg.norm(self.femur_mesh.vertices, axis=1)) / np.mean(np.linalg.norm(shere_mesh_femur.vertices, axis=1))   
        
        # Calculate the distance between the meshes
        distance = self.pelvis_mesh.nearest.on_surface(shere_mesh_femur.vertices)

        # Get logical array of the distances
        is_covered_femur = distance[1] < threshold

        # Calculate the area of the covered faces
        covered_area = calculate_area(shere_mesh_femur.vertices[is_covered_femur])
        covered_area = covered_area * ratio**2
        print(f"Threshold: {threshold} - Covered Area: {covered_area:.2f}")

        # plot the meshes with the distance color map
        try:
            fig, ax = self.plot_coverage(self.pelvis_mesh, shere_mesh_femur, threshold, is_covered_femur, covered_area)
            self.save_fig(fig, f"sphere_{threshold}.png")
        except Exception as e:
            print(f"Error: Could not save figure")
            print(e)

        # print to .csv
        self.covered_area = covered_area
        self.threshold = threshold
        self.time_taken = time.time() - start_time
        self.save_csv()      
        
        return covered_area

    def nearest_algorithm(self, threshold):
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
        self.algorithm = 'nearest'

        # Calculate the distance between the meshes (reutrns number of the nearest face and the distance on the femur mesh)
        distance = self.pelvis_mesh.nearest.on_surface(self.femur_mesh.vertices)

        # Get logical array of the distances
        is_covered_femur = distance[1] < threshold

        # Calculate the area of the covered faces
        covered_area = calculate_area(self.femur_mesh.vertices[is_covered_femur])
        print(f"Threshold: {threshold} - Covered Area: {covered_area:.2f}")

        # plot the meshes with the distance color map
        try:
            fig, ax = self.plot_coverage(self.pelvis_mesh, self.femur_mesh, threshold, is_covered_femur, covered_area)
            self.save_fig(fig, f"nearest_{threshold}.png")
        except Exception as e:
            print(f"Error: Could not save figure")
            print(e)

        # print to .csv
        self.covered_area = covered_area
        self.threshold = threshold
        self.time_taken = time.time() - start_time
        self.save_csv()
        
        return covered_area
                  
    def compare_area_covered_different_thersholds(self, algorithm='nearest'):
        """
        Compares the area covered by the pelvis mesh for different thresholds.
        
        """
        self.algorithm = algorithm
        print(f"Comparing meshes: ")
        print(f"Pelvis: {self.pelvis_path}")
        print(f"Femur: {self.femur_path}")
        results = pd.read_csv(self.results_path)
        
        
        # loop through the thresholds to calculate the covered area
        for threshold in self.threshold_list:
            
            # check if the results already exist and if we should replace them
            if any([int(self.subjectID) in results['subject'].values, self.threshold in results['threshold'].values,
            self.leg in results['leg'].values, self.algorithm in results['algorithm'].values]):
        
                if self.replace == False:
                    
                    continue
                
            if algorithm == 'nearest' or ():
                self.nearest_algorithm(threshold)

            elif algorithm == 'fit_sphere_algoritm':
                self.fit_sphere_algoritm(threshold)

    def plot_coverage(self, pelvis_mesh, femur_mesh, threshold, is_covered_femur, covered_area):
        # plot the meshes with the distance color map
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        plt.subplots_adjust(top=1.0, bottom=0.0, left=0.0, right=1.0, hspace=0.0, wspace=0.0)
        
        # plot the meshes in grey
        ax.scatter(femur_mesh.vertices[:,0], femur_mesh.vertices[:,1], femur_mesh.vertices[:,2],c='grey', s=1, alpha=0.1) 
        ax.scatter(pelvis_mesh.vertices[:,0], pelvis_mesh.vertices[:,1], pelvis_mesh.vertices[:,2],c='grey', s=1, alpha=0.1)

        # plot the points that are below the threshold in red
        ax.scatter(femur_mesh.vertices[is_covered_femur,0], femur_mesh.vertices[is_covered_femur,1], femur_mesh.vertices[is_covered_femur,2],c='red') # plot the points that are below the threshold in red

        ax.view_init(elev=16, azim=-35, roll=0) # set the view

        plt.title(f"Threshold: {threshold}")

        # add text with covered area to the top right corner outside the plot
        ax.text2D(0.95, 0.95, f'Covered Area: {covered_area:.1f} mm^2', transform=ax.transAxes, ha='right', va='top')

        return fig, ax

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

if __name__ == "__main__":

    ####################################################################################################
    #                                      Edit settings here                                          #
    ####################################################################################################
    skip = False
    legs = ["r", "l"]
    thresholds = [15]
    skip_subjects = []
    algorithm = 'nearest' # 'nearest' or 'fit_sphere_algoritm'
    restart_results = False


    ####################################################################################################
    project = Project()
    project.subjects = [subject for subject in project.subjects if subject not in skip_subjects]
    print(project.subjects)
    
    if restart_results:
        project.remove_all_results()

    if skip == False:
        for subject in project.subjects:
            if subject in skip_subjects:
                continue

            for leg in legs:
                
                # check if the files exist for the subject (pelvis and femur)
                pelvis_path = os.path.join(project.example_folder, subject ,f"acetabulum_{leg}.stl")
                femur_path = os.path.join(project.example_folder, subject, f"femoral_head_{leg}.stl")
                
                hip = Hip(subject, pelvis_path, femur_path, leg, threshold_list=thresholds)
                hip.compare_area_covered_different_thersholds(algorithm)
                
                project.write_to_log(f"Finished processing {subject} {leg} at: {time.ctime()}")
                
                

    project.plot_summary_results()