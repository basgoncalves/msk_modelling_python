import tkinter as tk
import msk_modelling_python as msk
import os

task_path = r"C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\example_data\db_movements\running"
task = msk.Task(task_path)

msk.osimData(os.path.join(task_path, 'average'))


if isinstance(task.s009.muscleForces, msk.bp.pd.DataFrame):
    print("Muscle Forces exist for subject 9")

