import pandas as pd
from tabulate import tabulate
# from trc import TRCData
import numpy as np
import os
from trc import TRCData

from pyomeca import Analogs

current_script_path = os.path.dirname(__file__)
data_path = os.path.join(current_script_path,"/tests/data/markers_analogs.c3d")

if not os.path.exists(data_path):
    print(data_path + " does not exist")
    print("Please download the data from here")
    exit()

muscles = [
    "Delt_ant",
    "Delt_med",
    "Delt_post",
    "Supra",
    "Infra",
    "Subscap",
]
emg = Analogs.from_c3d(data_path, suffix_delimiter=".", usecols=muscles)
emg.plot(x="time", col="channel", col_wrap=3)


exit()
#%% trc function copied from C:\Users\Bas\AppData\Local\Programs\Python\Python38\Lib\site-packages\trc.py
_REQUIRED_HEADER_KEYS = ['DataRate', 'CameraRate', 'NumFrames', 'NumMarkers', 'Units', 'OrigDataRate']
_HEADER_KEYS = ['DataRate', 'CameraRate', 'NumFrames', 'NumMarkers', 'Units', 'OrigDataRate', 'OrigDataStartFrame', 'OrigNumFrames']
_HEADER_TYPES = [float, float, int, int, str, float, int, int]
_COORDINATE_LABELS = ['X', 'Y', 'Z']


def _convert_header_key_value_to_type(key, value):
    index = _HEADER_KEYS.index(key)
    if _HEADER_TYPES[index] is float:
        return float(value)
    elif _HEADER_TYPES[index] is int:
        return int(value)

    return str(value)


def _convert_to_number(string):
    try:
        num = float(string)
    except ValueError:
        num = float('nan')
    return num


def _convert_coordinates(coordinates):
    return [_convert_to_number(value) for value in coordinates]


