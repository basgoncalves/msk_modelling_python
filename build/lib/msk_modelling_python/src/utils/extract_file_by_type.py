import os
import shutil
import numpy as np


def extract_files_by_type(src_folder, file_extensions):
    # Split the file extensions by semicolon
    extensions = file_extensions.split(';')
    
    # Create the destination folder name
    dest_folder = f"{src_folder}_extracted"
    
    list_skip = list(np.linspace(0, 58, 1))
    list_skip = [f"{i:03}" for i in range(1, 59)]
    
    # Walk through the source folder
    for root, dirs, files in os.walk(src_folder):
        
        stop_root = False
        for skip in list_skip:
            compare_path = os.path.join(src_folder, skip)
            if compare_path in root:
                print(f"Skipping {root}")
                stop_root = True
                continue
            
        if stop_root:
            continue
        
        print(f"Extracting files from {root}")
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                # Create the corresponding destination folder structure
                relative_path = os.path.relpath(root, src_folder)
                dest_path = os.path.join(dest_folder, relative_path)
                os.makedirs(dest_path, exist_ok=True)
                
                # Copy the file to the destination folder
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_path, file)
                try:
                    shutil.copy2(src_file, dest_file)
                except Exception as e:
                    print(f"Error copying {src_file} to {dest_file}: {e}")

if __name__ == "__main__":
    src_folder = input("Enter the source folder path: ")
    file_extensions = input("Enter the file extensions to extract (e.g., .c3d;.trc;.pdf): ")
    extract_files_by_type(src_folder, file_extensions)