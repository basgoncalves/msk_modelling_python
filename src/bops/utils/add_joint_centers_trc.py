import msk_modelling_python as msk


trc_file_path = r"C:\Git\research_documents\students\marcel_BSc_vienna\data\pilot01\static_00\static_00.trc"
pelvis_markers = ['RASI', 'LASI', 'LSACR', 'RSACR']
l_knee_markers = ['LMMAL', 'LLMAL']
r_knee_markers = ['RMMAL', 'RLMAL']

def harrington_hjc(trc_df, lasis = 'LASI', rasis = 'RASI', lpsis = 'LPSIS', rpsis = 'RPSIS'):
    ''' 
    Calculate the hip joint center using the Harrington method
    https://simtk-confluence.stanford.edu:8443/display/OpenSim/Harrington+Hip+Joint+Center
    Harrington, M. E., Zavatsky, A. B., Lawson, S. E., Yuan, Z., & Theologis, T. N. (2007). 
    Prediction of the hip joint centre in adults, children, and patients with cerebral palsy based on 
    magnetic resonance imaging. Journal of biomechanics, 40(3), 595-602.
    
    INPUTS: trc_df: pandas DataFrame with the marker data
            lasis, rasis, lpsis, rpsis: strings with the names of the markers for the pelvis

    
    Calculation:     
    x = -0.24PD - 9.9
    y = -30PW - 10.9
    z = 0.33PW + 7.3
    
    OUTPUTS: 
    
    '''
        
    pelvis_depth = msk.src.np.mean(trc_df[lasis] - trc_df[lpsis])
    pelvis_width = msk.src.np.mean(trc_df[lpsis] - trc_df[rpsis])

    # Create a new column to store the differences
    r_asi = msk.src.np.array(trc_df[lasis])
    pelvis_depth = [msk.src.np.array(lasi) - msk.src.np.array(lsacr) for lasi, lsacr in zip(trc_df[lasis], trc_df[lpsis])]
    np = msk.src.np
    import pdb; pdb.set_trace()
    x = np.array([1, 2, 3, 5, 6])
    y = np.array([1, 2, 3, 5, 6])
    z = np.array([1, 2, 3, 5, 6])
    coordinates = np.vstack((x, y, z)).T
    pd = msk.src.pd
    data = {'x': x, 'y': y, 'z': z}
    df = pd.DataFrame(data)

if not msk.os.path.isfile(trc_file_path):
    trc_file_path = msk.ui.select_file('Select the TRC file to import')

# import pdb; pdb.set_trace()
trc_dict, trc_df = msk.bops.import_trc_file(trc_file_path)

if not all(marker in trc_df.columns for marker in pelvis_markers):
    msk.log_error('Pelvis markers not found in TRC file')
else:
            
    print('Pelvis markers found in TRC file')

import pdb; pdb.set_trace()
print(trc_df.head())


print('Script completed successfully!')
# END