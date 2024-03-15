import os
import sys

# Calculate the path to module1 directory
module1_path = r'C:\Users\Bas\Desktop\module1'

# Add module1 directory to sys.path
sys.path.insert(0, module1_path)

if not os.path.isdir(module1_path):
    raise Exception('module1 directory does not exist')
else:
    print('module added:', module1_path)

