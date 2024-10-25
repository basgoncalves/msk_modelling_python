import os
import pandas as pd
import msk_modelling_python as msk

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
    
    


if __name__ == "__main__":
    
    elaboratedDataDir = r'C:\Users\Bas\Downloads\hip\PersMeshPersF'
    subject = 's009'
    session = 'pre'
    trialName = 'RunStraight1'

    sessionPath = os.path.join(elaboratedDataDir, subject, session)

    ikPath = os.path.join(sessionPath, 'InverseKinematics', trialName ,'IK.mot')
    loadsPath = os.path.join(sessionPath, 'JointReactionAnalysis', trialName ,'JCF_JointReaction_ReactionLoads.sto')

    osim_to_febio(ikPath, loadsPath)
                

                