import os
import shutil


def extract_files_by_type(src_folder, file_extension):
    # Create the destination folder name
    dest_folder = f"{src_folder}_{file_extension}"
    
    # Walk through the source folder
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            if file.endswith(file_extension):
                # Create the corresponding destination folder structure
                relative_path = os.path.relpath(root, src_folder)
                dest_path = os.path.join(dest_folder, relative_path)
                os.makedirs(dest_path, exist_ok=True)
                
                # Copy the file to the destination folder
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_path, file)
                shutil.copy2(src_file, dest_file)
                print(f"Copied {src_file} to {dest_file}")

if __name__ == "__main__":
    src_folder = input("Enter the source folder path: ")
    file_extension = input("Enter the file extension to extract (e.g., .txt): ")
    extract_files_by_type(src_folder, file_extension)