"""Model-editing operations backed by the OpenSim API.

Masses, isometric force, coordinate ranges/locks, wrapping surfaces, muscle
copying and the moment-arm sanity checks -- everything that CHANGES an .osim.
``bioscout.model.edit.ops`` declares these in its ``delegates_to=`` map.

Split out of the old ``bioscout/utils/openSim.py`` (docs/RESTRUCTURE_PLAN.md,
stage 6) -- the code is unchanged, only its address.
"""
import os
from xml.etree import ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt
import opensim as osim
from bioscout import utils
from bioscout.model.opensim_base import _quiet_model, terminal_warnings


#: Cap on evaluation points per muscle in sampleMuscleQuantities -- guards
#: against combinatorial explosion for muscles spanning many DOFs. Above it the
#: per-coordinate N is reduced until the grid fits, so a nominal N is NOT always
#: the N a muscle actually gets: at 1500, a 3-DOF muscle collapses from N=12 to
#: an effective 11, and a 4-DOF muscle sits at 6 from N=7 upwards. Module-level
#: so a convergence study can raise it (tests/ModeneseN --max-eval-points)
#: without editing this file. Changing it changes results for any muscle it
#: binds on, so leave the default alone for production runs.
MAX_EVAL_POINTS = 1500

#: Coordinates the muscle optimiser must NOT treat as spanned, by exact name or
#: by substring. The grid is N**nDOF, so every extra coordinate multiplies the
#: cost by N — and a secondary DOF earns its place only if the muscle really
#: does change length over it.
#:
#: Measured on GPK_v3 (Athlete_06, N=4): `knee_adduction` and `subtalar_angle`
#: are unlocked with ranges of +-20 deg and +-30 deg, and they push the
#: hamstrings/quadriceps group to 5 spanned coordinates (4**5 = 1024 poses,
#: 177 s each) and the gastrocnemii to 6 (capped down to 3**6 = 729, 113 s
#: each). Those 13 muscles cost 34 of the run's 39 minutes. Excluding the two
#: secondary DOFs drops them to 4 coordinates.
#:
#: Empty by default — this changes results, so a project opts in through
#: BatchSettings.muscle_opt_skip_coords rather than inheriting it silently.
MUSCLE_OPT_SKIP_COORDS = ()

#: A coordinate counts as spanned only if the muscle's moment arm exceeds this
#: anywhere in its range. 1e-4 m = 0.1 mm, which is below the resolution of
#: any musculoskeletal geometry and lets numerical noise add a whole axis to
#: the grid. Raise it to exclude coordinates the muscle barely acts on.
MUSCLE_OPT_MA_TOL = 1e-4

# Model editing functions
def scale_body_masses(osim_modelPath):
    """ 
    Scale the body masses of model_target to match the percentages of model_reference.
    """

    model_ref = _quiet_model(osim_modelPath)

    model_targ_path = osim_modelPath.replace('.osim', '_scaledMasses.osim')
    model_targ = _quiet_model(model_targ_path)

    state1 = model_ref.initSystem()
    state2 = model_targ.initSystem()

    # prnt model weight
    print(f"Model: {model_ref.getName()}, Weight: {model_ref.getTotalMass(state1)} kg")
    print(f"Model: {model_targ.getName()}, Weight: {model_targ.getTotalMass(state2)} kg")

    # Compare each body's mass between model1 and model2
    bodyset_ref = {body.getName(): body for body in model_ref.getBodySet()}
    bodyset_targ = {body.getName(): body for body in model_targ.getBodySet()}

    print("\nComparison of body masses between model1 and model2:")

    for body_name in bodyset_ref:
        if body_name in bodyset_targ:
            mass_ref = bodyset_ref[body_name].getMass()
            mass_targ = bodyset_targ[body_name].getMass()
            percent_mass_ref = (mass_ref / model_ref.getTotalMass(state1)) * 100
            percent_mass_targ = (mass_targ / model_targ.getTotalMass(state2)) * 100
            print(f"Body: {body_name}, Model1 Mass: {mass_ref} kg ({percent_mass_ref:.2f}%), Model2 Mass: {mass_targ} kg ({percent_mass_targ:.2f}%)")
            
            # change mass of body in model2 to match model1 percentage
            if percent_mass_ref != percent_mass_targ:
                new_body_mass_targ = (percent_mass_ref / 100) * model_targ.getTotalMass(state2)
                bodyset_targ[body_name].setMass(new_body_mass_targ)
                print(f"Updated Model2 {body_name} mass to: {new_body_mass_targ} kg, {percent_mass_ref:.2f}%")
            
        else:
            mass_ref = bodyset_ref[body_name].getMass()
            print(f"Body: {body_name}, Model1 Mass: {mass_ref} kg, Model2 Mass: Not Found")
            
    # save model2 with updated masses
    model_targ.setName(model_targ.getName() + "_updated_masses")
    model_targ.printToXML(model_targ_path)
    print(f"\nUpdated model saved to: {model_targ_path}")

        
    return model_targ

def add_mass_to_body(osim_modelPath, body_name, mass_to_add):
    """
    Add a specific mass to a body in the OpenSim model.
    """
    model = _quiet_model(osim_modelPath)
    state = model.initSystem()

    save_path = osim_modelPath.replace('.osim', '_updatedMasses.osim')

    body = model.getBodySet().get(body_name)
    
    if body:
        current_mass = body.getMass()
        new_mass = current_mass + mass_to_add
        body.setMass(new_mass)
        model.printToXML(save_path)
        print(f"Updated {body_name} mass from {current_mass} kg to {new_mass} kg.")
    else:
        print(f"Body '{body_name}' not found in the model.")

