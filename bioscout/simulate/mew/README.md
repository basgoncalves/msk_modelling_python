# mew — muscle extrapolation web

(Was `muscle_analyser` until 2026-09-10.)

CEINMS in Python, with a tier ladder so it **always returns muscle forces**.

Minimum input: a base `.osim`, the participant's **height** and **mass**, and a set of
**kinematics**. GRF, EMG and subject calibration are optional and each raises the tier.

Full architecture, formulation and the bioscout integration plan: **[DESIGN.md](DESIGN.md)**.

---

## Status — draft, 2026-09-02

Working and verified:

* Hill-type MTU (rigid tendon), activation dynamics, EMG-to-activation nonlinearity
* the hybrid solver (moment tracking + effort + EMG tracking + smoothing + ML prior)
* tier selection, moment sources, confidence scoring
* geometry from OpenSim MuscleAnalysis tables, the OpenSim API, or a fitted surrogate
* MTU parameters read straight out of the `.osim` by XML — no OpenSim import needed
* bioscout-layout discovery and CEINMS-compatible `.sto` output
* two tests, both passing (below)

Stubbed, with the contract written down:

* `calibrate.prepare()` — needs `Mew.run()` split into `_assemble()` + solve
* `ml.SurrogateSolver` — port `FAIS_machine_learning/code/ml_model.py` in here
* `ml.GRFPredictor` — the model that turns a camera-only capture from tier 0 into tier 1

---

## Muscle forces AND joint contact forces, in one command

From a session it is a pipeline stage like SO (model and body mass come from
`session.yaml`; missing IK/ID/MA/SO prerequisites are filled, never overwritten;
an existing `mew/` result is skipped unless `replace=True`):

```python
Session(session_dir).iteration("gpk").run(trials=["Walking_01"], do_mew=True)
```
```bash
bioscout simulate mew <session_dir> --iteration gpk --trial Walking_01
```

On a bare trial folder:

```bash
python -m bioscout.simulate.mew analyse <trial_dir> --model <model.osim> --jcf
```

Everything lands in `<trial>/mew/` — nothing a CEINMS or SO run produced is
touched:

One quantity per file, named the way CEINMS names them — same reason OpenSim does it:
units stay consistent within a file, and a reader never has to know which columns of a
mixed file it wants.

| file | columns | what it is |
|---|---|---|
| `MuscleForces.sto` | muscles | total tendon force (N) |
| `MuscleForcesActive.sto` | muscles | the activation-dependent part |
| `MuscleForcesPassive.sto` | muscles | the passive (parallel-elastic) part |
| `Activations.sto` | muscles | activation, 0–1 |
| `FibreLengths.sto` | muscles | fibre length (m) |
| `NormFibreLengths.sto` | muscles | fibre length / optimal — **the diagnostic that matters** |
| `NormFibreVelocities.sto` | muscles | fibre velocity / v_max |
| `TendonLengths.sto` | muscles | tendon length (m); constant = `l_ts` with a rigid tendon, by definition |
| `NormTendonLengths.sto` | muscles | tendon length / slack length |
| `MTULengths.sto` | muscles | musculotendon length (m) |
| `PennationAngles.sto` | muscles | pennation (rad) |
| `Reserves.sto` | **coordinates** | **read this first** — what the muscles could NOT produce, per DOF |
| `MomentsTracked.sto` | coordinates | the moments the solve was asked to hit |
| `provenance.json` | — | tier, weights, EMG channels, every warning |
| `JRA_forces.sto` | everything | JointReaction-ready: muscles **+** merged residual/reserve/GRF |
| `JRA_ReactionLoads.sto` | joints | joint contact forces (with `--jcf`, when OpenSim is reachable) |
| `comparison_vs_static_optimisation.csv`, `comparison_vs_ceinms.csv` | | per-muscle peak ratio, RMSE, R² raw and filtered |
| `baseline_so_vs_ceinms.csv` | | how far YOUR two existing methods sit from each other |
| `muscle_forces.png` | | top-9 force traces vs SO / CEINMS |
| `manifest.json` | | the whole run in one file |

