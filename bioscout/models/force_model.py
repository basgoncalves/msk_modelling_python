"""
Loader for the FAIS muscle-force / joint-reaction surrogate.

The model is trained in the ``FAIS_machine_learning`` repo
(``code/machine_learning/``) and shipped here as a pickle of plain numpy
arrays, so bioscout never needs torch to use it.

Why this module exists
----------------------
The model it supersedes, ``kinematics_only_model.pkl``, was exported from a
BatchNorm residual network as bare ``W1 b1 W2 b2``, dropping the running
statistics. The forward pass it left behind is correct at exactly one point --
the training mean, where the weight path vanishes -- and diverges everywhere
else: 1,110 N at the mean, 32,583 N one standard deviation away, 113,250 N on a
real trial from its own training set. ``shot_analysis`` reimplemented that same
two-layer pass inline, and so inherited the fault.

The replacement has no BatchNorm. Every layer is a pure function of one sample
(Linear, LayerNorm, ReLU), so ``forward`` below is the arithmetic the network
was trained with rather than a reconstruction of it, and ``self_test`` checks
that on load.

Units
-----
Targets are **bodyweight**: ``force / (mass_kg * 9.80665)``. Muscle forces are
converted to newtons by :func:`predict`; joint reaction forces are left in
bodyweight, which is how joint loading is normally reported.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

G = 9.80665

# Physiological ceilings used by the sanity check, in bodyweight.
MAX_MUSCLE_BW = 12.0
MAX_JRF_BW = 20.0


class ForceModelError(RuntimeError):
    """The model file is unusable -- wrong format, or it fails its own check."""


# ── loading ───────────────────────────────────────────────────────────────────

def load(path):
    """Load a trained bundle and verify it before returning it.

    A model that cannot predict a sane force at its own training mean is broken
    in the way the previous one was, and refusing it here is the whole point.
    """
    path = Path(path)
    with open(path, "rb") as fh:
        bundle = pickle.load(fh)

    missing = {"weights", "feature_names", "target_names", "inputs"} - set(bundle)
    if missing:
        raise ForceModelError(
            f"{path.name} is not a FAIS surrogate bundle (missing {sorted(missing)}). "
            "The pre-2026-09 kinematics_only_model.pkl has this shape and is known "
            "to be broken -- retrain and re-export from FAIS_machine_learning.")

    peak = self_test(bundle)
    if peak > MAX_MUSCLE_BW:
        raise ForceModelError(
            f"{path.name} predicts {peak:.0f} bodyweight of muscle force at its own "
            f"training mean; the file does not match the network it came from.")
    return bundle


def self_test(bundle):
    """Peak predicted muscle force, in bodyweight, at the training mean."""
    w = bundle["weights"]
    y = forward(bundle, w["x_mean"][None, :])
    idx = muscle_indices(bundle)
    return float(np.abs(y[:, idx]).max())


# ── the network ───────────────────────────────────────────────────────────────

def _layernorm(x, w, b, eps=1e-5):
    mu = x.mean(axis=-1, keepdims=True)
    var = x.var(axis=-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * w + b


def forward(bundle, X):
    """Raw features -> targets in bodyweight units. X is (n_frames, n_features)."""
    w = bundle["weights"]
    X = np.asarray(X, dtype=np.float64)
    if X.shape[1] != len(w["x_mean"]):
        raise ForceModelError(
            f"expected {len(w['x_mean'])} features, got {X.shape[1]}")
    z = (X - w["x_mean"]) / np.where(np.abs(w["x_std"]) < 1e-12, 1.0, w["x_std"])
    h = np.maximum(0.0, z @ w["stem_W"] + w["stem_b"])
    for blk in w["blocks"]:
        n = _layernorm(h, blk["norm_w"], blk["norm_b"])
        n = np.maximum(0.0, n @ blk["fc1_W"] + blk["fc1_b"])
        h = h + n @ blk["fc2_W"] + blk["fc2_b"]
    h = _layernorm(h, w["norm_w"], w["norm_b"])
    return (h @ w["head_W"] + w["head_b"]) * w["y_std"] + w["y_mean"]


# ── target and feature bookkeeping ────────────────────────────────────────────

def muscle_names(bundle):
    """The 80 muscle outputs, in order."""
    return [t for t in bundle["target_names"] if not t.startswith(("hip_", "knee_", "ankle_"))]


def jrf_names(bundle):
    """The six joint reaction magnitudes."""
    return [t for t in bundle["target_names"] if t.endswith("_mag")]


def muscle_indices(bundle):
    names = set(muscle_names(bundle))
    return [i for i, t in enumerate(bundle["target_names"]) if t in names]


def jrf_indices(bundle):
    names = set(jrf_names(bundle))
    return [i for i, t in enumerate(bundle["target_names"]) if t in names]


def coordinate_names(bundle):
    """Every joint coordinate the model reads, whether as a position or not."""
    seen = []
    for f in bundle["feature_names"]:
        for pre in ("q_", "qd_", "qdd_"):
            if f.startswith(pre) and f[len(pre):] not in seen:
                seen.append(f[len(pre):])
    return seen


# ── prediction ────────────────────────────────────────────────────────────────

def _derivative(v, t):
    """Central difference, one-sided at the ends."""
    out = np.zeros_like(v)
    n = len(t)
    for i in range(n):
        i0, i1 = max(0, i - 1), min(n - 1, i + 1)
        dt = t[i1] - t[i0]
        out[i] = (v[i1] - v[i0]) / dt if dt > 0 else 0.0
    return out


def build_features(bundle, coords, times, mass_kg, height_m):
    """Assemble the feature matrix from measured coordinate series.

    Coordinates that were not supplied are held at the model's TRAINING MEAN,
    and so are their derivatives. Zero is not a neutral choice: it is itself an
    extrapolation for a coordinate whose mean is nowhere near it.

    Returns (X, missing, out_of_range) where `out_of_range` maps a supplied
    coordinate to how many training standard deviations its worst frame sits
    from the training mean -- the number that says whether an answer is an
    estimate or an extrapolation.
    """
    w = bundle["weights"]
    feat = list(bundle["feature_names"])
    times = np.asarray(times, dtype=np.float64)
    n = len(times)

    series = {}
    for name, values in coords.items():
        v = np.asarray(values, dtype=np.float64)
        if v.shape[0] != n:
            v = np.interp(times, np.linspace(times[0], times[-1], v.shape[0]), v)
        d = _derivative(v, times)
        series[name] = {"q": v, "qd": d, "qdd": _derivative(d, times)}

    X = np.tile(w["x_mean"], (n, 1))
    missing, out_of_range = [], {}
    for j, f in enumerate(feat):
        if f == "mass_kg":
            X[:, j] = mass_kg
            continue
        if f == "height_m":
            X[:, j] = height_m
            continue
        for pre, kind in (("qdd_", "qdd"), ("qd_", "qd"), ("q_", "q")):
            if f.startswith(pre):
                base = f[len(pre):]
                if base in series:
                    X[:, j] = series[base][kind]
                    if kind == "q":
                        sd = max(abs(w["x_std"][j]), 1e-9)
                        out_of_range[base] = float(
                            np.abs(X[:, j] - w["x_mean"][j]).max() / sd)
                elif kind == "q" and base not in missing:
                    missing.append(base)
                break
    return X, missing, out_of_range


def predict(bundle, coords, times, mass_kg, height_m=1.75):
    """Muscle forces in newtons and joint reaction forces in bodyweight.

    `coords` maps OpenSim coordinate names (Rajagopal conventions, degrees for
    rotations and metres for translations) to per-frame series; `times` is in
    seconds and must be real, because velocity and acceleration are
    differentiated from it.
    """
    X, missing, out_of_range = build_features(bundle, coords, times, mass_kg, height_m)
    y = forward(bundle, X)
    mi, ji = muscle_indices(bundle), jrf_indices(bundle)
    forces = y[:, mi] * mass_kg * G
    return {
        "muscle_names": muscle_names(bundle),
        "muscle_forces_N": forces,
        "jrf_names": jrf_names(bundle),
        "jrf_BW": y[:, ji],
        "missing_coords": missing,
        "sigma_from_training_mean": out_of_range,
        "implausible_fraction": float((np.abs(y[:, mi]) > MAX_MUSCLE_BW).mean()),
    }