def print_body_mass_per_segment(osim_modelPath=None):
    """ 
    Print the mass of each body segment in the OpenSim model.
    """
    if not osim_modelPath:
        osim_modelPath = input("Enter path to OpenSim model (.osim): ").strip('"')
    
    model = _quiet_model(osim_modelPath)
    state = model.initSystem()

    print("Body Segment Masses:")
    for body in model.getBodySet():
        print(f"{body.getName()}: {body.getMass()} kg ({body.getMass() / model.getTotalMass(state) * 100:.2f}%)")

def increase_isometric_force(osim_modelPath=None, muscleList='all', factor: float = None):
    """
    Increase the isometric force of a specified muscle by a given factor.
    """
    if not osim_modelPath:
        osim_modelPath = input("Enter path to OpenSim model (.osim): ").strip('"')
    
    if not factor:
        factor = float(input("Enter factor to increase max isometric force (e.g., 1.2 for 20% increase): "))

    model = _quiet_model(osim_modelPath)
    
    if muscleList == 'all':
        muscleList = []
        for muscle in model.getMuscles():
            muscleList.append(muscle.getName())
    
    _n = 0
    for muscle_name in muscleList:
        muscle = model.getMuscles().get(muscle_name)
        if muscle:
            muscle.setMaxIsometricForce(muscle.getMaxIsometricForce() * factor)
            _n += 1
        else:
            print(f"Muscle '{muscle_name}' not found in the model.")

    _out = osim_modelPath.replace('.osim', f'_increased_{factor:.2f}.osim')
    model.printToXML(_out)
    print(f"[scale] increased isometric force x{factor:.2f} on {_n} muscles -> {os.path.basename(_out)}")

def lock_model_coordinates(osim_modelPath=None, coordinates_to_lock: list = None, save_path=None, unlock=False):
    """
    Lock specified coordinates in the OpenSim model.
    """
    if not osim_modelPath:
        osim_modelPath = input("Enter path to OpenSim model (.osim): ").strip('"')
    
    if not coordinates_to_lock:
        coordinates_to_lock = input("Enter coordinates to lock (comma-separated): ").split(',')

    model = _quiet_model(osim_modelPath)
    state = model.initSystem()
    
    for coord_name in coordinates_to_lock:
        coord = model.getCoordinateSet().get(coord_name)
        if coord:
            if unlock:
                coord.setDefaultLocked(False)
                print(f"Unlocked coordinate: {coord_name}")
            else:
                coord.setDefaultLocked(True)
                print(f"Locked coordinate: {coord_name}")
        else:
            print(f"Coordinate '{coord_name}' not found in the model.")

    if not save_path:
        save_path = osim_modelPath.replace('.osim', '_lockedCoords.osim')
    model.printToXML(save_path)
    print(f"Updated model with locked coordinates saved to: {save_path}")

def coord_moment_arms(osim_model, muscle_list):
    '''Check which coordinates the muscles in the list have moment arms about (non-zero across the range of the model)'''

    model = _quiet_model(osim_model)
    state = model.initSystem()
    coord_moment_arms = {}

    for muscle_name in muscle_list:
        try:
            muscle = model.getMuscles().get(muscle_name)
            moment_arms = {}
            for i in range(model.getNumCoordinates()):
                coord = model.getCoordinateSet().get(i)
                model.realizePosition(state)
                moment_arm_value = muscle.computeMomentArm(state, coord)
                if not np.isclose(moment_arm_value, 0):
                    moment_arms[coord.getName()] = moment_arm_value
            coord_moment_arms[muscle_name] = moment_arms
        except Exception as e:
            print(f"Error processing muscle {muscle_name}: {e}")
    
    coord_names = set()
    for muscle, mom_arms in coord_moment_arms.items():
        for coord in mom_arms.keys():
            if not np.isnan(mom_arms[coord]):
                coord_names.add(coord)

    return coord_names

def add_wrapping_surfaces(reference_model_path=None, target_model_path=None, output_model_path=None):
    """
    Add wrapping surfaces from reference OpenSim model to target model.
    
    Args:
        reference_model_path (str): Path to reference .osim file
        target_model_path (str): Path to target .osim file
        output_model_path (str): Path for output .osim file with wrapping surfaces
    """

    # prompt user for paths if not provided
    if not reference_model_path:
        reference_model_path = input("Enter path to reference OpenSim model (.osim): ").strip('"')
    if not target_model_path:
        target_model_path = input("Enter path to target OpenSim model (.osim): ").strip('"')
    if not output_model_path:
        output_model_path = input("Enter path to save output OpenSim model with wrapping surfaces (.osim): ").strip('"')

    # turn off OpenSim terminal warnings for cleaner output
    terminal_warnings('off')
    try:
        # Load both models
        reference_model = _quiet_model(reference_model_path)
        target_model = _quiet_model(target_model_path)
        
        # Get wrapping surfaces from reference model
        reference_bodies = reference_model.getBodySet()
        target_bodies = target_model.getBodySet()
        
        # Add wrapping surfaces to target model
        for i in range(reference_bodies.getSize()):
            ref_body = reference_bodies.get(i)
            wrapping_surfaces = ref_body.getWrapObjectSet()
            
            if wrapping_surfaces.getSize() > 0:
                try:
                    # find matching body in target model
                    target_body = target_bodies.get(ref_body.getName())
                    target_wrap_set = target_body.getWrapObjectSet()
                    
                    for j in range(wrapping_surfaces.getSize()):
                        wrap_obj = wrapping_surfaces.get(j)
                        wrap_name = wrap_obj.getName()
                        
                        # Check if surface already exists
                        if target_wrap_set.getIndex(wrap_name) >= 0:
                            print(f"Skipped wrapping surface '{wrap_name}' on body '{target_body.getName()}' (already exists)")
                        else:
                            target_body.addWrapObject(wrap_obj)
                            print(f"Added wrapping surface '{wrap_name}' to body '{target_body.getName()}'")
                except RuntimeError:
                    print(f"Body '{ref_body.getName()}' not found in target model")
        
        # change model name to avoid confusion
        target_model.setName(target_model.getName() + "_with_wrapping")

        # Save output model
        target_model.printToXML(output_model_path)
        print(f"\nModel saved to: {output_model_path}")
        
    except ImportError:
        print("Error: OpenSim Python API not installed. Please install opensim package.")
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
    except Exception as e:
        print(f"Error: {e}")

