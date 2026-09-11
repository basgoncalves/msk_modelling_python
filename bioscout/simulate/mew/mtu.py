"""Hill-type muscle-tendon unit: activation dynamics and force generation.

numpy only. Everything is vectorised over muscles, so one call evaluates the
whole model at one frame (or, where noted, all frames at once).

Default is a RIGID TENDON, which makes muscle force a closed-form function of
``(l_mt, v_mt, a)`` with no per-frame root-find. That is what keeps the solver
linear-in-activation (see solver.py) and the real-time path viable. An elastic
tendon path is provided for offline accuracy work.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence

import numpy as np


# --------------------------------------------------------------------------- #
#  Parameters
# --------------------------------------------------------------------------- #
@dataclass
class MuscleParameters:
    """The vector theta. One entry per muscle, arrays ordered like ``names``."""
    names: List[str]
    f_max: np.ndarray            # maximum isometric force (N)
    l_opt: np.ndarray            # optimal fibre length (m)
    l_ts: np.ndarray             # tendon slack length (m)
    alpha_0: np.ndarray          # pennation angle at optimal fibre length (rad)
    v_max: np.ndarray            # maximum contraction velocity (l_opt/s)
    tau_act: np.ndarray          # activation time constant (s)
    tau_deact: np.ndarray        # deactivation time constant (s)
    shape_A: np.ndarray          # EMG-to-activation nonlinearity, -3..0
    strength: np.ndarray         # group strength coefficient (multiplies f_max)
    source: str = "model_default"

    @property
    def n(self) -> int:
        return len(self.names)

    def index(self, muscle) -> int:
        return self.names.index(muscle)

    def subset(self, names: Sequence[str]) -> "MuscleParameters":
        idx = [self.names.index(m) for m in names]
        return MuscleParameters(
            names=list(names),
            **{k: getattr(self, k)[idx] for k in
               ("f_max", "l_opt", "l_ts", "alpha_0", "v_max",
                "tau_act", "tau_deact", "shape_A", "strength")},
            source=self.source)

    def copy(self) -> "MuscleParameters":
        return replace(self, names=list(self.names),
                       **{k: np.array(getattr(self, k), dtype=float) for k in
                          ("f_max", "l_opt", "l_ts", "alpha_0", "v_max",
                           "tau_act", "tau_deact", "shape_A", "strength")})

    @classmethod
    def defaults(cls, names: Sequence[str], f_max=None, l_opt=None,
                 l_ts=None, alpha_0=None) -> "MuscleParameters":
        """Generic parameters; used when a value cannot be read from the model."""
        n = len(names)
        ones = np.ones(n)
        return cls(
            names=list(names),
            f_max=np.asarray(f_max, float) if f_max is not None else 1000.0 * ones,
            l_opt=np.asarray(l_opt, float) if l_opt is not None else 0.10 * ones,
            l_ts=np.asarray(l_ts, float) if l_ts is not None else 0.20 * ones,
            alpha_0=np.asarray(alpha_0, float) if alpha_0 is not None else 0.0 * ones,
            v_max=10.0 * ones,
            tau_act=0.015 * ones,
            tau_deact=0.050 * ones,
            shape_A=-1.0 * ones,
            strength=1.0 * ones,
        )

    def to_dict(self) -> dict:
        return {"names": list(self.names), "source": self.source,
                **{k: np.asarray(getattr(self, k)).tolist() for k in
                   ("f_max", "l_opt", "l_ts", "alpha_0", "v_max",
                    "tau_act", "tau_deact", "shape_A", "strength")}}

    @classmethod
    def from_dict(cls, d: dict) -> "MuscleParameters":
        return cls(names=list(d["names"]), source=d.get("source", "file"),
                   **{k: np.asarray(d[k], float) for k in
                      ("f_max", "l_opt", "l_ts", "alpha_0", "v_max",
                       "tau_act", "tau_deact", "shape_A", "strength")})


# --------------------------------------------------------------------------- #
#  Height / mass scaling  --  the "just height and weight" entry point
# --------------------------------------------------------------------------- #
#  Reference anthropometry of the generic models this pipeline uses
#  (Rajagopal2015 / gait2392 are both built around ~75 kg, 1.70 m).
REF_MASS = 75.0
REF_HEIGHT = 1.70


def scale_parameters(params: MuscleParameters, height=None, mass=None,
                     *, ref_mass=REF_MASS, ref_height=REF_HEIGHT) -> MuscleParameters:
    """Scale generic MTU parameters to a participant from height and mass alone.

    Force scales with physiological cross-sectional area, i.e. muscle VOLUME
    divided by fibre LENGTH. Muscle volume scales with body mass (Handsfield
    2014 reports volume ~ mass * height); fibre and tendon lengths scale with
    a linear dimension, i.e. height. Hence::

        l_opt, l_ts  <-  * (height / ref_height)
        f_max        <-  * (mass*height) / (ref_mass*ref_height) / (height/ref_height)
                      =  * (mass / ref_mass)

    which is why F_max ends up essentially mass-proportional and lengths
    height-proportional. Written out rather than collapsed, because the two
    factors are separately arguable and someone will want to change one.

    This is a PRIOR, not a personalisation. It exists so the pipeline never
    blocks on a calibration session; calibrate.py supersedes it.
    """
    out = params.copy()
    hs = 1.0 if not height else float(height) / ref_height
    ms = 1.0 if not mass else float(mass) / ref_mass
    volume_scale = ms * hs                 # muscle volume ~ mass * height
    out.l_opt = params.l_opt * hs
    out.l_ts = params.l_ts * hs
    out.f_max = params.f_max * (volume_scale / hs)     # = PCSA scale
    out.source = f"scaled:height_mass(h={height},m={mass})"
    return out


# --------------------------------------------------------------------------- #
#  Activation dynamics
# --------------------------------------------------------------------------- #
def emg_to_activation(u: np.ndarray, shape_A: np.ndarray) -> np.ndarray:
    """Nonlinear EMG-to-activation transfer (Lloyd & Besier 2003).

        a = (exp(A*u) - 1) / (exp(A) - 1),   A in [-3, 0)

    A -> 0 is linear; A -> -3 is strongly concave (low excitations produce
    relatively more activation).
    """
    u = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    A = np.clip(np.asarray(shape_A, dtype=float), -2.999, -1e-6)
    return (np.exp(A * u) - 1.0) / (np.exp(A) - 1.0)


def activation_dynamics(u: np.ndarray, dt: float, params: MuscleParameters,
                        a0: Optional[np.ndarray] = None) -> np.ndarray:
    """First-order activation dynamics over a whole excitation time series.

    ``u`` is (nt, nm) neural excitation in 0-1. Returns activations (nt, nm).
    Uses the standard asymmetric time constants: activation is faster than
    deactivation.
    """
    u = np.atleast_2d(np.asarray(u, dtype=float))
    nt, nm = u.shape
    a = np.empty((nt, nm), dtype=float)
    a[0] = u[0] if a0 is None else np.asarray(a0, dtype=float)
    for i in range(1, nt):
        rising = u[i] >= a[i - 1]
        tau = np.where(rising, params.tau_act, params.tau_deact)
        # backward Euler: stable for any dt, which matters at 2000 Hz EMG
        a[i] = (a[i - 1] + (dt / tau) * u[i]) / (1.0 + dt / tau)
    return np.clip(a, 0.0, 1.0)


# --------------------------------------------------------------------------- #
#  Force-length / force-velocity curves
# --------------------------------------------------------------------------- #
def f_active_length(l_norm: np.ndarray) -> np.ndarray:
    """Active force-length. Gaussian approximation, ~Thelen 2003 (kshape 0.45)."""
    l = np.asarray(l_norm, dtype=float)
    return np.exp(-((l - 1.0) ** 2) / 0.45)


def f_passive_length(l_norm: np.ndarray, k_pe=4.0, eps_0m=0.6) -> np.ndarray:
    """Passive force-length, exponential (Thelen 2003). Zero below l_norm = 1."""
    l = np.asarray(l_norm, dtype=float)
    num = np.exp(k_pe * (l - 1.0) / eps_0m) - 1.0
    den = np.exp(k_pe) - 1.0
    return np.clip(num / den, 0.0, None)


def f_velocity(v_norm: np.ndarray, a_f=0.25, f_len=1.4) -> np.ndarray:
    """Force-velocity. ``v_norm`` in optimal-fibre-lengths per second, divided
    by v_max: negative = shortening.

    Hill hyperbola while shortening, saturating branch while lengthening.
    """
    v = np.clip(np.asarray(v_norm, dtype=float), -1.0, 1.0)
    short = (1.0 + v) / (1.0 - v / a_f)                       # v <= 0
    d = 1.0 + v * (2.0 + 2.0 / a_f) / (f_len - 1.0)
    lengthen = np.where(d > 1e-9, f_len - (f_len - 1.0) / d, f_len)
    return np.clip(np.where(v <= 0.0, short, lengthen), 0.0, f_len)


def f_tendon(strain: np.ndarray, k_t=35.0, eps_0t=0.033) -> np.ndarray:
    """Normalised tendon force from tendon strain (Thelen 2003 exponential).

    The exponent is clipped before exp(): during bisection the trial fibre
    length can imply an absurd tendon strain, and np.exp overflows to inf,
    which poisons the comparison the bisection is making. Above the physical
    strain range the curve is continued LINEARLY -- still monotonic, so the
    bisection converges, and never reached at the solution.
    """
    e = np.asarray(strain, dtype=float)
    x = k_t * e / eps_0t
    den = np.exp(k_t) - 1.0
    lin = x > k_t
    out = np.where(lin,
                   (np.exp(np.minimum(x, k_t)) - 1.0) + np.exp(k_t) * (x - k_t),
                   np.exp(np.minimum(x, k_t)) - 1.0)
    return np.clip(out / den, 0.0, None)


# --------------------------------------------------------------------------- #
#  The MTU model
# --------------------------------------------------------------------------- #
@dataclass
class MuscleState:
    """The MTU at one frame, LINEARISED in activation: F = gain * a + passive.

    Splitting the state out this way is what makes the solver fast: the joint
    moment is then linear in ``a`` and the frame solves as a bounded least
    squares.

    With a rigid tendon the split is exact. With an elastic tendon the fibre
    length itself depends on activation, so the state is built at a GUESSED
    activation and the solver iterates (see ``FrameSolver(..., passes=)``) --
    exact at convergence, and still one linear solve per pass.
    """
    l_norm: np.ndarray           # normalised fibre length
    v_norm: np.ndarray           # normalised fibre velocity (/v_max)
    cos_pen: np.ndarray          # cos(pennation)
    gain: np.ndarray             # N of force per unit activation
    passive: np.ndarray          # N of activation-independent force
    l_m: Optional[np.ndarray] = None      # fibre length (m), for velocity carry-over
    l_t: Optional[np.ndarray] = None      # tendon length (m)
    l_mt: Optional[np.ndarray] = None     # musculotendon length (m)


class RigidTendonMTU:
    """Rigid tendon: fibre length follows MTU length directly.

    l_m = (l_mt - l_ts) / cos(pennation), with pennation from the constant
    muscle-thickness assumption  l_m*sin(alpha) = l_opt*sin(alpha_0).
    """

    def __init__(self, params: MuscleParameters):
        self.p = params
        self._h = params.l_opt * np.sin(params.alpha_0)   # constant thickness

    # -- geometry ----------------------------------------------------------
    def fibre_length(self, l_mt: np.ndarray) -> np.ndarray:
        p = self.p
        l_along = np.maximum(np.asarray(l_mt, float) - p.l_ts, 1e-4)
        # l_m^2 = l_along^2 + h^2   (right triangle, constant thickness)
        return np.sqrt(l_along ** 2 + self._h ** 2)

    def cos_pennation(self, l_m: np.ndarray) -> np.ndarray:
        s = np.clip(self._h / np.maximum(l_m, 1e-6), 0.0, 0.999)
        return np.sqrt(1.0 - s ** 2)

    # -- state -------------------------------------------------------------
    activation_dependent = False

    def state(self, l_mt: np.ndarray, v_mt: np.ndarray, a=None,
              l_m_prev=None, dt=None) -> MuscleState:
        """Linearised state at this frame. ``a`` is ignored for a rigid tendon."""
        p = self.p
        l_m = self.fibre_length(l_mt)
        cos_pen = self.cos_pennation(l_m)
        l_norm = l_m / p.l_opt
        v_m = np.asarray(v_mt, dtype=float) * cos_pen
        v_norm = np.clip(v_m / (p.v_max * p.l_opt), -1.0, 1.0)

        fmax = p.f_max * p.strength
        gain = fmax * f_active_length(l_norm) * f_velocity(v_norm) * cos_pen
        passive = fmax * f_passive_length(l_norm) * cos_pen
        # With a RIGID tendon the tendon length IS l_ts by definition -- that
        # is what "rigid" means. It is written out anyway so the output files
        # carry the same columns whichever tendon model ran, and so a constant
        # column is a visible, checkable statement rather than a missing file.
        return MuscleState(l_norm=l_norm, v_norm=v_norm, cos_pen=cos_pen,
                           gain=gain, passive=passive, l_m=l_m,
                           l_t=np.broadcast_to(p.l_ts, l_m.shape).copy(),
                           l_mt=np.asarray(l_mt, float))

    # -- force -------------------------------------------------------------
    def force(self, a: np.ndarray, state: MuscleState) -> np.ndarray:
        """Tendon force (N) for activations ``a`` at a precomputed state."""
        return np.clip(a, 0.0, 1.0) * state.gain + state.passive

    def force_from_length(self, a, l_mt, v_mt) -> np.ndarray:
        return self.force(a, self.state(l_mt, v_mt))

    # -- diagnostics --------------------------------------------------------
    def operating_range(self, l_mt: np.ndarray) -> "dict":
        """Where each muscle sits on the force-length curve across a trial.

        THE most useful diagnostic in the package. A muscle stuck far down the
        ascending limb cannot generate force whatever the solver does, so the
        moment goes to the reserves and the result looks like a solver failure
        when it is really a tendon-slack-length problem. Long-tendon muscles
        (soleus, gastrocs: tendon/fibre > 6) are where this bites.
        """
        p = self.p
        l_norm = self.fibre_length(np.atleast_2d(l_mt)) / p.l_opt
        fl = f_active_length(l_norm)
        return {
            "muscles": list(p.names),
            "l_norm_min": l_norm.min(axis=0), "l_norm_max": l_norm.max(axis=0),
            "l_norm_mean": l_norm.mean(axis=0), "mean_f_L": fl.mean(axis=0),
            "tendon_ratio": p.l_ts / p.l_opt,
        }


class ElasticTendonMTU(RigidTendonMTU):
    """Elastic tendon via per-frame fibre-length equilibrium.

    Slower (a scalar root-find per muscle per frame) and NOT linear in
    activation, so the solver falls back to SLSQP. Use for offline accuracy
    work; benchmark against the rigid path before trusting the extra cost.
    """

    def __init__(self, params: MuscleParameters, tol=1e-6, max_iter=30):
        super().__init__(params)
        self.tol, self.max_iter = tol, max_iter

    def equilibrium_fibre_length(self, a, l_mt, v_mt=None):
        p = self.p
        a = np.clip(np.asarray(a, float), 1e-3, 1.0)
        l_mt = np.asarray(l_mt, float)
        # Wide bracket: with generic (uncalibrated) tendon slack lengths the
        # equilibrium fibre length of a long-tendon muscle can sit well outside
        # the textbook 0.5-1.5 range. A bracket that excludes the true root
        # silently returns the bracket edge, which looks like a converged solve.
        lo = np.full_like(l_mt, 0.05) * p.l_opt
        hi = np.full_like(l_mt, 3.00) * p.l_opt
        for _ in range(self.max_iter):                     # vectorised bisection
            mid = 0.5 * (lo + hi)
            cos_pen = self.cos_pennation(mid)
            l_norm = mid / p.l_opt
            f_m = (a * f_active_length(l_norm) + f_passive_length(l_norm)) * cos_pen
            l_t = l_mt - mid * cos_pen
            f_t = f_tendon(np.clip(l_t / p.l_ts - 1.0, 0.0, None))
            too_short = f_m < f_t
            lo = np.where(too_short, mid, lo)
            hi = np.where(too_short, hi, mid)
            if np.all(hi - lo < self.tol):
                break
        return 0.5 * (lo + hi)

    activation_dependent = True

    def state(self, l_mt, v_mt, a=None, l_m_prev=None, dt=None) -> MuscleState:
        """Equilibrium fibre length at activation ``a``, linearised there.

        Fibre velocity cannot come from ``v_mt`` here -- with a compliant tendon
        the fibre and the whole MTU move differently, and at the ankle they can
        move in OPPOSITE directions. It is estimated from the previous frame's
        equilibrium fibre length instead, which is causal and is what a forward
        EMG-driven simulation does. The first frame falls back to ``v_mt``.
        """
        p = self.p
        a_g = np.full(p.n, 0.05) if a is None else np.clip(np.asarray(a, float), 0.0, 1.0)
        l_m = self.equilibrium_fibre_length(a_g, l_mt)
        cos_pen = self.cos_pennation(l_m)
        l_norm = l_m / p.l_opt

        if l_m_prev is not None and dt:
            v_m = (l_m - np.asarray(l_m_prev, float)) / float(dt)
        else:
            v_m = np.asarray(v_mt, float) * cos_pen
        v_norm = np.clip(v_m / (p.v_max * p.l_opt), -1.0, 1.0)

        fmax = p.f_max * p.strength
        gain = fmax * f_active_length(l_norm) * f_velocity(v_norm) * cos_pen
        passive = fmax * f_passive_length(l_norm) * cos_pen
        return MuscleState(l_norm=l_norm, v_norm=v_norm, cos_pen=cos_pen,
                           gain=gain, passive=passive, l_m=l_m,
                           l_t=np.asarray(l_mt, float) - l_m * cos_pen,
                           l_mt=np.asarray(l_mt, float))

    def force_from_length(self, a, l_mt, v_mt=None):
        p = self.p
        l_m = self.equilibrium_fibre_length(a, l_mt, v_mt)
        l_t = np.asarray(l_mt, float) - l_m * self.cos_pennation(l_m)
        return p.f_max * p.strength * f_tendon(np.clip(l_t / p.l_ts - 1.0, 0.0, None))


#  Above this tendon-slack / optimal-fibre ratio, tendon compliance dominates
#  and a rigid tendon is simply invalid. Soleus (~6) and the gastrocs (~8) are
#  well past it -- and they are the highest-force muscles in running, so getting
#  this wrong is not a rounding error.
COMPLIANT_TENDON_RATIO = 3.0


def build_mtu(params: MuscleParameters, tendon="auto"):
    """``"rigid"`` | ``"elastic"`` | ``"auto"``.

    ``auto`` currently resolves to RIGID, and that is an evidence-based choice
    rather than a default nobody revisited. On FAIS 022/Run_baselineA1 the
    elastic path did NOT improve agreement with OpenSim SO (stance-limb median
    peak ratio 0.99 elastic vs 0.97 rigid; force-weighted R2 slightly worse),
    while costing ~4 linearisation passes per frame. Both are wrong in the same
    way and for the same reason -- generic, uncalibrated tendon slack lengths --
    so paying for tendon compliance buys nothing until l_ts is calibrated.
    Revisit this once tier 3 works: ``tendon="elastic"`` is fully implemented.
    """
    mode = str(tendon).lower()
    if mode.startswith("auto"):
        mode = "rigid"
    if mode.startswith("elast"):
        return ElasticTendonMTU(params)
    return RigidTendonMTU(params)
