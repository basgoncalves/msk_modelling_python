import os
import shutil
from tkinter.filedialog import askdirectory

def compare_directories(dir1, dir2):

    files_not_in_dir1 = set()

    # Get all files in dir2
    for root, dirs, files in os.walk(dir2):
        for file in files:
            filepath = os.path.join(root, file)
            relative_path = filepath[len(dir2):].lstrip(os.path.sep)
            path_dir1 = os.path.join(dir1, relative_path)
            if not os.path.exists(path_dir1):
                files_not_in_dir1.add(filepath)

    with open(r'C:\Users\Bas\Desktop\output.txt', 'w') as file_txt:
    # Print the files
        for file in files_not_in_dir1:
            try:
                file_txt.write(file + '\n')
            except Exception as e:
                print(f"Error: {e}")
                continue
            # Copy the file to dir1
            try:
                unique_part = os.path.relpath(file, dir2)
                destination = os.path.join(dir1, unique_part)
                destination_directory = os.path.dirname(destination)
                os.makedirs(destination_directory, exist_ok=True) # Create the destination directory if it doesn't exist
                shutil.copy2(file, destination)
            except Exception as e:
                print(f"Error: {e}")
                continue


dir1 = askdirectory('Select the first directory')
dir2 = askdirectory('Select the second directory')


compare_directories(dir1, dir2) # Call the compare_directories function

