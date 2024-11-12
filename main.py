from msk_modelling_python import *
import msk_modelling_python as msk

# print('Running main.py')


if __name__ == "__main__":
  
  print('Running main.py')
  settings = msk.bops.get_bops_settings()

  
  
  if settings['gui']:
    msk.bops.batch_run_example()
  
  if settings['update']:
    msk.update_version(3, msk, invert=False)
  
  
  
  
  
  # Implement in the future
  print('next step to fix: SO and ID gui and batch')
  msk.bops.print_terminal_spaced('fix also: ')
  print('C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\plot\basics.py')
  
  # Create GUI
  
  
  
  
  
# END
  
