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

initial_path =  r'C:\Git\research_data\models\Gerometry_bones\femur'
vtp_path = msk.ui.select_file("Select the VTP file to load", staring_path=initial_path)






################
print(f"--- {time.time() - start_time} seconds ---")