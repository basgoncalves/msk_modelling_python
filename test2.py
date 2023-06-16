from bops import *

def add_title(axes):
    for i, ax in enumerate(axes):
        ax.set_title("ax%d" % (i+1), fontsize=18)
        
fig = plt.figure(figsize=(8, 8))
ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=2)
ax2 = plt.subplot2grid((3, 3), (0, 2), rowspan=3)
ax3 = plt.subplot2grid((3, 3), (1, 0), rowspan=2)
ax4 = plt.subplot2grid((3, 3), (1, 1))
ax5 = plt.subplot2grid((3, 3), (2, 1))

add_title(fig.axes)

plt.show()