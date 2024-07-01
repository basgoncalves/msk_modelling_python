# # %% use this to test functions before inputing them into bops or other modules
# from bops import *
# import bops as bp
# try:
#     import ceinms_setup as cs
# except ModuleNotFoundError:
#     print('ModuleNotFoundError: ceinms_setup not found')
# import bops as bp

# trcFilePath = r"C:\Users\Bas\ucloud\FAIS_data_PhD\Simulations\009\pre\inverseKinematics\Run_baseline1\IK.mot"
# trc_data, trc_dataframe = bp.import_trc_file(trcFilePath)


import pydicom
from scipy import ndimage

# Load the DICOM file
dataset = pydicom.dcmread(r"E:\DataFolder\Running_FAI\MRI\009\DICOMDIR")

# Original in-plane dimensions
original_rows, original_columns = dataset.Rows, dataset.Columns

# New desired in-plane dimensions (adjust as needed)
new_rows, new_columns = 768, 785

# Rescale using linear interpolation (adjust interpolation method if needed)
rescaled_data = pydicom.pixel_data_handlers.numpy.apply_windowing(dataset.pixel_array, dataset.WindowCenter, dataset.WindowWidth)  # Convert to NumPy array
rescaled_data = ndimage.resample(rescaled_data, (new_rows, new_columns), interpolation="linear")  # Resample with interpolation

# Update dataset with rescaled data and potentially adjusted spacing values
dataset.PixelArray = pydicom.pixel_data_handlers.numpy.ToPyDicomArray(rescaled_data)
# Depending on the library, you might need to adjust the spacing values to reflect the new in-plane dimensions

# Save the rescaled DICOM file
dataset.saveas(r"E:\DataFolder\Running_FAI\MRI\009\DICOMDIR_rescaled.dcm")