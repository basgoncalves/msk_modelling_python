import msk_modelling_python as msk
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

def rotate_markers(matrix, angle, direction = 'x'):
    """Rotates the matrix around the x-axis by the specified angle.

    Args:
        matrix (numpy.array()): The input matrix with columns for time, X, Y, and Z coordinates. (e.g. matrix = np.array())
        angle(int): The rotation angle in degrees.

    Returns:
        The rotated matrix(numpy.array()).
    
    Example:
        matrix_unrotated = np.array([[0, 1, 2, 3], [1, 4, 5, 6], [2, 7, 8, 9]]) 
        rotated_matrix = rotate_markers(matrix = matrix, angle = 90, direction='x')
    """   

    # Create a rotation matrix around the x-axis
    rotation = Rotation.from_euler(direction, angle, degrees=True).as_matrix()

    # Apply the rotation matrix to the coordinates
    rotated_coordinates = np.dot(matrix, rotation.T)

    return rotated_coordinates
  
# example usage
plotting = False
trc_file_path = r"C:\Git\research_documents\students\marcel_BSc_vienna\static_00\static_00.trc"
trc_data, trc_df =  msk.bops.import_trc_file(trc_file_path)
time = trc_df['time'].tolist()
frame_rate = 1 / (time[1] - time[0])

for col in trc_df.columns:
  if 'time' in col.lower():
      continue
  
  lists = trc_df[col].tolist()
  matrix = np.array([list(item) for item in lists])
  rotated_matrix = rotate_markers(matrix = matrix, angle = 90, direction='x')

  # add the rotated markers to the trc data
  trc_df[col] = rotated_matrix
  
  # plot the original and rotated markers
  if plotting:
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(matrix[:, 1], matrix[:, 2], matrix[:, 3], label='Original')
    ax.scatter(rotated_matrix[:, 1], rotated_matrix[:, 2], rotated_matrix[:, 3], label='Rotated')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.legend()

# add time to the trc data and move it to the first column
trc_df.insert(0, 'time', time)

# save new trc file
new_trc_file_path = trc_file_path.replace('.trc', '_rotated.trc')
msk.bops.import_trc_file(trc_data, new_trc_file_path,frame_rate)

if plotting:
  plt.show()

