from msk_modelling_python import *
import msk_modelling_python as msk
from PIL import Image, ImageTk
import customtkinter as ctk


def create_ui_with_3_buttons():
  # Create a Tkinter window
  window = ctk.CTk()
  
  window.title("Platypus")
  
  # Create a Tkinter button
  button = ctk.CTkButton(window, text="Click me!")
  button.pack()
  
  # Create a Tkinter button
  button2 = ctk.CTkButton(window, text="Click me too!")
  button2.pack()
  
  # Create a Tkinter button
  button3 = ctk.CTkButton(window, text="quit", command=window.destroy)
  button3.pack()
  
  # Run the Tkinter event loop
  window.mainloop()

if __name__ == "__main__":
  try:
    print('Running main.py')
    settings = msk.bops.get_bops_settings()
    
    if settings['gui']:
      msk.bops.run_example()
      # create_ui_with_3_buttons()
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

    

# if __name__ == "__main__":
#   settings = msk.bops.get_bops_settings()
#   e = 'test'
#   msk.log_error(e)
#   image_path = r'C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\bops\utils\platypus_sad.jpg'
#   show_image(image_path)
      









