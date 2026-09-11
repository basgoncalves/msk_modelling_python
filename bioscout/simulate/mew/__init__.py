"""mew (muscle extrapolation web) -- a Python-native, always-answers muscle force estimator.

CEINMS's hybrid EMG-informed solve, rebuilt in numpy/scipy, with a tier ladder
so it returns forces from as little as height + mass + a model + kinematics, and
gets better as GRF, EMG and subject calibration are added.

    from bioscout.simulate.mew import Mew
    ma = Mew(model="Rajagopal2015.osim", height=1.81, mass=78,
             kinematics="joint_angles.mot")
    res = ma.run()
    print(res.summary())          # tier, confidence, moment residual
    res.write_sto("ceinms/Optimised/MuscleForces.sto")

See DESIGN.md for the architecture, the tier ladder and the bioscout
integration plan.

Import discipline: this module and everything it imports at module level depend
on numpy/scipy only. OpenSim, torch and bioscout are optional and confined to
``geometry``, ``ml`` and ``bioscout_adapter``.
"""
__version__ = "0.1.0-draft"

from .types import Tier, SubjectSpec, TrialInputs, MuscleForceResult, Provenance
from .mtu import MuscleParameters, scale_parameters, build_mtu
from .solver import SolverWeights, MODE_PRESETS, solve_trial
from .analyser import Mew
from .pipeline import analyse_trial
from .io_ports import read_storage, write_sto
from .jcf import contact_force_magnitude

__all__ = [
    "Mew", "analyse_trial", "Tier", "SubjectSpec", "TrialInputs",
    "MuscleForceResult", "Provenance", "MuscleParameters",
    "scale_parameters", "build_mtu", "SolverWeights", "MODE_PRESETS",
    "solve_trial", "read_storage", "write_sto", "contact_force_magnitude", "__version__",
]
