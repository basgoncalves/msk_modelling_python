import msk_modelling_python as msk    

project_path = r'C:\Git\python-envs\msk_modelling\Lib\site-packages\msk_modelling_python\example_data\ischemia_amin'

# Project = msk.bops.StartProject(project_folder=project_path)
# Project.add_template_subject()

bopd_settings = msk.bops.get_bops_settings()

project_paths = msk.bops.ProjectPaths(project_path)