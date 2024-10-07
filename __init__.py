

__version__ = '0.1.2'

from . import src
from .utils import general_utils as ut
import importlib
from. import ui
import pyperclip

class utils:
    def __init__(self):
        pass
   
    def is_intalled(package_name):
        import importlib.util
        return importlib.util.find_spec(package_name) is not None

    def import_lib(package_name):
        if is_intalled(package_name):
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
        
        importlib.import_module(package_name)

class mcf: # make coding fancy
    
    def __init__(self):
        pass
    
    header = staticmethod(lambda: pyperclip.copy("#%% ##################################### header \n " +
                                                 " # Description: \n " +
                                                 "######################################################"))


def update_version(level=3):
    global __version__
    version_parts = list(map(int, __version__.split('.')))
    version_parts[level - 1] += 1
    for i in range(level, len(version_parts)):
        version_parts[i] = 0
    __version__ = '.'.join(map(str, version_parts))

    with open(__file__, 'r') as file:
        lines = file.readlines()

    with open(__file__, 'w') as file:
        for line in lines:
            if line.startswith('__version__'):
                file.write(f"__version__ = '{__version__}'\n")
            else:
                file.write(line)
    
    print(f'Updated version to {__version__}')
    
def load_project(project_path=''):
    if not project_path:
        project_path = src.bp.select_folder("Select project folder")
    
    print(src.bp.get_project_settings(project_path))
    
    
    return project_path


update_version = ut.Option(update_version)

# END