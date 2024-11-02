# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021):
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

from msk_modelling_python.src.bops import *



#%% ######################################################  import / save data  #########################################################
def import_file(file_path):
    df = pd.DataFrame()
    if os.path.isfile(file_path):
        file_extension = os.path.splitext(file_path)[1]
        if file_extension.lower() == ".c3d":
            c3d_dict = import_c3d_to_dict(file_path)
            df =  pd.DataFrame(c3d_dict.items())
                    
        elif file_extension.lower() == ".sto":
            df = import_sto_data(file_path)
            
        elif file_extension.lower() == ".trc":
            import_trc_file(file_path)
            
        elif file_extension.lower() == ".csv":
            df = pd.read_csv(file_path)
        
        else:
            print('file extension does not match any of the bops options')
            
    else:
        print('file path does not exist!')
        
    return df

def import_c3d_to_dict(c3dFilePath):

    c3d_dict = dict()
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)

    c3d_dict['FilePath'] = c3dFilePath
    c3d_dict['DataRate'] = c3d.get_video_fps(itf)
    c3d_dict['CameraRate'] = c3d.get_video_fps(itf)
    c3d_dict["OrigDataRate"] = c3d.get_video_fps(itf)
    c3d_dict["OrigAnalogRate"] = c3d.get_analog_fps(itf)
    c3d_dict["OrigDataStartFrame"] = 0
    c3d_dict["OrigDataLAstFrame"] = c3d.get_last_frame(itf)

    c3d_dict["NumFrames"] = c3d.get_num_frames(itf)
    c3d_dict["OrigNumFrames"] = c3d.get_num_frames(itf)

    c3d_dict['MarkerNames'] = c3d.get_marker_names(itf)
    c3d_dict['NumMarkers'] = len(c3d_dict['MarkerNames'] )

    c3d_dict['Labels'] = c3d.get_marker_names(itf)

    c3d_dict['TimeStamps'] = c3d.get_video_times(itf)

    c3d_data = c3d.get_dict_markers(itf)
    my_dict = c3d_data['DATA']['POS']
    c3d_dict["Data"] = np.empty(shape=(c3d_dict["NumMarkers"], c3d_dict["NumFrames"], 3), dtype=np.float32)
    for i, label in enumerate(my_dict):
        c3d_dict["Data"][i] = my_dict[label]

    return c3d_dict

def import_sto_data(stoFilePath, headings_to_select='all'):
    if not os.path.exists(stoFilePath):
        print('file do not exists')

    file_id = open(stoFilePath, 'r')

    if os.path.getsize(stoFilePath) == 0:
        print(stoFilePath + ' is empty') 
        return pd.DataFrame()
    
    # read header
    next_line = file_id.readline()
    header = [next_line]
    nc = 0
    nr = 0
    while not 'endheader' in next_line:
        if 'datacolumns' in next_line:
            nc = int(next_line[next_line.index(' ') + 1:len(next_line)])
        elif 'datarows' in next_line:
            nr = int(next_line[next_line.index(' ') + 1:len(next_line)])
        elif 'nColumns' in next_line:
            nc = int(next_line[next_line.index('=') + 1:len(next_line)])
        elif 'nRows' in next_line:
            nr = int(next_line[next_line.index('=') + 1:len(next_line)])

        next_line = file_id.readline()
        header.append(next_line)

    # process column labels
    next_line = file_id.readline()
    if next_line.isspace() == True:
        next_line = file_id.readline()

    labels = next_line.split()

    # get data
    data = []
    for i in range(1, nr + 1):
        d = [float(x) for x in file_id.readline().split()]
        data.append(d)

    file_id.close()
    
    # Create a Pandas DataFrame
    df = pd.DataFrame(data, columns=labels)

    # Select specific columns if headings_to_select is provided
    if headings_to_select and headings_to_select != 'all':
        selected_headings = [heading for heading in headings_to_select if heading in df.columns]
        
        if not selected_headings == headings_to_select:
            print('Some headings were not found in the .sto file')
            different_strings = [item for item in headings_to_select + selected_headings 
                                 if item not in headings_to_select or item not in selected_headings]
            print(different_strings)

        df = df[selected_headings]

    return df

def import_c3d_analog_data(c3dFilePath):
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)
    analog_dict = c3d.get_dict_analogs(itf)
    analog_df = pd.DataFrame()
    # analog_df['time'] = c3d.get_video_times(itf)
    
    for iLab in analog_dict['LABELS']:
        iData = analog_dict['DATA'][iLab]
        analog_df[iLab] = iData.tolist()
    
    return analog_df

def import_trc_file(trcFilePath):
    trc_data = TRCData()
    trc_data.load(trcFilePath)
    
    # convert data to DataFrame 
    data_dict = {}
    headers = list(trc_data.keys())
    
    # only include columns from "Time" to "Markers" (i.e. labeled markers)
    data = list(trc_data.values())[headers.index('Time'):headers.index('Markers')-1]
    headers = headers[headers.index('Time'):headers.index('Markers')-1]
    
    for col_idx in range(1,len(data)):
        col_name = headers[col_idx]
        col_data = data[col_idx]
        data_dict[col_name] = col_data

    # convert data to DataFrame 
    trc_dataframe = pd.DataFrame(data_dict)
    trc_dataframe.to_csv(os.path.join(os.path.dirname(trcFilePath),'test.csv'))
    
    return trc_data, trc_dataframe

def import_json_file(jsonFilePath):
    with open(jsonFilePath, 'r') as f:
        data = json.load(f)
    return data

def save_json_file(data, jsonFilePath):
    if type(data) == subject_paths: # convert to dictionary
        data = data.__dict__

    with open(jsonFilePath, 'w') as f:
        json.dump(data, f, indent=4)

