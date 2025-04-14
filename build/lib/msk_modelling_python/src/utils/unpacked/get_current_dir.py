import os

dir_path = os.path.dirname(os.path.realpath(__file__)) # for .py
dir_path = os.getcwd() # for ipynb

os.chdir(dir_path)