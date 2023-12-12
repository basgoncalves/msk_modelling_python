import tkinter as tk
from tkinter import filedialog, Text
import os 
import unittest
import subprocess

#install_requirements
try:
    subprocess.check_call(['pip', 'install', '-r', 'requirements.txt'])
    print('Requirements installed successfully.')
except subprocess.CalledProcessError:
    print('Failed to install requirements.')


# Get the file names in the src directory
src_dir = 'src'
file_names = os.listdir(src_dir)
# Import all the modules in the src directory
for file_name in file_names:
    if file_name.endswith('.py'):
        module_name = file_name[:-3]  # Remove the .py extension
        module = __import__(f'{src_dir}.{module_name}', fromlist=[module_name])

from src import database_tools




download_dependencies()

def print_design():
    print('designed by Dr Bas')
    print('designed by Dr Bas')

root = tk.Tk()

canvas = tk.Canvas(root, height=700, width=900, bg='#263D54')
canvas.pack()

# Run gui
root.mainloop()

gui()
test()

class test_bops(unittest.TestCase):
    
    ##### TESTS WORKING ######
    def test_print(self):
        print_design()

# Load the            
  
if __name__ == '__main__':
    print_design()