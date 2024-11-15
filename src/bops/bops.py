# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021):
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

__version__ = '0.0.3'
__testing__ = False

from msk_modelling_python.src.utils import general_utils as ut
from msk_modelling_python.src.bops import *
from msk_modelling_python.src.bops import ghost
from msk_modelling_python.src.classes import *
import msk_modelling_python as msk
from msk_modelling_python import osim

def update_version(level=3, module='', invert=False):
    try:
        if not module:
            module = __file__
        msk.update_version(level, module, invert)
    except Exception as e:
        print(f"Error updating version: {e}")
        
def is_setup_file(file_path, type = 'OpenSimDocument', print_output=False):
    
    is_setup = False
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if type in line:
                    is_setup = True
                    break
                
                #if is last line and no match, return false
                if line == None:
                    is_setup = False
                    
    except Exception as e:
        print(f"Error reading file: {e}")
    
    if print_output and is_setup:
        print(f"{file_path} is a setup file")
    elif print_output and not is_setup:
        print(f"{file_path} is not a setup file")
        
    return is_setup  
    

#%% ######################################################  General  #####################################################################
def select_file(original_path=''):
    if not original_path:
        original_path = os.getcwd()
    elif os.path.isfile(original_path):
        original_path = os.path.dirname
        
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    file_path = filedialog.askopenfilename(title="Select a file", initialdir=original_path)

    if file_path:
        pass
    else:
        raise ValueError('No file selected')    

    return file_path

def select_folder(prompt='Please select your folder', staring_path=''):
    if not staring_path: # if empty
        staring_path = os.getcwd()      

    selected_folder = filedialog.askdirectory(initialdir=staring_path,title=prompt)
    return selected_folder



def select_subjects():
   subject_names = get_subject_names()

def get_dir_bops():
    return os.path.dirname(os.path.realpath(__file__))

def get_dir_simulations():
    return os.path.join(get_current_project_folder(),'simulations')

def add_bops_to_python_path():        

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
        print(f"'{custom_paths_file}' already exists")
        
def get_subject_folders(dir_simulations = ''):
    if dir_simulations:
        return [f.path for f in os.scandir(dir_simulations) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]
    else:
        return [f.path for f in os.scandir(get_dir_simulations()) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]

def get_subject_names():
    subject_names = []
    for i_folder in get_subject_folders():
        subject_names.append(os.path.basename(os.path.normpath(i_folder)))
    return subject_names

def get_subjects_selected():
    return list(get_bops_settings()['subjects'].values())

def get_subject_sessions(subject_folder):
    return [f.path for f in os.scandir(subject_folder) if f.is_dir()] # (for all subdirectories) [x[0] for x in os.walk(dir_simulations())]

def get_trial_list(sessionPath='',full_dir=False):
    # get all the folders in sessionPath that contain c3dfile.c3d and are not "static" trials
    if not sessionPath:
        sessionPath = select_folder('Select session folder',get_dir_simulations())

    if full_dir:
        trial_list = [f.path for f in os.scandir(sessionPath) if f.is_dir()]
    else:
        trial_list = [f.name for f in os.scandir(sessionPath) if f.is_dir()]   

    return trial_list

# Project functions
def get_bops_settings():
    '''
    Function to get the settings from the bops directory. If the settings do not exist, it will create a new settings.json file in the project folder.
    
    '''
    
    # get settings from bops directory
    current_dir = os.path.dirname(os.path.realpath(__file__))   
    jsonfile = os.path.join(current_dir,'settings.json')

    # open settings.json (or create a new dictionary if it does not exist)
    try:   
        with open(jsonfile, 'r') as f:
            bops_settings = json.load(f)
        
        # update jsonfile path to ensure it is saved in the settings from new root           
        bops_settings['jsonfile'] = jsonfile 
        
    except Exception as e:
        ut.debug_print(jsonfile + ' could not be loaded')
        print(e)    
        print('Could not open settings.json. ') 
        print('Check path ' + jsonfile)
        
        bops_settings = None
        return bops_settings
           
    # check if all variables are in the settings [OPTIONAL]
    try:
        valid_vars = ['current_project_folder','subjects','emg_labels','analog_labels','filters']
        for var in valid_vars:
            if var not in bops_settings:
                bops_settings[var] = None
                print(f'{var} not in settings. File might be corrupted.')
    except:
        if msk.__testing__:
            print('Error checking settings variables')
            
    return bops_settings
    
def select_project(project_folder=''): 
    
    bops_settings = get_bops_settings()
       
    if not project_folder:
        project_folder = select_folder('Please select project directory')
        create_project_settings(project_folder)
    elif os.path.isdir(project_folder):    
        create_project_settings(project_folder=project_folder) # create new settings.json in the project folder
    else:
        print('project folder does not exist')
        project_folder = select_folder('Please select project directory')
        create_project_settings(project_folder)

    # if project folder is not the same as the one in settings, update settings
    if os.path.isdir(project_folder) and not bops_settings['current_project_folder'] == project_folder:
        bops_settings['current_project_folder'] = project_folder
        save_bops_settings(bops_settings)
        
        # open settings to return variable    
        with open(bops_settings.jsonfile, 'r') as f:
            bops_settings = json.load(f)
    
    bops_settings = get_bops_settings()
            
    return bops_settings

def save_bops_settings(settings):
    jsonpath = Path(get_dir_bops()) / ("settings.json")
    jsonpath.write_text(json.dumps(settings,indent=2))

def get_current_project_folder():

    bops_settings = get_bops_settings()
        
    project_folder = bops_settings['current_project_folder']
    project_json = os.path.join(project_folder,'settings.json')

    # if project settings.json does not exist, create one
    if not os.path.isfile(project_json):                                         
        create_project_settings(project_folder)

    return project_folder

def get_project_settings(project_folder=''):
    if not project_folder:
        try:
            project_folder = get_current_project_folder()
        except:
            project_folder = select_folder('Please select project directory')
    else:
        bops_settings = get_bops_settings(project_folder)
        
    
    json_file_path = os.path.join(project_folder,'settings.json')
    settings = import_json_file(json_file_path)    

    return settings

def get_trial_dirs(sessionPath, trialName):
       
    # get directories of all files for the trial name given 
    dirs = dict()
    dirs['c3d'] = os.path.join(sessionPath,trialName,'c3dfile.c3d')
    dirs['trc'] = os.path.join(sessionPath,trialName,'marker_experimental.trc')
    dirs['grf'] = os.path.join(sessionPath,trialName,'grf.mot')
    dirs['emg'] = os.path.join(sessionPath,trialName,'emg.csv')
    dirs['ik'] = os.path.join(sessionPath,trialName,'ik.mot')
    dirs['id'] = os.path.join(sessionPath,trialName,'inverse_dynamics.sto')
    dirs['so_force'] = os.path.join(sessionPath,trialName,'_StaticOptimization_force.sto')
    dirs['so_activation'] = os.path.join(sessionPath,trialName,'_StaticOptimization_activation.sto')
    dirs['jra'] = os.path.join(sessionPath,trialName,'_joint reaction analysis_ReactionLoads.sto')

    all_paths_exist = True
    for key in dirs:
        filename = os.path.basename(dirs[key])
        if all_paths_exist and not os.path.isfile(dirs[key]):                                        
            print(os.path.join(sessionPath))
            
            print(filename + ' does not exist')
            all_paths_exist = False
        elif not os.path.isfile(dirs[key]):
            print(filename + ' does not exist')
            
        
        
        
            
        
    return dirs

