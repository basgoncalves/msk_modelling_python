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

import opensim as osim
import numpy as np
import os
import matplotlib.pyplot as plt
import pandas as pd
import msk_modelling_python as msk

model_path = r'C:\Git\1_current_projects\Fatigue-prediction-MSC-Thesis\simulations\009\scaled_models\009_Rajagopal2015_FAI_v4.osim'
trial_path = r'C:\Git\1_current_projects\Fatigue-prediction-MSC-Thesis\simulations\009\Run_baselineA1_BG1'
setup_file_path = os.path.join(trial_path, 'setup_ik.xml')
print(model_path)

osimAnalysis = msk.classes.osimSetup()

# osimAnalysis.run_ik_tool_from_xml(model_path, setup_file_path=setup_file_path, run_tool = True)

osimAnalysis.run_ik_tool_from_xml(model_path, setup_file_path)  # Correct

################
print(f"--- {time.time() - start_time} seconds ---")