import os
import shutil


def extract_files_by_type(src_folder, file_extensions):
    # Split the file extensions by semicolon
    extensions = file_extensions.split(';')
    
    # Create the destination folder name
    dest_folder = f"{src_folder}_extracted"
    
    # Walk through the source folder
    for root, dirs, files in os.walk(src_folder):
        print(f"Processing folder: {root}")
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