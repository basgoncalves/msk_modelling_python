import sys  # System imports
import os
import time
START_TIME = time.time()

import unittest
from PIL import Image
from PIL import ImageTk
import tkinter as tk
import numpy as np  # DATA IMPORTS
import pandas as pd
import scipy.signal as sig
import scipy.linalg
import scipy.integrate as integrate
import matplotlib.pyplot as plt     # PLOT IMPORTS
import xml.etree.ElementTree as ET # XML IMPORTS
from xml.dom import minidom
import shutil
import math
import warnings

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))

__testing__ = False

if __testing__:
    print("msk_modelling_python package loaded.")  
    print("Testing mode is on.")
    print("To turn off testing mode, set __testing__ to False.") 
    
    print("Python version: ", sys.version)
    print("For the latest version, visit " + r'GitHub\basgoncalves\msk_modelling_python')
    
    print("Time to load package: ", time.time() - START_TIME)
 
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

#%% #####################################################  XML  ###################################################################
def xml_write(file_path, data, root_name, xmlPref):
    '''
    Write a dictionary to an XML file
    
    Inputs:
        file_path (str): The path to the XML file
        data (dict): The dictionary to write to the XML file
        root_name (str): The name of the root element in the XML file
        xmlPref (dict): The XML preferences for writing the file
    '''
    root = ET.Element(root_name)
    dict_to_xml(data, root)

    tree = ET.ElementTree(root)
    with open(file_path, "wb") as file:
        tree.write(file, encoding="utf-8", xml_declaration=True)
        if "indent" in xmlPref:
            xml_str = ET.tostring(root, encoding="utf-8")
            parsed = minidom.parseString(xml_str)
            pretty_xml = parsed.toprettyxml(indent=xmlPref["indent"])
            file.write(pretty_xml.encode("utf-8"))
    print(f"XML file created with proper indentation: {file_path}")


#%% #####################################################  UI  ###################################################################
def inputList(prompt, options):
    '''
    Display a list of options and prompt the user to select one
    Inputs:
        prompt (str): The prompt to display to the user
        options (list): The list of options to display
        
    Usage:
        options = ['Option 1', 'Option 2', 'Option 3']
        choice = inputList('Select an option:', options)
        print(f"You selected: {options[choice]}")
        
    '''
    print(prompt)
    for i, option in enumerate(options):
        print(f"{i+1}: {option}")
    while True:
        try:
            choice = int(input("Enter the number of the option you want: "))
            if choice < 1 or choice > len(options):
                raise ValueError()
            return choice-1
        except ValueError:
            print("Invalid choice. Please enter a number between 1 and ", len(options))


#%% #####################################################  Operations  ###################################################################
def dict_to_xml(data, parent):
    for key, value in data.items():
        if isinstance(value, dict):
            dict_to_xml(value, ET.SubElement(parent, key))
        else:
            ET.SubElement(parent, key).text = str(value)

def add_each_c3d_to_own_folder(sessionPath):

    c3d_files = [file for file in os.listdir(sessionPath) if file.endswith(".c3d")]
    for file in c3d_files:
        fname = file.replace('.c3d', '')
        src = os.path.join(sessionPath, file)
        dst_folder = os.path.join(sessionPath, fname)

        # create a new folder
        try: os.mkdir(dst_folder)
        except: 'nothing'

        # copy file
        dst = os.path.join(dst_folder, 'c3dfile.c3d')
        shutil.copy(src, dst)

def emg_filter(c3d_dict=0, band_lowcut=30, band_highcut=400, lowcut=6, order=4):
    
    if isinstance(c3d_dict, dict):
        pass
    elif not c3d_dict:   # if no input value is given use example data
        c3dFilePath = get_testing_file_path('c3d')
        c3d_dict = import_c3d_to_dict (c3dFilePath)
    elif os.path.isfile(c3d_dict):
        try:
            c3dFilePath = c3d_dict
            c3d_dict = import_c3d_to_dict (c3d_dict)
        except:
            if not isinstance(c3d_dict, dict):
                raise TypeError('first argument "c3d_dict" should be type dict. Use "get_testing_file_path(''c3d'')" for example file')
            else:
                raise TypeError('"c3d_dict"  has the correct file type but something is wrong with the file and doesnt open')
    
    fs = c3d_dict['OrigAnalogRate']
    if fs < band_highcut * 2:
        band_highcut = fs / 2
        warnings.warn("High pass frequency was too high. Using 1/2 *  sampling frequnecy instead")
    
    analog_df = import_c3d_analog_data(c3d_dict['FilePath'])
    max_emg_list = []
    for col in analog_df.columns:
            max_rolling_average = np.max(pd.Series(analog_df[col]).rolling(200, min_periods=1).mean())
            max_emg_list.append(max_rolling_average)

    nyq = 0.5 * fs
    normal_cutoff  = lowcut / nyq
    b_low, a_low = sig.butter(order, normal_cutoff, btype='low',analog=False)

    low = band_lowcut / nyq
    high = band_highcut / nyq
    b_band, a_band = sig.butter(order, [low, high], btype='band')

    for col in analog_df.columns:
        raw_emg_signal = analog_df[col]
        bandpass_signal = sig.filtfilt(b_band, a_band, raw_emg_signal)
        detrend_signal = sig.detrend(bandpass_signal, type='linear')
        rectified_signal = np.abs(detrend_signal)
        linear_envelope = sig.filtfilt(b_low, a_low, rectified_signal)
        analog_df[col] = linear_envelope

    return analog_df

