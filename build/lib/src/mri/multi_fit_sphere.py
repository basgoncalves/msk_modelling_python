import fit_sphere as fs
import os
import tkinter as tk
from tkinter import messagebox
import pandas as pd

maindir = r'C:\Users\Bas\ucloud\MRI_segmentation_BG\acetabular_coverage'
all_subjects = [entry for entry in os.listdir(maindir) if os.path.isdir(os.path.join(maindir, entry))]
subjects_to_run = []

if not subjects_to_run:
    subjects_to_run = []

    def save_selected_subjects():
        for i, subject in enumerate(all_subjects):
            if checkboxes[i].get():
                subjects_to_run.append(subject)
        
        root.destroy()

    root = tk.Tk()
    root.title("Select Subjects")

    checkboxes = []
    columns = 3
    checkbox_state_path = os.path.join(maindir, "checkbox_state.txt")
    for i, subject in enumerate(all_subjects):
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(root, text=subject, variable=var)
        checkbox.grid(row=i // columns, column=i % columns)
        checkboxes.append(var)
        # Load saved checkbox state if available
        if os.path.exists(checkbox_state_path):
            with open(checkbox_state_path, "r") as f:
                saved_state = f.read().splitlines()
                if saved_state[i] == "1":
                    checkbox.select()

    def save_selected_subjects():
        for i, subject in enumerate(all_subjects):
            if checkboxes[i].get():
                subjects_to_run.append(subject)

        # Save checkbox state
        with open(checkbox_state_path, "w") as f:
            for checkbox in checkboxes:
                if checkbox.get():
                    f.write("1\n")
                else:
                    f.write("0\n")
        root.destroy()

    button = tk.Button(root, text="Save", command=save_selected_subjects)
    button.grid(row=0, column=columns)

    root.mainloop()

    if not subjects_to_run:
        print("No subjects selected.")
        exit()

print(f"Subjects to analyse: {subjects_to_run}")
df = pd.DataFrame(columns=['Subject', 'Right', 'Left'])

for subject in all_subjects:
    if subject not in subjects_to_run:
        continue
    else:
        new_row = pd.DataFrame({'Subject': [subject], 'Right': [None], 'Left': [None]})
    for leg in ['r', 'l']:
        path_stl = os.path.join(maindir, subject, 'Meshlab_BG', f'acetabulum_{leg}.stl')
        if not os.path.exists(path_stl):
            messagebox.showerror("Error", f"STL file not found for {subject} {leg}")
        covered_area = fs.fit_sphere_and_plot(path_stl)
        if leg == 'r':
            new_row['Right'] = covered_area
        elif leg == 'l':
            new_row['Left'] = covered_area
    df = pd.concat([df, new_row], ignore_index=True)
    print(f'Fitted sphere for {subject}')

df.to_csv(os.path.join(maindir, 'coverage_results.csv'), index=False)
