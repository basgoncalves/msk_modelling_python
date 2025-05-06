import os
import dicom2fem
import dicom2fem.viewer

def load_stl():
    pass

def create_mesh():
    pass


class Model:
    def __init__(self, name):
        self.name = name
        self.mesh = None
    
    def load_mesh(self, file_path):
        self.mesh = load_stl(file_path)
    
    def create_mesh(self):
        self.mesh = create_mesh()
    
    def get_mesh(self):
        return self.mesh

    def set_forces(self, forces):
        self.forces = forces
        
    def set_kinematic_constraints(self, constraints):
        self.kinematic_constraints = constraints
        
    def sef_material_properties(self, properties):
        self.material_properties = properties
        
    def run(self):
        # Placeholder for running the simulation
        print(f"Running simulation for model: {self.name}")
        # Here you would typically call the simulation engine with the model's mesh and properties
        pass


class Simulation:
    def __init__(self):
        pass
    
    def add_model(self, model):
        pass
    
    def run(self):
        pass

if __name__ == "__main__":
    print("Running hip pressure simulation...")
    file_path = r"C:\Git\msk_modelling_python\tests\mri\hip_project\example_stls\009\acetabulum_l.stl"
    breakpoint()  # Set a breakpoint here for debugging
    V = dicom2fem.viewer.view_mesh(file_path)
    dicom2fem.viewer.main()
    V.show()
#%% END