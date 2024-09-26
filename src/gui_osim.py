from msk_modelling_python.src import bops as bp
import tkinter as tk
import os
import json
from tkinter import messagebox


#%% functions to add parts to the GUI
def add_label(root, text):
    label = tk.Label(root, text=text)
    label.pack()

def add_text_input_box(root, label_text, entry_text=None):
    add_label(root, label_text)
    var = tk.StringVar()
    entry = tk.Entry(root, textvariable=var)
    entry.pack()
    if entry_text:
        var.set(entry_text)

    return entry, var

def add_button(root, text, command, inputs=None , pady=10):
    if inputs is None:
        button = tk.Button(root, text=text, command=command)
    else:
        button = tk.Button(root, text=text, command=lambda: command(*inputs))
        if command is run_IK:
            import pdb; pdb.set_trace()
    button.pack(pady=pady)

def json_file_path():
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_file_path,"current_analysis.json")

#%% functions to be executed when the buttons are clicked
def select_file(Entry):
    path = bp.select_file()
    Entry.delete(0, tk.END)
    Entry.insert(0, path)

def select_folder(Entry, settings: dict =None):
    path = bp.select_folder()
    Entry.delete(0, tk.END)
    Entry.insert(0, path)
    if settings:
        save_settings_to_file(settings={"trial_folder": path})

def run_IK(osim_modelPath='test', trc_file_path='test', resultsDir='test'):
    # bp.run_IK(osim_modelPath, trc_file_path, resultsDir)
    if not os.path.isfile(osim_modelPath) or not osim_modelPath.endswith('.osim'):
        print("Error: Invalid .osim model path" + osim_modelPath)
        return
    
    if not os.path.isfile(trc_file_path) or not trc_file_path.endswith('.trc'):
        print("Error: Invalid .trc file path" + trc_file_path)
        return
    
    if not os.path.isdir(os.path.dirname(resultsDir)):
        print("Error: Invalid results directory path" + resultsDir)
        return

    print('Running IK ...')
    print("model at path: ", osim_modelPath)
    print("trc file at path: ", trc_file_path)
    print("Results will be saved at: ", resultsDir)
    print(" ")
    bp.run_IK(osim_modelPath, trc_file_path, resultsDir)
    print("IK run successfully")

def function4():
    print("Function 4")

def save_settings_to_file(settings_json_path=json_file_path(), settings=None):
        # Save settings to a JSON file (add each setting to a dictionary)
        if not settings:
            settings = load_settings_from_file()

        settings_json_text = {}
        for key in settings.keys():
            settings_json_text[key] = settings[key]

        
        with open(settings_json_path, "w") as file:
            json.dump(settings_json_text, file, indent=4)

        messagebox.showinfo("Settings Saved", "Settings have been saved to settings.json")

def load_settings_from_file(settings_json_path=json_file_path()):
        try:
            with open(settings_json_path, "r") as file:
                settings = json.load(file)
                return settings
        except FileNotFoundError:
            return None



#%% Start the GUI
def start_gui():

    settings = load_settings_from_file()

    root = bp.tk.Tk()
    root.geometry("400x600")
    root.title("Opensim run single trial")
    
    # Projct path input
    add_label(root, "Folder path")
    trial_box, project_path = add_text_input_box(root, "Enter path of the trial folder")
    add_button(root, "Select folder of the trial", select_folder, [trial_box])

    # Model path input      
    add_label(root, "Model path")
    osim_model_box, osim_modelPath = add_text_input_box(root, "Enter path of the scaled .osim model")
    add_button(root, "Select .osim file", select_file, [osim_model_box])

    # IK path input
    add_label(root, "IK path")
    trc_box, trc_path = add_text_input_box(root, "Enter path of the trc file")
    add_button(root, "Select trc file",  select_file, [trc_box])       
    def resultsDir():
        trial_box_value = trial_box.get()
        return os.path.join(trial_box_value, "ik.mot")
    
    add_button(root, "Run IK", lambda: run_IK(osim_model_box.get(),trc_box.get(),resultsDir()))
    # add_button(root, "Run IK", update_and_run_IK)

    # add close button
    add_button(root, "Close", root.quit)
    
    
    root.mainloop()
    

if __name__ == '__main__':
    start_gui()    