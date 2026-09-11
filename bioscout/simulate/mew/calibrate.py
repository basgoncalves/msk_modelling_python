"""Subject calibration: fit MTU parameters theta to a subject's own trials.

Same objective as the solver, one level up. The inner loop solves activations
given theta; the outer loop moves theta to make the inner loop's job easier --
smaller moment residual and better EMG agreement.

Bounds are expressed as FRACTIONS of the generic value, matching bioscout's
``session.yaml`` ``calibration:`` block, so an existing calibration config maps
straight across.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from .mtu import MuscleParameters, build_mtu
from .solver import FrameSolver, MODE_PRESETS, SolverWeights


DEFAULT_BOUNDS: Dict[str, Sequence[float]] = {
    # parameter : (low, high) as a multiple of the generic value
    "l_opt":    (0.95, 1.05),
    "l_ts":     (0.95, 1.05),
    "shape_A":  (0.30, 1.00),     # A in [-3, 0): fraction of the generic -1.0
    "strength": (0.50, 2.00),
    "tau_act":  (0.50, 2.00),
}


@dataclass
class CalibrationSpec:
    """What is free, over which trials, and how hard to try."""
    parameters: List[str] = field(
        default_factory=lambda: ["l_opt", "l_ts", "strength", "shape_A"])
    bounds: Dict[str, Sequence[float]] = field(
        default_factory=lambda: dict(DEFAULT_BOUNDS))
    groups: Optional[Dict[str, List[str]]] = None   # muscle group -> muscles
    max_iter: int = 60
    method: str = "L-BFGS-B"                        # or "differential_evolution"
    weights: SolverWeights = field(
        default_factory=lambda: MODE_PRESETS["hybrid"])


def default_groups(muscles: Sequence[str]) -> Dict[str, List[str]]:
    """Group muscles by name stem so calibration fits ~8 numbers, not ~400.

    ``vasmed_r``/``vaslat_r``/``vasint_r`` share a group; left and right stay
    separate (they are genuinely different in a patient population, which is the
    whole point in FAIS).
    """
    groups: Dict[str, List[str]] = {}
    for m in muscles:
        stem = m.rstrip("_rl").rstrip("_")
        stem = "".join(ch for ch in stem if not ch.isdigit())
        side = "_r" if m.endswith("_r") else ("_l" if m.endswith("_l") else "")
        groups.setdefault(stem[:6] + side, []).append(m)
    return groups


@dataclass
class TrialData:
    """One calibration trial, pre-computed so the outer loop never re-reads disk."""
    l_mt: np.ndarray
    v_mt: np.ndarray
    moment_arms: np.ndarray
    moment_target: np.ndarray
    a_emg: Optional[np.ndarray] = None
    emg_mask: Optional[np.ndarray] = None
    name: str = "trial"


def prepare(analyser, trial_names=None) -> List[TrialData]:
    """Run an analyser's input pipeline without solving, to build TrialData."""
    raise NotImplementedError(
        "prepare() is the seam between Mew.run() and calibration. "
        "Refactor Mew.run() to yield its assembled arrays (a "
        "_assemble() method) and call it here -- see DESIGN.md section 7.")


# --------------------------------------------------------------------------- #
#  The outer loop
# --------------------------------------------------------------------------- #
def _pack(params: MuscleParameters, spec: CalibrationSpec, groups):
    """theta vector <-> parameter arrays. Returns (x0, bounds, apply_fn)."""
    keys = list(spec.parameters)
    gnames = list(groups)
    x0, lo, hi = [], [], []
    for k in keys:
        b = spec.bounds.get(k, (0.9, 1.1))
        for _ in gnames:
            x0.append(1.0)
            lo.append(float(b[0]))
            hi.append(float(b[1]))
    base = params.copy()

    def apply(x):
        out = base.copy()
        idx = {m: i for i, m in enumerate(out.names)}
        p = 0
        for k in keys:
            arr = getattr(out, k).copy()
            for g in gnames:
                for m in groups[g]:
                    if m in idx:
                        arr[idx[m]] = getattr(base, k)[idx[m]] * x[p]
                p += 1
            setattr(out, k, arr)
        out.source = "calibrated"
        return out

    return np.array(x0), list(zip(lo, hi)), apply


def objective(params, trials: List[TrialData], weights, tendon="rigid") -> float:
    """Total cost across trials: normalised moment residual + EMG disagreement."""
    mtu = build_mtu(params, tendon=tendon)
    solver = FrameSolver(mtu, weights)
    total = 0.0
    for t in trials:
        sol = solver.solve(t.l_mt, t.v_mt, t.moment_arms, t.moment_target,
                           a_emg=t.a_emg, emg_mask=t.emg_mask)
        scale = np.maximum(np.percentile(np.abs(t.moment_target), 95, axis=0), 1e-6)
        total += float(np.mean((sol.residual / scale) ** 2))
        if t.a_emg is not None and t.emg_mask is not None and t.emg_mask.any():
            d = (sol.activations - t.a_emg)[:, t.emg_mask]
            total += weights.gamma / 100.0 * float(np.mean(d ** 2))
    return total / max(len(trials), 1)


def calibrate(params: MuscleParameters, trials: List[TrialData],
              spec: Optional[CalibrationSpec] = None, *, tendon="rigid",
              verbose=True) -> MuscleParameters:
    """Fit theta. Returns calibrated MuscleParameters; save with :func:`save`."""
    from scipy.optimize import minimize, differential_evolution

    spec = spec or CalibrationSpec()
    groups = spec.groups or default_groups(params.names)
    x0, bounds, apply = _pack(params, spec, groups)

    n_eval = {"n": 0}

    def cost(x):
        n_eval["n"] += 1
        c = objective(apply(x), trials, spec.weights, tendon=tendon)
        if verbose and n_eval["n"] % 10 == 0:
            print(f"  [{n_eval['n']:4d}]  cost = {c:.6f}")
        return c

    if spec.method == "differential_evolution":
        res = differential_evolution(cost, bounds, maxiter=spec.max_iter,
                                     polish=True, seed=0)
    else:
        res = minimize(cost, x0, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": spec.max_iter})

    out = apply(res.x)
    out.source = f"calibrated:{spec.method}(cost={float(res.fun):.5f})"
    if verbose:
        print(f"calibration finished: cost {float(res.fun):.6f} "
              f"after {n_eval['n']} evaluations")
    return out


def save(params: MuscleParameters, path) -> str:
    path = str(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(params.to_dict(), fh, indent=2)
    return path


def load(path) -> MuscleParameters:
    with open(str(path), "r", encoding="utf-8") as fh:
        return MuscleParameters.from_dict(json.load(fh))
