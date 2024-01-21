import opensim as osim
import os
import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np
from sklearn.metrics import mean_squared_error


id_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_70\inverse_dynamics.sto"
ceinms_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_70\ceinms_results\Torques.sto"

def import_sto_data(stoFilePath):

    if not os.path.exists(stoFilePath):
        print('file do not exists')

    file_id = open(stoFilePath, 'r')

    # read header
    next_line = file_id.readline()
    header = [next_line]
    nc = 0
    nr = 0
    while not 'endheader' in next_line:
        if 'datacolumns' in next_line:
            nc = int(next_line[next_line.index(' ') + 1:len(next_line)])
        elif 'datarows' in next_line:
            nr = int(next_line[next_line.index(' ') + 1:len(next_line)])
        elif 'nColumns' in next_line:
            nc = int(next_line[next_line.index('=') + 1:len(next_line)])
        elif 'nRows' in next_line:
            nr = int(next_line[next_line.index('=') + 1:len(next_line)])

        next_line = file_id.readline()
        header.append(next_line)

    # process column labels
    next_line = file_id.readline()
    if next_line.isspace() == True:
        next_line = file_id.readline()

    labels = next_line.split()

    # get data
    data = []
    for i in range(1, nr + 1):
        d = [float(x) for x in file_id.readline().split()]
        data.append(d)

    file_id.close()
    
    # Create a Pandas DataFrame
    df = pd.DataFrame(data, columns=labels)

    return df

mom_id = import_sto_data(id_path)
mom_ceinms = import_sto_data(ceinms_path)

mom_id = mom_id.drop(columns=['time'])
mom_ceinms = mom_ceinms.drop(columns=['time'])

nrows = 2
ncols = int(len(mom_ceinms.columns)/2)

# Create a new figure and subplots
fig, axs = plt.subplots(nrows, ncols, figsize=(15, 5))
for row, ax_row in enumerate(axs):
    for col, ax in enumerate(ax_row):
        ax_count = row * ncols + col

        heading = mom_ceinms.columns[ax_count]    
        heading_id = heading + '_moment'

        if heading_id not in mom_id.columns:
            print(f'Heading not found: {heading}')
            continue    
        else:
            print(f'Plotting: {heading}')
        
        # calculate RMS error
        error = np.sqrt(mean_squared_error(mom_id[heading_id],mom_ceinms[heading]))
        error_text = f'RMS error: {error:.2f}'
        # Plot data
        ax.plot(mom_id[heading_id])
        ax.plot(mom_ceinms[heading])
        ax.set_title(f'{heading}')
        ax.text(0.95, 0.95, error_text, fontsize=10, color='black',
                ha='right', va='top', transform=ax.transAxes)
        
        if row == 1:
            ax.set_xlabel('Time')
        if col == 0:
            ax.set_ylabel('Moment (Nm)')

plt.legend(['inverse dynamics', 'ceinms'])


# Adjust spacing between subplots
plt.tight_layout()

save_folder = r"C:\Git\isbs2024\Data\results\Athlete_03"
if not os.path.exists(save_folder):
    os.mkdir(save_folder)
plt.savefig(os.path.join(save_folder, "moment_errors.png"))

