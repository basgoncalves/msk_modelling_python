# SO actuators: reserves and residuals

{py:mod}`bioscout.simulate.so_actuators`

Rule per iteration (`so_actuators` in session.yaml):

* **set to a file** — that file's actuators *replace* the model's non-muscle
  actuators: SO runs on `<model>_noact.osim` (muscles only) + the file as a
  force set. The file actually used is copied to
  `static_optimisation/actuators_so.xml`, and JRA uses the same set.
* **unset** — the model's own actuators are used.
* **neither has any** — warning: SO would force the muscles to carry the pelvis
  residual too.

Pelvis residuals (FX FY FZ MX MY MZ) that cannot carry a trial's own ID
residual are raised to 10 % above its peak and logged (`update_actuators`).

## `percent_XX`

`so_actuators: percent_20` is a **recipe, not a file**: per trial, every
reserve (CoordinateActuator named `*_reserve`) in `so_actuators_template` gets

$$F^{opt}_{reserve,j} = \max\left(1,\ 0.20\cdot\max_t|\tau^{ID}_j(t)|\right)$$

from that trial's own ID ({py:func}`bioscout.simulate.so_actuators.percent_reserves`),
so a reserve can carry at most 20 % of its coordinate's peak net moment and
is priced accordingly. Residuals and other actuators keep the template's
values.

Reserves listed in a template comment keep the template value:

```xml
<!-- percent_fixed: knee_adduction_l_reserve knee_adduction_r_reserve -->
```

(e.g. knee ab/adduction, carried mostly by condyle contact and ligaments, pinned
at 50 N·m while everything else is 20 %).

## Reading the result

* **reserve share** — $|u_k F^{opt}_k| / |\tau^{ID}_j|$ per frame; in SO this
  equals the per-frame muscle-moment error $|\sum_m F_m r_{mj} - \tau^{ID}_j|/|\tau^{ID}_j|$.
* a reserve that matches a passive-tissue moment (sign, phase, size) is
  defensible; one carrying frontal/transverse hip moments is usually a sign of
  muscle-geometry error.
