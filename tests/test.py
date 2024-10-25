import tkinter as tk
import msk_modelling_python as msk

file_path = r"C:\Users\Bas\Downloads\hip\PersMeshPersF\kinematics_009_runStraight1\hip_rotation_r.txt"
msk.src.bops.plot_from_txt(file_path, title='Hip Rotation R')

file_path = r"C:\Users\Bas\Downloads\hip\PersMeshPersF\kinematics_009_runStraight1\hip_flexion_r.txt"
msk.src.bops.plot_from_txt(file_path, title='Hip Flexion R')

file_path = r"C:\Users\Bas\Downloads\hip\PersMeshPersF\kinematics_009_runStraight1\hip_adduction_r.txt"
msk.src.bops.plot_from_txt(file_path, title='Hip Adduction R')

msk.src.bops.plt.show()


