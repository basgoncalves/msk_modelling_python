
import os
import struct
import sys
os.add_dll_directory("C:/OpenSim 3.3/bin")
os.add_dll_directory(r"C:\Users\Bas\AppData\Local\Programs\Python\Python27\Lib\site-packages\opensim")
os.add_dll_directory(r'C:\OpenSim 3.3\sdk\Python')

print('python installed with ' + str(struct.calcsize("P") * 8) + ' bits')

