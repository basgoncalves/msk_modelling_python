import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  
import os
import pandas as pd
class Plane:
  def __init__(self, a, b, c, d):
    self.a = a
    self.b = b
    self.c = c
    self.d = d

  def __str__(self):
    return f"{self.a}x + {self.b}y + {self.c}z + {self.d} = 0"

  def __repr__(self):
    return f"Plane({self.a}, {self.b}, {self.c}, {self.d})"

  def __eq__(self, other):
    return self.a == other.a and self.b == other.b and self.c == other.c and self.d == other.d

  def normal_vector(self):
    return np.array([self.a, self.b, self.c])

  def point_on_plane(self):
    return np.array([0.0, 0.0, -self.d / self.c])

  def perpendicular_plane(self, point):
    normal = self.normal_vector()
    d = -np.dot(normal, point)
    return Plane(normal[0], normal[1], normal[2], d)

  def is_perpendicular(self, other):
    return np.dot(self.normal_vector(), other.normal_vector()) == 0

  def intersects_line(self, point, direction):
    denominator = np.dot(self.normal_vector(), direction)
    if abs(denominator) < 1e-6:
      return False

    numerator = -self.d - np.dot(self.normal_vector(), point)
    distance = numerator / denominator

    return distance >= 0
  
  def plot_plane(self,x_lim=[-0.1,0.1], y_lim=[-0.1,0.1],tolerance=1e-6,color='lightgray',alpha=0.7):

    a = self.a
    b = self.b
    c = self.c
    d = self.d

    plot_plane(a, b, c, d,x_lim=[-0.1,0.1], y_lim=[-0.1,0.1],tolerance=1e-18,color='lightgray',alpha=0.7)


def load_stl_vertices(filename):
  """
  Loads the vertices from a text-based STL file.

  Args:
      filename: The path to the STL file.

  Returns:
      A list of NumPy arrays, where each array represents a vertex (x, y, z).
  """

  vertices = []
  normal_vectors = []
  with open(filename, 'r') as f:
    lines = f.readlines()

  for line in lines:
    if line.startswith("      vertex"):
      # Extract coordinates (assuming scientific notation)
      coordinates = [float(x) for x in line.split()[1:]]
      vertices.append(np.array(coordinates))
    
    if line.startswith("  facet normal"):
      coordinates = [float(x) for x in line.split()[1:]]
      normal_vectors.append(np.array(coordinates))

  # Split vertices into groups of 3 (triangles)
  vertices = [vertices[i:i + 3] for i in range(0, len(vertices), 3)]

  # calculate the centers of each triangle
  centres = []
  for i,d in enumerate(vertices):
      mean_point = np.mean(np.array(d), axis=0)
      centres.append(mean_point)
  centres = np.array(centres)


  return vertices, centres, normal_vectors

def plot_3D_points(points,col='red'):
  """
  Plots a set of 3D points.

  Args:
      points: A list of NumPy arrays representing the 3D points (x, y, z).
  """
  
  create_figure()
  # Plot each point
  for point in points:
    ax.scatter(point[0], point[1], point[2], color=col, marker='o', s=5)

  # Set labels and title
  ax.set_xlabel("X")
  ax.set_ylabel("Y")
  ax.set_zlabel("Z")
  ax.set_title("3D Points")

