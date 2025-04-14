try:
    import bops as bops
    from classes import *
    from src import *
    from utils import *
    
except:
    from . import bops as bops
    from .classes import *
    from .utils import *
    
if __name__ == "__main__":
    bops.greet()
    bops.about()
    
    
    if False:
        data = bops.reader.c3d()
        print(data)
    
    if False:
        data_json = bops.reader.json()
        print(data_json)
    
    if False:
        data_mot = bops.reader.mot()
        print(data_mot)