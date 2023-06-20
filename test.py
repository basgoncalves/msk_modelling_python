
import time

start_time = time.time()

import sys
import os
import subprocess
src_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'src')
sys.path.append(src_path)
import msk_modelling_pkg_install
from bops import *
import bops as bp

# end_time = time.time()
# execution_time = end_time - start_time
# print(execution_time)
# exit()

c3dFilePath = bp.get_testing_file_path('c3d')
df = bp.import_c3d_analog_data(c3dFilePath)
c3d_dict = bp.import_c3d_to_dict(c3dFilePath)
# print('\n'.join(c3d_dict.keys()))
df = bp.emg_filter(c3dFilePath)

# plt.plot(df['time'],df['Voltage.RLicht'])
# plt.show()