def c3d_osim_export(c3dFilePath):
    
    trialFolder = create_trial_folder(c3dFilePath)
    
    # create a copy of c3d file 
    shutil.copyfile(c3dFilePath, os.path.join(trialFolder,'c3dfile.c3d'))

    # import c3d file data to a table
    adapter = osim.C3DFileAdapter()
    tables = adapter.read(c3dFilePath)

    # save marker .mot
    try:
        markers = adapter.getMarkersTable(tables)
        markersFlat = markers.flatten()
        markersFilename = os.path.join(trialFolder,'markers.trc')
        stoAdapter = osim.STOFileAdapter()
        stoAdapter.write(markersFlat, markersFilename)
    except:
        print(c3dFilePath + ' could not export markers.trc')

    # save grf .sto
    try:
        forces = adapter.getForcesTable(tables)
        forcesFlat = forces.flatten()
        forcesFilename = os.path.join(trialFolder,'grf.mot')
        stoAdapter = osim.STOFileAdapter()
        stoAdapter.write(forcesFlat, forcesFilename)
    except:
        print(c3dFilePath + 'could not export grf.mot')

    # save emg.csv
    try:
       c3d_emg_export(c3dFilePath)
    except:
        print(c3dFilePath + 'could not export emg.mot')

def c3d_osim_export_multiple(sessionPath='',replace=0):

    if not sessionPath:
        sessionPath = select_folder('Select session folder',get_dir_simulations())

    if not get_trial_list(sessionPath):
        add_each_c3d_to_own_folder(sessionPath)

    trial_list = get_trial_list(sessionPath)
    print('c3d convert ' + sessionPath)
    for trial in trial_list:
        trial_folder = os.path.join(sessionPath, trial)
        c3dpath = os.path.join(trial_folder, 'c3dfile.c3d')
        trcpath = os.path.join(trial_folder, 'markers.trc')
        motpath = os.path.join(trial_folder, 'grf.sto')

        if not os.path.isfile(c3dpath) or not os.path.isfile(trcpath) or not os.path.isfile(motpath):
            try:
                c3d_osim_export(c3dpath)
                print(trial + 'c3d exported')
            except:
                print('could not convert ' + trial + ' to markers, grf, or emg')

        # if not os.path.isfile(emgpath):
        #     try:
        #         c3d_emg_export(c3dpath,emg_labels)
        #     except:
        #         print('could not convert ' + c3dpath + ' to emg.csv')

def c3d_emg_export(c3dFilePath,emg_labels='all'):

    trialFolder = create_trial_folder(c3dFilePath)
    
    itf = c3d.c3dserver(msg=False)   # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    c3d.open_c3d(itf, c3dFilePath)   # Open a C3D file

    # For the information of all analogs(excluding or including forces/moments)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']

    # if no emg_labels are given export all analog labels
    if emg_labels == 'all':
        emg_labels = analog_labels

    # Initialize the final dataframe
    analog_df = pd.DataFrame()

    # Store each of the vectors in dict_analogs as a columns in the final dataframe
    for iLab in analog_labels:
        if iLab in emg_labels:
            iData = dict_analogs['DATA'][iLab]
            analog_df[iLab] = iData.tolist()
    
    # Sava data in parent directory
    emg_filename = os.path.join(trialFolder,'emg.csv')
    analog_df.to_csv(emg_filename, index=False)

def selec_analog_labels (c3dFilePath):
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver(msg=False)
    c3d.open_c3d(itf, c3dFilePath)
    dict_analogs = c3d.get_dict_analogs(itf)
    analog_labels = dict_analogs['LABELS']

    print(analog_labels)
    print(type(analog_labels))

def read_trc_file(trcFilePath):
    pass

def writeTRC(c3dFilePath, trcFilePath):

    print('writing trc file ...')
    c3d_dict = import_c3d_to_dict (c3dFilePath)

    with open(trcFilePath, 'w') as file:
        # from https://github.com/IISCI/c3d_2_trc/blob/master/extractMarkers.py
        # Write header
        file.write("PathFileType\t4\t(X/Y/Z)\toutput.trc\n")
        file.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        file.write("%d\t%d\t%d\t%d\tmm\t%d\t%d\t%d\n" % (c3d_dict["DataRate"], c3d_dict["CameraRate"], c3d_dict["NumFrames"],
                                                        c3d_dict["NumMarkers"], c3d_dict["OrigDataRate"],
                                                        c3d_dict["OrigDataStartFrame"], c3d_dict["OrigNumFrames"]))

        # Write labels
        file.write("Frame#\tTime\t")
        for i, label in enumerate(c3d_dict["Labels"]):
            if i != 0:
                file.write("\t")
            file.write("\t\t%s" % (label))
        file.write("\n")
        file.write("\t")
        for i in range(len(c3d_dict["Labels"]*3)):
            file.write("\t%c%d" % (chr(ord('X')+(i%3)), math.ceil((i+3)/3)))
        file.write("\n")

        # Write data
        for i in range(len(c3d_dict["Data"][0])):
            file.write("%d\t%f" % (i, c3d_dict["TimeStamps"][i]))
            for l in range(len(c3d_dict["Data"])):
                file.write("\t%f\t%f\t%f" % tuple(c3d_dict["Data"][l][i]))
            file.write("\n")

        print('trc file saved')

# sto functions

def write_sto_file(dataframe, file_path): # not working yet
    # Add header information
    header = [
        'CEINMS output',
        f'datacolumns {len(dataframe.columns)}',
        f'datarows {len(dataframe)}',
        'endheader'
    ]

    # Create a DataFrame with the header information
    header_df = pd.DataFrame([header], columns=['CEINMS output'])

    # Concatenate the header DataFrame with the original DataFrame
    output_df = pd.concat([header_df, dataframe], ignore_index=True)

    # Write the resulting DataFrame to the specified file
    output_df.to_csv(file_path, index=False, header=False)


