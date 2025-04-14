import pandas as pd
from tkinter import Tk, filedialog
import matplotlib.pyplot as plt
import os
import unittest
import msk_modelling_python as msk
import seaborn as sns
import screeninfo



# the functions below assume that the CSV files have the same structure unless otherwise specified
# the first column in the CSV files should be named "time" or "frame"


def select_file(initialdir=os.path.dirname(os.path.abspath(__file__))):
    # select single file. Default directory is the directory of the script
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(initialdir=initialdir, title="Select file", filetypes=(("CSV files", "*.csv"), ("all files", "*.*")))
    return file_path

def select_multiple_files(initialdir=os.path.dirname(os.path.abspath(__file__))):
    # select multiple files from same folder. Default directory is the directory of the script
    root = Tk()
    root.withdraw()
    files = filedialog.askopenfilenames(initialdir=initialdir, title="Select multiple files", filetypes=(("CSV files", "*.csv"), ("all files", "*.*")))
    return files

def get_screen_size():
    # Get the screen size
    Tk().withdraw()

def set_relative_figure_size(width=0.8, height=0.8):
    # Set the relative size of the figure
    plt.figure(figsize=(plt.gcf().get_size_inches()[0] * width, plt.gcf().get_size_inches()[1] * height))

def plot_curves(file1, file2):
    # Read the CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Get the header names
    header1 = df1.columns[0]
    header2 = df2.columns[0]

    # Check if the header names are "time" or "frame"
    if header1.lower() in ["time", "frame"] and header2.lower() in ["time", "frame"]:
        # Plot the curves
        plt.plot(df1[header1], label=f"{file1}_{header1}")
        plt.plot(df2[header2], label=f"{file2}_{header2}")

        # Add labels and legend
        plt.xlabel("X-axis")
        plt.ylabel("Y-axis")
        plt.legend()

        # Show the plot
        plt.show()
    else:
        print("The first column in both files should be named 'time' or 'frame.'")

def plot_multiple_curves(files):
    for file in files:
        df = pd.read_csv(file)
        header = df.columns[0]
        if header.lower() in ["time", "frame"]:
            plt.plot(df[header], label=f"{file}_{header}")
        else:
            print(f"The first column in {file} should be named 'time' or 'frame.'")
    plt.xlabel("X-axis")
    plt.ylabel("Y-axis")
    plt.legend()
    plt.show()

def spider(files):
    # Read the CSV files
    
    for file in files:
        df = pd.read_csv(file)
        header = df.columns[0]
        if header.lower() in ["time", "frame"]:
            plt.plot(df[header], label=f"{file}_{header}")
        else:
            print(f"The first column in {file} should be named 'time' or 'frame.'")
    plt.xlabel("X-axis")
    plt.ylabel("Y-axis")
    plt.legend()
    
    
    return None

def dataFrame(df, x='time', single_plot=False, show=False):
    '''
    Plot the data in a dataframe
    df: pandas dataframe
    x: x-axis column name
    single_plot: boolean, default False
    show: boolean
    '''
    
    if type(df) != pd.DataFrame:
        print("Error: The input data is not a pandas dataframe")
        return None
    
    # Plot the data 
    if single_plot:
        for column in df.columns[1:]:
            plt.plot(df[x], df[column], label=column)
        plt.xlabel(x)
        labels = [col for col in df.columns if col != x]
        plt.legend(labels)
        
    else:
        num_columns = 2  # Number of columns in the grid
        num_rows = (len(df.columns) - 1 + num_columns - 1) // num_columns  # Calculate the number of rows needed

        fig, axes = plt.subplots(num_rows, num_columns, figsize=(15, num_rows * 5))
        axes = axes.flatten()  # Flatten the 2D array of axes to 1D for easy iteration

        for i, column in enumerate(df.columns[1:]):
            axes[i].plot(df[x], df[column], label=column)
            axes[i].set_xlabel(x)
            axes[i].set_title(column)
            axes[i].legend()

        # Hide any unused subplots
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        plt.tight_layout()
        
    
    if show:
        plt.show()
        set_relative_figure_size(width=0.8, height=0.8)
     
def sto_file(filepath=None):
    
    if not filepath:
        filepath = select_file()
    
    if not filepath.endswith('.sto'):
        print("Warning: The function may not work as expected.")
    
    df = pd.read_table(filepath, sep='\t', skiprows=6)
    print(df.head())
    import pdb; pdb.set_trace()
    
    
# Testing the functions using unittest module when the script is run directly
class test(unittest.TestCase):
    # for each function assign True or false to run the test
    
    def test_plot_curves(self, run = False):
        if run:
            print('testing plot_curves ... ')
            file1 = select_file()
            plot_curves(file1, file1)
                    
    def test_plot_multiple_curves(self, run = False):
        if run:
            print('testing plot_multiple_curves ... ')
            files = select_multiple_files()
            plot_multiple_curves(files)
  
    def test_spider(self, run = False):
        if run:
            print('testing spider ... ')
            files = select_multiple_files()
            spider(files)

    def show_plot(self, run = False):
        if run:
            plt.show()
            
    def test_DataSet(self, run = True):
        if run:
            print('testing DataSet ... ')   
            data = DataSet()
            data.plot_lines(show=False)
            data.correlation_matrix(show=False)
            data.show()
    

if __name__ == "__main__":
    
    # output = unittest.main(exit=False)
    msk.ui.show_warning("Warning: This is function is testing but may not work when run directly. Please import the functions in another script.")

    
    # create figute with 5x3 subplots
    fig, axs = plt.subplots(5, 3)
    fig.suptitle('Subplots')
    
    # activate the subplots IK (first row)
    trial1 = msk.ui.select_file("Select a file to plot: ")
    trial2 = msk.ui.select_file("Select a second file to plot file: ")
    
    trial1_df = pd.read_csv(trial1, sep='\\t' ,skiprows=9)
    trial2_df = pd.read_excel(trial2, skiprows=10)
    
    
    plt.sca(axs[0, 0])
    plt.plot(trial1_df, trial2_df)
    
    plt.show()
            
   

# END