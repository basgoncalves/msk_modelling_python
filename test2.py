import pandas as pd
import bops as bp
import os 
from trc import TRCData


# Load TRC file as a dataframe
folder_name = r'C:\Git\research_data\torsion_deformities_healthy_kinematics\simulations\TD01\pre\dynamic1_l'
trc_file = os.path.join(folder_name,"markers.trc")

df = pd.read_csv(trc_file, skiprows=5, delimiter='\t')

df = bp.import_sto_data(trc_file)
# Calculate derivatives of columns LASI_2 and RASI_2
df['d_LASI'] = df['LASI_2'].diff()/1000 / df['time'].diff()
df['d_RASI'] = df['RASI_2'].diff()/1000 / df['time'].diff()

# Calculate average d_LASI and d_RASI
average_d_LASI = df['d_LASI'].mean()
average_d_RASI = df['d_RASI'].mean()

# Calculate the mean of the two averages
mean_derivative = (average_d_LASI + average_d_RASI) / 2

print(f"Average d_LASI: {average_d_LASI}")
print(f"Average d_RASI: {average_d_RASI}")
print(f"Mean of the two: {mean_derivative}")
