import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import trapz
from opensim import LoadMotion, CoordinateDirection

# Load the GRF data
data_path = 'Z:\Bas Goncalves\BD2II - Biomechanical Motion Analysis in Practice (2023S)\SJ_example\SJ1\grf.mot'
grf_data = LoadMotion(data_path)

# Get the sample rate of the data
sample_rate = int(1 / grf_data.get_time_step())

# Extract vertical GRF and remove baseline
vertical_grf = grf_data.get_column('vertical_force').to_numpy()
baseline = np.mean(vertical_grf[:100])
vgrf_without_baseline = vertical_grf - baseline

# Select time interval of interest
plt.plot(vgrf_without_baseline)
plt.show()
x = plt.ginput(2)
plt.close()

# Calculate impulse of vertical GRF
start_time = min(x[0][0], x[1][0])
end_time = max(x[0][0], x[1][0])
start_index = int(start_time * sample_rate)
end_index = int(end_time * sample_rate)
vgrf_of_interest = abs(vgrf_without_baseline[start_index:end_index])
impulse = trapz(vgrf_of_interest) / sample_rate

# Calculate jump height using impulse-momentum relationship
gravity = 9.81  # m/s^2
jump_height = impulse / (gravity * 2)  # assuming symmetric takeoff and landing

# Display jump height
print(f"Jump height: {jump_height:.2f} cm")
