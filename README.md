# msk_modelling_python (pre-release)
Basilio Goncalves, PhD, Univiersity of Vienna, 2024


## Pre-requisites for installation

1. Download a code interpreter (I recommend visual studio code, but use your prefered one)
https://code.visualstudio.com/download
	
2. Download and install python (suggest 3.8) - make sure it is the correct bit version
https://www.python.org/downloads/release/python-380/
	
3. Download and install OpenSim (suggest >=4.3)
https://simtk.org/frs/?group_id=91

4. Install Rapid Env Editor (optional)
https://www.rapidee.com/en/about	


## Usage 

1. create a virtual enviroment 
```sh
python -m venv myenv
```
2. copy this module "msk_modelling_python" to 
```
.\myenv\Lib\site-packages\msk_modelling_python
 ```

Note: ensure the name of the package is exactly "msk_modelling_python"


3. Run opensim setup from instalation folder - see https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python 

```sh
cd 'C:\OpenSim 4.5\sdk\Python'
python setup_win_python38.py
python -m pip install .
```
4. Add the path to the OpenSim libraries to your environment variables. This can be done by adding the following paths to your `PATH` variable:
    ```
    C:\OpenSim 4.4\bin
    C:\OpenSim 4.4\lib
    ```
5. Verify the installation by running a simple script to ensure everything is set up correctly:
    ```python
    import opensim as osim
    model = osim.Model()
    print("OpenSim model created successfully!")
    ```

6. Basic usage
    ```python
    import msk_modelling_python as msk

    project_path = r'.\'
    msk.bops.StartProject(peoject_path)

    # Create a folder structure:
    #   .\Project\Subject\Session\Trial1.c3d
    #   .\Project\Subject\Session\Trial2.c3d
    #   .\Project\Subject\Session\static.c3d
    ```

7. Use example scrtips in
    ```markdown
    Use example scripts in the "ExampleScripts" directory to get started with common tasks and workflows.
    ```

This package includes a combination of other packages and custom functions to manipulate and analyse biomechanical data.
Inspired by the MATLAB version of BOPS (Batch OpenSim Processing Scripts) - https://simtk.org/projects/bops/

## Tools to be included:
    - BTK               https://biomechanical-toolkit.github.io/docs/Wrapping/Python/_getting_started.html
    - c3dServer         https://www.c3dserver.com/ 
    - opensim v4.4      https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python 
    - 3D slicer         https://www.slicer.org/
    - FEbioStudio       https://febio.org/
    - MeshLab 2023.12   https://www.meshlab.net/

## Code structure 

1. msk_modelling_python
    ```markdown
    This is the main package including all the modules needed for msk modelling, stats, data_processing, etc.
    This package contains subpackages that can be used independently.
    ```
2. bops
    ```markdown
    Batch Opensim Processing Software

    package with functions and classes to use Opensim, CEINMS, stats, and others to use for easier processing
    ```

3. ui
    ```markdown
    functions to create user interface
    ```

## Examples

Find examples under "ExampleScripts".

## Contact

For any questions or inquiries, please contact:

- Name: Basilio Goncalves
- Email: basilio.goncalves@univie.ac.at
- ResearchGate: https://www.researchgate.net/profile/Basilio-Goncalves







