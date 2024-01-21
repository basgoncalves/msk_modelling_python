from matplotlib import pyplot as plt

nrows = 2
ncols = 5
fig, axs = plt.subplots(nrows, ncols, figsize=(8, 6))
for row, ax_row in enumerate(axs):
    for col, ax in enumerate(ax_row):
        ax_count = row * ncols + col
        print(ax_count)
