import msk_modelling_python as msk

if __name__ == "__main__":
  try:
    print('Running main.py')
    settings = msk.bops.get_bops_settings()
    
    if settings['gui']:
      msk.bops.run_example()
      pass
    
    if settings['update']:
      msk.update_version(3, msk, invert=False)
    
    print('Check implementations.txt for future upcoming implementations')
    print('.\msk_modelling_python\guide\log_problems\implementations.txt')
    print('Check the log file for any errors')
    print('.\msk_modelling_python\guide\log_problems\log.txt')
    
    msk.bops.Platypus().happy()
  
  except Exception as e:
    print("Error: ", e)
    msk.log_error(e)
    msk.bops.Platypus().sad()
  
# # END






