import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

class Trial:
    def __init__(self, movement, acceleration, knee_forces, hip_forces, ankle_forces, muscle_forces):
        self.movement = movement
        self.acceleration = acceleration
        self.knee_forces = knee_forces
        self.hip_forces = hip_forces
        self.ankle_forces = ankle_forces
        self.muscle_forces = muscle_forces

    def acc_x(self):
        return self.acceleration[:, 0]

    def acc_y(self):
        return self.acceleration[:, 1]

    def acc_z(self):
        return self.acceleration[:, 2]

    def plot(self):
        time = np.arange(self.acceleration.shape[0])
        plt.figure()
        plt.plot(time, self.acc_x(), label="Acc_X")
        plt.plot(time, self.acc_y(), label="Acc_Y")
        plt.plot(time, self.acc_z(), label="Acc_Z")
        plt.title(f"Acceleration - {self.movement}")
        plt.xlabel("Time")
        plt.ylabel("Acceleration")
        plt.legend()
        plt.show()

    def resultant_knee_force(self):
        return np.linalg.norm(self.knee_forces, axis=1)

    def resultant_hip_force(self):
        return np.linalg.norm(self.hip_forces, axis=1)

    def resultant_ankle_force(self):
        return np.linalg.norm(self.ankle_forces, axis=1)

class Subject:
    def __init__(self, subject_id):
        self.id = subject_id
        self.trials = {}

    def add_trial(self, trial_id, trial):
        self.trials[trial_id] = trial

    def get_trial(self, trial_id):
        return self.trials.get(trial_id)

class Dataset:
    def __init__(self):
        self.subjects = {}

    def add_subject(self, subject):
        self.subjects[subject.id] = subject

    def get_subject(self, subject_id):
        return self.subjects.get(subject_id)

    def train_model(self, features_percentage=1.0):
        X = []
        y = []
        for subject in self.subjects.values():
            for trial in subject.trials.values():
                X.append(np.concatenate([
                    trial.acceleration.flatten(),
                    trial.knee_forces.flatten(),
                    trial.hip_forces.flatten(),
                    trial.ankle_forces.flatten(),
                    trial.muscle_forces.flatten()
                ]))
                y.append(trial.movement)

        X = np.array(X)
        y = np.array(y)

        # Select a percentage of features
        num_features = int(X.shape[1] * features_percentage)
        X = X[:, :num_features]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        clf = SVC()
        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy with {features_percentage*100}% features: {accuracy}")
        return clf, X_test, y_test #return model, test data and test labels

def run_ghost_data_set():
    # Generate sample data
    num_subjects = 5
    num_trials = 5
    num_time_points = 100
    num_axes = 3
    num_muscle_forces = 5

    dataset = Dataset()

    for id in range(num_subjects):
        subject = Subject(id)
        for trial_id in range(num_trials):
            movement = np.random.choice(["running", "walking", "jumping"])
            acceleration = np.random.randn(num_time_points, num_axes)
            knee_forces = np.random.randn(num_time_points, num_axes)
            hip_forces = np.random.randn(num_time_points, num_axes)
            ankle_forces = np.random.randn(num_time_points, num_axes)
            muscle_forces = np.random.randn(num_time_points, num_muscle_forces)
            trial = Trial(movement, acceleration, knee_forces, hip_forces, ankle_forces, muscle_forces)
            subject.add_trial(trial_id, trial)
        dataset.add_subject(subject)

    # Example usage
    subject01 = dataset.get_subject(1)
    trial03 = subject01.get_trial(3)

    print(f"Subject ID: {subject01.id}, Trial ID: {trial03.movement}")
    
    # Train and test the model with different feature percentages
    model, X_test, y_test = dataset.train_model(features_percentage=1.0)
    dataset.train_model(features_percentage=0.5)
    dataset.train_model(features_percentage=0.25)

    # test the model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy on test data: {accuracy}")

    # Plot the comparison for the resultant 3 components and resultant in different plots
    trial03.plot()
    plt.figure()
    time = np.arange(trial03.acceleration.shape[0])
    plt.plot(time, trial03.resultant_knee_force(), label="Knee Force")
    plt.plot(time, trial03.resultant_hip_force(), label="Hip Force")
    plt.plot(time, trial03.resultant_ankle_force(), label="Ankle Force")
    plt.title(f"Resultant Forces - {trial03.movement}")
    plt.xlabel("Time")
    plt.ylabel("Force")
    plt.legend()
    plt.show()
    

if __name__ == "__main__":
    run_ghost_data_set()