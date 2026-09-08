"""OpenSim pipeline stages and the input prep that feeds them.

The ``simulate`` verb's engine: IK -> ID -> MA -> SO -> JRA (plus CMC, RRA,
IAA, energetics, body kinematics), the trc/mot/grf/xml wrangling each stage
needs, and ``run_emg_normalise`` (a pipeline STAGE -- the EMG domain logic it
calls lives in ``bioscout.emg``).

Model creation and editing are NOT here: see ``bioscout.model``
(``opensim_base`` for load_model and the logger plumbing, ``scale/`` for
ScaleTool, ``edit/`` for .osim edits, ``muscle_optimize`` for Modenese-2015).

Split out of the old ``bioscout/utils/openSim.py`` (docs/RESTRUCTURE_PLAN.md,
stage 6) -- the code is unchanged, only its address.
"""
import os
import sys
import datetime
from time import time
from xml.etree import ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import opensim as osim

try:                                    # the project's settings.py, if it has one
    from bioscout import settings
except Exception:                       # noqa: BLE001 - absent or mid-cycle
    settings = None
from bioscout import utils
from bioscout.model.opensim_base import (_assembly_accuracy, _osim_quiet_ctx,
                                         _quiet_console, _quiet_model,
                                         load_model)


_RESIDUAL_NAMES = ("FX", "FY", "FZ", "MX", "MY", "MZ")

