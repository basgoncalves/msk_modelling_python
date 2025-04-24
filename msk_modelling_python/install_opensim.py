import subprocess
import os
import sys

def run(osim_version='4.5'):
    try:
        # Change directory to the OpenSim Python SDK
        opensim_sdk_path = rf'C:\OpenSim {osim_version}\sdk\Python'
        if not os.path.exists(opensim_sdk_path):
            raise FileNotFoundError(f"Path does not exist: {opensim_sdk_path}")


        os.chdir(opensim_sdk_path)
        print(f"Changed directory to: {opensim_sdk_path}")

        # Print the current working directory
        print(f"Current working directory: {os.getcwd()}")

        # Run the setup script for Windows Python 3.8
        print("Running setup script for Windows Python 3.8...")
        setup_script = 'setup_win_python38.py'
        
        command_list = [sys.executable, setup_script]
        print(f"Executing:")
        print(f"{' '.join(command_list)}") # Print the command as it would look in the shell
        
        subprocess.run(command_list, check=True, cwd=opensim_sdk_path) # Use list and specify cwd explicitly
        print(f"Executed: python {setup_script}")

        # Install the Python bindings
        print("Installing OpenSim Python bindings...")
        install_command_list = [sys.executable, '-m', 'pip', 'install', '.']
        print(f"Executing:")
        print(f"{' '.join(install_command_list)}") # Print the command
        subprocess.run(install_command_list, check=True, cwd=opensim_sdk_path) # Use list and specify cwd explicitly
        print("Executed: python -m pip install .")

        print("OpenSim Python bindings installation process completed successfully.")

    except subprocess.CalledProcessError as e:
        print(f"Error during execution: {e}")
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}")
    except OSError as e:
        print(f"Error changing directory: {e}")

if __name__ == "__main__":
    run()