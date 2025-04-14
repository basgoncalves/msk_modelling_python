import tkinter as tk
import os
import json
from tkinter import messagebox
from msk_modelling_python.src.mri.coverage import calculate_coverage_batch, show_loading_bar, calculate_normal_vector
import msk_modelling_python.tests.test_print_xlsx as print_xlsx


def coverage_test(maindir, legs, thresholds, subjects_to_run):
    calculate_coverage_batch(maindir, legs, thresholds, subjects_to_run)

def save_settings_to_file(settings_json_path, settings, acetabular_coverage, path_xlsx, sheet_name):
        # Save settings to a JSON file (add each setting to a dictionary)
        settings_json_text = {}
        for key in settings.keys():
            import pdb
            pdb.set_trace()
            settings_json_text[key] = settings[key]
            # settings_json_text = {
            #     "acetabular_coverage": acetabular_coverage.get(),
            #     "path_xlsx": path_xlsx.get(),
            #     "sheet_name": sheet_name.get()
            # }
        
        with open(settings_json_path, "w") as file:
            json.dump(settings_json_text, file, indent=4)

        messagebox.showinfo("Settings Saved", "Settings have been saved to settings.json")

def load_settings_from_file(settings_json_path):
        try:
            with open(settings_json_path, "r") as file:
                settings = json.load(file)
                return settings
        except FileNotFoundError:
            return None

def create_button(root, text, command):
    button = tk.Button(root, text=text, command=command)
    button.pack(pady=20)

def add_coverage_to_xlsx():
    current_file_path = os.path.dirname(os.path.abspath(__file__))  
    settings_json_path = os.path.join(current_file_path,"settings.json")
        
    def on_button_click_coverage_run():
        print_xlsx.add_coverages_to_xlsx(acetabular_coverage.get(),  path_xlsx.get(), sheet_name.get())
        save_settings_to_file(settings_json_path, settings, acetabular_coverage, path_xlsx, sheet_name)
        root.destroy()  # Close the window

    def create_label_entry(root, text, previous_value=None):
        label = tk.Label(root, text=text)
        label.pack(pady=5)
        entry = tk.Entry(root, width=60)
        entry.pack(pady=5)
        entry.insert(0, previous_value)
        return entry

    # Create the main window
    root = tk.Tk()
    root.title("Simple GUI")
    root.geometry("400x300")  # Set the window size to 400x300

    if load_settings_from_file(settings_json_path) == None:
        acetabular_coverage = create_label_entry(root, "Enter acetabular_coverage path:")
        path_xlsx = create_label_entry(root, "Enter path for xlsx file:")
        sheet_name = create_label_entry(root, "Enter sheet name:")
    else:
        settings = load_settings_from_file(settings_json_path)
        acetabular_coverage = create_label_entry(root, "Enter acetabular_coverage path:", settings["acetabular_coverage"])
        path_xlsx = create_label_entry(root, "Enter path for xlsx file:", settings["path_xlsx"])
        sheet_name = create_label_entry(root, "Enter sheet name:", settings["sheet_name"])

    create_button(root, "Run Function", on_button_click_coverage_run)

    # Run the application
    root.mainloop()
    
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

def add_text_input_box(root, text):
    add_label(root, text)
    var = tk.StringVar()
    entry = tk.Entry(root)
    entry.pack()
    return var

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

    # Button for acetabular coverage
    button2 = tk.Button(root, text="Add coverages to xlsx", command=add_coverage_to_xlsx)
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