`Reserves.sto` gets its own file because it is indexed by **coordinate**, not by muscle —
a different number of columns with different names. A reserve is a *generalised* force:
a moment (Nm) at a rotational coordinate, a force (N) at a translational one, which is why
that one file mixes units exactly as OpenSim's own force files do.

### Smoothing — two knobs, and they are not the same thing

```bash
--smoothing W     # solver temporal-coupling weight (default 0.5; 0 = off)
--filter-hz HZ    # ALSO low-pass the outputs after solving (off by default)
```

`--smoothing` is smoothing done **during** the solve: each frame is penalised for
departing from the previous frame's activations, so the solution chosen is a smooth one
that *still satisfies the moment constraint*. `--smoothing 0` gives frame-independent
solving — the regime OpenSim SO runs in, chatter included. This is the physiologically
defensible kind: activation cannot jump discontinuously.

`--filter-hz` is a zero-lag low-pass applied to the outputs **after** solving. It makes
traces look smooth, but the filtered forces no longer reproduce the tracked moments — so
never feed a filtered result to JointReaction. On FAIS 022 a 10 Hz filter cut peak
`soleus_l` from 7370 N to 5009 N: a third of the peak, gone. Use it for figures, and
know that is what you did.

Measured on that trial (roughness = mean \|2nd difference\|, normalised):

| setting | roughness | mean \|reserve\| | peak soleus_l |
|---|---|---|---|
| `--smoothing 0` | 0.236 | 28.28 | 7370 N |
| default (0.5) | 0.227 | 28.35 | 7356 N |
| `--smoothing 5` | 0.203 | 29.11 | 7255 N |
| `--smoothing 0 --filter-hz 10` | **0.019** | 28.28 | **5009 N** |

The solver weight buys smoothness by paying in moment tracking — visibly, in the reserve
column. The post-filter buys it by quietly deleting peak force. Prefer the first.

The reserves are deliberately **not** filtered by `--filter-hz`: they are the record of
what the unfiltered solve could not explain, and smoothing them would improve the
confidence score without improving anything real.

Add `--ceinms-compat` to *also* write `ceinms/Optimised/MuscleForces.sto`, which is what
the existing bioscout plotting and `summarize_results.py` read.

### The JCF trap this handles for you

`JointReaction`'s forces file must contain **every** actuator — pelvis residuals `FX..MZ`,
coordinate reserves, lumbar actuators, GRF — not just muscles. Give it muscle columns
alone and it cannot balance the dynamics: it dumps the whole imbalance into the proximal
joint, giving a hip contact force ~100× too large that is also *identical whatever the
muscle forces were*. `jcf.build_forces_file()` merges those columns from the trial's SO
force file and **refuses to write an unbalanced file** unless you pass
`allow_unbalanced=True`. Where a `<dof>_reserve` column matches a DOF this solver tracked,
it substitutes **our own** residual, so the reserve means "what this solution could not
produce" rather than another model's leftovers. `jcf.sanity_check()` then flags any joint
above 12 BW.

The JointReaction call itself is the one step that needs `opensim` + `bioscout` importable.
If they are missing, the muscle forces and the balanced `JRA_forces.sto` are still written
and the manifest records why the last step was skipped — run it later from your bioscout
conda env with the same command.

## Try it

