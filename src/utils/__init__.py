from .general_utils import *


def security_check(filepath, identifier=None):
    '''
    Check if the file is a BOPS settings file
    '''
    
    with open(os.path.join(path,filepath), 'r') as f:
        
        first_line = f.readline()
        second_line = f.readline() # for json files
        if not second_line.__contains__(identifier): # check if the file line is the identifier
            print('settings.json file is not a BOPS settings file')
            return False
        else:
            return True