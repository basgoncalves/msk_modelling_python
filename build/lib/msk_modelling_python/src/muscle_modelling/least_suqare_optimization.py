import numpy as np
import matplotlib.pyplot as plt

def add_text_points(ax, markers):
    for i in range(markers.shape[0]):
        ax.text(markers[i, 0], markers[i, 1], markers[i, 2], str(i), color="blue", fontsize=9)

model_markers = np.array([[0,0,0], [1,0,0], [0,1,0]])
# object 2
experimental_markers = np.array([[0,0.5,0.5], [1.5,0.5,0], [0.5,1.5,0]])
weights = np.array([30,2,1])

# Calculate the least square positions
least_square_positions = np.linalg.lstsq(np.diag(weights) @ experimental_markers, np.diag(weights) @ model_markers, rcond=None)[0]

# Plot the 3 objects
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot model_markers
ax.scatter(model_markers[:, 0], model_markers[:, 1], model_markers[:, 2], c='r', label='Model Markers')
add_text_points(ax, model_markers)

# Plot experimental_markers
ax.scatter(experimental_markers[:, 0], experimental_markers[:, 1], experimental_markers[:, 2], c='g', label='Experimental Markers')
add_text_points(ax, experimental_markers)

# Plot least_square_positions
ax.scatter(least_square_positions[:, 0], least_square_positions[:, 1], least_square_positions[:, 2], c='b', label='Least Square Positions')
add_text_points(ax, least_square_positions)

ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.legend(['model_markers', 'experimental_markers', 'least_square_positions'])

plt.show()


