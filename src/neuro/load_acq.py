import argparse
import bioread
import matplotlib.pyplot as plt
import os
import pandas as pd
import numpy as np
from tkinter import filedialog

def load_acq(file_path = ''):
    if not file_path:
        file_path = filedialog.askopenfilename(title='Select acquisition file', filetypes=[('Acquisition files', '*.acq'), ('All files', '*.*')])
        
        if not os.path.exists(file_path):
            print('File not found')
            exit(1)

    data = bioread.read_file(file_path)
    emg_data = data.channels[0].data
    fs = data.samples_per_second

    print('file path: ', file_path)
    print('EMG data:', emg_data)
    print('EMG data type:', type(emg_data))
    print('sampling rate:', fs)

    return file_path, emg_data, fs

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load acquisition data')
    parser.add_argument('--file', type=str, required=True, help='Path to the acquisition file')
    args = parser.parse_args()

    file_path, emg_data, fs = load_acq(args.file)
