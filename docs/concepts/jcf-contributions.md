# Muscle contributions to the joint contact force

{py:mod}`bioscout.core.jcf_contributions`, run per trial by
{py:meth}`bioscout.core.analysis.Analyse.run_jra_contributions`.

## Why it is exact

At fixed kinematics the JointReaction analysis is **linear in the applied
forces**. Split the SO force file into a non-muscle part and muscle groups
$g$:

$$\mathbf F_{JCF}(t) = \underbrace{\mathbf F_{base}(t)}_{\text{all muscles}=0} + \sum_g \underbrace{\left[\mathbf F_{g}(t) - \mathbf F_{base}(t)\right]}_{\text{contribution of } g}$$

* **baseline** — JRA with every muscle force set to 0 but residuals, reserves
  and GRF kept: what gravity, segment inertia, the GRF and the actuators push
  through the joint;
* **group run** — JRA with only group $g$'s muscles on;
* **total** — JRA with all muscles, re-run so the check compares like with like.

`closure.txt` reports $\max_t|\mathbf F_{base}+\sum_g \mathbf c_g - \mathbf F_{total}|$;
it should be ~0 N. If not, the decomposition is not trustworthy.

## What is reported

`contributions_so/contributions.csv` (long format): per frame, joint and
source, the vector `fx, fy, fz` (additive) and

$$\text{along\_total}_g = \mathbf c_g\cdot\frac{\mathbf F_{total}}{|\mathbf F_{total}|}$$

the projection on the total's direction. Projections add up to $|\mathbf F_{total}|$;
magnitudes do not. The figures plot it as % of $|\mathbf F_{total}|$, so
negative = the group pulls against the resultant (e.g. dorsiflexors at the knee).
{py:func}`bioscout.core.jcf_contributions.summarise` gives, per source, the value
at the frame of peak JCF, its own peak and its impulse.

## Groups and cost

`groups={name: [muscle columns]}` (default: `settings.MUSCLE_GROUPS` +
`EXTRA_GROUPS`, leftovers one source each). Cost = one JRA per group + 2.
Runs are independent, so they are fanned out over `n_jobs` processes
(default min(CPUs-1, 8), env `BIOSCOUT_JCF_JOBS`).

Decomposing only the analysed leg (its groups, its other muscles as one
source, the other leg as one source) keeps the result exact for that leg's
joints and roughly halves the runs; the other leg's joints are then only split
coarsely.

## Traps
* Never strip the residual/reserve/GRF columns: the analysis cannot balance
  and the JCF stops depending on the muscles at all.
* Always go through `openSim.run_jra`, never a hand-made AnalyzeTool.
