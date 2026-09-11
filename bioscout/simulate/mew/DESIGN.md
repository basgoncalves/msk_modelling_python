# mew (muscle extrapolation web) — a Python-native, always-answers muscle force estimator

**Status:** draft / skeleton (2026-09-02)
**Home:** `bioscout/simulate/mew/` (moved from `FAIS_machine_learning/code/muscle_analyser` and renamed, 2026-09-10)
**Import as:** `bioscout.simulate.mew` — see §8.

---

## 1. The one-sentence goal

> Given a participant's **height**, **mass**, a **base musculoskeletal model** and a set of
> **kinematics**, return muscle forces — **always** — and get monotonically better as
> GRF, EMG, subject calibration and trained ML priors are added.

This is CEINMS's idea (EMG-informed / hybrid neuromusculoskeletal solving) rebuilt in
pure Python, with three differences that matter:

| | CEINMS.exe | `mew` |
|---|---|---|
| Inputs | all-or-nothing (needs EMG, ID moments, MA tables, calibrated model) | **tiered** — degrades to whatever you have, flags the tier |
| Failure mode | refuses to run / silent bad solve | always returns forces **plus a confidence record** |
| Extensibility | XML config + recompiled C++ | plain Python objects; solver, MTU model, priors are all swappable |
| Calibration | separate `ceinms-nn-calibrate.exe` pass | same code path, different objective |
| ML | none | first-class: surrogate solver, gap-filling, warm starts |

---

## 2. The core insight: everything is one optimisation

CEINMS's hybrid objective is

```
F_obj = alpha * E_trackMOM + beta * E_sumEXC + gamma * E_trackEMG
```

Static optimisation, EMG-driven, EMG-informed and calibration are **not four algorithms**.
They are the same objective with different weights and different free variables:

| Mode | free variables | alpha (track ID moments) | beta (min effort) | gamma (track EMG) |
|---|---|---|---|---|
| Static optimisation | activations `a(t)` | ∞ (hard constraint) | 1 | 0 |
| EMG-driven | — (forward only) | 0 | 0 | ∞ (a = a_EMG) |
| EMG-informed / hybrid | `a(t)` | high | low | high |
| **Calibration** | **MTU parameters θ** (shared across frames) | high | low | high |
| ML-warm-started hybrid | `a(t)`, initialised at `a_ML` | high | low | high + prior term |

So the package has **one solver** (`solver.py`) and **one MTU model** (`mtu.py`).
Everything else is weights, free-variable selection, and which terms are available.

This is why the tier ladder is cheap to implement: a missing input sets a weight to zero
and raises a flag, it does not need a different code path.

---

## 3. The tier ladder (the "always answers" part)

```
T3  calibrated_hybrid   subject-calibrated θ + EMG + ID(measured GRF)      confidence HIGH
T2  emg_informed        generic θ (height/mass-scaled) + EMG + ID          confidence GOOD
T1  static_optimisation ID from measured GRF, no EMG                       confidence FAIR
T0  kinematics_only     moments from a MomentSource surrogate              confidence LOW
```

`Mew.run()` picks the **highest tier the inputs support** unless you pin one.
Every `MuscleForceResult` carries:

* `tier` — which rung actually ran
* `confidence` — scalar 0–1, plus per-DOF residual of the moment tracking
* `provenance` — what each input was (measured / predicted / assumed), model file hash,
  θ source, solver settings. This is the thing that makes results defensible in a paper.

**T0 is where the honesty lives.** Without GRF you cannot do inverse dynamics for stance.
So T0 does not pretend: it asks a `MomentSource` for joint moments, and the source is
explicit about what it is —

* `MeasuredGRFMoments` — real ID from `inverse_dynamics.sto` (T1+)
* `PredictedGRFMoments` — an ML model predicting GRF from kinematics + mass, then ID (`ml.py`)
* `ScaledTemplateMoments` — mass- and height-scaled normative moment curves for the detected
  task, time-warped onto the trial. Crude; confidence is set accordingly.

That is the layer the camera-only / phone use case eventually plugs into.

---

## 4. Module map

