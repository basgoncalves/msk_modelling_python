
# to import bops need to deactivate some packages not intalled (offline mode, consider this when packaging)
import bops 

print(bops.get_project_folder())
# print(bops.select_folder())

bops.create_project_settings()