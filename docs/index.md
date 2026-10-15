# bioscout

bioscout runs OpenSim-based musculoskeletal pipelines over **sessions** of
motion-capture data: scaling → inverse kinematics → inverse dynamics → muscle
analysis → static optimisation → joint reaction (contact) forces, plus muscle
contributions, CEINMS, RRA/CMC, EMG processing and the figures that compare
**iterations** (model or setting variants) of the same trials.

These pages come in three parts:

* **Concepts** — how the pieces relate and how each quantity is computed.
  Start here.
* **Guides** — task-oriented notes (project setup, plotting, MRS, ...).
* **API reference** — every public module, class and function, generated from
  the docstrings in the code (so it is only as current as the docstrings).

```{toctree}
:maxdepth: 2
:caption: Concepts

concepts/overview
concepts/data-layout
concepts/session-yaml
concepts/pipeline
concepts/so-actuators
concepts/jcf-contributions
concepts/emg
concepts/outputs
```

```{toctree}
:maxdepth: 1
:caption: Guides

guide/project-setup
guide/plotting
guide/jcf-contributions
guide/jcf-direction
guide/model-ma-check
guide/mrs
guide/releasing
```

```{toctree}
:maxdepth: 2
:caption: API reference

api
```

```{toctree}
:maxdepth: 1
:caption: History

history/2026-09-08-v3-restructure-plan
history/2026-08-17-implementations
history/2026-08-24-proposal-models-and-cwd
history/2026-09-07-scaling-marker-names
history/2026-08-25-gui-fixes
history/2026-08-11-bops-issues
history/settings-py-annotated
```
