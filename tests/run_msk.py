
import msk_modelling_python as msk
msk.bops.greet()

CURRENT_DIR = msk.os.path.dirname(msk.os.path.abspath(__file__))
SIMULATION_DIR = msk.os.path.join(CURRENT_DIR, 'simulations')

SIMULATION_DIR = msk.bops.check_folder_path(SIMULATION_DIR)

SUBJECT = '009_simplified'
SESSION = ''
TASK = '10m_sprint'

C3D_PATH = msk.os.path.join(SIMULATION_DIR, SUBJECT, TASK, f'{TASK}.c3d')

C3D_PATH = msk.bops.check_file_path(C3D_PATH)

c3d = msk.bops.reader.c3d(C3D_PATH)
print(c3d)




