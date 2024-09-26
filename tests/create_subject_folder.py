import os
import pdb 

def create_subject_folders(folder_path):
  """
  Creates folders for subjects within the acetabular_coverage directory and a subfolder named Meshlab.

  Args:
      folder_path (str): Path to the directory containing the MRB files.
  """
  # Ensure FAIS_acetabular_stresses directory exists
  coverage_dir = os.path.join(os.path.dirname(folder_path), "acetabular_coverage")
  if not os.path.exists(coverage_dir):
    os.makedirs(coverage_dir)

  # Loop through files in the folder
  for filename in os.listdir(folder_path):
    if filename.endswith(".mrb"):
      # Extract subject name from filename (excluding .mrb)
      subject_name = filename[:-4]

      # Create subject folder within FAIS_acetabular_stresses
      subject_folder = os.path.join(coverage_dir, subject_name)
      if not os.path.exists(subject_folder):
        os.makedirs(subject_folder)

      # Create Meshlab subfolder within the subject folder
      meshlab_folder = os.path.join(subject_folder, "Meshlab")
      os.makedirs(meshlab_folder, exist_ok=True)  # Create Meshlab folder if it doesn't exist, ignoring errors



if __name__ == "__main__":
  # Replace 'path/to/your/folder' with the actual path to your folder containing MRB files
  folder_path = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\Scenes'
  create_subject_folders(folder_path)
  print("Folder creation completed!")
