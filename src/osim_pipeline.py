from bops import bops as bp


print(bp.__version__)

pathfile = bp.osimSetup().print_osim_info()
print(pathfile)