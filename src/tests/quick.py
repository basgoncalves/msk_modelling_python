import tkinter as tk
import msk_modelling_python as msk
import os

project_path = r"C:\Git\charizard"
data_path = os.path.join(project_path, 'data')
osimModel_path = os.path.join(project_path, 'osimModel')


project = msk.Project(project_path)
print(project.subjects)

exit()

# Athlete data = folders in the data folder
athlethes = os.listdir(data_path)

for ath in athlethes:
    # create a task object for each task
    ath_path = os.path.join(data_path, ath)
    tasks = os.listdir(ath_path)
    
    for task in tasks:
        task_path = os.path.join(ath_path, task)
        msk.Task(task_path)


task_path = r"C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\example_data\db_movements\running"
task = msk.Task(task_path)

msk.osimData(os.path.join(task_path, 'average'))


if isinstance(task.s009.muscleForces, msk.bp.pd.DataFrame):
    print("Muscle Forces exist for subject 9")

