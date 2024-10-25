# from setuptools import setup, find_packages
# import tkinter as tk
# import os
# import subprocess
# # from msk_modelling_python.utils.general_utils import select_folder
# from tkinter import simpledialog as sd
# from msk_modelling_python.tests import test
import tkinter as tk
import msk_modelling_python as msk

# root = tk.Tk()
main_dir = msk.ut.select_folder('Please select the main folder for your analysis')

msk.src.mri.method_sangeux_json(main_dir=main_dir, legs=['R', 'L'], subjects=['009'], scale_factors=[1, 1, 1])


exit()

print("Module imported successfully")

folder = test.select_folder()
print(f"Selected folder: {folder}")


exit()

# ut.select_folder('Please select the folder for the virtual environment')


exit()


from msk_modelling_python.utils import general_utils as ut


print("Creating virtual environment")
print("Please select the folder for the virtual environment")

# Function to create an example analysis file
def create_example_analysis_file(path):
    example_content = """# Example Analysis File
# Add your analysis code here

import msk_modelling_python as msk
import venv
import subprocess

main_path = msk.ut.select_folder('Please select the main folder for your analysis')
msk.ut.create_folder('data')

if __name__ == "__main__":
    main()
"""
    with open(os.path.join(path, 'example_analysis.py'), 'w') as file:
        file.write(example_content)

# select virtual environment or create one
def select_or_create_virtualenv(env_path=''):
    if not os.path.exists(env_path):
        env_path = ut.select_folder('Please select the folder for the virtual environment')
    
    
    if not os.path.exists(os.path.join(env_path, 'Scripts', 'python.exe')):
        env_name = sd.askstring('no path', 'test')
        # env_name = ut.input_popup('The path is not an environment. What name do you want to give to the environment?')
        env_path = os.path.join(env_path, env_name)
            
        print(f"Creating virtual environment at {env_path}")
        # venv.create(env_path, with_pip=True)
    else:
        print(f"Using existing virtual environment at {env_path}")

    # Activate the virtual environment
    activate_script = os.path.join(env_path, 'Scripts', 'activate')
    exec(open(activate_script).read(), {'__file__': activate_script})

    # Install required packages
    subprocess.check_call([os.path.join(env_path, 'Scripts', 'pip'), 'install', '-r', 'requirements.txt'])

# Example usage
env_path = input("Enter the path for the virtual environment: ")
select_or_create_virtualenv(env_path)

exit()
# Read the requirements from the requirements.txt file
current_dir = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(current_dir,'requirements.txt')) as f:
    requirements = f.read().splitlines()

# Get the path input by the user
user_input_path = input("Enter the path where the example analysis file should be created: ")

# Create the example analysis file
create_example_analysis_file(user_input_path)

setup(
    name='msk_modelling_python',
    version='0.1.3',
    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,
    description='A package for MSK modelling',
    author='Basilio Goncalves',
    author_email='basilio.goncalves7@gmail.com',
    url='https://github.com/yourusername/msk_modelling_python',
)