# c3d export functions
def c3d_to_trc(c3d_file_path, emg_string_list=['emg'], create_folder=True):
    """
    Export a C3D file using the exportC3D module.

    Args:
        c3d_file_path (str): Path to the C3D file to export.
        emg_string_list (list): List of EMG channel prefixes to filter.
        create_folder (bool): Whether to create output folder if it doesn't exist.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Call the export function
        from bioscout.session import exportC3D   # lazy: exportC3D imports us back
        exportC3D.main(
            c3d_file_path,
            emg_string_list=emg_string_list,
            create_folder=create_folder
        )

        return True, f"C3D file exported successfully: {c3d_file_path}"

    except Exception as e:
        import traceback
        return False, f"Error exporting C3D file: {str(e)}\n{traceback.format_exc()}"

def convert_trc_os3_to_os4(trc_file_path: str = '', output_trc_file_path: str = ''):
    """
    Convert a .trc file from OpenSim 3 format to OpenSim 4 format.

    Parameters:
    trc_file_path (str): Path to the input .trc file in OpenSim 3 format.
    output_trc_file_path (str): Path to save the converted .trc file in OpenSim 4 format.
    """

    if not os.path.isfile(trc_file_path):
        trc_file_path = input("Enter the path to the .trc file to convert: ").strip('"')

    if not output_trc_file_path:
        output_trc_file_path = trc_file_path.replace('.trc', '_os4.trc')

    trc_df = utils.load_any_data_file(trc_file_path)  # This will raise an error if the file is not found or not a valid .trc file

    def load_trc_metadata_os3(trc_file_path):
        with open(trc_file_path, 'r') as file:
            lines = file.readlines()
        
        metadata = {}
        for i, line in enumerate(lines):
            parts = line.strip().split('\t')
            if parts[0] == "DataRate" and i + 1 < len(lines):
                values = lines[i + 1].strip().split('\t')
                keys = parts
                type_map = {'DataRate': float, 'CameraRate': float, 'NumFrames': int,
                            'NumMarkers': int, 'Units': str, 'OrigDataRate': float,
                            'DataStartFrame': int, 'OrigNumFrames': int}
                for key, val in zip(keys, values):
                    if key in type_map:
                        metadata[key] = type_map[key](val)
                break
        
        return metadata
    
    trc_metadata = load_trc_metadata_os3(trc_file_path)

    # remove columnn 'Frame#' if it exists
    if 'Frame#' in trc_df.columns:
        trc_df = trc_df.drop(columns=['Frame#'])

    utils.write_trc(trc_df,
                    trc_file=output_trc_file_path,
                    units=trc_metadata.get('Units'),
                    frame_rate=trc_metadata.get('DataRate'),
                    first_frame=trc_metadata.get('DataStartFrame'))

    print(f"Converted .trc file saved to: {output_trc_file_path}")

# Marker data and inverse kinematics functions
def add_joint_centers_to_trc(input_trc_path=None, output_trc_path=None, marker_map=None):
    """
    Add hip, knee, and ankle joint centre markers to a TRC file.

    New markers added (if computable):
      - RHJC, LHJC (hip joint centres)
      - RKJC, LKJC (knee joint centres)
      - RAJC, LAJC (ankle joint centres)

    Inputs:
        - input_trc_path: path to input TRC file 
        - output_trc_path: path to output TRC file (if None, will save in same directory with suffix '_with_JointCenters')
        - marker_map: dictionary specifying marker names for pelvis, knee pairs, ankle pairs, and existing hip markers.

    """
    if input_trc_path is None:
        input_trc_path = input("Enter path to input TRC file: ").strip('"')

    if output_trc_path is None:
        output_trc_path = input_trc_path.replace(".trc", "_with_JointCenters.trc")

    # -----------------------------
    # TRC read
    # -----------------------------
    with open(input_trc_path, "r") as f:
        lines = f.readlines()

    if len(lines) < 6:
        raise ValueError(f"Invalid TRC file: {input_trc_path}")

    header_1 = lines[0].rstrip("\n")
    header_keys = [x for x in lines[1].strip().split("\t") if x != ""]
    header_vals = [x for x in lines[2].strip().split("\t") if x != ""]

    marker_header = lines[3].rstrip("\n")
    coord_header = lines[4].rstrip("\n")

    df = pd.read_csv(input_trc_path, sep="\t", skiprows=5, header=None)

    marker_names = [m for m in marker_header.split("\t")[2:] if m.strip()]
    cols = ["Frame#", "Time"]
    for m in marker_names:
        cols.extend([f"{m}_X", f"{m}_Y", f"{m}_Z"])

    df = df.iloc[:, :len(cols)]
    df.columns = cols

    # -----------------------------
    # helpers
    # -----------------------------
    def has_marker(m):
        return all(c in df.columns for c in [f"{m}_X", f"{m}_Y", f"{m}_Z"])

    def get_marker_xyz(m):
        return df[[f"{m}_X", f"{m}_Y", f"{m}_Z"]].to_numpy(dtype=float)

    def set_marker_xyz(m, xyz):
        df[f"{m}_X"] = xyz[:, 0]
        df[f"{m}_Y"] = xyz[:, 1]
        df[f"{m}_Z"] = xyz[:, 2]

    def midpoint(m1, m2):
        return 0.5 * (get_marker_xyz(m1) + get_marker_xyz(m2))

    def first_valid_pair(pairs):
        for a, b in pairs:
            if has_marker(a) and has_marker(b):
                return a, b
        return None

    # -----------------------------
    # default marker map
    # -----------------------------
    default_map =  {
        "pelvis": {"LASI": "LASI", "RASI": "RASI", "LPSI": "LPSI", "RPSI": "RPSI"},
        "knee_r_pairs": [("RLFC", "RMFC"), ("RKNE", "RKNM"), ("RKNE", "RKNI"), ("RLK", "RMK")],
        "knee_l_pairs": [("LLFC", "LMFC"), ("LKNE", "LKNM"), ("LKNE", "LKNI"), ("LLK", "LMK")],
        "ankle_r_pairs": [("RANK", "RMED"), ("RANK", "RANM"), ("RANK", "RANKM"), ("RLA", "RMA")],
        "ankle_l_pairs": [("LANK", "LMED"), ("LANK", "LANM"), ("LANK", "LANKM"), ("LLA", "LMA")],
        "existing_hip_r": ["RHJC", "RHIP"],
        "existing_hip_l": ["LHJC", "LHIP"],
        }
    if marker_map is None:
        marker_map = default_map

    # -----------------------------
    # hip centres (Harrington-style pelvis-frame estimate)
    # -----------------------------
    rhjc_added = False
    lhjc_added = False

    # Use existing hip markers if present
    for m in marker_map["existing_hip_r"]:
        if has_marker(m):
            set_marker_xyz("RHJC", get_marker_xyz(m))
            rhjc_added = True
            break

    for m in marker_map["existing_hip_l"]:
        if has_marker(m):
            set_marker_xyz("LHJC", get_marker_xyz(m))
            lhjc_added = True
            break

    # If not available, estimate from pelvis landmarks
    pelvis = marker_map["pelvis"]
    if (not rhjc_added or not lhjc_added) and all(has_marker(pelvis[k]) for k in ["LASI", "RASI", "LPSI", "RPSI"]):
        LASI = get_marker_xyz(pelvis["LASI"])
        RASI = get_marker_xyz(pelvis["RASI"])
        LPSI = get_marker_xyz(pelvis["LPSI"])
        RPSI = get_marker_xyz(pelvis["RPSI"])

        mid_asis = 0.5 * (LASI + RASI)
        mid_psi = 0.5 * (LPSI + RPSI)

        # pelvis axes
        z_axis = RASI - LASI  # left -> right
        z_axis /= np.linalg.norm(z_axis, axis=1, keepdims=True)

        x_axis = mid_asis - mid_psi  # posterior -> anterior
        x_axis /= np.linalg.norm(x_axis, axis=1, keepdims=True)

        y_axis = np.cross(z_axis, x_axis)  # superior
        y_axis /= np.linalg.norm(y_axis, axis=1, keepdims=True)

        # re-orthogonalize x
        x_axis = np.cross(y_axis, z_axis)
        x_axis /= np.linalg.norm(x_axis, axis=1, keepdims=True)

        pelvis_width = np.linalg.norm(RASI - LASI, axis=1)   # mm
        pelvis_depth = np.linalg.norm(mid_asis - mid_psi, axis=1)  # mm

        # Harrington-like offsets (mm)
        x_post = -0.24 * pelvis_depth - 9.9
        y_inf = -0.30 * pelvis_width - 10.9
        z_lat = 0.33 * pelvis_width + 7.3

        # right(+z), left(-z)
        RHJC = mid_asis + x_axis * x_post[:, None] + y_axis * y_inf[:, None] + z_axis * z_lat[:, None]
        LHJC = mid_asis + x_axis * x_post[:, None] + y_axis * y_inf[:, None] - z_axis * z_lat[:, None]

        if not rhjc_added:
            set_marker_xyz("RHJC", RHJC)
        if not lhjc_added:
            set_marker_xyz("LHJC", LHJC)

    # -----------------------------
    # knee centres
    # -----------------------------
#     breakpoint()
    pair = first_valid_pair(marker_map["knee_r_pairs"])
    if pair is not None:
        set_marker_xyz("RKJC", midpoint(*pair))

    pair = first_valid_pair(marker_map["knee_l_pairs"])
    if pair is not None:
        set_marker_xyz("LKJC", midpoint(*pair))

    # -----------------------------
    # ankle centres
    # -----------------------------
    pair = first_valid_pair(marker_map["ankle_r_pairs"])
    if pair is not None:
        set_marker_xyz("RAJC", midpoint(*pair))

    pair = first_valid_pair(marker_map["ankle_l_pairs"])
    if pair is not None:
        set_marker_xyz("LAJC", midpoint(*pair))

    # -----------------------------
    # TRC write
    # -----------------------------
    out_marker_names = [c[:-2] for c in df.columns if c.endswith("_X")]
    num_markers = len(out_marker_names)

    # update header values
    header_map = dict(zip(header_keys, header_vals))
    if "NumFrames" in header_map:
        header_map["NumFrames"] = str(len(df))
    if "NumMarkers" in header_map:
        header_map["NumMarkers"] = str(num_markers)

    updated_vals = [header_map.get(k, "") for k in header_keys]
    line2 = "\t".join(header_keys) + "\n"
    line3 = "\t".join(updated_vals) + "\n"

    # marker + coord header
    line4_parts = ["Frame#", "Time"]
    for m in out_marker_names:
        line4_parts.extend([m, "", ""])
    line4 = "\t".join(line4_parts).rstrip() + "\n"

    line5_parts = ["", ""]
    for i in range(1, num_markers + 1):
        line5_parts.extend([f"X{i}", f"Y{i}", f"Z{i}"])
    line5 = "\t".join(line5_parts).rstrip() + "\n"

    with open(output_trc_path, "w") as f:
        f.write(header_1 + "\n")
        f.write(line2)
        f.write(line3)
        f.write(line4)
        f.write(line5)
        df.to_csv(f, sep="\t", index=False, header=False, float_format="%.6f", lineterminator="\n")

    print(f"Saved TRC with joint centres: {output_trc_path}")

def validate_markers_used(osim_modelPath, ikTool, markers_path):

    def get_all_marker_parent_frames(model_path):
        model = _quiet_model(model_path)
        model.initSystem()

        marker_set = model.getMarkerSet()
        result = {}
        for i in range(marker_set.getSize()):
            marker = marker_set.get(i)
            result[marker.getName()] = marker.getParentFrameName()
        return result

    model =  _quiet_model(osim_modelPath)
    markerSet = model.get_MarkerSet() 
    markers_model = [marker.getName() for marker in markerSet]

    task_set_template = ikTool.upd_IKTaskSet()
    markers_df = utils.load_trc(markers_path)
    markers_trc = markers_df.columns.get_level_values(0).unique().tolist()
    
    for marker_name in markers_model:
        if marker_name not in markers_trc:
            print(f"Warning: Marker '{marker_name}' not found in TRC file.")

    markers_in_task = [task.getName() for task in task_set_template if isinstance(task, osim.IKMarkerTask)]
    markers_parent_frames = get_all_marker_parent_frames(osim_modelPath)

    # Marker IK weights are keyed by the parent BODY (e.g. 'pelvis', 'femur_r',
    # 'calcn_l') in BatchSettings.marker_weights. NOTE: the value lives on the
    # BatchSettings *class*, not the settings module — `settings.marker_weights`
    # raised AttributeError and silently forced every weight to 1.0. Markers
    # whose body isn't listed default to 1.0.
    try:
        _marker_weights = dict(getattr(settings.BatchSettings, 'marker_weights', {}) or {})
    except Exception:
        _marker_weights = {}

    # Markers to exclude from IK entirely (e.g. belt/noise markers BL, BR). Their
    # IK task is disabled so they don't pull the fit. Listed in
    # BatchSettings.markers_to_skip; matched case-insensitively.
    try:
        _skip = {str(s).upper() for s in getattr(settings.BatchSettings, 'markers_to_skip', []) or []}
    except Exception:
        _skip = set()

    def _weight_for(_mname):
        _pf = (markers_parent_frames.get(_mname) or "").replace("/bodyset/", "")
        return float(_marker_weights.get(_pf, 1.0)), _pf

    for marker_name in markers_model:
        _w, _pf = _weight_for(marker_name)
        _skipped = marker_name.upper() in _skip
        _in_trc = (marker_name in markers_trc) and not _skipped
        if marker_name in markers_in_task:
            task = task_set_template.get(marker_name)
            task.setWeight(_w)                 # apply weight to template markers too
            task.setApply(_in_trc)
            if _skipped:
                print(f"Marker '{marker_name}' SKIPPED (markers_to_skip). Disabling task.")
            elif not _in_trc:
                print(f"Marker '{marker_name}' not found in TRC file. Disabling task.")
            else:
                print(f"Marker '{marker_name}' weight={_w} (body '{_pf}').")
        else:
            newTask = osim.IKMarkerTask()
            newTask.setName(marker_name)
            newTask.setWeight(_w)
            newTask.setApply(_in_trc)
            if _skipped:
                print(f"Marker '{marker_name}' SKIPPED (markers_to_skip). Disabling task.")
            elif _in_trc:
                print(f"Marker '{marker_name}' added with weight={_w} (body '{_pf}').")
            else:
                print(f"Marker '{marker_name}' in Model not found in TRC file. Disabling task.")
            task_set_template.adoptAndAppend(newTask)


    
    return ikTool

def compare_marker_locations(marker_experimental_path=None, marker_virtual_path=None):
    """
    Calculates the root mean square error between experimental and virtual markers.

    Args:
        marker_experimental_path (str, optional): Path to the experimental .trc file.
        marker_virtual_path (str, optional): Path to the virtual .sto markers file.
    """

    # Select the trials if needed
    if not marker_experimental_path:
        marker_experimental_path = input("Enter path to experimental .trc markers file: ").strip('"')
        if not marker_experimental_path: return # User cancelled

    if not marker_virtual_path:
        marker_virtual_path = input("Enter path to virtual .sto markers file: ").strip('"')
        if not marker_virtual_path: return # User cancelled

    # Load marker data
    virtual_markers_df = utils.load_sto(marker_virtual_path)
    experimental_markers_df = utils.load_trc(marker_experimental_path,
                                combine_headers=True)

    exp_marker_names = experimental_markers_df.columns.get_level_values(0).unique().tolist()
    
    # Find frames to plot in the experimental data
    time = virtual_markers_df['time']
    
    # Find the closest indices in experimental time to the start and end of virtual time
    exp_time = experimental_markers_df['time']
    initial_index = (exp_time - time.iloc[0]).abs().idxmin()
    final_index = (exp_time - time.iloc[-1]).abs().idxmin()

    distances = pd.DataFrame({'time': time.values})
    
    # Marker errors describe IK quality -> write them next to the IK outputs,
    # i.e. the same folder as the virtual/model marker locations file
    # (<sim_trial>/external_biomechanics/). Deriving the folder from the
    # experimental TRC (marker_experimental_path) is wrong: that file lives in
    # the experimental data tree, so the errors ended up there.
    output_dir = os.path.dirname(os.path.abspath(marker_virtual_path))
    _extbio = os.path.join(os.path.dirname(output_dir), "external_biomechanics")
    if os.path.basename(output_dir) != "external_biomechanics" and os.path.isdir(_extbio):
        output_dir = _extbio
    mean_errors_filename = os.path.join(output_dir, '_ik_marker_errors_mean.txt')

    print('Calculating marker errors for all markers...')
    with open(mean_errors_filename, 'w') as f_mean_errors:
        f_mean_errors.write('mean errors for each marker (m)\n\n')

        for marker_name in exp_marker_names:

            if 'time' in marker_name.lower() or 'frame' in marker_name.lower():
                continue

            try:
                marker_name = marker_name.split('_')[0]
                exp_cols = [col for col in exp_marker_names if col.split('_')[0] == marker_name]
                virtual_cols = [col for col in virtual_markers_df.columns if col.split('_')[0] == marker_name]

                if not exp_cols or not virtual_cols:
                    continue

                # Get experimental data for the current time range and convert mm to m
                exp_slice = experimental_markers_df.iloc[initial_index:final_index + 1]
                x1 = pd.to_numeric(exp_slice[exp_cols[0]], errors='coerce').values / 1000.0
                y1 = pd.to_numeric(exp_slice[exp_cols[1]], errors='coerce').values / 1000.0
                z1 = pd.to_numeric(exp_slice[exp_cols[2]], errors='coerce').values / 1000.0

                # Get virtual data
                x2 = virtual_markers_df[virtual_cols[0]].values
                y2 = virtual_markers_df[virtual_cols[1]].values
                z2 = virtual_markers_df[virtual_cols[2]].values
                
                # Ensure arrays are the same length by trimming the longer one
                min_len = min(len(x1), len(x2))
                x1, y1, z1 = x1[:min_len], y1[:min_len], z1[:min_len]
                x2, y2, z2 = x2[:min_len], y2[:min_len], z2[:min_len]
                
                # Calculate the 3D distance
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
                distances[marker_name] = pd.Series(dist)

                # Write mean error to file
                mean_error_text = f'{marker_name} = {np.mean(dist):.4f} m\n'
                f_mean_errors.write(mean_error_text)

            except (KeyError, IndexError) as e:
                print(f"Could not process marker '{marker_name}'. It might be missing in one of the files. Error: {e}")

    # Write all distance data to a .sto file
    all_errors_filename = os.path.join(output_dir, '_ik_marker_errors_all.sto')
    utils.write_sto_file(distances.dropna(axis=1, how='all'), all_errors_filename)
    print(f"Mean errors saved to: {mean_errors_filename}")
    print(f"All error data saved to: {all_errors_filename}")
    
    # plot marker errors over time    
    plt.figure(figsize=(12, 6))
    for marker_name in distances.columns:
        if marker_name != 'time':
            plt.plot(distances['time'], distances[marker_name], label=marker_name)
    
    # plot mean error as a dashed line
    mean_errors = distances.drop(columns='time').mean(axis=1)
    plt.plot(distances['time'], mean_errors, label='Mean Error', linestyle='--', color='black')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Marker Error (m)')
    plt.title('Marker Errors Over Time')
    plt.legend()
    plt.grid()
    
    # save fig
    plt.savefig(os.path.join(output_dir, '_ik_marker_errors_plot.png'))
    plt.close()
    print(f"Marker errors plot saved to: {os.path.join(output_dir, '_ik_marker_errors_plot.png')}")

def assign_grfs_to_feet(grf_mot_path=None, marker_trc_path=None,
                        right_foot_markers=None, left_foot_markers=None,
                        right_foot_body='calcn_r', left_foot_body='calcn_l',
                        vert_force_threshold=10.0, max_cop_foot_dist_mm=None):
    """
    Detect force plates from a GRF .mot file and assign each to left/right foot.

    Loads the .mot file, auto-detects force-plate columns, then assigns each
    active plate to a foot by comparing median CoP Y with mean foot-marker Y
    from the TRC file.

    Parameters
    ----------
    grf_mot_path : str
        Path to the GRF .mot file.
    marker_trc_path : str, optional
        Path to the marker TRC file for anatomical assignment.
        If not provided, plates are sorted by CoP Y and alternated R/L.
    right_foot_markers : list of str, optional
        Marker names for right foot. Defaults to common heel/toe names.
    left_foot_markers : list of str, optional
        Marker names for left foot. Defaults to common heel/toe names.
    right_foot_body : str
        OpenSim body name for right foot (default 'calcn_r').
    left_foot_body : str
        OpenSim body name for left foot (default 'calcn_l').
    vert_force_threshold : float
        Minimum |Fy| in N to consider a plate active (default 10 N).

    Returns
    -------
    dict
        {plate_num_str: body_name}  e.g. {'4': 'calcn_r', '5': 'calcn_l'}
    """
    import re

    if not grf_mot_path:
        grf_mot_path = input('Paste the grf mot file path: ').strip('"')

    if not marker_trc_path:
        marker_trc_path = input('Paste the markers trc file path: ').strip('"')

    DEFAULT_RIGHT = ['RHEE', 'RTOE', 'RANK', 'RANM', 'RMED', 'RMT2', 'RCAL', 'RKNE']
    DEFAULT_LEFT  = ['LHEE', 'LTOE', 'LANK', 'LANM', 'LMED', 'LMT2', 'LCAL', 'LKNE']
    right_markers = list(right_foot_markers or DEFAULT_RIGHT)
    left_markers  = list(left_foot_markers  or DEFAULT_LEFT)

    # ------------------------------------------------------------------ #
    # 1. Load GRF file and detect plates from column names
    # ------------------------------------------------------------------ #
    grf_df = utils.load_sto(grf_mot_path)
    cols = grf_df.columns.tolist()

    plates = {}
    for col in cols:
        col_str = str(col)
        if col_str.lower() == 'time':
            continue
        nums = re.findall(r'\d+', col_str)
        if not nums:
            continue
        pnum = nums[0]
        plates.setdefault(pnum, {})
        if re.search(r'vx$', col_str, re.IGNORECASE) and 'force' in col_str.lower():
            plates[pnum]['force_id'] = col_str[:-1]        # strip trailing 'x'
        elif re.search(r'px$', col_str, re.IGNORECASE) and 'force' in col_str.lower():
            plates[pnum]['point_id'] = col_str[:-1]        # strip trailing 'x'
        elif re.search(r'x$', col_str, re.IGNORECASE) and 'torque' in col_str.lower():
            plates[pnum]['torque_id'] = col_str[:-1]

    valid = {k: v for k, v in plates.items()
             if 'force_id' in v and 'point_id' in v}
    if not valid:
        raise ValueError(f"No force-plate columns detected in {grf_mot_path}")

    print(f"Detected {len(valid)} force plate(s): {sorted(valid.keys(), key=int)}")

    # ------------------------------------------------------------------ #
    # 2. Median CoP Y for each active plate
    # ------------------------------------------------------------------ #
    def find_col(name):
        nl = name.lower()
        for c in grf_df.columns:
            if str(c).lower() == nl:
                return c
        return None

    # The plate->foot assignment must compare the CoP and the foot markers on the
    # SAME (medio-lateral) axis. In the OpenSim GRF frame Y is VERTICAL, so CoP-Y
    # is ~0 at the ground and cannot separate left from right — every plate then
    # collapses to the nearest foot. Use the lateral axis (BatchSettings.
    # trc_lateral_axis, default Z), matching how the foot markers are read below.
    _lateral = getattr(getattr(settings, 'BatchSettings', None),
                       'trc_lateral_axis', 'Z').upper()
    cop_y_per_plate = {}
    for pnum, ids in valid.items():
        fy_col = find_col(ids['force_id'] + 'y')                 # vertical force (active-plate test)
        py_col = find_col(ids['point_id'] + _lateral.lower())    # lateral CoP (L/R assignment)
        if fy_col is None or py_col is None:
            print(f"  Plate {pnum}: Fy or CoP-Y column missing — skipping")
            continue
        fy = pd.to_numeric(grf_df[fy_col], errors='coerce')
        py = pd.to_numeric(grf_df[py_col], errors='coerce')
        active = fy.abs() > vert_force_threshold
        if not active.any():
            print(f"  Plate {pnum}: no active frames (|Fy| > {vert_force_threshold} N) — skipping")
            continue
        cop_y_per_plate[pnum] = float(py[active].median())

    if not cop_y_per_plate:
        print("  Warning: no active plates — returning empty assignment")
        return {}

    # ------------------------------------------------------------------ #
    # 3. Auto-detect CoP units  (metres → mm)
    # ------------------------------------------------------------------ #
    max_cop = max(abs(v) for v in cop_y_per_plate.values())
    if max_cop < 10.0:
        cop_y_per_plate = {k: v * 1000.0 for k, v in cop_y_per_plate.items()}
        print(f"  CoP units: metres detected → converted to mm")
    else:
        print(f"  CoP units: mm (max |CoP Y| = {max_cop:.1f} mm)")

    for pnum, cy in sorted(cop_y_per_plate.items(), key=lambda x: int(x[0])):
        print(f"  Plate {pnum}: median CoP Y = {cy:.1f} mm")

    # ------------------------------------------------------------------ #
    # 4. Mean foot-marker lateral position from TRC  (mm)
    # ------------------------------------------------------------------ #
    # Which TRC axis separates left from right foot comes from settings.
    # After exportC3D (OpenSim frame) this is Z; in raw lab frame it is X.
    _lateral = getattr(
        getattr(settings, 'BatchSettings', None), 'trc_lateral_axis', 'Z'
    ).upper()

    r_foot_y = None
    l_foot_y = None

    if marker_trc_path and os.path.exists(str(marker_trc_path)):
        try:
            trc_df = utils.load_trc(marker_trc_path)

            # Flatten MultiIndex → "MARKER_COORD" lookup.
            # TRC sub-headers are "X1","Y1","Z1" (numbered) so use
            # startswith — e.g. "RHEE_Z" matches "RHEE_Z1", "RHEE_Z2", etc.
            if isinstance(trc_df.columns, pd.MultiIndex):
                _pairs = [(f"{str(m).upper()}_{str(c).upper()}", (m, c))
                          for m, c in trc_df.columns]
                def get_y(name):
                    prefix = f"{name.upper()}_{_lateral}"
                    for _k, _col in _pairs:
                        if _k == prefix or _k.startswith(prefix):
                            return pd.to_numeric(trc_df[_col], errors='coerce').dropna()
                    return pd.Series(dtype=float)
            else:
                _flat_cols = [(str(c).upper(), c) for c in trc_df.columns]
                def get_y(name):
                    prefix = f"{name.upper()}_{_lateral}"
                    for _k, _col in _flat_cols:
                        if _k == prefix or _k.startswith(prefix):
                            return pd.to_numeric(trc_df[_col], errors='coerce').dropna()
                    return pd.Series(dtype=float)

            def mean_foot_y(names, label):
                vals, found = [], []
                for n in names:
                    s = get_y(n)
                    if not s.empty:
                        vals.append(float(s.mean()))
                        found.append(n)
                if vals:
                    print(f"  {label} markers found: {found}  →  mean Y = {np.mean(vals):.1f} mm")
                    return float(np.mean(vals))
                print(f"  {label} markers not found in TRC")
                return None

            r_foot_y = mean_foot_y(right_markers, 'Right foot')
            l_foot_y = mean_foot_y(left_markers,  'Left  foot')

        except Exception as exc:
            print(f"  Warning: could not load TRC — {exc}")

    # ------------------------------------------------------------------ #
    # 5. Assign each plate to a foot
    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    # 5. TEMPORAL, horizontal-plane assignment.
    #    For each plate, over ONLY the frames it is loaded, pick the foot whose
    #    markers are closest to the CoP in the (X,Z) horizontal plane (Y is
    #    vertical in the OpenSim GRF frame). Robust to walkway orientation and
    #    straight-line walking — does NOT use session-mean foot positions.
    # ------------------------------------------------------------------ #
    _tcol = find_col('time')
    _gt = pd.to_numeric(grf_df[_tcol], errors='coerce').values if _tcol is not None else None

    _trc = None
    if marker_trc_path and os.path.exists(str(marker_trc_path)):
        try:
            _trc = utils.load_trc(marker_trc_path)
        except Exception as _e:
            print(f"  Warning: could not load TRC for assignment — {_e}")

    def _series(pref):
        """First TRC column whose flattened NAME_AXIS starts with pref (upper)."""
        if _trc is None:
            return None
        if isinstance(_trc.columns, pd.MultiIndex):
            for m, c in _trc.columns:
                if f"{str(m).upper()}_{str(c).upper()}".startswith(pref):
                    return pd.to_numeric(_trc[(m, c)], errors='coerce').values
        else:
            for c in _trc.columns:
                if str(c).upper().startswith(pref):
                    return pd.to_numeric(_trc[c], errors='coerce').values
        return None

    _tt = _series("TIME")

    def _foot_xz(markers, t0, t1):
        xs, zs = [], []
        for m in markers:
            for axis, acc in (('X', xs), ('Z', zs)):
                v = _series(f"{m.upper()}_{axis}")
                if v is None:
                    continue
                if _tt is not None and np.isfinite(_tt).any():
                    sel = (_tt >= t0) & (_tt <= t1) & np.isfinite(v)
                    if sel.any():
                        acc.append(float(np.nanmedian(v[sel])))
                        continue
                acc.append(float(np.nanmedian(v)))
        return (float(np.mean(xs)) if xs else None,
                float(np.mean(zs)) if zs else None)

    # A plate whose CoP sits farther than this (mm) from BOTH foot-marker centroids
    # is not acting on a foot (e.g. a loaded barbell resting on a plate during a
    # deadlift) and is dropped so it never enters GRF.xml. None/0 disables the check.
    if max_cop_foot_dist_mm is None:
        max_cop_foot_dist_mm = getattr(getattr(settings, 'BatchSettings', None),
                                       'grf_max_cop_foot_dist_mm', 300.0)

    plate_to_body = {}
    print("  Assignment (temporal CoP<->foot distance, horizontal plane):")
    for pnum in sorted(valid.keys(), key=int):
        ids = valid[pnum]
        fy = pd.to_numeric(grf_df[find_col(ids['force_id'] + 'y')], errors='coerce').values
        pxc = find_col(ids['point_id'] + 'x')
        pzc = find_col(ids['point_id'] + 'z')
        active = np.abs(fy) > vert_force_threshold
        if not active.any():
            # Empty/unused plate (never loaded above threshold) — EXCLUDE entirely.
            # Do NOT parity-assign it to a foot: an ExternalForce with ~0 N and an
            # undefined CoP (M/Fz -> 0/0) pollutes ID/JRA with a phantom load.
            print(f"    Plate {pnum}: no active frames (|Fy| <= {vert_force_threshold:.0f} N) "
                  f"— EXCLUDED (empty plate)")
            continue
        if pxc is None or pzc is None:
            body = right_foot_body if int(pnum) % 2 == 1 else left_foot_body
            plate_to_body[pnum] = body
            print(f"    Plate {pnum}: active but no CoP columns -> parity fallback {body}")
            continue
        px = pd.to_numeric(grf_df[pxc], errors='coerce').values
        pz = pd.to_numeric(grf_df[pzc], errors='coerce').values
        cx = float(np.nanmedian(px[active]))
        cz = float(np.nanmedian(pz[active]))
        if max(abs(cx), abs(cz)) < 10.0:          # metres -> mm (match TRC)
            cx *= 1000.0; cz *= 1000.0
        if _gt is not None:
            ta = _gt[active]
            t0, t1 = float(np.nanmin(ta)), float(np.nanmax(ta))
        else:
            t0, t1 = -np.inf, np.inf
        rx, rz = _foot_xz(right_markers, t0, t1)
        lx, lz = _foot_xz(left_markers, t0, t1)
        # FAIS patch 2026-08-12: decide LEFT/RIGHT on the LATERAL axis ALONE.
        # The CoP sits mid-foot, ~150 mm forward of the heel marker, so the
        # progression-axis error is systematically LARGER than the real left/right
        # separation (~50-100 mm). Scoring on the horizontal plane let that offset
        # dominate and collapsed every plate onto one foot: Run_baselineA1 put all
        # three plates on calcn_l, so the right leg had kinematics but no GRF and
        # therefore no ankle moment. The horizontal distance is still used, but
        # only for the "is this a foot at all" gate below.
        _lat = getattr(getattr(settings, 'BatchSettings', None),
                       'trc_lateral_axis', 'Z').upper()
        _c_lat, _r_lat, _l_lat = ((cx, rx, lx) if _lat == 'X' else (cz, rz, lz))
        dR = abs(_c_lat - _r_lat) if _r_lat is not None else np.inf
        dL = abs(_c_lat - _l_lat) if _l_lat is not None else np.inf
        _hR = np.hypot(cx - rx, cz - rz) if rx is not None else np.inf
        _hL = np.hypot(cx - lx, cz - lz) if lx is not None else np.inf
        print(f"    Plate {pnum}: lateral({_lat}) CoP={_c_lat:.0f} "
              f"R={_r_lat if _r_lat is None else round(_r_lat)} "
              f"L={_l_lat if _l_lat is None else round(_l_lat)} "
              f"-> dR={dR:.0f} dL={dL:.0f} mm")
        if not np.isfinite(dR) and not np.isfinite(dL):
            body = right_foot_body if int(pnum) % 2 == 1 else left_foot_body
        else:
            body = right_foot_body if dR <= dL else left_foot_body
        # Reject plates whose CoP is too far from BOTH foot centroids — not on a
        # foot (e.g. a loaded barbell on the plate). Excluded from GRF.xml.
        _dmin = min([d for d in (dR, dL) if np.isfinite(d)], default=np.inf)
        if max_cop_foot_dist_mm and np.isfinite(_dmin) and _dmin > float(max_cop_foot_dist_mm):
            print(f"    Plate {pnum}: CoP=({cx:.0f},{cz:.0f})  dR={dR:.0f}  dL={dL:.0f}  "
                  f"-> nearest foot {_dmin:.0f} mm > {float(max_cop_foot_dist_mm):.0f} mm "
                  f"threshold — NOT on a foot; EXCLUDED")
            continue
        side = 'R' if body == right_foot_body else 'L'
        plate_to_body[pnum] = body
        print(f"    Plate {pnum}: CoP=({cx:.0f},{cz:.0f})  dR={dR:.0f}  dL={dL:.0f}  ->  {side} ({body})")

    return plate_to_body

def create_grf_xml(grf_mot_path=None, output_xml_path=None,
                   marker_trc_path=None,
                   right_foot_markers=None, left_foot_markers=None,
                   right_foot_body='calcn_r', left_foot_body='calcn_l',
                   vert_force_threshold=10.0,
                   max_cop_foot_dist_mm=None,
                   filter_cutoff=6,
                   datafile=None):
    """
    Create a working OpenSim ExternalLoads XML (GRF.xml) from a GRF .mot file.

    Automatically detects force-plate column names, assigns each plate to the
    left or right foot using marker TRC data or COP Z-position heuristic, and
    writes a correctly-formatted GRF.xml.

    Parameters
    ----------
    grf_mot_path : str
        Path to the GRF .mot file containing force plate data.
    output_xml_path : str, optional
        Output XML path. Defaults to GRF.xml next to the .mot file.
    marker_trc_path : str, optional
        Marker TRC file used to assign plates to feet by comparing COP
        positions to foot marker Z-positions.
    right_foot_markers : list of str, optional
        Marker names for the right foot (e.g. ['RHEE', 'RTOE']).
        If None, common names are tried automatically.
    left_foot_markers : list of str, optional
        Marker names for the left foot (e.g. ['LHEE', 'LTOE']).
        If None, common names are tried automatically.
    right_foot_body : str
        OpenSim body for the right foot (default 'calcn_r').
    left_foot_body : str
        OpenSim body for the left foot (default 'calcn_l').
    vert_force_threshold : float
        Minimum vertical force (N) to consider a plate active (default 10.0).
    filter_cutoff : float
        Low-pass filter cut-off for load kinematics in the XML (default 6 Hz).
    datafile : str, optional
        Value for the <datafile> tag. Defaults to the basename of grf_mot_path.
    """
    import re
    import xml.etree.ElementTree as ET

    if not os.path.exists(grf_mot_path):
        raise FileNotFoundError(f"GRF .mot file not found: {grf_mot_path}")

    if output_xml_path is None:
        output_xml_path = os.path.join(os.path.dirname(grf_mot_path), 'GRF.xml')

    if datafile is None:
        datafile = os.path.basename(grf_mot_path)

    # ------------------------------------------------------------------ #
    # 1. Load .mot and detect column name patterns per force plate
    # ------------------------------------------------------------------ #
    grf_df = utils.load_sto(grf_mot_path)
    cols = grf_df.columns.tolist()

    # plates[plate_number] = {'force_id': ..., 'point_id': ..., 'torque_id': ...}
    plates = {}

    for col in cols:
        if col.lower() == 'time':
            continue

        # Force columns: end in vx/vy/vz (e.g. ground_force3_vx)
        if re.search(r'vx$', col, re.IGNORECASE) and 'force' in col.lower():
            identifier = col[:-1]   # strip trailing 'x' → e.g. 'ground_force3_v'
            nums = re.findall(r'\d+', col)
            if nums:
                plates.setdefault(nums[0], {})['force_id'] = identifier
            continue

        # Point columns: end in px/py/pz (e.g. ground_force3_px)
        if re.search(r'px$', col, re.IGNORECASE) and 'force' in col.lower():
            identifier = col[:-1]   # → e.g. 'ground_force3_p'
            nums = re.findall(r'\d+', col)
            if nums:
                plates.setdefault(nums[0], {})['point_id'] = identifier
            continue

        # Torque columns: contain 'torque' and end in x (e.g. ground_torque3_x or ground_torque3_mx)
        if re.search(r'x$', col, re.IGNORECASE) and 'torque' in col.lower():
            identifier = col[:-1]   # → e.g. 'ground_torque3_' or 'ground_torque3_m'
            nums = re.findall(r'\d+', col)
            if nums:
                plates.setdefault(nums[0], {})['torque_id'] = identifier

    if not plates:
        raise ValueError("No force plate columns detected in the .mot file. "
                         "Expected columns like 'ground_force1_vx', 'ground_force1_px', etc.")

    print(f"Detected force plates: {sorted(plates.keys(), key=lambda x: int(x))}")
    for n, ids in sorted(plates.items(), key=lambda x: int(x[0])):
        print(f"  Plate {n}: force_id='{ids.get('force_id','')}', "
              f"point_id='{ids.get('point_id','')}', torque_id='{ids.get('torque_id','')}'")

    # ------------------------------------------------------------------ #
    # 2. Assign each plate to a foot
    # ------------------------------------------------------------------ #
    print("\nAssigning force plates to feet...")
    plate_to_body = assign_grfs_to_feet(
        grf_mot_path=grf_mot_path,
        marker_trc_path=marker_trc_path,
        right_foot_markers=right_foot_markers,
        left_foot_markers=left_foot_markers,
        right_foot_body=right_foot_body,
        left_foot_body=left_foot_body,
        vert_force_threshold=vert_force_threshold,
        max_cop_foot_dist_mm=max_cop_foot_dist_mm,
    )

    # ------------------------------------------------------------------ #
    # 3. Build XML tree
    # ------------------------------------------------------------------ #
    root = ET.Element('OpenSimDocument')
    root.set('Version', '40000')

    ext_loads = ET.SubElement(root, 'ExternalLoads')
    ext_loads.set('name', 'externalloads')
    objects_el = ET.SubElement(ext_loads, 'objects')

    for plate_num in sorted(plates.keys(), key=lambda x: int(x)):
        ids = plates[plate_num]
        if 'force_id' not in ids or 'point_id' not in ids:
            continue

        # Only include plates that are actually in plate_to_body (have significant force data)
        if plate_num not in plate_to_body:
            continue

        body = plate_to_body[plate_num]
        side = 'r' if body == right_foot_body else 'l'
        force_name = f'grf_{side}_{plate_num}'

        ef = ET.SubElement(objects_el, 'ExternalForce')
        ef.set('name', force_name)
        ET.SubElement(ef, 'applied_to_body').text          = body
        ET.SubElement(ef, 'force_expressed_in_body').text  = 'ground'
        ET.SubElement(ef, 'point_expressed_in_body').text  = 'ground'
        ET.SubElement(ef, 'force_identifier').text         = ids['force_id']
        ET.SubElement(ef, 'point_identifier').text         = ids['point_id']
        ET.SubElement(ef, 'torque_identifier').text        = ids.get('torque_id', '')
        ET.SubElement(ef, 'data_source_name').text         = ''

    ET.SubElement(ext_loads, 'groups')
    ET.SubElement(ext_loads, 'datafile').text = datafile
    ET.SubElement(ext_loads, 'external_loads_model_kinematics_file').text = ''
    ET.SubElement(ext_loads, 'lowpass_cutoff_frequency_for_load_kinematics').text = str(filter_cutoff)

    # ------------------------------------------------------------------ #
    # 4. Save using utils pretty-printer
    # ------------------------------------------------------------------ #
    tree = ET.ElementTree(root)
    utils.save_pretty_xml(tree, output_xml_path)

    print(f"\nGRF XML saved to: {os.path.abspath(output_xml_path)}")
    print(f"Plates: {sorted(plates.keys(), key=lambda x: int(x))}  |  Data file: {datafile}")
    return os.path.abspath(output_xml_path)

def convert_mot_to_sto(mot_file_path = None):
    """
    Convert a .mot file to a .sto file.
    """
    if not mot_file_path:
        mot_file_path = input("Enter path to .mot file: ").strip('"')
    
    sto_file_path = mot_file_path.replace('.mot', '.sto')
    
    if not os.path.exists(mot_file_path):
        print(f".mot file not found: {mot_file_path}")
        return

    if os.path.exists(sto_file_path):
        print(f".sto file already exists: {sto_file_path}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        sto_file_path = mot_file_path.replace('.mot', f'_{timestamp}.sto')
    
    mot_data = utils.load_any_data_file(mot_file_path)
    utils.write_sto_file(mot_data, sto_file_path)
    
    print(f"Converted {mot_file_path} to {sto_file_path}")

    return sto_file_path

# --- Inverse Kinematics ---
def create_setup_IK(osim_modelPath=None, marker_trc=None,
                    ik_output=None, taskSetPath=None, time_range=None,
                    saveXMLPath=None):
    """
    Create an Inverse Kinematics (IK) setup XML file for OpenSim.
    """
    if not osim_modelPath:
        raise ValueError("create_setup_IK: osim_modelPath is required")

    if not marker_trc:
        raise ValueError("create_setup_IK: marker_trc is required")
        
    if not os.path.exists(osim_modelPath):
        print(f"OpenSim model file not found: {osim_modelPath}")
        return
    
    # Load the model
    model = _quiet_model(osim_modelPath)
    
    # Load markers
    markers = osim.Storage(marker_trc)

    # Create the Inverse Kinematics tool
    ikTool = osim.InverseKinematicsTool()
    
    if taskSetPath:
        ikTaskSet_template = osim.IKTaskSet(taskSetPath) 
        ikTool.set_IKTaskSet(ikTaskSet_template)    
    
    # simple function to validate the markers used in the IK setup
    ikTool = validate_markers_used(osim_modelPath, ikTool, marker_trc)

    # Set the model and parameters
    ikTool.setModel(model)

    # Use relative path for model file for portability
    if saveXMLPath:
        setup_dir = os.path.dirname(saveXMLPath)
        relative_model_path = os.path.relpath(osim_modelPath, setup_dir)
        ikTool.set_model_file(relative_model_path)
    else:
        ikTool.set_model_file(osim_modelPath)

    # Set the marker data file and time range
    ikTool.setMarkerDataFileName(marker_trc)
    ikTool.set_report_marker_locations(True)
    ikTool.set_report_errors(True)

    # # check time range is valid and set it
    print(f"Input time_range: {time_range}")
    print(f"Marker data time range: [{markers.getFirstTime()}, {markers.getLastTime()}]")

    if time_range is not None:
        try:
            # Handle different time_range formats
            if isinstance(time_range, str):
                # Parse string format like "[0.0, 1.5]" or "np.float64(0.0), np.float64(1.5)"
                cleaned = time_range.strip('[]').replace('np.float64(', '').replace(')', '')
                parts = cleaned.split(',')
                time_range = [float(p.strip()) for p in parts]
            elif isinstance(time_range, (list, tuple)):
                time_range = [float(t) for t in time_range]
            else:
                time_range = None

            if time_range and len(time_range) >= 2:
                print(f"Parsed time_range: [{time_range[0]}, {time_range[1]}]")
                if time_range[0] < markers.getFirstTime() or time_range[1] > markers.getLastTime():
                    print("Warning: Specified time range is outside the bounds of the marker data. Using full range instead.")
                    time_range = [markers.getFirstTime(), markers.getLastTime()]

                ikTool.setStartTime(float(time_range[0]))  # Set start time
                ikTool.setEndTime(float(time_range[1]))    # Set end time
                print(f"IK time range set to: [{time_range[0]}, {time_range[1]}]")
            else:
                time_range = None
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error parsing time_range: {e}. Using full range instead.")
            time_range = None

    if time_range is None:
        print(f"Using full marker data time range for IK")
        ikTool.setStartTime(markers.getFirstTime())  # Default start time
        ikTool.setEndTime(markers.getLastTime())    # Default end time
    
    # Set the output motion file name relative to the results directory.
    #
    # setResultsDir('./') meant the PROCESS CWD, not the trial folder, and
    # set_report_errors(True) above makes OpenSim write `_ik_marker_errors.sto`
    # and `_ik_model_marker_locations.sto` into that results dir. Run from a
    # project root (as settings.py is) and those land in the repo root, are
    # rewritten by every trial, and `Analyse.calculate_mean_marker_error`
    # then reads whichever one happened to be last -- for the wrong trial.
    # Point it at the trial's own folder.
    resultsDir = os.path.dirname(os.path.abspath(ik_output))
    os.makedirs(resultsDir, exist_ok=True)
    ikTool.setResultsDir(resultsDir)
    ikTool.setOutputMotionFileName(os.path.relpath(ik_output, resultsDir))
    if saveXMLPath is None:
        saveXMLPath = ik_output.replace('.mot', '_ik_setup.xml')
    ikTool.printToXML(saveXMLPath)
    print(f"Inverse Kinematics setup saved to {os.path.abspath(saveXMLPath)}")

@_quiet_console
def run_ik(osim_modelPath=None, setup_xml=None, resultsDir=None):
    print(f"DEBUG: run_ik() called with osim_modelPath={osim_modelPath}, setup_xml={setup_xml}, resultsDir={resultsDir}")
    utils.print_to_log(f"DEBUG: run_ik() called with osim_modelPath={osim_modelPath}, setup_xml={setup_xml}, resultsDir={resultsDir}")

    if osim_modelPath is None:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')
    if setup_xml is None:
        setup_xml = input("Enter the path to save the IK setup XML file (.xml): ").strip('"')

    # Determine results directory
    if resultsDir is None:
        resultsDir = os.path.dirname(os.path.abspath(setup_xml))

    resultsDir = os.path.abspath(resultsDir)
    original_cwd = os.getcwd()
    print(f"DEBUG: resultsDir={resultsDir}, original_cwd={original_cwd}")
    utils.print_to_log(f"DEBUG: resultsDir={resultsDir}, original_cwd={original_cwd}")

    try:
        # Pre-flight checks
        print(f"[IK] Performing pre-flight checks...")
        _check_ik_prerequisites(osim_modelPath, setup_xml, resultsDir)

        # Change to the results directory to ensure output files are created in the correct location
        os.chdir(resultsDir)
        print(f"Changed working directory to: {resultsDir}")
        utils.print_to_log(f"Changed working directory to: {resultsDir}")

        # Load the model
        print(f"Loading model from {osim_modelPath}")
        model = _quiet_model(osim_modelPath)

        # Initialize the system before disabling analyses
        model.initSystem()
        print(f"Model initialized")

        # Disable all analyses to avoid "null upcall object" errors
        analysisSet = model.getAnalysisSet()
        print(f"Number of analyses in model: {analysisSet.getSize()}")
        for i in range(analysisSet.getSize()):
            try:
                analysis = analysisSet.get(i)
                analysis.setEnabled(False)
                print(f"Disabled analysis {i}: {analysis.getName()}")
            except Exception as e:
                print(f"Error disabling analysis {i}: {e}")

        # Finalize the model after modifying analyses
        try:
            model.finalizeConnections()
            print("Model connections finalized")
        except Exception as e:
            print(f"Warning: Error finalizing connections: {e}")

        # Reload tool from xml
        print(f"Loading IK tool from {setup_xml}")
        ikTool = osim.InverseKinematicsTool(setup_xml)
        ikTool.setModel(model)

        # --- NaN interpolation: fill missing marker data before IK ---
        # Gaps in the TRC can make AssemblySolver return -nan and crash. We fill
        # them by linear interpolation, but the TRC format MUST be preserved
        # exactly: a .trc has a fixed 5-line header where line 3 is the numeric
        # DataRate row and line 4 ("Frame#  Time  ...") + line 5 (X1 Y1 Z1 ...)
        # are the column headers. Data begins on line 6. We anchor on the
        # 'Frame#' row, interpolate only the numeric data block, keep the header
        # verbatim, and restore the original file on any error.
        try:
            import xml.etree.ElementTree as _ET
            import numpy as _np
            _tree = _ET.parse(setup_xml)
            _mf = _tree.getroot().findtext('.//marker_file') or ''
            if _mf and not os.path.isabs(_mf):
                _mf = os.path.join(resultsDir, _mf)
            if _mf and os.path.isfile(_mf):
                _orig = open(_mf, 'r').read()
                try:
                    _lines = _orig.splitlines(keepends=True)
                    # Locate the 'Frame#' column-header row; data starts 2 lines
                    # below it (after the X1/Y1/Z1 axis-label row).
                    _fr = next((i for i, l in enumerate(_lines)
                                if l.lstrip().lower().startswith('frame#')), None)
                    if _fr is not None and _fr + 2 < len(_lines):
                        _hdr = _lines[:_fr + 2]
                        _data = [l for l in _lines[_fr + 2:] if l.strip()]
                        _rows = []
                        for _l in _data:
                            _cells = _l.rstrip('\r\n').split('\t')
                            _rows.append([
                                float(_c) if _c.strip() not in ('', 'nan', 'NaN')
                                else _np.nan for _c in _cells])
                        _w = max(len(r) for r in _rows)
                        _A = _np.full((len(_rows), _w), _np.nan)
                        for _i, _r in enumerate(_rows):
                            _A[_i, :len(_r)] = _r
                        # Columns 0,1 are Frame# and Time; only fill SHORT
                        # interior gaps in the marker columns (2..end). Long gaps,
                        # leading/trailing gaps, and fully-missing markers are left
                        # EMPTY so OpenSim treats them as 'marker absent' and skips
                        # them — filling those (e.g. with 0,0,0 or a long straight
                        # line) plants markers far from the body and makes IK
                        # diverge / fail.
                        # Fill what can be filled, honestly.
                        #
                        # This used to be a straight-line interpolation over
                        # gaps of up to 20 frames and nothing else. It reported
                        # "Filled 0 of 178168" on 022's running trials and moved
                        # on, and IK then solved a pelvis that was unobserved
                        # for a third of the window — which OpenSim does not
                        # complain about, because a marker it cannot see costs
                        # it nothing. bioscout.simulate.gapfill does the two things
                        # that actually work: spline through short gaps, and
                        # reconstruct longer ones from the other markers on the
                        # same segment, refusing when it cannot do so to a
                        # measured tolerance. What it refuses stays empty.
                        _nan_count = int(_np.isnan(_A[:, 2:]).sum())
                        if _nan_count > 0:
                            from bioscout.simulate import gapfill as _gf
                            _nmk = (_w - 2) // 3
                            _cube = _A[:, 2:2 + 3 * _nmk].reshape(len(_rows), _nmk, 3)
                            try:
                                _names = [c.strip() for c in
                                          _lines[_fr].rstrip('\r\n').split('\t')[2:]
                                          if c.strip()][:_nmk]
                            except Exception:
                                _names = None
                            _filledA, _rep = _gf.fill_array(_cube, _names)
                            _rep.path = _mf
                            for _ln in _gf.format_report(_rep).splitlines():
                                print(f"[IK] {_ln}")
                            _A[:, 2:2 + 3 * _nmk] = _filledA.reshape(len(_rows), -1)
                            # Say what is still solvable. A window that keeps
                            # frames nothing constrains is a window that will
                            # produce kinematics nobody should trust, and this
                            # is the last moment anyone is looking.
                            try:
                                _s0, _e0, _L0, _why0 = _gf.usable_window(_filledA, _names)
                                _tcol = _A[:, 1]
                                if _L0 and _L0 < 0.95 * len(_rows):
                                    print(f"[IK] {_why0}")
                                    print(f"[IK] markers support at most "
                                          f"time_range: [{_tcol[_s0]:.3f}, "
                                          f"{_tcol[_e0 - 1]:.3f}] "
                                          f"({_tcol[_e0 - 1] - _tcol[_s0]:.3f} s) — "
                                          f"solving wider than this fits a pose "
                                          f"nothing observed.")
                            except Exception:
                                pass
                            _out = list(_hdr)
                            for _i in range(_A.shape[0]):
                                _v = _A[_i]
                                _frame = int(round(_v[0])) if not _np.isnan(_v[0]) else _i + 1
                                _cells = [str(_frame)] + [
                                    ("" if _np.isnan(_x) else f"{_x:.5f}") for _x in _v[1:]]
                                _out.append('\t'.join(_cells) + '\n')
                            with open(_mf, 'w', newline='') as _f:
                                _f.writelines(_out)
                            print(f"[IK] TRC gap-fill complete → {_mf}")
                except Exception as _ie:
                    # Any problem → put the original TRC back so IK still runs.
                    with open(_mf, 'w', newline='') as _f:
                        _f.write(_orig)
                    print(f"[IK] NaN interpolation skipped, original TRC restored ({_ie})")
        except Exception as _nan_e:
            print(f"[IK] Warning: NaN interpolation step failed (continuing): {_nan_e}")

        # Setup XML now lives in a subfolder (external_biomechanics/). OpenSim
        # resolves relative <marker_file>/<output_motion_file> in a deserialized
        # tool against the SETUP FILE's directory, not the cwd — so trial-root-
        # relative paths (e.g. inputs\marker_experimental.trc) break. Force them
        # absolute on the tool so the subfoldered layout works.
        try:
            import xml.etree.ElementTree as _ET2
            _setup_dir = os.path.dirname(os.path.abspath(setup_xml))
            _r2 = _ET2.parse(setup_xml).getroot()
            _mk = _r2.findtext('.//marker_file') or ''
            _om = _r2.findtext('.//output_motion_file') or ''
            # marker_file is written trial-root-relative; resolve to wherever the
            # file actually exists (trial root, else next to the setup).
            if _mk and not os.path.isabs(_mk):
                _cands = [os.path.abspath(os.path.join(resultsDir, _mk)),
                          os.path.abspath(os.path.join(_setup_dir, _mk))]
                _mk_abs = next((c for c in _cands if os.path.isfile(c)), _cands[0])
            else:
                _mk_abs = _mk
            # output_motion_file is written relative to the setup file's own dir
            # (OpenSim convention), i.e. it belongs NEXT TO setup_IK.xml.
            _om_abs = _om if (not _om or os.path.isabs(_om)) else \
                os.path.abspath(os.path.join(_setup_dir, _om))
            if _mk:
                try:    ikTool.set_marker_file(_mk_abs)
                except Exception: ikTool.setMarkerDataFileName(_mk_abs)
            if _om:
                os.makedirs(os.path.dirname(_om_abs), exist_ok=True)
                try:    ikTool.set_output_motion_file(_om_abs)
                except Exception: ikTool.setOutputMotionFileName(_om_abs)
            print(f"[IK] marker_file={_mk_abs}\n[IK] output_motion_file={_om_abs}")
        except Exception as _abs_e:
            print(f"[IK] Warning: could not set absolute tool paths ({_abs_e})")

        # Run the inverse kinematics calculation. The TOOL loads its own
        # model from the setup XML, so _quiet_model() upstream cannot reach
        # that copy's printBasicInfo — only the fd-level context can.
        with _osim_quiet_ctx():
            ikTool.run()
        utils.print_to_log(f"Inverse Kinematics calculation completed. Results saved to {resultsDir}")
        print(f"Inverse Kinematics calculation completed successfully")
        # Cold-start repair: the FIRST solved frame starts from the model's
        # default pose and can converge to a folded mirror solution (pelvis
        # ~90 deg off) that the warm-started frames never revisit. ID then
        # differentiates that single frame into multi-kNm pelvis moments.
        # Replace leading frames that sit far from the trial median with the
        # first good frame.
        try:
            _sanitize_ik_leading_frames(_om_abs)
        except Exception as _se:
            print(f"[IK] leading-frame check skipped: {_se}")

    except Exception as e:
        utils.print_to_log(f"Error running IK: {e}")
        print(f"Error running IK: {e}")
        # OpenSim writes the real failure detail to opensim.log (in cwd); surface
        # the tail so the actual cause is visible instead of the generic message.
        try:
            for _logp in ('opensim.log', os.path.join(resultsDir, 'opensim.log')):
                if os.path.isfile(_logp):
                    _tail = open(_logp, 'r', errors='replace').read().splitlines()[-25:]
                    print("----- opensim.log (last 25 lines) -----")
                    print("\n".join(_tail))
                    print("---------------------------------------")
                    break
        except Exception:
            pass
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Always restore original working directory
        try:
            os.chdir(original_cwd)
            print(f"Restored working directory to: {original_cwd}")
        except Exception as e:
            print(f"Warning: Could not restore original working directory: {e}")

def _sanitize_ik_leading_frames(mot_path, max_lead=5, tol_deg=30.0):
    """Replace up to `max_lead` leading frames whose pelvis orientation is more
    than `tol_deg` from the trial median (IK cold-start fold) with the first
    good frame's values. In-place; no-op when the file starts clean."""
    import numpy as _np
    lines = open(mot_path, errors="replace").read().splitlines()
    h = max(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    cols = lines[h + 1].split()
    body = [l for l in lines[h + 2:] if l.strip()]
    d = _np.array([[float(x) for x in l.split()] for l in body])
    idx = [cols.index(c) for c in ("pelvis_tilt", "pelvis_list", "pelvis_rotation")
           if c in cols]
    if not idx or len(d) < max_lead + 2:
        return
    med = _np.median(d[:, idx], axis=0)
    bad = _np.abs(d[:, idx] - med).max(axis=1) > tol_deg
    n = 0
    while n < min(max_lead, len(d) - 1) and bad[n]:
        n += 1
    if n == 0:
        return
    good = d[n].copy()
    for k in range(n):
        t = d[k, 0]
        d[k] = good
        d[k, 0] = t
    fmt = "\t".join(["%12.8f"] * d.shape[1])
    out = lines[:h + 2] + [fmt % tuple(r) for r in d]
    open(mot_path, "w").write("\n".join(out) + "\n")
    print(f"[IK] cold-start repair: replaced {n} leading frame(s) with the "
          f"first good frame (pelvis was >{tol_deg:.0f} deg off the trial median)")

def _check_ik_prerequisites(osim_modelPath, setup_xml, resultsDir):
    """
    Pre-flight checks for IK: verify all required files exist.
    Raises detailed error messages if issues are found.
    """
    errors = []

    # Check model file
    if not os.path.isfile(osim_modelPath):
        errors.append(f"Model file not found: {osim_modelPath}")

    # Check setup XML file
    if not os.path.isfile(setup_xml):
        errors.append(f"IK setup XML not found: {setup_xml}")
    else:
        # Parse setup XML to find required input files
        try:
            tree = ET.parse(setup_xml)
            root = tree.getroot()

            # Find the IK tool element (usually the root or a child)
            ik_tool = root.find('.//InverseKinematicsTool') or root

            # Get the marker data file
            marker_file_elem = ik_tool.find('.//marker_file') or ik_tool.find('.//MarkerFile')
            if marker_file_elem is not None and marker_file_elem.text:
                marker_file = marker_file_elem.text.strip()
                # Resolve relative paths
                if not os.path.isabs(marker_file):
                    marker_file = os.path.join(resultsDir, marker_file)

                if not os.path.isfile(marker_file):
                    errors.append(f"Marker file (TRC) not found: {marker_file}")
                else:
                    print(f"[IK] ✓ Marker file found: {marker_file}")

            # Get the coordinate file (IK output)
            coord_file_elem = ik_tool.find('.//output_motion_file') or ik_tool.find('.//OutputMotionFile')
            if coord_file_elem is not None and coord_file_elem.text:
                coord_file = coord_file_elem.text.strip()
                print(f"[IK] ✓ Output will be saved to: {os.path.join(resultsDir, coord_file)}")

        except Exception as e:
            errors.append(f"Error parsing IK setup XML: {e}")

    # Check results directory
    if not os.path.isdir(resultsDir):
        errors.append(f"Results directory not found: {resultsDir}")

    if errors:
        error_msg = "IK Pre-flight Check Failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise RuntimeError(error_msg)

# --- Muscle Analysis ---
def find_non_zero_mom_arm_muscles(ma_data: pd.DataFrame, muscles: list) -> list:
    '''
    Find the muscles that have non-zero moment arms in the given data.
    '''
    
    non_zero_muscles = []
    for muscle in muscles:
        if ma_data is None:
            continue
        if muscle not in ma_data.columns:
            continue
        if ma_data[muscle].abs().sum() > 0:
            non_zero_muscles.append(muscle)
    return non_zero_muscles

def relativise_setup_xml(xml_path):
    """Rewrite absolute filesystem paths in an OpenSim/CEINMS setup XML to paths
    RELATIVE to the setup file's own directory, so the setup is portable (OpenSim
    resolves relative paths against the setup dir). Only rewrites values that look
    like absolute paths (drive-letter, UNC, or POSIX-absolute); everything else is
    left untouched. Best-effort — no-op on parse failure."""
    import xml.etree.ElementTree as _ET
    try:
        xml_path = os.path.abspath(xml_path)
        base = os.path.dirname(xml_path)
        tree = _ET.parse(xml_path)
        root = tree.getroot()
    except Exception:
        return
    def _is_abs(t):
        return len(t) > 2 and (t[1:3] in (":\\", ":/") or t.startswith(("/", "\\\\")))
    changed = False
    for el in root.iter():
        t = (el.text or "").strip()
        if not t or " " in t and not _is_abs(t):
            continue
        # a value may be a space-separated LIST of paths (e.g. force set files)
        parts = t.split()
        if parts and all(_is_abs(p) for p in parts):
            try:
                el.text = " ".join(os.path.relpath(p, base).replace("/", "\\") for p in parts)
                changed = True
            except Exception:
                pass
    if changed:
        try:
            tree.write(xml_path)
        except Exception:
            pass

def create_analysis_tool(marker_trc, externalloadsfile, osim_modelPath,
                         results_directory, actuators=None):
    """Creates and configures an OpenSim AnalyzeTool object.

    Args:
    coordinates_file: Path to the motion data file (e.g., .trc or .mot).
    model_path: Path to the OpenSim model file (.osim).
    results_directory: Path to the directory for storing results.
    force_set_files (optional): List of paths to actuator force set files.

    Returns:
    OpenSim AnalyzeTool object.

    # Example usage:
        coordinates_file = "your_motion_data.trc"
        model_path = "your_model.osim"
        results_directory = "analysis_results"
        force_set_files = ["actuator1_forces.xml", "actuator2_forces.xml"]  # Optional

        analysis_tool = create_analysis_tool(coordinates_file, model_path, results_directory, force_set_files)

        # Run the analysis
        analysis_tool.run()
    """

    # Load the motion data
    mot_data = osim.Storage(marker_trc)

    # Get initial and final time
    initial_time = mot_data.getFirstTime()
    final_time = mot_data.getLastTime()

    # Create and set model
    model = _quiet_model(osim_modelPath)
    analyze_tool = osim.AnalyzeTool()
    analyze_tool.setModel(model)

    # Set other parameters. Use ABSOLUTE paths: the setup XML may be saved in a
    # different subfolder than the coordinates/model, and OpenSim resolves
    # relative paths against the setup file's own dir — absolute sidesteps that.
    analyze_tool.setModelFilename(os.path.abspath(osim_modelPath))
    analyze_tool.setReplaceForceSet(False)

    # set results directory
    analyze_tool.setResultsDir(os.path.abspath(results_directory))
    analyze_tool.setOutputPrecision(8)

    # Set actuator force files (if provided)
    if actuators:
        force_set = osim.ArrayStr()
        for file in actuators:
            force_set.append(file)
        analyze_tool.setForceSetFiles(force_set)

    # Set initial and final time
    analyze_tool.setInitialTime(initial_time)
    analyze_tool.setFinalTime(final_time)

    # Set analysis parameters
    analyze_tool.setSolveForEquilibrium(False)
    analyze_tool.setMaximumNumberOfSteps(20000)
    analyze_tool.setMaxDT(1)
    analyze_tool.setMinDT(1e-8)
    analyze_tool.setErrorTolerance(1e-5)

    # Set external loads and coordinates files (absolute — see note above).
    analyze_tool.setExternalLoadsFileName(os.path.abspath(externalloadsfile))
    analyze_tool.setCoordinatesFileName(os.path.abspath(marker_trc))

    # Set filter cutoff frequency
    analyze_tool.setLowpassCutoffFrequency(6)


    # Return the analysis tool
    return analyze_tool

# --- Induced Acceleration Analysis ---
def create_iaa_tool(osim_modelPath=None, ik_output=None, grf_xml=None, setup_file_path=None, so_controls_file=None, actuators=None):
    """
    Create and configure an OpenSim Induced Acceleration Tool object.

    Args:
        osim_modelPath (str): Path to the OpenSim model file (.osim).
        ik_output (str): Path to the Inverse Kinematics output file (.mot).
        grf_xml (str): Path to the Ground Reaction Forces XML file (.xml).
        setup_file_path (str): Path to the Induced Acceleration setup XML file (.xml).
        so_controls_file (str, optional): Path to the Static Optimization controls file (.sto).

    Returns:
        OpenSim InducedAccelerationTool object.
    """

    if not osim_modelPath:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')

    if not ik_output:
        ik_output = input("Enter the path to the Inverse Kinematics output file (.mot): ").strip('"')

    if not grf_xml:
        grf_xml = input("Enter the path to the Ground Reaction Forces XML file (.xml): ").strip('"')

    if not setup_file_path:
        setup_file_path = os.path.join(os.path.dirname(os.path.abspath(ik_output)), 'setup_IAA.xml')

    if not so_controls_file:
        so_controls_file = input("Enter the path to the Static Optimization controls file (.sto): ").strip('"')

        activation_file = input("Enter the path to the Static Optimization activations file (.sto) (or press Enter to skip): ").strip('"')

    # Create and set model
    model = _quiet_model(osim_modelPath)
    tool = osim.AnalyzeTool(model)
    tool.setName("InducedAccelerations_Tool")
    tool.setModelFilename(osim_modelPath)

    # Load motion to get start/end times
    motion = osim.Storage(ik_output)
    initial_time = motion.getFirstTime()
    final_time = motion.getLastTime()

    # Set Tool Parameters
    tool.setInitialTime(initial_time)
    tool.setFinalTime(final_time)
    tool.setCoordinatesFileName(ik_output)
    tool.setExternalLoadsFileName(grf_xml)
    tool.setControlsFileName(so_controls_file)
    tool.setSolveForEquilibrium(True)
    tool.setLowpassCutoffFrequency(6.0) # Filter coordinates

    tool.setStatesFileName(activation_file)
    tool.setSolveForEquilibrium(False)
    
    # Set results directory relative to where the setup file will be, or absolute
    results_dir = os.path.join(os.path.dirname(setup_file_path), "IAA_Results")
    tool.setResultsDir(results_dir)

    # Set actuator force files (if provided)
    if actuators:
        force_set = osim.ArrayStr()
        for file in actuators:
            force_set.append(os.path.abspath(file))
        tool.setForceSetFiles(force_set)
        tool.setReplaceForceSet(False)

    # 3. Configure the InducedAccelerations Analysis
    iaa_analysis = osim.InducedAccelerations()
    iaa_analysis.setName("InducedAccelerations")
    iaa_analysis.setStartTime(initial_time)
    iaa_analysis.setEndTime(final_time)
    
    # Add the Analysis to the Tool
    tool.getAnalysisSet().adoptAndAppend(iaa_analysis)

    # Save the setup file for reference
    tool.printToXML(setup_file_path)
    print(f"IAA Tool configured. Setup file saved to: {setup_file_path}")
    tool.run()
    return tool

# --- Main OSIM Analysis ---
def create_setup_ID(osim_modelPath=None, ik_output=None, grf_xml=None,
                   id_output=None, taskSetPath=None, saveXMLPath=None):
    """
    Create an Inverse Dynamics (ID) setup XML file for OpenSim.

    This function creates the setup XML that will be used by run_id().
    """
    if not osim_modelPath:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')
    if not ik_output:
        ik_output = input("Enter the path to the IK output file (.mot): ").strip('"')
    if not grf_xml:
        grf_xml = input("Enter the path to the GRF XML file (.xml): ").strip('"')
    if not id_output:
        id_output = input("Enter the desired output path for the ID results (.sto): ").strip('"')

    if not os.path.exists(osim_modelPath):
        raise FileNotFoundError(f"OpenSim model file not found: {osim_modelPath}")
    if not os.path.exists(ik_output):
        raise FileNotFoundError(f"IK output file not found: {ik_output}")
    if not os.path.exists(grf_xml):
        raise FileNotFoundError(f"GRF XML file not found: {grf_xml}")

    # Load the model
    model = _quiet_model(osim_modelPath)
    model.initSystem()

    # Load the motion data
    motion = osim.Storage(ik_output)

    # Create the Inverse Dynamics tool
    idTool = osim.InverseDynamicsTool()
    idTool.setModel(model)
    idTool.setOutputGenForceFileName(os.path.basename(id_output))

    # Use relative paths for portability
    if saveXMLPath:
        setup_dir = os.path.dirname(saveXMLPath)
        relative_model = os.path.relpath(osim_modelPath, setup_dir)
        relative_ik = os.path.relpath(ik_output, setup_dir)
        relative_grf = os.path.relpath(grf_xml, setup_dir)
        relative_results = "./"
    else:
        relative_model = osim_modelPath
        relative_ik = ik_output
        relative_grf = grf_xml
        relative_results = os.path.dirname(os.path.abspath(id_output))

    idTool.setModelFileName(relative_model)
    idTool.setCoordinatesFileName(relative_ik)
    idTool.setStartTime(motion.getFirstTime())
    idTool.setEndTime(motion.getLastTime())
    idTool.setExternalLoadsFileName(relative_grf)
    idTool.setResultsDir(relative_results)
    idTool.setLowpassCutoffFrequency(6)

    # Save setup XML
    if saveXMLPath is None:
        saveXMLPath = id_output.replace('.sto', '_id_setup.xml')

    idTool.printToXML(saveXMLPath)

    # Load xml and edit forces to exclude
    xml = utils.read_xml(saveXMLPath)
    xml.find('.//forces_to_exclude').text = 'Muscles'
    utils.save_pretty_xml(xml, saveXMLPath)

    print(f"Inverse Dynamics setup saved to {os.path.abspath(saveXMLPath)}")

@_quiet_console
def run_id(osimModelPath=None, ikOutputPath=None, grfXmlPath=None,
         setupXmlPath=None):
    """
    Example usage:
    main(osim_modelPath='path/to/model.osim',
         ik_output='path/to/ik_output.mot',
         grf_xml='path/to/grf.xml',
         setup_xml='path/to/setup.xml',
         resultsDir='path/to/results')

    """
    # If setupXmlPath is provided, load parameters from it
    if setupXmlPath and os.path.exists(setupXmlPath):
        setup_dir = os.path.dirname(os.path.abspath(setupXmlPath))
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(setupXmlPath)
            root = tree.getroot()

            # Extract paths from setup XML
            if not osimModelPath:
                model_elem = root.find('.//model_file')
                if model_elem is not None and model_elem.text:
                    model_file = model_elem.text
                    # Convert relative to absolute if needed
                    if not os.path.isabs(model_file):
                        osimModelPath = os.path.normpath(os.path.join(setup_dir, model_file))
                    else:
                        osimModelPath = model_file

            if not ikOutputPath:
                coord_elem = root.find('.//coordinates_file')
                if coord_elem is not None and coord_elem.text:
                    coord_file = coord_elem.text
                    if not os.path.isabs(coord_file):
                        ikOutputPath = os.path.normpath(os.path.join(setup_dir, coord_file))
                    else:
                        ikOutputPath = coord_file

            if not grfXmlPath:
                grf_elem = root.find('.//external_loads_file')
                if grf_elem is not None and grf_elem.text:
                    grf_file = grf_elem.text
                    if not os.path.isabs(grf_file):
                        grfXmlPath = os.path.normpath(os.path.join(setup_dir, grf_file))
                    else:
                        grfXmlPath = grf_file
        except Exception as e:
            print(f"Warning: Could not read parameters from setup XML: {e}")

    # Fall back to prompting if parameters are still missing
    if not osimModelPath:
        osimModelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')
    if not ikOutputPath:
        ikOutputPath = input("Enter the path to the Inverse Kinematics output file (.mot): ").strip('"')
    if not grfXmlPath:
        grfXmlPath = input("Enter the path to the Ground Reaction Forces XML file (.xml): ").strip('"')
    if not setupXmlPath:
        setupXmlPath = input("Enter the path to save the Inverse Dynamics setup XML file (.xml): ").strip('"')

    resultsDir = os.path.dirname(os.path.abspath(setupXmlPath))
    
    if not os.path.exists(osimModelPath):
        raise FileNotFoundError(f"OpenSim model file not found: {osimModelPath}")
    
    if not os.path.exists(ikOutputPath):
        raise FileNotFoundError(f"Inverse Kinematics motion file not found: {ikOutputPath}")

    if not os.path.exists(grfXmlPath):
        raise FileNotFoundError(f"Ground Reaction Forces XML file not found: {grfXmlPath}")
    
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)
    
    # Load the model
    print(f"Loading OpenSim model from {osimModelPath}")
    model = load_model(osimModelPath)
    model.initSystem()

    # Load the motion data
    motion = osim.Storage(ikOutputPath)

    # Create the Inverse Dynamics tool
    idTool = osim.InverseDynamicsTool()
    idTool.setModel(model)
    idTool.setOutputGenForceFileName("inverse_dynamics.sto") # Output file name for the forces
    idTool.setModelFileName(os.path.relpath(osimModelPath, start=os.path.dirname(setupXmlPath)))
    idTool.setCoordinatesFileName(os.path.relpath(ikOutputPath, start=os.path.dirname(setupXmlPath)))
    idTool.setStartTime(motion.getFirstTime()) # Start time
    idTool.setEndTime(motion.getLastTime()) # end time
    idTool.setExternalLoadsFileName(os.path.relpath(grfXmlPath, start=os.path.dirname(setupXmlPath)))
    idTool.setResultsDir(os.path.relpath(resultsDir, start=os.path.dirname(setupXmlPath)))
    
    # Set lowpass filter frequency
    idTool.setLowpassCutoffFrequency(6)
    
    # Print the setup to XML
    idTool.printToXML(setupXmlPath)
    print(f"Inverse Dynamics setup saved to {setupXmlPath}")
    
    # Load xml and edit forces to exclude
    xml = utils.read_xml(setupXmlPath)
    xml.find('.//forces_to_exclude').text = 'Muscles'
    utils.save_pretty_xml(xml, setupXmlPath)

    # Reload tool from xml
    idTool = osim.InverseDynamicsTool(setupXmlPath)
    idTool.printToXML(setupXmlPath)  # Print to XML again to ensure changes are saved

    # Run the inverse dynamics calculation
    original_cwd = os.getcwd()
    try:
        os.chdir(resultsDir)
        with _osim_quiet_ctx():
            idTool.run()
        idTool.setModel(model)  # Set the model again after running
        print(f"Inverse Dynamics calculation completed. Results saved to {resultsDir}\\inverse_dynamics.sto")
    finally:
        # Restore original working directory
        try:
            os.chdir(original_cwd)
        except Exception as e:
            print(f"Warning: Could not restore original working directory: {e}")

