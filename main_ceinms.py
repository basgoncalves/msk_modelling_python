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
    def __init__(self, id, age, group, column2, column3, column4, column5, column6, column7, column8, column9, column10):
        self.id = id
        self.age = age
        self.group = group
        self.column2 = column2
        self.column3 = column3
        self.column4 = column4
        self.column5 = column5
        self.column6 = column6
        self.column7 = column7
        self.column8 = column8
        self.column9 = column9
        self.column10 = column10

simulations_folder = r'C:\Git\msk_modelling_python\example_data\running\simulations'
main_folder = os.path.dirname(simulations_folder)
subjectcsv = os.path.join(main_folder, 'subjectinfo.csv')

def add_s_to_subject_info_id(subjectcsv):
    df = pd.read_csv(subjectcsv)
    df['id'] = 's' + df['id'].astype(str).str.zfill(3)
    df.to_csv(os.path.join(main_folder, subjectcsv), index=False)
    
    print('file saved at: ' + os.path.join(main_folder, subjectcsv))

def print_columns(subjectcsv, column_name = 'group'):
    df = pd.read_csv(subjectcsv)   
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

print_id_values(subjectcsv, column_name = 'jcffai', value = 'Yes')