```
mew/
  types.py            SubjectSpec, TrialInputs, MuscleForceResult, Tier, Provenance
  io_ports.py         .sto/.mot/.trc read+write, resampling. Uses bioscout.utils.io when importable,
                      falls back to a self-contained parser so the package runs standalone.
  geometry.py         MTUGeometry: moment arms r(q) and MTU length l_mt(q) for every muscle.
                      Three providers, same interface:
                        OpenSimGeometry   — live OpenSim API calls (accurate, slow)
                        TableGeometry     — bioscout MuscleAnalysis .sto tables (accurate, fast)
                        SurrogateGeometry — polynomial/MLP fit of r(q), l_mt(q) (fast, real-time path)
  mtu.py              Hill-type MTU. Activation dynamics (Zajac/Lloyd-Besier), active+passive FL,
                      FV, tendon. Rigid tendon by default; elastic-tendon equilibrium optional.
  excitation.py       raw EMG -> excitation: band-pass, rectify, low-pass, MVC normalise,
                      electromechanical delay, per-channel gain and shape factor A.
                      Channel->muscle mapping is bioscout's emg_map format.
  solver.py           per-frame constrained least squares (the hybrid objective, §2).
  tiers.py            input inspection -> tier selection, confidence scoring.
  calibrate.py        subject calibration: optimise θ over calibration trials.
  ml.py               optional ML layers: surrogate solver, GRF/EMG gap-fillers, warm starts.
                      Torch is an optional dependency; absent torch, everything else still runs.
  analyser.py         Mew — the public facade.
  bioscout_adapter.py read a bioscout Iteration/trial, write MuscleForces.sto in CEINMS layout.
  __main__.py         CLI: python -m bioscout.simulate.mew run <trial_dir> ...
```

Hard rule: **`types.py`, `mtu.py`, `solver.py` and `tiers.py` import nothing heavier than
numpy/scipy.** OpenSim, torch and bioscout are all optional and confined to
`geometry.py`, `ml.py` and `bioscout_adapter.py`. This is the same discipline
`bioscout.simulate.ceinms.modes` follows, and for the same reason: a missing OpenSim DLL
must never silently change which solve you got.

---

## 5. The MTU model

Per muscle *m*, per frame *t*:

```
excitation      u(t)        from EMG, or a free variable
activation      a(t)        first-order activation dynamics + nonlinear shape factor A
fibre length    l_m         from l_mt(q) - l_t, with pennation
normalised      l~ = l_m / l_opt,   v~ = v_m / v_max
force           F = F_max * [ a * f_L(l~) * f_V(v~) + f_PE(l~) ] * cos(alpha)
joint moment    M_dof = sum_m r_m,dof(q) * F_m
```

**Parameter vector θ per muscle** (what calibration touches, same set CEINMS calibrates):

* `F_max` — maximum isometric force
* `l_opt` — optimal fibre length
* `l_ts` — tendon slack length
* `alpha_0` — pennation at optimal fibre length
* `tau_act`, `tau_deact` — activation time constants
* `A` — EMG-to-activation nonlinearity shape factor
* `strength_coeff` — group-wise scale factor

**Generic θ from height + mass only.** This is the "just height and weight" entry point:
`mtu.scale_parameters(base_model_params, height, mass)` scales `F_max` by a
mass^(2/3)-style volume/PCSA argument (Handsfield-type regressions) and `l_opt`/`l_ts` by
the model's own segment scaling. Not subject-specific, but it is a defensible prior and
it means the pipeline never blocks on a calibration session.

Rigid tendon is the default because it removes the per-frame root-find and makes the whole
model a closed-form function of `(q, q̇, a)` — which is what makes both the real-time path
and gradient-based calibration tractable. Elastic tendon is a flag for offline accuracy work.

---

## 6. The solver

Per frame, minimise over `a ∈ [0,1]^n`:

```
J(a) = alpha * || W_dof (M_model(a) - M_ID) ||^2
     + beta  * || a ||_p^p                                  (p = 2 by default)
     + gamma * || S_emg (a - a_EMG) ||^2                     (EMG channels only)
     + delta * || a - a_prev ||^2                            (temporal smoothing)
     + eps   * || a - a_ML ||^2                              (ML prior, tier-dependent)
```

* `scipy.optimize.lsq_linear` when the FV term is frozen at the previous frame's fibre
  velocity — the objective is then **linear in `a`** and each frame solves in microseconds.
