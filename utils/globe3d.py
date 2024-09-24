import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Create a 3D globe
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Earth radius (in arbitrary units for visualization)
earth_radius = 1

# Define latitude and longitude for Portugal, Vienna, and Finland
portugal_coords = (38.7223, -9.1393)  # Lisbon, Portugal
vienna_coords = (48.2082, 16.3738)   # Vienna, Austria
finland_coords = (61.9241, 25.7482)  # Helsinki, Finland

# Convert latitude and longitude to 3D Cartesian coordinates
def lat_lon_to_cartesian(lat, lon):
    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)
    x = earth_radius * np.cos(lat_rad) * np.cos(lon_rad)
    y = earth_radius * np.cos(lat_rad) * np.sin(lon_rad)
    z = earth_radius * np.sin(lat_rad)
    return x, y, z

portugal_cartesian = lat_lon_to_cartesian(*portugal_coords)
vienna_cartesian = lat_lon_to_cartesian(*vienna_coords)
finland_cartesian = lat_lon_to_cartesian(*finland_coords)

# Plot the Earth's surface
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
x = earth_radius * np.outer(np.cos(u), np.sin(v))
y = earth_radius * np.outer(np.sin(u), np.sin(v))
z = earth_radius * np.outer(np.ones(np.size(u)), np.cos(v))
ax.plot_surface(x, y, z, color='b')

# Plot vectors from Portugal to Vienna and Finland
ax.quiver(*portugal_cartesian, *(vienna_cartesian - portugal_cartesian), color='r', label='Portugal to Vienna')
ax.quiver(*portugal_cartesian, *(finland_cartesian - portugal_cartesian), color='g', label='Portugal to Finland')

# Customize the plot
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('3D Globe with Vectors')
ax.legend()

# Show the plot
plt.show()

