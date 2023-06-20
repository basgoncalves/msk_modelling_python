from bops import *
import bops as bp 

c3dFilePath = bp.get_testing_file_path('c3d')
itf = c3d.c3dserver(msg=False)
c3d.open_c3d(itf, c3dFilePath)
analog_dict = c3d.get_dict_analogs(itf)

analog_df = pd.DataFrame()
for iLab in analog_dict['LABELS']:
    iData = analog_dict['DATA'][iLab]
    analog_df[iLab] = iData.tolist()

print('\n'.join(analog_dict.keys()))
print(analog_dict['LABELS'])

