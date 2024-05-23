import numpy as np
import coverage as cv
from fractions import Fraction
from sympy import Point3D, Plane, Line3D 
from mpmath import *
from sympy.plotting import plot3d 
import time

def convert_str_to_float(text):
  """
  Converts a string representation of a number with a slash (/) to a float.

  Args:
      text: The string to convert (e.g., "200/66").

  Returns:
      The converted float value or None if the conversion fails.

  Raises:
      ValueError: If the denominator is zero.
  """

  try:
    # Split the string by the slash
    numerator, denominator = text.split("/")

    # Convert numerator and denominator to floats
    return float(numerator) / float(denominator)
  except (ValueError, ZeroDivisionError):
    # Handle potential errors during conversion (including zero division)
    return None

def get_coefficients_form_plane_sympy(plane):
  ''' 
  get the coefficients from a plane object from sympy
  '''
  if not isinstance(plane, Plane):
    raise ValueError('plane should be a Plane object')
    
  coefficients = []
  for i in plane.equation().args:
    coef = str(i).replace('*','').replace('x','').replace('y','').replace('z','')
    coefficients.append(convert_str_to_float(coef))
  return coefficients

def calculate_triangle_area_3d(point1, point2, point3):
    vector1 = np.array(point2) - np.array(point1)
    vector2 = np.array(point3) - np.array(point1)
    cross_product = np.cross(vector1, vector2)
    area = 0.5 * np.linalg.norm(cross_product)
    return area

def calculate_distance(point1, point2):
  """
  Calculates the 3D Euclidean distance between two points.

  Args:
      point1: A NumPy array representing the first point (3D coordinates).
      point2: A NumPy array representing the second point (3D coordinates).

  Returns:
      The Euclidean distance between the two points.
  """

  # Calculate the difference between corresponding coordinates
  difference = point2 - point1

  # Calculate the magnitude (distance) using the Euclidean norm
  distance = np.linalg.norm(difference)

  return distance

def mean_distance_verticies(vertices1, vertices2):
  """
  Calculates the mean distance between two sets of vertices.

  Args:
      vertices1: A list of vertices (x, y, z) for the first set.
      vertices2: A list of vertices (x, y, z) for the second set.

  Returns:
      The mean distance between the two sets of vertices.
  """

  # Check if the number of vertices is not equal
  if len(vertices1) != len(vertices2):
    raise ValueError('The number of vertices in the two files are not equal')

  # loop through the vertices and calculate the distance
  sum_distances = 0
  for i in range(len(vertices1)):
    sum_distances += calculate_distance(vertices1[i], vertices2[i])
  
  # Calculate the mean distance
  return sum_distances / len(vertices1)

def find_close_vertices(vertices1, vertices2, threshold):
  """
  Finds indices of vertices in vertices1 that have at least one close point in vertices2.

  Args:
      vertices1: A list of NumPy arrays representing points in 3D space.
      vertices2: Another list of NumPy arrays representing points in 3D space.
      threshold: The maximum distance for a point in vertices2 to be considered close.

  Returns:
      A list of indices from vertices1 that have at least one close point in vertices2.
  """

  close_vertices_idx = []
  for i, point1 in enumerate(vertices1):
    # Iterate through each point in vertices2
    for point2 in vertices2:
      # Calculate distance between current points
      distance = mean_distance_verticies(point1,point2)
      # Check if distance is less than or equal to the threshold
      if distance <= threshold:
        # Add the index of point1 from vertices1 if a close point is found
        close_vertices_idx.append(i)
        # Since we only need one close point, break out of the inner loop
        break

  return close_vertices_idx


vertices1 = cv.load_stl_vertices(r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\test.stl')
vertices2 = cv.load_stl_vertices(r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\test_pelvis.stl')

# vertices1 = cv.load_stl_vertices(r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\Segmentation_L_femur_mesh.stl')
# vertices2 = cv.load_stl_vertices(r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\Segmentation_L_pelvis_mesh.stl')
close_vertices_idx = find_close_vertices(vertices1, vertices2, threshold=18.3)
face_idx = []
area = 0
# Initialize the progress bar
total_iterations = len(close_vertices_idx)
progress_bar_length = 50
progress_bar = "[" + " " * progress_bar_length + "]"
progress_bar_index = 0

for i in range(len(vertices1)):
  if i in close_vertices_idx:
    x,y,z = vertices1[i]
    cv.plot_triangle(x,y,z,facecolor='r')
    area += calculate_triangle_area_3d(vertices1[i][0], vertices1[i][1], vertices1[i][2])
  else:
    x,y,z = vertices1[i]
    cv.plot_triangle(x,y,z,facecolor='gray')

  # Update the progress bar
  progress = (i * len(vertices1)) / total_iterations
  progress_bar_index = int(progress * progress_bar_length)
  progress_bar = "[" + "#" * progress_bar_index + " " * (progress_bar_length - progress_bar_index) + "]"

  # Print the progress bar
  print("\r" + progress_bar, end="")
  time.sleep(0.1)


total_femur_area = len(vertices1) * calculate_triangle_area_3d(vertices1[0][0], vertices1[0][1], vertices1[0][2]) # femur area = sum of all triangles
normalized_area = area / total_femur_area *100
print("\narea:", area)
print("total femur area:", total_femur_area)
print("normalized area:", normalized_area)
cv.plt.show()