* `scipy.optimize.minimize(method="SLSQP")` as the general nonlinear fallback.
* Frames are solved sequentially with warm starts (previous frame's `a`), which is both
  faster and what makes the `delta` smoothing term meaningful.

Residual actuators: a small penalised slack per DOF absorbs moments the muscles cannot
produce, instead of the solve failing. The slack magnitude is reported — it is a direct,
readable measure of "how much this model could not explain", and a large slack is exactly
the signal that should drop the confidence score.

---

## 7. Calibration

`calibrate.py` optimises θ (a few dozen parameters, shared across all frames of a few
calibration trials) to minimise the same objective, evaluated over the trial set:

```
theta* = argmin_theta  sum_trials sum_frames  J(a*(theta); theta)
```

Outer loop: `scipy.optimize.differential_evolution` or `minimize(L-BFGS-B)` with bounds
expressed as **fractions of the generic value** (e.g. `l_opt ∈ [0.95, 1.05] × generic`) —
the same bound convention as bioscout's `session.yaml` `calibration:` block, so an existing
session's calibration config maps straight across.

Output: a `theta.json` per subject/model, cached beside the model. `Mew` picks it
up automatically and reports tier T3.

---

## 8. bioscout compatibility

Non-negotiable constraints, taken from the existing package:

1. **Layout.** Writes go to `<trial>/ceinms/Optimised/MuscleForces.sto` — the path
   `bioscout.core.analysis.LAYOUT_DIRS` defines and `ml_model.ceinms_forces_path()`
   already reads. Same `.sto` header, same column names (OpenSim muscle names), so every
   existing plot, `summarize_results.py`, and the FAIS ML training set work unchanged.
   A `MewForces.sto` sidecar carries the extra columns (activations, per-DOF
   residual, tier) so nothing pollutes the CEINMS-shaped file.
2. **Inputs.** Reads the canonical trial files:
   `external_biomechanics/joint_angles.mot`, `external_biomechanics/inverse_dynamics.sto`,
   `inputs/emg_filtered_normalised.mot`, `muscle_analysis/` MA tables, `inputs/grf.mot`.
3. **Config.** Subject/trial metadata comes from `session.yaml` via
   `bioscout.session` (`Iteration`, `trial_config`, `resolve_emg_map`,
   `resolve_calibration`). No new config file format.
4. **Optional import.** `import bioscout.simulate.mew` must succeed with no
   OpenSim and no torch installed, and without pulling in the rest of bioscout (the
   package root and `bioscout.simulate` are both lazy). The adapter is the only module
   that imports other bioscout modules, and it does so lazily inside functions.

Drop-in usage once merged:

```python
from bioscout.session import Session
it = Session(session).iteration("rajagopal_fai")

from bioscout.simulate.mew import Mew
ma = Mew.from_bioscout(it, trial="Run_baselineA1")
res = ma.run()                      # picks the highest tier the trial supports
res.write_sto()                     # ceinms/Optimised/MuscleForces.sto
print(res.tier, res.confidence)
```

And the standalone / minimum-input path:

```python
ma = Mew(
    model="models/generic/Rajagopal2015.osim",
    height=1.81, mass=78.0,
    kinematics="joint_angles.mot",     # everything below is optional
)
res = ma.run()                         # T0, confidence low, but it returns forces
```

Migration is additive: `Analyse.run()` gains `muscle_solver="ceinms" | "mew"`,
defaulting to `"ceinms"` until the validation in §10 passes.

---

## 9. The route to the real-time camera goal

The project's third goal (phone camera → muscle forces, semi-real-time) falls out of this
design rather than needing a separate system:

1. `movement_detector` gives 2D/3D keypoints → joint angles `q(t)`.
2. `SurrogateGeometry` replaces OpenSim API calls with a fitted `r(q), l_mt(q)` — this is the
   single biggest speed win, and it is a pure function.
3. `PredictedGRFMoments` (ml.py) gives moments without a force plate.
4. Rigid-tendon MTU + linear-in-`a` solver runs a frame in well under a millisecond.
5. Offline CEINMS/T3 results are the **training labels** for the ML layers — which is
   exactly the dataset `ml_model.py` already builds. That existing surrogate becomes
   `ml.SurrogateSolver` inside this package rather than a parallel script.

So: the offline pipeline generates its own real-time model. Each tier's output is the
next tier's training data.

---

## 10. Validation plan (before it replaces anything)

1. **Unit**: MTU force at known `(a, l~, v~)` against published Thelen/Millard curves.
2. **Moment closure**: `sum r*F` reproduces `inverse_dynamics.sto` within the residual budget.
3. **Against OpenSim SO**: T1 vs `SO_StaticOptimization_force.sto` on the same trials —
   should agree to within a few percent; systematic disagreement means a geometry or
   parameter bug, not a modelling choice.
4. **Against CEINMS**: T2/T3 vs `ceinms/Optimised/MuscleForces.sto` on the FAIS set.
   Report per-muscle R² and RMSE, and correlation of EMG-to-activation.
5. **Against literature**: reuse `bioscout.muscle_inspect.literature_jcf` — JCF derived
   from these forces must sit inside the published bands.
6. **Tier degradation curve**: same trials solved at T3→T0, plotting accuracy loss per rung.
   This is the headline figure and the honest answer to "how much worse is kinematics-only?"

---

## 10b. First validation run — what actually happened (2026-09-02)

FAIS `022/pre/.../Run_baselineA1`, tier 2 (EMG-informed, left-side electrodes),
80 muscles, 71 frames (`time_range: [3.95, 4.30]` from session.yaml), against that
trial's existing `SO_StaticOptimization_force.sto`.

**Peak magnitudes agree; waveform agreement is limb-dependent.**

| | peak ratio (new/SO) | R² raw | R² filtered |
|---|---|---|---|
| soleus_l | 0.99 | 0.69 | 0.72 |
| gasmed_l | 0.76 | 0.74 | 0.92 |
| vaslat_l | 1.22 | 0.31 | 0.53 |
| soleus_r | **0.05** | −0.39 | −2.69 |

Three findings, in order of how much they change what to do next:

1. **The aggregate R² is not a meaningful number on this trial.** The window is a
   LEFT stance phase: `ankle_angle_r` carries p95 = 17.6 Nm against 387 Nm on the left.
   Our `soleus_r` is ~225 N because there is no right ankle moment to produce, and the
   right-ankle residual is 1.4 Nm — the solve is doing the right thing. SO's 4359 N
   `soleus_r` in the same frames is the number that needs explaining, not ours.
   **Validate against SO on the stance limb only, or on trials with a full cycle.**
2. **Comparing raw traces charges this solver for SO's noise.** OpenSim SO solves each
   frame independently with no temporal coupling and its traces chatter; this solver has
   a smoothing term and its traces do not. `compare.compare_forces` now reports `r2` and
   `r2_smooth` (both signals low-passed identically at 15 Hz) — on the stance limb
   filtering raises agreement across the board, which is the honest comparison.
3. **7 muscles cannot reach their rated force with generic parameters.** `gasmed_r`
   sits at mean f_L = 0.28 (tendon/fibre = 7.8), `gaslat_r` at 0.36. Their fibres are
   parked far down the ascending limb because tendon slack length is generic. This is
   not a solver failure and no amount of solver work fixes it — it is exactly what
   calibrating `l_ts` is for. `Mew.run()` now raises this as a warning
   automatically, via `RigidTendonMTU.operating_range()`.

**Rigid vs elastic tendon — question from §11, now answered with data.** The elastic
path is implemented and converges (~4 linearisation passes/frame), and it does NOT
improve agreement with SO here: stance-limb median peak ratio 0.99 elastic vs 0.97
rigid, force-weighted R² slightly worse. Both are wrong the same way for the same
reason — uncalibrated `l_ts` — so tendon compliance buys nothing until tier 3 works.
`build_mtu(tendon="auto")` therefore resolves to **rigid**, and this paragraph is why.
Revisit after calibration.

**So: not yet a validated replacement for SO or CEINMS.** It is a working solver whose
disagreements are now located and explained, which is the point of the validation step.

### Then the CEINMS comparison was added, and it changed the reading

CEINMS output for this trial was not at `ceinms/Optimised/` but at
`ceinms/Execution_a10_b1_g1000/` — `simulate/ceinms/modes.py` TAGS each arm with its
weights, so a multi-arm run leaves several side by side and the plain untagged name may
not exist at all. `bioscout_adapter.find_ceinms_forces()` now resolves the arm by
`session.yaml`'s own `ceinms: alpha/beta/gamma`, which on a sweep picks the PRODUCTION
arm rather than whichever ran last.

With CEINMS in the picture, on load-bearing muscles (reference peak ≥ 5 % of the largest):

| comparison | weighted R² (raw / filtered) | median R² | median peak ratio |
|---|---|---|---|
| ours vs SO | −0.02 / −0.06 | −0.37 | 0.90 |
| ours vs CEINMS | −0.37 / −0.31 | −0.91 | 0.84 |
| **your SO vs your CEINMS** | **−0.62 / −0.50** | **−1.50** | 0.95 |

**The two established methods disagree with each other more than this solver disagrees
with either of them.** That does not make this solver right — all three could be wrong —
but it does mean "agreement with SO" is not a validation target on this trial. The
pipeline now prints that SO-vs-CEINMS baseline on every run for exactly this reason, and
writes `baseline_so_vs_ceinms.csv` beside the other outputs.

It also settles the `soleus_r` / `gasmed_r` question from finding 1: **CEINMS agrees with
us that the right plantarflexors are near zero** in this left-stance window. SO is the
outlier, and its spikes there should be treated as an SO artefact rather than a target.

One numerical fix this exposed: R² is unbounded below, so a single muscle whose reference
is nearly constant returned −10 000 and produced a force-weighted R² of −1066. Aggregates
now floor R² at −1, drop muscles carrying under 5 % of peak load, and report the median
alongside the weighted mean (`compare.aggregate`).

## 11. Open questions

* ~~Rigid vs elastic tendon~~ — answered in §10b: rigid, until `l_ts` is calibrated.
* Why does OpenSim SO put 4.4 kN through `soleus_r` during right-limb swing? Either its
  GRF assignment differs from `inverse_dynamics.sto` (cf. the plate-side bug) or its
  reserves are absorbing something. Worth knowing before using SO as a reference at all.
* Should `strength_coeff` be calibrated per muscle group (CEINMS-style) or predicted from
  height/mass/sex/training status by a small regressor?
* Where does the residual-actuator budget come from — fixed fraction of the ID moment, or
  learned from the calibration set?
* Left/right symmetry: solve both limbs jointly (shares trunk DOFs) or independently?
