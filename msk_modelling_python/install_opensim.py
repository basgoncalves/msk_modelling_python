
import msk_modelling_python as msk
import os

msk.greet()
OSIM_version = 4.5
USER_DIR = os.path.expanduser("~")
BASEDIR_OPENSIM = os.path.join(USER_DIR, "Documents", f'OpenSim{OSIM_version}')

# from the OpenSim installation directory, find the path to the OpenSim library
OPENSIM_LIB_PATH = os.path.join(BASEDIR_OPENSIM, "sdk", "lib")
print(f"OpenSim library path: {OPENSIM_LIB_PATH}")

