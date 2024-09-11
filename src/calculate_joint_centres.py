
import numpy as np
import pyc3dserver as c3d
import math
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
import opensim as osim


def import_c3d_to_dict(c3dFilePath=''):

    if c3dFilePath == '':
      root = tk.Tk()
      root.withdraw()
      c3dFilePath = filedialog.askopenfilename()

    c3d_dict = dict()
    # Get the COM object of C3Dserver (https://pypi.org/project/pyc3dserver/)
    itf = c3d.c3dserver()
    c3d.open_c3d(itf, c3dFilePath)

    c3d_dict['FilePath'] = c3dFilePath
    c3d_dict['DataRate'] = c3d.get_video_fps(itf)
    c3d_dict['CameraRate'] = c3d.get_video_fps(itf)
    c3d_dict["OrigDataRate"] = c3d.get_video_fps(itf)
    c3d_dict["OrigAnalogRate"] = c3d.get_analog_fps(itf)
    c3d_dict["OrigDataStartFrame"] = 0
    c3d_dict["OrigDataLAstFrame"] = c3d.get_last_frame(itf)

    c3d_dict["NumFrames"] = c3d.get_num_frames(itf)
    c3d_dict["OrigNumFrames"] = c3d.get_num_frames(itf)

    c3d_dict['MarkerNames'] = c3d.get_marker_names(itf)
    c3d_dict['NumMarkers'] = len(c3d_dict['MarkerNames'] )

    c3d_dict['Labels'] = c3d.get_marker_names(itf)

    c3d_dict['TimeStamps'] = c3d.get_video_times(itf)

    c3d_data = c3d.get_dict_markers(itf)
    my_dict = c3d_data['DATA']['POS']
    c3d_dict["Data"] = np.empty(shape=(c3d_dict["NumMarkers"], c3d_dict["NumFrames"], 3), dtype=np.float32)
    for i, label in enumerate(my_dict):
        c3d_dict["Data"][i] = my_dict[label]

    return c3d_dict

def writeTRC(c3dFilePath, trcFilePath):

    print('writing trc file ...')
    c3d_dict = import_c3d_to_dict (c3dFilePath)

    with open(trcFilePath, 'w') as file:
        # from https://github.com/IISCI/c3d_2_trc/blob/master/extractMarkers.py
        # Write header
        file.write("PathFileType\t4\t(X/Y/Z)\toutput.trc\n")
        file.write("DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n")
        file.write("%d\t%d\t%d\t%d\tmm\t%d\t%d\t%d\n" % (c3d_dict["DataRate"], c3d_dict["CameraRate"], c3d_dict["NumFrames"],
                                                        c3d_dict["NumMarkers"], c3d_dict["OrigDataRate"],
                                                        c3d_dict["OrigDataStartFrame"], c3d_dict["OrigNumFrames"]))

        # Write labels
        file.write("Frame#\tTime\t")
        for i, label in enumerate(c3d_dict["Labels"]):
            if i != 0:
                file.write("\t")
            file.write("\t\t%s" % (label))
        file.write("\n")
        file.write("\t")
        for i in range(len(c3d_dict["Labels"]*3)):
            file.write("\t%c%d" % (chr(ord('X')+(i%3)), math.ceil((i+3)/3)))
        file.write("\n")

        # Write data
        for i in range(len(c3d_dict["Data"][0])):
            file.write("%d\t%f" % (i, c3d_dict["TimeStamps"][i]))
            for l in range(len(c3d_dict["Data"])):
                file.write("\t%f\t%f\t%f" % tuple(c3d_dict["Data"][l][i]))
            file.write("\n")

        print('trc file saved')

