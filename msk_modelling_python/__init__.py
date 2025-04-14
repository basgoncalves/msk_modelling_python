try:
    from .osimRun import greet


except:
    from osimRun import greet

import bops
    
if __name__ == "__main__":
    greet()
    bops.about()