# %%
from bops import *
import ceinms_setup as cs   
import bops as bp
import plotting as pltc
from test import plot_coordinates_api


data_folder = cs.get_main_path()

subject_name = 'Athlete_03'
trial_name = 'sq_90'
paths = cs.subject_paths(data_folder, subject_name, trial_name)

file_path = paths.so_output_forces
model_path = paths.model_scaled
muscles_r = get_muscles_by_group_osim(model_path,['right_leg'])
columns_to_plot = muscles_r['all_selected']
title = 'SO_athlete_03'
save_path = os.path.join(paths.trial,'results' , title + '.png')


fig  = plot_line_df(file_path, sep_subplots = False, columns_to_plot=columns_to_plot,
                xlabel='Frames',ylabel='Force(N)', legend='',save_path=save_path, title=title)
plt.show()
ax.legend(ncol=2)

print('Done')

# END 