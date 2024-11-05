# msk_modelling_python (beta)
Basilio Goncalves, PhD, Univiersity of Vienna
first release 2024

## Usage 

1. create a virtual enviroment 
```sh
python -m venv myenv
```
2. copy this module "msk_modelling_python" to 
```
.\myenv\Lib\site-packages\
 ```
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

## Installation

1. Download a code interpreter (I recommend visual studio code, but do whatever)
https://code.visualstudio.com/download
	
2. Install Rapid Env Editor (optinonal)
https://www.rapidee.com/en/about
	
3. Download and install python (suggest 3.8) - make sure it is the correct bit version
https://www.python.org/downloads/release/python-380/
	
4. Download and install OpenSim (suggest >=4.3)
https://simtk.org/frs/?group_id=91
	
5. Configure OpenSim and Python by running bops.py
    for manual setup of opensim go to https://simtk-confluence.stanford.edu:8443/display/OpenSim/Scripting+in+Python

6. Install ezc3d 
    see ..\guide\steps_install_ezc3d_python.txt

## Examples

Find examples under "ExampleScripts".

## Contributing

Guidelines for contributing to the project.

## License

Information about the project's license.

## Contact

For any questions or inquiries, please contact:

- Name: Basilio Goncalves
- Email: basilio.goncalves@univie.ac.at
- ResearchGate: https://www.researchgate.net/profile/Basilio-Goncalves

## Colaborators
Basilio Goncalves, University of Vienna, basilio.goncalves@univie.ac.at






## OpenBio

[Mendeley for markdown](https://medium.com/@krzysztofczarnecki/i-wrote-my-thesis-in-markdown-heres-how-it-went-3f60140dfe65#id_token=eyJhbGciOiJSUzI1NiIsImtpZCI6IjdkMzM0NDk3NTA2YWNiNzRjZGVlZGFhNjYxODRkMTU1NDdmODM2OTMiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIyMTYyOTYwMzU4MzQtazFrNnFlMDYwczJ0cDJhMmphbTRsamRjbXMwMHN0dGcuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiIyMTYyOTYwMzU4MzQtazFrNnFlMDYwczJ0cDJhMmphbTRsamRjbXMwMHN0dGcuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMTQxMzM1NjM1MDM5NTI1NDkwNDAiLCJlbWFpbCI6ImJhc2lsaW8uZ29uY2FsdmVzN0BnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwibmJmIjoxNjk3ODEyMzU3LCJuYW1lIjoiQmFzw61saW8gR29uw6dhbHZlcyIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKT25sWEhrYkhnM2tIcjRMa3NrOVVYOTZCUHJlcDJBb3FWZ1FKcWZNNS1ZNkhuPXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6IkJhc8OtbGlvIiwiZmFtaWx5X25hbWUiOiJHb27Dp2FsdmVzIiwibG9jYWxlIjoiZW4tR0IiLCJpYXQiOjE2OTc4MTI2NTcsImV4cCI6MTY5NzgxNjI1NywianRpIjoiMDZiOTlmYWVmZGIyMGQ2NTY0OGQyM2MxNzAxYWUxMDllYTY3ODQxZCJ9.AJ8tmPp6w-s2mj-qOy7m9BYS1hTeVMRuORhtYaltN8EV8f5kj-okhRX0tno8bVk5B9cC_leLaHKWN5gx7PTHZMoo5ScS_RiMVpUECXs3tnefpuInedRsCyTK1sDXNgGfTAbR3sXn77ggigavdug0_bTGJtdvQ5aJOarsbAmWc6ELumsyWMjRSRDEtxSzDFYgyj2733AmbGSyWdFuDifsMDQN7nE_mAvRxavypSIojUF0CYVJtwR55f1nUnVqaE1R9YrhvozJdAy26ZFetBH5Tvwtu6Nw0ckPbNBn7vJUz-hkGyT0c7qE-qV98UJyaIBohL92i7woZ5pZc4aqCGPxww)

## Intro 

One of five theoretical models (“the minimum fatigue model,” Dul er al., 198) predicted individual muscle forces adequately. However.

Herzog, W., & Leonard, T. R. (1991). Validation of optimization models that estimate the forces exerted by synergistic muscles. Journal of Biomechanics, 24, 31–39. https://doi.org/https://doi.org/10.1016/0021-9290(91)90375-W

## Open access tool to analyse data in biomechanics

## Example files with metrics and normal data for people to see

### Running annimation

## Basic signal processing

## Statistics 

## OpenSim 

## Muscle modelling 
When $a \ne 0$, there are two solutions to $(ax^2 + bx + c = 0)$ and they are 
$$ x = {-b \pm \sqrt{b^2-4ac} \over 2a} $$

## Uses of muscle modelling

## Aim 


## Code block examples - https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet

 
```python 3.8.10
s = "Python syntax highlighting"
print s
```
