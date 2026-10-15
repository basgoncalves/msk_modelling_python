# Outputs and figures

Per **trial × iteration** (written by the stages, `3_iterations/<it>/<trial>/`):

| figure | where | shows |
|---|---|---|
| `kinematics_moments.png`, `inverse_dynamics.png`, `residuals.png` | `external_biomechanics/` | IK / ID / pelvis residuals, task strip on top |
| `muscle_moments_<side>.png`, `muscle_groups.png` | `static_optimisation/` | SO muscle moment vs ID, group forces vs EMG |
| `jrf_so.png`, `jrf_so_coverage_*.png` | `joint_contact_forces/` | JCF per joint (+ implant, literature), contact location |

Per **trial** (shared): `grf_events.png`, `emg_processing.png` in `2_experimental/<trial>/`.

Every time-series figure uses the **task strip** layout
({py:class}`bioscout.plot.task_figure.TaskStrip`): posed skeleton at the foot
events with GRF arrows, vertical GRF with events, then the figure's own rows on
a shared time axis.

## Comparing iterations

`<session>/4_outputs/` holds cross-iteration figures (built by test/analysis
scripts with `charite_tools.compare` and the plotting helpers), e.g.

* `muscle_dynamics_<family>_<trial>.png` — |JCF| vs implant on top; per muscle
  group: force, contribution to JCF (% of |JCF|), activation (+EMG), MTU length;
* `moments_<family>_<trial>.png` — ID vs summed muscle moment per DOF;
* `tradeoff_<family>.png` — JCF error and EMG error against muscle-moment error,
  normalised, quadratic fit and elbow.

### Error metrics used there
* **JCF error** — RMSE of |JCF| vs the implant (BW) over frames where the
  measured foot is on a plate and the ID pelvis residual < 5 % BW.
* **muscle-moment error** — mean over frames of $|\sum_m F_m r_m - \tau^{ID}| / \max(|\tau^{ID}|, 0.05\max|\tau^{ID}|)$.
* **EMG error** — $1 - r$, r = correlation of the normalised EMG with the mean SO
  activation of the channel's muscles (scale-free).