def edit_model_range_coordinates(osim_modelPath, coordinate_name, new_range: list, save_path):
    """
    Edit the range of motion for a specific coordinate in the OpenSim model.

    Args:
        osim_modelPath (str): Path to the .osim model file
        coordinate_name (str): Name of the coordinate to edit
        new_range (list): New range of motion as [min, max] in radians
        save_path (str): Path to save the modified model

    """
    model = _quiet_model(osim_modelPath)
    state = model.initSystem()

    coordinate = model.getCoordinateSet().get(coordinate_name)

    if coordinate:
        current_range = (coordinate.getRangeMin(), coordinate.getRangeMax())
        coordinate.setRangeMin(new_range[0])
        coordinate.setRangeMax(new_range[1])
        model.printToXML(save_path)
        print(f"Updated {coordinate_name} range from {current_range} to {new_range}.")
    else:
        print(f"Coordinate '{coordinate_name}' not found in the model.")

def add_wrapping_surface_to_model(model_path, surface_name, wrap_name, save_path=None):
    """
    Add a wrapping surface to an OpenSim model.
    
    Args:
        model_path (str): Path to the .osim model file
        surface_name (str): Name of the wrapping surface to add
        wrap_name (str): Name of the wrap object to create
        save_path (str, optional): Path to save the modified model. If None, saves to model_path with '_wrap_added' suffix
    
    Returns:
        str: Path to the saved model file
    """
    
    # Load model
    model = _quiet_model(model_path)
    
    # Initialize system
    state = model.initSystem()
    
    try:
        # Create wrapping surface (example: a cylinder)
        wrap_surface = osim.WrapCylinder(surface_name, 0.05, 0.1)  # name, radius, length
        
        # Add wrapping surface to model
        model.addWrapObject(wrap_surface)
        
        print(f"Added wrapping surface: {surface_name}")
        
    except Exception as e:
        print(f"Error adding wrapping surface '{surface_name}': {e}")
    
    # Finalize connections and initialize system
    model.finalizeConnections()
    
    # Determine save path
    if save_path is None:
        base_name = os.path.splitext(model_path)[0]
        save_path = f"{base_name}_wrap_added.osim"
    
    # change model name to indicate wrap added
    model.setName(model.getName() + "_wrap_added")

    # Save the modified model
    model.printToXML(save_path)
    
    print(f"Modified model saved to: {save_path}")
    
    return save_path

def add_muscles_to_model(source_model_path, target_model_path, muscle_names, save_path=None):
    """
    Add muscles from a source OpenSim model to a target OpenSim model.
    
    Args:
        source_model_path (str): Path to the source .osim model file
        target_model_path (str): Path to the target .osim model file
        muscle_names (list): List of muscle names to copy from source to target
        save_path (str, optional): Path to save the modified model. If None, saves to target_model_path with '_muscles_added' suffix
    
    Returns:
        str: Path to the saved model file
    """
    
    # Load models
    source_model = _quiet_model(source_model_path)
    target_model = _quiet_model(target_model_path)
    
    # Initialize systems
    source_state = source_model.initSystem()
    target_state = target_model.initSystem()
    
    muscles_added = []
    muscles_skipped = []
    
    for muscle_name in muscle_names:
        try:
            # Check if muscle already exists in target
            if target_model.getMuscles().contains(muscle_name):
                print(f"Muscle '{muscle_name}' already exists in target model. Skipping.")
                muscles_skipped.append(muscle_name)
                continue
            
            # Get muscle from source model
            source_muscle = source_model.getMuscles().get(muscle_name)
            
            # Clone the muscle
            cloned_muscle = source_muscle.clone()
            
            # Add to target model
            target_model.addForce(cloned_muscle)
            
            # Find wrap objects referenced by this muscle's geometry path
            source_path_wraps = source_muscle.getGeometryPath().getWrapSet()

            for i in range(source_path_wraps.getSize()):
                path_wrap = source_path_wraps.get(i)
                wrap_object_name = path_wrap.getWrapObjectName()

                # Search all bodies in source model for the wrap object
                source_wrap_obj = None
                source_body = None
                body_set = source_model.getBodySet()
                for b in range(body_set.getSize()):
                    body = body_set.get(b)
                    wrap_set = body.getWrapObjectSet()
                    for w in range(wrap_set.getSize()):
                        if wrap_set.get(w).getName() == wrap_object_name:
                            source_wrap_obj = wrap_set.get(w)
                            source_body = body
                            break
                    if source_wrap_obj is not None:
                        break

                if source_wrap_obj is None:
                    print(f"Wrap object '{wrap_object_name}' not found in source model. Skipping.")
                    continue

                target_body_name = source_body.getName()
                if not target_model.getBodySet().contains(target_body_name):
                    print(f"Body '{target_body_name}' not found in target model. Cannot add wrap object '{wrap_object_name}'.")
                    continue

                target_body = target_model.getBodySet().get(target_body_name)
                target_wrap_set = target_body.getWrapObjectSet()

                # Check if wrap object already exists on that body
                wrap_exists = any(target_wrap_set.get(w).getName() == wrap_object_name
                                  for w in range(target_wrap_set.getSize()))
                if not wrap_exists:
                    cloned_wrap = source_wrap_obj.clone()
                    target_body.addWrapObject(cloned_wrap)
                    print(f"Added wrap object: {wrap_object_name} to body: {target_body_name} for muscle: {muscle_name}")
                else:
                    print(f"Wrap object '{wrap_object_name}' already exists on body '{target_body_name}'. Skipping.")
            muscles_added.append(muscle_name)
            print(f"Added muscle: {muscle_name}")
     
        except Exception as e:
            print(f"Error adding muscle '{muscle_name}': {e}")
            muscles_skipped.append(muscle_name)
    
    # Finalize connections and initialize system
    target_model.finalizeConnections()
    
    # Determine save path
    if save_path is None:
        base_name = os.path.splitext(target_model_path)[0]
        save_path = f"{base_name}_muscles_added.osim"
    
    # change model name to indicate muscles added
    target_model.setName(target_model.getName() + "_muscles_added")

    # Save the modified model
    target_model.printToXML(save_path)
    
    print(f"\n=== Summary ===")
    print(f"Muscles added: {len(muscles_added)}")
    print(f"Muscles skipped: {len(muscles_skipped)}")
    print(f"Modified model saved to: {save_path}")
    
    return save_path

