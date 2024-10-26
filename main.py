import tkinter as tk
import msk_modelling_python as msk

def run():
  print("Running")
  
  ui = msk.ui.GUI()
  ui.start()


if __name__ == "__main__":
  run()
  
  # msk.update_version(3, msk, invert=False)
  
  
# END
  
