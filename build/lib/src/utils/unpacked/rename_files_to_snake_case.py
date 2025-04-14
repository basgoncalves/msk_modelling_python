import os
from tkinter import filedialog
import tkinter as tk
import re

# Function to find unique file types in a folder
def find_file_types(folder_path):
    file_types = set()
    for root, dirs, files in os.walk(folder_path):
        # Remove hidden items from dirs
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            _, file_ext = os.path.splitext(file)
            if not file_ext:
                continue
            file_types.add(file_ext)
    return file_types

# Function to update renaming options based on file types in a folder
def update_renaming_options(folder_path, renaming_options):
    if not folder_path:
        return renaming_options

    file_types = find_file_types(folder_path)
    for file_type in file_types:
        if file_type not in renaming_options.values():
            new_key = "_" + file_type.replace(".", "")
            renaming_options[new_key] = file_type
    return renaming_options

# Function to convert camel case to snake case for the last name in the path
def convert_camel_case_to_snake_case(old_path,renaming_options):
    # Extract the last component of the path
    head, tail = os.path.split(old_path)
    
    # Use a regular expression to find occurrences of lowercase followed by uppercase
    pattern = re.compile(r'([a-z])([A-Z])')
    
    # Replace occurrences with lowercase followed by underscore and lowercase
    converted_tail = re.sub(pattern, r'\1_\2', tail)
    
    # Convert the entire string to lowercase
    converted_tail = converted_tail.lower()
    
    # Join the modified tail with the head to get the full path
    new_path = os.path.join(head, converted_tail)
    
    # Replace the old file extension with the new file extension
    # Construct a regular expression pattern for matching each old substring at the end
    pattern = re.compile('|'.join(re.escape(old) + '$' for old in renaming_options.keys()))
        
    # Replace occurrences of old substrings at the end with the corresponding new values
    new_path = pattern.sub(lambda match: renaming_options[match.group(0)], new_path)

    # If the new name already exists and is the same as old, don't rename 
    if os.path.exists(new_path) and old_path == new_path: 
        return

    os.rename(old_path, new_path)
    
# Function to rename files and folders
def rename_files_and_folders(renaming_options=dict()):
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    
    renaming_options = update_renaming_options(folder_path, renaming_options)
    
    if folder_path:
        for root, dirs, files in os.walk(folder_path):
            
            dirs[:] = [d for d in dirs if not d.startswith('.')] # Remove hidden items from dirs
            files = [f for f in files if not f.startswith('.')] # Remove hidden items from files
            
            dirs[:] = [d for d in dirs if not d.startswith('__')] # Remove items starting with '__' from dirs
            files = [f for f in files if not f.startswith('__')] # Remove items starting with '__' from files
                            
            for dir in dirs:
                old_path = os.path.join(root, dir)
                convert_camel_case_to_snake_case(old_path,renaming_options)
                if dir == 'Presentation':
                    a=2
                
            for file in files:
                old_path = os.path.join(root, file)
                convert_camel_case_to_snake_case(old_path,renaming_options)

if __name__ == "__main__":
    # Function to rename files and folders
    rename_files_and_folders()


# END

