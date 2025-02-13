import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import msk_modelling_python as msk

################
def format_subject_id(subject_id):
        """Formats a subject ID to a 3-digit string."""
        try:
            # Convert to integer first to handle cases like '01'
            subject_id = int(subject_id)
            return f"{subject_id:03d}"  # Formats the integer to a 3-digit string
        except ValueError:
            # Handle cases where the value is not convertible to an integer
            return str(subject_id)  # Return the original value as a string  


file_path = r"C:\Git\research_data\Projects\runbops_FAIS_phd\subject_info.csv"
info = pd.read_csv(file_path)

print(info.head())
print(info['Subject'])

info['Subject'] = info['Subject'].apply(format_subject_id)
info['Subject'] = info['Subject'].astype(str)
info.to_csv(file_path.replace('.csv','_upd.csv'), index=False)

print(info.head())
print(info['Subject'])