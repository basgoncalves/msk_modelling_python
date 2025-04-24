import subprocess
import os

def run(osim_version='4.5'):
    try:
        # Change directory to the OpenSim Python SDK
        opensim_sdk_path = rf'C:\OpenSim {osim_version}\sdk\Python'
        if not os.path.exists(opensim_sdk_path):
            raise FileNotFoundError(f"Path does not exist: {opensim_sdk_path}")
        
    
        os.chdir(opensim_sdk_path)
        print(f"Changed directory to: {opensim_sdk_path}")

        # Run the setup script for Windows Python 3.8
        print("Running setup script for Windows Python 3.8...")
        setup_script = 'setup_win_python38.py'
        command = opensim_sdk_path + ' python ' + setup_script
        subprocess.run(command, check=True)
        print(f"Executed: python {setup_script}")

        # Install the Python bindings
        print("Installing OpenSim Python bindings...")
        install_command = opensim_sdk_path + ' python -m pip install' + '.'
        subprocess.run(install_command, check=True)
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