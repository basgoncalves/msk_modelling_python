import scipy.io
import opensim as osim
from bops import *

def get_matlab_data(mat_file_path):
    # Load the .mat file
    data = scipy.io.loadmat(mat_file_path)

    # Do further processing with the loaded data
    # ...

    return data
    # Specify the path to the .mat file
    mat_file_path = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_90\settings.mat"

    # Load the .mat file
    data = scipy.io.loadmat(mat_file_path)


    print(type(data))
    print(data.keys())
    print(type(data['cycle'][0][0][0][0]))
    print((data['cycle'][0][0][0][0]))
    print(len(data['cycle'][0][0][0][0]))
    print(type(data['duration'][0]))
    print((data['duration'][0]))
    print((data['firstFrame'][0]))
    # ...

    # Do further processing with the loaded data
    # ...


import xml.etree.ElementTree as ET

def print_excitation_input_pairs(xml_path):
    with open(xml_path, 'r', encoding='utf-8') as file:
        tree = ET.parse(xml_path)
        root = tree.getroot()

    # Get the input signals
    input_signals = root.find('./inputSignals')
    input_signal_names = input_signals.text.split()

    
    # Iterate through excitation elements and print pairs
    for excitation in root.findall('./mapping/excitation'):
        excitation_id = excitation.get('id')
        input_element = excitation.find('input')
        input_value = input_element.text if input_element is not None else None

# xml_path = r'C:\Git\isbs2024\Data\Simulations\Athlete_03\ceinms_shared\ceinms_excitation_generator.xml'
# print_excitation_input_pairs(xml_path)


# END