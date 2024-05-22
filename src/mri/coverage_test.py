import numpy as np
import coverage as cv
from fractions import Fraction
from sympy import Point3D, Plane, Line3D 
from mpmath import *
from sympy.plotting import plot3d 

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
    

vertices1 = cv.load_stl_vertices(r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\test.stl')

p1 = Plane(Point3D(vertices1[0]), Point3D(vertices1[1]), Point3D(vertices1[2]))

# using perpendicular_plane() with two parameters 
p2 = p1.perpendicular_plane(vertices1[0],vertices1[1])
coeff1 = get_coefficients_form_plane_sympy(p1)
coeff2 = get_coefficients_form_plane_sympy(p2)
plane1 = cv.Plane(coeff1[0],coeff1[1],coeff1[2],coeff1[3])
plane2 = cv.Plane(coeff2[0],coeff2[1],coeff2[2],coeff2[3])
plane1.plot_plane()
plane2.plot_plane()
exit()
cv.plot_plane(coeff1[0],coeff1[1],coeff1[2],coeff1[3])
cv.plot_plane(coeff2[0],coeff2[1],coeff2[2],coeff2[3])

print(p1.is_perpendicular(p2))

cv.plt.show()