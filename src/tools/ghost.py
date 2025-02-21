# module to create a ghost version of a project

import msk_modelling_python as msk
import os
import numpy as np
import pandas as pd
import time

class Ghost:
    
    def __init__(self):
        self.module_path = msk.__file__
        self.module_dir = os.path.dirname(self.module_path)
        self.data_dir = os.path.join(self.module_dir, 'data')
        self.template_data_path = os.path.join(self.data_dir, 'template_data.csv') 
        
    def create_template_osim_subject(parent_dir=''):
    
        print('Creating a template subject...')
        

    def get_dataset(self, folder_path):
        # Get all CSV files in the designated folder path
        files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.csv')]
        datasets = [pd.read_csv(file) for file in files]
        return datasets
        
    def create_template_dataset(self, folder_path, num_samples=100):
        # Generate random data for angles, muscle forces, activations, and joint loads
        angles = np.random.uniform(low=-180, high=180, size=(num_samples, 3))  # Assuming 3 angles
        muscle_forces = np.random.uniform(low=0, high=1000, size=(num_samples, 8))  # Assuming 8 muscle forces
        activations = np.random.uniform(low=0, high=1, size=(num_samples, 8))  # Assuming 8 activations
        joint_loads = np.random.uniform(low=0, high=500, size=(num_samples, 3))  # Assuming 3 joint loads

        # Create a DataFrame
        data = np.hstack((angles, muscle_forces, activations, joint_loads))
        columns = (
            [f'angle_{i+1}' for i in range(angles.shape[1])] +
            [f'muscle_force_{i+1}' for i in range(muscle_forces.shape[1])] +
            [f'activation_{i+1}' for i in range(activations.shape[1])] +
            [f'joint_load_{i+1}' for i in range(joint_loads.shape[1])]
        )
        df = pd.DataFrame(data, columns=columns)

        # Save the DataFrame to a CSV file in the specified folder path
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        if not os.path.isdir(self.template_data_path):
            df.to_csv(self.template_data_path, index=False)
        
        
        return df
    
    def get_template_dataset(self):
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        df = self.create_template_dataset(self.data_dir)
        return df
        

def unit_test():
    ghost = Ghost()
    print('Unit test passed')