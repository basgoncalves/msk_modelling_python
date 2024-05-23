import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # appropriate import to draw 3d polygons
from matplotlib import style


def plot_triangle(x,y,z,facecolor='#800000',alpha=0.5):
    
    custom=plt.subplot(111,projection='3d')

    custom.scatter(x,y,z)

    # 1. create vertices from points
    verts = [list(zip(x, y, z))]
    # 2. create 3d polygons and specify parameters
    srf = Poly3DCollection(verts, alpha=alpha, facecolor=facecolor)
    # 3. add polygon to the figure (current axes)
    plt.gca().add_collection3d(srf)

    custom.set_xlabel('X')
    custom.set_ylabel('Y')
    custom.set_zlabel('Z')


x1=np.array([1, -2, 1])
y1=np.array([5, 3, 7])
z1=np.array([0, 0, 6])  # z1 should have 3 coordinates, right?

# plt.figure(figsize=(6,6))
plot_triangle(x1,y1,z1)

x2=np.array([1, -2, 2])
y2=np.array([5, 3, 4])
z2=np.array([0, 0, 7])
plot_triangle(x2,y2,z2)  

