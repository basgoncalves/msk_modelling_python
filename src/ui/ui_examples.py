import os
import tkinter as tk
import customtkinter as ctk
import screeninfo as si
import unittest

# Examples of UI functions that can be used in the msk_modelling_python package
# These functions can be used to create a UI for the user to interact with the package

def print_colour(message, colour='black'):
    if colour == 'black':
        print(f"\033[30m{message}\033[0m")
    elif colour == 'red':
        print(f"\033[31m{message}\033[0m")
    elif colour == 'green':
        print(f"\033[32m{message}\033[0m")
    elif colour == 'yellow':
        print(f"\033[33m{message}\033[0m")
    elif colour == 'blue':
        print(f"\033[34m{message}\033[0m")

def get_ui_settings(settings_type = 'Default'):
    
    if settings_type == 'Default':
        settings = {
            "bg_color": "white",
            "fg_color": "black",
            "font": ("Arial", 12),
        }
    elif settings_type == 'Dark':
        settings = {
            "bg_color": "black",
            "fg_color": "white",
            "font": ("Arial", 12)
        }
    
    return settings

def show_warning(message, settings_type = 'Default'):  
    root = ctk.CTk()
    root.title("Warning")
        
    screen = si.get_monitors()[0]
    width = 300
    height = 150
    x = (screen.width - width) // 2
    y = (screen.height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    label = ctk.CTkLabel(root, text=message, wraplength=280)
    label.pack(pady=20)
    
    button = ctk.CTkButton(root, text="OK", command=root.quit)
    button.pack(pady=10)
    
    root.mainloop()

def select_folder(prompt='Please select your folder', staring_path=''):    
    try:
        selected_folder = ctk.filedialog.askdirectory(initialdir=staring_path, title=prompt)
    except Exception as e:
        print_colour("Error: Could not select the folder", 'yellow')
        print(e)
        return None
    
    return selected_folder

def select_file(prompt='Please select your file', staring_path=''):
    file_path = ctk.filedialog.askopenfilename(title="Select a file")
    
    if not file_path: raise ValueError('No file selected')

    return file_path

def select_folder_multiple (prompt='Please select multiple folders', staring_path=''):
    root = ctk.CTk()
    folder_list = ctk.filedialog.askdirectory(title=prompt, mustexist=True)
    return folder_list

def create_folder(folder_path = ''):
    if not folder_path:
        folder_path = select_folder()
        show_warning(f"Creaing folder at {folder_path}")
           
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        print(f"Folder {folder_path} already exists.")
    
    return folder_path

def create_subfolders(main_dir, subfolder_name):
    for folder in os.listdir(main_dir):
        
        folder_path = os.path.join(main_dir, folder)
        
        if not os.path.isdir(folder_path):
            continue
        else:
            sub_folder_path = os.path.join(folder_path, subfolder_name)
            print(sub_folder_path)
            create_folder(sub_folder_path)


# BOPS specific functions



# TESTS
class test_default_ui_examples(unittest.TestCase):
    
    ##### TESTS WORKING ######
    def test_show_warning(self):
        show_warning("This is a warning message")
        self.assertTrue(True)
        
    def test_select_multiple_folders(self):
        folder_list = select_folder_multiple()
        self.assertTrue(True)

if __name__ == '__main__':
    # Run the tests
    unittest.main()
   

# END