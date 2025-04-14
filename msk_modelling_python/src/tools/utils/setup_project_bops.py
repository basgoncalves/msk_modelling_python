import msk_modelling_python as msk    

project_path = r'C:\Git\research_data\Projects\leon_openCap\Squat_Opencap'

# Project = msk.bops.StartProject(project_folder=project_path)
# Project.add_template_subject()

# bopd_settings = msk.bops.get_bops_settings()

project_paths = msk.bops.ProjectPaths(project_path)
print(project_paths.subject_list)

# c3d_path = r"C:\Git\research_data\Projects\leon_openCap\Squat_Opencap\pilot_04\squat_01.c3d"
# msk.bops.c3d_osim_export_multiple(c3d_path)

msk.ut.files_above_100mb.run()