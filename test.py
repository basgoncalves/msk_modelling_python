
import sys
import os
import subprocess
src_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'src')
sys.path.append(src_path)
import msk_modelling_pkg_install
from bops import *
import bops as bp
osim.STOFileAdapter()
stoFilePath = bp.get_testing_file_path('id')
df = bp.import_sto_data(stoFilePath)
# bp.create_sto_plot()


# end_time = time.time()
# execution_time = end_time - start_time
# print(execution_time)
# exit()
bp.play_pong()

# plt.plot(df['time'],df['Voltage.RLicht'])
# plt.show()