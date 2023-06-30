
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

bp.play_pong-0
