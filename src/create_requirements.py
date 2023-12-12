
import os
import pkg_resources

# Get the list of installed packages
installed_packages = [pkg.key for pkg in pkg_resources.working_set]

# Get the list of Python files in the current folder
current_folder = os.path.dirname(os.path.abspath(__file__))
python_files = [file for file in os.listdir(current_folder) if file.endswith('.py')]

# Extract the imported modules from each Python file
imported_modules = set()
for file in python_files:
    with open(os.path.join(current_folder, file), 'r') as f:  
        lines = f.readlines()
        for line in lines:
            if line.startswith('import') or line.startswith('from'):
                module = line.split()[1]
                imported_modules.add(module)

# Filter out the installed packages from the imported modules
required_modules = [module for module in imported_modules if module not in installed_packages]

# Write the required modules to requirements.txt
with open('requirements.txt', 'w') as f:
    for module in required_modules:
        f.write(f"{module}\n")
