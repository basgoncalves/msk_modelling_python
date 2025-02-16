import os
# from msk_modelling_python.src.bops import bops
import pandas as pd

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

currentp_path = os.path.dirname(os.path.abspath(__file__))

emg_data_path = os.path.join(currentp_path, 'FullROM02', 'EMG.csv')
force_data_path = os.path.join(currentp_path, 'FullROM02', 'Force.csv')

emg_columns_of_interest = ['']

emg_data = pd.read_csv(emg_data_path, skiprows=3)
emg_data = emg_data.drop(0)

force_data = pd.read_excel(force_data_path, skiprows=2)
force_data = force_data.drop(1)

# combine column names and row 0 to make new header
# new_header = force_data.iloc[0]
# force_data = force_data[1:]
# force_data.columns = new_header

# max_force = force_data['Force'].max()
# print(force_data.head())
# print(emg_data.head())

force_columns = force_data.columns

# check if force_columns contains 'KMP-5 - Force'

if 'KMP-5 - Force' in force_columns:
    print('KMP-5 - Force is in the columns')
    
    # find index of the column 'KMP-5 - Force'
    force_index = force_columns.get_loc('KMP-5 - Force')
    
    print(force_columns)
    
    # in row 0, check force_index until force_index + 3 and find the column with name "Fz"
    for i in range(force_index, force_index + 3):
        current_cell = force_data.iloc[0, i]
        print(current_cell)
        if current_cell.__contains__('Fz'):
            print('Fz is in the columns')
            break
        
    # vertical force is now in the column force_data.iloc[:, i]
    force_vertical = force_data.iloc[:, i]
    
    max_force = force_vertical.max()
    index_max_force = force_vertical.idxmax()
    
    
    # find the corresponding EMG data
    emg_data_columns = emg_data.columns
    
    
    
else:
    print('KMP-5 - Force is not in the columns')
    print(force_columns)