folder = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage"


file_mapping = {
    'Segmentation_bg_l_femur.stl': 'Segmentation_l_femur.stl',
    'Segmentation_bg_ r_femur.stl': 'Segmentation_r_femur.stl',
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

# loop through all files in the folder and subfolders
for root, dirs, files in os.walk(folder):
    for file in files:
        if any(substring in file for substring in file_mapping.keys()):
            print(file)
            new_file = file_mapping[file]
            print(os.path.join(root, file))
            
            os.rename(os.path.join(root, file), os.path.join(root, new_file))
            print(f"Renamed {file} to {new_file}")
    
