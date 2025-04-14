import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class Muscle:
    def __init__(self, name = 'default', max_force = 100, opt_length = 0.1, length = 0.5, velocity = 0.0, activation = 0.0, pennation_angle = 0.0):
        '''
        inputs:
            name(str): name of the muscle
            max_force(float): maximum force of the muscle
            opt_length(float): length at which muscle produces more force in meters
            length(float): current length of the muscle in meters
            velocity(float): current velocity of the muscle in meters per second
            activation(float): current activation of the muscle
            pennation_angle(float): angle of the muscle fibers in degrees
        '''
        self.name = name
        self.max_force = max_force
        self.opt_length = opt_length
        self.length = length
        self.velocity = velocity
        self.activation = activation
        self.pennation_angle = np.radians(pennation_angle)  # convert to radians
        
        self.max_contractile_velocity = 10.0
        self.time_steps = 0.01
        
        initial_state = np.array([[0.0, 0.0, 0.0, 0.0, 0.0]])
        self.state = pd.DataFrame(initial_state, columns=['time', 'length', 'velocity', 'activation', 'force'])
    
    def force_length_curve(self, length = 1):
        '''
        create a force length curve for the muscle based optimal length and max force
        output:
            a polynomial function that represents the force length curve with max force and optimal length
        '''
        curve = np.poly1d([self.max_force / self.opt_length**2, 0, 0])
        current_max_force = curve(length)
        
        return current_max_force, curve
    
    def force_velocity_curve(self, velocity = 1):
        '''
        create a force velocity curve for the muscle based on the max contractile velocity
        output:
            a polynomial function that represents the force velocity curve with max contractile velocity
        '''
        curve = np.poly1d([self.max_force / self.max_contractile_velocity, 0])
        current_max_force = curve(velocity)
        
        return current_max_force, curve
    
    def update(self, length, velocity, activation):
        '''
        updates the state of the muscle based on the inputs
        inputs:
            length(float): current length of the muscle in meters
            velocity(float): current velocity of the muscle in meters per second
            activation(float): current activation of the muscle
        
        outputs:
            None
            Updates the state of the muscle object with the new values
            DataFrame with the new state row
        '''
        
        force = self.force_length_curve(length) * (self.velocity / self.max_contractile_velocity) * np.cos(self.pennation_angle)
        last_time = self.state['time'].iloc[-1]
        # add row to state
        self.state.loc[len(self.state)] = [last_time + self.time_steps, length, velocity, activation, force]

    def plot_state(self):
        '''
        Plots the state of the muscle
        '''
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
        
        plt.show()
        
        

class FatigueModel:
    def __init__(self, max_force, fatigue_rate):
        self.max_force = max_force
        self.fatigue_rate = fatigue_rate
        self.force = max_force
        self.activation = 0.0

    def update(self, length, velocity, activation, time_step):
        force = self.max_force * activation * self.force_reduction(length, velocity)
        self.force = force - self.fatigue_rate * time_step
        self.activation = activation

    def force_reduction(self, length, velocity):
        # Implement your force reduction function here
        # This function should return a value between 0 and 1
        # based on the muscle length and velocity
        return 1.0

# Example usage
fatigue_model = FatigueModel(max_force=100, fatigue_rate=0.1)
length = 0.5
velocity = 1.0
activation = 0.8
time_step = 100

fatigue_model.update(length, velocity, activation, time_step)


biceps = Muscle(name='biceps', max_force=100, opt_length=0.1, length=0.5, velocity=0.0, activation=0.0, pennation_angle=0.0)
activations = np.linspace(0, 1, 100)

for activation in activations:
    biceps.update(length=0.5, velocity=5, activation=activation)

biceps.plot_state()