class TRCData(dict):
    """
    A trc data object when populated via 'load' or 'parse' contains motion capture data.
    For a valid trc file the following keys will be present (among others):
    - FileName
    - DataFormat
    - Markers
    - DataRate
    - NumFrames
    - NumMarkers

    Each marker found in the header part of the data will be a key in the dictionary containing a list
    of the coordinates for that label at each frame.
    """

    def _append_per_label_data(self, markers, data):
        for index, marker_data in enumerate(data):
            self[markers[index]] += [marker_data]

    def _process_contents(self, contents):
        markers = []
        file_header_keys = []
        data_header_markers = []
        data_format_count = 0
        header_read_successfully = False
        current_line_number = 0
        for line in contents:
            current_line_number += 1
            line = line.strip()
            if current_line_number == 1:
                # File Header 1
                sections = line.split('\t')
                if len(sections) != 4:
                    raise IOError('File format invalid: Header line 1 does not start have four sections.')
                self[sections[0]] = sections[1]
                self['DataFormat'] = sections[2]
                data_format_count = len(sections[2].split('/'))
                self['FileName'] = sections[3]
            elif current_line_number == 2:
                # File Header 2
                file_header_keys = line.split('\t')
            elif current_line_number == 3:
                # File Header 3
                file_header_data = line.split('\t')
                if len(file_header_keys) == len(file_header_data):
                    for index, key in enumerate(file_header_keys):
                        if key == 'Units':
                            self[key] = file_header_data[index]
                        else:
                            self[key] = float(file_header_data[index])
                else:
                    raise IOError('File format invalid: File header keys count (%d) is not equal to file header '
                                'data count (%d)' % (len(file_header_keys), len(file_header_data)))
            elif current_line_number == 4:
                # Data Header 1
                data_header_markers = line.split('\t')
                if data_header_markers[0] != 'Frame#':
                    raise IOError('File format invalid: Data header does not start with "Frame#".')
                if data_header_markers[1] != 'Time':
                    raise IOError('File format invalid: Data header in position 2 is not "Time".')

                self['Frame#'] = []
                self['Time'] = []
            elif current_line_number == 5:
                # Data Header 1
                data_header_sub_marker = line.split('\t')
                if len(data_header_markers) != len(data_header_sub_marker):
                    raise IOError('File format invalid: Data header marker count (%d) is not equal to data header '
                                'sub-marker count (%d)' % (len(data_header_markers), len(data_header_sub_marker)))

                # Remove 'Frame#' and 'Time' from array of markers.
                data_header_markers.pop(0)
                data_header_markers.pop(0)
                markers = []
                for marker in data_header_markers:
                    marker = marker.strip()
                    if len(marker):
                        self[marker] = []
                        markers.append(marker)

                self['Markers'] = markers
            elif current_line_number == 6 and len(line) == 0:
                # Blank line
                header_read_successfully = True
            else:
                # Some files don't have a blank line at line six
                if current_line_number == 6:
                    header_read_successfully = True
                # Data section
                if header_read_successfully:
                    sections = line.split('\t')

                    try:
                        frame = int(sections.pop(0))
                        self['Frame#'].append(frame)
                    except ValueError:
                        if int(self['NumFrames']) == len(self['Frame#']):
                            # We have reached the end of the specified frames
                            continue
                        else:
                            raise IOError(
                                f"File format invalid: Data frame {len(self['Frame#'])} is not valid.")

                    time = float(sections.pop(0))
                    self['Time'].append(time)

                    line_data = [[float('nan')] * data_format_count] * int(self['NumMarkers'])
                    len_section = len(sections)
                    expected_entries = len(line_data) * data_format_count
                    if len_section > expected_entries:
                        print(f'Bad data line, frame: {frame}, time: {time}, expected entries: {expected_entries},'
                            f' actual entries: {len_section}')
                        self[frame] = (time, line_data)
                        self._append_per_label_data(markers, line_data)
                    elif len_section % data_format_count == 0:
                        for index, place in enumerate(range(0, len_section, data_format_count)):
                            coordinates = _convert_coordinates(sections[place:place + data_format_count])
                            line_data[index] = coordinates

                        self[frame] = (time, line_data)
                        self._append_per_label_data(markers, line_data)
                    else:
                        raise IOError('File format invalid: Data frame %d does not match the data format' % len_section)

    def parse(self, data):
        """
        Parse trc formatted motion capture data into a dictionary like object.

        :param data: The multi-line string of the data to parse.
        """
        contents = data.split('\n')
        self._process_contents(contents)

    def load(self, filename):
        """
        Load a trc motion capture data file into a dictionary like object.

        :param filename: The name of the file to load.
        """
        with open(filename, 'rb') as f:
            contents = f.read().decode()

        contents = contents.split(os.linesep)
        self._process_contents(contents)

    def save(self, filename):
        if 'PathFileType' in self:
            header_line_1 = f"PathFileType\t{self['PathFileType']}\t{self['DataFormat']}\t{self['FileName']}{os.linesep}"
        else:
            raise NotImplementedError('Do not know this file type.')

        # Check that all known header keys are present
        for header_key in _HEADER_KEYS:
            if header_key not in self:
                raise KeyError(f'Could not find required header key: {header_key}')

        data_format_count = len(self['DataFormat'].split('/'))

        header_line_2 = '\t'.join(_HEADER_KEYS) + os.linesep
        header_line_3 = '\t'.join([str(_convert_header_key_value_to_type(key, self[key])) for key in _HEADER_KEYS]) + os.linesep

        coordinate_labels = _COORDINATE_LABELS[:data_format_count]
        markers_header = [entry for marker in self['Markers'] for entry in [marker, '', '']]
        marker_sub_heading = [f'{coordinate}{i + 1}' for i in range(len(self['Markers'])) for coordinate in coordinate_labels]
        data_header_line_1 = 'Frame#\tTime\t' + '\t'.join(markers_header).strip() + os.linesep
        data_header_line_2 = '\t\t' + '\t'.join(marker_sub_heading) + os.linesep

        blank_line = os.linesep

        with open(filename, 'w') as f:

            f.write(header_line_1)
            f.write(header_line_2)
            f.write(header_line_3)

            f.write(data_header_line_1)
            f.write(data_header_line_2)

            f.write(blank_line)

            for frame in self['Frame#']:
                time, line_data = self[frame]
                values = [f'{v:.5f}' for values in line_data for v in values]
                numeric_values = '\t'.join(values)
                f.write(f'{frame}\t{time:.3f}\t{numeric_values}{os.linesep}')


#%% my functions	
# df = pd.DataFrame(np.array([[1,2,6], [3,4,5],[8,9,3]]), columns=['a','b','c'])
def add_marker_data(trc_data,marker_name,data_list):
    # Check if trc_data is an instance of TRCData
    if not isinstance(trc_data, TRCData):
        raise ValueError("trc_data must be an instance of TRCData")
    
    # Check if data_list has 3 columns
    if len(data_list[0]) != 3:
        raise ValueError("data_list must have 3 columns")
    
    # Add or update marker data in trc_data
    trc_data[marker_name] = data_list

    # Add marker name to the list of markers
    trc_data['Markers'].append(marker_name)

    return trc_data

#%% test TRCData
file_path = r"C:\Git\research_documents\Uvienna\Bachelors_thesis_supervision\2023W\ksenija_jancic_spowi\data\Mocap\037\Run_baselineA1\markers.trc"
file_path = r"C:\Users\Bas\Desktop\markers_example.trc"
trc_data = TRCData()
print(trc_data)
# %% test TRCData continue (save new file)
trc_data.load(file_path)
trc_data.save(file_path.replace('.trc', '_2.trc'))

num_frames = int(trc_data['NumFrames'])

trc_data['OrigNumFrames'] = num_frames

data_list = np.random.rand(num_frames, 3) 
trc_data = add_marker_data(trc_data,'new_marker2',data_list)
trc_data.save(file_path.replace('.trc', '_2.trc'))

# %%
    
def f():
    pass    

#%%

