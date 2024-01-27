import msk_modelling_pkg_install
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import scipy
from opensim import C3DFileAdapter
import opensim as osim
import numpy as np
import os
import bops
import shutil


import matplotlib.pyplot as plt
import numpy as np
# Data
x = [1, 2, 3, 4, 5]
y = [1, 10, 100, 500, 1000]

# Plot configuration
plt.bar(x, y, color='grey')
plt.xticks([])
plt.box(False)
plt.tick_params(axis='both', which='major', labelsize=18, width=0)
plt.rcParams['font.family'] = 'Arial'
plt.gcf().set_facecolor('none')

# Save the figure
plt.savefig('C:\\Git\\MSKmodelling\\Projects\\MatlabStaticOptimization\\TestData\\figures\\barplot.png', dpi=300, transparent=True, bbox_inches='tight')
# plt.show()