def copy_model_coordinate(src_model=None, target_model=None, coordinate_name=None, target_joint_name=None):
    """Copy one or more coordinates from a source model to a target model via XML manipulation.

    coordinate_name: str or list of str
    target_joint_name: str, list of str (matched by index to coordinate_name), or None
        If None, the source joint name is used for each coordinate.

    Adds each coordinate to the target joint's <coordinates> list and mirrors
    any SpatialTransform/TransformAxis references from the source joint.
    """
    import copy

    if not src_model:
        src_model = input("Enter the path to the source model (.osim): ")
    if not target_model:
        target_model = input("Enter the path to the target model (.osim): ")
    if not coordinate_name:
        coordinate_name = input("Enter coordinate name(s) (comma-separated): ").split(',')

    # Normalise to lists
    if isinstance(coordinate_name, str):
        coordinate_name = [coordinate_name]
    if target_joint_name is None:
        target_joint_name = [None] * len(coordinate_name)
    elif isinstance(target_joint_name, str):
        target_joint_name = [target_joint_name] * len(coordinate_name)

    src_tree = ET.parse(src_model)
    tar_tree = ET.parse(target_model)
    src_root = src_tree.getroot()
    tar_root = tar_tree.getroot()

    src_parent_map = {c: p for p in src_root.iter() for c in p}
    _skip_tags = {'CoordinateSet', 'coordinates', 'objects', 'groups', 'components'}

    for coord_name, joint_override in zip(coordinate_name, target_joint_name):

        # --- Find coordinate element and parent joint in source ---
        src_coord_elem = None
        for coord in src_root.iter('Coordinate'):
            if coord.get('name') == coord_name:
                src_coord_elem = coord
                break
        if src_coord_elem is None:
            print(f"Warning: Coordinate '{coord_name}' not found in source model. Skipping.")
            continue

        src_joint_name = None
        src_joint_elem = None
        elem = src_coord_elem
        while elem in src_parent_map:
            parent = src_parent_map[elem]
            if parent.get('name') and parent.tag not in _skip_tags:
                src_joint_name = parent.get('name')
                src_joint_elem = parent
                break
            elem = parent
        print(f"Found coordinate '{coord_name}' in joint '{src_joint_name}'.")

        # Find which TransformAxis names in source reference this coordinate
        src_axes_referencing = []
        if src_joint_elem is not None:
            for axis in src_joint_elem.iter('TransformAxis'):
                coords_elem = axis.find('coordinates')
                if coords_elem is not None and coords_elem.text and coord_name in coords_elem.text.split():
                    src_axes_referencing.append(axis.get('name'))
        print(f"Source TransformAxes referencing '{coord_name}': {src_axes_referencing}")

        # --- Locate target joint ---
        joint_to_find = joint_override if joint_override else src_joint_name
        tar_joint_elem = None
        for jelem in tar_root.iter():
            if jelem.get('name') == joint_to_find:
                tar_joint_elem = jelem
                break
        if tar_joint_elem is None:
            print(f"Warning: Joint '{joint_to_find}' not found in target model. Skipping '{coord_name}'.")
            continue

        # --- Add coordinate to target joint's <coordinates> list ---
        coords_container = tar_joint_elem.find('coordinates')
        if coords_container is None:
            coords_container = ET.SubElement(tar_joint_elem, 'coordinates')

        existing = None
        for coord in coords_container.findall('Coordinate'):
            if coord.get('name') == coord_name:
                existing = coord
                break

        if existing is not None:
            for child in list(existing):
                existing.remove(child)
            for child in src_coord_elem:
                existing.append(copy.deepcopy(child))
            print(f"Updated existing coordinate '{coord_name}'.")
        else:
            coords_container.append(copy.deepcopy(src_coord_elem))
            print(f"Appended coordinate '{coord_name}' to joint '{joint_to_find}'.")

        # --- Update SpatialTransform in target to reference coordinate ---
        for axis in tar_joint_elem.iter('TransformAxis'):
            if axis.get('name') in src_axes_referencing:
                coords_elem = axis.find('coordinates')
                if coords_elem is None:
                    coords_elem = ET.SubElement(axis, 'coordinates')
                coords_elem.text = coord_name
                print(f"Updated TransformAxis '{axis.get('name')}' to reference '{coord_name}'.")

    # --- Fix empty <translation> tags ---
    for elem in tar_root.iter('translation'):
        if not elem.text or not elem.text.strip():
            elem.text = '0 0 0'

    save_path = target_model.replace('.osim', '_modified.osim')
    tar_tree.write(save_path, encoding='unicode', xml_declaration=True)
    print(f"Saved modified model to: {save_path}")

    # Verify all coordinates exist in saved XML
    verify_root = ET.parse(save_path).getroot()
    saved_coords = {c.get('name') for c in verify_root.iter('Coordinate')}
    for coord_name in coordinate_name:
        if coord_name in saved_coords:
            print(f"Verified: '{coord_name}' exists in the modified model.")
        else:
            print(f"Error: '{coord_name}' not found in the modified model.")

    # Validate by loading with OpenSim API; save to separate file
    validated_path = save_path.replace('.osim', '_validated.osim')
    model = _quiet_model(save_path)
    model.initSystem()
    model.setName('tps_transformed_with_added_coordinates')
    model.printToXML(validated_path)
    print(f"OpenSim-validated model saved to: {validated_path}")

