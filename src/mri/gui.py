import tkinter as tk
import os
from coverage_test import calculate_coverage_batch, show_loading_bar, calculate_normal_vector
def coverage_test(maindir, legs, thresholds, subjects_to_run):
    calculate_coverage_batch(maindir, legs, thresholds, subjects_to_run)

def function1():
    # Function to be executed when the "Function 1" button is clicked
    # Add your code here
    pass

def function2():
    # Function to be executed when the "Function 2" button is clicked
    # Add your code here
    pass

def function3():
    # Function to be executed when the "Function 3" button is clicked
    # Add your code here
    pass

def function4():
    # Function to be executed when the "Function 4" button is clicked
    # Add your code here
    pass

def add_label(root, text):
    label = tk.Label(root, text=text)
    label.pack()

def create_gui():
    root = tk.Tk()
    # Set the size of the window to 400x600 pixels
    root.geometry("400x600")

    # Get the screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calculate the x and y coordinates to center the window
    x = (screen_width - 400) // 2
    y = (screen_height - 600) // 2

    # Set the position of the window to the center of the screen
    root.geometry(f"+{x}+{y}")

    # Create buttons
    button1 = tk.Button(root, text="Coverage Test", command=coverage_test)
    button1.pack()

    button2 = tk.Button(root, text="Function 1", command=function1)
    button2.pack()

    button3 = tk.Button(root, text="Function 2", command=function2)
    button3.pack()

    button4 = tk.Button(root, text="Function 3", command=function3)
    button4.pack()

    button5 = tk.Button(root, text="Function 4", command=function4)
    button5.pack()
    # Create text box for file path
    add_label(root, "Enter file path:")
    file_path_entry = tk.Entry(root)
    file_path_entry.pack()

    # Create dropdown menu for options
    add_label(root, "Select legs to analyse:")
    options = ['r', 'l', 'both']
    selected_leg = tk.StringVar()
    dropdown_menu = tk.OptionMenu(root, selected_leg, *options)
    dropdown_menu.pack()
    legs = selected_leg.get()

    # Create text box for string input
    add_label(root, "Enter file path:")
    string_entry = tk.Entry(root)
    string_entry.pack()

    # Create text box for number input
    number_entry = tk.Entry(root)
    number_entry.pack()

    root.mainloop()

if __name__ == "__main__":
    create_gui()