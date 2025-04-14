import msk_modelling_python as msk

path = r"C:\Git\opensim_tutorial\tutorials\repeated_sprinting\models\009_rajagopal_scaled.osim"
joint_angles = r"C:\Git\opensim_tutorial\tutorials\repeated_sprinting\Simulations\009_simplified\run_baseline\ik.mot"
model = msk.osim.Model(path)
model.initSystem()
muscles = model.getMuscles()

mtus = []
for muscle in muscles:
    mtu = {
        "name": muscle.getName(),
        "c1": "-0.5",
        "c2": "-0.5",
        "shapeFactor": "0.1",
        "optimalFibreLength": muscle.getOptimalFiberLength(),
        "pennationAngle": muscle.getPennationAngleAtOptimalFiberLength(),
        "tendonSlackLength": muscle.getTendonSlackLength(),
        "tendonSlackLength": muscle.getTendonSlackLength(),
        "maxIsometricForce": muscle.getMaxIsometricForce(),
        "strengthCoefficient": "1"
    }
    # calculate muscle force for a state
    
    muscle_states = msk.pd.DataFrame(columns=['activation', 'fiberLength', 'fiberVelocity', 'tendonForce', 'fiberForce', 'tendonForce', 'tendonLength', 'muscleStiffness', 'fiberForce'])
    activations = msk.np.linspace(0, 1, 100)
    
    for activation in activations:        
        state = model.initSystem()
        muscle.setActivation(state, activation)
        model.realizeDynamics(state)
        tendon_force = muscle.getTendonForce(state)
        pennation_angle = muscle.getPennationAngle(state)
        fiber_length = muscle.getFiberLength(state)
        fiber_velocity = muscle.getFiberVelocity(state)
        tendon_length = muscle.getTendonLength(state)
        muscle_stiffness = muscle.getMuscleStiffness(state)
        
        # calculate fiber force
        fiber_force = muscle.getMaxIsometricForce() * activation * np.cos(pennation_angle) * (fiber_length / muscle.getOptimalFiberLength())
        
        muscle_states.loc[len(muscle_states)] = [activation, 
                             fiber_length, 
                             fiber_velocity, 
                             tendon_force, 
                             fiber_force, 
                             tendon_force, 
                             tendon_length, 
                             muscle_stiffness,
                             fiber_force]
        
        import pdb; pdb.set_trace()