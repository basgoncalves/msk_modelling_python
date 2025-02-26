'''
This is an example file on how to run an analysis using the msk_modelling_python module.
Change settings on the .\settings.json file to change the behaviour of the module.

'''
import msk_modelling_python as msk

if __name__ == "__main__":
  try:
    msk.run_bops()
    msk.log_error('main.py completed without errors')
    
  except Exception as e:
    print("Error: ", e)
    msk.log_error(e)
    msk.bops.Platypus().sad()
    
# # END






