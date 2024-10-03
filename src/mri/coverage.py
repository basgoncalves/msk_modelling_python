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

def calculate_coverage_batch(maindir, legs, thresholds, subjects_to_run):
    """
    Calculate the acetabular coverage for a batch of subjects.
    """
    subjects = [entry for entry in os.listdir(maindir) if os.path.isdir(os.path.join(maindir, entry))]
    
    df = pd.DataFrame({"Subject": subjects})
    df.index.name = "Index"
    print(df)
        
    for subject in subjects:
      if subject not in subjects_to_run:
        continue
      for leg in legs:
        
        initial_time = time.time()  # start time to measure the total time of the process

        stl_file_femur = os.path.join(maindir, subject, 'Meshlab_BG', str('femoral_head_' + leg + '.stl'))
        stl_file_acetabulum = os.path.join(maindir, subject, 'Meshlab_BG', str('acetabulum_' + leg + '.stl'))

        if os.path.exists(stl_file_femur) and os.path.exists(stl_file_acetabulum):
          print(f"\nSubject: {subject}, Leg: {leg}")
        else:
          print(f"Files not found for {subject} {leg}")
          print(f"Files: {stl_file_femur}, {stl_file_acetabulum}")
          continue

        filename = os.path.basename(stl_file_femur)

        vertices_femur, centres_femur, normal_vectors_femur = pv.load_stl_vertices(stl_file_femur)
        vertices_ace, centres_ace, normal_vectors_ace = pv.load_stl_vertices(stl_file_acetabulum)

        nframes = len(centres_femur)
        print('number faces = ', len(centres_femur))
        print('data loaded in:', time.time() - initial_time)

        for threshold in thresholds:
          print(f"\nThreshold: {threshold}")
          covered_area = 0
          total_femur_area = 0
        for i,_ in enumerate(centres_femur[:nframes]):  
          show_loading_bar(i + 1, len(centres_femur[:nframes]))
          centre_face_femur = centres_femur[i]  
          face_femur = np.array([vertices_femur[i][0], vertices_femur[i][1], vertices_femur[i][2]])
          normal_vector_femur = calculate_normal_vector(face_femur[0], face_femur[1], face_femur[2])

          # distance to acetabulum based on threshold
          distances = pv.calculate_distances(centre_face_femur, centres_ace)
          distances_below_threshold = (distances <= threshold).astype(int)  
          valid_indices = np.where((distances <= threshold) & (distances > 0))[0]

          # calculate angle between the current face and the acetabulum faces 
          # that are below the threshold
          angle_between_faces = []
          normal_femur_intercepts_acetabulum_face = False
          for index in valid_indices:
            
            centre_face_femur = centres_femur[i]
            face_ace = np.array([vertices_ace[index][0], vertices_ace[index][1], vertices_ace[index][2]])
            angle_between_faces.append(pv.angle_between_two_faces(face_femur,face_ace))

            # using the Moeller-Trumbore algorithm to check if the normal vector of the acetabulum 
            normal_intercept = moeller_trumbore_intersect(centre_face_femur, normal_vector_femur, 
                face_ace[0], face_ace[1], face_ace[2])
            # check if the negative vector also intercepts the triangle (in care the vecotor is going outwards)
            neg_normal_intercept = moeller_trumbore_intersect(centre_face_femur, -normal_vector_femur, 
                face_ace[0], face_ace[1], face_ace[2])
            
            if normal_intercept or neg_normal_intercept:
              normal_femur_intercepts_acetabulum_face = True
              break
          
          angle_between_faces = np.array(angle_between_faces)

          # total area
          total_femur_area += pv.calculate_triangle_area_3d(vertices_femur[i][0], vertices_femur[i][1], vertices_femur[i][2]) 

          # check if triangle is covered AND the angle between the faces is less than 45 degrees
          if np.sum(distances_below_threshold) > 0 and normal_femur_intercepts_acetabulum_face:
            ax = pv.plot_triangle(np.array(vertices_femur[i]),facecolor='r',alpha=1)
            covered_area += pv.calculate_triangle_area_3d(vertices_femur[i][0], vertices_femur[i][1], vertices_femur[i][2])
          else:
            ax = pv.plot_triangle(np.array(vertices_femur[i]),facecolor='gray',alpha=0.7)

        # plot the acetabulum
        plot_stl_mesh(vertices_ace, facecolor='#8a9990', alpha=0.4) 

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
        new_folder = stl_file_femur.replace('.stl', f'_threshold_{threshold}')
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
          # Save the figure as an STL file
          stl_filename = os.path.join(new_folder, f'{filename}_{elev}_{azim}.stl')
          import pdb; pdb.set_trace()
          from mayavi import mlab
          scene = mlab.figure(figure=fig)
          # Save the scene as an STL file
          mlab.savefig('my_plot.stl')

        pv.plt.close(fig)

        # Save results to a text file
        filename = os.path.basename(stl_file_femur).replace('.stl','')
        txtfile = os.path.join(new_folder, f'{filename}.txt')
        with open(txtfile, 'w') as file:
          file.write(f"Coverage based on a threshold of {threshold} \n")
          file.write(f"Area Covered: {covered_area} \n")
          file.write(f"Total Femur Area: {total_femur_area}\n")
          file.write(f"Normalized Area Covered: {normalized_area}% \n")
          file.write(f"Total Time: {total_time}s\n")


if __name__ == "__main__":
  
  maindir = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage'
  legs = ['l']
  thresholds = [25] # distance threshold in mm
  # select the subjects to run
  subjects_to_run = ["044"]
  

  calculate_coverage_batch(maindir, legs, thresholds, subjects_to_run)