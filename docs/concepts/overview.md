# Overview: the objects and how they relate

```
Project ─┬─ Subject ── Session (one recording day, one session.yaml)
         │                 │
         │                 ├── trials       Static_01, Gehen_01, Stairsup_01 ...  (model-independent)
         │                 └── iterations   gpkv4, gpkv4_pct20, elena ...         (model / setting variants)
         │                        │
         │                        └── Iteration × trial  =  Analyse   (the unit every stage runs on)
         └─ settings.py / project.yaml (project-wide defaults)
```

| object | class | what it is |
|---|---|---|
| project | {py:class}`bioscout.core.analysis.Project` | a folder with `simulations/`, `models/`, `setupFiles/`; iterates subjects/sessions |
| session | {py:class}`bioscout.session.recording.Session` | `simulations/<subject>/<session>/` + its `session.yaml`; owns the trials and declares the iterations |
| iteration | {py:class}`bioscout.session.iteration.Iteration` | one **variant** of the analysis: a model (generic → scaled), an actuator set for SO, EMG map, CEINMS settings... Runs the stages over the session's trials |
| trial analysis | {py:class}`bioscout.core.analysis.Analyse` | one iteration × one trial: holds every file path of that trial and the `run_*` / `plot_*` methods |

The split that matters most: **trials are shared, iterations are not.**
Markers, GRF, EMG and the in-vivo reference live once per trial in
`2_experimental/<trial>/`; every iteration writes its own results into
`3_iterations/<iteration>/<trial>/`. Comparing two models or two actuator sets
on the same data is therefore just two iterations of one session.

```python
import bioscout as bs
s = bs.Session(r"...\simulations\K2L\11_03_24")
it = s.iteration("gpkv4_pct20")              # one variant
it.run(trials=["Gehen_01"], do_exbiomec=True, do_muscle_analysis=True, do_so=True)
tr = it.trial("Gehen_01")                    # an Analyse
tr.run_jra_contributions(forces_type="so")
```

The command line (`bioscout ...`, {py:mod}`bioscout.cli`) is a thin layer over
the same calls.

See {doc}`data-layout` for the folders, {doc}`session-yaml` for the
configuration and {doc}`pipeline` for what each stage computes.
