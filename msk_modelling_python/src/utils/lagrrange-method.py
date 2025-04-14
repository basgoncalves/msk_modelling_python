import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import CubicSpline

def lagrange_interpolation(x, y, x_val):
    n = len(x)
    result = 0
    for i in range(n):
        term = y[i]
        for j in range(n):
            if j != i:
                term *= (x_val - x[j]) / (x[i] - x[j])
        result += term
    return result

def cubic_spline_interpolation(x, y, x_val):
    cs = CubicSpline(x, y)
    return cs(x_val)

x = [1, 2, 3, 4, 5]
y = [2, 1, 3, 5, 4]
x_val = np.linspace(1, 5, 100)
y_val_lagrange = lagrange_interpolation(x, y, x_val)
y_val_cubic_spline = cubic_spline_interpolation(x, y, x_val)

plt.plot(x, y, 'ro', label='Data Points')
plt.plot(x_val, y_val_lagrange, label='Lagrange Interpolation')
plt.plot(x_val, y_val_cubic_spline, label='Cubic Spline Interpolation')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Interpolation Methods')
plt.legend()
plt.show()
