"""bioscout.simulate.mrs -- the KU Leuven Muscle Redundancy Solver, driven from BioScout.

    from bioscout.simulate.mrs import MRSConfig, run
    cfg = MRSConfig(model_path=..., ik_files=[...], id_files=[...],
                    time=[0.5, 1.8], dof_names=["hip_flexion_r", "knee_angle_r"],
                    out_path=".../mrs")
    run(cfg)

BioScout writes mrs_config.json, MATLAB runs solveMuscleRedundancy through
run_mrs.m, and the resulting MRS_Results.mat is exported to OpenSim .sto files.
The toolbox itself is NOT vendored: clone it and point BIOSCOUT_MRS_DIR at it.
"""
from .config import MRSConfig            # noqa: F401
from .runner import run, check, find_matlab, find_mrs_dir, DRIVER   # noqa: F401
from .io import export, write_sto        # noqa: F401

__all__ = ["MRSConfig", "run", "check", "find_matlab", "find_mrs_dir",
           "export", "write_sto", "DRIVER"]
