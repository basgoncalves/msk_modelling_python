import numpy as np
import os
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

def create_sphere(radius):
    phi, theta = np.mgrid[0.0:2.0*np.pi:100j, 0.0:np.pi:50j]
    x = radius * np.sin(theta) * np.cos(phi)
    y = radius * np.sin(theta) * np.sin(phi)
    z = radius * np.cos(theta)
    return x, y, z

def create_sphere_segment(radius, segment_radius):
    phi, theta = np.mgrid[0.0:2.0*np.pi:100j, 0.0:np.pi/2:50j]
    x = segment_radius * np.sin(theta) * np.cos(phi)
    y = segment_radius * np.sin(theta) * np.sin(phi)
    z = segment_radius * np.cos(theta)
    return x, y, z

def calculate_area(radius, segment_radius):
    segment_area = 2 * np.pi * segment_radius**2
    return segment_area

def plot_sphere_and_segment(radius, segment_radius):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    x, y, z = create_sphere(radius)
    ax.plot_surface(x, y, z, color='b', alpha=0.3)

    x_seg, y_seg, z_seg = create_sphere_segment(radius, segment_radius)
    ax.plot_surface(x_seg, y_seg, z_seg, color='r', alpha=0.6)

    plt.title('Sphere and Sphere Segment')
    
    # Save the plot
    current_folder = os.path.dirname(os.path.abspath(__file__))
    plt.savefig(os.path.join(current_folder, 'sphere_and_segment.png'))
    print(f"Plot saved as 'sphere_and_segment.png' in {current_folder}")
    
    plt.show()

if __name__ == "__main__":
    radius = float(input("Enter the radius of the sphere: "))
    segment_radius = radius * 1.05
    area = calculate_area(radius, segment_radius)
    print(f"Total area covered by the half sphere segment projected on the sphere: {area:.2f} square units")
    plot_sphere_and_segment(radius, segment_radius)