@_quiet_console
def run_ma(osim_modelPath=None, ik_output=None,
         grf_xml=None, results_dir=None, coordinates=None,
         solve_equilibrium=False):
    if osim_modelPath is None:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')
    if ik_output is None:
        ik_output = input("Enter the desired output path for the IK results (.mot): ").strip('"')
    if grf_xml is None:
        grf_xml = input("Enter the path to the GRF XML file (.xml): ").strip('"')
    
    ikParentDir = os.path.dirname(os.path.abspath(ik_output))
    # Write MA outputs to the caller-specified folder (muscle_analysis/ in the
    # subfoldered layout); fall back to the legacy MuscleAnalysis/ next to IK.
    resultsDir = os.path.abspath(results_dir) if results_dir else os.path.join(ikParentDir, 'MuscleAnalysis')
    setup_xml = os.path.join(resultsDir, 'setup_MA.xml')
    

    if not os.path.exists(osim_modelPath):
        raise FileNotFoundError(f"OpenSim model file not found: {osim_modelPath}")
    
    if not os.path.exists(ik_output):
        raise FileNotFoundError(f"Inverse Kinematics motion file not found: {ik_output}")
    
    if not os.path.exists(grf_xml):
        raise FileNotFoundError(f"Ground Reaction Forces XML file not found: {grf_xml}")
        
    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir, exist_ok=True)
    
    # Load the model
    print(f"Loading OpenSim model from {osim_modelPath}")
    model = load_model(osim_modelPath)
    model.initSystem()

    # Load the motion data
    motion = osim.Storage(ik_output)

    # Create a MuscleAnalysis object
    muscleAnalysis = osim.MuscleAnalysis()
    muscleAnalysis.setModel(model)
    muscleAnalysis.setStartTime(motion.getFirstTime())
    muscleAnalysis.setEndTime(motion.getLastTime())

    # Restrict MA to the coordinates we actually use. By default MuscleAnalysis
    # computes moment arms + moments for EVERY coordinate (arms, lumbar, wrist,
    # mtp, ...), which is the bulk of MA compute and disk I/O (~80 .sto files).
    # Limiting to the lower-limb DOFs is a large speed-up with no loss for our
    # analyses/validation. The list can be overridden via the `coordinates`
    # argument or settings.MuscleAnalysisSettings.coordinates.
    if coordinates is None:
        try:
            coordinates = list(getattr(settings, 'MuscleAnalysisSettings', None)
                               and settings.MuscleAnalysisSettings.coordinates or [])
        except Exception:
            coordinates = []
        if not coordinates:
            coordinates = ['hip_flexion', 'hip_adduction', 'hip_rotation',
                           'knee_angle', 'knee_adduction', 'ankle_angle',
                           'subtalar_angle']
    try:
        cs = model.getCoordinateSet()
        model_names = {cs.get(i).getName() for i in range(cs.getSize())}
        want = []
        for base in coordinates:
            cands = [base] if base in model_names else [f'{base}_r', f'{base}_l']
            for nm in cands:
                if nm in model_names and nm not in want:
                    want.append(nm)
        if want:
            arr = osim.ArrayStr()
            for nm in want:
                arr.append(nm)
            muscleAnalysis.setCoordinates(arr)
            print(f"MuscleAnalysis restricted to {len(want)} coordinates: {want}")
    except Exception as _e:
        print(f"Warning: could not restrict MuscleAnalysis coordinates ({_e}); "
              "computing all.")

    # Create the muscle analysis tool
    maTool = osim.AnalyzeTool()
    maTool.setModel(model)
    maTool.setModelFilename(os.path.relpath(osim_modelPath,  start=os.path.dirname(setup_xml)))
    maTool.setLowpassCutoffFrequency(6)
    maTool.setCoordinatesFileName(os.path.relpath(ik_output, start=os.path.dirname(setup_xml)))
    maTool.setName('')
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setStartTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.getAnalysisSet().cloneAndAppend(muscleAnalysis)
    maTool.setResultsDir(os.path.relpath(resultsDir, start=os.path.dirname(setup_xml)))
    maTool.setInitialTime(motion.getFirstTime())
    maTool.setFinalTime(motion.getLastTime())
    maTool.setExternalLoadsFileName(os.path.relpath(grf_xml, start=os.path.dirname(setup_xml)))
    # With equilibrium OFF the tool never solves the fibre/tendon force
    # balance, so _MuscleAnalysis_FiberLength.sto comes back at the muscle's
    # INITIAL fibre length for every frame -- 0.1000 m for every muscle in
    # every model -- and FiberVelocity is then the derivative of a flat line,
    # reaching 631 m/s. Moment arms, MTU length and the kinematic outputs are
    # unaffected, which is why this went unnoticed: only the fibre columns are
    # wrong. Turn it on when a fibre-level quantity is actually wanted; it is
    # slower, and with a coordinates file and no states OpenSim solves at a
    # default activation, so the result is a kinematically consistent fibre
    # length rather than an activation-specific one.
    maTool.setSolveForEquilibrium(bool(solve_equilibrium))
    maTool.setReplaceForceSet(False)
    maTool.setMaximumNumberOfSteps(20000)
    maTool.setOutputPrecision(8)
    maTool.setMaxDT(1)
    maTool.setMinDT(1e-008)
    maTool.setErrorTolerance(1e-005)
    maTool.removeControllerSetFromModel()
    maTool.setLowpassCutoffFrequency(6)
    maTool.printToXML(setup_xml)

    # Reload analysis from xml
    maTool = osim.AnalyzeTool(setup_xml)
    try:
        maTool.getModel().set_assembly_accuracy(_assembly_accuracy())
    except Exception:
        pass
    maTool.getModel().initSystem()
    # Run the muscle analysis calculation
    original_cwd = os.getcwd()
    try:
        os.chdir(resultsDir)
        maTool.run()
    finally:
        # Restore original working directory
        try:
            os.chdir(original_cwd)
        except Exception as e:
            print(f"Warning: Could not restore original working directory: {e}")

