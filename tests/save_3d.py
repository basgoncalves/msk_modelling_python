import os
from mayavi import mlab
import numpy as np

# Create a sphere
mlab.figure(1, bgcolor=(1, 1, 1))

# Generate data for the sphere
phi, theta = np.mgrid[0:np.pi:100j, 0:2*np.pi:100j]
x = np.sin(phi) * np.cos(theta)
y = np.sin(phi) * np.sin(theta)
z = np.cos(phi)

# Create the mesh
sphere = mlab.mesh(x, y, z, color=(0.5, 0.5, 0.5))

# Save the scene as a PNG image
current_folder = os.path.dirname(os.path.abspath(__file__))
mlab.savefig(os.path.join(current_folder, 'my_plot.obj'))