```bash
# no data needed: 6-muscle synthetic leg, checks the solver recovers known activations
python -m bioscout.simulate.mew selftest

# bundled real trial (repo root; example_data/ is gitignored, so local only):
# OrthoLoad H1L level walking, scaled GPK model, measured hip contact force alongside
T=example_data/orthoload/simulations/H1_orthoload/11_05_06/3_iterations/gpk/Walking_01
M=example_data/orthoload/models/personalised/H1_orthoload/11_05_06/gpk_scaled.osim
python -m bioscout.simulate.mew analyse $T --model $M --jcf

# what does this trial have, and what tier does it reach?
python -m bioscout.simulate.mew inspect simulations/009/post/3_iterations/rajagopal_fai/RunL1

# solve it
python -m bioscout.simulate.mew run simulations/009/post/3_iterations/rajagopal_fai/RunL1 \
    --model models/personalised/009/009_Rajagopal2015_FAI.osim \
    --height 1.78 --mass 75 --write

# the degradation curve: same trial at every tier it supports
python -m bioscout.simulate.mew tiers <trial_dir> --model <model.osim>
```

Real run, FAIS 009 / RunL1, 80 muscles, 71 frames, tier 1: **2.6 s wall clock** including
imports, peak soleus 6.0 kN, mean unexplained moment 7.3 Nm (8–10 % of peak at the hip and
ankle, ~2 % at the knee).

## API

```python
from bioscout.simulate.mew import Mew

# minimum viable: height, mass, model, kinematics
ma = Mew(model="Rajagopal2015.osim", height=1.81, mass=78,
         kinematics="joint_angles.mot")
res = ma.run()
print(res.summary())        # tier, confidence, mean residual
print(res.provenance.warnings)

# everything optional, added
ma = Mew(model=..., height=1.81, mass=78,
         kinematics="external_biomechanics/joint_angles.mot",
         moments="external_biomechanics/inverse_dynamics.sto",
         emg="inputs/emg_filtered_normalised.mot",
         emg_map={"RF": ["recfem_r"], "VAS": ["vasmed_r", "vaslat_r"]},
         moment_arms="muscle_analysis/",
         theta_file="009_theta.json")
res = ma.run()                              # -> tier 3
res.write_sto("ceinms/Optimised/MuscleForces.sto", extra=True)

# from a bioscout session (reads body_mass, emg_map, side, time_range from session.yaml)
from bioscout.session import Session
it = Session(session_dir).iteration("rajagopal_fai")
res = Mew.from_bioscout(it, "RunL1").run()
```

## Compatibility with bioscout

* writes `<trial>/ceinms/Optimised/MuscleForces.sto` — the exact path
  `bioscout.core.analysis.LAYOUT_DIRS` defines and `ml_model.ceinms_forces_path()` reads,
  so existing plots, `summarize_results.py` and the ML training set work unchanged
* reads the canonical trial files and `session.yaml` via `bioscout.session`
* **`import bioscout.simulate.mew` works with no bioscout, no OpenSim and no torch installed.**
  Only `bioscout_adapter`, `geometry.OpenSimGeometry` and `ml` touch those, all lazily.

## Tests

```bash
python -m unittest bioscout.tests.test_mew -v   # all of the below + the OrthoLoad trial
python -m bioscout.simulate.mew selftest              # solver vs known ground truth
python bioscout/simulate/mew/tests/test_end_to_end.py # full API, files on disk, tier ladder
```

`selftest` result, for reference — the number that matters is the third line:

```
tier1 static_opt     residual 0.36% of peak | activation MAE 0.0627 | force MAE 25.4%
tier2 emg_informed   residual 0.44% of peak | activation MAE 0.0294 | force MAE 11.5%
```

Both tiers track the joint moment essentially perfectly, but SO's activations are twice as
wrong. That is the muscle-redundancy degeneracy made visible, and it is the entire argument
for the EMG-informed tier: **moment tracking does not tell you whether the muscle forces are
right.** It is also why every result carries a tier and a confidence rather than just numbers.

## Next

1. Split `Mew.run()` into `_assemble()` + solve, so `calibrate.prepare()` works.
2. Validate tier 1 against `SO_StaticOptimization_force.sto` and tier 2/3 against CEINMS on
   the FAIS set — see DESIGN.md §10.
3. Port `ml_model.py` in as `ml.SurrogateSolver`, predicting activations rather than forces.
4. `ml.GRFPredictor`, then the surrogate geometry path, then the camera pipeline.
