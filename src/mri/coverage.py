import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

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

  def create_figure(self):
    try:
      # Attempt to get the current figure
      fig = plt.gcf()
      ax = fig.get_axes()
    except (AttributeError, ValueError):
      fig = plt.figure(figsize=(plt.rcParams['figure.figsize'][0] * 1.5, plt.rcParams['figure.figsize'][1] * 1.5))
      ax = fig.add_subplot(111, projection='3d')

    return ax
  
  def plot_plane(self,x_lim=[-0.1,0.1], y_lim=[-0.1,0.1],tolerance=1e-6,color='lightgray',alpha=0.7):

    a = self.a
    b = self.b
    c = self.c
    d = self.d

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
    ax = self.create_figure()

    # Calculate grid points within the limits
    xx, yy = np.meshgrid(np.linspace(x_lim[0], x_lim[1], 40),
                        np.linspace(y_lim[0], y_lim[1], 40))

    # Calculate z values for the grid points using the plane equation
    # z = (-d - a * xx - b * yy) / c
    mask = np.abs(c) > tolerance  # Mask for points where c is not close to zero
    z = np.zeros_like(xx)
    z[mask] = (d - a * xx[mask] - b * yy[mask]) / c

    # Plot the plane using the generated grid
    x_1d = xx.ravel()
    y_1d = yy.ravel()
    z_1d = z.ravel()

    ax.plot_trisurf(x_1d, y_1d, z_1d, color=color, alpha=0.7)

    # Set labels and title
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Plane")

    return ax


def load_stl_vertices(filename):
  """
  Loads the vertices from a text-based STL file.

  Args:
      filename: The path to the STL file.

  Returns:
      A list of NumPy arrays, where each array represents a vertex (x, y, z).
  """

  vertices = []
  with open(filename, 'r') as f:
    lines = f.readlines()

  for line in lines:
    if line.startswith("      vertex"):
      # Extract coordinates (assuming scientific notation)
      coordinates = [float(x) for x in line.split()[1:]]
      vertices.append(np.array(coordinates))

  return vertices

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

def plot_plane(a, b, c, d,x_lim=[-0.1,0.1], y_lim=[-0.1,0.1],tolerance=1e-6,color='lightgray',alpha=0.7):
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

  # Calculate grid points within the limits
  xx, yy = np.meshgrid(np.linspace(x_lim[0], x_lim[1], 40),
                       np.linspace(y_lim[0], y_lim[1], 40))

  # Calculate z values for the grid points using the plane equation
  # z = (-d - a * xx - b * yy) / c
  mask = np.abs(c) > tolerance  # Mask for points where c is not close to zero
  z = np.zeros_like(xx)
  z[mask] = (d - a * xx[mask] - b * yy[mask]) / c

  # Plot the plane using the generated grid
  x_1d = xx.ravel()
  y_1d = yy.ravel()
  z_1d = z.ravel()

  ax.plot_trisurf(x_1d, y_1d, z_1d, color=color, alpha=0.7)

  # Set labels and title
  ax.set_xlabel("X")
  ax.set_ylabel("Y")
  ax.set_zlabel("Z")
  ax.set_title("Plane")

  return ax

def plot_normal_vector_to_plane(normal_vector, point):
  """
  Plots a normal vector to a plane at a given point.

  Args:
      normal_vector: A NumPy array representing the normal vector.
      point: A NumPy array representing the point where the normal vector originates.
  """
  # Plot the normal vector
  ax.quiver(point[0], point[1], point[2],
            normal_vector[0], normal_vector[1], normal_vector[2],
            color='blue', length=10.0, arrow_length_ratio=0.1)

  # Set labels and title
  ax.set_xlabel("X")
  ax.set_ylabel("Y")
  ax.set_zlabel("Z")
  ax.set_title("Normal Vector to Plane")

def calculate_plane_function(v1, v2, v3, ratio=0.01):
  # Calculate the normal vector of the plane
  normal_vector = np.cross(v2 - v1, v3 - v1)

  # Calculate the coefficients of the plane equation
  a, b, c = normal_vector

  # Calculate the d coefficient of the plane equation
  d = -np.dot(normal_vector, v1)

  x_lim = [min(v1[0], v2[0], v3[0]) - ratio*min(v1[0], v2[0], v3[0]), max(v1[0], v2[0], v3[0]) + ratio*max(v1[0], v2[0], v3[0])]
  y_lim = [min(v1[1], v2[1], v3[1]) - ratio*min(v1[1], v2[1], v3[1]), max(v1[1], v2[1], v3[1]) + ratio*max(v1[1], v2[1], v3[1])]

  return a, b, c, d, x_lim, y_lim

