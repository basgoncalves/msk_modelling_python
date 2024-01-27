import os
import bops


main_dir = r'Z:\GaitRetraining\MonteCarlo'
data_dir = os.path.join(main_dir, 'TD10_Data')

model_path = os.path.join(main_dir, 'Model', 'defModel_scaled.osim')
marker_weights_path = os.path.join(main_dir, 'marker_weights.xml')

# get_marker_weight_from_model(model_path,marker_weights_path)

trial_list = [f.name for f in os.scandir(data_dir) if f.is_dir()]
trial_list = [s for s in trial_list if 'static' not in s]


for trial in trial_list:
    # file directories
    trialDir = os.path.join(data_dir, trial)
    trc_file = os.path.join(trialDir, 'marker_experimental.trc')
    grf_file = os.path.join(trialDir, 'grf.mot')
    grf_xml = os.path.join(trialDir, 'GRF.xml')
    c3dpath = os.path.join(trialDir, 'c3dfile.c3d')
    mot_file = os.path.join(trialDir, 'ik.mot')

    resultsDir = trialDir

    print(trialDir)
    # c3dExport(c3dpath)
    
    bops.run_IK(model_path,trc_file,resultsDir,marker_weights_path)
    
    try:
        # run_ID(model_path,mot_file,grf_xml,resultsDir)
        bops.run_MA(model_path, mot_file, grf_xml, os.path.join(resultsDir, 'ma_results'))
    except:
        print('didn''t work')
