"""Optional ML layers. Torch is not required for anything else in the package.

Three distinct jobs, deliberately kept apart:

1. ``SurrogateSolver``  -- predict activations/forces directly. Fast; used as a
   warm start (``Mew.ml_prior``, solver weight ``eps``) or, at the
   extreme, in place of the solve for real-time use.
2. ``GRFPredictor``     -- predict ground reaction forces from kinematics + mass,
   so tier 0 can become a real inverse dynamics instead of a template.
3. ``ActivationPredictor`` -- predict missing EMG channels from the ones present.

All three train on the SAME labels: tier-3 (or CEINMS) output from trials that
DID have every input. That is the loop that makes the offline pipeline generate
its own real-time model.

``FAIS_machine_learning/code/ml_model.py`` is the working prototype of (1); the
intent is that it moves in here as ``SurrogateSolver`` rather than living as a
parallel script.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np


def torch_available() -> bool:
    try:
        import torch                                     # noqa: F401,WPS433
        return True
    except ImportError:
        return False


class MLLayer:
    """Common interface: everything is optional and says so if it is not trained."""

    name = "abstract"
    trained = False

    def require_trained(self):
        if not self.trained:
            raise RuntimeError(
                f"{self.name} is not trained. Train it on trials that have every "
                "input (tier 3), then reuse it where inputs are missing.")


class SurrogateSolver(MLLayer):
    """Predict activations (and hence forces) from kinematics + moments + EMG.

    Used as a PRIOR by default rather than a replacement: the physics solver
    still runs, warm-started, and the moment residual still tells you whether
    the prediction was any good. That keeps the ML honest -- a surrogate that
    drifts shows up as a rising residual instead of as plausible-looking forces.
    """

    name = "surrogate_solver"

    def __init__(self, model=None, muscles: Optional[Sequence[str]] = None):
        self.model = model
        self.muscles = list(muscles) if muscles else []
        self.trained = model is not None

    def activations(self, q, muscles: List[str], times: np.ndarray) -> np.ndarray:
        self.require_trained()
        raise NotImplementedError(
            "Port MachineLearningModel from FAIS_machine_learning/code/ml_model.py "
            "here: it already builds (X, y) from bioscout trial folders and "
            "predicts CEINMS forces. Predict ACTIVATIONS rather than forces so "
            "the output feeds the solver's `a_prior` directly.")

    @classmethod
    def from_fais_model(cls, pickle_path):
        """Load the existing FAIS ml_model.py pickle. Bridge while porting."""
        raise NotImplementedError("bridge to ml_model.MachineLearningModel.load()")


class GRFPredictor(MLLayer):
    """Kinematics + mass -> ground reaction forces -> real inverse dynamics.

    The single highest-value model in the package: it is what turns a
    camera-only capture from tier 0 into tier 1.
    """

    name = "grf_predictor"

    def __init__(self, model=None):
        self.model = model
        self.trained = model is not None

    def grf(self, q, subject) -> "object":
        self.require_trained()
        raise NotImplementedError

    def moments(self, times, dofs, inputs, subject) -> np.ndarray:
        """Signature matches tiers.MomentSource so it plugs straight in."""
        self.require_trained()
        raise NotImplementedError(
            "predict GRF, write a temporary grf.mot + GRF.xml, then call "
            "bioscout.simulate.opensim.run_id -- or implement ID directly here.")


class ActivationPredictor(MLLayer):
    """Fill in muscles with no electrode from the channels that do exist."""

    name = "activation_predictor"

    def __init__(self, model=None):
        self.model = model
        self.trained = model is not None

    def fill(self, a_emg: np.ndarray, mask: np.ndarray) -> np.ndarray:
        self.require_trained()
        raise NotImplementedError
