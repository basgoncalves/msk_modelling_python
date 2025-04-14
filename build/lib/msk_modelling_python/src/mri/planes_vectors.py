import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection 
from mpl_toolkits.mplot3d import Axes3D
import math
import pandas as pd
import os

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
      coordinates = [float(x) for x in line.split()[2:]]
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


#%% calculations
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

def calculate_normal_vector(vertex1, vertex2, vertex3):
  """
  Calculates the normal vector to the plane defined by three vertices.

  Args:
      vertex1: A numpy array representing the first vertex of the plane (3D).
      vertex2: A numpy array representing the second vertex of the plane (3D).
      vertex3: A numpy array representing the third vertex of the plane (3D).

  Returns:
      A numpy array representing the normal vector to the plane.
  """

  # Calculate two edge vectors of the triangle
  edge1 = vertex2 - vertex1
  edge2 = vertex3 - vertex2

  # Calculate the normal vector (cross product of edge vectors)
  normal_vector = np.cross(edge1, edge2)

  # Normalize the normal vector (optional)
  normal_vector /= np.linalg.norm(normal_vector)

  return normal_vector

def calculate_centre_of_triangle(point1, point2, point3):
  vertices = np.array([[point1, point2, point3]])
  centres = []
  for i,d in enumerate(vertices):
      mean_point = np.mean(np.array(d), axis=0)
      centres.append(mean_point)
  return centres[0]

def calculate_plane_coefficients(normal_vector, point_on_plane):
  """
  Calculates the coefficients A, B, and C in the plane equation (Ax + By + Cz + D = 0)
  given the normal vector and a point on the plane.

  Args:
      normal_vector: A numpy array representing the normal vector to the plane (3D).
      point_on_plane: A numpy array representing a point on the plane (3D).

  Returns:
      A tuple containing the coefficients A, B, and C.
  """

  A = normal_vector[0]
  B = normal_vector[1]
  C = normal_vector[2]

  # Solve for D using the plane equation
  D = - (A * point_on_plane[0] + B * point_on_plane[1] + C * point_on_plane[2])

  return A, B, C, D

def calculate_normal_vector2(A, B, C):
  """
  Calculates the normal vector to a plane defined by the equation Ax + By + Cz + D = 0.

  Args:
      A: A coefficient in the plane equation (float).
      B: A coefficient in the plane equation (float).
      C: A coefficient in the plane equation (float).
      D: A coefficient in the plane equation (float).

  Returns:
      A numpy array representing the normal vector to the plane (3D).
  """

  # Normal vector components are the negative coefficients of x, y, and z
  normal_vector = np.array([-A, -B, -C])

  # Normalize the normal vector (optional)
  normal_vector /= np.linalg.norm(normal_vector)

  return normal_vector

def intersects_plane_segment(vector, vertex1, vertex2, vertex3):
  """
  Checks if a normal vector intersects a plane segment defined by three vertices.

  Args:
      normal_vector: A numpy array representing the normal vector (3D).
      vertex1: A numpy array representing the first vertex of the segment (3D).
      vertex2: A numpy array representing the second vertex of the segment (3D).
      vertex3: A numpy array representing the third vertex of the segment (3D).

  Returns:
      True if the normal vector intersects the plane segment, False otherwise.
  """

  # Calculate the direction vector of the segment (vertex2 - vertex1)
  segment_direction = vertex2 - vertex1

 
  return True

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

def angle_between_two_faces(face1,face2):
  """
  face1 and face2 should be 3D numpy arrays representing the vertices of the faces.
  vertex1 = np.array([-98, -16, 26])
  vertex2 = np.array([-97, -18, 27])
  vertex3 = np.array([-100, -16, 27])
  face1 = np.array([vertex1, vertex2, vertex3])

  see https://onlinemschool.com/math/assistance/vector/angl/
  """
  # Calculate the normal vector to the plane defined by the face
  normal_vector1 = calculate_normal_vector(face1[0], face1[1], face1[2])
  normal_vector2 = calculate_normal_vector(face2[0], face2[1], face2[2])

  dot_product = np.clip(np.dot(normal_vector1,normal_vector2),-1,1)
  angle_between_faces = math.acos(dot_product) * 180 / np.pi # angle between vectors in degrees

  return angle_between_faces

