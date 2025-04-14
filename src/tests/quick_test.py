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

filename = r"C:\Git\research_data\Projects\squatting_fais\c3dfiles\009\SJ\SJ_post1.c3d"

data = open(filename, 'rb').read()

print(data)

################
print(f"--- {time.time() - start_time} seconds ---")