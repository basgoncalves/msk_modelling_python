from coverage import *
import coverage as cv
import time

def show_loading_bar(iteration, total_iterations, bar_length=20):
  """
  Shows a dynamic loading bar in the terminal.

  Args:
      iteration: The current iteration number (int).
      total_iterations: The total number of iterations in the loop (int).
      bar_length: The desired length of the loading bar (int, default=20).
  
  Example:
    for i in range(6000):
      # Simulate some work
      show_loading_bar(i + 1, 6000)
  """

  # Calculate progress percentage
  progress = float(iteration) / total_iterations

  # Construct the loading bar elements
  filled_length = int(round(bar_length * progress))
  empty_length = bar_length - filled_length

  filled_bar = '#' * filled_length
  empty_bar = '-' * empty_length

  # Print the loading bar
  print(f'[{filled_bar}{empty_bar}] ({iteration}/{total_iterations})', end='\r')

  # Clear the line after the loop finishes
  if iteration == total_iterations:
    print()

# Example usage
initial_time = time.time()  
stl_file1 = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\Segmentation_L_femur_mesh.stl'
stl_file2 = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\010\Meshlab\Segmentation_L_pelvis_mesh.stl'

vertices1, centres1 = cv.load_stl_vertices(stl_file1)
vertices2, centres2 = cv.load_stl_vertices(stl_file2)

print('number faces = ', len(centres1))
print('data loaded in:', time.time() - initial_time)
threshold = 10
covered_area = 0
total_femur_area = 0
nframes = len(centres1)
print("len(centres1):", len(centres1[:nframes]))
for i,_ in enumerate(centres1[:nframes]):  
  show_loading_bar(i + 1, len(centres1[:nframes]))
  point = centres1[i]  # Example point (x, y, z)
  matrix = centres2 # Example matrix with 60000 3D points

  distances = cv.calculate_distances(point, matrix)
  distances_below_threshold = (distances <= threshold).astype(int)
  total_femur_area += cv.calculate_triangle_area_3d(vertices1[i][0], vertices1[i][1], vertices1[i][2])
  if np.sum(distances_below_threshold) > 0:
    cv.plot_triangle(np.array(vertices1[i]),facecolor='r')
    covered_area += cv.calculate_triangle_area_3d(vertices1[i][0], vertices1[i][1], vertices1[i][2])
  else:
    cv.plot_triangle(np.array(vertices1[i]),facecolor='gray')

covered_area = round(covered_area,1)
total_femur_area = round(total_femur_area,1)
normalized_area = round(covered_area / total_femur_area *100,1)
total_time = round(time.time() - initial_time,1)
print("\n covered area:", covered_area)
print("total femur area:", total_femur_area)
print("normalized covered area:", normalized_area,'%')
print("total time:", total_time,'s')

# Save results to a text file
txtfile = stl_file1.replace('.stl', '.txt')
with open(txtfile, 'w') as file:
  file.write(f"Coverage based on a threshold of {threshold} \n")
  file.write(f"Area Covered: {covered_area} \n")
  file.write(f"Total Femur Area: {total_femur_area}\n")
  file.write(f"Normalized Area Covered: {normalized_area}% \n")
  file.write(f"Total Time: {total_time}s\n")

cv.plt.savefig(stl_file1.replace('.stl', '.png'))
