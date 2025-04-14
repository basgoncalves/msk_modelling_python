from mpl_toolkits.mplot3d import Axes3D

import matplotlib.pyplot as plt

def plot_cube(length, height, width):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Define the coordinates of the cube
    x = [0, length, length, 0, 0, length, length, 0]
    y = [0, 0, height, height, 0, 0, height, height]
    z = [0, 0, 0, 0, width, width, width, width]

    # Plot the cube surface
    ax.plot_surface([x[0], x[1]], [y[0], y[1]], [z[0], z[1]], color='r')
    ax.plot_surface([x[1], x[2]], [y[1], y[2]], [z[1], z[2]], color='g')
    ax.plot_surface([x[2], x[3]], [y[2], y[3]], [z[2], z[3]], color='b')
    ax.plot_surface([x[3], x[0]], [y[3], y[0]], [z[3], z[0]], color='y')
    ax.plot_surface([x[4], x[5]], [y[4], y[5]], [z[4], z[5]], color='c')
    ax.plot_surface([x[5], x[6]], [y[5], y[6]], [z[5], z[6]], color='m')
    ax.plot_surface([x[6], x[7]], [y[6], y[7]], [z[6], z[7]], color='k')
    ax.plot_surface([x[7], x[4]], [y[7], y[4]], [z[7], z[4]], color='w')
    ax.plot_surface([x[0], x[4]], [y[0], y[4]], [z[0], z[4]], color='r')
    ax.plot_surface([x[1], x[5]], [y[1], y[5]], [z[1], z[5]], color='g')
    ax.plot_surface([x[2], x[6]], [y[2], y[6]], [z[2], z[6]], color='b')
    ax.plot_surface([x[3], x[7]], [y[3], y[7]], [z[3], z[7]], color='y')

    # Set labels and title
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Cube')

    # Show the plot
    plt.show()

# Example usage
length = 42
height = 62
width = 10
plot_cube(length, height, width)
# Calculate and display volume
volume = length * height * width
print("Volume:", volume)