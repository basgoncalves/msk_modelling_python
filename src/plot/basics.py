import pandas as pd
from tkinter import Tk, filedialog
import matplotlib.pyplot as plt
import os

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



if __name__ == "__main__":
    
    # # Example usage
    # file1 = select_file()
    # file2 = select_file()
    # plot_curves(file1, file2)

    # Example usage for multiple files
    files = select_multiple_files()
    plot_multiple_curves(files)



# END