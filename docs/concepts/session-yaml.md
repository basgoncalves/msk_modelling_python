# session.yaml

One file per session; the single place that says what the session contains
and how each iteration differs. Keys are validated against
{py:class}`bioscout.session.config.SessionKeys` and
{py:class}`bioscout.session.config.IterationKeys` — an unknown key is reported
and ignored, never silently used.

```yaml
subject: K2L
session: '11_03_24'
body_mass: 90.24            # kg; else estimated from the static trial
measured_side: l            # instrumented / analysed leg: l | r | both
instrumented_joint: knee
static_trial: Static_01
models_dir: models          # relative to the project
setup_dir: setupFiles
emg_map:                    # analog channel -> model muscles it represents
  EMG_Channels_EMG01_vast_lat_l: [vaslat_l, vasint_l]
  ...
trials:
  Gehen_01: {type: walking, side: both, time_range: [5.017, 6.783],
             emg_normalisation: true, calibration: false}
iterations:
  gpkv4_pct20:
    model_generic: ./generic/GPK/GPK_v4_016.osim
    model_scaled:  ./personalised/<subject>/<session>/gpkv4_scaled.osim
    so_actuators:  percent_20                     # or a .xml path, see SO actuators
    so_actuators_template: ./actuators_gpkv4.xml
    mvic_scaling: 1.0 | handsfield                # max isometric force scaling
    ceinms: {alpha: 1, beta: 1, gamma: 30}
```

* **trials** — `type` drives event detection and which literature bands are
  overlaid; `time_range` is the analysis window; `emg_normalisation` says
  whether the trial takes part in the session-max EMG reference.
* **iterations** — any number. An iteration may point at another one's scaled
  model; it then reuses that model's IK/ID/MA (only the stages after them
  depend on the iteration).
* `<subject>` / `<session>` placeholders are filled from the file.