def reserve_actuator_plan(model, actuators_path, model_path=""):
    """Decide whether SO's reserve actuators come from the MODEL or from a file.

    They must come from exactly ONE of the two. StaticOptimization runs with
    useModelForceSet(True) and ALSO appends whatever force-set files it is
    given, so an actuator present in both is created TWICE: two independent
    actuators on the same coordinate. That halves the effective cost of using a
    reserve and doubles the reserve torque available, and nothing warns.

    Present in NEITHER is worse, and quieter. SO then has nothing to absorb the
    difference between the muscle moments and the inverse-dynamics moments, so
    it drives the muscles to whatever it takes. Measured case: a walking hip
    contact force of 26 BW against a true 5.4, gastrocnemius off by 5.9 kN, and
    no error, warning or missing file anywhere -- the only visible symptom was
    the force file carrying 128 columns instead of 144.

    -> ("model", note)  skip the append
       ("file",  note)  append, as before
    Raises RuntimeError when neither source has them, or when they are split
    across both.
    """
    import re as _re
    have = set()
    fs = model.getForceSet()
    for i in range(fs.getSize()):
        n = fs.get(i).getName()
        if n.endswith("_reserve") or n in _RESIDUAL_NAMES:
            have.add(n)

    want, file_state = set(), "missing"
    if actuators_path and os.path.exists(actuators_path):
        file_state = "present but empty"
        try:
            with open(actuators_path, encoding="utf-8", errors="replace") as _fh:
                _txt = _fh.read()
            want = set(_re.findall(
                r'<(?:Coordinate|Point|Torque)Actuator name="([^"]+)"', _txt))
            if want:
                file_state = "%d actuator(s)" % len(want)
        except OSError:
            file_state = "unreadable"

    if have and want:
        both = have & want
        if both == want:
            return "model", ("%d already in the model; NOT appending %s "
                             "(appending would create each one twice)"
                             % (len(have), os.path.basename(actuators_path)))
        raise RuntimeError(
            "[SO ERROR] reserve actuators are SPLIT across the model and the "
            "force-set file; the overlap would be duplicated.\n"
            "  model only : %s\n"
            "  file only  : %s\n"
            "  in both    : %s\n"
            "Put the whole set in one place -- all in the model, or all in %s."
            % (sorted(have - want), sorted(want - have), sorted(both),
               actuators_path))

    if have:
        return "model", ("%d in the model (force-set file: %s); nothing appended"
                         % (len(have), file_state))
    if want:
        return "file", ("%d appended from %s"
                        % (len(want), os.path.basename(actuators_path)))

    raise RuntimeError(
        "[SO ERROR] no reserve or residual actuators anywhere -- static "
        "optimisation cannot run honestly.\n"
        "  model : %s\n"
        "          contains no *_reserve and none of FX/FY/FZ/MX/MY/MZ\n"
        "  file  : %s\n"
        "          %s\n"
        "Without them SO has nothing to absorb the muscle-moment vs ID-moment "
        "difference and will drive the muscle forces to compensate, silently. "
        "Add the actuators to the model, or restore the force-set file."
        % (model_path or "(unnamed)", actuators_path or "(none given)",
           file_state))