# XML functions
def readXML(xml_file_path):
    import xml.etree.ElementTree as ET

    # Load XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Print the root element
    print("Root element:", root.tag)

    # Iterate through elements
    for element in root:
        print("Element:", element.tag)

    # Find specific elements
    target_element = root.find('target_element_name')
    if target_element is not None:
        print("Found target element:", target_element.tag)
        # Manipulate target_element as needed

    # Modify existing element attributes or text
    for element in root:
        if element.tag == 'target_element_name':
            element.set('attribute_name', 'new_attribute_value')
            element.text = 'new_text_value'

    # Add new elements
    new_element = ET.Element('new_element')
    new_element.text = 'new_element_text'
    root.append(new_element)

    return tree

def writeXML(tree,xml_file_path):    
    tree.write(xml_file_path)

def get_tag_xml(xml_file_path, tag_name):
    try:
        # Load the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        # Find the specified tag and return its value
        tag = root.find(f'.//{tag_name}')
        if tag is not None:
            tag_value = tag.text
            return tag_value
        else:
            return None  # Return None if the specified tag is not found

    except Exception as e:
        print(f"Error while processing the XML file: {e}")
        return None


# figure functions
def save_fig(fig, save_path):
    if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))

    fig.savefig(save_path)

    print('figure saved to: ' + save_path)


#%% #####################################################  Operations  ###################################################################
def selectOsimVersion():
    osim_folders = [folder for folder in os.listdir('C:/') if 'OpenSim' in folder]
    installed_versions = [folder.replace('OpenSim ', '') for folder in osim_folders]
    msg = 'These OpenSim versions are currently installed in "C:/", please select one'
    indx = inputList(msg, installed_versions)
    osim_version_bops = float(installed_versions[indx])

    bops = {
        'osimVersion': osim_version_bops,
        'directories': {
            'setupbopsXML': 'path/to/setupbops.xml'
        },
        'xmlPref': {
            'indent': '  '
        }
    }

    xml_write(bops['directories']['setupbopsXML'], bops, 'bops', bops['xmlPref'])

def inputList(prompt, options):
    print(prompt)
    for i, option in enumerate(options):
        print(f"{i+1}: {option}")
    while True:
        try:
            choice = int(input("Enter the number of the option you want: "))
            if choice < 1 or choice > len(options):
                raise ValueError()
            return choice-1
        except ValueError:
            print("Invalid choice. Please enter a number between 1 and ", len(options))

def xml_write(file, data, root_name, pref):
    root = ET.Element(root_name)
    dict_to_xml(data, root)
    tree = ET.ElementTree(root)
    tree.write(file, xml_declaration=True, encoding='UTF-8', method="xml", short_empty_elements=False, indent=pref['indent'])

def dict_to_xml(data, parent):
    for key, value in data.items():
        if isinstance(value, dict):
            dict_to_xml(value, ET.SubElement(parent, key))
        else:
            ET.SubElement(parent, key).text = str(value)

def add_each_c3d_to_own_folder(sessionPath):

    c3d_files = [file for file in os.listdir(sessionPath) if file.endswith(".c3d")]
    for file in c3d_files:
        fname = file.replace('.c3d', '')
        src = os.path.join(sessionPath, file)
        dst_folder = os.path.join(sessionPath, fname)

        # create a new folder
        try: os.mkdir(dst_folder)
        except: 'nothing'

        # copy file
        dst = os.path.join(dst_folder, 'c3dfile.c3d')
        shutil.copy(src, dst)

def emg_filter(c3d_dict=0, band_lowcut=30, band_highcut=400, lowcut=6, order=4):
    
    if isinstance(c3d_dict, dict):
        pass
    elif not c3d_dict:   # if no input value is given use example data
        c3dFilePath = get_testing_file_path('c3d')
        c3d_dict = import_c3d_to_dict (c3dFilePath)
    elif os.path.isfile(c3d_dict):
        try:
            c3dFilePath = c3d_dict
            c3d_dict = import_c3d_to_dict (c3d_dict)
        except:
            if not isinstance(c3d_dict, dict):
                raise TypeError('first argument "c3d_dict" should be type dict. Use "get_testing_file_path(''c3d'')" for example file')
            else:
                raise TypeError('"c3d_dict"  has the correct file type but something is wrong with the file and doesnt open')
    
    fs = c3d_dict['OrigAnalogRate']
    if fs < band_highcut * 2:
        band_highcut = fs / 2
        warnings.warn("High pass frequency was too high. Using 1/2 *  sampling frequnecy instead")
    
    analog_df = import_c3d_analog_data(c3d_dict['FilePath'])
    max_emg_list = []
    for col in analog_df.columns:
            max_rolling_average = np.max(pd.Series(analog_df[col]).rolling(200, min_periods=1).mean())
            max_emg_list.append(max_rolling_average)

    nyq = 0.5 * fs
    normal_cutoff  = lowcut / nyq
    b_low, a_low = sig.butter(order, normal_cutoff, btype='low',analog=False)

    low = band_lowcut / nyq
    high = band_highcut / nyq
    b_band, a_band = sig.butter(order, [low, high], btype='band')

    for col in analog_df.columns:
        raw_emg_signal = analog_df[col]
        bandpass_signal = sig.filtfilt(b_band, a_band, raw_emg_signal)
        detrend_signal = sig.detrend(bandpass_signal, type='linear')
        rectified_signal = np.abs(detrend_signal)
        linear_envelope = sig.filtfilt(b_low, a_low, rectified_signal)
        analog_df[col] = linear_envelope

    return analog_df