def calculate_perpendicular_vector(v1, v2):
  """
  Generates a vector perpendicular to both v1 and v2.

  Args:
      v1: A 3D numpy array representing the first vector.
      v2: A 3D numpy array representing the second vector.

  Returns:
      A 3D numpy array representing a vector perpendicular to v1 and v2.
  """

  # Ensure both vectors are unit vectors
  v1 /= np.linalg.norm(v1)
  v2 /= np.linalg.norm(v2)

  # Calculate the cross product of v1 and v2
  v3 = np.cross(v1, v2)

  # Check if the cross product is zero (indicating parallel vectors)
  if np.allclose(v3, np.zeros(3)):
    # If parallel, choose an arbitrary vector not aligned with v1
    # This ensures we don't end up with a zero vector after cross product
    arbitrary_vector = np.ones(3) - v1
    v3 = np.cross(v1, arbitrary_vector)

  # Normalize the resulting vector
  v3 /= np.linalg.norm(v3)

  return v3


#%% Ploting

def update_figure():
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

def plot_vector(v1,origin,color='red',label='Vector 1'):
    # Calculate the end points for the vector
    v1_point = origin + v1

    ax = update_figure()
    ax.quiver(origin[0], origin[1], origin[2], v1[0], v1[1], v1[2], color=color, label=label)
    ax.scatter(v1_point[0], v1_point[1], v1_point[2], color='k')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

def plot_prependicular_vector(v1, v2,origin):
    """
    v1 and v2 should be 3D numpy arrays representing the vectors directions.
    origin should be a 3D numpy array representing the origin of the vectors.
    """
    # Generate third vector perpendicular to v1 and v2
    v3 = calculate_perpendicular_vector(v1, v2)

    # Calculate the end points for the vectors
    v1_point = origin + v1
    v2_point = origin + v2

    # Plot the vectors
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    _,x,y,z = plot_triangle(np.array([origin, v1_point, v2_point]), facecolor='gray', alpha=0.5)
    ax.scatter(x, y, z, color='black')
    ax.quiver(origin[0], origin[1], origin[2], v1[0], v1[1], v1[2], color='red', label='Vector 1')
    ax.quiver(origin[0], origin[1], origin[2], v2[0], v2[1], v2[2], color='blue', label='Vector 2')
    ax.quiver(origin[0], origin[1], origin[2], v3[0], v3[1], v3[2], color='green', label='Vector 3 (Perpendicular to V1 and V2)')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Perpendicular 3D Vectors')
    plt.legend()

    # add the points to the end of each vector
    ax.scatter(v1_point[0], v1_point[1], v1_point[2], color='red')
    ax.scatter(v2_point[0], v2_point[1], v2_point[2], color='blue')
    ax.scatter(v3[0], v3[1], v3[2], color='green')

    # Calculate dot product
    dot_product = np.dot(v1, v3)

    print("Dot product:", dot_product)
    if np.isclose(dot_product, 0.0):
        print("The vectors are perpendicular.")
    else:
        print("The vectors are not perpendicular.")

    plt.show()

def plot_3D_points(points,col='red'):
  """
  Plots a set of 3D points.

  Args:
      points: A list of NumPy arrays representing the 3D points (x, y, z).
  """
  
  ax = update_figure()
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
  ax = update_figure()
  x = np.linspace(-1,1,10)
  y = np.linspace(-1,1,10)

  # Create a meshgrid
  X,Y = np.meshgrid(x,y)

  # Mask for points where c is not close to zero
  mask = np.abs(c) > tolerance  
  Z = np.zeros_like(X)
  # Calculate the corresponding z values
  Z[mask] = (d - a * X[mask] - b * Y[mask]) / c

  ax = update_figure()
  surf = ax.plot_surface(X, Y, Z)

  # Set labels and title
  ax.set_xlabel("X")
  ax.set_ylabel("Y")
  ax.set_zlabel("Z")
  ax.set_title("Plane")

  return ax

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

def line_point(t):
    return plane_centre1 + t * normal_vector_femur