@_quiet_console
def run_so(osim_modelPath=None, ik_output=None, grf_xml=None,
           setup_xml=None, actuators=None, resultsDir=None):
    if not osim_modelPath:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')

    if not ik_output:
        ik_output = input("Enter the desired output path for the IK results (.mot): ").strip('"')

    if not grf_xml:
        grf_xml = input("Enter the path to the GRF XML file (.xml): ").strip('"')

    if not setup_xml:
        setup_xml = input("Enter the path to the setup XML file (.xml): ").strip('"')

    if not actuators:
        actuators = input("Enter the path to the actuators file (.xml): ").strip('"')

    if not resultsDir:
        resultsDir = os.path.dirname(ik_output)

    # Pre-flight file existence checks
    errors = []
    if not os.path.exists(osim_modelPath):
        errors.append(f"Model file not found: {osim_modelPath}")
    if not os.path.exists(ik_output):
        errors.append(f"IK output file not found: {ik_output}")
    if not os.path.exists(grf_xml):
        errors.append(f"GRF XML file not found: {grf_xml}")
    # A missing actuator file is NOT fatal on its own any more: the reserve
    # actuators may live in the model instead. reserve_actuator_plan() below
    # raises if they are in neither place, which is the condition that matters.

    if errors:
        error_msg = "SO Pre-flight Check Failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise RuntimeError(error_msg)

    if not os.path.exists(resultsDir):
        os.makedirs(resultsDir)

    # Load the model
    print(f"Loading OpenSim model from {osim_modelPath}")

    model = load_model(osim_modelPath)
    # model.initSystem()

    # load the motion data
    motion = osim.Storage(ik_output)

    # Create a StaticOptimization object
    so = osim.StaticOptimization()
    so.setStartTime(motion.getFirstTime())
    so.setEndTime(motion.getLastTime())
    so.setInDegrees(True)
    so.setUseMusclePhysiology(True)
    so.setUseModelForceSet(True)
    
    
    # Create analyze tool for static optimization
    so_analyze_tool = osim.AnalyzeTool()
    so_analyze_tool.setName("SO")

    # Set model file, motion files and external load file names
    so_analyze_tool.setModelFilename(os.path.relpath(osim_modelPath, start=os.path.dirname(setup_xml)))
    so_analyze_tool.setCoordinatesFileName(os.path.relpath(ik_output, start=os.path.dirname(setup_xml)))
    so_analyze_tool.setExternalLoadsFileName(os.path.relpath(grf_xml, start=os.path.dirname(setup_xml)))
    so_analyze_tool.setReplaceForceSet(False)
    _res_src, _res_note = reserve_actuator_plan(model, actuators, osim_modelPath)
    print(f"[SO] reserve actuators: {_res_note}")
    if _res_src == "file":
        so_analyze_tool.getForceSetFiles().append(
            os.path.relpath(actuators, start=os.path.dirname(setup_xml)))

    so_analyze_tool.setLowpassCutoffFrequency(6)
    
    # Add StaticOptimization analysis to the tool
    so_analyze_tool.updAnalysisSet().cloneAndAppend(so)

    # Configure analyze tool
    so_analyze_tool.setReplaceForceSet(False)
    so_analyze_tool.setStartTime(motion.getFirstTime())
    so_analyze_tool.setFinalTime(motion.getLastTime())

    # Set results directory
    so_analyze_tool.setResultsDir(os.path.relpath(resultsDir, start=os.path.dirname(setup_xml)))

    # Print configuration to XML file
    so_analyze_tool.printToXML(setup_xml)
    print("\n \n Static Optimization setup saved to:", setup_xml)
    
    # change optimizer_max_iterations in the xml file
    xml = utils.read_xml(setup_xml)
    static_opt = xml.getroot().find('.//StaticOptimization/optimizer_max_iterations')
    static_opt.text = '100'  # Set to 10 iterations
    utils.save_pretty_xml(xml, setup_xml)
    
    # run the Static Optimization
    so_analyze_tool = osim.AnalyzeTool(setup_xml)
    original_cwd = os.getcwd()
    try:
        os.chdir(resultsDir)
        so_analyze_tool.run()
        print(f"Static Optimization calculation completed. Results saved to {resultsDir}")
    except Exception as e:
        print(f"Error during Static Optimization: {e}")
    finally:
        # Restore original working directory
        try:
            os.chdir(original_cwd)
        except Exception as e:
            print(f"Warning: Could not restore original working directory: {e}")

