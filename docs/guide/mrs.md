# `bioscout simulate mrs` — Muscle Redundancy Solver (KU Leuven)

Wraps [MuscleRedundancySolver](https://github.com/KULeuvenNeuromechanics/MuscleRedundancySolver)
(MATLAB + CasADi). BioScout writes the inputs, MATLAB runs `solveMuscleRedundancy`,
BioScout reads the results back as OpenSim `.sto`.

## 1. One-time setup

```bash
git clone https://github.com/KULeuvenNeuromechanics/MuscleRedundancySolver
```

In MATLAB, install CasADi (https://web.casadi.org/get/) and add it to the path,
and make sure the OpenSim MATLAB API is configured (`configureOpenSim.m`).

Tell BioScout where things are — either environment variables:

```bash
export BIOSCOUT_MRS_DIR="C:/Git/MuscleRedundancySolver"
export BIOSCOUT_MATLAB="C:/Program Files/MATLAB/R2023b/bin/matlab.exe"
```

or in your project `settings.py` (`class BatchSettings`):

```python
mrs_dir   = r"C:\Git\MuscleRedundancySolver"
matlab_exe = r"C:\Program Files\MATLAB\R2023b\bin\matlab.exe"
enable_mrs = True
```

Check it:

```bash
bioscout simulate mrs check
```

## 2. Run a trial

Needs IK and ID already done (`external_biomechanics/joint_angles.mot`,
`inverse_dynamics.sto`).

```bash
# plain muscle redundancy, all DOFs found in the ID file
bioscout simulate mrs run path/to/trial

# pick DOFs / muscles / time window, and where results go
bioscout simulate mrs run path/to/trial --dofs hip_flexion_r knee_angle_r ankle_angle_r \
    --time 0.8 2.1 --mesh 100 --out path/to/trial/mrs

# EMG-constrained
bioscout simulate mrs run path/to/trial --emg inputs/emg_filtered_normalised.mot \
    --emg-muscles soleus_r med_gas_r vas_lat_r

# calibration: estimate optimal fibre length + tendon slack length
bioscout simulate mrs run path/to/trial --calibrate soleus_r med_gas_r --estimate-kT soleus_r
```

From Python:

```python
from bioscout.core.analysis import Analyse
Analyse(trial).run_mrs(dofs=["hip_flexion_r", "knee_angle_r"],
                       calibrate=["soleus_r"], emg=True)
```

## 3. Outputs — `<trial>/mrs/`

| file | what |
|---|---|
| `mrs_config.json` | exactly what MATLAB was given (the `Misc` struct) |
| `mrs_matlab.log` | full MATLAB console output |
| `MRS_Results.mat` | raw `Results`, `DatStore`, `Misc` |
| `MRS_<problem>_activation.sto` | activations, one file per solved problem (`genericMRS`, `MTE`, `validationMRS`) |
| `MRS_<problem>_excitation.sto` | excitations |
| `MRS_<problem>_force.sto` | tendon forces (N) |
| `MRS_<problem>_fibre_length_norm.sto` | normalised fibre lengths |
| `MRS_<problem>_reserves.sto` | reserve actuators (Nm) |
| `MRS_parameters.json` | estimated scaling factors (calibration runs only) |

`genericMRS` is the standard solve; `MTE` is the parameter-estimation solve;
`validationMRS` re-solves with the estimated parameters.

## 4. Code map

```
bioscout/mrs/
  config.py   MRSConfig dataclass -> Misc, written as mrs_config.json
  run_mrs.m   MATLAB driver: reads the JSON, calls solveMuscleRedundancy, saves .mat
  runner.py   finds MATLAB + the toolbox, runs `matlab -batch`, exports results
  io.py       MRS_Results.mat -> .sto / .json
  cli.py      `bioscout simulate mrs check|run`
```

Every `MRSConfig` field maps 1:1 to a `Misc.<Field>`; the mapping is
`_MISC_MAP` in `config.py`, so anything the MATLAB README documents can be set
without touching the driver. Fields left `None` are not written and MRS applies
its own default.

## Notes

- The toolbox is **not** vendored — it stays a separate checkout you can update.
- `--calibrate` needs explicit muscle names (MRS estimates named muscles only).
- A run overwrites nothing by default: pass `--replace` to re-solve.
