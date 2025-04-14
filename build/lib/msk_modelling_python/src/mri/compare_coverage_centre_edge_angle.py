import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def mmfn():
    # Set the style of the plot
    plt.style.use('seaborn-whitegrid')

    # Set the font size for the plot
    plt.rcParams.update({'font.size': 12})

    # Set the figure size
    ax = plt.gca()

    # Customize the axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_linewidth(0.5)
    ax.tick_params(axis='both', which='both', length=0)

    # Customize the grid
    ax.grid(color='gray', linestyle='--', linewidth=0.5)


# Path to the Excel file
file_path = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\ParticipantData and Labelling.xlsx"

# Read the Excel file
df = pd.read_excel(file_path, sheet_name='Demographics', skiprows=0)

coverage_R_column = 'R_acetabular coverage_BG'
coverage_L_column = 'L_acetabular coverage_BG'

# Print the specified columns
columns_to_print = ['Subject','Measured Leg', coverage_R_column, coverage_L_column, 'Centre edge angle ']
LCEA = []
Alpha_angle = []
Coverage = []
for iRow in df.index:
    
    value = np.nan
    if df.loc[iRow, 'Measured Leg'] == 'R':
        value = df.loc[iRow, coverage_R_column]
        if pd.api.types.is_numeric_dtype(value) and not np.isnan(value):
            Coverage.append(df.loc[iRow, coverage_R_column])
            LCEA.append(df.loc[iRow, 'Centre edge angle'])
            Alpha_angle.append(df.loc[iRow, 'Alpha angle'])

    elif df.loc[iRow, 'Measured Leg'] == 'L':
        value = df.loc[iRow, coverage_L_column]
        if pd.api.types.is_numeric_dtype(value) and not np.isnan(value):
            Coverage.append(df.loc[iRow, coverage_L_column])
            LCEA.append(df.loc[iRow, 'Centre edge angle'])
            Alpha_angle.append(df.loc[iRow, 'Alpha angle'])
    
# calculate the correlation between LCEA and Coverage
correlation = round(pd.Series(LCEA).corr(pd.Series(Coverage)),2)

# Calculate the linear regression lines 
m, b = np.polyfit(np.array(LCEA), np.array(Coverage), 1)
regression_line_LCEA = np.polyval([m, b], LCEA)

m, b = np.polyfit(np.array(Alpha_angle), np.array(Coverage), 1)
regression_line_Alpha_angle = np.polyval([m, b], Alpha_angle)

# scatter plot of LCEA vs Coverage 
plt.figure(figsize=(15, 5))
ax = plt.subplot(1, 2, 1)
plt.scatter(LCEA, Coverage)

plt.plot(LCEA, regression_line_LCEA, color='black', linestyle = 'dashed', label='Linear Regression')

plt.xlabel('Centre edge angle')
plt.ylabel('Acetabular coverage')
plt.legend(['pearson r = ' + str(correlation)])
mmfn()

# scatter plot of Alpha angle vs Coverage
plt.subplot(1, 2, 2)
plt.scatter(Alpha_angle, Coverage)

plt.plot(Alpha_angle, regression_line_Alpha_angle, color='black', linestyle = 'dashed', label='Linear Regression')

plt.xlabel('Alpha angle')
plt.ylabel('Acetabular coverage')
plt.legend(['pearson r = ' + str(correlation)])
mmfn()

savedir = os.path.join(os.path.dirname(file_path), 'Compare_coverage_centre_edge_angle.png')
plt.savefig(savedir)
plt.show()