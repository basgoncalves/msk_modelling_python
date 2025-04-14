
import bops as bops
from classes import *

import opensim as osim

__all__ = ["bops"]
    
if __name__ == "__main__":
    bops.greet()
    bops.about()
    
    
    if False:
        data = bops.reader.c3d()
        print(data)
    
    if False:
        data_json = bops.reader.json()
        print(data_json)
    
    if True:
        data_mot = bops.reader.mot()
        print(data_mot)