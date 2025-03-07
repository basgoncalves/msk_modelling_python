import msk_modelling_python as msk
import opensim as osim
import sys
import pyc3dserver as c3d

filepath = r"C:\Git\opensim_tutorial\tutorials\repeated_sprinting\settings.bops"

# print(msk.bops.settings.read())
filepath = r"C:\Git\opensim_tutorial\tutorials\repeated_sprinting\Simulations\009_simplified\settings.json"
# msk.bops.read(filepath)

c3d_file = r"C:\Git\opensim_tutorial\tutorials\repeated_sprinting\Simulations\009_simplified\10m_sprint\10m_sprint.c3d"
import c3d
r = c3d.Reader(open(c3d_file, 'rb'))

import pdb; pdb.set_trace()