def filtering_force_plates(file_path='', cutoff_frequency=2, order=2, sampling_rate=1000, body_weight=''):
    if not body_weight:
        body_weight = 1 
    def normalize_bodyweight(data):
                normalized_data = [x  / body_weight for x in data]
                return normalized_data
            
    nyquist_frequency = 0.5 * sampling_rate
    Wn = cutoff_frequency / nyquist_frequency 
    b, a = sig.butter(order, Wn, btype='low', analog=False)
    
    if not file_path:
        file_path = os.path.join(get_dir_bops(), 'ExampleData/BMA-force-plate/CSV-Test/p1/cmj3.csv')
    
    if os.path.isfile(file_path):
        file_extension = os.path.splitext(file_path)[1]
        if file_extension.lower() == ".xlsx":
            data = pd.read_excel(file_path)
            fz=[]
            for i in range(1, data.shape[0]):
                fz.append(float(data.iloc[i,0])) 
            normalized_time = np.arange(len(data) - 1) / (len(data) - 2)
            fz_offset= fz - np.mean(fz)
            filtered_fz = sig.lfilter(b, a, fz_offset)
            plt.plot(normalized_time, normalize_bodyweight(filtered_fz), label='z values')
            plt.xlabel('Time (% of the task)')
            plt.ylabel('Force (% of body weight)')
            plt.legend()
            plt.grid(True)
            plt.title('Graph of force signal vs. time', fontsize=10)
            plt.show()

        elif file_extension.lower() == ".csv":
            data = pd.read_csv(file_path, sep=",",header=3)
            normalized_time = np.arange(len(data) - 1) / (len(data) - 2)
            fx1=[]
            fy1=[]
            fz1=[]
            fx2=[]
            fy2=[]
            fz2=[]
            fx3=[]
            fy3=[]
            fz3=[]
            fx4=[]
            fy4=[]
            fz4=[]
            fx5=[]
            fy5=[]
            fz5=[]
            data.fillna(0, inplace=True)
            for i in range(1, data.shape[0]):
                fx1.append(float(data.iloc[i,11]))  
                fy1.append(float(data.iloc[i,12]))  
                fz1.append(float(data.iloc[i,13]))  
                fx2.append(float(data.iloc[i,2]))  
                fy2.append(float(data.iloc[i,3]))  
                fz2.append(float(data.iloc[i,4]))
                fx3.append(float(data.iloc[i,36]))  
                fy3.append(float(data.iloc[i,37]))  
                fz3.append(float(data.iloc[i,38]))
                fx4.append(float(data.iloc[i,42]))  
                fy4.append(float(data.iloc[i,43]))  
                fz4.append(float(data.iloc[i,44]))
                fx5.append(float(data.iloc[i,48]))  
                fy5.append(float(data.iloc[i,49]))  
                fz5.append(float(data.iloc[i,50]))  


        #OFFSET
            list_fx = [fx1, fx2, fx3, fx4, fx5]
            list_fy = [fy1, fy2, fy3, fy4, fy5]
            list_fz = [fz1, fz2, fz3, fz4, fz5]
            mean_fx = [np.mean(lst) for lst in list_fx]
            mean_fy = [np.mean(lst) for lst in list_fy]
            mean_fz = [np.mean(lst) for lst in list_fz]
            fx_red = [[x - mean for x in lst] for lst, mean in zip(list_fx, mean_fx)]
            fy_red = [[x - mean for x in lst] for lst, mean in zip(list_fy, mean_fy)]
            fz_red = [[x - mean for x in lst] for lst, mean in zip(list_fz, mean_fz)]
            
            filtered_data_listx= []
            for data in fx_red:
                filtered_data_x = sig.lfilter(b, a, data)  
                filtered_data_listx.append(filtered_data_x)
            filtered_data_listy= []
            for data in fy_red:
                filtered_data_y = sig.lfilter(b, a, data)  
                filtered_data_listy.append(filtered_data_y)
            filtered_data_listz= []
            for data in fz_red:
                filtered_data_z = sig.lfilter(b, a, data)  
                filtered_data_listz.append(filtered_data_z)
            
            fig, axes = plt.subplots(3,1)
            axes[0].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listx)), label='x values')
            axes[1].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listy)), label='y values')
            axes[2].plot(normalized_time, normalize_bodyweight(sum(filtered_data_listz)), label='z values')
            axes[0].legend(loc='upper right')
            axes[1].legend(loc='upper right')
            axes[2].legend(loc='upper right')
            plt.xlabel('Time (% of the task)')
            axes[0].set_ylabel('Force (% of \nbody weight)')
            axes[1].set_ylabel('Force (% of \nbody weight)')
            axes[2].set_ylabel('Force (% of \nbody weight)')
            axes[0].set_title('Graph of force signal vs. time', fontsize=10)  
            axes[0].grid(True)
            axes[1].grid(True)
            axes[2].grid(True)
            plt.show()

        else:
            print('file extension does not match any of the bops options for filtering the force plates signal')
    else:
        print('file path does not exist!')

def time_normalise_df(df, fs=''):

    if not type(df) == pd.core.frame.DataFrame:
        raise Exception('Input must be a pandas DataFrame')
    
    if not fs:
        try:
            fs = 1/(df['time'][1]-df['time'][0])
        except  KeyError as e:
            raise Exception('Input DataFrame must contain a column named "time"')
    
    normalised_df = pd.DataFrame(columns=df.columns)

    for column in df.columns:
        normalised_df[column] = np.zeros(101)

        currentData = df[column]
        currentData = currentData[~np.isnan(currentData)]
        
        timeTrial = np.arange(0, len(currentData)/fs, 1/fs)        
        Tnorm = np.arange(0, timeTrial[-1], timeTrial[-1]/101)
        if len(Tnorm) == 102:
            Tnorm = Tnorm[:-1]
        normalised_df[column] = np.interp(Tnorm, timeTrial, currentData)
    
    return normalised_df

def normalise_df(df,value = 1):
    normlaised_df = df.copy()
    for column in normlaised_df.columns:
        if column != 'time':
            normlaised_df[column] = normlaised_df[column] / value

    return normlaised_df

def sum_similar_columns(df):
    # Sum columns with the same name except for one digit
    summed_df = pd.DataFrame()

    for col_name in df.columns:
        # Find the position of the last '_' in the column name
        last_underscore_index = col_name.rfind('_')
        leg = col_name[last_underscore_index + 1]
        muscle_name = col_name[:last_underscore_index-1]

        # Find all columns with similar names (e.g., 'glmax_r')
        similar_columns = [col for col in df.columns if 
                           col == col_name or (col.startswith(muscle_name) and col[-1] == leg)]
    
        summed_df = pd.concat([df[col_name].copy() for col_name in df.columns], axis=1)

        # Check if the muscle name is already in the new DataFrame
        if not muscle_name in summed_df.columns and len(similar_columns) > 1:    
            # Sum the selected columns and add to the new DataFrame
            summed_df[muscle_name] = df[similar_columns].sum(axis=1)
        

    return summed_df