def filtering_force_plates(file_path='', cutoff_frequency=2, order=2, sampling_rate=1000, body_weight=''):
    if not body_weight:
        body_weight = 1 
    def normalize_bodyweight(data):
                normalized_data = [x  / body_weight for x in data]
                return normalized_data
            
    nyquist_frequency = 0.5 * sampling_rate
    Wn = cutoff_frequency / nyquist_frequency 
    b, a = sig.butter(order, Wn, btype='low', analog=False)
    
    if not file_path:
        file_path = os.path.join(get_dir_bops(), 'ExampleData/BMA-force-plate/CSV-Test/p1/cmj3.csv')
    
    if os.path.isfile(file_path):
        file_extension = os.path.splitext(file_path)[1]
        if file_extension.lower() == ".xlsx":
            data = pd.read_excel(file_path)
            fz=[]
            for i in range(1, data.shape[0]):
                fz.append(float(data.iloc[i,0])) 
            normalized_time = np.arange(len(data) - 1) / (len(data) - 2)
            fz_offset= fz - np.mean(fz)
            filtered_fz = sig.lfilter(b, a, fz_offset)
            plt.plot(normalized_time, normalize_bodyweight(filtered_fz), label='z values')
            plt.xlabel('Time (% of the task)')
            plt.ylabel('Force (% of body weight)')
            plt.legend()
            plt.grid(True)
            plt.title('Graph of force signal vs. time', fontsize=10)
            plt.show()

        elif file_extension.lower() == ".csv":
            data = pd.read_csv(file_path, sep=",",header=3)
            normalized_time = np.arange(len(data) - 1) / (len(data) - 2)
            fx1=[]
            fy1=[]
            fz1=[]
            fx2=[]
            fy2=[]
            fz2=[]
            fx3=[]
            fy3=[]
            fz3=[]
            fx4=[]
            fy4=[]
            fz4=[]
            fx5=[]
            fy5=[]
            fz5=[]
            data.fillna(0, inplace=True)
            for i in range(1, data.shape[0]):
                fx1.append(float(data.iloc[i,11]))  
                fy1.append(float(data.iloc[i,12]))  
                fz1.append(float(data.iloc[i,13]))  
                fx2.append(float(data.iloc[i,2]))  
                fy2.append(float(data.iloc[i,3]))  
                fz2.append(float(data.iloc[i,4]))
                fx3.append(float(data.iloc[i,36]))  
                fy3.append(float(data.iloc[i,37]))  
                fz3.append(float(data.iloc[i,38]))
                fx4.append(float(data.iloc[i,42]))  
                fy4.append(float(data.iloc[i,43]))  
                fz4.append(float(data.iloc[i,44]))
                fx5.append(float(data.iloc[i,48]))  
                fy5.append(float(data.iloc[i,49]))  
                fz5.append(float(data.iloc[i,50]))  


        #OFFSET
            list_fx = [fx1, fx2, fx3, fx4, fx5]
            list_fy = [fy1, fy2, fy3, fy4, fy5]
            list_fz = [fz1, fz2, fz3, fz4, fz5]
            mean_fx = [np.mean(lst) for lst in list_fx]
            mean_fy = [np.mean(lst) for lst in list_fy]
            mean_fz = [np.mean(lst) for lst in list_fz]
            fx_red = [[x - mean for x in lst] for lst, mean in zip(list_fx, mean_fx)]
            fy_red = [[x - mean for x in lst] for lst, mean in zip(list_fy, mean_fy)]
            fz_red = [[x - mean for x in lst] for lst, mean in zip(list_fz, mean_fz)]
            
            filtered_data_listx= []
            for data in fx_red:
                filtered_data_x = sig.lfilter(b, a, data)  
                filtered_data_listx.append(filtered_data_x)
            filtered_data_listy= []
            for data in fy_red:
                filtered_data_y = sig.lfilter(b, a, data)  
                filtered_data_listy.append(filtered_data_y)
            filtered_data_listz= []
            for data in fz_red:
                filtered_data_z = sig.lfilter(b, a, data)  
                filtered_data_listz.append(filtered_data_z)
            
            fig, axes = plt.subplots(3,1)
            axes[0].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listx)), label='x values')
            axes[1].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listy)), label='y values')
            axes[2].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listz)), label='z values')
            axes[0].legend(loc='upper right')
            axes[1].legend(loc='upper right')
            axes[2].legend(loc='upper right')
            plt.xlabel('Time (% of the task)')
            axes[0].set_ylabel('Force (% of \nbody weight)')
            axes[1].set_ylabel('Force (% of \nbody weight)')
            axes[2].set_ylabel('Force (% of \nbody weight)')
            axes[0].set_title('Graph of force signal vs. time', fontsize=10)  
            axes[0].grid(True)
            axes[1].grid(True)
            axes[2].grid(True)
            plt.show()

        else:
            print('file extension does not match any of the bops options for filtering the force plates signal')
    else:
        print('file path does not exist!')

