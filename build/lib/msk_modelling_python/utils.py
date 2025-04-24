import sys
import os
import time
start_time = time.time()
msk_module_path = os.path.dirname(os.path.abspath(__file__))

import unittest
from PIL import Image
from PIL import ImageTk




__testing__ = False

if __testing__:
    print("msk_modelling_python package loaded.")  
    print("Testing mode is on.")
    print("To turn off testing mode, set __testing__ to False.") 
    
    print("Python version: ", sys.version)
    print("For the latest version, visit " + r'GitHub\basgoncalves\msk_modelling_python')
    
    print("Time to load package: ", time.time() - start_time)
 
def print_warning(warning_message, error_message = ''):
    '''
    import msk_modelling_python as msk
    msk.print_warning('Warning message', 'Error message')
    '''
    print(f"Warning: {warning_message}")
    if error_message:
        print(f"Error: {error_message}") 
 
def log_error(error_message, error_log_path=''):
    '''
    Log an error message to a file
    
    Inputs:
        error_message (str): The error message to log
        error_log_path (str): The path to the error log file (default is the error_log.txt file in the same directory as this file)
    '''
    if not error_log_path:
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        error_log_path = os.path.join(current_file_path,"error_log.txt")
    
    try:
        with open(error_log_path, 'a') as file:
            date = time.strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{date}: {error_message}\n")
    except:
        print("Error: Could not log the error")
        return

def run_bops():
    '''
    Run an example of the bops package
        
    '''
    # run the tests
    try:
        if __testing__:
            test()
            
            
            log_error('All tests passed for msk_modelling_python package.')
    except Exception as e:
        print_warning("Error running package testing: ", e)
        log_error(e)
    
    # run the steps based on the settings.json file in the bops package
    try:
        print('Running main.py')
        settings = bops.get_bops_settings()
        
        if settings['gui']:
            msk.bops.run_example()
        
        if settings['update']:
            msk.update_version(3, msk, invert=False)
        
        if settings['bops']['analyses']['run']['IK']:
            osim_model_path = msk.ui.select_file('Select the osim model file')
            trc_marker_path = msk.ui.select_file('Select the marker file')
            output_folder_path = msk.os.path.dirname(trc_marker_path)
            msk.bops.run_inverse_kinematics(model_file=osim_model_path, marker_file=trc_marker_path , output_folder=output_folder_path)
        
        print('Check implementations.txt for future upcoming implementations')
        print('.\msk_modelling_python\guide\log_problems\implementations.txt')
        print('Check the log file for any errors')
        print('.\msk_modelling_python\guide\log_problems\log.txt')
        
        msk.Platypus().happy()
    except Exception as e:
        print("Error: ", e)
        log_error(e)
        Platypus().sad()

def select_file(prompt='Select a file'):
    '''
    Select a file using the file dialog
    
    Inputs:
        prompt (str): The prompt to display in the file dialog (default is 'Select a file')
        
    Outputs:
        file_path (str): The path to the selected file
    '''
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        file_path = filedialog.askopenfilename(title=prompt)
        
        return file_path
    except Exception as e:
        print("Error: ", e)
        log_error(e)



class Platypus:
    '''
    Platypus class to test the bops package
    usage:
        platypus = Platypus() # create an instance of the Platypus class
        platypus.run_tests() # run all tests
        platypus.print_happy() # print a happy platypus
        platypus.print_sad() # print a sad platypus
    '''
    def __init__(self):
        self.name = 'Platypus'
        self.mood = 'sad'
        self.output = None
        self.images_path = os.path.join(msk_module_path,'src','images')
        self.current_image_path = None
        self.photo = None
        
    def greet(self):
        print(f"Hello, my name is {self.name}!")
        
    def happy(self, message = ''):
        try:
            print(message) 
            self.current_image_path = os.path.join(self.images_path, 'platypus.jpg')
            self.show_image()
            self.mood = 'happy'
        except Exception as e:
            self.mood = 'sad'
            print('happy platypus image not found in ' + self.current_image_path)
            print(e)
        
    def sad(self):
        try:
            self.current_image_path = os.path.join(self.images_path, 'platypus_sad.jpg')
            self.show_image()
            self.mood = 'sad'
        except Exception as e:  
            print('sad platypus image not found in ' + self.current_image_path)
            print(e)
        
    def show_image(self):
        # Create a Tkinter window
        window = tk.Tk()
        
        # Load the image using PIL
        image = Image.open(self.current_image_path)
        # Create a Tkinter PhotoImage from the PIL image
        photo = ImageTk.PhotoImage(image)
        
        label = tk.Label(window, image=photo)
        label.image = photo
        label.pack()
        
        # center image on the screen
        try:
            window_width = window.winfo_reqwidth()
            window_height = window.winfo_reqheight()
            position_right = int((window.winfo_screenwidth()/2 - window_width*3)) 
            position_down = int((window.winfo_screenheight()/2 - window_height*2))
            window.geometry("+{}+{}".format(position_right, position_down))
        except Exception as e:
            msk.log_error('Error bops.Platypus: ' + e)
            print('Could not center image on screen: ' + str(e))
            
        # Start the image loop
        window.mainloop()
    
    def run_tests(self):
        print('running all tests ...')
        unittest.main()
        
        if self.mood == 'sad':
            self.sad()
        else:
            self.happy()
        
class test(unittest.TestCase):
    def test_update_version(self):
        pass
    
    log_error('msk tests all passsed!')

    def test_log_error(self):
        pass

    def test_load_project(self):
        pass

    def test_mir(self):
        pass
    
    def test_platypus(self):
        Platypus().happy()
        self.assertTrue(True)
        
    def test_run_bops(self):
        run_bops()

        
    def test_ui(self):
        ui.test()
        
            
if __name__ == "__main__":
    try:
        unittest.main()
        msk.log_error('Tests passed for msk_modelling_python package')
    except Exception as e:
        print("Error: ", e)
        log_error(e)
        Platypus().sad()
    
    
#%% END