def calculate_joint_centres(trc_filepath, new_filepath=None, plot_hjc=False):
  """
  Calculates hip joint centers in a TRC file according to Harrington et al.

  Args:
      trc_filepath (str): Path to the TRC file.
      new_filepath (str, optional): Path to save the modified TRC file. Defaults to None.
      plot_hjc (bool, optional): Whether to plot the HJC for verification. Defaults to False.

  Returns:
      dict: Dictionary containing the modified TRC data.
  """

  # Load TRC data
  with open(trc_filepath, 'r') as f:
    # ... (Implementation for loading TRC data using your preferred library)
    trc = ...

  # Set default output filepath
  if new_filepath is None:
    new_filepath = trc_filepath.replace('.trc', '_HJC.trc')

  # Sample rate (assuming data is evenly sampled)
  rate = round(1 / (trc['Time'][1] - trc['Time'][0]))

  # Add HJC using Harrington equations
  trc = add_hjc_harrington(trc)

  # Optional: Plot HJC for verification
  if plot_hjc:
    plot_hjc_3d(trc)

  # Add knee and ankle joint centers (assuming markers exist)
  trc['RKJC'] = (trc['RKNE'] + trc['RKNM']) / 2
  trc['LKJC'] = (trc['LKNE'] + trc['LKNM']) / 2
  trc['RAJC'] = (trc['RANK'] + trc['RANM']) / 2
  trc['LAJC'] = (trc['LANK'] + trc['LANM']) / 2

  # Convert markers to separate data and labels (assuming specific format)
  markers_data = np.array([v for k, v in trc.items() if k != 'Time'])
  marker_labels = list(trc.keys())[1:]

  # Save modified TRC data
  try:
    # ... (Implementation for saving TRC data using your preferred library)
    write_trc_os4(markers_data, marker_labels, rate, new_filepath)
  except Exception as e:
    print(f"Error saving TRC file: {e}")
    # Handle potential issues (e.g., missing markers)

  return trc

def add_hjc_harrington(trc):
  """
  Calculates hip joint centers (HJC) using Harrington et al. (2006) formulas.

  Args:
      trc (dict): Dictionary containing TRC data.

  Returns:
      dict: Modified TRC data with added HJC markers.
  """

  lasis = trc['LASI'].T
  rasis = trc['RASI'].T

  # Handle missing SACRUM marker
  try:
    sacrum = trc['SACR'].T
  except KeyError:
    sacrum = (trc['LPSI'] + trc['RPSI']) / 2
    trc['SACR'] = sacrum.T

  num_frames = len(rasis)
  hjc_left, hjc_right = np.empty((3, num_frames)), np.empty((3, num_frames))

  for i in range(num_frames):
    # Right-handed pelvis reference system definition
    pelvis_center = (lasis[:, i] + rasis[:, i]) / 2
    provv = (rasis[:, i] - sacrum[:, i]) / np.linalg.norm(rasis[:, i] - sacrum[:, i])
    ib = (rasis[:, i] - lasis[:, i]) / np.linalg.norm(rasis[:, i] - lasis[:, i])
    kb = np.cross(ib, provv)
    kb /= np.linalg.norm(kb)
    jb = np.cross(kb, ib)
    jb /= np.linalg.norm(jb)

    pelvis_transform = np.array([ib[0], jb[0], kb[0], pelvis_center[0]],
                                  [ib[1], jb[1], kb[1], pelvis_center[1],
                                  ib[2], jb[1]])



if __name__ == "__main__":
  # Example usage
  trc_filepath = 'example.trc'
  new_filepath = 'example_HJC.trc'
  c3dFilePath = r"C:\Git\isbs2024\Data\Simulations\Athlete_03\sq_70\c3dfile.c3d"
  c3dDict = import_c3d_to_dict(c3dFilePath)
  import opensim as osim

  def import_c3d_data(c3d_file_path):
    """Imports C3D data using OpenSim's C3DFileAdapter.

    Args:
        c3d_file_path: Path to the C3D file.

    Returns:
        A tuple containing:
            - markers: A Pandas DataFrame containing marker trajectories.
            - force_plates: A dictionary containing force plate data.
            - other_data: A dictionary containing other data (optional).
    """

    # Read the C3D data
    data_adapter = osim.C3DFileAdapter()
    tables = data_adapter.read(c3d_file_path)

    # Extract marker data (assuming markers table exists)
    markers_table = tables.get("markers", None)
    if markers_table:
      markers = osim.to_pandas(markers_table)
    else:
      markers = None

    # Extract force plate data (assuming force plate tables exist)
    force_plates = {}
    for table_name, table in tables.items():
      if table_name.startswith("force_plate"):
        force_plates[table_name] = osim.to_pandas(table)

    # Extract other data (optional)
    # You can add logic to extract other data from tables if needed
    other_data = {}

    return markers, force_plates, other_data

  # Example usage
  c3d_file_path = "/path/to/your/c3d/file.c3d"
  markers, force_plates, other_data = import_c3d_data(c3d_file_path)

  # Access marker data
  print(markers.head())

  # Access force plate data for a specific plate
  plate_name = "force_plate_1"
  plate_data = force_plates.get(plate_name)

  # (Perform further analysis using the extracted data)
