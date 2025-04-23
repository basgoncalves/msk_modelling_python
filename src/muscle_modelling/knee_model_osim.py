import os
import json
import time
import pandas as pd
import numpy as np
import opensim as osim
import matplotlib.pyplot as plt
import msk_modelling_python as msk
import matplotlib.pyplot as plt
parent_dir = os.path.dirname(os.getcwd())
start_time = time.time()
################

import vtk

#%% 1. Define functions

def read_vtp_file(filename):
    """
    Reads a VTK PolyData file (.vtp) and returns a vtkPolyData object.
    """
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

def visualise_vtp(vtp_file):
    """
    Visualises a vtkPolyData object.
    """
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(vtp_file)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(0.1, 0.2, 0.4)
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window_interactor = vtk.vtkRenderWindowInteractor()
    render_window_interactor.SetRenderWindow(render_window)
    render_window.Render()
    render_window_interactor.Start()

#% 2 Create models and joints

# Define global model where the leg lives.
leg = osim.Model()
leg.setUseVisualizer(True)

# ---------------------------------------------------------------------------
# Create two links, each with a mass of 1 kg, centre of mass at the body's
# origin, and moments and products of inertia of zero.
# ---------------------------------------------------------------------------
length_femur = 0.5
length_tibia = 1
length_foot = 0.5

femur = osim.Body("femur",
                    length_femur,
                    osim.Vec3(0, 0, 0),
                    osim.Inertia(0, 0, 0))
tibia = osim.Body("tibia",
                   length_tibia,
                   osim.Vec3(0, 0, 0),
                   osim.Inertia(0, 0, 0))

foot = osim.Body("foot",
                    length_foot,
                    osim.Vec3(0, 0, 0),
                    osim.Inertia(0, 0, 0))


# ---------------------------------------------------------------------------
# Connect the bodies with pin joints. Assume each body is 1m long.
# ---------------------------------------------------------------------------

hip = osim.PinJoint("hip",
                    leg.getGround(),  # PhysicalFrame
                    osim.Vec3(0, 0, 0),
                    osim.Vec3(0, 0, 0),
                    femur,  # PhysicalFrame
                    osim.Vec3(0, length_femur, 0),
                    osim.Vec3(0, 0, 0))

knee = osim.PinJoint("knee",
                     femur,  # PhysicalFrame
                     osim.Vec3(0, 0, 0),
                     osim.Vec3(0, 0, 0),
                     tibia,  # PhysicalFrame
                     osim.Vec3(0, length_tibia, 0),
                     osim.Vec3(0, 0, 0))

ankle = osim.PinJoint("ankle",
                        tibia,  # PhysicalFrame
                        osim.Vec3(0, 0, 0),
                        osim.Vec3(0, 0, 0),
                        foot,  # PhysicalFrame
                        osim.Vec3(0, 0.5, 0),
                        osim.Vec3(0, 0, 0))

#%% END