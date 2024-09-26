__version__ = '0.1.1'

from . import src
from . import utils

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