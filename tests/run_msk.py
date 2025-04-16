
import msk_modelling_python as msk
msk.bops.greet()

CURRENT_DIR = msk.os.path.dirname(msk.os.path.abspath(__file__))
SIMULATION_DIR = r'C:\Git\research_data\Projects\runbops_FAIS_phd\simulations'

SUBJECT = '009'
SESSION = 'pre'
TASK = 'sprint_1'
TASK_FOLDER = msk.os.path.join(SIMULATION_DIR, SUBJECT, SESSION, TASK)

Trial = msk.bops.Trial(TASK_FOLDER)

Trial.write_to_json()

