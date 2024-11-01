import os
import tkinter as tk
import pandas as pd
import msk_modelling_python as msk


#%% s009 plot data from the TXT files to inspect the inputs for the loads 

def plot_from_txt(file_path, title=None):
    
    main_dir = r'C:\Users\Bas\Downloads\hip\PersMeshPersF'

    file_path = os.path.join(main_dir, 'kinematics_009_runStraight1\hip_rotation_r.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip Rotation R')

    file_path = os.path.join(main_dir, 'kinematics_009_runStraight1\hip_flexion_r.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip Flexion R')

    file_path = os.path.join(main_dir, 'kinematics_009_runStraight1\hip_adduction_r.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip Adduction R')

    file_path = os.path.join(main_dir, '\loads_009_runStraight1\hip_r_on_pelvis_in_pelvis_fx.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip R on Pelvis in Pelvis Fx')

    file_path = os.path.join(main_dir, '\loads_009_runStraight1\hip_r_on_pelvis_in_pelvis_fy.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip R on Pelvis in Pelvis Fy')

    file_path = os.path.join(main_dir, '\loads_009_runStraight1\hip_r_on_pelvis_in_pelvis_fz.txt')
    msk.src.bops.plot_from_txt(file_path, title='Hip R on Pelvis in Pelvis Fz')

    msk.src.bops.plt.show()


def add_seconds_to_dataframe(dataFrame, seconds):
    # Calculate the time step
    time_steps = dataFrame['time'].iloc[1] - dataFrame['time'].iloc[0]
    
    # Create new rows for the specified seconds of data prior to the existing DataFrame
    num_new_rows = int(seconds / time_steps)
    new_time = pd.DataFrame({
        'time': [i * time_steps for i in range(num_new_rows)]
    })
    for column in dataFrame.columns:
        if column != 'time':
            new_time[column] = 0
    
    # Concatenate the new rows with the existing DataFrame
    dataFrame['time'] += seconds  # Delay the original time by the specified seconds
    dataFrame = pd.concat([new_time, dataFrame], ignore_index=True)
    
    return dataFrame



def split_dataFrame_to_txt(dataFrame, outputDir):
    os.makedirs(outputDir, exist_ok=True)
    print('Saving data to: ', outputDir)
    
    time = dataFrame[['time']]
    # make time starting from 0 + 1 second
    time['time'] = time['time'] - time['time'][0]
    for column in dataFrame.columns:
        if column == 'time':
            continue
        data = dataFrame[[column]]
        data = pd.concat([time, data], axis=1)  
        data = add_seconds_to_dataframe(data, 1)
        
        data.to_csv(os.path.join(outputDir, column + '.txt'), sep=' ', index=False)
        
    print('Data saved!')


def osim_to_febio(ikPath, loadsPath):
    ik_df = msk.src.bops.import_sto_data(ikPath)
    loads_df = msk.src.bops.import_sto_data(loadsPath)
    
    savePath = os.path.join(os.path.dirname(ikPath), 'febio')
    split_dataFrame_to_txt(ik_df, savePath)
    
    savePath = os.path.join(os.path.dirname(loadsPath), 'febio')
    split_dataFrame_to_txt(loads_df, savePath)
    
    # create a zero file with the same time as ik_df + 1 second
    zero_df = ik_df[['time']].copy()
    zero_df['time'] = zero_df['time'] - zero_df['time'].iloc[0] + 1
    zero_df['Zeros'] = 0
    # zero_df = add_seconds_to_dataframe(zero_df, 1)
    
    savePath = os.path.join(os.path.dirname(ikPath))
    zero_df.to_csv(os.path.join(savePath, 'zero.txt'), sep=' ', index=False)

if __name__ == "__main__":
    
    elaboratedDataDir = r'C:\Users\Bas\Downloads\hip\PersMeshPersF'
    subject = 's009'
    session = 'pre'
    trialName = 'RunStraight1'

    sessionPath = os.path.join(elaboratedDataDir, subject, session)

    ikPath = os.path.join(sessionPath, 'InverseKinematics', trialName ,'IK.mot')
    loadsPath = os.path.join(sessionPath, 'JointReactionAnalysis', trialName ,'JCF_JointReaction_ReactionLoads.sto')

    osim_to_febio(ikPath, loadsPath)
                

# END