def calculate_integral(df):
    # Calculate the integral over time for all columns
    integral_df = pd.DataFrame({'time': [1]})

    # create this to avoid fragmented df
#     integral_df = pd.DataFrame({
#     column: integrate.trapz(df[column], df['time']) for column in df.columns[1:]
# })

    if not 'time' in df.columns:
        raise Exception('Input DataFrame must contain a column named "time"')

    for column in df.columns[1:]:
        integral_values = integrate.trapz(df[column], df['time'])
        integral_df[column] = integral_values

    integral_df = sum_similar_columns(integral_df)
    return integral_df

def rotateAroundAxes(data, rotations, modelMarkers):

    if len(rotations) != len(rotations[0]*2) + 1:
        raise ValueError("Correct format is order of axes followed by two marker specifying each axis")

    for a, axis in enumerate(rotations[0]):

        markerName1 = rotations[1+a*2]
        markerName2 = rotations[1 + a*2 + 1]
        marker1 = data["Labels"].index(markerName1)
        marker2 = data["Labels"].index(markerName2)
        axisIdx = ord(axis) - ord('x')
        if (0<=axisIdx<=2) == False:
            raise ValueError("Axes can only be x y or z")

        origAxis = [0,0,0]
        origAxis[axisIdx] = 1
        if modelMarkers is not None:
            origAxis = modelMarkers[markerName1] - modelMarkers[markerName2]
            origAxis /= scipy.linalg.norm(origAxis)
        rotateAxis = data["Data"][marker1] - data["Data"][marker2]
        rotateAxis /= scipy.linalg.norm(rotateAxis, axis=1, keepdims=True)

        for i, rotAxis in enumerate(rotateAxis):
            angle = np.arccos(np.clip(np.dot(origAxis, rotAxis), -1.0, 1.0))
            r = Rotation.from_euler('y', -angle)
            data["Data"][:,i] = r.apply(data["Data"][:,i])


    return data

def calculate_jump_height_impulse(vert_grf,sample_rate):
    
    gravity = 9.81
    # Check if the variable is a NumPy array
    if isinstance(vert_grf, np.ndarray):
        print("Variable is a NumPy array")
    else:
        print("Variable is not a NumPy array")
    
    time = np.arange(0, len(vert_grf)/sample_rate, 1/sample_rate)

    # Select time interval of interest
    plt.plot(vert_grf)
    x = plt.ginput(n=1, show_clicks=True)
    plt.close()

    baseline = np.mean(vert_grf[:250])
    mass = baseline/gravity
        
    #find zeros on vGRF
    idx_zeros = vert_grf[vert_grf == 0]
    flight_time_sec = len(idx_zeros/sample_rate)/1000
        
    # find the end of jump index = first zero in vert_grf
    take_off_frame = np.where(vert_grf == 0)[0][0] 
        
    # find the start of jump index --> the start value is already in the file
    start_of_jump_frame = int(np.round(x[0][0]))
    
        # Calculate impulse of vertical GRF    
    vgrf_of_interest = vert_grf[start_of_jump_frame:take_off_frame]

    # Create the time vector
    time = np.arange(0, len(vgrf_of_interest)/sample_rate, 1/sample_rate)

    vertical_impulse_bw = mass * gravity * time[-1]
    vertical_impulse_grf = np.trapz(vgrf_of_interest, time)

    # subtract impulse BW
    vertical_impulse_net = vertical_impulse_grf - vertical_impulse_bw


    take_off_velocity = vertical_impulse_net / mass

    # Calculate jump height using impulse-momentum relationship (DOI: 10.1123/jab.27.3.207)
    jump_height = (take_off_velocity / 2 * gravity)
    jump_height = (take_off_velocity**2 / 2 * 9.81) /100   # devie by 100 to convert to m

    # calculate jump height from flight time
    jump_height_flight = 0.5 * 9.81 * (flight_time_sec / 2)**2   

    print('take off velocity = ' , take_off_velocity, 'm/s')
    print('cmj time = ' , time[-1], ' s')
    print('impulse = ', vertical_impulse_net, 'N.s')
    print('impulse jump height = ', jump_height, ' m')
    print('flight time jump height = ', jump_height_flight, ' m')
    
    return jump_height, vertical_impulse_net

def blandAltman(method1=[],method2=[]):
    # Generate example data
    if not method1:
        method1 = np.array([1.2, 2.4, 3.1, 4.5, 5.2, 6.7, 7.3, 8.1, 9.5, 10.2])
        method2 = np.array([1.1, 2.6, 3.3, 4.4, 5.3, 6.5, 7.4, 8.0, 9.4, 10.4])

    # Calculate the mean difference and the limits of agreement
    mean_diff = np.mean(method1 - method2)
    std_diff = np.std(method1 - method2, ddof=1)
    upper_limit = mean_diff + 1.96 * std_diff
    lower_limit = mean_diff - 1.96 * std_diff

    # Plot the Bland-Altman plot
    plt.scatter((method1 + method2) / 2, method1 - method2)
    plt.axhline(mean_diff, color='gray', linestyle='--')
    plt.axhline(upper_limit, color='gray', linestyle='--')
    plt.axhline(lower_limit, color='gray', linestyle='--')
    plt.xlabel('Mean of two methods')
    plt.ylabel('Difference between two methods')
    plt.title('Bland-Altman plot')
    plt.show()

    # Print the results
    print('Mean difference:', mean_diff)
    print('Standard deviation of difference:', std_diff)
    print('Upper limit of agreement:', upper_limit)
    print('Lower limit of agreement:', lower_limit)

def sum3d_vector(df, columns_to_sum = ['x','y','z'], new_column_name = 'sum'):
    df[new_column_name] = df[columns_to_sum].sum(axis=1)
    return df

