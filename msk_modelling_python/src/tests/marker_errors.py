import msk_modelling_python as msk

trial_path = r"C:\Git\research_documents\students\marcel_BSc_vienna\sumo_dl_80kg00"

ik_markers = msk.os.path.join(trial_path, '_ik_model_marker_locations.sto')
exp_markers = msk.os.path.join(trial_path, 'markers_experimental.trc')

ik_markers_df = msk.bops.import_file(ik_markers)
exp_markers_df = msk.bops.pd.read_csv(exp_markers, sep='\t', skiprows=7)
print(ik_markers_df.head()) 
print(exp_markers_df.head())

print('Script completed successfully!')
# END