def calculate_plane_center(v1, v2, v3):
  # Calculate the center by averaging the coordinates of the three points
  center = (v1 + v2 + v3) / 3

  return center

def calculate_normal_vector(v1, v2, v3):
  # Calculate two edge vectors along the plane
  edge1 = v2 - v1
  edge2 = v3 - v1

  # Calculate the normal vector as the cross product of the edge vectors
  normal = np.cross(edge1, edge2)

  # Normalize the normal vector (optional)
  normal = normal / np.linalg.norm(normal)

  return normal

def get_perpendicular_plane_coefficients_method1(normal_vector):
   # Plane passes through the origin, so d = 0
  coefficients = np.concatenate((normal_vector, [0]))

  return coefficients

def get_perpendicular_plane(plane1_normal, point_on_plane2):
  """
  Finds the equation of a plane perpendicular to another plane.

  Args:
      plane1_normal: A NumPy array representing the normal vector of the first plane.
      point_on_plane2: A NumPy array representing a point on the second plane.

  Returns:
      A list containing:
          - A NumPy array representing the normal vector of the perpendicular plane.
          - A float representing the constant d in the plane equation.
  """

  # Ensure plane1_normal is a unit vector
  plane1_normal = plane1_normal / np.linalg.norm(plane1_normal)

  # The normal vector of the perpendicular plane is the same as the normal vector of plane1
  normal_perpendicular = plane1_normal

  # Use the point_on_plane2 and normal vector to get the constant d in the equation
  d = -np.dot(normal_perpendicular, point_on_plane2)

  return normal_perpendicular, d

def get_perpendicular_plane_from_equation(plane1_equation):
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


def plot_plane_and_points(v1,v2,v3):
  a, b, c, d, x_lim, y_lim = calculate_plane_function(v1, v2, v3, ratio=1)
  plot_3D_points([v1, v2, v3])
  plot_plane(a, b, c, d,x_lim, y_lim)
  centre = calculate_plane_center(v1, v2, v3)
  normal_vector = calculate_normal_vector(v1, v2, v3)
  plot_normal_vector_to_plane(normal_vector, centre)

  return a, b, c, d, centre, normal_vector, x_lim, y_lim

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
  if 'ax' in globals():
    print('using existing figure')
    return None
  else:
    print('creating new figure')
    fig = plt.figure(figsize=(plt.rcParams['figure.figsize'][0] * 1.5, plt.rcParams['figure.figsize'][1] * 1.5))
    ax = fig.add_subplot(111, projection='3d')
    return ax

