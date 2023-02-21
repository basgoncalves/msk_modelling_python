
import os
import struct
import sys
os.add_dll_directory("C:/OpenSim 4.3/bin")
os.add_dll_directory(r"C:\Users\Bas\AppData\Local\Programs\Python\Python311\Lib\site-packages\opensim")
os.add_dll_directory('C:\OpenSim 4.3\sdk\Simbody')
print('python installed with ' + str(struct.calcsize("P") * 8) + ' bits')

