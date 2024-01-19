import opensim as osim
import os
import pandas as pd
import matplotlib.pyplot as plt
import math

id_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_70\inverse_dynamics.sto"
ceinms_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_70\ceinms_results\Torques.sto"

def import_sto_data(stoFilePath):
    """ Reads OpenSim .sto files.
    Parameters
    ----------
    filename: absolute path to the .sto file
    Returns
    -------
    header: the header of the .sto
    labels: the labels of the columns
    data: an array of the data
    
    Credit: Dimitar Stanev
    https://gist.github.com/mitkof6/03c887ccc867e1c8976694459a34edc3#file-opensim_sto_reader-py
    
    Added the conversion to pd.DataFrame(s)
    """

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

data1 = import_sto_data(id_path)
data2 = import_sto_data(ceinms_path)

nrows = int(math.sqrt(len(data2.columns)))

data2.plot(subplots=True, layout=(nrows, nrows), figsize=(10, 10))
plt.tight_layout()
plt.show()

exit()
# Loop through the headings
for heading in data2.columns:
    if heading == 'time':
        continue

    heading_id = heading + '_moment'
    if heading_id not in data1.columns:
        print(f'Heading not found: {heading}')
        continue    
    else:
        print(f'Plotting: {heading}')
        
    # Create a new figure and subplots
    fig, axs = plt.subplots(2, 1, figsize=(8, 6))

    # Plot data1
    axs[0].plot(data1[heading_id])
    axs[0].set_title(f'{heading} - data1')

    # Plot data2
    axs[1].plot(data2[heading])
    axs[1].set_title(f'{heading} - data2')

    # Adjust spacing between subplots
    plt.tight_layout()

    # Show the plot
    plt.show()
