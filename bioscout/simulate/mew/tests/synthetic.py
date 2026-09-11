"""Synthetic end-to-end check. No data, no OpenSim, no bioscout needed.

Builds a toy 2-DOF / 6-muscle "leg", generates a known activation pattern,
computes the moments it produces, then asks the solver to recover the
activations from those moments. If the recovery is good, the MTU model, the
geometry contract and the solver agree with each other.

    python -m bioscout.simulate.mew selftest
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..geometry import GeometryProvider
from ..mtu import MuscleParameters, build_mtu
from ..solver import FrameSolver, MODE_PRESETS


MUSCLES = ["ext_a", "ext_b", "ext_c", "flex_a", "flex_b", "biart"]
DOFS = ["knee_angle_r", "hip_flexion_r"]


class ToyGeometry(GeometryProvider):
    """Analytic moment arms and lengths -- the reference the solver is tested against."""

    source = "toy_analytic"

    def __init__(self):
        self.muscles, self.dofs = list(MUSCLES), list(DOFS)
        #  (ndof, nm) nominal moment arms, m. Last muscle is biarticular.
        self._r0 = np.array([
            [0.045, 0.040, 0.035, -0.038, -0.042, -0.030],   # knee
            [0.010, 0.005, 0.000, 0.055, 0.050, 0.048],      # hip
        ])

    def _q(self, q):
        return np.column_stack([np.deg2rad(q[d].to_numpy(float)) for d in self.dofs])

    def moment_arms(self, q):
        Q = self._q(q)
        # mild, smooth angle dependence -- enough to exercise the machinery
        mod = 1.0 + 0.15 * np.cos(Q)                       # (nt, ndof)
        return self._r0[None, :, :] * mod[:, :, None]

    def mtu_lengths(self, q):
        Q = self._q(q)
        base = np.array([0.42, 0.40, 0.38, 0.44, 0.43, 0.50])
        # length shortens as the joints flex, weighted by the moment arms
        dl = -(Q @ self._r0)
        return base[None, :] + dl

    def parameters(self):
        p = MuscleParameters.defaults(
            MUSCLES,
            f_max=[2500, 1800, 1200, 1600, 1400, 900],
            l_opt=[0.10, 0.09, 0.08, 0.11, 0.10, 0.12],
            l_ts=[0.30, 0.30, 0.29, 0.32, 0.32, 0.37],
        )
        p.source = "toy"
        return p


def make_trial(nt=200, dur=1.0):
    t = np.linspace(0.0, dur, nt)
    q = pd.DataFrame({
        "time": t,
        "knee_angle_r": 35.0 + 25.0 * np.sin(2 * np.pi * t),
        "hip_flexion_r": 20.0 + 15.0 * np.sin(2 * np.pi * t + 0.6),
    })
    return t, q


def selftest(verbose=True) -> int:
    t, q = make_trial()
    g = ToyGeometry()
    params = g.parameters()
    mtu = build_mtu(params)

    l_mt = g.mtu_lengths(q)
    v_mt = np.gradient(l_mt, t, axis=0)
    R = g.moment_arms(q)

    # --- ground truth: a known activation pattern ------------------------
    rng = np.random.default_rng(0)
    phase = np.linspace(0, 2 * np.pi, len(t))
    a_true = np.clip(np.column_stack([
        0.55 * (np.sin(phase) ** 2),
        0.40 * (np.sin(phase + 0.4) ** 2),
        0.25 * (np.sin(phase + 0.8) ** 2),
        0.45 * (np.cos(phase) ** 2),
        0.35 * (np.cos(phase + 0.3) ** 2),
        0.30 * (np.sin(phase + 1.2) ** 2),
    ]) + 0.02, 0.0, 1.0)

    f_true = np.array([mtu.force(a_true[i], mtu.state(l_mt[i], v_mt[i]))
                       for i in range(len(t))])
    M = np.einsum("tdm,tm->td", R, f_true)

    # --- tier 1: static optimisation, moments only ------------------------
    so = FrameSolver(mtu, MODE_PRESETS["static_optimisation"]).solve(
        l_mt, v_mt, R, M)

    # --- tier 2: EMG-informed, electrodes on 3 of 6 muscles ---------------
    emg_mask = np.array([True, False, False, True, False, True])
    a_emg = np.clip(a_true + rng.normal(0, 0.03, a_true.shape), 0, 1)
    ei = FrameSolver(mtu, MODE_PRESETS["emg_informed"]).solve(
        l_mt, v_mt, R, M, a_emg=a_emg, emg_mask=emg_mask)

    def report(name, sol):
        m_res = float(np.mean(np.abs(sol.residual)))
        m_pk = float(np.percentile(np.abs(M), 95))
        a_err = float(np.mean(np.abs(sol.activations - a_true)))
        f_err = float(np.mean(np.abs(sol.forces - f_true)))
        f_scale = float(np.mean(np.abs(f_true))) or 1.0
        if verbose:
            print(f"  {name:22s} residual {m_res:7.3f} Nm ({100*m_res/m_pk:5.2f}% of peak) "
                  f"| activation MAE {a_err:.4f} | force MAE {f_err:7.2f} N "
                  f"({100*f_err/f_scale:5.2f}%) | failed {sol.n_failed}")
        return m_res / m_pk, a_err

    if verbose:
        print("mew selftest -- 6 muscles, 2 DOF, 200 frames")
        print(f"  peak |moment| {np.percentile(np.abs(M), 95):.1f} Nm, "
              f"peak force {f_true.max():.0f} N\n")

    r_so, e_so = report("tier1 static_opt", so)
    r_ei, e_ei = report("tier2 emg_informed", ei)

    ok = True
    checks = [
        ("moment tracking (SO)  < 2% of peak", r_so < 0.02),
        ("moment tracking (EMG) < 5% of peak", r_ei < 0.05),
        ("EMG informing improves activation recovery", e_ei < e_so),
        ("no solver failures", so.n_failed == 0 and ei.n_failed == 0),
        ("forces are non-negative", so.forces.min() >= -1e-9),
        ("activations within bounds", so.activations.min() >= -1e-9
         and so.activations.max() <= 1.0 + 1e-9),
    ]
    if verbose:
        print()
    for label, passed in checks:
        ok &= bool(passed)
        if verbose:
            print(f"  [{'PASS' if passed else 'FAIL'}] {label}")

    # activation recovery is EXPECTED to be imperfect for SO: many activation
    # patterns produce the same joint moment. That degeneracy is precisely what
    # EMG resolves, which is what the third check above is measuring.
    if verbose:
        print(f"\n  {'SELFTEST PASSED' if ok else 'SELFTEST FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
