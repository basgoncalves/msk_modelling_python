# fais_force_model.pkl

Surrogate for OpenSim static optimisation and JointReaction, used by
`load_tracking/shot_analysis.py`. Loaded through `bioscout/models/force_model.py`,
which needs only numpy.

Trained in the `FAIS_machine_learning` repo (`code/machine_learning/`) on 570
solved trials from 26 subjects — running, sprinting and single-leg squats.

| | |
|---|---|
| inputs | 35 joint positions, 37 velocities, 37 accelerations, mass, height (111) |
| outputs | 80 muscle forces, 18 joint-reaction components, 6 joint-reaction magnitudes |
| units | **bodyweight** — `force_model.predict()` returns muscles in newtons and joint reactions in bodyweight |

Accuracy on held-out subjects, as within-trial R² (how well the predicted curve
follows the real one during one movement): 0.35 muscle force, 0.83 joint
contact force.

## Refresh it

```bash
cd C:/Git/FAIS_machine_learning/code
python -m machine_learning.train --inputs kinematics
python -m machine_learning.audit --model machine_learning/artifacts/model_kinematics.pkl
copy machine_learning\artifacts\model_kinematics.pkl ^
     C:\Git\bioscout\bioscout\models\fais_force_model.pkl
```

`force_model.load()` runs the model at its own training mean and refuses a file
that predicts more than 12 bodyweight there, so a bad export fails on load
rather than in a figure.

## kinematics_only_model.pkl — superseded, do not use

Kept only because the failure is instructive. It predicted 1,110 N at its
training mean, 32,583 N one standard deviation away, and 113,250 N on a real
trial from its own training set. It was a BatchNorm residual MLP exported as
bare `W1 b1 W2 b2`: the running statistics were dropped, so the file was not the
network that was trained, and it behaved at exactly one point — the training
mean, where the weight path vanishes.

`shot_analysis.py` had reimplemented that two-layer pass inline and inherited
the fault. `force_model.load()` now rejects the file by shape.

## Shooting is outside the training data

The model has never seen a basketball shot. Two things follow, and
`predict_muscle_forces` reports both in `result["_meta"]` rather than leaving
them to be discovered:

* a single view supplies four sagittal angles; the other **33 coordinates are
  held at the training mean**;
* `arm_flex` in a shot reaches about 150°, where the training data stops at 90°.

Read the shape of the curves, not the newtons. Joint contact force is the more
reliable of the two outputs.

One convention was wrong before 2026-09-02 and is worth knowing about: the video
knee angle was mapped as `-(180 - v)`, flexion negative, which is the
gait2392/GPK convention. This model is Rajagopal, where knee flexion is
**positive** (0–160°). A 90° knee was being fed in as −90°, a value the
coordinate never takes in training. `_VIDEO_TO_OPENSIM` in `shot_analysis.py`
now carries the training ranges next to each conversion.