def time_normalise_df(df, fs=''):

    if not type(df) == pd.core.frame.DataFrame:
        raise Exception('Input must be a pandas DataFrame')
    
    if not fs:
        try:
            fs = 1/(df['time'][1]-df['time'][0])
        except  KeyError as e:
            raise Exception('Input DataFrame must contain a column named "time"')
    
    normalised_df = pd.DataFrame(columns=df.columns)

    for column in df.columns:
        normalised_df[column] = np.zeros(101)

        currentData = df[column]
        currentData = currentData[~np.isnan(currentData)]
        
        timeTrial = np.arange(0, len(currentData)/fs, 1/fs)        
        Tnorm = np.arange(0, timeTrial[-1], timeTrial[-1]/101)
        if len(Tnorm) == 102:
            Tnorm = Tnorm[:-1]
        normalised_df[column] = np.interp(Tnorm, timeTrial, currentData)
    
    return normalised_df

def normalise_df(df,value = 1):
    normlaised_df = df.copy()
    for column in normlaised_df.columns:
        if column != 'time':
            normlaised_df[column] = normlaised_df[column] / value

    return normlaised_df

def sum_similar_columns(df):
    # Sum columns with the same name except for one digit
    summed_df = pd.DataFrame()

    for col_name in df.columns:
        # Find the position of the last '_' in the column name
        last_underscore_index = col_name.rfind('_')
        leg = col_name[last_underscore_index + 1]
        muscle_name = col_name[:last_underscore_index-1]

        # Find all columns with similar names (e.g., 'glmax_r')
        similar_columns = [col for col in df.columns if 
                           col == col_name or (col.startswith(muscle_name) and col[-1] == leg)]
    
        summed_df = pd.concat([df[col_name].copy() for col_name in df.columns], axis=1)

        # Check if the muscle name is already in the new DataFrame
        if not muscle_name in summed_df.columns and len(similar_columns) > 1:    
            # Sum the selected columns and add to the new DataFrame
            summed_df[muscle_name] = df[similar_columns].sum(axis=1)
        

    return summed_df

def calculate_integral(df):
    # Calculate the integral over time for all columns
    integral_df = pd.DataFrame({'time': [1]})

    # create this to avoid fragmented df
#     integral_df = pd.DataFrame({
#     column: integrate.trapz(df[column], df['time']) for column in df.columns[1:]
# })

    if not 'time' in df.columns:
        raise Exception('Input DataFrame must contain a column named "time"')

    for column in df.columns[1:]:
        integral_values = integrate.trapz(df[column], df['time'])
        integral_df[column] = integral_values

    integral_df = sum_similar_columns(integral_df)
    return integral_df

def rotateAroundAxes(data, rotations, modelMarkers):

    if len(rotations) != len(rotations[0]*2) + 1:
        raise ValueError("Correct format is order of axes followed by two marker specifying each axis")

    for a, axis in enumerate(rotations[0]):

        markerName1 = rotations[1+a*2]
        markerName2 = rotations[1 + a*2 + 1]
        marker1 = data["Labels"].index(markerName1)
        marker2 = data["Labels"].index(markerName2)
        axisIdx = ord(axis) - ord('x')
        if (0<=axisIdx<=2) == False:
            raise ValueError("Axes can only be x y or z")

        origAxis = [0,0,0]
        origAxis[axisIdx] = 1
        if modelMarkers is not None:
            origAxis = modelMarkers[markerName1] - modelMarkers[markerName2]
            origAxis /= scipy.linalg.norm(origAxis)
        rotateAxis = data["Data"][marker1] - data["Data"][marker2]
        rotateAxis /= scipy.linalg.norm(rotateAxis, axis=1, keepdims=True)

        for i, rotAxis in enumerate(rotateAxis):
            angle = np.arccos(np.clip(np.dot(origAxis, rotAxis), -1.0, 1.0))
            r = Rotation.from_euler('y', -angle)
            data["Data"][:,i] = r.apply(data["Data"][:,i])


    return data

