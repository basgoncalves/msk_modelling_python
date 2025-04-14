import msk_modelling_python as msk
import pandas as pd
import numpy as np

'''
Description: This script converts results from OpenSim (.mot, .sot, .trc) to a .txt file.
'''

def add_seconds_to_df(df, seconds):
    '''
    Add a certain amount of seconds to the beginning of the time column of a DataFrame.
    
    Usage: 
    df = pd.DataFrame({
        'time': np.arange(0, 2, 0.05),
        'column1': np.arange(0, 2, 0.05),
        'column2': np.arange(0, 2, 0.05) ** 2
    })
    new_df = add_seconds_to_df(df, 1)
    print(new_df)
    '''
    # Create a sample DataFrame
  

    # Add 1 second of zeros before the first time point for each column
    fs = 1 / df['time'][1]
    list_zeros = np.arange(0, seconds, 1/fs)
    df_zeros = pd.DataFrame({'time': list_zeros})

    # Concatenate the zeros DataFrame with the original DataFrame
    df['time'] = df['time'] + 1
    new_df = pd.concat([df_zeros, df], ignore_index=True)

    # Change NaNs by zeros
    new_df = new_df.fillna(0)
    
    return new_df

def convert_to_txt(file_path):
    """
    Converts a .osim file to a .txt file.

    Parameters:
    file_path (str): The path to the .osim file to be converted.
    """
    extension = file_path.split('.')[-1]
    if extension not in ['mot', 'sto', 'trc']:
        print("Error: The file extension is not supported")
        print("Supported extensions: .mot, .sto, .trc")
        return
    
    data = msk.bops.import_file(file_path)
    
    if data is None:
        print("Error: Could not import the file")
        return
    
    # make time start from 0
    data['time'] = data['time'] - data['time'][0]
    
    # add 1 second before the first time point
    data = add_seconds_to_df(data, 1)
    

    try:
        trial_name = os.path.basename(file_path).split('.')[0]
        new_folder = os.path.join(os.path.dirname(file_path), trial_name)
        if not os.path.exists(new_folder):
            os.makedirs(new_folder)

    # loop through all columns and save them in separate files
        for column in data.columns:
            if column == 'time':
                continue
            new_df = pd.DataFrame(data['time'], columns=['time',column])
           
            new_df['time'] = data['time']
            new_df[column] = data[column].apply(lambda x: round(x, 4))            
            new_df.to_csv(os.path.join(new_folder, f"{column}.txt"), index=False, header=False, sep=' ')
        
        print(f"Files saved in {new_folder}")
    except Exception as e:
        print("Error: Could not convert the file")
        print(e)
        return

if __name__ == "__main__":
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ik_file = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\msk_simulations\010\pre\Run_baselineA1\joint_angles.mot"
    jrf_file = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\msk_simulations\010\pre\Run_baselineA1\joint_reaction_loads.sto"
    
    
    # if not os.path.isfile(ik_file):
    #     ik_file = msk.ui.select_file(prompt='Select the inverse kinematics file')
        
    # if not os.path.isfile(jrf_file):
    #     jrf_file = msk.ui.select_file(prompt='Select the joint reactions file')

    
    convert_to_txt(ik_file)
    convert_to_txt(jrf_file)