def plot_plane(a, b, c, d,x_lim=[-0.1,0.1], y_lim=[-0.1,0.1],tolerance=1e-18,color='lightgray',alpha=0.7):
  """
  Plots a plane defined by the equation ax + by + cz + d = 0.

  Args:
      a, b, c, d: Coefficients of the plane equation (ax + by + cz + d = 0).
  """
  if type(x_lim)!=list or type(y_lim)!=list:
    raise Warning("x_lim and y_lim must be a list with two values.")  
  elif len(x_lim) != 2 or len(y_lim) != 2:
    raise Warning("x_lim and y_lim must contain two values each.")
  
  if x_lim[0] == 0 and x_lim[1] == 0:
    print("x_lim values cannot be both zero. Setting them to 1%% of max (a,b,c,d)")
    max_val = max(abs(a),abs(b),abs(c),abs(d))
    x_lim = [-0.01*max_val,0.01*max_val]

  if y_lim[0] == 0 and y_lim[1] == 0:
    print("y_lim values cannot be both zero. Setting them to 1%% of max (a,b,c,d)")
    max_val = max(abs(a),abs(b),abs(c),abs(d))
    y_lim = [-0.01*max_val,0.01*max_val]

  # initiate the plot if needed
  ax = create_figure()
  x = np.linspace(-1,1,10)
  y = np.linspace(-1,1,10)

  # Create a meshgrid
  X,Y = np.meshgrid(x,y)

  # Mask for points where c is not close to zero
  mask = np.abs(c) > tolerance  
  Z = np.zeros_like(X)
  # Calculate the corresponding z values
  Z[mask] = (d - a * X[mask] - b * Y[mask]) / c


  # fig = plt.figure(figsize=(plt.rcParams['figure.figsize'][0] * 1.5, plt.rcParams['figure.figsize'][1] * 1.5))
  # ax = fig.add_subplot(111, projection='3d')

  surf = ax.plot_surface(X, Y, Z)

  # Set labels and title
  ax.set_xlabel("X")
  ax.set_ylabel("Y")
  ax.set_zlabel("Z")
  ax.set_title("Plane")

  return ax

  """
  Finds the equation of a plane perpendicular to another plane given its equation.

  Args:
      plane1_equation: A string representing the equation of the first plane (ax + by + cz + d = 0).

  Returns:
      A list containing:
          - A NumPy array representing the normal vector of the perpendicular plane.
          - A float representing the constant d in the plane equation.
  """

  # Extract coefficients from the plane equation
  a, b, c, d = plane1_equation

  # Convert coefficients to a NumPy array (normal vector)
  plane1_normal = np.array([a, b, c])

  # Choose a random point on plane1 (origin is always a valid choice)
  point_on_plane1 = np.array([0.0, 0.0, 0.0])

  # Find the equation of a perpendicular plane using the point and normal vector
  normal_perpendicular, d_perpendicular = get_perpendicular_plane(plane1_normal, point_on_plane1)

  return normal_perpendicular, d_perpendicular

def plot_triangle(pointArray,facecolor='#800000',alpha=0.05,pointsize=0.5):
    """
    Plots a triangle in 3D space. The triangle is defined by three points.
    pointArray: A 2D NumPy array with shape (3, 3) representing the triangle vertices.
    """
    if not isinstance(pointArray, np.ndarray) or pointArray.shape != (3, 3):
      raise ValueError("Input must be a 2D NumPy array with shape (3, 3)")

    x = pointArray[:, 0]
    y = pointArray[:, 1]
    z = pointArray[:, 2]

    # plot the points
    custom=plt.subplot(111,projection='3d')
    custom.scatter(x,y,z, s=pointsize, color='black')

    # 1. create vertices from points
    verts = [list(zip(x, y, z))]
    # 2. create 3d polygons and specify parameters
    srf = Poly3DCollection(verts, alpha=alpha, facecolor=facecolor)
    # 3. add polygon to the figure (current axes)
    ax = plt.gca().add_collection3d(srf)

    custom.set_xlabel('X')
    custom.set_ylabel('Y')
    custom.set_zlabel('Z')

    return ax

def does_vector_intersect_plane(point, direction, a, b, c, d, normal, x_lim, y_lim):
    """
    Checks if a vector intersects a plane defined by its equation and a normal vector.

    Args:
    point: A NumPy array representing the starting point of the vector (x, y, z).
    direction: A NumPy array representing the direction vector (x, y, z).
    a, b, c, d: Coefficients of the plane equation (ax + by + cz + d = 0).
    normal: A NumPy array representing the normal vector of the plane.

    Returns:
    True if the vector intersects the plane, False otherwise.
    """

    # Calculate the denominator (dot product of direction and normal)
    denominator = np.dot(direction, normal)

    # Check for parallel lines (denominator close to zero)
    if abs(denominator) < 1e-6:
        return False

    # Calculate the distance from the plane to the starting point
    d_numerator = np.dot(point - np.array([a, b, c]), normal) + d
    d = d_numerator / denominator

    # Check if the distance is positive (ray originates in front of the plane)
    if d <= 0:
        print("The vector does not intersect plane 2.")
        return False

    # Calculate intersection point
    intersection_point = point + d * direction

    intersect_lims = (x_lim[0] <= intersection_point[0] <= x_lim[1] and
            y_lim[0] <= intersection_point[1] <= y_lim[1])

    if intersect_lims:
        print("The vector intersects plane 2.")
    else:
        print("The vector does not intersect plane 2.")



    # Check if intersection point is within limits
    return 

def generate_points_on_plane(equation_coeffs):
  """
  Generates three random points on a plane defined by its equation coefficients.

  Args:
      equation_coeffs: A list containing the coefficients (a, b, c, d) of the plane equation.

  Returns:
      A list of three NumPy arrays representing the generated points.
  """

  a, b, c, d = equation_coeffs
  points = []
  for _ in range(3):
    # Generate a random point
    point = np.random.rand(3)

    # Adjust the point to lie on the plane
    point = point - (a * point[0] + b * point[1] + c * point[2] + d) / (a**2 + b**2 + c**2)

    points.append(point)

  return points

