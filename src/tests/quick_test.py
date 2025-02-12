import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Sample DataFrame (replace with your actual DataFrame)
data = {'threshold': [10, 15, 20, 10, 15, 20, 10, 15, 20],
        'covered_area': [7391.232877, 12476.212893, 16725.837971, 
                         5842.719398, 10108.066135, 13878.470279, 
                         4835.434849, 8707.562546, 13374.003104],
        'time': [7.758052, 5.285596, 5.621986, 
                 7.609042, 5.015001, 5.701381, 
                 4.915967, 4.513439, 4.546807],
        'subject': [9, 9, 9, 10, 10, 10, 10, 10, 10]}
df = pd.DataFrame(data)

# Group data by subject and threshold
grouped_df = df.groupby(['subject', 'threshold'])['covered_area'].mean().reset_index()

# Create a figure and axes
fig, ax = plt.subplots()

# Define x positions for each subject's bars
x = np.arange(len(grouped_df['subject'].unique()))
width = 0.2

# Create grouped bar plot with appropriate x positions
for i, (subject, group_df) in enumerate(grouped_df.groupby('subject')):
    x_pos = x[i] + np.arange(len(group_df)) * width - (len(group_df) - 1) * width / 2
    ax.bar(x_pos, group_df['covered_area'], width=width, label=f'Subject {subject}')

# Set x-axis labels with subject names
ax.set_xticks(x)
ax.set_xticklabels(grouped_df['subject'].unique())

# Set x-axis label
ax.set_xlabel('Subject')

# Set y-axis label
ax.set_ylabel('Covered Area')

# Set title
ax.set_title('Covered Area by Threshold and Subject')

# Add legend
ax.legend()

# Show the plot
plt.show()