#%% ############################################  Torsion Tool (to be complete)  ########################################################
def torsion_tool(): # to complete...
   pass


#%% #############################################  OpenSim setup (to be complete)  #######################################################


#%% ##############################################  OpenSim run (to be complete)  ############################################################
def scale_model(originalModelPath,targetModelPath,trcFilePath,setupScaleXML):
    osimModel = osim.Model(originalModelPath)                             
    state = osimModel.initSystem()
    
    readXML(setupScaleXML)
    
    
    command = f'opensim-cmd run-tool {setupScaleXML}'
    subprocess.run(command, shell=True)
    
    print('Osim model scaled and saved in ' + targetModelPath)
    print()

def run_IK(osim_modelPath, trc_file, resultsDir):

    # Load the TRC file
    tuple_data = import_trc_file(trc_file)
    df = pd.DataFrame.from_records(tuple_data, columns=[x[0] for x in tuple_data])
    column_names = [x[0] for x in tuple_data]
    if len(set(column_names)) != len(column_names):
        print("Error: Duplicate column names found.")
    # Load the model
    osimModel = osim.Model(osim_modelPath)                              
    state = osimModel.initSystem()

    # Define the time range for the analysis
    import pdb; pdb.set_trace()
    initialTime = TRCData.getIndependentColumn()
    finalTime = TRCData.getLastTime()

    # Create the inverse kinematics tool
    ikTool = osim.InverseKinematicsTool()
    ikTool.setModel(osimModel)
    ikTool.setStartTime(initialTime)
    ikTool.setEndTime(finalTime)
    ikTool.setMarkerDataFileName(trc_file)
    ikTool.setResultsDir(resultsDir)
    ikTool.set_accuracy(1e-6)
    ikTool.setOutputMotionFileName(os.path.join(resultsDir, "ik.mot"))

    # print setup
    ikTool.printToXML(os.path.join(resultsDir, "ik_setup.xml"))         

    # Run inverse kinematics
    print("running ik...")                                             
    ikTool.run()

def run_inverse_kinematics(model_file, marker_file, output_motion_file):
    # Load model and create an InverseKinematicsTool
    model = osim.Model(model_file)
    ik_tool = osim.InverseKinematicsTool()

    # Set the model for the InverseKinematicsTool
    ik_tool.setModel(model)

    # Set the marker data file for the InverseKinematicsTool
    ik_tool.setMarkerDataFileName(marker_file)

    # Specify output motion file
    ik_tool.setOutputMotionFileName(output_motion_file)

    # Save setup file
    ik_tool.printToXML('setup_ik.xml')

    # Run Inverse Kinematics
    ik_tool.run()

def run_ID(osim_modelPath, ik_results_file, mot_file, grf_xml, resultsDir):
        
    # Load the model
    osimModel = osim.Model(osim_modelPath)
    osimModel.initSystem()

    # Load the motion data and times
    motion = osim.Storage(ik_results_file)
    initialTime = round(motion.getFirstTime(),2)
    finalTime = round(motion.getLastTime(),2)   

    # Create the inverse kinematics tool
    idTool = osim.InverseDynamics()
    idTool.setModel(osimModel)
    idTool.setStartTime(initialTime)
    idTool.setEndTime(finalTime)

    
    idTool.printToXML(os.path.join(os.path.dirname(resultsDir), "id_setup2.xml"))

    
    trial_folder = os.path.dirname(ik_results_file)
    
    # edit XML file tags
    XML = readXML(os.path.join(os.path.dirname(resultsDir), "id_setup2.xml"))
    
    XML.find('.//InverseDynamics').insert(0,ET.Element('results_directory'))
    XML.find('.//results_directory').text = '.' + os.path.sep

    XML.find('.//InverseDynamics').insert(0,ET.Element('external_loads_file'))
    XML.find('.//external_loads_file').text = os.path.relpath(grf_xml, trial_folder)
    
    XML.find('.//InverseDynamics').insert(0,ET.Element('time_range'))
    XML.find('.//time_range').text = f'{initialTime} {finalTime}'

    XML.find('.//InverseDynamics').insert(0,ET.Element('coordinates_file'))
    XML.find('.//coordinates_file').text = os.path.relpath(ik_results_file, trial_folder)

    XML.find('.//InverseDynamics').insert(0,ET.Element('output_gen_force_file'))
    XML.find('.//output_gen_force_file').text = os.path.relpath(resultsDir, trial_folder)

    writeXML(XML, os.path.join(os.path.dirname(resultsDir), "id_setup2.xml"))
    idTool = osim.InverseDynamicsTool(os.path.join(os.path.dirname(resultsDir), "id_setup2.xml"))
    import pdb; pdb.set_trace()
    # Run inverse kinematics
    print("running id...")
    idTool.run()
    exit()
    # Create analysis tool
    analysisTool = osim.AnalyzeTool()
    analysisTool.setModel(osimModel)
    analysisTool.setModelFilename(osim_modelPath)
    analysisTool.setLowpassCutoffFrequency(6)
    analysisTool.setCoordinatesFileName(ik_results_file)
    analysisTool.setName('Inverse Dynamics')
    analysisTool.setMaximumNumberOfSteps(20000)
    analysisTool.setStartTime(initialTime)
    analysisTool.setFinalTime(finalTime)
    analysisTool.getAnalysisSet().cloneAndAppend(idTool)
    analysisTool.setResultsDir(os.path.dirname(resultsDir))
    analysisTool.setInitialTime(initialTime)
    analysisTool.setFinalTime(finalTime)
    analysisTool.setExternalLoadsFileName(grf_xml)
    analysisTool.setSolveForEquilibrium(False)
    analysisTool.setReplaceForceSet(False)
    analysisTool.setMaximumNumberOfSteps(20000)
    analysisTool.setOutputPrecision(8)
    analysisTool.setMaxDT(1)
    analysisTool.setMinDT(1e-008)
    analysisTool.setErrorTolerance(1e-005)
    analysisTool.removeControllerSetFromModel()
    

    # print setup
    import pdb; pdb.set_trace()
    
    # analysisTool.run()
    idTool.run()