def create_figure():
  """
  Creates a new 3D figure if none exists, otherwise reuses the existing one.

  Returns:
      A matplotlib.pyplot.Axes3D object representing the figure's main axes.
  """

  try:
    # Attempt to get the current figure
    fig = plt.gcf()
    ax = fig.gca()  # Get the current axes (might be 2D or 3D)

    # Check if the current axes is a 3D axes object
    if not isinstance(ax, Axes3D):
      # If not 3D, create a new figure and 3D axes
      plt.close(fig)  # Close the existing figure (might be 2D)
      fig = plt.figure(figsize=(plt.rcParams['figure.figsize'][0] * 1.5, plt.rcParams['figure.figsize'][1] * 1.5))
      ax = fig.add_subplot(111, projection='3d')
      print('created new figure')
    else:
      # Reuse existing figure and axes (assuming it's 3D)
      print('reusing existing figure')

  except (AttributeError, ValueError):
    # If no figure exists, create a new one
    fig = plt.figure(figsize=(plt.rcParams['figure.figsize'][0] * 1.5, plt.rcParams['figure.figsize'][1] * 1.5))
    ax = fig.add_subplot(111, projection='3d')
    print('created new figure')

  return ax

def calculate_triangle_area_3d(point1, point2, point3):
    vector1 = np.array(point2) - np.array(point1)
    vector2 = np.array(point3) - np.array(point1)
    cross_product = np.cross(vector1, vector2)
    area = 0.5 * np.linalg.norm(cross_product)
    return area

def calculate_distances(point, matrix):
  """
  Calculates distances between a point and all points in a 3D point matrix.

  Args:
      point: A NumPy array representing a single 3D point (x, y, z).
      matrix: A NumPy array with dimensions (60000, 3) representing 60000 3D points.

  Returns:
      A NumPy array containing distances between the point and each point in the matrix.
  """

  # Reshape point to a column vector for broadcasting
  point_reshaped = point.reshape(-1)

  # Calculate squared differences efficiently using broadcasting
  squared_diffs = np.sum((matrix - point_reshaped) ** 2, axis=1)

  # Calculate distances using the square root (optional for Euclidean distance)
  distances = np.sqrt(squared_diffs)

  return distances

def calculate_centre_of_triangle(point1, point2, point3):
  vertices = np.array([[point1, point2, point3]])
  centres = []
  for i,d in enumerate(vertices):
      mean_point = np.mean(np.array(d), axis=0)
      centres.append(mean_point)
  return centres[0]

def compare_normalized_coverages(folder_path):
  normalized_coverage_values = []
  threshold = []
  
  for root, dirs, files in os.walk(folder_path):
    for dir_name in dirs:
      if "_l_threshold" in dir_name:
        coverage_file_path = os.path.join(root, dir_name, "femoral_head_l.txt")
        if os.path.isfile(coverage_file_path):
          try:
            with open(coverage_file_path, 'r') as file:
              for line in file:
                if "Normalized Area Covered:" in line:
                  value = line.split(": ")[1].strip().replace("%", "")
                  normalized_coverage_values.append(value)
                  threshold.append(dir_name.split("_")[4])
          except:
            print(f"Error reading file: {coverage_file_path}")
            continue
  
  coverage = pd.DataFrame({
    'Normalized Coverage Values': normalized_coverage_values,
    'Threshold': threshold})

  coverage['Threshold'] = pd.to_numeric(coverage['Threshold'])
  coverage['Normalized Coverage Values'] = pd.to_numeric(coverage['Normalized Coverage Values'])
  coverage = coverage.sort_values('Threshold')

  return coverage

def distance_points_3d(p1, p2):
  """
  Calculates the absolute distance between two 3D points.

  Args:
      p1: A 3D NumPy array representing the first point (x1, y1, z1).
      p2: A 3D NumPy array representing the second point (x2, y2, z2).

  Returns:
      The absolute distance between the two points.
  """

  difference = p2 - p1
  squared_magnitude = np.sum(difference**2)
  distance = np.sqrt(squared_magnitude) # Take the square root to get the absolute distance

  return distance



if __name__ == "__main__": 

  # Generate coefficients and points for a random plane
  # coefficients, points = generate_random_plane_points()
  coefficients = [1.0, 1.0, 3.0, 1.0]
  plane_equation = f"{coefficients[0]}x + {coefficients[1]}y + {coefficients[2]}z + {coefficients[3]} = 0"
  print("Plane equation:", plane_equation)
  

  ax = create_figure()
  plot_plane(coefficients[0], coefficients[1], coefficients[2], coefficients[3],[-1,1],[-1,1])

  exit()
