import os
import msk_modelling_python as msk
main_dir = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage'
subfolder_name = 'cartilage'

for folder in os.listdir(main_dir):
    
    folder_path = os.path.join(main_dir, folder)
    
    if not os.path.isdir(folder_path):
        continue
    else:
        sub_folder_path = os.path.join(folder_path, subfolder_name)
        print(sub_folder_path)
        msk.ut.create_folder(sub_folder_path)
       