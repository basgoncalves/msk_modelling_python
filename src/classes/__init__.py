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


#%% OSIM DATA CLASSES
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
        
class Task:
    # For each task, create a class that contains the osimData objects
    # check example folder structure: C:\Project\Subject\Task\osimData
    def __init__(self, taskPath):
        self.path = taskPath
        self.folders = os.listdir(taskPath)
        
        for folder in self.folders:
            folderPath = os.path.join(taskPath, folder)
            self.__dict__[folder] = msk.osimData(folderPath)
            

class Subject:
    # For each subject, create a class that contains the Task objects
    # check example folder structure: C:\Project\Subject\Task\osimData
    def __init__(self, path):
        self.path = path
        self.tasks = os.listdir(path)
        
        for task in self.tasks:
            taskPath = os.path.join(path, task)
            if os.path.isdir(taskPath):
                self.__dict__[task] = msk.Task(taskPath)
        


class Project:
    # For each project, create a class that contains the Subject objects
    # check example folder structure: C:\Project\Subject\Task\osimData
    def __init__(self, projectPath):
        self.path = projectPath
        self.dataPath = os.path.join(projectPath, 'Data')
        self.subjects = []
        
        for subject in os.listdir(self.dataPath):
            subjectPath = os.path.join(self.dataPath, subject)
            if os.path.isdir(subjectPath):
                self.__dict__[subject] = msk.Subject(subjectPath)    
                self.subjects.append(subject)
    

def isTask(var):
    return isinstance(var, msk.Task)

def isSubject(var):
    return isinstance(var, msk.Subject)

def isProject(var):
    return isinstance(var, msk.Project)
    
        
# END