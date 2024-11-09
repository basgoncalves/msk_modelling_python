from msk_modelling_python import *
import msk_modelling_python as msk
from msk_modelling_python.ui import Element, GUI
from msk_modelling_python.src.bops import *

def run(update_version=False):
  print("Running main code from msk_modelling_python")
  
  # implement gui functions
  gui = msk.ui.run_example()
  
  # implement version update if needed
  if update_version:
    msk.update_version(3, msk, invert=False)
    print(f"New version: {msk.__version__}")
  else:
    print(f"Current version: {msk.__version__}")


if __name__ == "__main__":
  
  update_version =  False
  run(update_version)
  # ui.batch_run_example()
  
  
  # Implement in the future
  print('next step to fix: SO and ID gui and batch')
  print('files to fix:')
  print('C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\plot\basics.py')
  
  # Create GUI
  
  
  
  
  
# END
  
