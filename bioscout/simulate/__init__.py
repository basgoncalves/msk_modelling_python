"""Everything ``bioscout simulate`` backs: things that consume a model and
produce results. Today that is ``mrs/`` (the KU Leuven Muscle Redundancy
Solver, ``bioscout simulate mrs``); the OpenSim/CEINMS pipeline stages still
live in ``bioscout.utils.openSim`` / ``bioscout.utils.ceinms`` until they are
extracted here (docs/RESTRUCTURE_PLAN.md, stage 6).

Nothing is imported eagerly so ``import bioscout.simulate`` stays light.
"""
