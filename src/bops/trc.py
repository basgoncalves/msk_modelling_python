import os
import pandas as pd
import numpy as np
from msk_modelling_python.src import ui

def load_trc(file_path):
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found")
    
    return pd.read_csv(file_path, sep='\t', skiprows=6)



if __name__ == "__main__":
    trc_file_path = "data/athlete_1/static_00.trc"
    if not os.path.exists("data/athlete_1/static_00.trc"):
        ui.show_warning("File not found")
        trc_file_path = ui.select_file("Select a file .trc")
    
    try:
        trc = load_trc(trc_file_path)
    except Exception as e:
        print(e)    
        exit()

    
    print(trc.head())
    print(trc.columns)
    print(trc.shape)    
    