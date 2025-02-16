import msk_modelling_python as msk


ik_setup = r"C:\Git\research_data\Projects\runbops_example_data\simulations\009\pre\Run_baseline1\setup_IK.xml"
model_path = r"C:\Git\research_data\Projects\runbops_example_data\simulations\009\pre\009_Rajagopal2015_FAI.osim"
ikTool = msk.bops.osim.InverseKinematicsTool(ik_setup)
osimModel = msk.bops.osim.Model(model_path) 
                             
state = osimModel.initSystem()
ikTool.setModel(osimModel)



ikTool.run()