def run_MA(osim_modelPath, ik_mot, grf_xml, resultsDir):
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)

    # Load the model
    model = osim.Model(osim_modelPath)
    model.initSystem()

    # Load the motion data
    motion = osim.Storage(ik_mot)

    # Create a MuscleAnalysis object
    muscleAnalysis = osim.MuscleAnalysis()
    muscleAnalysis.setModel(model)
    muscleAnalysis.setStartTime(motion.getFirstTime())
    muscleAnalysis.setEndTime(motion.getLastTime())

    # Create the muscle analysis tool
    maTool = osim.AnalyzeTool()
    maTool.setModel(model)
    maTool.setModelFilename(osim_modelPath)
    maTool.setLowpassCutoffFrequency(6)
    maTool.setCoordinatesFileName(ik_mot)
    maTool.setName('Muscle analysis')
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setStartTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.getAnalysisSet().cloneAndAppend(muscleAnalysis)
    maTool.setResultsDir(resultsDir)
    maTool.setInitialTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.setExternalLoadsFileName(grf_xml)
    maTool.setSolveForEquilibrium(False)
    maTool.setReplaceForceSet(False)
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setOutputPrecision(8)
    maTool.setMaxDT(1)
    maTool.setMinDT(1e-008)
    maTool.setErrorTolerance(1e-005)
    maTool.removeControllerSetFromModel()
    maTool.print(os.path.join(resultsDir, '..', 'ma_setup.xml'))

    # Reload analysis from xml
    maTool = osim.AnalyzeTool(os.path.join(resultsDir, '..', 'ma_setup.xml'))

    # Run the muscle analysis calculation
    maTool.run()

def run_SO(modelpath, trialpath, actuators_file_path):
    os.chdir(trialpath)

    # create directories
    results_directory = os.path.relpath(trialpath, trialpath)
    coordinates_file = os.path.join(trialpath, "IK.mot")
    modelpath_relative = os.path.relpath(modelpath, trialpath)

    # create a local copy of the actuator file path and update name
    actuators_file_path = os.path.relpath(actuators_file_path, trialpath)

    # start model
    OsimModel = osim.Model(modelpath_relative)

    # Get mot data to determine time range
    motData = osim.Storage(coordinates_file)

    # Get initial and intial time
    initial_time = motData.getFirstTime()
    final_time = motData.getLastTime()

    # Static Optimization
    so = osim.StaticOptimization()
    so.setName('StaticOptimization')
    so.setModel(OsimModel)

    # Set other parameters as needed
    so.setStartTime(initial_time)
    so.setEndTime(final_time)
    so.setMaxIterations(25)

    analyzeTool_SO = osimSetup.create_analysis_tool(coordinates_file,modelpath_relative,results_directory)
    analyzeTool_SO.getAnalysisSet().cloneAndAppend (so)
    analyzeTool_SO.getForceSetFiles().append(actuators_file_path)
    analyzeTool_SO.setReplaceForceSet(False)
    OsimModel.addAnalysis(so)

    analyzeTool_SO.printToXML(".\setup_so.xml")

    analyzeTool_SO = osim.AnalyzeTool(".\setup_so.xml")

    trial = os.path.basename(trialpath)
    print(f"so for {trial}")

    # run
    analyzeTool_SO.run()

def runJRA(modelpath, trialPath, setupFilePath):
    os.chdir(trialPath)
    results_directory = [trialPath]
    coordinates_file = [trialPath, 'IK.mot']
    _, trialName = os.path.split(trialPath)

    # start model
    osimModel = osim.Model(modelpath)

    # Get mot data to determine time range
    motData = osim.Storage(coordinates_file)

    # Get initial and intial time
    initial_time = motData.getFirstTime()
    final_time = motData.getLastTime()

    # start joint reaction analysis
    jr = osim.JointReaction(setupFilePath)
    jr.setName('joint reaction analysis')
    jr.set_model(osimModel)

    inFrame = osim.ArrayStr()
    onBody = osim.ArrayStr()
    jointNames = osim.ArrayStr()
    inFrame.set(0, 'child')
    onBody.set(0, 'child')
    jointNames.set(0, 'all')

    jr.setInFrame(inFrame)
    jr.setOnBody(onBody)
    jr.setJointNames(jointNames)

    # Set other parameters as needed
    jr.setStartTime(initial_time)
    jr.setEndTime(final_time)
    jr.setForcesFileName([results_directory, '_StaticOptimization_force.sto'])

    # add to analysis tool
    analyzeTool_JR = create_analysisTool(coordinates_file, modelpath, results_directory)
    analyzeTool_JR.get().AnalysisSet.cloneAndAppend(jr)
    osimModel.addAnalysis(jr)

    # save setup file and run
    analyzeTool_JR.print(['./setup_jra.xml'])
    analyzeTool_JR = AnalyzeTool(['./setup_jra.xml'])
    print('jra for', trialName)
    analyzeTool_JR.run()



