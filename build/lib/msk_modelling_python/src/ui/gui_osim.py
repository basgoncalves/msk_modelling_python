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
        save_settings_to_file(new_settings={"trial_folder": path})

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
    print("please continue fixing ...")
    bp.run_inverse_kinematics(osim_modelPath, trc_file_path, resultsDir)
    print("IK run successfully")

def function4():
    print("Function 4")

def save_settings_to_file(settings_json_path=json_file_path(), new_settings=None):
        # Save settings to a JSON file (add each setting to a dictionary)
        old_settings = load_settings_from_file()

        for key in new_settings.keys():
            old_settings[key] = new_settings[key]

        with open(settings_json_path, "w") as file:
            json.dump(old_settings, file, indent=4)

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

    root = tk.Tk()
    root.geometry("500x800")
    root.title("Opensim run single trial")
    
    # Projct path input
    add_label(root, "Folder path")
    trial_box, project_path = add_text_input_box(root, "Enter path of the trial folder", settings["trial"])
    add_button(root, "Select folder of the trial", select_folder, [trial_box])

    # Model path input      
    add_label(root, "Model path")
    osim_model_box, osim_modelPath = add_text_input_box(root, "Enter path of the scaled .osim model", settings["model_scaled"])
    add_button(root, "Select .osim file", select_file, [osim_model_box])

    # IK path input
    add_label(root, "IK path")
    trc_box, trc_path = add_text_input_box(root, "Enter path of the trc file", settings["markers"])
    mot_box, mot_path = add_text_input_box(root, "Enter path of the grf .mot file", settings["grf"])
    grf_xml_box, xml_path = add_text_input_box(root, "Enter path of the grf .xml file", settings["grf_xml"])
    add_button(root, "Select trc file",  select_file, [trc_box])       
    def resultsDir(analyis = 'ik'):
        trial_box_value = trial_box.get()
        if analyis == 'ik':
            return os.path.join(trial_box_value, "ik.mot")
        elif analyis == 'id':
            return os.path.join(trial_box_value, "inverse_dynamics.sto")
        
    def actuators_file_path():
        return os.path.join(trial_box.get(), "actuators_so.xml")
    
    add_button(root, "Run IK", lambda: run_IK(osim_model_box.get(),trc_box.get(),resultsDir()))
    add_button(root, "Run ID", lambda: bp.run_ID(osim_model_box.get(),resultsDir(analyis='ik'), 
                                                 mot_box.get(),grf_xml_box.get(), resultsDir(analyis='id')))
    add_button(root, "Run SO", lambda: bp.run_SO(osim_model_box.get(),trial_box.get(),actuators_file_path()))

    def update_settings():
        save_settings_to_file(new_settings={"model_scaled": osim_model_box.get(), 
                                        "markers": trc_box.get(), 
                                        "trial": trial_box.get()})

    # add close button
    add_button(root, "Save", update_settings)
    add_button(root, "Close", root.quit)
    
    
    root.mainloop()
    

if __name__ == '__main__':
    start_gui()    