def calculate_jump_height_impulse(vert_grf,sample_rate):
    
    gravity = 9.81
    # Check if the variable is a NumPy array
    if isinstance(vert_grf, np.ndarray):
        print("Variable is a NumPy array")
    else:
        print("Variable is not a NumPy array")
    
    time = np.arange(0, len(vert_grf)/sample_rate, 1/sample_rate)

    # Select time interval of interest
    plt.plot(vert_grf)
    x = plt.ginput(n=1, show_clicks=True)
    plt.close()

    baseline = np.mean(vert_grf[:250])
    mass = baseline/gravity
        
    #find zeros on vGRF
    idx_zeros = vert_grf[vert_grf == 0]
    flight_time_sec = len(idx_zeros/sample_rate)/1000
        
    # find the end of jump index = first zero in vert_grf
    take_off_frame = np.where(vert_grf == 0)[0][0] 
        
    # find the start of jump index --> the start value is already in the file
    start_of_jump_frame = int(np.round(x[0][0]))
    
        # Calculate impulse of vertical GRF    
    vgrf_of_interest = vert_grf[start_of_jump_frame:take_off_frame]

    # Create the time vector
    time = np.arange(0, len(vgrf_of_interest)/sample_rate, 1/sample_rate)

    vertical_impulse_bw = mass * gravity * time[-1]
    vertical_impulse_grf = np.trapz(vgrf_of_interest, time)

    # subtract impulse BW
    vertical_impulse_net = vertical_impulse_grf - vertical_impulse_bw


    take_off_velocity = vertical_impulse_net / mass

    # Calculate jump height using impulse-momentum relationship (DOI: 10.1123/jab.27.3.207)
    jump_height = (take_off_velocity / 2 * gravity)
    jump_height = (take_off_velocity**2 / 2 * 9.81) /100   # devie by 100 to convert to m

    # calculate jump height from flight time
    jump_height_flight = 0.5 * 9.81 * (flight_time_sec / 2)**2   

    print('take off velocity = ' , take_off_velocity, 'm/s')
    print('cmj time = ' , time[-1], ' s')
    print('impulse = ', vertical_impulse_net, 'N.s')
    print('impulse jump height = ', jump_height, ' m')
    print('flight time jump height = ', jump_height_flight, ' m')
    
    return jump_height, vertical_impulse_net

def blandAltman(method1=[],method2=[]):
    # Generate example data
    if not method1:
        method1 = np.array([1.2, 2.4, 3.1, 4.5, 5.2, 6.7, 7.3, 8.1, 9.5, 10.2])
        method2 = np.array([1.1, 2.6, 3.3, 4.4, 5.3, 6.5, 7.4, 8.0, 9.4, 10.4])

    # Calculate the mean difference and the limits of agreement
    mean_diff = np.mean(method1 - method2)
    std_diff = np.std(method1 - method2, ddof=1)
    upper_limit = mean_diff + 1.96 * std_diff
    lower_limit = mean_diff - 1.96 * std_diff

    # Plot the Bland-Altman plot
    plt.scatter((method1 + method2) / 2, method1 - method2)
    plt.axhline(mean_diff, color='gray', linestyle='--')
    plt.axhline(upper_limit, color='gray', linestyle='--')
    plt.axhline(lower_limit, color='gray', linestyle='--')
    plt.xlabel('Mean of two methods')
    plt.ylabel('Difference between two methods')
    plt.title('Bland-Altman plot')
    plt.show()

    # Print the results
    print('Mean difference:', mean_diff)
    print('Standard deviation of difference:', std_diff)
    print('Upper limit of agreement:', upper_limit)
    print('Lower limit of agreement:', lower_limit)

def sum3d_vector(df, columns_to_sum = ['x','y','z'], new_column_name = 'sum'):
    df[new_column_name] = df[columns_to_sum].sum(axis=1)
    return df





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
        self.images_path = os.path.join(MODULE_PATH,'src','images')
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
        log_error('Tests passed for msk_modelling_python package')
    except Exception as e:
        print("Error: ", e)
        log_error(e)
        Platypus().sad()
    
    
#%% END