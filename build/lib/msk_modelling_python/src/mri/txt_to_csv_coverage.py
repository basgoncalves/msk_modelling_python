import os
import pandas as pd

csv_file = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage\coverage_results.csv"
xls_file = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\ParticipantData and Labelling - Copy.xlsx"
coverage_path = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage'

# Read the Excel file
df = pd.read_excel(xls_file, sheet_name='Demographics', skiprows=0)

column_name_l = 'L_acetabular coverage_BG'
legs = ['r','l']


for folder in os.listdir(coverage_path):
    for leg in legs:
        coverage_txt = os.path.join(coverage_path, folder, 'Meshlab_BG',f'femoral_head_{leg}_threshold_25',f'femoral_head_{leg}.txt')
        if os.path.isfile(coverage_txt):
            coverage = pd.read_csv(coverage_txt, sep='\t', header=None) 
            column_name = f'{leg.upper()}_acetabular coverage_BG'             
        else:
            print(f"File {coverage_txt} does not exist")
            continue
            
        # find the line that contains "Normalized Area Covered" and extract the value with the percentage sign
        coverage_percent = None
        for line in coverage[0]:
            if "Normalized Area Covered:" in line:
                coverage_percent = float(line.split(":")[1].strip()[:-1])
                break
        
        # add the coverage percent to the dataframe column for the corresponding subject
        if coverage_percent is not None:
            df.loc[df['Subject'] == folder, column_name] = coverage_percent
        else:
            print("Normalized Area Covered not found in coverage file")
            continue

# Save the updated dataframe to a new Excel file
df.to_excel(xls_file.replace('.xlsx','_updated.xlsx'), index=False)
      


