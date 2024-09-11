import os
import trimesh
import numpy as np
import trimesh
import numpy as np
import tkinter as tk
from tkinter import filedialog
from scipy.optimize import least_squares
import matplotlib.pyplot as plt

def error_function(params, points, centroid):
    center = params[:3]
    radius = params[3]
    distances = np.linalg.norm(points - center, axis=1) - radius
    return distances


def calculate_centroid(mesh_path = ''):
    if not mesh_path:
        mesh_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])
    mesh = trimesh.load(mesh_path)

    points = mesh.vertices
    centroid = np.mean(points, axis=0)

    distances = np.linalg.norm(points - centroid, axis=1)
    initial_radius = np.mean(distances)

    return points, centroid, initial_radius

def generate_sphere_points(center, radius, num_points=1000):
    phi = np.random.uniform(0, np.pi, num_points)
    theta = np.random.uniform(0, 2 * np.pi, num_points)
    x = center[0] + radius * np.sin(phi) * np.cos(theta)
    y = center[1] + radius * np.sin(phi) * np.sin(theta)
    z = center[2] + radius * np.cos(phi)

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
    plt.savefig(os.path.join(os.path.dirname(mesh_path), filename_without_extension + '_fitted_sphere.png'))

    return covered_area
    


if __name__ == '__main__':

    mesh_path = filedialog.askopenfilename(title='Select STL file', filetypes=[('STL Files', '*.stl')])
    covered_area = fit_sphere_and_plot(mesh_path)
    print(f"Approximate covered area of the sphere: {covered_area:.1f} mm^2")
    plt.show()
