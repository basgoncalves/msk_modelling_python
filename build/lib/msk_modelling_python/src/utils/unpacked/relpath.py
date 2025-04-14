import os

# Example usage
path1 = r'C:\OpenSim 4.3\Resources\Models\Rajagopal_2015_FullBodyModel-4.0\Geometry'
path2 = r'C:\Git\research_data\Project_achiles_tendinopathy_AP\Models\Rajagopal2015_Nante.osim'
relpath = os.path.relpath(path1,path2)
print(relpath)