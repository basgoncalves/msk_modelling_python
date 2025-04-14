import numpy as np

import matplotlib.pyplot as plt

def simulate_running(mass, stiffness, damping, initial_position, initial_velocity, time):
    # Constants
    gravity = 9.8  # m/s^2

    # Variables
    position = [initial_position]
    velocity = [initial_velocity]
    acceleration = [0]

    # Simulation
    for t in np.arange(0, time, 0.01):
        # Calculate acceleration
        a = (gravity - (stiffness / mass) * position[-1] - (damping / mass) * velocity[-1])

        # Update velocity and position using Euler's method
        v = velocity[-1] + a * 0.01
        x = position[-1] + v * 0.01

        # Store values
        acceleration.append(a)
        velocity.append(v)
        position.append(x)

    return position, velocity, acceleration


if __name__ == '__main__':
    # Example usage
    mass = 70  # kg
    stiffness = 1000  # N/m
    damping = 0  # Ns/m
    initial_position = 0  # m
    initial_velocity = 5  # m/s
    time = 10  # seconds

    # Plotting
    t = np.arange(0, time + 0.01, 0.01)
    plt.figure(figsize=(10, 6))
    for i in [1000, 5000, 10000]:
        stiffness = i  # N/m
        position, velocity, acceleration = simulate_running(mass, stiffness, damping, initial_position, initial_velocity, time)
        plt.subplot(3, 1, 1)
        plt.plot(t, position)

        plt.subplot(3, 1, 2)
        plt.plot(t, velocity)

        plt.subplot(3, 1, 3)
        plt.plot(t, acceleration)

    plt.legend(['Stiffness = 1000','Stiffness = 5000', 'Stiffness = 10000'])

    plt.subplot(3, 1, 1)
    plt.xlabel('Time (s)')
    plt.ylabel('Position (m)')
    plt.title('Position vs Time')

    plt.subplot(3, 1, 2)
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Velocity vs Time')

    plt.subplot(3, 1, 3)
    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration (m/s^2)')
    plt.title('Acceleration vs Time')

    plt.tight_layout()
    plt.show()