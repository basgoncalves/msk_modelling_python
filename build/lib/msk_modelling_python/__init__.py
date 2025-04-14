try:
    from .osimRun import greet


except:
    from osimRun import greet

import src
import src.tools
    
if __name__ == "__main__":
    greet()
    breakpoint()
    src.tools.bops