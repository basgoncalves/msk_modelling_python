import os
import pandas as pd
import numpy as np
from scipy.integrate import trapz
import matplotlib.pyplot as plt


plot_data = 0

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

#------------------
    

# =============================================================================
# def calculate_jump_height(x):
#     
#     # Get the sample rate of the data
#     sample_rate = 1000
#     gravity = 9.81  # m/s^2
#     
#     # Extract vertical GRF and remove baseline
#     vertical_grf = x['Fz'].to_numpy()
#     baseline = np.mean(vertical_grf[:1000])
#     mass = baseline/gravity
#     
#     vgrf_without_baseline = vertical_grf - baseline
#     
#     #find zeros on vGRF
#     idx_zeros = vertical_grf==0
#     flight_time = len(vertical_grf[idx_zeros])/sample_rate
#     
#     # Select time interval of interest
#     plt.plot(vgrf_without_baseline)
#     plt.show()
#     x = plt.ginput(2)
#     plt.close()
#     
#     # Calculate impulse of vertical GRF
#     start_time = min(x[0][0], x[1][0])
#     end_time = max(x[0][0], x[1][0])
#     start_index = int(start_time * sample_rate)
#     end_index = int(end_time * sample_rate)
#     vgrf_of_interest = abs(vgrf_without_baseline[start_index:end_index])
#     impulse = trapz(vgrf_of_interest) / sample_rate
#     
#     launch_velocity = impulse / mass
#     
#     # calculate power
#     average_force = np.mean(vgrf_of_interest) # + baseline 
#     power = average_force * launch_velocity 
#     
#     
#     # Calculate jump height using impulse-momentum relationship
#     jump_height = impulse / (gravity * 2)  # assuming symmetric takeoff and landing
#     
#     return jump_height, flight_time, mass, launch_velocity, power
# 
# =============================================================================



#=============================================================================

    
# Get the sample rate of the data
sample_rate = 1000
gravity = 9.81  # m/s^2
    
vert_grf = np.array(cmj7['Fz-abs'])

# Select time interval of interest
plt.plot(vert_grf)
x = plt.ginput(n=1, show_clicks=True)
plt.close()

baseline = np.mean(vert_grf[:250])
mass = baseline/gravity
vert_grf_without_baseline = vert_grf-baseline

if plot_data:
    plt.plot(vert_grf)
    plt.plot(vert_grf_without_baseline)
    plt.show()

    
#find zeros on vGRF
idx_zeros = vert_grf[vert_grf == 0]
flight_time = len(idx_zeros/sample_rate)
    
# find the end of jump index = first zero in vert_grf
take_off_frame = np.where(vert_grf == 0)[0][0] 
    
# find the start of jump index --> the start value is already in the file
start_of_jump = int(np.round(x[0][0]))

# Calculate impulse of vertical GRF    
vgrf_of_interest = vert_grf_without_baseline[start_of_jump:take_off_frame]

if plot_data:
    plt.plot(vgrf_of_interest)
    plt.show()

#vgrf_of_interest = vgrf_of_interest * sample_rate 
impulse = trapz(vgrf_of_interest) /sample_rate
take_off_velocity = impulse / mass
  
# Calculate jump height using impulse-momentum relationship  
jump_height = 1/2 * (take_off_velocity / gravity)

    
print(jump_height,',' ,flight_time)

if plot_data:
    plt.plot(vgrf_of_interest)
    plt.show()
