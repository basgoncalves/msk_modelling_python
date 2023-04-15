import json
import bops as bp

switches = [1,0,0,0,0,0,0,0]
settings = bp.get_bops_settings()
settings['subjects'] = dict()
settings['subjects']['ID'] = []
settings['subjects']['Used'] = []
for i, switch in enumerate(switches):
    settings['subjects']['ID'].append(i)
    settings['subjects']['Used'] .append(switch)

bp.save_bops_settings(settings)

# import numpy as np

# # create a vertical vector
# v = np.array([1, 2, 3]).reshape(1, -1)

# # make the vector horizontal
# h = v.T

# print(h) 