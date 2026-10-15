# API reference

Generated from the docstrings. The packages, in the order a run touches them:

```{eval-rst}
.. autosummary::
   :toctree: _autosummary
   :recursive:

   bioscout.session
   bioscout.core
   bioscout.simulate
   bioscout.model
   bioscout.emg
   bioscout.plot
   bioscout.utils
   bioscout.config
   bioscout.cli
   bioscout.pipeline
```

## Where to start

| you want to... | look at |
|---|---|
| open a session and run stages | {py:class}`bioscout.session.recording.Session`, {py:class}`bioscout.session.iteration.Iteration` (`run`, `scale_model`, `run_emg_normalise`) |
| work on one trial of one iteration | {py:class}`bioscout.core.analysis.Analyse` (`run_ik`, `run_id`, `run_ma`, `run_so`, `run_jra`, `run_jra_contributions`, `plot_*`) |
| understand session.yaml keys | {py:mod}`bioscout.session.config` (`SessionKeys`, `IterationKeys`) |
| SO reserve / residual actuators | {py:mod}`bioscout.simulate.so_actuators` (`plan`, `percent_spec`, `percent_reserves`) |
| muscle contributions to JCF | {py:mod}`bioscout.core.jcf_contributions` (`decompose`, `build_groups`, `summarise`) |
| folder layout resolvers | {py:mod}`bioscout.session.layout` |
| figures | {py:mod}`bioscout.plot` (`task_figure.TaskStrip`, `emg_figure`, `jcf_coverage`, ...) |
