
from bops import *
import bops as bp
import ceinms_setup as cs
from plotting import plot_ceinms as pltc
from results_isbs2024 import get_personlised_label



data_folder = cs.get_main_path()
project_settings = bp.create_project_settings(data_folder)
subject_list = project_settings['subject_list']
subject_list = ['Athlete_03','Athlete_06','Athlete_22']
trial_list = ['sq_70','sq_90']

for subject_name in subject_list:
    for trial_name in trial_list:

        if subject_name.endswith('_torsion'):
            continue

        
        cs.print_terminal_spaced('Plotting JRA: ' + subject_name + ' ' + trial_name)
        cs.print_to_log_file('\n Plotting JRA: ' + subject_name + ' ' + trial_name)

        try:
            compare_jra_trials_torsion(subject_name,trial_name)
            cs.print_to_log_file('                compared jra time series ')

            compare_jra_angles(subject_name,trial_name)
            cs.print_to_log_file('                compared jra angles ')

            create_summary_table(subject_name,trial_name)
            cs.print_to_log_file('                summary completed ')
        except Exception as e:
            
            cs.print_to_log_file('Error processing: ' + subject_name + ' ' + trial_name)
            cs.print_to_log_file(str(e))    



