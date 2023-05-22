from bops import *

c3dFilePath = get_testing_file_path('c3d')
title_name = os.path.basename(c3dFilePath).split(".")[0]
c3d_dict = import_c3d_data (c3dFilePath)

print( c3d_dict['analog_rate'])

# emg_filtered = emg_filter(c3dFilePath)

# # Create a emg plot
# fig, ax = plt.subplots()  # Create a figure containing a single axes.
# ax.plot(emg_filtered)  # Plot some data on the axes.
# plt.title(title_name)
# plt.xlabel("Time")
# plt.ylabel("Volt")
# plt.show()