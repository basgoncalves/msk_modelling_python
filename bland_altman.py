import numpy as np
import matplotlib.pyplot as plt

# import data 

# Generate example data
method1 = np.array([1.2, 2.4, 3.1, 4.5, 5.2, 6.7, 7.3, 8.1, 9.5, 10.2])
method2 = np.array([1.1, 2.6, 3.3, 4.4, 5.3, 6.5, 7.4, 8.0, 9.4, 10.4])

# Calculate the mean difference and the limits of agreement
mean_diff = np.mean(method1 - method2)
std_diff = np.std(method1 - method2, ddof=1)
upper_limit = mean_diff + 1.96 * std_diff
lower_limit = mean_diff - 1.96 * std_diff

# Plot the Bland-Altman plot
plt.scatter((method1 + method2) / 2, method1 - method2)
plt.axhline(mean_diff, color='gray', linestyle='--')
plt.axhline(upper_limit, color='gray', linestyle='--')
plt.axhline(lower_limit, color='gray', linestyle='--')
plt.xlabel('Mean of two methods')
plt.ylabel('Difference between two methods')
plt.title('Bland-Altman plot')
plt.show()

# Print the results
print('Mean difference:', mean_diff)
print('Standard deviation of difference:', std_diff)
print('Upper limit of agreement:', upper_limit)
print('Lower limit of agreement:', lower_limit)
