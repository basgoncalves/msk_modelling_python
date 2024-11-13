import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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

    def force_length_curve(self, muscle_length):
        # Implement your desired force-length curve function here
        w = 0.56  # Shape factor for force-length relationship
        return np.exp(-((muscle_length - 1) ** 2) / w)

    def force_velocity_curve(self, muscle_velocity):
        # Implement your desired force-velocity curve function here
        a_f = 1.5  # Shape factor for force-velocity relationship
        b_f = 0.25  # Shape factor for force-velocity relationship
        if muscle_velocity < 0:
            self.max_contractile_velocity = -self.max_contractile_velocity
            
        return (1 - muscle_velocity / self.max_contractile_velocity) / (a_f + b_f * (1 - muscle_velocity / self.max_contractile_velocity))
    

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
            
        
if __name__ == '__main__':
    biceps = Muscle(name='biceps', max_force=100, opt_length=0.1, length=0.1, velocity=0.0, activation=0.0, pennation_angle=0.0)
    
    for i in range(100):
        state_activation = 0.01 * i 
        state_velocity = 0.0
        state_length = 0.01 * i
        biceps.update(length=state_length, velocity=state_velocity, activation=state_activation, time_step=0.01)
        
    biceps.plot_state()
    biceps.plot('force')
    biceps.plot('length')
    biceps.plot('tendon_force')
    plt.show()