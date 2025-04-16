import msk_modelling_python as msk
msk.bops.greet()


joint_forces = msk.bops.read.mot(r"C:\Git\research_data\Projects\runbops_FAIS_phd\simulations\009\pre\sprint_1\joint_reaction_loads.sto")

print(joint_forces.columns)