
import os 


file_path1 = "python-envs/msk_modelling/Lib/site-packages/msk_modelling_python/src/tests/test.py"
file_path2 = "research_data/Projects/opensim-deadlift-techniques/python/main.py"
json_path = r"C:\Git\research_data\Projects\opensim-deadlift-techniques\athlete_1_increased_force_3\settings.json"


rel_path = os.path.relpath(file_path2, json_path)

print(rel_path)  # ../../research_data/Projects/opensim-deadlift-techniques/python/main.py