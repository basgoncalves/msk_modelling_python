# Scaling assumes the powerlifting marker set — FIXED 2026-09-07

> **Status: fault 1 fixed and tested; fault 2 believed fixed, NOT verified
> against a real model.** `scale_measurements` now
> takes a `{expected: actual}` alias map through `compute_joint_centres`,
> `augment_static_trc` and `resolve_spec`; `openSim.scale_model` accepts
> `marker_aliases=`; and `bioscout scale` is a new interactive verb that works
> the map out by asking. `bioscout model joint-centres --alias EXPECTED=ACTUAL`
> does the same for a bare TRC. The history below is kept because the SHAPE of
> the failure is the point: the crash was never the danger.
>
> Verified on the real FAIS marker names: **1 of 13 measurements before, 13 of
> 13 after**, and the floor refuses the 1-of-13 case rather than scaling a
> pelvis onto generic femurs. That test is pure-Python (spec resolution and the
> floor); it did NOT run OpenSim.
>
> Fault 2 (`upper_limb` reaching an arm-less model) should now resolve on its
> own: with `SACR3`/`STRN`/`XIPH` aliased the measurement becomes satisfiable,
> `build_measurement_set` then finds none of its bodies on GPK and drops it, so
> nothing names `humerus_l`. That is reasoning, not evidence — it needs one run
> against a real arm-less model to confirm, and the ScaleSet path that produced
> the original crash was never traced.


Written 2026-09-07 from the FAIS project, which is the first FAIS arm to ask
bioscout to scale anything. Two faults, both in
`bioscout/utils/scale_measurements.py` + `Iteration.scale_model`. Neither
produces an error that names the real cause.

## 1. The marker names are hard-coded to one laboratory

`DEFAULT_SPEC`, `_MIDPOINT_JC` and `_HARRINGTON_MARKERS` name the powerlifting
markers directly. There is no hook to override them: `build_measurement_set`
takes a `spec=`, but `Iteration.scale_model` never passes one and nothing reads
a project-level spec (`grep -rn "measurement_spec\|scale_spec"` returns
nothing). `project.yaml` — the file whose whole purpose is lab facts that differ
from bioscout's defaults — cannot express this.

Marker naming is the definition of a lab fact. FAIS records:

| bioscout expects | FAIS records | what is lost |
|---|---|---|
| `LPSI`, `RPSI` | `LSACR`, `RSACR`, `USACR` | Harrington cannot run → **no hip joint centre** |
| `RKNEL`, `RKNEM` | `RLFC`, `RMFC` | no knee joint centre |
| `RMALL`, `RMALM` | `RLMAL`, `RMMAL` | no ankle joint centre |
| `RTOE` | `RMT1`, `RMT2`, `RMT5` | no foot length |
| `SACR3`, `STRN`, `XIPH` | `C7`, `CLAV`, `T10` | no trunk measurement |
| `LASI`, `RASI` | `LASI`, `RASI` | the only match |

Result on a real FAIS session:

```
[scale] no joint centres could be computed from marker_experimental.trc
        — femur/tibia scaling will have no measurement basis.
[scale] MeasurementSet: 1 measurements
[scale]   pelvis_z: LASI-RASI -> pelvis[Z]
[scale]   SKIPPED pelvis_x, pelvis_y, femur_r, femur_l, tibia_r, tibia_l,
          foot_r_xy, foot_r_z, foot_l_xy, foot_l_z, torso, upper_limb
```

One measurement of thirteen. **This is the dangerous part**: had ScaleTool
completed, it would have written a model with a scaled pelvis width and generic
femurs, tibiae and feet, and every stage downstream would have run happily on
it. Segment lengths wrong by 10-20 % produce moment arms and contact forces that
are wrong by more, and nothing in the output says so.

`SKIPPED` at `[scale]` level is the right thing to print, but it is a
progress-log line among hundreds. A run that ends up with 1 of 13 measurements
has not "scaled with some measurements missing" — it has failed to scale, and
should refuse. Suggested: a floor (no joint centre at all, or no long-bone
measurement, is fatal) rather than a count.

### Suggested fix

Move the three name constants into the spec, and let `project.yaml` supply
either a full spec or just a rename map:

```yaml
batch:
  scale_marker_aliases:
    LPSI: LSACR
    RPSI: RSACR
    RKNEL: RLFC
    RKNEM: RMFC
    RMALL: RLMAL
    RMALM: RMMAL
```

An alias map is much smaller than a spec and covers every case seen so far;
`build_measurement_set(spec=)` already exists for anyone who needs more.

## 2. `upper_limb` reaches a model that has no arms

GPK_v4_016's bodies stop at `torso`. The `upper_limb` entry of `DEFAULT_SPEC`
scales `humerus_*`, `ulna_*`, `radius_*`, `hand_*`. The log correctly reports it
as skipped —

```
[scale]   SKIPPED upper_limb (markers SACR3,STRN,XIPH; bodies hand_l,hand_r,
          humerus_l,humerus_r,radius_l,radius_r,ulna_l,ulna_r)
```

— and ScaleTool then dies on exactly those bodies:

```
[scale ERROR] pre/gpk: std::exception in 'bool OpenSim::ScaleTool::run() const':
Failed to connect Socket 'parent_frame' of type PhysicalFrame
(details: Component 'ModelScaling' could not find '/bodyset/humerus_l'
 of type PhysicalFrame.)
```

So the measurement is filtered out of the MeasurementSet but its bodies still
reach the ScaleSet. The docstring above `DEFAULT_SPEC` says entries are emitted
"only for the bodies that exist in this model" — that filter is not being
applied on the ScaleSet path. `model_body_names()` already exists; the ScaleSet
needs the same intersection the MeasurementSet gets.

This one is a clean bug with a clean repro: scale any arm-less model (GPK,
Lernagopal's lower-limb variants) with the default spec.

## Reproducer

```
model  : bioscout/models/GPK_v4_016.osim          (no arm bodies)
static : any TRC without LPSI/RPSI/RKNEL/RKNEM/RMALL/RMALM
call   : Session.open(<session>).iteration("gpk").run(do_scale=True, ...)
```

Fault 2 raises; remove the `upper_limb` entry and fault 1 remains, silently.

## How FAIS is working around it

Not by patching bioscout: the GPK arm is declared `prescaled: true` and the
model is built outside the pipeline, which is how every other FAIS model was
already made. `FAIS_machine_learning/code/add_joint_centres.py` writes the six
joint centres into the static TRC under the names the project's own
`markers_FAIS.xml` and `setup_files/setup_scale.xml` already use, importing
`scale_measurements.harrington_hjc` rather than reimplementing the regression.

Worth noting for the alias-map design: that script needed only a rename map plus
the two midpoint rules — no new maths — which is evidence the alias approach is
sufficient.


---

## What was added

| where | what |
|---|---|
| `utils/scale_measurements.py` | `EXPECTED_MARKERS`, `apply_aliases`, `resolve_spec`, `suggest_alias`; `compute_joint_centres(..., aliases=)`, `augment_static_trc(..., aliases=)` |
| `utils/openSim.py` | `scale_model(..., marker_aliases=)`, threaded into the joint-centre step and the measurement set |
| `scale_interactive.py` | the `bioscout scale` command: prompting, marker resolution, the measurement table, the floor |
| `cli.py` / `__main__.py` | the `scale` verb; `--alias` on `model joint-centres` |

```bash
bioscout scale                       # asks for everything
bioscout scale --model g.osim --static s.trc --mass 78.4 --dry-run
bioscout scale --alias LPSI=LSACR --alias RKNEL=RLFC -y
bioscout model jc static.trc --alias LPSI=LSACR
```

`suggest_alias` offers a shortlist from the markers the TRC actually contains,
same side first. It is a menu for a human, never an automatic substitution:
picking the wrong malleolus is not an error anything downstream can detect.

## The floor

`bioscout scale` refuses (exit 2) when the surviving measurements do not cover
the pelvis, both femurs and both tibiae. Reproducing the FAIS case:

```
NO aliases:    joint centres NONE   | 1 of 13  [pelvis_z]
               floor gaps: right femur, left femur, right tibia, left tibia
               -> REFUSE
with aliases:  joint centres all 6  | 13 of 13
               -> proceed
```

That refusal is the whole point. ScaleTool is perfectly happy to apply a scale
factor of 1.0 to every body and hand back generic geometry wearing the
subject's mass; the model loads, IK solves, joint moments look plausible.
