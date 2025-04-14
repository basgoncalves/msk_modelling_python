# import packages
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
import pandas as pd

current_path = os.getcwd()

# User select the folder of the volume you want to convert folders
target_path = askdirectory(initialdir=current_path)
print(target_path)
size_bytes = pd.DataFrame(columns=["file", "size"])
count = -1

for root, dirs, files in os.walk(target_path):
    for filename in files:
        full_path = os.path.join(root, filename)
        if os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            size_in_mb = round(size / (1024 * 1024), 2)
            if size_in_mb > 100:
                count += 1
                # Remove common part of target_path from full_path
                relative_path = os.path.relpath(full_path, target_path)
                size_bytes.loc[count] = [relative_path, size_in_mb]

# Display the resulting DataFrame
print(size_bytes)
