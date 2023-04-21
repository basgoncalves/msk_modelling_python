import bops as bp

c3dFilePath = bp.get_testing_file_path('c3d')
print(c3dFilePath)

bp.c3d_osim_export(c3dFilePath)