import opensim as osim
import os
import pandas as pd
import matplotlib.pyplot as plt
import math
import numpy as np
from sklearn.metrics import mean_squared_error
import ceinms_setup as cs
import bops as bp


def mmfn():
    fig = plt.gcf()
    fig.set_tight_layout(True)

def plot_df(df, columns_to_plot='all',xlabel=' ',ylabel=' ', legend=['data1', 'data2'],save_path='', title=''):
    if columns_to_plot == 'all':
        columns_to_plot = df.columns
    
    nrows = 2
    ncols = int(len(columns_to_plot)/2)

    # Create a new figure and subplots
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

    fig.set_tight_layout(True)

    if save_path:
        plt.savefig(save_path)
    
    return fig, axs

def plot_two_df(df1,df2,axs):
    
    for row, ax_row in enumerate(axs):
        for col, ax in enumerate(ax_row):
            ncols = len(ax_row)

            ax_count = row * ncols + col

            # remove extra axes
            if ax_count >= len(df1.columns):
                ax.remove()
                continue

            heading = df1.columns[ax_count]
            if heading not in df2.columns:  
                print(f'Heading not found: {heading}')
                continue
            
            # calculate RMS error
            error = np.sqrt(mean_squared_error(df1[heading],df2[heading]))
            error_text = f'RMS error: {error:.2f}'
            # Plot data
            ax.plot(df1[heading])
            ax.plot(df2[heading])
            ax.set_title(f'{heading}')
            ax.text(0.95, 0.95, error_text, fontsize=10, color='black',
                    ha='right', va='top', transform=ax.transAxes)

def compare_moments(id_path, ceinms_path,save_folder):
    mom_id = bp.import_sto_data(id_path)
    mom_ceinms = bp.import_sto_data(ceinms_path)

    mom_id = mom_id.drop(columns=['time'])
    mom_ceinms = mom_ceinms.drop(columns=['time'])

    nrows = 2
    ncols = int(len(mom_ceinms.columns)/2)

    # Create a new figure and subplots
    fig, axs = plt.subplots(nrows, ncols, figsize=(15, 5))
    for row, ax_row in enumerate(axs):
        for col, ax in enumerate(ax_row):
            ax_count = row * ncols + col

            heading = mom_ceinms.columns[ax_count]    
            heading_id = heading + '_moment'

            if heading_id not in mom_id.columns:
                print(f'Heading not found: {heading}')
                continue    
            else:
                print(f'Plotting: {heading}')
            
            # calculate RMS error
            error = np.sqrt(mean_squared_error(mom_id[heading_id],mom_ceinms[heading]))
            error_text = f'RMS error: {error:.2f}'
            # Plot data
            ax.plot(mom_id[heading_id])
            ax.plot(mom_ceinms[heading])
            ax.set_title(f'{heading}')
            ax.text(0.95, 0.95, error_text, fontsize=10, color='black',
                    ha='right', va='top', transform=ax.transAxes)
            
            if row == 1:
                ax.set_xlabel('Time')
            if col == 0:
                ax.set_ylabel('Moment (Nm)')

    plt.legend(['inverse dynamics', 'ceinms'])

    # Adjust spacing between subplots
    plt.tight_layout()

    if not save_folder:
        save_folder = os.path.join(os.path.dirname(id_path), 'moment_errors.png')
    
    if not os.path.exists(save_folder):
        os.mkdir(save_folder)
    
    trial_name = os.path.basename(id_path).split('.')[0]
    plt.savefig(os.path.join(save_folder, trial_name + "moment_errors.png"))

    print(f'Saved to: {save_folder}')

