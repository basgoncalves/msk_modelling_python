from msk_modelling_python import *
import msk_modelling_python as msk
from msk_modelling_python.ui import Element, GUI

def run(update_version=False):
  print("Running")
  
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
  # run(update_version)
  print(print(sys.executable))
  
  print('next step to fix: make function create_analysis_tool() fpr bops and ceinms_setup')
  
  # Create GUI
  
  
  
  
  
# END
  
