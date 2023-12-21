import os
import re 
import sys
import tkinter as tk
from tkinter import filedialog, Text
import unittest
import subprocess
import pkg_resources
from src.add_to_system_path import is_admin
from src import download_dependencies

# dowload required packages
# download_dependencies.create_virtual_environment()
# download_dependencies.create_requirements()
# download_dependencies.install_requirements()

from src import database_tools
import pandas as pd
import pandas as pd

def print_design():
    print('copyright by Basilio Goncalves')
    
class subject:
    def __init__(self, id, age, weight, height, leg_length, group, symptomatic_side, measured_leg, dominant_leg, 
                 running_phase, alpha_angle_max, intramuscular, fadir, faber, pain,test):
        self.id = id
        self.age = age
        self.weight = weight
        self.height = height
        self.leg_length = leg_length
        self.group = group
        self.symptomatic_side = symptomatic_side
        self.measured_leg = measured_leg
        self.dominant_leg = dominant_leg
        self.running_phase = running_phase
        self.alpha_angle_max = alpha_angle_max
        self.intramuscular = intramuscular
        self.fadir = fadir
        self.faber = faber
        self.pain = pain
        self.test = test

class subject_with_variable_keys:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

subject_instance = subject_with_variable_keys() # create an empty subject instance
subject_instance.new_key = "new_value" # add a new key to the subject instance

def find_number_of_keys_in_subject():
    try:
        s = subject()
    except Exception as e:
        str_after_init = e.__str__().split("__init__() missing ")[1]
        number_of_keys = int(str_after_init[0:2])
        print(number_of_keys)
        
        str_after_arg = e.__str__().split("positional arguments: ")[1]
        key_names = str_after_arg.replace("'","").replace('and ','').split(", ") # remove "'", "and", and split by ', '
      
        if not len(key_names) == number_of_keys:
            print('error: number of keys and number of arguments do not match')
        
    return number_of_keys, key_names

    

def add_s_to_subject_info_id(subjectcsv):
    df = pd.read_csv(subjectcsv)
    df['id'] = 's' + df['id'].astype(str).str.zfill(3)
    df.to_csv(os.path.join(main_folder, subjectcsv), index=False)
    
    print('file saved at: ' + os.path.join(main_folder, subjectcsv))

def print_columns(subjectcsv, column_name = 'group'):
    df = pd.read_csv(subjectcsv)   
    
    if column_name == 'column':
        print(df.columns)
    else:
        for column in df[column_name]:
            print(column)
    
def convert_camel_case_to_snake_case(old_string):
    # turn cammel to snake case (e.g aE => a_e)
    pattern = re.compile(r'([a-z])([A-Z])')
    snake_case_string = re.sub(pattern, r'\1_\2', old_string)
    
    new_string = snake_case_string.lower().replace(" ", "_")
    
    return new_string

def replace_headers_with_camel_case(subjectcsv):
    df = pd.read_csv(subjectcsv)
    new_columns = [convert_camel_case_to_snake_case(col) for col in df.columns]
    df.columns = new_columns
    df.to_csv(os.path.join(main_folder, subjectcsv), index=False)
    
    print('file saved at: ' + os.path.join(main_folder, subjectcsv))    

def print_id_values(subjectcsv, column_name = 'jcffai', value = 'Yes'):
    df = pd.read_csv(subjectcsv)
    filtered_df = df.loc[df['jcffai'] == 'Yes']
    print('id values for ' + column_name + ' = ' + value)
    print(filtered_df['id'].values)
    
    return filtered_df['id'].values

def create_subject_from_csv_row(subjectcsv, id='s001'):
    df = pd.read_csv(subjectcsv)
    row = df.loc[df['id'] == id]
    
    _, key_names = find_number_of_keys_in_subject() # get the key names from the subject class
    
    # create an empty subject instance
    if not row.empty:
        for header in row.columns:
            if header in key_names:
                setattr(subject, header, row[header].values[0])
        return subject
    else:
        return None

# input the paths
simulations_folder = r'C:\Git\running_fai\simulations'
main_folder = os.path.dirname(simulations_folder)
subjectcsv = os.path.join(main_folder, 'subjectinfo.csv')

# functions to manipulate the database and create subject from it
def make_subjectcsv_pretty(subjectcsv):
    print_id_values(subjectcsv, column_name = 'jcffai', value = 'Yes')
    print_columns(subjectcsv, column_name = 'column')
    print(create_subject_from_csv_row(subjectcsv, id='s010').pain)



