import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import bops as bp

# Load data
dir_path = os.path.dirname(os.path.realpath(__file__)) # for .py
data_path = os.path.join(dir_path,'..\ExampleData\SJ_example\SJ1','grf.mot')
if not os.path.isfile(data_path):
    print(data_path + ' does not exist as a file path')
GRF, labels = pd.read_excel(data_path)

# # Set the sample rate of the data
# sample_rate = 1000  # Hz

# # Calculate vertical GRF
# vertical_GRF = GRF['f2_3'] + GRF['f3_3']

# # Calculate baseline
# baseline = np.mean(vertical_GRF[0:100])

# # Subtract baseline from vertical GRF
# vGRF_without_baseline = vertical_GRF - baseline

# # Select start
# fig, ax = plt.subplots()
# ax.plot(vGRF_without_baseline)
# plt.show(block=False)

# x = plt.ginput(2)
# plt.close(fig)

# # Calculate the impulse of the vGRF
# vGRF_of_interest = np.abs(vGRF_without_baseline[int(x[0][0]):int(x[1][0])])
# impulse = np.trapz(vGRF_of_interest) / sample_rate

# # Calculate the jump height using the impulse-momentum relationship
# gravity = 9.81  # m/s^2
# jump_height = impulse / (gravity * 2)  # assuming symmetric takeoff and landing

# # Display the jump height
# print(f"Jump height: {jump_height:.2f} cm")
