import pandas as pd

filename = r'C:\Git\research_data\torsion_deformities_healthy_kinematics\subjectinfo.csv'
delimiter = '\\t'
df = pd.read_csv(filename, sep=delimiter)

new_filename = filename.replace('.csv','_new.csv')
df.to_csv(new_filename, index=False)
print(df)
