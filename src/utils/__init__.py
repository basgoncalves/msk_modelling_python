from .general_utils import *
import tkinter as tk
from tkinter import filedialog
import json
import os
import customtkinter as ctk

def security_check(filepath, identifier=None):
    '''
    Check if the file is a BOPS settings file
    '''
    
    with open(os.path.join(path,filepath), 'r') as f:
        
        first_line = f.readline()
        second_line = f.readline() # for json files
        if not second_line.__contains__(identifier): # check if the file line is the identifier
            print('settings.json file is not a BOPS settings file')
            return False
        else:
            return True
        


def print_json(filepath=None):
    '''Print the contents of a json file'''
    
    if not filepath:
        root = ctk.CTk()
        filepath = ctk.filedialog.askopenfilename(title="Select .json file", filetypes=(("json files", "*.json"), ("all files", "*.*")))
    
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    print(data)
    
    # close dialog box
    root.withdraw()
    root.destroy()
    
    return data


# End