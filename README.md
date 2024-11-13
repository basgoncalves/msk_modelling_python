# msk_modelling_python (pre-release)

**Author:** Basilio Goncalves, PhD, University of Vienna, 2024

---

## Pre-requisites for Installation

1. **Download a Code Interpreter**  
    I recommend [Visual Studio Code](https://code.visualstudio.com/download), but use your preferred one.

2. **Download and Install Python (suggest 3.8)**  
    Make sure it is the correct bit version: [Python 3.8](https://www.python.org/downloads/release/python-380/)

3. **Download and Install OpenSim (suggest >=4.3)**  
    [OpenSim Downloads](https://simtk.org/frs/?group_id=91)

4. **Install Rapid Env Editor (optional)**  
    [Rapid Env Editor](https://www.rapidee.com/en/about)

---

## Usage

1. **Create a Virtual Environment**
     ```sh
     python -m venv myenv
     ```

2. **Copy this Module "msk_modelling_python" to**
     ```
     .\myenv\Lib\site-packages\msk_modelling_python
     ```
     *Note: Ensure the name of the package is exactly "msk_modelling_python"*

3. **Run OpenSim Setup from Installation Folder**  
    See [OpenSim Scripting in Python](https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python)
     ```sh
     cd 'C:\OpenSim 4.5\sdk\Python'
     python setup_win_python38.py
     python -m pip install .
     ```

4. **Add the Path to the OpenSim Libraries to Your Environment Variables**  
    Add the following paths to your `PATH` variable:
     ```
     C:\OpenSim 4.4\bin
     C:\OpenSim 4.4\lib
     ```

5. **Verify the Installation**
     ```python
     import opensim as osim
     model = osim.Model()
     print("OpenSim model created successfully!")
     ```

6. **Basic Usage**
     ```python
     import msk_modelling_python as msk

     project_path = r'.\'
     msk.bops.StartProject(project_path)

     # Create a folder structure:
     #   .\Project\Subject\Session\Trial1.c3d
     #   .\Project\Subject\Session\Trial2.c3d
     #   .\Project\Subject\Session\static.c3d
     ```

7. **Use Example Scripts**
     Use example scripts in the "ExampleScripts" directory to get started with common tasks and workflows.

---

This package includes a combination of other packages and custom functions to manipulate and analyze biomechanical data. Inspired by the MATLAB version of BOPS (Batch OpenSim Processing Scripts) - [BOPS](https://simtk.org/projects/bops/)

## Tools to be Included:
- **BTK**  
  [BTK Documentation](https://biomechanical-toolkit.github.io/docs/Wrapping/Python/_getting_started.html)
- **c3dServer**  
  [c3dServer](https://www.c3dserver.com/)
- **OpenSim v4.4**  
  [OpenSim Scripting in Python](https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python)
- **3D Slicer**  
  [3D Slicer](https://www.slicer.org/)
- **FEbioStudio**  
  [FEbioStudio](https://febio.org/)
- **MeshLab 2023.12**  
  [MeshLab](https://www.meshlab.net/)

---

## Code Structure

1. **msk_modelling_python**
     This is the main package including all the modules needed for msk modelling, stats, data_processing, etc. This package contains subpackages that can be used independently.

2. **bops**
     Batch Opensim Processing Software  
     Package with functions and classes to use Opensim, CEINMS, stats, and others for easier processing.

3. **ui**
     Functions to create user interface.

---

## Examples

Find examples under "ExampleScripts".

---

## Contact

For any questions or inquiries, please contact:

- **Name:** Basilio Goncalves
- **Email:** basilio.goncalves@univie.ac.at
- **ResearchGate:** [Basilio Goncalves](https://www.researchgate.net/profile/Basilio-Goncalves)