def moeller_trumbore_intersect(ray_origin, ray_direction, triangle_v1, triangle_v2, triangle_v3):
  """
  Checks for intersection between a ray and a triangle using the Möller-Trumbore algorithm.

  Args:
      ray_origin: Origin of the ray (numpy array of shape (3,)).
      ray_direction: Direction of the ray (normalized, numpy array of shape (3,)).
      triangle_v1, triangle_v2, triangle_v3: Vertices of the triangle (numpy arrays of shape (3,)).

  Returns:
      True if there's an intersection, False otherwise.
  """

  # Edge vectors
  edge1 = triangle_v2 - triangle_v1
  edge2 = triangle_v3 - triangle_v1

  # Calculate p, q, and t
  pvec = np.cross(ray_direction, edge2)
  det = np.dot(edge1, pvec)
  if abs(det) < 1e-6:
      return False

  tvec = ray_origin - triangle_v1
  u = np.dot(tvec, pvec) / det
  if u < 0 or u > 1:
      return False

  qvec = np.cross(tvec, edge1)
  v = np.dot(ray_direction, qvec) / det
  if v < 0 or u + v > 1:
      return False

  t = np.dot(edge2, qvec) / det

  return t > 0  # Check for positive t (intersection behind the ray origin is ignored)

  # Example usage (assuming you have ray_origin, ray_direction, and triangle vertices defined)
  if moeller_trumbore_intersect(ray_origin, ray_direction, vertex1, vertex2, vertex3):
    print("Intersection detected!")
  else:
    print("No intersection found.")

#%% Main
if __name__ == "__main__":

  # run main as example of how the code works
  visualise_vectors = True
  theresold = 0.7

  #%% Example 1 - Calculate the normal vector to a plane
  # Plane 1 (modify the vertices to test different scenarios)
  vertex1 = np.array([-9.774294e+01, -1.658581e+01, 2.546803e+01])
  vertex2 = np.array([-9.774294e+01, -1.859728e+01, 2.756273e+01])
  vertex3 = np.array([-1.005839e+02, -1.658581e+01, 2.756273e+01])
  face_femur = np.array([vertex1, vertex2, vertex3])
  plane_centre1 = calculate_centre_of_triangle(vertex1, vertex2, vertex3)
  normal_vector_femur = -calculate_normal_vector(face_femur[0], face_femur[1], face_femur[2]) # negative to point outwards
  
  # Plane 2 (modify the vertices to test different scenarios)
  vertex1b = vertex1 + 0.5
  vertex2b = vertex2 + 1
  vertex3b = vertex3 + 3
  face_ace = np.array([vertex1b, vertex2b, vertex3b])
  plane_centre2 = calculate_centre_of_triangle(vertex1b, vertex2b, vertex3b)
  normal_vector2 = calculate_normal_vector(face_ace[0], face_ace[1], face_ace[2])
  A,B,C,D = calculate_plane_coefficients(normal_vector2, plane_centre1)

  intercept_moeller = moeller_trumbore_intersect(plane_centre2, normal_vector2, vertex1, vertex2, vertex3)
  angle_between_faces = angle_between_two_faces(face_femur,face_ace)
  distance_planes = distance_points_3d(plane_centre1,plane_centre2)

  # if visualise_vectors is true, plot the vectors and planes
  if visualise_vectors:  
    plot_vector(normal_vector_femur,plane_centre1,color='blue',label='Normal Vector 1')
    plot_triangle(face_femur, facecolor='gray', alpha=0.5)
    plot_triangle(face_ace, facecolor='red', alpha=0.5)
  

  print("Normal Vector 1:", normal_vector_femur)
  print("Angle between faces:", angle_between_faces)
  print("Distance between planes:", distance_planes)
  print("Intercepts via moeller_trumbore method:", intercept_moeller)

  ax = update_figure() 
  
  if intercept_moeller:
    ax.set_title('normal vector 1 intercepts plane 2')
  else:
    ax.set_title('normal vector 1 does not intercept plane 2')

  # print the ouput of a second method using the normal vector and the angle between the faces
  if angle_between_faces < 45 and distance_planes < theresold:
    print("Planes at an angle less than 45 degrees (" , angle_between_faces ,") and within threshold distance (", theresold ,")")
    print("Normal vector 1 intercepts plane 2 (old method)")
  else:
    print("Planes at an angle greater than 45 degrees (" , angle_between_faces ,") or not within threshold distance (", theresold ,")")
    print("Normal vector 1 does not intercept plane 2 (old method 2)")

  plt.show()

  exit()
  
# %%