def compare_two_df(df1,df2, columns_to_compare='all',xlabel=' ',ylabel=' ', legend=['data1', 'data2'],save_path=''):
    if len(columns_to_compare) == 1 and columns_to_compare == 'all':
        columns_to_compare = df1.columns
    
    N = len(columns_to_compare)
    if N  > 2:
        ncols = math.ceil(math.sqrt(N))
        nrows = math.ceil(N / ncols)
    elif N  == 0:
        print('No columns to plot')
        print('could not save figure')
        fig = [] 
        axs = []
        return fig, axs 
    else:
        ncols = N
        nrows = 1
    
    # remove columns that are not in the variable columns_to_compare
    try:
        df1 = df1[columns_to_compare]
        df2 = df2[columns_to_compare]
    except KeyError as e:
        print(f'KeyError: {e}')
        print(f'Columns in df1: {df1.columns}')
        print(f'Columns in df2: {df2.columns}')
        
    
    if (len(df1.columns) == 0 or len(df2.columns) == 0) or len(df1.columns) != len(df2.columns):
        print('number of columns does not match between df1 and df2')
        fig = [] 
        axs = []
        return fig, axs

    # Create a new figure and subplots
    fig, axs = plt.subplots(nrows, ncols, figsize=(15, 5))
    
    plot_two_df(df1,df2,axs)

    plt.legend(legend)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    fig.set_tight_layout(True)

    if save_path:
        save_fig(fig, save_path)
    
    return fig, axs

def plot_sum_muscle_forces_integral(df, columns_to_plot='all',xlabel=' ',ylabel=' ', legend=['data1', 'data2'],save_path='', title=''):
    
    if columns_to_plot == 'all':
        columns_to_plot = df.columns

    nrows = 2
    ncols = int(len(columns_to_plot)/2)

    # Create a new figure and subplots
    fig, axs = plt.subplots(nrows, ncols, figsize=(15, 5))

    for row, ax_row in enumerate(axs):
        for col, ax in enumerate(ax_row):
            ax_count = row * ncols + col

            heading = columns_to_plot[ax_count]    
            if heading not in df.columns:
                print(f'Heading not found: {heading}')
                continue    
            
            # Plot data
            AUC = df[heading].sum()
            ax.plot(AUC)
            ax.set_title(f'{heading}')
            
            if row == 1:
                ax.set_xlabel(xlabel)
            if col == 0:
                ax.set_ylabel(ylabel)

    plt.legend(legend)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    fig.set_tight_layout(True)

    if save_path:
        plt.savefig(save_path)

    return fig, axs

def save_dataframe_as_sto(df, filepath):
    df.to_csv(filepath, sep='\t', index=False)

def plot_muscle_work_per_leg(df): # plot muscle work as bar chart split by right and left

    # Separate columns based on the last letter
    df_r = df.loc[:, df.columns[df.columns.str.endswith('_r')]]
    df_l = df.loc[:, df.columns[df.columns.str.endswith('_l')]]

    # Transpose the DataFrames for easier plotting
    df_r_transposed = df_r.T.reset_index()
    df_l_transposed = df_l.T.reset_index()

    # Plot the bar chart with different colors for '_r' and '_l'
    plt.figure(figsize=(12, 6))
    bar_width = 0.35
    index = range(len(df_r_transposed))

    plt.bar(index, df_r_transposed[0], width=bar_width, label='_r', color='blue', align='center')
    plt.bar([i + bar_width for i in index], df_l_transposed[0], width=bar_width, label='_l', color='orange', align='center')

    plt.xticks([i + bar_width/2 for i in index], df_r_transposed['index'], rotation=45, ha='right')

    plt.xlabel('')
    plt.ylabel('Muscle work (N.s)')
    plt.title(' ')
    plt.xticks([i + bar_width/2 for i in index], df_r_transposed['index'])
    plt.legend(['right', 'left'])
    plt.tight_layout()
    
    return plt.gcf()

def save_fig(fig, save_path):
    if not os.path.exists(os.path.dirname(save_path)):
            os.mkdir(os.path.dirname(save_path))

    fig.savefig(save_path)

def muscles_to_plot():
    return []

# END