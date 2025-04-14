import matplotlib.pyplot as plt

def mmfn():
    # Set the style of the plot
    plt.style.use('seaborn-whitegrid')

    # Set the font size for the plot
    plt.rcParams.update({'font.size': 12})

    # Set the figure size
    ax = plt.gca()

    # Customize the axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.spines['left'].set_linewidth(0.5)
    ax.tick_params(axis='both', which='both', length=0)

    # Customize the grid
    ax.grid(color='gray', linestyle='--', linewidth=0.5)

if __name__ == '__main__':
    mmfn()
    plt.show()