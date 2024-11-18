import os
import sys
import shutil
import unittest

try:
    import opensim as osim
except: 
    class osim:
        pass     
    print('=============================================================================================')
    print('could not import opensim')
    print('check if the opensim python package is installed in your python environment')
    pythonPath = os.path.dirname(sys.executable)
    initPath = os.path.join(pythonPath,'lib\site-packages\opensim\__init__.py')
    print('init path is: ', initPath)    
    print('For opensim installation, visit: https://simtk-confluence.stanford.edu/display/OpenSim/Scripting+with+Python')
    print('=============================================================================================\n\n\n\n\n')

import msk_modelling_python as msk

class test(unittest.TestCase):
    
    def test_1(self):
        self.assertTrue(True)
          

if __name__ == "__main__":
    try:
        unittest.main()
        msk.log_error('Tests passed for msk_modelling_python package')
    except Exception as e:
        print("Error: ", e)
        msk.log_error(e)
        msk.bops.Platypus().sad()