@_quiet_console
def run_jra(osim_modelPath=None, ik_output=None,
         grf_xml=None, setup_xml=None, actuators=None,
         muscle_force_path=None, saveFileName=None):
    if not osim_modelPath:
        osim_modelPath = input("Enter the path to the OpenSim model file (.osim): ").strip('"')
    if not ik_output:
        ik_output = input("Enter the path to the coordinates motion file (.mot or .trc): ").strip('"')
    if not grf_xml:
        grf_xml = input("Enter the path to the external loads file (.xml): ").strip('"')
    if not setup_xml:
        setup_xml = input("Enter the path to save the JRA setup XML file (.xml): ").strip('"')
    if not muscle_force_path:
        muscle_force_path = input("Enter the path to the muscle forces file (.sto): ").strip('"')
    
    # Results + intermediate output belong next to the JRA SETUP file
    # (joint_contact_forces/), not next to the coordinates file
    # (external_biomechanics/). Derive from setup_xml, falling back to ik_output.
    setup_xml_parent = os.path.dirname(os.path.abspath(setup_xml)) if setup_xml \
        else os.path.dirname(os.path.abspath(ik_output))

    # start model
    osimModel = _quiet_model(osim_modelPath)
    
    # Get mot data to determine time range
    motData = osim.Storage(ik_output)

    # Get initial and intial time
    initial_time = motData.getFirstTime()
    final_time = motData.getLastTime()
    
    # start joint reaction analysis
    jr = osim.JointReaction(setup_xml)
    
    # add muscle forces file name to joint reaction analysis
    jr.setName('JRA')
    
    # define JRA 
    inFrame = osim.ArrayStr()
    onBody = osim.ArrayStr()
    jointNames = osim.ArrayStr()
    inFrame.set(0, 'child')
    onBody.set(0, 'child')
    jointNames.set(0, 'all')

    jr.setInFrame(inFrame)
    jr.setOnBody(onBody)
    jr.setJointNames(jointNames)

    # Set other parameters as needed
    jr.setStartTime(initial_time)
    jr.setEndTime(final_time)
    jr.setForcesFileName(os.path.abspath(muscle_force_path))

    # add to analysis tool
    analyzeTool_JR = create_analysis_tool(marker_trc = ik_output,
                                          externalloadsfile = grf_xml,
                                          osim_modelPath = osim_modelPath, 
                                          results_directory = setup_xml_parent, 
                                          actuators=actuators)
    
    analyzeTool_JR.setName('Analyse')
    analyzeTool_JR.getAnalysisSet().cloneAndAppend(jr)
    osimModel.addAnalysis(jr)

    # save setup file, rewrite its file paths RELATIVE to the setup's own dir
    # (portable), then reload so OpenSim resolves them against that dir.
    analyzeTool_JR.printToXML(setup_xml)
    relativise_setup_xml(setup_xml)
    analyzeTool_JR = osim.AnalyzeTool(setup_xml)
    # JRA's AnalyzeTool reloads the model from the setup XML, so the looser
    # assembly accuracy set elsewhere is lost -> the coupled (walker/Lerner) knee
    # trips SimTK's 1e-10 assembler tolerance and spams recoverable [error] lines.
    # Re-apply the project assembly accuracy on JRA's own model copy.
    try:
        analyzeTool_JR.getModel().set_assembly_accuracy(_assembly_accuracy())
    except Exception:
        pass
    print('jra for', setup_xml)
    analyzeTool_JR.run()
    
    # rename output file
    output_jra_file = os.path.join(setup_xml_parent, 'Analyse_JRA_ReactionLoads.sto')
    if saveFileName:
        new_jra_file = os.path.abspath(saveFileName)
        if os.path.exists(output_jra_file) and new_jra_file != output_jra_file:
            if os.path.exists(new_jra_file):
                os.remove(new_jra_file)
            os.rename(output_jra_file, new_jra_file)
            print(f"Joint Reaction Analysis results saved to: {new_jra_file}")
    else:
        if os.path.exists(output_jra_file):
            print(f"Joint Reaction Analysis results saved to: {output_jra_file}")

