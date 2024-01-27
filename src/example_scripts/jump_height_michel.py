import os
import pandas as pd
import numpy as np
from scipy.integrate import trapz
import matplotlib.pyplot as plt

def calculate_jump_height_impulse(vert_grf,sample_rate):
    
        
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


re_process = 0
#------------------
dir_path = os.path.dirname(os.path.realpath(__file__)) # for .py
folder_path = os.path.join(dir_path,'ExampleData\BMA-force-plate\CSV-Test\p1')

for files in os.listdir(folder_path):
    if files.endswith('.xlsx'):
        files_t = os.path.join(folder_path, files)
        df = pd.read_excel(files_t)
        df_name = os.path.splitext(files)[0]
        globals()[df_name] = df
        
        
jumps = [cmj1, cmj2, cmj3, cmj4, cmj5, cmj6, cmj7]        


for i in jumps: 
    i['Fz-abs'] = i.Fz.abs()

#------------------

results_p1 = pd.DataFrame()
results_p1['jump'] = []
results_p1['kg'] = []
results_p1['flight_time'] = []
results_p1['jump_height'] = []
results_p1['power'] = []
results_p1['velocity'] = []
results_p1['start_frame'] = []
    

    
# Get the sample rate of the data
sample_rate = 1000
gravity = 9.81  # m/s^2
    
vert_grf = np.array(cmj7['Fz-abs'])

calculate_jump_height_impulse(vert_grf,sample_rate)