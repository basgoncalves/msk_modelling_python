import os

def create_folder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)

def create_file(path):
    with open(path, 'w') as f:
        pass


if __name__ == "__main__":
    # Define the name of the directory to be created
    base_dir = input("Enter the name of the directory to be created: ")

    if not os.path.exists(os.path.dirname(base_dir)):
        print(f"Error: {base_dir} does not exists")
        exit()
    
    elif base_dir == '.':        
        module_name = input("Enter the name of the module: ")
        base_dir = os.getcwd() + '/' + module_name
        if os.path.exists(base_dir):
            print(f"Error: {base_dir} already exists")
            exit()

        print(f"Creating directory ... \n {base_dir}")

    else:
        print(f"Creating directory ... \n {base_dir}")

    # Create directories
    try:
        create_folder(f'{base_dir}')
        create_folder(f'{base_dir}/tests')
        create_folder(f'{base_dir}/docs')
    except Exception as e:
        print ('Error: Creating directory. ' +  base_dir)
        print(e)
        exit()  


    # Create files
    try:    
        create_file(f'{base_dir}/__init__.py')
        create_file(f'{base_dir}/module.py')
        create_file(f'{base_dir}/utils.py')
        create_file(f'{base_dir}/tests/__init__.py')
        create_file(f'{base_dir}/tests/test_module.py')
        create_file(f'{base_dir}/docs/index.md')
        create_file(f'{base_dir}/docs/module.md')
        create_file(f'{base_dir}/.gitignore')
        create_file(f'{base_dir}/setup.py')
        create_file(f'{base_dir}/README.md')
    except Exception as e:
        print ('Error: Creating file. ' +  base_dir)
        print(e)
        exit()


# END