# %% ##############################################  OpenSim operations (to be complete)  ############################################################
def sum_muscle_work(model_path, muscle_force_sto, muscle_length_sto, body_weight = 1):
    
    def sum_df_columns(df, groups = {}):
        # Function to sum columns of a dataframe based on a dictionary of groups
        # groups = {group_name: [column1, column2, column3]}
        summed_df = pd.DataFrame()

        if not groups:
            groups = {'all': df.columns}

        for group_name, group_columns in groups.items():
            group_sum = df[group_columns].sum(axis=1)
            summed_df[group_name] = group_sum

        return summed_df

    if not os.path.isfile(muscle_force_sto):
        print_terminal_spaced('File not found:', muscle_force_sto)
        return

    if not os.path.isfile(model_path):
        print_terminal_spaced('File not found:', model_path)
        return
    
    if not os.path.isfile(muscle_length_sto):
        print_terminal_spaced('File not found:', muscle_length_sto)
        return
    

    # muscle_work 
    muscle_work = calculate_muscle_work(muscle_length_sto,muscle_force_sto, save = False, save_path = None)
    muscle_work.to_csv(os.path.join(os.path.dirname(muscle_force_sto),'MuscleWork.csv'), index=False)
    
    # force curce normalise to weight and save as csv
    muscle_force = time_normalise_df(import_sto_data(muscle_force_sto))
    muscle_force_normalised_to_weight = normalise_df(muscle_force,body_weight)
    muscle_force_normalised_to_weight.to_csv(os.path.join(os.path.dirname(muscle_force_sto),'MuscleForces_normalised.csv'), index=False)

    # muscle work normalised to weight and save as csv
    muscle_work_normalised_to_weight = normalise_df(muscle_work,body_weight)
    muscle_work_normalised_to_weight.to_csv(os.path.join(os.path.dirname(muscle_force_sto),'MuscleWork_normalised.csv'), index=False)

    muscles_r_hip_flex = osimSetup.get_muscles_by_group_osim(model_path,['hip_flex_r','hip_add_r','hip_inrot_r'])
    muscles_r_hip_ext = osimSetup.get_muscles_by_group_osim(model_path,['hip_ext_r','hip_abd_r','hip_exrot_r'])
    muscles_r_knee_flex = osimSetup.get_muscles_by_group_osim(model_path,['knee_flex_r'])
    muscles_r_knee_ext = osimSetup.get_muscles_by_group_osim(model_path,['knee_ext_r'])
    muscles_r_ankle_df = osimSetup.get_muscles_by_group_osim(model_path,['ankle_df_r'])
    muscles_r_ankle_pf = osimSetup.get_muscles_by_group_osim(model_path,['ankle_pf_r'])

    muscles_l_hip_flex = osimSetup.get_muscles_by_group_osim(model_path,['hip_flex_l','hip_add_l','hip_inrot_l'])
    muscles_l_hip_ext = osimSetup.get_muscles_by_group_osim(model_path,['hip_ext_l','hip_abd_l','hip_exrot_l'])
    muscles_l_knee_flex = osimSetup.get_muscles_by_group_osim(model_path,['knee_flex_l'])
    muscles_l_knee_ext = osimSetup.get_muscles_by_group_osim(model_path,['knee_ext_l'])
    muscles_l_ankle_df = osimSetup.get_muscles_by_group_osim(model_path,['ankle_df_l'])
    muscles_l_ankle_pf = osimSetup.get_muscles_by_group_osim(model_path,['ankle_pf_l'])

    groups = {  'RightHipFlex': muscles_r_hip_flex['all_selected'],
                'RightHipExt': muscles_r_hip_ext['all_selected'],
                'RightKneeFlex': muscles_r_knee_flex['all_selected'],
                'RightKneeExt': muscles_r_knee_ext['all_selected'],
                'RightAnkleDF': muscles_r_ankle_df['all_selected'],
                'RightAnklePF': muscles_r_ankle_pf['all_selected'],
                'LeftHipFlex': muscles_l_hip_flex['all_selected'],
                'LeftHipExt': muscles_l_hip_ext['all_selected'],
                'LeftKneeFlex': muscles_l_knee_flex['all_selected'],
                'LeftKneeExt': muscles_l_knee_ext['all_selected'],
                'LeftAnkleDF': muscles_l_ankle_df['all_selected'],
                'LeftAnklePF': muscles_l_ankle_pf['all_selected']
    }
    # Perform grouping and summing for each group
    muscle_work_summed = sum_df_columns(muscle_work_normalised_to_weight,groups)
    # sum the work per group 
    muscle_work_summed= muscle_work_summed.sum(axis=0)
    return muscle_work_summed

def calculate_muscle_work(muscle_length_sto,muscle_force_sto, save = True, save_path = None):

    try:
        length = time_normalise_df(import_sto_data(muscle_length_sto))
        force = time_normalise_df(import_sto_data(muscle_force_sto))
    except:
        print('Error importing files')
        return
    
    work = pd.DataFrame()
    
    for muscle in length.columns:
        if muscle == 'time':
            work['time'] = length['time']
        elif muscle in force.columns:
            work_series = length[muscle] * force[muscle]
            work[muscle] = work_series.sum(axis=0) 
        else:
            print('Muscle', muscle, 'not found in forces')
    work = work.iloc[[0]]
    if save and not save_path:
        work.to_csv(os.path.join(os.path.dirname(muscle_force_sto),'results'),'muscle_work.csv')
        print('Data saved to', os.path.join(os.path.dirname(muscle_force_sto),'results'),'muscle_work.csv')
    elif save and save_path:
        work.to_csv(save_path)
        print('Data saved to', save_path)

    return work




if __name__ == '__main__':
    
    clear_terminal()
    uni_vie_print()
    
    def add_bops_to_python_path():        
        import os

        # Directory to be added to the path
        directory_to_add = get_dir_bops()

        # Get the site-packages directory
        site_packages_dir = os.path.dirname(os.path.dirname(os.__file__))
        custom_paths_file = os.path.join(site_packages_dir, 'custom_paths.pth')

        # Check if the custom_paths.pth file already exists
        if not os.path.exists(custom_paths_file):
            with open(custom_paths_file, 'w') as file:
                file.write(directory_to_add)
                print(f"Added '{directory_to_add}' to custom_paths.pth")
        else:
            with open(custom_paths_file, 'r') as file:
                paths = file.read().splitlines()
            if directory_to_add not in paths:
                with open(custom_paths_file, 'a') as file:
                    file.write('\n' + directory_to_add)
                    print(f"Added '{directory_to_add}' to custom_paths.pth")
            else:
                print(f"'{directory_to_add}' already exists in custom_paths.pth")

    add_bops_to_python_path()
    
    print('runnung all tests ...')
    output = unittest.main(exit=False)
    if output.result.errors or output.result.failures:
        print_sad_platypus()
    else:
        print('no errors')
        print_happy_platypus()
    
    
# end