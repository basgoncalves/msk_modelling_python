import json
import os
import numpy as np
from scipy.spatial.transform import Rotation
from mpl_toolkits.mplot3d import Axes3D
import sys
import os
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------ #
# Copyright (c) 2023 B. Goncalves & W. Koller
#    Author:   Basilio Goncalves & Willi Koller,  2023
#    email:    basilio.goncalves@univie.ac.at / willi.koller@univie.ac.at
# ----------------------------------------------------------------------- #

# Method_Sangeux_2015 (c) by Basilio Goncalves & Willi Koller, University of Vienna
#
# Method_Sangeux_2015 is licensed under a
# Creative Commons Attribution-NonCommercial 4.0 International License.
#
# You should have received a copy of the license along with this
# work. If not, see <http://creativecommons.org/licenses/by-nc/4.0/>.

# this script uses GIBBON- and MSK-STAPLE toolboxes
# https://github.com/modenaxe/msk-STAPLE
# https://github.com/gibbonCode/

fname = r'C:\Git\research_documents\Uvienna\Teaching\w2023\bachelors_thesis\ksenija_jancic\data\MRI\009\right.mrk.json'
side = 'L'
plotFigure = False
# if a STL named " *(side)_femur*.stl" is available in the same folder, it
# is used for plotting and also to calculate AVA in transverse plane

with open(fname, 'r') as file:
    str = file.read()
data = json.loads(str)

folder = os.path.dirname(fname)
files = os.listdir(folder)
STLfileName = ''

for file in files:
    if '.stl' in file and side + '_femur' in file:
        STLfileName = file
        break

hjcI = None
gtI = None
psI = None
dsI = None
lcI = None
mcI = None

controlPoints = data['markups'][0]['controlPoints']

for i, controlPoint in enumerate(controlPoints):
    label = controlPoint['label']
    if label == 'HJC':
        hjcI = i
    elif label == 'GT':
        gtI = i
    elif label == 'PS':
        psI = i
    elif label == 'DS':
        dsI = i
    elif label == 'LC':
        lcI = i
    elif label == 'MC':
        mcI = i

neckAxis = np.subtract(controlPoints[hjcI]['position'], controlPoints[gtI]['position'])
shaftAxis = np.subtract(controlPoints[psI]['position'], controlPoints[dsI]['position'])
kneeAxis = np.subtract(controlPoints[lcI]['position'], controlPoints[mcI]['position'])

# NSA in 3D
cross_product = np.cross(-neckAxis, shaftAxis)
dot_product = np.dot(-neckAxis, shaftAxis)
norm_cross_product = np.linalg.norm(cross_product)
NSA = round(np.degrees(np.arctan2(norm_cross_product, dot_product)),1)
print('Neck-Shaft Angle = '+ NSA.__str__() + '°')

def GG(A, B):
    return np.array([[np.dot(A, B), -np.linalg.norm(np.cross(A, B)), 0],
                     [np.linalg.norm(np.cross(A, B)), np.dot(A, B), 0],
                     [0, 0, 1]])

def FFi(A, B):
    return np.column_stack((A, (B - np.dot(A, B) * A) / np.linalg.norm(B - np.dot(A, B) * A), np.cross(B, A)))

def UU(Fi, G):
    return np.dot(np.dot(Fi, G), np.linalg.inv(Fi))

a = shaftAxis / np.linalg.norm(shaftAxis)
b = np.array([0, 0, 1])
U = UU(FFi(a, b), GG(a, b))
print('norm(U):', np.linalg.norm(U))
print('norm(b-U*a):', np.linalg.norm(b - np.dot(U, a)))
print('U:', U)

neckAxisRotated = np.dot(U, neckAxis)
kneeAxisRotated = np.dot(U, kneeAxis)
shaftAxisRotated = np.dot(U, shaftAxis)

u = neckAxisRotated[:2]
v = kneeAxisRotated[:2] * (-1)
CosTheta = max(min(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)), 1), -1)
AVA_inPlanePerpendicularToShaft = round(np.degrees(np.arccos(CosTheta)), 1)
print('Anteversion in plane perpendicular to shaft = ' +  AVA_inPlanePerpendicularToShaft.__str__() + '°')

if plotFigure:
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle('View on plane which is perpendicular to shaft axis')

    ax1 = fig.add_subplot(121, projection='3d')
    ax1.set_box_aspect([1, 1, 1])
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')
    ax1.quiver(controlPoints[gtI]['position'][0], controlPoints[gtI]['position'][1], controlPoints[gtI]['position'][2],
            neckAxis[0], neckAxis[1], neckAxis[2], linewidth=2, label='Neck Axis')
    ax1.quiver(controlPoints[dsI]['position'][0], controlPoints[dsI]['position'][1], controlPoints[dsI]['position'][2],
            shaftAxis[0], shaftAxis[1], shaftAxis[2], linewidth=2, label='Shaft Axis')
    ax1.quiver(controlPoints[mcI]['position'][0], controlPoints[mcI]['position'][1], controlPoints[mcI]['position'][2],
            kneeAxis[0], kneeAxis[1], kneeAxis[2], linewidth=2, label='Knee Axis')
    ax1.legend()
    ax1.view_init(elev=30, azim=-60)

    ax2 = fig.add_subplot(122, projection='3d')
    ax2.set_box_aspect([1, 1, 1])
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('Z')
    ax2.quiver(controlPoints[gtI]['position'][0], controlPoints[gtI]['position'][1], controlPoints[gtI]['position'][2],
            neckAxis[0], neckAxis[1], neckAxis[2], linewidth=2, label='Neck Axis')
    ax2.quiver(controlPoints[dsI]['position'][0], controlPoints[dsI]['position'][1], controlPoints[dsI]['position'][2],
            shaftAxis[0], shaftAxis[1], shaftAxis[2], linewidth=2, label='Shaft Axis')
    ax2.quiver(controlPoints[mcI]['position'][0], controlPoints[mcI]['position'][1], controlPoints[mcI]['position'][2],
            kneeAxis[0], kneeAxis[1], kneeAxis[2], linewidth=2, label='Knee Axis')
    ax2.legend()
    ax2.view_init(elev=0, azim=0)

    plt.show()


# save in .txt doc
parent_folder, filename = os.path.split(fname)
txt_file = os.path.join(parent_folder, 'torsion_measures.txt')

with open(txt_file, 'a') as fid:
    fid.write(filename)
    fid.write('\n')
    fid.write('Anteversion in plane perpendicular to shaft = ' + f"{AVA_inPlanePerpendicularToShaft}°" + ' \n')
    fid.write('Neck-Shaft Angle = ' + NSA.__str__() + '° \n')
    fid.write('\n')
