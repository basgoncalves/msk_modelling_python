import os
import json
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import msk_modelling_python as msk
import matplotlib.pyplot as plt
parent_dir = os.path.dirname(__file__)
start_time = time.time()
################
file = r'C:\Git\research_data\Projects\runbops_FAIS_phd\results\mean_ci\mean_ci.csv'
# df =  msk.bops.pd.read_csv(file)

# stats = file.replace('mean_ci.csv', 'group_comparison.xlsx')
# df_stats = pd.read_excel(stats)

# # radar plot 
# line_columns = ['mean', 'ci_low', 'ci_high']


# con = df[df['group'] == 'CON']
# fais = df[df['group'] == 'FAIS']
# cam = df[df['group'] == 'CAM']

# column_dict = ['Alpha angle' 'Centre edge angle' 'Coverage_tested_leg_BG'
#  'sphere_coverage_tested_leg_bg' 'HJCF_BW' 'HJCF_BW_normalised'
#  'HJCF_Newtons' 'HJCF_Newtons_normalised' 'HJCF_pHF_Newtons'
#  'HJCF_pHF_Newtons_normalised' 'HJCF_pHF_BW' 'HJCF_pHF_BW_normalised'
#  'Weight' 'Height' 'Age']


# print(df.head())
# print(df.columns)
# print(df['column'].unique())

#%%
subjects = ['CON', 'FAIS', 'CAM']
trial_path = 
sprint_1 = msk.


