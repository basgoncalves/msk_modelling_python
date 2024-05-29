from planes_vectors import *
import planes_vectors as pv
import time
import os

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

def plot_stl_mesh(vertices, facecolor='gray', alpha=0.7):
  """
  Plots a 3D mesh using the provided vertices from load_stl_vertices.
  """
  for i in range(len(vertices)):
    pv.plot_triangle(np.array(vertices[i]),facecolor=facecolor,alpha=alpha)


# Example usage
initial_time = time.time()  
stl_file1 = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\013\Meshlab\femoral_head_r.stl'
stl_file2 = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\FAIS_acetabular_stresses\013\Meshlab\acetabulum_r.stl'

maindir = os.path.dirname(stl_file1)
filename = os.path.basename(stl_file1)

vertices1, centres1, normal_vectors1 = pv.load_stl_vertices(stl_file1)
vertices2, centres2, normal_vectors2 = pv.load_stl_vertices(stl_file2)

nframes = len(centres1)

print(centres1[:nframes])

print('number faces = ', len(centres1))
print('data loaded in:', time.time() - initial_time)
thresholds = [8]#,9,10,11,12,13,14,15]
for threshold in thresholds:
  print(f"\nThreshold: {threshold}")
  covered_area = 0
  total_femur_area = 0
  for i,_ in enumerate(centres1[:nframes]):  
    show_loading_bar(i + 1, len(centres1[:nframes]))
    point = centres1[i]  
    face1 = np.array([vertices1[i][0], vertices1[i][1], vertices1[i][2]])
    

    # distance to acetabulum based on threshold
    distances = pv.calculate_distances(point, centres2)
    distances_below_threshold = (distances <= threshold).astype(int)  
    valid_indices = np.where((distances <= threshold) & (distances > 0))[0]

    angle_between_faces = []
    for index in valid_indices:
      face2 = np.array([vertices2[index][0], vertices2[index][1], vertices2[index][2]])
      angle_between_faces.append(pv.angle_between_two_faces(face1,face2)) 
    angle_between_faces = np.array(angle_between_faces)

    # total area
    total_femur_area += pv.calculate_triangle_area_3d(vertices1[i][0], vertices1[i][1], vertices1[i][2]) 

    # check if triangle is covered
    if np.sum(distances_below_threshold) > 0 and np.any(angle_between_faces < 45):
      ax = pv.plot_triangle(np.array(vertices1[i]),facecolor='r',alpha=1)
      covered_area += pv.calculate_triangle_area_3d(vertices1[i][0], vertices1[i][1], vertices1[i][2])
    else:
      ax = pv.plot_triangle(np.array(vertices1[i]),facecolor='gray',alpha=0.7)

  # plot the acetabulum
  plot_stl_mesh(vertices2, facecolor='#8a9990', alpha=0.4) 

  covered_area = round(covered_area,1)
  total_femur_area = round(total_femur_area,1)
  normalized_area = round(covered_area / total_femur_area *100,1)
  total_time = round(time.time() - initial_time,1)
  print("\n covered area:", covered_area)
  print("total femur area:", total_femur_area)
  print("normalized covered area:", normalized_area,'%')
  print("total time:", total_time,'s')

  # add text to the plot (coverage and threshold)
  ax = pv.plt.gca()
  ax.text2D(0.05, 0.05, f'Coverage: {normalized_area}', transform=ax.transAxes)

  # create a new folder for the current threshold
  new_folder = stl_file1.replace('.stl', f'_threshold_{threshold}')
  if os.path.exists(new_folder):
    print("Folder already exists")
  else:
    os.mkdir(new_folder)

  # save fig from different angles
  # Define desired viewpoints (adjust angles for your preference)
  viewpoints = [(0,0), (90,90), (10, 20), (45, 30), (-20, 60)]  # Elevation (elev), Azimuth (azim)

  # Loop through viewpoints and save images
  print("Saving images in different rotations...")
  for i, (elev, azim) in enumerate(viewpoints):
    print(f"Viewpoint {i+1}/{len(viewpoints)}: Elevation={elev}, Azimuth={azim}")
    ax.view_init(elev=elev, azim=azim)  # Set viewpoint for each image
    figname = os.path.join(new_folder, f'{filename}_{elev}_{azim}.png')
    fig = pv.plt.gcf()  
    fig.savefig(figname, bbox_inches='tight') 

  pv.plt.close(fig)

  # Save results to a text file
  filename = os.path.basename(stl_file1).replace('.stl','')
  txtfile = os.path.join(new_folder, f'{filename}.txt')
  with open(txtfile, 'w') as file:
    file.write(f"Coverage based on a threshold of {threshold} \n")
    file.write(f"Area Covered: {covered_area} \n")
    file.write(f"Total Femur Area: {total_femur_area}\n")
    file.write(f"Normalized Area Covered: {normalized_area}% \n")
    file.write(f"Total Time: {total_time}s\n")

pv.compare_normalized_coverages(maindir)
figname = os.path.join(maindir, f'coverage_per_threshold.png')
pv.plt.savefig(figname)
