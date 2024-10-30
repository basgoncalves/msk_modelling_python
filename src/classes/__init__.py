from msk_modelling_python import *
import msk_modelling_python as msk
import pyperclip
import json
import os

class mcf: # make coding fancy
    
    def __init__(self):
        pass
            
    header = staticmethod(lambda: pyperclip.copy("#%% #############################################################\n" +
                                                 "#                        Description:                           # \n" +
                                                 "##################################################################"))


# create a class for each option so that we can print the option names
class cmd_function:
    def __init__(self, func):
        self.func = func

    def run(self, *args, **kwargs):
        self.func(*args, **kwargs)


class osimData:
    def __init__(self,path):
        self.path = path

        filesToImport = ['ik.mot', 'muscleFroces.sto', 'jointLoads.sto']
        
        # check if the files exist and load the existing files
        for file in filesToImport:
            if not os.path.isfile(os.path.join(path, file)):
                print(f"Error: {file} not found in {path}")
            else:
                if file == 'ik.mot':
                    self.angles = msk.bp.import_sto_data(os.path.join(path, file))
                elif file == 'muscleFroces.sto':
                    self.muscleForces = msk.bp.import_sto_data(os.path.join(path, file))
                elif file == 'jointLoads.sto':
                    self.jointLoads = msk.bp.import_sto_data(os.path.join(path, file))
        

# settings class
class Task:
    def __init__(self, path):
        self.path = path
        self.folders = os.listdir(path)
        
        for folder in self.folders:
            folderPath = os.path.join(path, folder)
            self.__dict__[folder] = msk.osimData(folderPath)
            

    
    
    
        
# END