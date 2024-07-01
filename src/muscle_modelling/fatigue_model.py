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
print(fatigue_model.force)