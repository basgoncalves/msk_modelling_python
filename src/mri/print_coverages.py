import os

main_dir = r"C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage"

subjects = [entry for entry in os.listdir(main_dir) if os.path.isdir(os.path.join(main_dir, entry))]

legs = ['l', 'r']
thresholds = [25]  # distance threshold in mm
for subject in subjects:
    for leg in legs:
        current_results = f'{main_dir}\\{subject}\\Meshlab_BG\\femoral_head_{leg}_threshold_25\\femoral_head_{leg}.txt'
        try:
            with open(current_results, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.startswith('Normalized Area Covered: '):
                        numbers = line.split(':')[1].strip().split()
                        print(f"Numbers after 'Normalized Area Covered {subject}_{leg}_{numbers}")
        except FileNotFoundError:
            print(f"File {current_results} does not exist")
            continue