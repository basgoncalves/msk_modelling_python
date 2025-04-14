# IMPORT LIBRARIES
from multiprocessing import current_process
from pathlib import Path
import pandas as pd
import sqlite3 
import os
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from pandas.api.types import is_numeric_dtype

# CREATE SQL FIELDS FROM CSV
def create_sql_fields(df):                                          # gather the headers of the CSV and create two strings 
    fields_sql = []                                                 # str1 = var1 TYPE, va2, TYPE ...
    header_names = []                                               # str2 = var1, var2, var3, var4
    for col in range(0,len(df.columns)):
        fields_sql.append(df.columns[col])
        fields_sql.append(str(df.dtypes[col]))

        header_names.append(df.columns[col])
        if col != len(df.columns)-1:
            fields_sql.append(',')
            header_names.append(',')

    fields_sql = ' '.join(fields_sql)
    fields_sql = fields_sql.replace('int64','integer')
    fields_sql = fields_sql.replace('float64','integer')
    fields_sql = fields_sql.replace('object','text')

    header_sql_string = '(' + ''.join(header_names) + ')'
    
    return fields_sql, header_sql_string


def csv_to_db(csv_filedir):

    # SELECT CSV FILE PATH AND LOAD DATA

    if not Path(csv_filedir).is_file():                                                             # if needed ask for user to input directory of CVS file 
        current_path = os.getcwd()
        Tk().withdraw()                                     
        csv_filedir = askopenfilename(initialdir=current_path)      
    try:
        data = pd.read_csv(csv_filedir)                                                             # load CSV file
    except:
        print("Something went wrong when opening to the file")
        print(csv_filedir)

    # STRUTURE DATA
    csv_df = pd.DataFrame(data)
    for col in csv_df.columns:
        if is_numeric_dtype(csv_df[col].dtype)==0:
            csv_df[col] = csv_df[col].str.replace("\'", "\'\'")                                  # replace " ' " for " '' " for SQL in each column
    csv_df = csv_df.fillna('NULL')                                                               # make NaN = to 'NULL' for SQL format 


    # CREATE EMPTY DATABASE
    [path,filename] = os.path.split(csv_filedir)                                                 # define path and filename for .db file
    [filename,_] = os.path.splitext(filename)
    database_filedir = os.path.join(path, filename + '.db')
    conn = sqlite3.connect(database_filedir)                                                     # connect to SQL server
    [fields_sql, header_sql_string] = create_sql_fields(csv_df)
    create_sql = ''.join(['CREATE TABLE IF NOT EXISTS ' + filename + ' (' + fields_sql + ')'])
    cursor = conn.cursor()
    cursor.execute(create_sql)


    # INSERT EACH ROW IN THE SQL DATABASE
    csv_tuple = csv_df.values.tolist()                                                             # convert df to list
    for irow in csv_tuple:
        insert_values_string = ''.join(['INSERT INTO ', filename, header_sql_string, ' VALUES'])   
        insert_sql = f"{insert_values_string} {tuple(irow)}"                                        # convert each row list to tuple and to string
        print(insert_sql)
        cursor.execute(insert_sql)                                                                  # add row to database

    # COMMIT CHANGES TO DATABASE AND CLOSE CONNECTION
    conn.commit()                                                                                   # commit changes
    conn.close()                                                                                    # close database

    print('\n' + csv_filedir + ' \n converted to \n' + database_filedir)

    return database_filedir


csv_to_db('')