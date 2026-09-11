"""The one solver. Static optimisation, EMG-informed and hybrid are weights.

Objective, per frame, over activations ``a`` in [0,1]^nm:

    J(a) = alpha * || W (R F(a) - M_target) ||^2      moment tracking
         + beta  * || a ||^2                          effort
         + gamma * || S (a - a_emg) ||^2              EMG tracking (mapped muscles)
         + delta * || a - a_prev ||^2                 temporal smoothing
         + eps   * || a - a_prior ||^2                ML / warm-start prior

With a rigid tendon, F(a) = gain * a + passive is AFFINE in a, so the whole
objective is a bounded linear least squares -- microseconds per frame via
``scipy.optimize.lsq_linear``. That is the fast path and the default.

Residual actuators: the moment a solution cannot produce is reported rather
than forced. A large residual is the honest signal that the model could not
explain the data, and it is what drives the confidence score down.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .mtu import RigidTendonMTU


@dataclass
class SolverWeights:
    """Weights ARE the mode. See MODE_PRESETS."""
    alpha: float = 100.0     # track ID moments
    beta: float = 1.0        # minimise effort
    gamma: float = 0.0       # track EMG
    delta: float = 0.5       # temporal smoothing
    eps: float = 0.0         # ML / prior tracking
    activation_power: int = 2

    def as_dict(self):
        return {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma,
                "delta": self.delta, "eps": self.eps}


MODE_PRESETS = {
    # bioscout's session.yaml alpha/beta/gamma convention maps straight onto this
    "static_optimisation": SolverWeights(alpha=100.0, beta=1.0, gamma=0.0),
    "emg_informed":        SolverWeights(alpha=100.0, beta=1.0, gamma=30.0),
    "emg_driven":          SolverWeights(alpha=0.0, beta=0.0, gamma=1000.0),
    "hybrid":              SolverWeights(alpha=100.0, beta=0.5, gamma=100.0),
}


@dataclass
class SolveResult:
    activations: np.ndarray       # (nt, nm)
    forces: np.ndarray            # (nt, nm)  total tendon force
    residual: np.ndarray          # (nt, ndof) generalised force the muscles did not make
    n_failed: int = 0
    method: str = "lsq_linear"
    #: Per-frame MTU state, all (nt, nm). Collected during the solve because
    #: recomputing it afterwards would re-derive the elastic-tendon equilibrium
    #: at a DIFFERENT activation than the one that produced these forces.
    series: Dict[str, np.ndarray] = field(default_factory=dict)


class FrameSolver:
    """Solve one trial frame by frame, warm-starting from the previous frame."""

    def __init__(self, mtu: RigidTendonMTU, weights: SolverWeights,
                 dof_weights: Optional[np.ndarray] = None,
                 max_force_scale: float = 1.0, passes: Optional[int] = None,
                 tol: float = 1e-3):
        self.mtu = mtu
        self.w = weights
        self.dof_weights = dof_weights
        self.max_force_scale = float(max_force_scale)
        # With an elastic tendon the fibre length depends on activation, so the
        # linearisation must be iterated to convergence. Rigid tendons are exact
        # in one pass, so iterating them would be pure waste.
        self.passes = int(passes if passes is not None
                          else (4 if getattr(mtu, "activation_dependent", False) else 1))
        self.tol = float(tol)

    # ------------------------------------------------------------------ #
    def solve(self, l_mt, v_mt, moment_arms, moment_target,
              a_emg=None, emg_mask=None, a_prior=None, dt=None) -> SolveResult:
        """
        Parameters
        ----------
        l_mt          (nt, nm)        MTU lengths (m)
        v_mt          (nt, nm)        MTU velocities (m/s)
        moment_arms   (nt, ndof, nm)  moment arms (m)
        moment_target (nt, ndof)      moments to track (Nm)
        a_emg         (nt, nm)        EMG-derived activation, or None
        emg_mask      (nm,) bool      which muscles EMG actually informs
        a_prior       (nt, nm)        ML prior, or None
        """
        from scipy.optimize import lsq_linear

        l_mt = np.asarray(l_mt, float)
        nt, nm = l_mt.shape
        # frame time step, needed to turn the change in equilibrium fibre length
        # into a fibre VELOCITY when the tendon is compliant
        self._dt = float(dt) if dt else None
        ndof = moment_arms.shape[1]
        w = self.w

        dw = (np.ones(ndof) if self.dof_weights is None
              else np.asarray(self.dof_weights, float))
        # Normalise the moment term so alpha means the same thing at the ankle
        # and the hip -- without this, big-moment DOFs silently dominate.
        m_scale = np.maximum(np.percentile(np.abs(moment_target), 95, axis=0), 1.0)
        dw = dw / m_scale

        if a_emg is None:
            a_emg = np.zeros((nt, nm))
        if emg_mask is None:
            emg_mask = np.zeros(nm, dtype=bool)
        s_emg = np.where(np.asarray(emg_mask, bool), 1.0, 0.0)
        use_prior = a_prior is not None and w.eps > 0

        acts = np.zeros((nt, nm))
        forces = np.zeros((nt, nm))
        residual = np.zeros((nt, ndof))
        series = {k: np.zeros((nt, nm)) for k in
                  ("fibre_length", "norm_fibre_length", "tendon_length",
                   "norm_tendon_length", "mtu_length", "norm_fibre_velocity",
                   "pennation", "force_active", "force_passive")}
        a_prev = np.full(nm, 0.02)
        l_m_prev = None
        dt = float(np.median(np.diff(np.arange(nt)))) if nt > 1 else 1.0
        n_failed = 0
        n_passes_used = 0
        p_lts = self.mtu.p.l_ts

        sa, sb = np.sqrt(w.alpha), np.sqrt(w.beta)
        sg, sd, se = np.sqrt(w.gamma), np.sqrt(w.delta), np.sqrt(w.eps)

        for i in range(nt):
            R = moment_arms[i]                                    # (ndof, nm)
            a = a_prev.copy()
            st = None

            for _pass in range(self.passes):
                st = self.mtu.state(l_mt[i], v_mt[i], a=a,
                                    l_m_prev=l_m_prev, dt=self._dt)
                gain = st.gain * self.max_force_scale

                # --- moment block: R (gain*a + passive) ~ M  ->  A a ~ b
                A_mom = (R * gain[None, :]) * dw[:, None]
                b_mom = (moment_target[i] - R @ st.passive) * dw

                blocks = [sa * A_mom]
                rhs = [sa * b_mom]

                blocks.append(sb * np.eye(nm))                    # effort
                rhs.append(np.zeros(nm))

                if w.gamma > 0 and s_emg.any():                   # EMG tracking
                    blocks.append(sg * np.diag(s_emg))
                    rhs.append(sg * s_emg * a_emg[i])

                if w.delta > 0:                                   # smoothing
                    blocks.append(sd * np.eye(nm))
                    rhs.append(sd * a_prev)

                if use_prior:                                     # ML prior
                    blocks.append(se * np.eye(nm))
                    rhs.append(se * a_prior[i])

                try:
                    sol = lsq_linear(np.vstack(blocks), np.concatenate(rhs),
                                     bounds=(0.0, 1.0), max_iter=200)
                    a_new = np.clip(sol.x, 0.0, 1.0)
                except Exception:
                    n_failed += 1
                    a_new = a_prev.copy()

                n_passes_used += 1
                converged = np.max(np.abs(a_new - a)) < self.tol
                a = a_new
                if converged:
                    break

            # rebuild the state at the ACCEPTED activation so the reported force
            # is the converged one, not the one from the last linearisation point
            st = self.mtu.state(l_mt[i], v_mt[i], a=a, l_m_prev=l_m_prev,
                                dt=self._dt)
            f = self.mtu.force(a, st) * self.max_force_scale
            acts[i] = a
            forces[i] = f
            residual[i] = moment_target[i] - R @ f

            series["fibre_length"][i] = st.l_m
            series["norm_fibre_length"][i] = st.l_norm
            series["tendon_length"][i] = st.l_t
            series["norm_tendon_length"][i] = st.l_t / np.maximum(p_lts, 1e-9)
            series["mtu_length"][i] = st.l_mt
            series["norm_fibre_velocity"][i] = st.v_norm
            series["pennation"][i] = np.arccos(np.clip(st.cos_pen, -1.0, 1.0))
            series["force_active"][i] = a * st.gain * self.max_force_scale
            series["force_passive"][i] = st.passive * self.max_force_scale

            a_prev = a
            l_m_prev = st.l_m

        return SolveResult(
            activations=acts, forces=forces, residual=residual,
            n_failed=n_failed,
            method=f"lsq_linear x{n_passes_used / max(nt, 1):.1f} passes/frame",
            series=series)


def solve_trial(mtu, l_mt, v_mt, moment_arms, moment_target, *,
                mode="emg_informed", weights=None, a_emg=None, emg_mask=None,
                a_prior=None, dof_weights=None, dt=None) -> SolveResult:
    """Convenience wrapper: pick a preset (or pass explicit weights) and solve."""
    w = weights or MODE_PRESETS.get(mode)
    if w is None:
        raise ValueError(f"unknown mode {mode!r}; try {sorted(MODE_PRESETS)}")
    return FrameSolver(mtu, w, dof_weights=dof_weights).solve(
        l_mt, v_mt, moment_arms, moment_target,
        a_emg=a_emg, emg_mask=emg_mask, a_prior=a_prior, dt=dt)
