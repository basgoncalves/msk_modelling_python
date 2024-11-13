from msk_modelling_python import *
import msk_modelling_python as msk
from PIL import Image, ImageTk
import customtkinter as ctk


def show_image(image_path):
  # Create a Tkinter window
  window = ctk.CTk()
  # Load the image using PIL
  image_object = Image.open(image_path)
  # Create a Tkinter PhotoImage from the PIL image
  photo = ImageTk.PhotoImage(image_object)
  
  label = ctk.CTkLabel(window, image=photo)
  label.image = photo
  label.pack()

  # Run the Tkinter event loop
  window.mainloop()

if __name__ == "__main__":
  try:
    print('Running main.py')
    settings = msk.bops.get_bops_settings()

    
    
    if settings['gui']:
      msk.bops.run_example()
    
    if settings['update']:
      msk.update_version(3, msk, invert=False)
    
    
    
    
    
    print('Check implementations.txt for future upcoming implementations')
    print('.\msk_modelling_python\guide\log_problems\implementations.txt')
    print('Check the log file for any errors')
    print('.\msk_modelling_python\guide\log_problems\log.txt')
    print('')
    print('fix also: ')
    print('C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\plot\basics.py')
    
    # msk.bops.Platypus().happy()
    file = r'C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\bops\utils\platypus.jpg'
    show_image(file)
  
  except Exception as e:
    # print("Error: ", e)
    # msk.log_error(e)
    
    image_path = r'C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\src\bops\utils\platypus_sad.jpg'
    show_image(image_path)
    # msk.bops.Platypus().sad()
  
  
  
  
  
  
# # END