def checkMuscleMomentArms(model_file_path=None, ik_file_path=None, leg = 'l', threshold = 0.005):
    '''
    Adapted from Willi Koller: https://github.com/WilliKoller/OpenSimMatlabBasic/blob/main/checkMuscleMomentArms.m
    Models Verified for:
        - Rajagopal 2015
        - Cateli 
    '''
    def get_model_coord(model, coord_name):
        try:
            index = model.getCoordinateSet().getIndex(coord_name)
            coord = model.updCoordinateSet().get(index)
        except:
            index = None
            coord = None
            print(f'Coordinate {coord_name} not found in model')
        
        return index, coord

    if not model_file_path or not os.path.isfile(model_file_path):
        model_file_path = input("Enter path to OpenSim model (.osim): ").strip('"')

    if not ik_file_path or not os.path.isfile(ik_file_path):
        ik_file_path = input("Enter path to OpenSim motion file (.mot or .sto): ").strip('"')

    # raise Exception('This function is not yet working. Please use the Matlab version for now or fix line containing " time_discontinuity.append(time_vector[discontinuity_indices]) "')

    # Load motions and model
    motion = osim.Storage(ik_file_path)
    model = _quiet_model(model_file_path)

    # Initialize system and state
    model.initSystem()
    state = model.initSystem()

    # coordinate names
    flexIndexLHip, flexCoordLHip = get_model_coord(model, 'hip_flexion_' + leg)
    rotIndexLHip, rotCoordLHip = get_model_coord(model, 'hip_rotation_' + leg)
    addIndexLHip, addCoordLHip = get_model_coord(model, 'hip_adduction_' + leg)
    addIndexLKnee, addCoordLKnee = get_model_coord(model, 'knee_adduction_' + leg)
    flexIndexLKnee, flexCoordLKnee = get_model_coord(model, 'knee_angle_' + leg)
    flexIndexLAnk, flexCoordLAnk = get_model_coord(model, 'ankle_angle_' + leg)

    # get names of the hip muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_hip = []
    muscleNames_hip = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        if ('add' in tmp_muscleName or 'gl' in tmp_muscleName or 'semi' in tmp_muscleName or 'bf' in tmp_muscleName or
                'grac' in tmp_muscleName or 'piri' in tmp_muscleName or 'sart' in tmp_muscleName or 'tfl' in tmp_muscleName or
                'iliacus' in tmp_muscleName or 'psoas' in tmp_muscleName or 'rect' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_hip.append(i)
            muscleNames_hip.append(tmp_muscleName)

    flexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))
    addMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))
    rotMomentArms = np.zeros((motion.getSize(), len(muscleIndices_hip)))

    # get names of the knee muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_knee = []
    muscleNames_knee = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        if ('bf' in tmp_muscleName or 'gas' in tmp_muscleName or 'grac' in tmp_muscleName or 'sart' in tmp_muscleName or
                'semim' in tmp_muscleName or 'semit' in tmp_muscleName or 'rec' in tmp_muscleName or 'vas' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_knee.append(i)
            muscleNames_knee.append(tmp_muscleName)

    kneeFlexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_knee)))

    # get names of the ankle muscles
    numMuscles = model.getMuscles().getSize()
    muscleIndices_ankle = []
    muscleNames_ankle = []
    for i in range(numMuscles):
        tmp_muscleName = str(model.getMuscles().get(i).getName())
        print(tmp_muscleName)
        if ('edl' in tmp_muscleName or 'ehl' in tmp_muscleName or 'tibant' in tmp_muscleName or 'gas' in tmp_muscleName or
                'fdl' in tmp_muscleName or 'fhl' in tmp_muscleName or 'perb' in tmp_muscleName or 'perl' in tmp_muscleName or
                'sole' in tmp_muscleName or 'tibpos' in tmp_muscleName) and ('_' + leg in tmp_muscleName):
            muscleIndices_ankle.append(i)
            muscleNames_ankle.append(tmp_muscleName)

    ankleFlexMomentArms = np.zeros((motion.getSize(), len(muscleIndices_ankle)))

    # compute moment arms for each muscle and create time vector
    time_vector = []
    for i in range(1, motion.getSize()):
        flexAngleL = motion.getStateVector(i-1).getData().get(flexIndexLHip) / 180 * np.pi
        rotAngleL = motion.getStateVector(i-1).getData().get(rotIndexLHip) / 180 * np.pi
        addAngleL = motion.getStateVector(i-1).getData().get(addIndexLHip) / 180 * np.pi
        addAngleLKnee = motion.getStateVector(i-1).getData().get(addIndexLKnee) / 180 * np.pi
        flexAngleLknee = motion.getStateVector(i-1).getData().get(flexIndexLKnee) / 180 * np.pi
        flexAngleLank = motion.getStateVector(i-1).getData().get(flexIndexLAnk) / 180 * np.pi

        time_vector.append(motion.getStateVector(i-1).getTime())
        # Update the state with the joint angle
        coordSet = model.updCoordinateSet()
        coordSet.get(flexIndexLHip).setValue(state, flexAngleL)
        coordSet.get(rotIndexLHip).setValue(state, rotAngleL)
        coordSet.get(addIndexLHip).setValue(state, addAngleL)
        coordSet.get(flexIndexLKnee).setValue(state, flexAngleLknee)
        coordSet.get(addIndexLKnee).setValue(state, addAngleLKnee)
        coordSet.get(flexIndexLAnk).setValue(state, flexAngleLank)

        # Realize the state to compute dependent quantities
        model.computeStateVariableDerivatives(state)
        model.realizeVelocity(state)

        # Compute the moment arm hip
        for j in range(len(muscleIndices_hip)):
            muscleIndex = muscleIndices_hip[j]
            if muscleNames_hip[j][-1] == leg:
                flexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordLHip)
                flexMomentArms[i, j] = flexMomentArm

                rotMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, rotCoordLHip)
                rotMomentArms[i, j] = rotMomentArm

                addMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, addCoordLHip)
                addMomentArms[i, j] = addMomentArm

        # Compute the moment arm knee
        for j in range(len(muscleNames_knee)):
            muscleIndex = muscleIndices_knee[j]
            if muscleNames_knee[j][-1] == leg:
                kneeFlexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordLKnee)
                kneeFlexMomentArms[i, j] = kneeFlexMomentArm

                kneeAddMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, addCoordLKnee)
                addMomentArms[i, j] = kneeAddMomentArm

        # Compute the moment arm ankle
        for j in range(len(muscleNames_ankle)):
            muscleIndex = muscleIndices_ankle[j]
            if muscleNames_ankle[j][-1] == leg:
                ankleFlexMomentArm = model.getMuscles().get(muscleIndex).computeMomentArm(state, flexCoordLAnk)
                ankleFlexMomentArms[i, j] = ankleFlexMomentArm

    # check discontinuities
    discontinuity = []
    muscle_action = []
    time_discontinuity = []
    discontinuity_frames = []

    fDistC = plt.figure('Discontinuity', figsize=(8, 8))
    plt.title(ik_file_path)

    save_folder = os.path.join(os.path.dirname(ik_file_path),'momentArmsCheck')

    def find_discontinuities(momArms, threshold, muscleNames, action, discontinuity, muscle_action, time_discontinuity, discontinuity_frames):
        for i in range(momArms.shape[1]):
            dy = np.diff(momArms[:, i])
            discontinuity_indices = np.where(np.abs(dy) > threshold)[0]
            if discontinuity_indices.size > 0:
                print('Discontinuity detected at', muscleNames[i], 'at ', action, ' moment arm')
                plt.plot(momArms[:, i])
                plt.plot(discontinuity_indices, momArms[discontinuity_indices, i], 'rx')
                discontinuity.append(i)
                muscle_action.append(str(muscleNames[i] + ' ' + action + ' at frames: ' + str(discontinuity_indices)))
                time_discontinuity.append([time_vector[index] for index in discontinuity_indices])
                discontinuity_frames.append(discontinuity_indices)


        return discontinuity, muscle_action, time_discontinuity, discontinuity_frames

    # hip flexion
    discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
        flexMomentArms, threshold, muscleNames_hip, 'flexion', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)

    # hip adduction
    discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
        addMomentArms, threshold, muscleNames_hip, 'adduction', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)
    
    # hip rotation
    discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
        rotMomentArms, threshold, muscleNames_hip, 'rotation', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)
    
    # knee flexion
    discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
        kneeFlexMomentArms, threshold, muscleNames_knee, 'flexion', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)
    
    # knee adduction
    try:
        discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
            addMomentArms, threshold, muscleNames_knee, 'adduction', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)
    except Exception as e:
        print(f'Error in knee adduction discontinuity check: {e}')
    
    # ankle flexion
    discontinuity, muscle_action, time_discontinuity, discontinuity_frames = find_discontinuities(
        ankleFlexMomentArms, threshold, muscleNames_ankle, 'dorsiflexion', discontinuity, muscle_action, time_discontinuity, discontinuity_frames)
    
    # plot discontinuities
    if len(discontinuity) > 0:
        plt.legend(muscle_action)
        plt.ylabel('Muscle Moment Arms with discontinuities (m)')
        plt.xlabel('Frame (after start time)')
        utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'discontinuities_' + leg + '.png'))
        print('\n\nYou should alter the model - most probably you have to reduce the radius of corresponding wrap objects for the identified muscles\n\n\n')

        # save txt file with discontinuities
        with open(os.path.join(save_folder, 'discontinuities_' + leg + '.txt'), 'w') as f:
            f.write(f"model file = {model_file_path}\n")
            f.write(f"motion file = {ik_file_path}\n")
            f.write(f"leg checked = {leg}\n")
            
            f.write("\n muscles with discontinuities \n", ) 
            
            for i in range(len(muscle_action)):
                try:
                    f.write("%s : time %s \n" % (muscle_action[i], time_discontinuity[i]))
                except:
                    print('no discontinuities detected')

        momentArmsAreWrong = 1
    else:
        plt.close(fDistC)
        print('No discontinuities detected')
        momentArmsAreWrong = 0

    # plot hip flexion
    plt.figure('flexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(flexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Flexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_flex_MomentArms_' + leg + '.png'))

    # hip adduction
    plt.figure('addMomentArms_' + leg, figsize=(8, 8))
    plt.plot(addMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Adduction Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_add_MomentArms_' + leg + '.png'))

    # hip rotation
    plt.figure('rotMomentArms_' + leg, figsize=(8, 8))
    plt.plot(rotMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_hip, loc='best')
    plt.ylabel('Hip Rotation Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'hip_rot_MomentArms_' + leg + '.png'))

    # knee flexion
    plt.figure('kneeFlexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(kneeFlexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_knee, loc='best')
    plt.ylabel('Knee Flexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'knee_MomentArms_' + leg + '.png'))

    # ankle flexion
    plt.figure('ankleFlexMomentArms_' + leg, figsize=(8, 8))
    plt.plot(ankleFlexMomentArms)
    plt.title('All muscle moment arms in motion ' + ik_file_path)
    plt.legend(muscleNames_ankle, loc='best')
    plt.ylabel('Ankle Dorsiflexion Moment Arm (m)')
    plt.xlabel('Frame (after start time)')
    utils.save_fig(plt.gcf(), save_path=os.path.join(save_folder, 'ankle_MomentArms_' + leg + '.png'))

    print('Moment arms checked for ' + ik_file_path)
    print('Results saved in ' + save_folder + ' \n\n' )

    return momentArmsAreWrong, discontinuity, muscle_action, discontinuity_frames

def muscles_per_coordinate(osimModel=None):

    if osimModel is None:
        osimModel = input("Enter path to OpenSim model (.osim): ").strip('"')
        osimModel = _quiet_model(osimModel)


    muscles = {}
    indexes = {}
    coordSet = osimModel.getCoordinateSet()

    for i in range(coordSet.getSize()):
        coord = coordSet.get(i)    
        coord_name = coord.getName()
        muscles[coord_name] = []
        indexes[coord_name] = []
        coord = osimModel.getCoordinateSet().get(coord_name)
        state = osimModel.initSystem()
        osimModel.realizePosition(state)

        for i in range(osimModel.getMuscles().getSize()):
            muscle = osimModel.getMuscles().get(i)
            if abs(muscle.computeMomentArm(state, coord)) > 1e-4:
                muscles[coord_name].append(muscle.getName())
                indexes[coord_name].append(i)

    if __name__ == "__main__":
        
        for coord_name in muscles.keys():
            print(f'coordinate: {coord_name} : \n')
            print(muscles[coord_name])
            print('\n')

    return muscles, indexes

def sampleMuscleQuantities(osimModel, osimMuscle, muscleQuant, N_eval):
    """Sample muscle-tendon quantities across the range of motion of the
    coordinates spanned by the muscle (Modenese 2015 muscle optimiser helper).

    For each combination of N_eval values per spanned coordinate the model is
    posed, muscles are equilibrated (elastic tendon, activation = 1) and the
    following are recorded per evaluation point:

        [muscleTendonLength, normalizedFiberLength, tendonLength,
         normalizedFiberLength*cos(pennation), pennationAngle]

    muscleQuant='MTL' returns only muscleTendonLength per point; 'all' returns
    the full row above (the indices used by optimMuscleParams are 0,1,2,4).
    """
    import itertools

    state = osimModel.initSystem()
    gp = osimMuscle.getGeometryPath()
    coords = osimModel.getCoordinateSet()

    # getMuscles().get(...) hands back a base-class Muscle handle, and
    # computeInitialFiberEquilibrium is declared on the CONCRETE type
    # (Millard2012EquilibriumMuscle, Thelen2003Muscle, ...). Without this
    # downcast BOTH getattr lookups in _equilibrate_single miss, every
    # evaluation point falls through to equilibrateMuscles(), and the whole
    # model is equilibrated to sample one muscle. Measured on this project's
    # 80-muscle Catelli model: 0.39 ms/call for the model against 0.010 ms for
    # the single muscle. The comment below always claimed it equilibrated only
    # the current muscle; until now it never did.
    _mus = osimMuscle
    try:
        _cc = getattr(osim, osimMuscle.getConcreteClassName(), None)
        if _cc is not None and hasattr(_cc, "safeDownCast"):
            _mus = _cc.safeDownCast(osimMuscle) or osimMuscle
    except Exception:                                        # noqa: BLE001
        pass

    def _equilibrate_single():
        """Equilibrate ONLY the current muscle (not all ~100 muscles)."""
        for meth in ("computeInitialFiberEquilibrium", "computeFiberEquilibrium"):
            fn = getattr(_mus, meth, None)
            if fn is not None:
                try:
                    fn(state)
                    return
                except Exception:
                    pass
        try:
            osimModel.equilibrateMuscles(state)   # fallback (slow)
        except Exception:
            pass

    # --- coordinates spanned by the muscle (non-zero moment arm in ROM) -------
    # Detection only needs the muscle path length/moment arm, so realizePosition
    # (cheap) is enough here -- no need for the full constraint assembler.
    _skip = tuple(MUSCLE_OPT_SKIP_COORDS or ())
    _ma_tol = float(MUSCLE_OPT_MA_TOL)
    spanned = []
    _excluded = []
    for i in range(coords.getSize()):
        c = coords.get(i)
        try:
            if c.getLocked(state) or c.isConstrained(state):
                continue
        except Exception:
            pass
        _nm = c.getName()
        if any(_s == _nm or _s in _nm for _s in _skip):
            _excluded.append(_nm)
            continue
        rmin, rmax = c.getRangeMin(), c.getRangeMax()
        hit = False
        for frac in (0.0, 0.5, 1.0):
            c.setValue(state, rmin + frac * (rmax - rmin), False)
            osimModel.realizePosition(state)
            try:
                if abs(gp.computeMomentArm(state, c)) > _ma_tol:
                    hit = True
                    break
            except Exception:
                pass
        c.setValue(state, 0.5 * (rmin + rmax), False)
        if hit:
            spanned.append(i)

    # --- full-factorial grid over the spanned coordinates --------------------
    # Bound the grid BEFORE building it: cap the number of DOFs and reduce the
    # points-per-axis so N_per**nDOF stays under MAX_EVAL_POINTS (a full product
    # of N_eval**nDOF would blow up memory for multi-joint muscles).
    MAX_DOF = 6
    if len(spanned) > MAX_DOF:
        spanned = spanned[:MAX_DOF]
    nDOF = len(spanned)
    if _excluded:
        print(f"      [opt] {osimMuscle.getName()}: {nDOF} DOF "
              f"(excluded {', '.join(_excluded)})")
    n_per = N_eval
    if nDOF and n_per ** nDOF > MAX_EVAL_POINTS:
        n_per = max(2, int(MAX_EVAL_POINTS ** (1.0 / nDOF)))
    axes = [np.linspace(coords.get(i).getRangeMin(),
                        coords.get(i).getRangeMax(), n_per) for i in spanned]
    combos = list(itertools.product(*axes)) if axes else [()]

    need_equil = (muscleQuant != 'MTL')                   # MTL needs geometry only
    if need_equil:
        try:
            osimMuscle.setActivation(state, 1.0)
        except Exception:
            pass

    musOutput = []
    for combo in combos:
        # set independent coords; enforce constraints once (updates coupled DOFs)
        for k, i in enumerate(spanned):
            coords.get(i).setValue(state, float(combo[k]),
                                   k == len(spanned) - 1)
        if not spanned:
            osimModel.assemble(state)

        if not need_equil:
            osimModel.realizePosition(state)
            musOutput.append(osimMuscle.getLength(state))
            continue

        osimModel.realizeVelocity(state)
        _equilibrate_single()
        MTL = osimMuscle.getLength(state)
        try:
            LfibNorm = osimMuscle.getNormalizedFiberLength(state)
            Lten = osimMuscle.getTendonLength(state)
            penAngle = osimMuscle.getPennationAngle(state)
        except Exception:
            LfibNorm, Lten, penAngle = np.nan, np.nan, 0.0
        musOutput.append([MTL, LfibNorm, Lten,
                          LfibNorm * np.cos(penAngle), penAngle])
    return musOutput

# --- Static optimisation --
def edit_pelvis_com_actuators(osim_modelPath, actuatorsFilePath):
    """
    Edit the pelvis center of mass actuator in the OpenSim model.
    """ 
    model = _quiet_model(osim_modelPath)
    model.initSystem()

    # Find the pelvis center of mass actuator
    pelvis = model.getBodySet().get('pelvis')
    com = pelvis.get_mass_center().to_numpy()

    actuators = utils.read_xml(actuatorsFilePath)
    point_actuators = actuators.find('ForceSet').find('objects').findall('PointActuator')
    
    for actuator in point_actuators:
        if actuator.get('name') in ['FX', 'FY', 'FZ']:
            # Update the point in the actuator to match the pelvis center of mass
            point = actuator.find('point')
            point.text = f"{com[0]} {com[1]} {com[2]}"
    
    # Save the modified actuators file
    utils.save_pretty_xml(actuators, actuatorsFilePath)
    
    print(f"Updated pelvis center of mass actuator in {actuatorsFilePath} to {com}")

def normalise_muscle(muscle_forces_path, osim_modelPath):
    
    muscle_forces = utils.load_any_data_file(muscle_forces_path)
    model = _quiet_model(osim_modelPath)
    model_muscles = model.getMuscles()
    for muscle in muscle_forces.columns:
        try:
            muscle_obj = model_muscles.get(muscle)
        except Exception as e:
            print(f"Error retrieving muscle '{muscle}': {e}")
            continue
                
        # Normalize the muscle forces
        normalized_forces = muscle_forces[muscle] / muscle_obj.getMaxIsometricForce()
        
        # Save the normalized forces back to the DataFrame
        muscle_forces[muscle] = normalized_forces
    
    # Save the normalized muscle forces to a new file
    header = utils.load_sto_header(muscle_forces_path)
    utils.write_sto_file(muscle_forces, muscle_forces_path.replace('.sto', '_normalised.sto'), header=header)
    
    print(f"Normalized muscle forces saved to {muscle_forces_path.replace('.sto','_normalised.sto')}")

# --- Joint Reaction Analysis ---
def _strip_trailing_nulls(osim_path):
    """If an .osim (or any XML) file is padded with NUL bytes after its closing
    tag (a corruption some TPS/warping tools produce that segfaults ScaleTool),
    truncate the padding in place — backing up the original as ``<file>.nulbak``.
    Returns the (now clean) path. No-op if the file has no NULs."""
    import shutil as _shutil
    try:
        with open(osim_path, "rb") as f:
            b = f.read()
        if b.count(0) == 0:
            return osim_path
        end = b.rfind(b"</OpenSimDocument>")
        if end < 0:
            end = b.rfind(b">")                    # generic XML fallback
        if end < 0:
            return osim_path
        cut = end + (len(b"</OpenSimDocument>") if b[end:end + 18] == b"</OpenSimDocument>" else 1)
        if b[cut:cut + 2] == b"\r\n":
            cut += 2
        elif b[cut:cut + 1] == b"\n":
            cut += 1
        clean = b[:cut]
        if clean.count(0):                          # still dirty -> leave it alone
            return osim_path
        if not os.path.exists(osim_path + ".nulbak"):
            _shutil.copy2(osim_path, osim_path + ".nulbak")
        with open(osim_path, "wb") as f:
            f.write(clean)
        print(f"[scale] stripped {b.count(0)} trailing NUL bytes from "
              f"{os.path.basename(osim_path)} (backup: {os.path.basename(osim_path)}.nulbak)")
    except Exception:
        pass
    return osim_path