def run_emg_normalise(target_emg_path=None, normalise_emg_list=None):
    """
    Normalises EMG data based on a target EMG file.
    The target EMG file is used to scale the other EMG files in the list.
    """
    
    if not target_emg_path:
        target_emg_path = input("Enter the path to the target EMG .mot file to normalise: ").strip('"')
        
    if not normalise_emg_list:
        normalise_emg_list = []
        print("Enter paths to EMG .mot files to use for normalisation (one per line). Enter an empty line to finish:")
        while True:
            emg_file = input().strip('"')
            if emg_file == "":
                break
            if os.path.exists(emg_file):
                normalise_emg_list.append(emg_file)
            else:
                print(f"File not found: {emg_file}. Please try again.")
    
    target_emg = utils.load_any_data_file(target_emg_path)
    max_values = pd.DataFrame(columns=target_emg.columns)

    # Calculate the max of each EMG channel in normalise_emg_list
    for emg_file in normalise_emg_list:
        if not os.path.exists(emg_file):
            utils.print_to_log(f"EMG file not found: {emg_file}")
            continue
        emg_data = utils.load_any_data_file(emg_file)
        if emg_data is not None:
            max_values = pd.concat([max_values, pd.DataFrame([emg_data.max()])], ignore_index=True)
        else:
            print(f"Warning: Could not load EMG data from {emg_file}")
            
    if max_values.empty:
        utils.print_to_log("No valid EMG data found in the provided list.")
    
    
    if target_emg is None:
        utils.print_to_log(f"Target EMG file not found or could not be loaded: {target_emg_path}")

    
    # Normalise the target EMG to its own max values
    max_per_column = max_values.max(axis=0)
    target_emg_norm = target_emg.divide(max_per_column, axis=1)
    target_emg_norm['time'] = target_emg['time']  # Ensure time column is preserved
    
    # Save the normalised target EMG
    ext = os.path.splitext(target_emg_path)[1]
    savePath = os.path.abspath(target_emg_path.replace(ext, f'_normalised{ext}'))   
    utils.write_sto_file(dataFrame=target_emg_norm, 
                         file_path=savePath)

    utils.print_to_log(f"Normalised EMG data saved to: {savePath}")

def run_iaa(osim_modelPath=None, ik_output=None, grf_xml=None, setup_file_path=None, so_controls_file=None, actuators=None, setup_xml=None):
    """
    Run an Induced Acceleration Analysis (IAA) using OpenSim.
    """

    if os.path.exists(setup_xml):
        try:
            tool = osim.AnalyzeTool(setup_xml)
            tool.run()
            utils.print_to_log(f"IAA run successfully with existing setup XML: {setup_xml}")
            return
        except Exception as e:
            print(f"Error running IAA with existing setup XML: {e}")
            print("Falling back to creating a new IAA tool.")
            utils.print_to_log(f"Error running IAA with existing setup XML: {e}. Falling back to creating a new IAA tool.")
    
    try:
        tool = create_iaa_tool(osim_modelPath, ik_output, grf_xml, setup_file_path, so_controls_file, actuators)
        tool.run()
        utils.print_to_log("IAA run successfully.")
    except Exception as e:
        print(f"Error running IAA: {e}")
        utils.print_to_log(f"Error running IAA: {e}")