def select_new_project_folder():

    bops_settings = get_bops_settings()
    project_folder = select_folder('Please select project directory')
    project_json = os.path.join(project_folder,'settings.json')
    bops_settings['current_project_folder'] = project_folder

    jsonpath = Path(get_dir_bops()) / ("settings.json")
    jsonpath.write_text(json.dumps(bops_settings))

    if not os.path.isfile(project_json):                                         # if json does not exist, create one
        create_project_settings(project_folder)

    return project_folder

def create_new_project_folder(basedir = ''): # to complete

    if not basedir:
        basedir = select_folder('Select folder to create new project folder')

    ut.create_folder(os.path.join(basedir,'simulations'))
    ut.create_folder(os.path.join(basedir,'setupFiles'))
    ut.create_folder(os.path.join(basedir,'results'))
    ut.create_folder(os.path.join(basedir,'models'))

    print_warning('function not complete')

    project_settings = create_project_settings(basedir)
    import pdb; pdb.set_trace()
    for setting in project_settings:
        if is_potential_path(setting):
            print('folder is path: ' + setting)
            ut.create_folder(setting)
            print(setting)

    return project_settings

def create_project_settings(project_folder='', overwrite=False):

    if not project_folder or not os.path.isdir(project_folder):                                       
        project_folder = select_folder('Please select project directory')
    
    jsonpath = Path(project_folder) / ("settings.json")
    
    if os.path.isfile(jsonpath) and not overwrite:
        project_settings = get_project_settings(project_folder)
        print('settings.json already exists')
        return
    
    print('creating new project settings.json... \n \n')
    
    project = msk.bops.ProjectPaths(project_folder=project_folder)
    project.create_settings_json()

    print('project directory was set to: ' + project_folder)

    return project_settings

def create_trial_folder(c3dFilePath):
    trialName = os.path.splitext(c3dFilePath)[0]
    parentDirC3d = os.path.dirname(c3dFilePath)
    trialFolder = os.path.join(parentDirC3d, trialName)

    if not os.path.isdir(trialFolder):
        os.makedirs(trialFolder)
        
    return trialFolder 


# Testing functions and paths




#%% import / save data  
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
            df = pd.read_csv(file_path, sep='\t')
        
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
    
    try:
        with open(jsonFilePath, 'r') as f:
            data = json.load(f)
    except:
        print_warning('Error reading ' + jsonFilePath)
        data = dict()
        
    return data

def save_json_file(data, jsonFilePath):
    if type(data) == SubjectPaths: # convert to dictionary
        data = data.__dict__

    with open(jsonFilePath, 'w') as f:
        json.dump(data, f, indent=4)

    json_data = import_json_file(jsonFilePath)
    return json_data

#%% C3D export functions    
def c3d_osim_export(c3dFilePath, replace = True):
    
    trialFolder = create_trial_folder(c3dFilePath)
    
    # create a copy of c3d file 
    new_c3d_file = os.path.join(trialFolder,'c3dfile.c3d')
    shutil.copyfile(c3dFilePath, new_c3d_file)
    
    # upadate c3d file path
    c3dFilePath = new_c3d_file

    # save analog.csv
    try:
        settings = get_bops_settings()
        analog_df = c3d_analog_export(c3dFilePath)
        
    except Exception as e:
        ut.print_warning(c3dFilePath + 'could not export emg.mot')
        print(e)
        
    # import c3d file data to a table
    try:
        adapter = osim.C3DFileAdapter()
        tables = adapter.read(c3dFilePath)
    except Exception as e:
        ut.print_warning(c3dFilePath + ' could not be read')
        if msk.__testing__:
            print(e)

    # save markers.trc
    try:
        markers = adapter.getMarkersTable(tables)
        markersFlat = markers.flatten()
        markersFilename = os.path.join(trialFolder,'markers.trc')
        stoAdapter = osim.STOFileAdapter()
        
        if not os.path.isfile(markersFilename) or replace:
            stoAdapter.write(markersFlat, markersFilename)
        
        print('markers.trc exported to ' + trialFolder)
    except Exception as e:
        ut.print_warning(c3dFilePath + ' could not export markers.trc')
        if msk.__testing__:
            print(e)

    # save grf.mot
    try:
        forces = adapter.getForcesTable(tables)
        forcesFlat = forces.flatten()
        forcesFilename = os.path.join(trialFolder,'grf.mot')
        stoAdapter = osim.STOFileAdapter()
        
        if not os.path.isfile(forcesFilename) or replace:
            stoAdapter.write(forcesFlat, forcesFilename)
        
        # change heading names to match OpenSim
        array = forcesFlat.getMatrix().to_numpy()
        force_labels = forcesFlat.getColumnLabels()
        analog_labels = analog_df.columns
        
    except Exception as e:
        ut.print_warning(c3dFilePath + 'could not export grf.mot')
        if msk.__testing__:
            print(e)

    return force_labels

def c3d_osim_export_multiple(sessionPath='',replace=0):

    if not sessionPath:
        sessionPath = select_folder('Select session folder',get_dir_simulations())

    session = Session(sessionPath)
    print('c3d convert ' + sessionPath)
    for i_trial in session.trial_paths:
        trial = session.get_trial(i_trial)
        trial.exportC3D()
        print('c3d convert ' + trial.name)
        
def c3d_analog_export(c3dFilePath,emg_labels='all', replace = True):
    
    analog_file_path = os.path.join(os.path.dirname(c3dFilePath),'analog.csv')
    
    # if the file already exists, return the file
    if os.path.isfile(analog_file_path) and not replace:
        df = pd.read_csv(analog_file_path)
        print('analog.csv already exists. File not replaced.')
        return df
    
    print('Exporting analog data to csv ...')
    
    # read c3d file
    reader = c3d.Reader(open(c3dFilePath, 'rb'))

    # get analog labels, trimmed and replace '.' with '_'
    analog_labels = reader.analog_labels
    analog_labels = [label.strip() for label in analog_labels]
    analog_labels = [label.replace('.', '_') for label in analog_labels]

    # get analog labels, trimmed and replace '.' with '_'
    num_frames = reader.frame_count
    df = pd.DataFrame(index=range(num_frames),columns=analog_labels)
    
    # loop through frames and add analog data to dataframe
    for i_frame, points, analog in reader.read_frames():
        
        # get row number and print loading bar
        i_row = i_frame - reader.first_frame
        # msk.ut.print_loading_bar(i_row/num_frames)
        
        # convert analog data to list
        analog_list  = analog.data.tolist()
        
        # loop through analog channels and add to dataframe
        for i_channel in range(len(analog_list)):
            channel_name = analog_labels[i_channel]
            
            # add channel to dataframe
            df.loc[i_row, channel_name] = analog[i_channel][0]
    
    # save emg data to csv
    df.to_csv(analog_file_path)
    print('analog.csv exported to ' + analog_file_path)  
    
    return df
    
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

