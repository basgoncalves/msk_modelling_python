import os
import shutil


def copy_files_to_parent_folder(folder_path):
    """
    Copy files from subdirectories to the parent directory.

    Args:
        folder_path (str): The path of the parent directory.

    Returns:
        None
    """
    for root, dirs, files in os.walk(folder_path):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            files_in_dir = os.listdir(dir_path)
            if len(files_in_dir) == 1:
                file_name = files_in_dir[0]
                file_path = os.path.join(dir_path, file_name)
                shutil.copy(file_path, os.path.join(folder_path, dir + "_" + file_name))

folder_path = r"C:\Git\research_documents\Uvienna\Teaching\350045-1 MSB.V - Methods and Concepts of Biomechanics and Computer Science in Sport\2023W\Quiz1"
copy_files_to_parent_folder(folder_path)