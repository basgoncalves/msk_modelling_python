import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# Path to the Excel file
file_path = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\ParticipantData and Labelling.xlsx"

# Read the Excel file
df = pd.read_excel(file_path, sheet_name='Demographics', skiprows=1)

# Print the specified columns
columns_to_print = ['Subject','Measured Leg', 'R_acetabular coverage', 'L_acetabular coverage', 'Centre edge angle ']
LCEA = []
Coverage = []
for iRow in df.index:

    value = np.nan
    if df.loc[iRow, 'Measured Leg'] == 'R' and not np.isnan(df.loc[iRow, 'R_acetabular coverage']):
        Coverage.append(df.loc[iRow, 'R_acetabular coverage'])
        LCEA.append(df.loc[iRow, 'Centre edge angle '])
    elif df.loc[iRow, 'Measured Leg'] == 'L' and not np.isnan(df.loc[iRow, 'L_acetabular coverage']):
        Coverage.append(df.loc[iRow, 'L_acetabular coverage'])
        LCEA.append(df.loc[iRow, 'Centre edge angle '])
    
# calculate the correlation between LCEA and Coverage
correlation = round(pd.Series(LCEA).corr(pd.Series(Coverage)),2)

# scatter plot of LCEA vs Coverage
plt.scatter(LCEA, Coverage)
# Calculate the linear regression line
m, b = np.polyfit(np.array(LCEA), np.array(Coverage), 1)
regression_line = np.polyval([m, b], LCEA)

# Plot the scatter plot and linear regression line
plt.scatter(LCEA, Coverage)
plt.plot(LCEA, regression_line, color='black', linestyle = 'dashed', label='Linear Regression')

plt.xlabel('Centre edge angle')
plt.ylabel('Acetabular coverage')
plt.title('Centre edge angle vs Acetabular coverage')
plt.legend(['pearson r = ' + str(correlation)])

savedir = os.path.join(os.path.dirname(file_path), 'Compare_coverage_centre_edge_angle.png')
plt.savefig(savedir)
plt.show()