def create_grf_xml(grf_file, output_file= '', apply_force_body_name='calcn_r', force_expressed_in_body_name='ground'):     
    '''Create an external loads XML file from a GRF file.
    Usage:
    import msk_modelling_python as msk
    msk.bops.create_grf_xml(grf_file, output_file= '', apply_force_body_name='calcn_r', force_expressed_in_body_name='ground')    
    
    '''       
    # create empty ExternalLoads object and set the data file name
    try:
        external_loads = osim.ExternalLoads()
        external_loads.setDataFileName(grf_file) 
        if output_file == '':
            output_file = os.path.dirname(grf_file) + '/grf.xml'
        external_loads.printToXML(output_file)

    except Exception as e:
        msk.ut.debug_print('Could not create external loads for ' + grf_file)
        if msk.__testing__: 
            msk.bops.Platypus().sad()
                        
    # add external forces based on the GRF file
    try:
        xml = msk.bops.readXML(output_file)
        forces = msk.bops.import_sto_data(grf_file)
        columns = forces.columns.drop('time')
        
        # num forces as the number of columns in the GRF file containing f[number]_
        num_forces = len([col for col in columns if col.startswith('f') and col.endswith('1')])

        external_loads_tag = xml.find('ExternalLoads')
        objects_tag = xml.find('ExternalLoads/objects')
        
        # Add new ExternalForce elements
        for i in range(num_forces):
            new_force = ET.Element('ExternalForce')
            new_force.set('name', f'externalforce_{i}')  # Adjust names as needed

            def create_element(tag, text):
                element = ET.Element(tag)
                element.text = text
                return element
            
            def indent(elem, level=0):
                '''
                Input: 
                elem - XML element
                level - integer representing the level of indentation
                '''
                
                i = "\n" + level * "  "
                if len(elem):
                    if not elem.text or not elem.text.strip():
                        elem.text = i + "  "
                    for child in elem:
                        indent(child, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
                else:
                    if level and (not elem.tail or not elem.tail.strip()):
                        elem.tail = i
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
                    
            # Add child elements with desired attributes for each force
            new_force.append(create_element('applied_to_body', apply_force_body_name))
            new_force.append(create_element('force_expressed_in_body', force_expressed_in_body_name))
            new_force.append(create_element('force_identifier', f'f{i}_'))
            new_force.append(create_element('point_identifier', f'p{i}_'))
            new_force.append(create_element('torque_identifier', f'm{i}_'))
            
            indent(new_force, level=5)
            objects_tag.insert(i, new_force)

        # Save the updated XML file
        xml.write(output_file, encoding='utf-8', xml_declaration=True, )

        
        print(f'External loads XML file saved to: {output_file}')
    except Exception as e:
        ut.print_warning('error adding forces to grf.xml: ' + output_file + '\n' + str(e))
        msk.ut.debug_print('error adding forces to grf.xml: ' + output_file)
        if msk.__testing__: 
            msk.bops.Platypus().sad() 
            


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


    return tree

def get_tag_xml(xml_file_path, tag_name):
    '''
    Function to extract the value of a specified tag from an XML file.
    Usage: get_tag_xml('file.xml', 'tag_name')
    '''
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

class osimSetup:
    def __init__(self):
        pass
    
    def print_osim_info():
        print('Osim module version: ' + osim.__version__)
        print('Osim module path: ' + osim.__file__)
        
    def create_analysis_tool(coordinates_file, modelpath, results_directory, force_set_files=None):
        # Get mot data to determine time range
        motData = osim.Storage(coordinates_file)

        # Get initial and final time
        initial_time = motData.getFirstTime()
        final_time = motData.getLastTime()

        # Set the model
        model = osim.Model(modelpath)

        # Create AnalyzeTool
        analyzeTool = osim.AnalyzeTool()
        analyzeTool.setModel(model)
        analyzeTool.setModelFilename(model.getDocumentFileName())

        analyzeTool.setReplaceForceSet(False)
        analyzeTool.setResultsDir(results_directory)
        analyzeTool.setOutputPrecision(8)

        if force_set_files is not None:  # Set actuators file
            forceSet = osim.ArrayStr()
            forceSet.append(force_set_files)
            analyzeTool.setForceSetFiles(forceSet)

        # motData.print('.\states.sto')
        # states = osim.Storage('.\states.sto')
        # analyzeTool.setStatesStorage(states)
        analyzeTool.setInitialTime(initial_time)
        analyzeTool.setFinalTime(final_time)

        analyzeTool.setSolveForEquilibrium(False)
        analyzeTool.setMaximumNumberOfSteps(20000)
        analyzeTool.setMaxDT(1)
        analyzeTool.setMinDT(1e-008)
        analyzeTool.setErrorTolerance(1e-005)

        analyzeTool.setExternalLoadsFileName('.\GRF.xml')
        analyzeTool.setCoordinatesFileName(coordinates_file)
        analyzeTool.setLowpassCutoffFrequency(6)

        return analyzeTool

    def get_muscles_by_group_osim(xml_path, group_names): # olny tested for Catelli model Opensim 3.3
        members_dict = {}

        try:
            with open(xml_path, 'r', encoding='utf-8') as file:
                tree = ET.parse(xml_path)
                root = tree.getroot()
        except Exception as e:
            print('Error parsing xml file: {}'.format(e))
            return members_dict
        
        if group_names == 'all':
            # Find all ObjectGroup names
            group_names = [group.attrib['name'] for group in root.findall(".//ObjectGroup")]


        members_dict['all_selected'] = []
        for group_name in group_names:
            members = []
            for group in root.findall(".//ObjectGroup[@name='{}']".format(group_name)):
                members_str = group.find('members').text
                members.extend(members_str.split())
            
            members_dict[group_name] = members
            members_dict['all_selected'] = members_dict['all_selected'] + members 

        return members_dict

    def increase_max_isometric_force(model_path, factor, compare_models = False): # opensim API
        # Load the OpenSim model
        model = osim.Model(model_path)

        # Loop through muscles and update their maximum isometric force
        muscles = pd.DataFrame()
        muscle_data = []
        for muscle in model.getMuscles():
            current_max_force = muscle.getMaxIsometricForce()
            new_max_force = current_max_force * factor
            muscle_data.append([muscle.getName(), current_max_force, new_max_force])
            muscle.setMaxIsometricForce(new_max_force)

        # Create a DataFrame with the muscle data
        muscle_df = pd.DataFrame(muscle_data, columns=['Muscle Name', 'Old Max Isometric Force', 'New Max Isometric Force'])
        
        # Save the modified model
        output_model_path = model_path.replace('.osim', f'_increased_force_{factor}.osim')
        model.printToXML(output_model_path)

        print(f'Model with increased forces saved to: {output_model_path}')
        
        if compare_models:
            # plot muscle_df
            fig, ax = plt.subplots()
            ax.bar(muscle_df['Muscle Name'], muscle_df['Old Max Isometric Force'], label='Old Max Isometric Force')
            ax.bar(muscle_df['Muscle Name'], muscle_df['New Max Isometric Force'], label='New Max Isometric Force')
            ax.set_ylabel('Max Isometric Force')           
            plt.show()
            
        
        return output_model_path

    def update_max_isometric_force_xml(xml_file, factor,output_file = ''): # xml
        # Parse the XML file
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find all Millard2012EquilibriumMuscle elements
        muscles = root.findall('.//Millard2012EquilibriumMuscle')

        # Update max_isometric_force for each muscle
        n = 0
        for muscle in muscles:
            max_force_element = muscle.find('./max_isometric_force')
            if max_force_element is not None:
                current_max_force = float(max_force_element.text)
                new_max_force = current_max_force * factor
                max_force_element.text = str(new_max_force)
                n = 1
        if n == 0:
            print('No Millard2012EquilibriumMuscle elements found in the XML file.')
            
        # Save the modified XML file
        if not output_file:
            output_xml_file = xml_file.replace('.xml', f'_updated.xml')
        else:
            output_xml_file = output_file
            
        tree.write(output_xml_file)

        print(f'Modified XML saved to: {output_xml_file}')
        
    def reorder_markers(xml_path, order):
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Create a dictionary to store marker elements by name
        # markers_dict = {marker.find('name').text: marker for marker in root.findall('.//Marker')}

        # Create a new MarkerSet element to replace the existing one
        new_marker_set = ET.Element('MarkerSet')
        # Create the 'objects' element
        objects_element = ET.SubElement(new_marker_set, 'objects')    
        groups_element = ET.SubElement(new_marker_set, 'groups')    

        # Add Marker elements to the new MarkerSet in the specified order
        for marker_name in order:
            existing_marker = root.find('.//Marker[@name="' + marker_name + '"]')
            if existing_marker:
                objects_element.append(existing_marker)

        # Replace the existing MarkerSet with the new one
        existing_marker_set = root.find('.//MarkerSet')
        existing_marker_set.clear()
        existing_marker_set.extend(new_marker_set)

        # Save the modified XML back to a file
        tree.write(xml_path)

    def copy_marker_locations(model_path1,model_path2,marker_names='all',marker_common_frame='RASI'):
        '''
        This function copies the location of markers from model2 to model1. 
        The location of the marker in model1 is changed to the location of the marker in model2 
        in the frame of the common marker. 
        The location of the marker in model1 is changed back to the original parent frame. 
        The model with the changed marker locations is saved as a new model.
        '''
        # Load the OpenSim model
        model1 = Model(model_path1)
        model1_version = model1.version
        model1_xml = model1.xml
        model1 = model1.osim_object
        markerset1 = model1.get_MarkerSet()
        state1 = model1.initSystem()

        model2 = osim.Model(model_path2)
        markerset2 = model2.get_MarkerSet()
        state2 = model2.initSystem()
        
        # if marker_names == 'all' then use all markers in model1
        if marker_names == 'all':
            marker_names = [markerset1.get(i).getName() for i in range(markerset1.getSize())]

        if marker_common_frame not in marker_names:
            raise ValueError('The marker_common_frame must be included in marker_names')

        # Loop through muscles and update their maximum isometric force
        for marker_name in marker_names:

            try:
                if markerset1.contains(marker_name):
                    marker1 = dict()
                    marker2 = dict()
                    
                    # get marker objects
                    marker1['marker'] = markerset1.get(marker_name)
                    marker2['marker'] = markerset2.get(marker_name)

                    # get location of markers
                    marker1['location'] = list(marker1['marker'].get_location().to_numpy())           
                    marker2['location'] = list(marker2['marker'].get_location().to_numpy())

                    # get parent frame of markers            
                    marker1['parent_frame'] = marker1['marker'].getParentFrame()
                    marker2['parent_frame'] = marker2['marker'].getParentFrame()

                    # get pelvis frame from marker_common_frame marker
                    marker1['pelvis_frame'] = markerset1.get(marker_common_frame).getParentFrame()
                    marker2['pelvis_frame'] = markerset2.get(marker_common_frame).getParentFrame()
                    
                    # get location of marker 2 in pelvis frame
                    marker2['marker'].changeFramePreserveLocation(state2,marker2['pelvis_frame'])
                    marker2['location_in_pelvis'] = marker2['marker'].get_location()
                    
                    # change location of marker 1 to marker 2 in pelvis frame
                    marker1['marker'].changeFramePreserveLocation(state1,marker1['pelvis_frame'])
                    marker1['marker'].set_location(marker2['location_in_pelvis'])

                    # change marker 1 back to original parent frame
                    marker1['marker'].changeFramePreserveLocation(state1,marker1['parent_frame'])
                    marker1['location'] = list(marker1['marker'].get_location().to_numpy())  

                    # if orginal model is 3.3 change the 
                    if int(model1_version[0]) == 3:
                        model1_xml.getroot().find('.//Marker[@name="' + marker_name + '"]/location').text = ' '.join(map(str, marker1['location']))

                    print(f'Location of marker {marker_name} changed')
            except Exception as e:
                print(f'Error changing location of marker {marker_name}: {e}')


        # Save the modified model
        if int(model1_version[0]) == 3:
            output_model_path = model_path1.replace('.osim', '_new.osim')
            model1_xml.write(model_path1.replace('.osim', '_new.osim'))
            print(f'Model saved to: {model_path1}')
        else:    
            output_model_path = model_path1.replace('.osim', '_new.osim')
            model1.printToXML(output_model_path)
            print(f'Model saved to: {output_model_path}')

    def create_grf_xml(grf_file, output_file):     

        # Create the OpenSim ExternalLoads object
        external_loads = osim.ExternalLoads()

        # Set the external loads file
        external_loads.setDataFileName(grf_file)
        external_loads.printToXML(output_file)
        
        print(f'External loads XML file saved to: {output_file}')
         
    # Operations    
    def sum_body_mass(model_path):
        '''
        This function sums the body mass of the model
        '''
        # Load the OpenSim model
        model = model(model_path)
        mass = 0
        for i in range(model.osim_object.getBodySet().getSize()):
            mass += model.osim_object.getBodySet().get(i).getMass()
        print(f'The total mass of the model is: {mass} kg')
        return mass

def example_data(trial_name = 'walking1'):
    
    if trial_name == 'walking1':
        osim
        
        

    

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

def create_analysis_tool(coordinates_file, model_path, results_directory, force_set_files=None):
  """Creates and configures an OpenSim AnalyzeTool object.

  Args:
    coordinates_file: Path to the motion data file (e.g., .trc or .mot).
    model_path: Path to the OpenSim model file (.osim).
    results_directory: Path to the directory for storing results.
    force_set_files (optional): List of paths to actuator force set files.

  Returns:
    OpenSim AnalyzeTool object.

    # Example usage:
        coordinates_file = "your_motion_data.trc"
        model_path = "your_model.osim"
        results_directory = "analysis_results"
        force_set_files = ["actuator1_forces.xml", "actuator2_forces.xml"]  # Optional

        analysis_tool = create_analysis_tool(coordinates_file, model_path, results_directory, force_set_files)

        # Run the analysis
        analysis_tool.run()
  """

  # Load the motion data
  mot_data = osim.Storage(coordinates_file)

  # Get initial and final time
  initial_time = mot_data.getStartTime()
  final_time = mot_data.getEndTime()

  # Create and set model
  model = osim.Model(model_path)
  analyze_tool = osim.AnalyzeTool()
  analyze_tool.setModel(model)

  # Set other parameters
  analyze_tool.setModelFilename(model.getFilePath())
  analyze_tool.setReplaceForceSet(False)
  analyze_tool.setResultsDir(results_directory)
  analyze_tool.setOutputPrecision(8)

  # Set actuator force files (if provided)
  if force_set_files:
    force_set = osim.ArrayStr()
    for file in force_set_files:
      force_set.append(file)
    analyze_tool.setForceSetFiles(force_set)

  # Set initial and final time
  analyze_tool.setInitialTime(initial_time)
  analyze_tool.setFinalTime(final_time)

  # Set analysis parameters
  analyze_tool.setSolveForEquilibrium(False)
  analyze_tool.setMaximumNumberOfSteps(20000)
  analyze_tool.setMaxDT(1)
  analyze_tool.setMinDT(1e-8)
  analyze_tool.setErrorTolerance(1e-5)

  # Set external loads and coordinates files
  analyze_tool.setExternalLoadsFileName("GRF.xml")  # Replace with your filename
  analyze_tool.setCoordinatesFileName(coordinates_file)

  # Set filter cutoff frequency
  analyze_tool.setLowpassCutoffFrequency(6)

  # Save settings to XML
  analyze_tool.printToXML(os.path.join(results_directory, "analyzeTool_setup.xml"))

  # Return the analysis tool
  return analyze_tool

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

def runJRA(modelpath, trial_path, setup_file_path):
    os.chdir(trial_path)
    results_directory = [trial_path]
    coordinates_file = [trial_path, 'ik.mot']
    _, trialName = os.path.split(trial_path)

    # start model
    osimModel = osim.Model(modelpath)

    # Get mot data to determine time range
    motData = osim.Storage(coordinates_file)

    # Get initial and intial time
    initial_time = motData.getFirstTime()
    final_time = motData.getLastTime()

    # start joint reaction analysis
    jr = osim.JointReaction(setup_file_path)
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
    jr.setForcesFileName(['.\joint_reaction_analysis.sto'])

    # add to analysis tool
    analyzeTool_JR = create_analysis_tool(coordinates_file, modelpath, results_directory)
    analyzeTool_JR.get().AnalysisSet.cloneAndAppend(jr)
    osimModel.addAnalysis(jr)

    # save setup file and run
    analyzeTool_JR.print(['./setup_jra.xml'])
    analyzeTool_JR = osim.AnalyzeTool(['./setup_jra.xml'])
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



#%% ##############################################  Data checks (to be complete) ############################################################
def checkMuscleMomentArms(model_file_path, ik_file_path, leg = 'l', threshold = 0.005):
# Adapted from Willi Koller: https://github.com/WilliKoller/OpenSimMatlabBasic/blob/main/checkMuscleMomentArms.m
# Only checked if works for for the Rajagopal and Catelli models

    def get_model_coord(model, coord_name):
        try:
            index = model.getCoordinateSet().getIndex(coord_name)
            coord = model.updCoordinateSet().get(index)
        except:
            index = None
            coord = None
            print(f'Coordinate {coord_name} not found in model')
        
        return index, coord


    # raise Exception('This function is not yet working. Please use the Matlab version for now or fix line containing " time_discontinuity.append(time_vector[discontinuity_indices]) "')

    # Load motions and model
    motion = osim.Storage(ik_file_path)
    model = osim.Model(model_file_path)

    # Initialize system and state
    model.initSystem()
    state = model.initSystem()

    # coordinate names
    flexIndexL, flexCoordL = get_model_coord(model, 'hip_flexion_' + leg)
    rotIndexL, rotCoordL = get_model_coord(model, 'hip_rotation_' + leg)
    addIndexL, addCoordL = get_model_coord(model, 'hip_adduction_' + leg)
    flexIndexLknee, flexCoordLknee = get_model_coord(model, 'knee_angle_' + leg)
    flexIndexLank, flexCoordLank = get_model_coord(model, 'ankle_angle_' + leg)

    # get names of the hip muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_hip = []
    muscleNames_hip = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        if ('add' in tmp_muscleName or 'gl' in tmp_muscleName or 'semi' in tmp_muscleName or 'bf' in tmp_muscleName or
                'grac' in tmp_muscleName or 'piri' in tmp_muscleName or 'sart' in tmp_muscleName or 'tfl' in tmp_muscleName or
                'iliacus' in tmp_muscleName or 'psoas' in tmp_muscleName or 'rect' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_hip.append(i)
            muscleNames_hip.append(tmp_muscleName)

    flexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))
    addMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))
    rotMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))

    # get names of the knee muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_knee = []
    muscleNames_knee = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        if ('bf' in tmp_muscleName or 'gas' in tmp_muscleName or 'grac' in tmp_muscleName or 'sart' in tmp_muscleName or
                'semim' in tmp_muscleName or 'semit' in tmp_muscleName or 'rec' in tmp_muscleName or 'vas' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_knee.append(i)
            muscleNames_knee.append(tmp_muscleName)

    kneeFlexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_knee)))

    # get names of the ankle muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_ankle = []
    muscleNames_ankle = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        print(tmp_muscleName)
        if ('edl' in tmp_muscleName or 'ehl' in tmp_muscleName or 'tibant' in tmp_muscleName or 'gas' in tmp_muscleName or
                'fdl' in tmp_muscleName or 'fhl' in tmp_muscleName or 'perb' in tmp_muscleName or 'perl' in tmp_muscleName or
                'sole' in tmp_muscleName or 'tibpos' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_ankle.append(i)
            muscleNames_ankle.append(tmp_muscleName)

    ankleFlexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_ankle)))

    # compute moment arms for each muscle and create time vector
    time_vector = []
    for i in range(1, motion.getSize()):
        flexAngleL = motion.getStateVector(i-1).getData().get(flexIndexL) / 180 * np.pi
        rotAngleL = motion.getStateVector(i-1).getData().get(rotIndexL) / 180 * np.pi
        addAngleL = motion.getStateVector(i-1).getData().get(addIndexL) / 180 * np.pi
        flexAngleLknee = motion.getStateVector(i-1).getData().get(flexIndexLknee) / 180 * np.pi
        flexAngleLank = motion.getStateVector(i-1).getData().get(flexIndexLank) / 180 * np.pi

        time_vector.append(motion.getStateVector(i-1).getTime())
        # Update the state with the joint angle
        coordSet = model.updCoordinateSet()
        coordSet.get(flexIndexL).setValue(state, flexAngleL)
        coordSet.get(rotIndexL).setValue(state, rotAngleL)
        coordSet.get(addIndexL).setValue(state, addAngleL)
        coordSet.get(flexIndexLknee).setValue(state, flexAngleLknee)
        coordSet.get(flexIndexLank).setValue(state, flexAngleLank)

        # Realize the state to compute dependent quantities
        model.computeStateVariableDerivatives(state)
        model.realizeVelocity(state)

        # Compute the moment arm hip
        for j in range(len(muscleIndices_hip)):
            muscleIndex = muscleIndices_hip[j]
            if muscleNames_hip[j][-1] == leg:
                flexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordL)
                flexMomentArms[i, j] = flexMomentArm

                rotMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, rotCoordL)
                rotMomentArms[i, j] = rotMomentArm

                addMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, addCoordL)
                addMomentArms[i, j] = addMomentArm

        # Compute the moment arm knee
        for j in range(len(muscleNames_knee)):
            muscleIndex = muscleIndices_knee[j]
            if muscleNames_knee[j][-1] == leg:
                kneeFlexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordLknee)
                kneeFlexMomentArms[i, j] = kneeFlexMomentArm

        # Compute the moment arm ankle
        for j in range(len(muscleNames_ankle)):
            muscleIndex = muscleIndices_ankle[j]
            if muscleNames_ankle[j][-1] == leg:
                ankleFlexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordLank)
                ankleFlexMomentArms[i, j] = ankleFlexMomentArm

    # check discontinuities
    discontinuity = []
    muscle_action = []
    time_discontinuity = []

    fDistC = plt.figure('Discontinuity', figsize=(8, 8))
    plt.title(ik_file_path)

    save_folder = os.path.join(os.path.dirname(ik_file_path),'momentArmsCheck')

    def find_discontinuities(momArms, threshold, muscleNames, action, discontinuity, muscle_action, time_discontinuity):
        for i in range(momArms.shape[1]):
            dy = np.diff(momArms[:, i])
            discontinuity_indices = np.where(np.abs(dy) > threshold)[0]
            if discontinuity_indices.size > 0:
                print('Discontinuity detected at', muscleNames[i], 'at ', action, ' moment arm')
                plt.plot(momArms[:, i])
                plt.plot(discontinuity_indices, momArms[discontinuity_indices, i], 'rx')
                discontinuity.append(i)
                muscle_action.append(str(muscleNames[i] + ' ' + action + ' at frames: ' + str(discontinuity_indices)))
                time_discontinuity.append([time_vector[index] for index in discontinuity_indices])


        return discontinuity, muscle_action, time_discontinuity

    # hip flexion
    discontinuity, muscle_action, time_discontinuity = find_discontinuities(
        flexMomentArms, threshold, muscleNames_hip, 'flexion', discontinuity, muscle_action, time_discontinuity)

    # hip adduction
    discontinuity, muscle_action, time_discontinuity = find_discontinuities(
        addMomentArms, threshold, muscleNames_hip, 'adduction', discontinuity, muscle_action, time_discontinuity)
    
    # hip rotation
    discontinuity, muscle_action, time_discontinuity = find_discontinuities(
        rotMomentArms, threshold, muscleNames_hip, 'rotation', discontinuity, muscle_action, time_discontinuity)
    
    # knee flexion
    discontinuity, muscle_action, time_discontinuity = find_discontinuities(
        kneeFlexMomentArms, threshold, muscleNames_knee, 'flexion', discontinuity, muscle_action, time_discontinuity)
    
    # ankle flexion
    discontinuity, muscle_action, time_discontinuity = find_discontinuities(
        ankleFlexMomentArms, threshold, muscleNames_ankle, 'dorsiflexion', discontinuity, muscle_action, time_discontinuity)
    
    # plot discontinuities
    if len(discontinuity) > 0:
        plt.legend(muscle_action)
        plt.ylabel('Muscle Moment Arms with discontinuities (m)')
        plt.xlabel('Frame (after start time)')
        save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'discontinuities_' + leg + '.png'))
        print('\n\nYou should alter the model - most probably you have to reduce the radius of corresponding wrap objects for the identified muscles\n\n\n')

        # save txt file with discontinuities
        with open(os.path.join(save_folder, 'discontinuities_' + leg + '.txt'), 'w') as f:
            f.write(f"model file = {model_file_path}\n")
            f.write(f"motion file = {ik_file_path}\n")
            f.write(f"leg checked = {leg}\n")
            
            f.write("\n muscles with discontinuities \n", ) 
            
            for i in range(len(muscle_action)):
                try:
                    f.write("%s : time %s \n" % (muscle_action[i], time_discontinuity[i]))
                except:
                    print('no discontinuities detected')

        momentArmsAreWrong = 1
    else:
        plt.close(fDistC)
        print('No discontinuities detected')
        momentArmsAreWrong = 0

    # plot hip flexion
    plt.figure('flexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(flexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Flexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_flex_MomentArms_' + leg + '.png'))

    # hip adduction
    plt.figure('addMomentArms_' + leg, figsize=(8, 8))
    plt.plot(addMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Adduction Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_add_MomentArms_' + leg + '.png'))

    # hip rotation
    plt.figure('rotMomentArms_' + leg, figsize=(8, 8))
    plt.plot(rotMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Rotation Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_rot_MomentArms_' + leg + '.png'))

    # knee flexion
    plt.figure('kneeFlexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(kneeFlexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_knee, loc='best')
    plt.ylabel('Knee Flexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'knee_MomentArms_' + leg + '.png'))

    # ankle flexion
    plt.figure('ankleFlexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(ankleFlexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_ankle, loc='best')
    plt.ylabel('Ankle Dorsiflexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'ankle_MomentArms_' + leg + '.png'))

    print('Moment arms checked for ' + ik_file_path)
    print('Results saved in ' + save_folder + ' \n\n' )

    return momentArmsAreWrong,  discontinuity, muscle_action

#%% ###############################################  GUI (to be complete)  #################################################################
def subjet_select_gui():

    def get_switches_status(switches):
        settings = get_bops_settings()
        settings['subjects'] = dict()
        for i, switch in enumerate(switches):
            settings['subjects'][subject_names[i]] = switch.get()

        save_bops_settings(settings)
        exit()


    ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    ctk.set_default_color_theme("dark-blue")  # Themes: "blue" (standard), "green", "dark-blue"

    screen_size = si.get_monitors()

    root = ctk.CTk()
    root.geometry('500x600')

    frame = ctk.CTkFrame(root)
    frame.pack(pady=5,padx=5,fill='both',expand=True)

    subject_names = get_subject_names()
    # create scrollable frame
    scrollable_frame = ctk.CTkScrollableFrame(frame, label_text="Choose the subjects")
    scrollable_frame.pack(padx=0, pady=0)
    # scrollable_frame.pack_configure(0, weight=1)
    scrollable_frame_switches = []
    switches_gui  = []
    values = []

    for idx, subject in enumerate(subject_names):
        switch = ctk.CTkSwitch(master=scrollable_frame, text=subject)
        switch.pack(padx=0, pady=0)
        switches_gui.append(switch)

        scrollable_frame_switches.append(switch)

    button1 = ctk.CTkButton(master = root, text='Select subjects',
                            command = lambda: get_switches_status(switches_gui))
    button1.pack(pady=12,padx=10)

    root.mainloop()

# function to run the example        
def run_example():
    app = msk.ui.App()
    
    # example data path for walking trial 1
    trial_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "example_data", "walking", "trial1")
    trial_paths = msk.TrialPaths(trial_path)
        
    app.add(type = 'osim_input', osim_model=trial_paths.model_torsion, setup_ik_path=trial_paths.setup_ik, 
            setup_id_path=trial_paths.setup_id, setup_so_path=trial_paths.setup_so, setup_jra_path=trial_paths.setup_jra)
    
    # add exit button
    app.add(type = 'exit_button')
    
    app.autoscale()
    
    app.start()    
    
    return app

def run_example_batch():
    project_path = msk.ut.select_folder("Select project folder")
        
    project = msk.Project(project_path)
    print("Project loaded")
    
    for subject in project.subjects:
        print(f"Subject: {subject}")
        for task in project.__dict__[subject].tasks:
            print(f"Trial: {task}")
            import pdb; pdb.set_trace()
            trial = project.__dict__[subject].__dict__[task]

    
    return project

   


#%% ########################################################  Plotting  ####################################################################
# when creating plots bops will only create the fig and axs. Use plt.show() to show the plot
def create_sto_plot(stoFilePath=False):
    # Specify the path to the .sto file
    if not stoFilePath:
        stoFilePath = get_testing_file_path('id')

    # Read the .sto file into a pandas DataFrame
    data = import_sto_data(stoFilePath)

    # Get the column names excluding 'time'
    column_names = [col for col in data.columns if col != 'time']

    # Calculate the grid size
    num_plots = len(column_names)
    grid_size = int(num_plots ** 0.5) + 1

    # Get the screen width and height
    user32 = ctypes.windll.user32
    screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    fig_width = screensize[0] * 0.9
    fig_height = screensize[1] * 0.9

    # Create the subplots
    fig, axs = plt.subplots(grid_size, grid_size, figsize=(10, 10))

    # Flatten the axs array for easier indexing
    axs = axs.flatten()

    # Create a custom color using RGB values (r,g,b)
    custom_color = (0.8, 0.4, 0.5)

    num_cols = data.shape[1]
    num_rows = int(np.ceil(num_cols / 3))  # Adjust the number of rows based on the number of columns

    # Iterate over the column names and plot the data
    for i, column in enumerate(column_names):
        ax = axs[i]
        ax.plot(data['time'], data[column], color=custom_color, linewidth=1.5)
        ax.set_title(column, fontsize=8)
        
        if i % 3 == 0:
            ax.set_ylabel('Moment (Nm)',fontsize=9)
            ax.set_yticks(np.arange(-3, 4))

        if i >= num_cols - 3:
            ax.set_xlabel('time (s)', fontsize=8)
            ax.set_xticks(np.arange(0, 11, 2))
        
        ax.grid(True, linestyle='--', linewidth=0.5)
        ax.tick_params(labelsize=8)

    # Remove any unused subplots
    if num_plots < len(axs):
        for i in range(num_plots, len(axs)):
            fig.delaxes(axs[i])

    # Adjust the spacing between subplots
    plt.tight_layout()

    return fig

def create_example_emg_plot(c3dFilePath=False):
    # Specify the path to the .sto file
    if not c3dFilePath:
        c3dFilePath = get_testing_file_path('c3d')

    # Read the .sto file into a pandas DataFrame
    data = import_c3d_analog_data(c3dFilePath)
    data_filtered = emg_filter(c3dFilePath)

    # Get the column names excluding 'time'
    column_names = [col for col in data.columns if col != 'time']

    # Calculate the grid size
    num_plots = len(column_names)
    grid_size = int(num_plots ** 0.5) + 1

    # Get the screen width and height
    user32 = ctypes.windll.user32
    screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    fig_width = screensize[0] * 0.9
    fig_height = screensize[1] * 0.9

    # Create the subplots
    fig, axs = plt.subplots(grid_size, grid_size, figsize=(10, 10))

    # Flatten the axs array for easier indexing
    axs = axs.flatten()

    # Create a custom color using RGB values (r,g,b)
    custom_color = (0.8, 0.4, 0.5)

    num_cols = data.shape[1]
    num_rows = int(np.ceil(num_cols / 3))  # Adjust the number of rows based on the number of columns

    # Iterate over the column names and plot the data
    for i, column in enumerate(column_names):
        ax = axs[i]
        ax.plot(data['time'], data[column], color=custom_color, linewidth=1.5)
        ax.plot(data_filtered['time'], data_filtered[column], color=custom_color, linewidth=1.5)
        ax.set_title(column, fontsize=8)
        
        if i % 3 == 0:
            ax.set_ylabel('Moment (Nm)',fontsize=9)
            ax.set_yticks(np.arange(-3, 4))

        if i >= num_cols - 3:
            ax.set_xlabel('time (s)', fontsize=8)
            ax.set_xticks(np.arange(0, 11, 2))
        
        ax.grid(True, linestyle='--', linewidth=0.5)
        ax.tick_params(labelsize=8)

    # Remove any unused subplots
    if num_plots < len(axs):
        for i in range(num_plots, len(axs)):
            fig.delaxes(axs[i])

    # Adjust the spacing between subplots
    plt.tight_layout()

    return fig     

def calculate_axes_number(num_plots):
    if num_plots  > 2:
        ncols = math.ceil(math.sqrt(num_plots))
        nrows = math.ceil(num_plots / ncols)
    else:
        ncols = num_plots
        nrows = 1

    return ncols, nrows

def plot_line_df(df,sep_subplots = True, columns_to_plot='all',xlabel=' ',ylabel=' ', legend=['data1'],save_path='', title=''):
    
    # Check if the input is a file path
    if type(df) == str and os.path.isfile(df):
        df = import_sto_data(df)
        pass
    
    if columns_to_plot == 'all':
        columns_to_plot = df.columns
    
    # Create a new figure and subplots
    if sep_subplots:
        ncols, nrows = calculate_axes_number(len(columns_to_plot))
        fig, axs = plt.subplots(nrows, ncols, figsize=(15, 5))
        
        for row, ax_row in enumerate(axs):
            for col, ax in enumerate(ax_row):
                ax_count = row * ncols + col

                heading = columns_to_plot[ax_count]    
                if heading not in df.columns:
                    print(f'Heading not found: {heading}')
                    continue    
                
                # Plot data
                ax.plot(df[heading])
                ax.set_title(f'{heading}')
                
                if row == 1:
                    ax.set_xlabel(xlabel)
                if col == 0:
                    ax.set_ylabel(ylabel)
    
        plt.legend(legend)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.title(title)
    
    else:
        fig, axs = plt.subplots(1, 1, figsize=(15, 5))
        for column in columns_to_plot:
            axs.plot(df[column])
            axs.set_title(f'{column}')
            axs.set_xlabel(xlabel)
            axs.set_ylabel(ylabel)
        
        plt.title(title)
        axs.legend(columns_to_plot,ncols=2)
    
    fig.set_tight_layout(True)

    if save_path:
        save_fig(fig,save_path)
    
    return fig, axs

def plot_bar_df(df,transpose = False):

    # Transpose the DataFrame to have rows as different bar series
    if transpose:
        df = df.transpose()

    # Plot the bar chart
    ax = df.plot(kind='bar', figsize=(10, 6), colormap='viridis')

    # Customize the plot
    ax.set_xlabel(' ')
    ax.set_ylabel(' ')
    ax.set_title(' ')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

    # Adjust subplot layout to make room for x-axis tick labels
    plt.subplots_adjust(bottom=0.2)

    return plt.gcf(), plt.gca()

def plot_line_list(data, labels = '', xlabel=' ', ylabel=' ', title=' ', save_path=''):
    # Create a new figure
    fig, ax = plt.subplots(figsize=(10, 6))

    if not labels:
        labels = [f'Data {i}' for i in range(len(data))]

    # Plot the data
    ax.plot(data, label=labels)

    # Customize the plot
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    

    return fig, ax

def plot_from_txt(file_path='', xlabel=' ', ylabel=' ', title=' ', save_path=''):
    
    if not file_path:
        file_path = select_file()
    
    # Read the data from the text file
    data = np.loadtxt(file_path)

    # plot simple line plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(data)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
            
    fig.set_tight_layout(True)

    if save_path:
        save_fig(fig,save_path)
    
    return fig, ax

#%% ####################################################    ##################################################################
#%% ####################################################  Error prints  ##################################################################
def exampleFunction():
    pass


#%% ################################################  CREATE BOPS SETTINGS ###############################################################
def add_markers_to_settings():
    settings = get_bops_settings()
    for subject_folder in get_subject_folders():
        for session in get_subject_sessions(subject_folder):
            sessionPath = os.path.join(subject_folder,session)
            for trial_name in get_trial_list(sessionPath,full_dir = False):

                c3dFilePath = get_trial_dirs(sessionPath, trial_name)['c3d']
                c3d_data = import_c3d_to_dict(c3dFilePath)


                settings['marker_names'] = c3d_data['marker_names']
                break
            break
        break

    save_bops_settings(settings)

def get_testing_file_path(file_type = 'c3d'):
    
    settings = get_bops_settings()
    
    msk_dir = msk.__path__[0]
    dir_simulations =  os.path.join(msk_dir, 'example_data\\running')
    if not os.path.exists(dir_simulations):
        raise_exception(dir_simulations + ' does not exist. ', hard=False)
        return None

    file_path = []
    for subject_folder in get_subject_folders(dir_simulations):
        for session in get_subject_sessions(subject_folder):
            sessionPath = os.path.join(subject_folder,session)
            for idx, trial_name in enumerate(get_trial_list(sessionPath,full_dir = False)):

                resultsDir = get_trial_list(sessionPath,full_dir = True)[idx]
                if file_type.__contains__('c3d'):
                    file_path.append(os.path.join(resultsDir,'c3dfile.c3d'))

                elif file_type.__contains__('trc'):
                    file_path.append(os.path.join(resultsDir,'markers.trc'))

                elif file_type.__contains__('so'):
                    file_path.append(os.path.join(resultsDir,'_StaticOptimization_activation.sto'))
                    file_path.append(os.path.join(resultsDir,'_StaticOptimization_force.sto'))
                
                elif file_type.__contains__('id'):
                    file_path.append(os.path.join(resultsDir,'inverse_dynamics.sto'))

                break
            break
        break
    file_path = file_path[0] # make it a string instead of a list

    return file_path

def progress_bar():
    total_steps = 5
    with tqdm(total=total_steps, desc="Processing") as pbar:
        pbar.update(1)


#%% ############################################################ UTILS ####################################################################

def clear_terminal():
    # Clear terminal command based on the operating system
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For macOS and Linux (posix)
        os.system('clear')

def uni_vie_print():
    print("=============================================")
    print("      DEVELOPED BY BASILIO GONCALVES         ")
    print("            University of Vienna             ")
    print("    Contact: basilio.goncalves@univie.ac.at  ")
    print("=============================================")

def ask_to_continue():
    print('Ensure your settings are correct before continuing.')
    answer = input("Press 'y' to continue or 'n' to exit: ")

    if answer == 'y':
        pass
    elif answer == 'n':
        sys.exit('Exiting...')
    else:
        print('Invalid input. Please try again (n/y).')
        ask_to_continue()

def is_potential_path(folderpath):

    if type(folderpath) != str:
        return False

    potential = True
    while potential == True:
        folderpath, tail = os.path.split(folderpath)
        if not folderpath:  # Reached root directory
            return False
        if os.path.exists(folderpath):
            return True
        if tail=='':
            return False

def print_terminal_spaced(text = " "):
    print("=============================================")
    print(" ")
    print(" ")
    print(" ")
    print(text)
    time.sleep(1.5)

def raise_exception(error_text = "Error, please check code. ", err = " ", hard = True):
    print(error_text + err)
    if hard:
        raise Exception (error_text)
    else:
        print('Continuing...')

def get_package_location(package_name):
  try:
    module = importlib.import_module(package_name)
    path = pathlib.Path(module.__file__).parent
    return str(path)
  except ImportError:
    return f"Package '{package_name}' not found."

  

#%% ######################################################### BOPS TESTING #################################################################

class Platypus:
    '''
    Platypus class to test the bops package
    usage:
        platypus = Platypus() # create an instance of the Platypus class
        platypus.run_tests() # run all tests
        platypus.print_happy() # print a happy platypus
        platypus.print_sad() # print a sad platypus
    '''
    def __init__(self):
        self.name = 'Platypus'
        self.dir_bops = get_dir_bops()
        self.mood = 'sad'
        self.output = None
        self.image_path = None
        self.photo = None
        
    def greet(self):
        print(f"Hello, my name is {self.name}!")
        
    def happy(self, message = ''):
        try:
            print(message) 
            self.image_path = os.path.join(self.dir_bops,'utils\platypus.jpg')
            self.show_image()
            self.mood = 'happy'
        except Exception as e:
            self.mood = 'sad'
            print('happy platypus image not found in ' + self.image_path)
            print(e)
        
    def sad(self):
        try:
            self.image_path = os.path.join(self.dir_bops,'utils\platypus_sad.jpg')
            self.show_image()
            self.mood = 'sad'
        except Exception as e:  
            print('sad platypus image not found in ' + self.image_path)
            print(e)
        
    def show_image(self):
        # Create a Tkinter window
        window = tk.Tk()
        # Load the image using PIL
        image = Image.open(self.image_path)
        # Create a Tkinter PhotoImage from the PIL image
        photo = ImageTk.PhotoImage(image)
        
        label = tk.Label(window, image=photo)
        label.image = photo
        label.pack()
        
        # Run the Tkinter event loop
        window.mainloop()
    
    def run_tests(self):
        print('running all tests ...')
        unittest.main()
        
        if self.mood == 'sad':
            self.sad()
        else:
            self.happy()
        
class test_bops(unittest.TestCase):
    
    ##### TESTS NOT WORKING ######
    def test_update_version(self):
        print('testing update_version ... ')
        self.assertRaises(Exception, update_version())
    
    def test_import_opensim(self):
        print('testing import opensim ... ')
        import opensim as osim
    
    def test_ProjectPaths(self):
        print('testing Project ... ')
        project_paths = ProjectPaths()
        # self.assertEqual(type(project_paths),ProjectPaths)
    
    def test_platypus(self):
        print('testing platypus ... ')
        platypus = Platypus()
        self.assertRaises(Exception, platypus.happy())
        self.assertEqual(type(platypus),Platypus)
        
    def test_create_grf_xml(self):
        print('testing create_grf_xml ... ')
        c3dFilePath = get_testing_file_path('c3d')
        create_grf_xml(c3dFilePath)
            
        
    not_working = False
    if not_working:                        
        def test_import_c3d_to_dict(self):
            print('testing import_c3d_to_dict ... ')
            
            c3dFilePath = get_testing_file_path('c3d')       
            
            self.assertEqual(type(c3dFilePath),str)
            self.assertTrue(os.path.isfile(c3dFilePath))        
            
            self.assertEqual(type(import_c3d_to_dict(c3dFilePath)),dict)
            
            # make sure that import c3d does not work with a string
            with self.assertRaises(Exception):
                import_c3d_to_dict(2)  
            
            
            filtered_emg = emg_filter(c3dFilePath)
            self.assertIs(type(filtered_emg),pd.DataFrame)
    
        def test_import_files(self):
            
            print('testing import_files ... ')


            for subject_folder in get_subject_folders():
                for session in get_subject_sessions(subject_folder):
                    session_path = os.path.join(subject_folder,session)           
                    for trial_name in get_trial_list(session_path,full_dir = False):
                        file_path = get_trial_dirs(session_path, trial_name)['id']
                        data = import_file(file_path)
            
            self.assertEqual(type(data),pd.DataFrame)
    
        def test_writeTRC(self):
            print('testing writeTRC ... ')
            trcFilePath = get_testing_file_path('trc')
            c3dFilePath = get_testing_file_path('c3d')
            writeTRC(c3dFilePath, trcFilePath)
        
        def test_c3d_export(self):
            print('testing c3d_export ... ')
            c3dFilePath = get_testing_file_path('c3d')
            c3d_dict = import_c3d_to_dict(c3dFilePath)
            self.assertEqual(type(c3d_dict),dict)
            c3d_osim_export(c3dFilePath)
        
        def test_get_testing_data(self):
            print('getting testing data')
            self.assertTrue(get_testing_file_path('id'))
        
        def test_opensim(self):
            print('testing opensim ... ')
            import opensim as osim
            self.assertTrue(osim.__version__ > '4.2')

    ###### TESTS FAILING ######
    # def test_loop_through_folders(self):
    #     print('testing loop through folders ... ')
    #     for subject_folder in get_subject_folders(get_testing_file_path()):
    #         for session in get_subject_sessions(subject_folder):
    #             session_path = os.path.join(subject_folder,session)
    #             for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

    #                 resultsDir = get_trial_list(session_path,full_dir = True)[idx]
    #                 self.assertEqual(resultsDir,str)
    #                 return
    
  
    ###### TESTS TO COMPLETE ######
    # def to_be_finished_test_add_marker_to_trc():
    #     print('testing add_marker_trc ... ')
        
    # def to_be_finished_test_IK():
    #     print('testing IK ... ')
    #     for subject_folder in get_subject_folders(get_testing_file_path()):
    #         for session in get_subject_sessions(subject_folder):
    #             session_path = os.path.join(subject_folder,session)
    #             for idx, trial_name in enumerate(get_trial_list(session_path,full_dir = False)):

    #                 model_path = r'.\test.osim'
    #                 ik_results_file = r'.\test.osim'
    #                 mot_file = r'.\test.osim'
    #                 grf_xml = r'.\test.osim'
    #                 resultsDir = get_trial_list(session_path,full_dir = True)[idx]
    #                 run_IK(model_path, trc_file, resultsDir, marker_weights_path)
    

#%% ######################################################### BOPS MAIN ####################################################################
if __name__ == '__main__':   
    if bops.__testing__:
        print('runnung all tests ...')
        unittest.main()
        
    Platypus().happy()
    
    
    
# end