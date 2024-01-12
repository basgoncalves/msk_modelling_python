import tkinter as tk
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

# Scaling factor to adjust the size of the stick man and window
def draw_stick_man(canvas, scale, arm_angle):
    # Clear the canvas
    canvas.delete("all")
    
    # Calculate head position and size (centered)
    head_size = 100 * scale
    head_x = (canvas.winfo_reqwidth() - head_size) / 2
    head_y = 50
    canvas.create_oval(head_x, head_y, head_x + head_size, head_y + head_size, fill="black")

    # Calculate body position and size (centered)
    body_x = head_x + head_size / 2 - 10 * scale
    body_y = head_y + head_size
    body_width = 20 * scale
    body_height = 100 * scale
    canvas.create_rectangle(body_x, body_y, body_x + body_width, body_y + body_height, fill="black")

    # Arms (centered on body)
    arm_length = 50 * scale
    arm_x = body_x + body_width / 2
    arm_y = body_y + 20 * scale
    elbow_x = arm_x - arm_length * arm_angle
    elbow_y = arm_y + 70 * scale
    canvas.create_line(arm_x, arm_y, elbow_x, elbow_y, fill="black")
    canvas.create_line(elbow_x, elbow_y, arm_x + arm_length * arm_angle, arm_y + 70 * scale, fill="black")

    # Legs (centered on body)
    leg_length = 50 * scale
    leg_x = body_x + body_width / 2
    leg_y = body_y + body_height
    knee_x = leg_x - leg_length
    knee_y = leg_y + 50 * scale
    canvas.create_line(leg_x, leg_y, knee_x, knee_y, fill="black")
    canvas.create_line(knee_x, knee_y, leg_x + leg_length, leg_y + 50 * scale, fill="black")

# Change this value to scale the window and stick man
def create_stick_man_window(scaling_factor = 1.5):
    
    # Function to update the stick man's arms based on the slider value
    def update_arms(value):
        arm_angle = float(value)
        draw_stick_man(canvas, window_scale, arm_angle)
        
    # Create the main window
    root = tk.Tk()
    root.title("Stick Man")

    # Create a slider to control the arm movement
    arm_slider = tk.Scale(root, from_=0.0, to=1.0, resolution=0.01, orient="horizontal", label="Arm Movement")
    arm_slider.pack()

    # Calculate screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Set the scaling factor
    window_scale = scaling_factor  # Set the desired scaling factor

    # Calculate window width and height
    window_width = int(300 * window_scale)
    window_height = int(400 * window_scale)

    # Set the window size and position to center it
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Create a canvas to draw the stick man
    canvas = tk.Canvas(root, width=window_width, height=window_height)
    canvas.pack()

    # Draw the stick man initially
    draw_stick_man(canvas, window_scale, 0.5)  # Initial arm position

    # Bind the slider to update the arms
    arm_slider.bind("<Motion>", lambda event: update_arms(arm_slider.get()))

    # Start the main loop
    root.mainloop()

#%% Create GUI with a few buttons
import tkinter as tk
from tkinter import filedialog
def start_GUI():
    def test():
        print("Hello World!")

    def test2():
        print("Hello Hell!")

    def create_window(title, geometry='500x500'):
        
        window = tk.Tk()

        # Set the window title
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Calculate the window width and height
        window_width = screen_width // 2
        window_height = screen_height // 2

        # Calculate the x and y coordinates for centering the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        # Set the window size and position
        window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        return window

    def add_button(window, text, command, padx=5, pady=5, x=0, y=0):
        button = tk.Button(window, text=text, command=command)
        button.pack(padx=padx, pady=pady)
        button.place(x=x, y=y)

    def select_folder():
        root = tk.Tk()
        root.withdraw()

        folder_path = filedialog.askdirectory()
        print("Selected folder:", folder_path)

    window = create_window("Test")
    add_button(window, "select folder", select_folder, padx=5, pady=5, x=0, y=0)

    # Start the GUI event loop
    try:
        window.mainloop()
    except KeyboardInterrupt:
        window.destroy()


#%% if main 
if __name__ == '__main__':
    start_GUI()
    create_stick_man_window()