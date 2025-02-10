# import msk_modelling_python as msk
# from msk_modelling_python.src import mri

import pandas as pd
import os
import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as plt

def read_csv_with_tables(file_path):
    """
    Reads a CSV file with tables separated by a single empty row and returns a list of DataFrames.

    Args:
        file_path: Path to the CSV file.

    Returns:
        A list of DataFrames, where each DataFrame represents one table in the CSV file.
    """

    with open(file_path, 'r') as f:
        lines = f.readlines()

    tables = []
    current_table = []

    for line in lines:
        if line.strip() == '':  # Check for empty line
            if current_table:  # If there are lines in the current table
                table_df = pd.DataFrame([row.split(',') for row in current_table])
                tables.append(table_df)
                current_table = []
        else:
            current_table.append(line.strip())

    if current_table:  # Handle the last table if it doesn't end with an empty line
        table_df = pd.DataFrame([row.split(',') for row in current_table])
        tables.append(table_df)

    return tables

def combine_subheadings(df):
    """
    Combines subheadings in a DataFrame to create column headings.

    Args:
        df: The DataFrame with subheadings in the first two rows.

    Returns:
        A new DataFrame with combined column headings.
    """

    new_cols = []
    subheading1 = ''
    count = -1
    for col in df.columns:
        count += 1
        if subheading1 == '' and count<2:  # For first 2 columns use only second row
            subheading2 = df.iloc[1, col]
            new_col = f"{subheading2}"
            
        elif df.iloc[0, col] == '':  # If the first row is empty, use the last first row heading
            subheading2 = df.iloc[1, col]
            new_col = f"{subheading1}_{subheading2}"
        
        else: # Combine the first and second row headings
            subheading1 = df.iloc[0, col]
            subheading2 = df.iloc[1, col]
            new_col = f"{subheading1}_{subheading2}"
            
        new_cols.append(new_col)

    df.columns = new_cols
    df = df.iloc[2:]  # Remove the subheading rows

    return df

def emg_filter(emg_df, fs, lowcut=10, band_lowcut=20, band_highcut=450, order=4):
    nyq = 0.5 * fs
    normal_cutoff  = lowcut / nyq
    b_low, a_low = sig.butter(order, normal_cutoff, btype='low',analog=False)

    low = band_lowcut / nyq
    high = band_highcut / nyq
    b_band, a_band = sig.butter(order, [low, high], btype='band')

    for col in emg_df.columns:
        if col is None:
            continue
        
        if any(substring in col for substring in ['Frame', 'Sub Frame']):
            continue
        
        try:
            raw_emg_signal = pd.to_numeric(emg_df[col], errors='coerce')
            bandpass_signal = sig.filtfilt(b_band, a_band, raw_emg_signal)
            detrend_signal = sig.detrend(bandpass_signal, type='linear')
            rectified_signal = np.abs(detrend_signal)
            linear_envelope = sig.filtfilt(b_low, a_low, rectified_signal)
            emg_df[col] = linear_envelope
        except Exception as e:
            print(f"Error in filtering {col}: {e}")
            continue
    return emg_df

# Example usage
main_folder = r"C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\example_data\BiomechanicsSquats"
trials_of_interest = ['PartialROMSquat', 'FullROM']
trials_in_folder = os.listdir(main_folder)

# Filter trials in folder that contain any of the strings in trials_of_interest
matching_trials = [trial for trial in trials_in_folder if any(interest in trial for interest in trials_of_interest)]
matching_trials = [trial for trial in matching_trials if trial.endswith('.csv')]

force_column_of_interest = 'KMP-5 - Force_Fz'
emg_column_of_interest = ['EMG01_FDS_right', 'EMG02_FDS_left','EMG03_biceps_brachii_right']

for trial in matching_trials:
    file_path = os.path.join(main_folder, trial)
    trial_name = trial.split('.')[0]
    
    print(f"Reading data from {file_path}...")
    dataframes = read_csv_with_tables(file_path)
    
    # Check if there are two tables in the CSV file (for one table not fixed yet)
    if len(dataframes) == 2:
        emg_data, force_data = dataframes
        emg_fs = int(emg_data.iloc[1, 0])
        force_fs = int(force_data.iloc[1, 0])
        
        # Remove the first 3 rows from each DataFrame
        emg_data = emg_data.iloc[3:]
        force_data = force_data.iloc[2:]
        
        # for force data there is an heading and subheading rows, combined them to make new header
        force_data = combine_subheadings(force_data)
        
        # Set the column names to the first row of each DataFrame
        emg_data.columns = emg_data.iloc[0]
        emg_data = emg_data.iloc[1:]
        
        # make index start from 0 and reset index
        emg_data.reset_index(drop=True, inplace=True)
        force_data.reset_index(drop=True, inplace=True)
        
        # remove first row again as it is not needed
        emg_data = emg_data.drop(0)
        force_data = force_data.drop(0)
        
        if emg_fs is None or force_fs is None:
            print('Error: Sampling frequency not found')
            break
        else:
            # filter emg data 
            emg_data_filtered = emg_filter(emg_data, emg_fs)
        
        print(f"EMG sampling frequency: {emg_fs}")
        print(f"Force sampling frequency: {force_fs}")
        
        print(emg_data_filtered.head())
        print(force_data.head())
        
        # vertical force from 
        vertical_force = pd.to_numeric(force_data[force_column_of_interest], errors='coerce')
        vertical_force = np.abs(vertical_force)
        max_force = vertical_force.max()
        index_max_force = vertical_force.idxmax()
        
        # save emg and force plots
        save_folder = os.path.join(main_folder, trial_name)
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        
        # plot emg data
        f_emg = plt.figure()
        for col in emg_column_of_interest:
            plt.plot(emg_data_filtered[col], label=col)
        f_emg.savefig(os.path.join(save_folder, 'emg_plot.png'))
        
        # plot force data
        f_force = plt.figure()
        plt.plot(vertical_force, label=force_column_of_interest)
        f_force.savefig(os.path.join(save_folder, 'force_plot.png'))
        
        # select emg range around max force (2 or 4 seconds before)
        if trial_name.__contains__('PartialROMSquat'):
            emg_start = index_max_force - 2*emg_fs
        elif trial_name == 'FullROM':
            emg_start = index_max_force - 4*emg_fs
        
        emg_eccentric = emg_data_filtered.iloc[emg_start:index_max_force]
        emg_eccentric_area = emg_eccentric.sum()
        
        # plot emg eccentric data
        f_emg_eccentric = plt.figure()
        for col in emg_column_of_interest:
            plt.plot(emg_eccentric[col], label=col)
        f_emg_eccentric.savefig(os.path.join(save_folder, 'emg_eccentric_plot.png'))
        
        
        # save as new csv
        emg_save_path = os.path.join(save_folder, 'emg_filtered.csv')
        force_save_path = os.path.join(save_folder, 'force.csv')
        emg_ecc_save_path = os.path.join(save_folder, 'emg_eccentric_area.csv')
        
        emg_data_filtered.to_csv(emg_save_path, index=False)
        force_data.to_csv(force_save_path, index=False)
        emg_eccentric_area.to_csv(emg_ecc_save_path, index=False)
        print(f"Data saved to {save_folder}")
        
        exit()
        
    elif len(dataframes) == 1:
        dataframes[0].columns = dataframes[0].iloc[3]
        print('Error still not fixed')
        import pdb; pdb.set_trace()
        break
        
    


    

