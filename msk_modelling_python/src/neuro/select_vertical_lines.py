import numpy as np
from tkinter import simpledialog, messagebox
import matplotlib.pyplot as plt


def select_vertical_line_position(root):
    messagebox.showinfo("Instructions", "Click on three points to place vertical lines.")
    points = []

    def onclick(event):
        points.append(event.xdata)
        if len(points) == 3:
            plt.close()

    fig, ax = plt.subplots()
    ax.plot(np.random.randn(1000))  # Placeholder plot for user to click on
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

    fig.canvas.mpl_disconnect(cid)
    return int(points[0]), int(points[1]), int(points[2])



# # EMG data detrend plot
# emg_data_detrended = np.random.randn(10000)
# section_length = 500

# for i in range(0, len(emg_data_detrended), section_length):
#     data_section = emg_data_detrended[i-50:i+section_length]
    

#     def plot_with_bars(data_section, point1, point2, point3):
#         plt.figure()
#         plt.plot(data_section)
#         plt.axvline(x=point1, color='r', linestyle='--', label='Point 1')
#         plt.axvline(x=point2, color='g', linestyle='--', label='Point 2')
#         plt.axvline(x=point3, color='b', linestyle='--', label='Point 3')
#         plt.legend()
#         plt.show()

#     def get_new_points():
#         points = []

#         def onclick(event):
#             points.append(event.xdata)
#             if len(points) == 3:
#                 plt.close()

#         fig, ax = plt.subplots()
#         ax.plot(data_section)
#         cid = fig.canvas.mpl_connect('button_press_event', onclick)
#         plt.show()

#         fig.canvas.mpl_disconnect(cid)
#         return int(points[0]), int(points[1]), int(points[2])

#     # Initial points
#     point1, point2, point3 = 100, 200, 300

#     while True:
#         plot_with_bars(data_section, point1, point2, point3)
#         answer = messagebox.askquestion("Question", "Are the bars good?")
#         if answer == "yes":
#             break
#         else:
#             point1, point2, point3 = get_new_points()
    
    
    
# END