if __name__ == "__main__": 

  def generate_random_plane_points():
    """
    Generates a random plane equation and three points on that plane.

    Returns:
        A tuple containing:
            - A list of coefficients (a, b, c, d) for the random plane.
            - A list of three NumPy arrays representing the defined points.
    """

    # Generate random coefficients for the plane equation
    a, b, c, d = np.random.rand(4)

    # Ensure at least one coefficient (a, b, or c) is non-zero to define a proper plane
    if abs(a) + abs(b) + abs(c) < 1e-6:
      a = 1.0  # Assign a small non-zero value to a if all coefficients are close to zero

    # Three points on the plane using different approaches:

    # Point 1: Origin (0, 0, 0) always lies on the plane
    point1 = np.array([0, 0, 0])

    # Point 2: Random offset from origin
    offset = np.random.rand(3)
    point2 = point1 + offset

    # Point 3 using a random direction vector
    direction = np.random.rand(3) - 0.5  # Offset to avoid zero values
    point3 = point1 + direction

    return [a, b, c, d], [point1, point2, point3]

  # Generate coefficients and points for a random plane
  # coefficients, points = generate_random_plane_points()
  coefficients = [1.0, 1.0, 3.0, 1.0]
  plane_equation = f"{coefficients[0]}x + {coefficients[1]}y + {coefficients[2]}z + {coefficients[3]} = 0"
  print("Plane equation:", plane_equation)
  

  ax = create_figure()
  plot_plane(coefficients[0], coefficients[1], coefficients[2], coefficients[3],[-1,1],[-1,1])
  # points =  generate_points_on_plane(coefficients)
  

  def find_z(coef, x, y):
    return (coef[3]-x*coef[0]-y*coef[1])/coef[2]
  
  def generate_points_on_plane(coefficients):
    points = [np.array([0,0,find_z(coefficients, 0, 0)]),
              np.array([0,1,find_z(coefficients, 0, 1)]),
              np.array([1,0,find_z(coefficients, 1, 0)])]
    return points
  points = generate_points_on_plane(coefficients)
  
  print("Points on the plane:", points)
  plot_3D_points(points)

  # second plane 
  x_lim = [-2,2]
  y_lim = [-2,2]
  centre = calculate_plane_center(points[0], points[1], points[2])
  normal_vector = calculate_normal_vector(points[0], points[1], points[2])
  plane2, d = get_perpendicular_plane_from_equation(coefficients)
  print(plane2)
  plot_plane(plane2[0], plane2[1], plane2[2], d ,x_lim, y_lim,color='green')
  exit()  
  points2 =  generate_points_on_plane(plane2)
  plot_3D_points(points2,col='black')
  normal_vector2 = calculate_normal_vector(points2[0], points2[1], points2[2])

  intersects_plane2 = does_vector_intersect_plane(centre, normal_vector, plane2[0], plane2[1], plane2[2], plane2[3], normal_vector2,x_lim, y_lim)


  plt.show()

  exit()

  ax = create_figure()
  x_lim = [-2,2]
  y_lim = [-2,2]
  plane1 = [1, 0, 0, 0]
  plot_plane(plane1[0], plane1[1], plane1[2], plane1[3],x_lim, y_lim)
  points =  generate_points_on_plane(plane1)
  plot_3D_points(points)
  plt.show()
  exit()

  centre = calculate_plane_center(points[0], points[1], points[2])
  normal_vector = calculate_normal_vector(points[0], points[1], points[2])

  plane2 = get_perpendicular_plane_coefficients_method1(normal_vector)
  plot_plane(plane2[0], plane2[1], plane2[2], plane2[3],x_lim, y_lim)
  points2 =  generate_points_on_plane(plane2)
  plot_3D_points(points2)

  normal_vector2 = calculate_normal_vector(points2[0], points2[1], points2[2])

  intersects_plane2 = does_vector_intersect_plane(centre, normal_vector, plane2[0], plane2[1], plane2[2], plane2[3], normal_vector2,x_lim, y_lim)

  plt.show()
  exit()

  # face 1
  v1 = np.array([-1.039459e+02, -2.215638e+01, -1.938544e+01])
  v2 = np.array([-1.043997e+02, -2.193705e+01, -1.934748e+01])
  v3 = np.array([-1.040420e+02, -2.218708e+01, -1.981359e+01])
  a, b, c, d, centre, normal_vector, x_lim, y_lim = plot_plane_and_points(v1,v2,v3)

  # face 2
  v1 = np.array([-2.039459e+02, -3.215638e+01, -4.938544e+01])
  v2 = np.array([-2.043997e+02, -3.193705e+01, -0.934748e+01])
  v3 = np.array([-2.040420e+02, -3.218708e+01, -2.981359e+01])
  a2, b2, c2, d2, centre2, normal_vector2, x_lim2, y_lim2 = plot_plane_and_points(v1,v2,v3)





  # Example usage
  point = np.array([-1.0, 2.0, 3.0])
  direction = np.array([1.0, 1.0, 1.0])
  a1, b1, c1, d1 = 1.0, 1.0, 1.0, 0.0  # Plane 1 equation (x+y+z=0)
  a2, b2, c2, d2 = 0.0, 1.0, 0.0, 1.0  # Plane 2 equation (y=1)
  normal2 = np.array([0.0, 1.0, 0.0])  # Normal vector of plane 2

  intersects_plane2 = does_vector_intersect_plane(centre, normal_vector, a2, b2, c2, d2, normal_vector2,x_lim2, y_lim2)
  plt.show()