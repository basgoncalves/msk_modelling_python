import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from tkinter import *
from tkinter import messagebox
import random

def read_coordinates(file_name):
    with open(file_name, 'r') as f:
        data = f.readlines()
    coordinates = [list(map(float, line.strip().split(','))) for line in data]
    return coordinates

def plot_coordinates(coordinates):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    xs = [coord[0] for coord in coordinates]
    ys = [coord[1] for coord in coordinates]
    zs = [coord[2] for coord in coordinates]
    ax.scatter(xs, ys, zs)
    plt.show()


def on_button_click():
    try:
        coordinates = read_coordinates('coordinates.txt')
        plot_coordinates(coordinates)
    except Exception:
        messagebox.showerror("Error", "Try again dickhead")
        fake_coordinates = []
        for _ in range(10):
            x = random.uniform(0, 10)
            y = random.uniform(0, 10)
            z = random.uniform(0, 10)
            fake_coordinates.append([x, y, z])
        with open('coordinates.txt', 'w') as f:
            for coord in fake_coordinates:
                f.write(','.join(str(c) for c in coord) + '\n')

root = Tk()
button = Button(root, text="Plot Coordinates", command=on_button_click)
button.pack()
root.mainloop()
