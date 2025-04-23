import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import opensim as osim


class Muscle:
    def __init__(self, name='default', max_force=100, opt_length=0.1, length=0.5, velocity=0.0, activation=0.0, pennation_angle=0.0, tendon_slack_length=0.05, tendon_stiffness=10000):
        """
        Inputs:
            name (str): Name of the muscle.
            max_force (float): Maximum isometric force of the muscle.
            opt_length (float): Optimal fiber length for force production.
            length (float): Current muscle fiber length.
            velocity (float): Current muscle fiber velocity.
            activation (float): Current muscle activation level (0-1).
            pennation_angle (float): Pennation angle in radians.
            tendon_slack_length (float): Slack length of the tendon.
            tendon_stiffness (float): Stiffness of the tendon.
        """
        self.name = name
        self.max_force = max_force
        self.opt_length = opt_length
        self.length = length
        self.velocity = velocity
        self.activation = activation
        self.pennation_angle = pennation_angle
        self.tendon_slack_length = tendon_slack_length
        self.tendon_stiffness = tendon_stiffness
        self.max_contractile_velocity = 10.0

        self.time_steps = 0.01
        initial_state = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
        self.state = pd.DataFrame(initial_state, columns=['time', 'length', 'velocity', 'activation', 'force', 'tendon_force'])

    def to_json(self, filepath=None):
        
        """
        Converts the muscle object to a JSON string.

        Args:
            filepath (str): Optional filepath to save the JSON string to.

        Returns:
            str: JSON string representation of the muscle object.
        """
        muscle_dict = {
            'name': self.name,
            'max_force': self.max_force,
            'opt_length': self.opt_length,
            'length': self.length,
            'velocity': self.velocity,
            'activation': self.activation,
            'pennation_angle': self.pennation_angle,
            'tendon_slack_length': self.tendon_slack_length,
            'tendon_stiffness': self.tendon_stiffness
        }
        json_string = json.dumps(muscle_dict, indent=4)
        
        
        if not filepath:
            filepath = os.path.join(os.getcwd(), 'muscle.json')
            
        with open(filepath, 'w') as f:
            f.write(json_string)
        return json_string
    
    def force_length_curve(self,length):
        """Approximation of the combined force-length relationship."""

        # Active component (Gaussian)
        a_active = 1.0  # Amplitude
        b_active = 1.0  # Center
        c_active = 0.3  # Width
        offset_active = 0.0  # Vertical offset
        active_force = a_active * np.exp(-((length - b_active) ** 2) / (2 * c_active ** 2)) + offset_active

        # Passive component (Exponential, but scaled down and shifted)
        a_passive = 0.1  # Reduced amplitude
        b_passive = 5.0  # Rate of increase
        c_passive = -0.1  # Reduced offset
        passive_force = a_passive * np.exp(b_passive * (length - 1.1)) + c_passive

        # Apply condition to passive_force using boolean indexing (vectorized operation)
        passive_force = np.where(length < 1.1, 0, passive_force)

        # Combine active and passive components
        total_force = active_force + passive_force
        return total_force

    def force_velocity_curve(self, velocity):
        """
        Recreates the force-velocity curve based on the provided data points.

        Args:
            velocity (float or list): The velocity value(s) at which to evaluate the force.

        Returns:
            float or list: The corresponding force value(s) based on the curve.
        """

        x_points = [-10, -1, -0.6, -0.3, -0.1, 0, 0.1, 0.3, 0.6, 0.8, 10]
        y_points = [0, 0, 0.08, 0.2, 0.55, 1, 1.4, 1.6, 1.7, 1.75, 1.75]

        if isinstance(velocity, (int, float)):
            # Handle single velocity input
            if velocity <= x_points[0]:
                return y_points[0]
            elif velocity >= x_points[-1]:
                return y_points[-1]
            else:
                for i in range(len(x_points) - 1):
                    if x_points[i] <= velocity <= x_points[i + 1]:
                        # Linear interpolation
                        slope = (y_points[i + 1] - y_points[i]) / (x_points[i + 1] - x_points[i])
                        return y_points[i] + slope * (velocity - x_points[i])
        else:
            # Handle list of velocity inputs
            force_values = []
            for v in velocity:
                if v <= x_points[0]:
                    force_values.append(y_points[0])
                elif v >= x_points[-1]:
                    force_values.append(y_points[-1])
                else:
                    for i in range(len(x_points) - 1):
                        if x_points[i] <= v <= x_points[i + 1]:
                            slope = (y_points[i + 1] - y_points[i]) / (x_points[i + 1] - x_points[i])
                            force_values.append(y_points[i] + slope * (v - x_points[i]))
            return force_values
        
    def passive_force_length_curve(self, muscle_length):
        # Implement your desired passive force-length curve function here
        k_pe = 4.0  # Passive force-length shape factor
        strain = (muscle_length - 1.0) / 0.6  # Normalized strain
        if strain > 0:
            return self.max_force * (np.exp(k_pe * strain) - 1) / (np.exp(k_pe) - 1)
        else:
            return 0.0

    def tendon_force_length_curve(self, tendon_length):
        # Implement your desired tendon force-length curve function here
        strain = (tendon_length - self.tendon_slack_length) / self.tendon_slack_length
        if strain > 0:
            return self.tendon_stiffness * strain
        else:
            return 0.0

    def get_force(self):
        """
        Calculates the muscle force based on the equilibrium musculotendon model.

        Returns:
            float: Muscle force.
        """

        # Calculate muscle force components
        f_max = self.max_force
        f_l = self.force_length_curve(self.length / self.opt_length)  # Normalize length
        f_v = self.force_velocity_curve(self.velocity / self.opt_length)  # Normalize velocity
        f_pe = self.passive_force_length_curve(self.length / self.opt_length)

        # Calculate muscle force
        muscle_force = self.activation * f_max * f_l * f_v + f_pe

        # Calculate tendon force
        tendon_length = self.length - self.tendon_slack_length
        tendon_force = self.tendon_force_length_curve(tendon_length)

        # Solve for muscle force using equilibrium equation (Eq. 5)
        muscle_force = tendon_force / (np.cos(self.pennation_angle) * f_l * f_v)

        # update self
        self.tendon_length = tendon_length
        self.tendon_force = tendon_force
        self.muscle_force = muscle_force
        self.f_l = f_l
        self.f_v = f_v
        self.f_pe = f_pe


        return muscle_force

    def update(self, length, velocity, activation, time_step):
        """
        Updates the muscle state based on the given inputs.

        Inputs:
            length (float): Muscle fiber length.
            velocity (float): Muscle fiber velocity.
            activation (float): Muscle activation level (0-1).
            time_step (float): Time step for the update.
        """
        self.length = length
        self.velocity = velocity
        self.activation = activation

        # Calculate muscle force
        muscle_force = self.get_force()

        # Update muscle state
        last_time = self.state['time'].iloc[-1]
        self.state.loc[len(self.state)] = [last_time + time_step, length, velocity, activation, muscle_force, self.tendon_force]

    def plot_state(self):
        """
        Plots the state of the muscle.
        """
        plt.figure()
        plt.subplot(3, 1, 1)
        plt.plot(self.state['time'], self.state['length'])
        plt.ylabel('length (m)')

        plt.subplot(3, 1, 2)
        plt.plot(self.state['time'], self.state['force'])
        plt.ylabel('force (N)')

        plt.subplot(3, 1, 3)
        plt.plot(self.state['time'], self.state['activation'])
        plt.ylabel('activation')

        plt.xlabel('time (s)')

    def plot(self, parameter = 'force'):
        """
        Plots the muscle state.

        Inputs:
            parameter (str): Parameter to plot ('length', 'velocity', 'activation', 'force').
        """
        try:
            plt.figure()
            plt.plot(self.state['time'], self.state[parameter])
            plt.ylabel(parameter)
            plt.xlabel('time (s)')
        except Exception as e:
            print('Parameter not found.')

    def plot_force_length_curve(self):
        """
        Plots the force-length curve of the muscle.
        """
        muscle_lengths = np.linspace(0.5, 1.5, 100)
        self.update(length=0.1, velocity=0.0, activation=0.0, time_step=0.01)
        muscle_forces = [self.get_force(length=length) for length in muscle_lengths]

        plt.figure()
        plt.plot(muscle_lengths, muscle_forces)
        plt.xlabel('muscle length (m)')
        plt.ylabel('muscle force (N)')


if __name__ == '__main__':

    biceps = Muscle(name='biceps', max_force=100, opt_length=0.1,
                    length=0.1, velocity=0.0, activation=0.0, 
                    pennation_angle=0.0, tendon_slack_length=0.05, tendon_stiffness=10000)
    
   