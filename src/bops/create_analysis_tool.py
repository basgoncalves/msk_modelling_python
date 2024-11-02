import opensim as osim

def create_analysis_tool(coordinates_file, model_path, results_directory, force_set_files=None):
  """Creates and configures an OpenSim AnalyzeTool object.

  Args:
    coordinates_file: Path to the motion data file (e.g., .trc or .mot).
    model_path: Path to the OpenSim model file (.osim).
    results_directory: Path to the directory for storing results.
    force_set_files (optional): List of paths to actuator force set files.

  Returns:
    OpenSim AnalyzeTool object.
  """

  # Load the motion data
  mot_data = osim.Storage(coordinates_file)

  # Get initial and final time
  initial_time = mot_data.getStartTime()
  final_time = mot_data.getEndTime()

  # Create and set model
  model = osim.Model(model_path)
  analyze_tool = osim.AnalyzeTool()
  analyze_tool.setModel(model)

  # Set other parameters
  analyze_tool.setModelFilename(model.getFilePath())
  analyze_tool.setReplaceForceSet(False)
  analyze_tool.setResultsDir(results_directory)
  analyze_tool.setOutputPrecision(8)

  # Set actuator force files (if provided)
  if force_set_files:
    force_set = osim.ArrayStr()
    for file in force_set_files:
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

  # Set external loads and coordinates files
  analyze_tool.setExternalLoadsFileName("GRF.xml")  # Replace with your filename
  analyze_tool.setCoordinatesFileName(coordinates_file)

  # Set filter cutoff frequency
  analyze_tool.setLowpassCutoffFrequency(6)

  # Save settings to XML
  analyze_tool.printToXML(os.path.join(results_directory, "analyzeTool_setup.xml"))

  # Return the analysis tool
  return analyze_tool

# Example usage:
coordinates_file = "your_motion_data.trc"
model_path = "your_model.osim"
results_directory = "analysis_results"
force_set_files = ["actuator1_forces.xml", "actuator2_forces.xml"]  # Optional

analysis_tool = create_analysis_tool(coordinates_file, model_path, results_directory, force_set_files)

# Run the analysis
analysis_tool.run()