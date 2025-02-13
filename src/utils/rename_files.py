import os

folder = r"C:\Git\research_data\Projects\runbops_FAIS_phd\simulations"

rename_file = False
rename_folder = True

if rename_file == rename_folder:
    raise ValueError("Please select either rename_file or rename_folder")

file_mapping = {
    'Segmentation_bg_r_femur.stl': 'Segmentation_l_femur.stl',
    'Segmentation_bg_r_femur.stl': 'Segmentation_r_femur.stl',
    'Segmentation_bg_l_pelvis.stl': 'Segmentation_l_pelvis.stl',
    'Segmentation_bg_r_pelvis.stl': 'Segmentation_r_pelvis.stl',
    'Segmentation_bg_l_femur_cartilage.stl': 'Segmentation_l_femur_cartilage.stl',
    'Segmentation_bg_r_femur_cartilage.stl': 'Segmentation_r_femur_cartilage.stl',
    
    'Segmentation_bas_l_femur.stl': 'Segmentation_l_femur.stl',
    'Segmentation_bas_r_femur.stl': 'Segmentation_r_femur.stl',
    'Segmentation_bas_l_pelvis.stl': 'Segmentation_l_pelvis.stl',
    'Segmentation_bas_r_pelvis.stl': 'Segmentation_r_pelvis.stl',   
    'Segmentation_bas_l_femur_cartilage.stl': 'Segmentation_l_pelvis_cartilage.stl',
    'Segmentation_bas_r_femur_cartilage.stl': 'Segmentation_r_pelvis_cartilage.stl',
    
}

folder_mapping = {'Run_baselineA1': 'sprint_1',
                  'Run_baseline1': 'sprint_1',
                  'Run_baselineA2': 'sprint_2',}


if rename_file:
    # loop through all files in the folder and subfolders
    for root, dirs, files in os.walk(folder):
        for file in files:
            if any(substring in file for substring in file_mapping.keys()):
                print(file)
                new_file = file_mapping[file]
                print(os.path.join(root, file))
                
                os.rename(os.path.join(root, file), os.path.join(root, new_file))
                print(f"Renamed {file} to {new_file}")

elif rename_folder:
    for root, dirs, files in os.walk(folder):
        for dir in dirs:
            if any(substring in dir for substring in file_mapping.keys()):
                print(dir)
                new_dir = file_mapping[dir]
                print(os.path.join(root, dir))
                
                os.rename(os.path.join(root, dir), os.path.join(root, new_dir))
                print(f"Renamed {dir} to {new_dir}")    
