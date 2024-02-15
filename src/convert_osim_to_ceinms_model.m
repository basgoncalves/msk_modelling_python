
ID = 'Athlete03';
osim_file_path = 'C:\Users\Bas\Desktop\AlexP\Catelli-V4.0.osim';
dofListCell = split('hip_flexion_r hip_adduction_r hip_rotation_r knee_angle_r ankle_angle_r',' ');
output_uncal_subject_file_path = 'C:\Users\Bas\Desktop\AlexP\ceinms_test\ceinms_shared\ceinms_uncalibrated_subject_MATLAB.xml';
template_uncal_subject_file_path = 'C:\Users\Bas\Desktop\AlexP\ceinms_test\ceinms_shared\ceinms_uncalibrated_subject.xml';
convertOsimToSubjectXml(ID,osim_file_path,dofListCell,output_uncal_subject_file_path, template_uncal_subject_file_path)