# --- Residual Reduction Algorithm (RRA) ---
def run_rra(osim_modelPath=None, ik_output=None, grf_xml=None, actuators=None, setup_xml=None, results_dir=None):
    """
    Run Residual Reduction Algorithm (RRA) using OpenSim.

    RRA is used to reduce the residual forces and moments at the pelvis by adjusting
    body mass and inertia properties or applying model-wide kinematic adjustments.

    Args:
        osim_modelPath: Path to the OpenSim model file
        ik_output: Path to inverse kinematics output file (.mot)
        grf_xml: Path to ground reaction force XML file
        actuators: Path to actuators setup file
        setup_xml: Path to RRA setup XML file (if already created)
        results_dir: Directory for results output
    """
    try:
        print("Starting Residual Reduction Algorithm (RRA)...")

        if setup_xml and os.path.exists(setup_xml):
            # Use existing RRA setup file
            try:
                tool = osim.RRATool(setup_xml)
                model = _quiet_model(osim_modelPath)
                tool.setModel(model)
                tool.run()
                utils.print_to_log("RRA completed successfully using existing setup file.")
                print("RRA calculation completed.")
                return
            except Exception as e:
                print(f"Error running RRA with existing setup: {e}")
                utils.print_to_log(f"Error running RRA with existing setup: {e}")

        # Create a new RRA tool if setup_xml not provided
        if not osim_modelPath or not ik_output:
            raise ValueError("osim_modelPath and ik_output are required for RRA")

        model = _quiet_model(osim_modelPath)
        state = model.initSystem()

        # Create RRA tool
        rra_tool = osim.RRATool()
        rra_tool.setModel(model)
        rra_tool.setInitialTime(0.0)
        rra_tool.setFinalTime(0.0)

        # Set kinematics from IK output
        rra_tool.setKinematicsFileName(ik_output)

        # Set external loads if provided
        if grf_xml and os.path.exists(grf_xml):
            rra_tool.setExternalLoadsFileName(grf_xml)

        # Set output directory
        if results_dir:
            rra_tool.setOutputModelFileName(os.path.join(results_dir, "rra_adjusted_model.osim"))
            rra_tool.setResultsDir(results_dir)

        # Run RRA
        rra_tool.run()
        utils.print_to_log("RRA completed successfully.")
        print("RRA calculation completed. Results saved.")

    except Exception as e:
        error_msg = f"Error running RRA: {str(e)}"
        print(error_msg)
        utils.print_to_log(error_msg)
        raise

# --- Computed Muscle Control (CMC) ---
def run_cmc(osim_modelPath=None, ik_output=None, grf_xml=None, emg_file=None, actuators=None, setup_xml=None, results_dir=None):
    """
    Run Computed Muscle Control (CMC) using OpenSim.

    CMC uses an optimization approach to compute muscle excitations that produce the desired kinematics
    while minimizing a cost function, typically the sum of squared muscle activations.

    Args:
        osim_modelPath: Path to the OpenSim model file
        ik_output: Path to inverse kinematics output file (.mot)
        grf_xml: Path to ground reaction force XML file
        emg_file: Path to EMG data file for tracking constraints (optional)
        actuators: Path to actuators setup file
        setup_xml: Path to CMC setup XML file (if already created)
        results_dir: Directory for results output
    """
    try:
        print("Starting Computed Muscle Control (CMC)...")

        if setup_xml and os.path.exists(setup_xml):
            # Use existing CMC setup file
            try:
                tool = osim.CMCTool(setup_xml)
                # Do NOT setModel() here: CMCTool(setup) already built its model
                # WITH force_set_files applied; replacing it would silently drop
                # the residual/reserve actuators. The setup's <model_file> rules.
                tool.run()
                utils.print_to_log("CMC completed successfully using existing setup file.")
                print("CMC calculation completed.")
                return
            except Exception as e:
                print(f"Error running CMC with existing setup: {e}")
                utils.print_to_log(f"Error running CMC with existing setup: {e}")

        # Create a new CMC tool if setup_xml not provided
        if not osim_modelPath or not ik_output:
            raise ValueError("osim_modelPath and ik_output are required for CMC")

        model = _quiet_model(osim_modelPath)
        state = model.initSystem()

        # Create CMC tool
        cmc_tool = osim.CMCTool()
        cmc_tool.setModel(model)
        cmc_tool.setInitialTime(0.0)
        cmc_tool.setFinalTime(0.0)

        # Set kinematics from IK output
        cmc_tool.setDesiredKinematicsFileName(ik_output)

        # Set external loads if provided
        if grf_xml and os.path.exists(grf_xml):
            cmc_tool.setExternalLoadsFileName(grf_xml)

        # Set output directory
        if results_dir:
            cmc_tool.setResultsDir(results_dir)

        # Run CMC
        cmc_tool.run()
        utils.print_to_log("CMC completed successfully.")
        print("CMC calculation completed. Muscle excitations computed.")

    except Exception as e:
        error_msg = f"Error running CMC: {str(e)}"
        print(error_msg)
        utils.print_to_log(error_msg)
        raise

# --- Metabolic Cost Analysis (Energetics) ---
def run_energetics(osim_modelPath=None, ik_output=None, muscle_activations=None, setup_xml=None, results_dir=None):
    """
    Run Metabolic Cost Analysis (Energetics) using OpenSim.

    Computes the metabolic cost of a movement using muscle activations and kinematics.
    This uses the Metabolic Cost Analysis tool to estimate energy expenditure.

    Args:
        osim_modelPath: Path to the OpenSim model file
        ik_output: Path to inverse kinematics output file (.mot)
        muscle_activations: Path to muscle activation file (from CMC or SO)
        setup_xml: Path to Metabolic Cost Analysis setup XML file
        results_dir: Directory for results output
    """
    try:
        print("Starting Metabolic Cost Analysis (Energetics)...")

        # ------------------------------------------------------------------ #
        # Pre-flight checks
        # ------------------------------------------------------------------ #
        if not osim_modelPath or not os.path.exists(osim_modelPath):
            raise FileNotFoundError(f"Model file not found: {osim_modelPath}")
        if not ik_output or not os.path.exists(ik_output):
            raise FileNotFoundError(f"IK coordinates file not found: {ik_output}")

        if results_dir is None:
            results_dir = os.path.dirname(os.path.abspath(ik_output))
        os.makedirs(results_dir, exist_ok=True)

        # Absolute paths — the tool is run with cwd=results_dir below, so we keep
        # everything absolute to avoid relative-path surprises.
        osim_modelPath = os.path.abspath(osim_modelPath)
        ik_output = os.path.abspath(ik_output)
        if muscle_activations:
            muscle_activations = os.path.abspath(muscle_activations)

        # ------------------------------------------------------------------ #
        # Path A — an existing Metabolic Cost setup XML was supplied: use it.
        # ------------------------------------------------------------------ #
        if setup_xml and os.path.exists(setup_xml):
            try:
                tool = osim.AnalyzeTool(setup_xml)
                tool.setResultsDir(results_dir)
                original_cwd = os.getcwd()
                try:
                    os.chdir(results_dir)
                    tool.run()
                finally:
                    os.chdir(original_cwd)
                utils.print_to_log(
                    "Metabolic Cost Analysis completed using existing setup file.")
                print("Energetics calculation completed.")
                return
            except Exception as e:
                print(f"Existing energetics setup failed ({e}); rebuilding it.")
                utils.print_to_log(
                    f"Existing energetics setup failed ({e}); rebuilding it.")

        # ------------------------------------------------------------------ #
        # Path B — build a metabolic probe set + ProbeReporter from scratch.
        # ------------------------------------------------------------------ #
        model = _quiet_model(osim_modelPath)
        model.initSystem()

        # Attach an Umberger (2010) metabolic-energy probe covering every muscle.
        # All four rate components are reported (activation/maintenance,
        # shortening, mechanical work and basal), plus per-muscle breakdown.
        probe = osim.Umberger2010MuscleMetabolicsProbe()
        probe.setName("metabolics")
        for _setter, _val in (
            ("set_activation_maintenance_rate_on", True),
            ("set_shortening_rate_on",            True),
            ("set_basal_rate_on",                 True),
            ("set_mechanical_work_rate_on",       True),
            ("set_report_total_metabolics_only",  False),
            ("setOperation",                      "value"),
        ):
            try:
                getattr(probe, _setter)(_val)
            except Exception:
                pass  # property name varies slightly across OpenSim versions

        muscles = model.getMuscles()
        n_added = 0
        for i in range(muscles.getSize()):
            try:
                probe.addMuscle(muscles.get(i).getName(), 0.5)
                n_added += 1
            except Exception as e:
                print(f"  [warn] could not add muscle to metabolics probe: {e}")
        if n_added == 0:
            raise RuntimeError("No muscles could be added to the metabolics probe.")
        print(f"  Metabolics probe covers {n_added} muscles.")

        model.addProbe(probe)
        model.finalizeConnections()

        # Persist the probe-augmented model next to the results so the setup XML
        # is self-contained and reproducible.
        model_with_probes = os.path.join(results_dir, "model_metabolics.osim")
        model.printToXML(model_with_probes)

        # Time window from the IK motion.
        motion = osim.Storage(ik_output)
        initial_time = motion.getFirstTime()
        final_time = motion.getLastTime()

        # Build the AnalyzeTool around the in-memory (probe-augmented) model.
        tool = osim.AnalyzeTool(model)
        tool.setName("energetics")
        tool.setModelFilename(model_with_probes)
        tool.setCoordinatesFileName(ik_output)
        tool.setInitialTime(initial_time)
        tool.setFinalTime(final_time)
        tool.setLowpassCutoffFrequency(6.0)

        # Feed muscle activations (from Static Optimization) as the model states
        # so the probe evaluates real per-frame activations; solve fibre
        # equilibrium from the posed kinematics.
        if muscle_activations and os.path.exists(muscle_activations):
            tool.setStatesFileName(muscle_activations)
            try:
                tool.setSolveForEquilibrium(True)
            except Exception:
                pass
        else:
            print("  [warn] No SO activation file supplied — metabolic rates "
                  "will be based on default activation.")

        # Attach the ProbeReporter so probe outputs are written to .sto.
        probe_reporter = osim.ProbeReporter(model)
        probe_reporter.setName("ProbeReporter")
        probe_reporter.setStartTime(initial_time)
        probe_reporter.setEndTime(final_time)
        tool.updAnalysisSet().cloneAndAppend(probe_reporter)

        tool.setResultsDir(results_dir)

        # Save the setup for the record/debugging.
        if not setup_xml:
            setup_xml = os.path.join(results_dir, "setup_Energetics.xml")
        tool.printToXML(setup_xml)
        print(f"  Energetics setup saved to: {setup_xml}")

        # Run with cwd inside results_dir so all relative outputs land there.
        original_cwd = os.getcwd()
        try:
            os.chdir(results_dir)
            tool.run()
        finally:
            try:
                os.chdir(original_cwd)
            except Exception:
                pass

        out_file = os.path.join(results_dir, "energetics_ProbeReporter_probes.sto")
        utils.print_to_log(
            f"Metabolic Cost Analysis completed. Output: {out_file}")
        print(f"Energetics calculation completed. Metabolic cost written to "
              f"{results_dir}")

    except Exception as e:
        error_msg = f"Error running Metabolic Cost Analysis: {str(e)}"
        print(error_msg)
        utils.print_to_log(error_msg)
        raise

# --- Body Kinematics Analysis ---
def run_body_kinematics(osim_modelPath=None, ik_output=None, bodies=None, setup_xml=None, results_dir=None):
    """
    Run Body Kinematics Analysis using OpenSim.

    Computes body kinematics (position, velocity, acceleration) for specified bodies
    during a movement based on the inverse kinematics solution.

    Args:
        osim_modelPath: Path to the OpenSim model file
        ik_output: Path to inverse kinematics output file (.mot)
        bodies: List of body names to analyze (default: all bodies)
        setup_xml: Path to Body Kinematics setup XML file
        results_dir: Directory for results output
    """
    try:
        print("Starting Body Kinematics Analysis...")

        if setup_xml and os.path.exists(setup_xml):
            # Use existing Body Kinematics setup file
            try:
                tool = osim.AnalyzeTool(setup_xml)
                model = _quiet_model(osim_modelPath)
                tool.setModel(model)
                tool.run()
                utils.print_to_log("Body Kinematics Analysis completed successfully using existing setup file.")
                print("Body Kinematics calculation completed.")
                return
            except Exception as e:
                print(f"Error running Body Kinematics with existing setup: {e}")
                utils.print_to_log(f"Error running Body Kinematics with existing setup: {e}")

        # Create a new Body Kinematics Analysis if setup_xml not provided
        if not osim_modelPath or not ik_output:
            raise ValueError("osim_modelPath and ik_output are required for Body Kinematics Analysis")

        model = _quiet_model(osim_modelPath)
        state = model.initSystem()

        # Create AnalyzeTool for body kinematics
        analyze_tool = osim.AnalyzeTool()
        analyze_tool.setModel(model)

        # Set kinematics from IK output
        analyze_tool.setCoordinatesFileName(ik_output)

        # Get body set from model
        body_set = model.getBodySet()
        if bodies is None:
            # Analyze all bodies by default
            bodies = [body_set.get(i).getName() for i in range(body_set.getSize())]

        # Set output directory
        if results_dir:
            analyze_tool.setResultsDir(results_dir)

        # Run analysis
        analyze_tool.run()
        utils.print_to_log("Body Kinematics Analysis completed successfully.")
        print(f"Body Kinematics calculation completed for {len(bodies)} bodies.")

    except Exception as e:
        print(f"Error in Body Kinematics Analysis: {e}")
        utils.print_to_log(f"Error in Body Kinematics Analysis: {e}")
        raise


if __name__ == "__main__":

    class _Tee:
        """Write to both the original stdout and a log file simultaneously."""
        def __init__(self, log_file):
            self._stdout = sys.stdout
            self._log = log_file

        def write(self, data):
            self._stdout.write(data)
            self._stdout.flush()
            self._log.write(data)
            self._log.flush()

        def flush(self):
            self._stdout.flush()
            self._log.flush()

        def __getattr__(self, name):
            return getattr(self._stdout, name)

    LocalFuncs = [f for f in dir() if callable(globals()[f])]

    while True:
        print("Available commands:", LocalFuncs)
        command = input("Enter command: ")

        if command not in LocalFuncs:
            print("Invalid command. Please try again.")
            continue

        log_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs'))
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = os.path.join(log_dir, f'openSim_log_{timestamp}.log')

        with open(log_filename, 'w', encoding='utf-8') as _lf:
            _orig_stdout = sys.stdout
            sys.stdout = _Tee(_lf)
            _osim_sink = False
            try:
                osim.Logger.addFileSink(log_filename)
                _osim_sink = True
            except Exception:
                pass
            try:
                print(f"--- openSim command: {command} | {timestamp} ---")
                globals()[command]()
                print("Command executed successfully.")
            except Exception as e:
                print(f"Error executing {command}: {e}")
            finally:
                if _osim_sink:
                    try:
                        osim.Logger.removeFileSink(log_filename)
                    except Exception:
                        pass
                sys.stdout = _orig_stdout

        print(f"Log saved to: {log_filename}")
