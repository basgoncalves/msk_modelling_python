from bops import *
import bops as bp
import ceinms_setup as cs
import plotting as pltc
from bops import save_fig

paths = cs.subject_paths(cs.get_main_path(), 'Athlete_03', 'sq_90')
model_path = paths.model_scaled
muscle_force_sto = os.path.join(paths.so_output_forces)
muscle_length_sto = os.path.join(paths.ma_output_folder,'_MuscleAnalysis_Length.sto')  

