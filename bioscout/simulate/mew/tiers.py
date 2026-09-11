"""Tier selection and moment sources -- the "always answers" machinery.

A missing input does not change the code path; it changes a weight and raises a
flag. What it CAN change is where the joint moments come from, and that is what
:class:`MomentSource` makes explicit.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .types import Tier, TrialInputs
from .solver import MODE_PRESETS, SolverWeights


# --------------------------------------------------------------------------- #
#  Where the moments come from
# --------------------------------------------------------------------------- #
class MomentSource:
    """Joint moments to track. Every implementation states what it really is."""

    name = "abstract"
    confidence_factor = 1.0

    def moments(self, times: np.ndarray, dofs: List[str],
                inputs: TrialInputs, subject) -> np.ndarray:
        raise NotImplementedError


class MeasuredGRFMoments(MomentSource):
    """Real inverse dynamics from measured GRF -- the only fully trustworthy source."""

    name = "measured_id"

    def moments(self, times, dofs, inputs, subject):
        from .io_ports import as_frame, resample
        df = resample(as_frame(inputs.moments, "moments"), times)
        cols = _match_moment_columns(df, dofs)
        out = np.zeros((len(times), len(dofs)))
        for j, c in enumerate(cols):
            if c is not None:
                out[:, j] = df[c].to_numpy(float)
        return out


class PredictedGRFMoments(MomentSource):
    """GRF predicted from kinematics + mass, then inverse dynamics.

    The route to camera-only estimation. Needs a trained predictor from
    :mod:`mew.ml`; raises a clear error rather than guessing.
    """

    name = "predicted_grf"
    confidence_factor = 0.6

    def __init__(self, predictor=None):
        self.predictor = predictor

    def moments(self, times, dofs, inputs, subject):
        if self.predictor is None:
            raise RuntimeError(
                "PredictedGRFMoments needs a trained predictor. Train one with "
                "mew.ml.GRFPredictor, or fall back to "
                "ScaledTemplateMoments.")
        return self.predictor.moments(times, dofs, inputs, subject)


class ScaledTemplateMoments(MomentSource):
    """Mass- and height-scaled normative moment curves for the detected task.

    Deliberately crude: it exists so tier 0 returns SOMETHING rather than
    failing, and its confidence factor says so. Never present a tier-0 result as
    a measurement.
    """

    name = "scaled_template"
    confidence_factor = 0.3

    #  peak moment, normalised to body mass (Nm/kg), sign = the dominant
    #  direction over the cycle. Order-of-magnitude values from the gait
    #  literature; replace with your own normative set when you have one.
    TEMPLATES = {
        "walking": {"hip_flexion": -0.9, "hip_adduction": -0.9, "knee_angle": 0.5,
                    "ankle_angle": -1.5, "lumbar_extension": 0.4},
        "running": {"hip_flexion": -2.2, "hip_adduction": -1.8, "knee_angle": 1.8,
                    "ankle_angle": -3.0, "lumbar_extension": 0.8},
        "squat":   {"hip_flexion": -1.6, "knee_angle": 1.4, "ankle_angle": -0.7},
    }

    def moments(self, times, dofs, inputs, subject):
        mass = subject.mass or 75.0
        task = (inputs.trial_type or "walking").lower()
        template = next((v for k, v in self.TEMPLATES.items() if k in task),
                        self.TEMPLATES["walking"])
        phase = np.linspace(0.0, 1.0, len(times))
        shape = np.sin(np.pi * phase) ** 2          # one smooth bell over the trial
        out = np.zeros((len(times), len(dofs)))
        for j, d in enumerate(dofs):
            base = d.rsplit("_", 1)[0] if d.endswith(("_r", "_l")) else d
            peak = template.get(base, template.get(d, 0.0))
            out[:, j] = peak * mass * shape
        return out


def _match_moment_columns(df: pd.DataFrame, dofs: List[str]) -> List[Optional[str]]:
    """Map DOF names to ID column names (``hip_flexion_r`` -> ``hip_flexion_r_moment``)."""
    lower = {c.lower(): c for c in df.columns}
    out = []
    for d in dofs:
        for cand in (f"{d}_moment", f"{d}_force", d):
            if cand.lower() in lower:
                out.append(lower[cand.lower()])
                break
        else:
            out.append(None)
    return out


# --------------------------------------------------------------------------- #
#  Tier selection
# --------------------------------------------------------------------------- #
def select_tier(inputs: TrialInputs, subject, *, pin: Optional[Tier] = None
                ) -> Tuple[Tier, MomentSource, SolverWeights, List[str]]:
    """Highest tier the inputs support, plus the moment source, weights, warnings.

    ``pin`` forces a tier; if the inputs cannot support it, that is an error --
    silently running a lower tier than asked for is exactly the failure mode
    this package exists to avoid.
    """
    have = inputs.available()
    warnings: List[str] = []

    if not have["kinematics"]:
        raise ValueError("kinematics are required -- nothing can run without q(t)")

    calibrated = bool(getattr(subject, "theta_file", None))
    if have["moments"]:
        source: MomentSource = MeasuredGRFMoments()
        if have["emg"]:
            tier = Tier.CALIBRATED_HYBRID if calibrated else Tier.EMG_INFORMED
            if not calibrated:
                warnings.append(
                    "no calibrated parameters: using generic height/mass-scaled "
                    "MTU parameters (run mew.calibrate for tier 3)")
        else:
            tier = Tier.STATIC_OPT
            warnings.append("no usable EMG (or no emg_map): running static "
                            "optimisation, muscle sharing is a minimum-effort assumption")
    else:
        tier = Tier.KINEMATICS_ONLY
        source = ScaledTemplateMoments()
        warnings.append(
            "no inverse-dynamics moments: joint moments come from a scaled "
            "normative template. Treat forces as indicative only.")
        if have["grf"]:
            warnings.append("GRF is present but inverse_dynamics.sto is not -- "
                            "run ID first to reach tier 1.")

    if pin is not None:
        pin = Tier(pin)
        if pin > tier:
            raise ValueError(
                f"tier {pin.label} was pinned but the inputs only support "
                f"{tier.label}. Missing: "
                f"{[k for k, v in have.items() if not v]}")
        if pin < tier:
            warnings.append(
                f"tier pinned to {pin.label} (inputs supported {tier.label}); "
                "available inputs were deliberately ignored")
        tier = pin
        # Pinning DOWN must also drop the moment source, or "tier 0" would
        # silently keep the measured inverse dynamics and the degradation curve
        # would be meaningless.
        if tier == Tier.KINEMATICS_ONLY and source.name == "measured_id":
            source = ScaledTemplateMoments()

    weights = {
        Tier.KINEMATICS_ONLY: MODE_PRESETS["static_optimisation"],
        Tier.STATIC_OPT: MODE_PRESETS["static_optimisation"],
        Tier.EMG_INFORMED: MODE_PRESETS["emg_informed"],
        Tier.CALIBRATED_HYBRID: MODE_PRESETS["hybrid"],
    }[tier]

    if tier == Tier.KINEMATICS_ONLY:
        # do not let the solver chase a template as if it were a measurement
        weights = SolverWeights(alpha=10.0, beta=1.0, gamma=0.0, delta=1.0)

    return tier, source, weights, warnings


def score_confidence(tier: Tier, source: MomentSource, residual, target,
                     n_failed=0, n_frames=1) -> float:
    """Tier prior x moment-source factor x how much moment went unexplained."""
    c = tier.nominal_confidence * source.confidence_factor
    if residual is not None and target is not None:
        scale = np.maximum(np.percentile(np.abs(target), 95, axis=0), 1e-6)
        rel = float(np.mean(np.abs(residual) / scale))
        c *= float(np.clip(1.0 - 2.0 * rel, 0.05, 1.0))
    if n_failed:
        c *= float(np.clip(1.0 - n_failed / max(n_frames, 1), 0.0, 1.0))
    return float(np.clip(c, 0.0, 1.0))
