# The pipeline: what each stage computes

`Iteration.run(...)` flags, in run order. Each stage reads the previous
stage's files from disk, so stages can be re-run individually; existing outputs
are kept unless `replace=True`.

| flag | stage | method | reads | writes |
|---|---|---|---|---|
| `do_scale` | scaling | `Iteration.scale_model` | static .trc, generic model, scale setup | `models/personalised/.../<it>_scaled.osim` |
| `export` | c3d → inputs | `Session.export` | `1_c3dfiles/*.c3d` | `2_experimental/<trial>/*`, EMG normalisation |
| `do_exbiomec` | IK, ID | `Analyse.run_ik`, `run_id` | markers, model, GRF | `external_biomechanics/` |
| `do_muscle_analysis` | MA | `Analyse.run_ma` | IK, model | `muscle_analysis/` |
| `do_so` | SO → muscle moments → JRA | `Analyse.run_so`, `run_jra` | IK, ID, MA, actuators | `static_optimisation/`, `joint_contact_forces/` |
| (separate) | JCF contributions | `Analyse.run_jra_contributions` | SO forces, IK, GRF | `joint_contact_forces/contributions_so/` |
| `do_rra` | residual reduction | `Analyse.run_rra` | IK, GRF | `residual_reduction/` (diagnostic) |
| `do_forward` | CMC + forward | | RRA or IK | `forward_simulation/` |
| `do_ceinms` | EMG-informed (CEINMS) | `run_ceinms_calibration`, `run_ceinms_exe` | EMG, MA, ID | `ceinms/`, JRA on CEINMS forces |

## Inverse kinematics / dynamics
OpenSim IKTool (weighted marker least squares, weights per body from
`ik_weights`) and IDTool (net joint moments, $\tau = M(q)\ddot q + C(q,\dot q) + G(q) - J^T F_{ext}$)
with the GRF applied to the bodies named in `GRF.xml`.

## Muscle analysis
OpenSim MuscleAnalysis over the IK motion: musculotendon length, moment arm
of every muscle about every coordinate, and (not equilibrated in this mode)
fibre states. Moment arms feed the muscle-moment check and the figures; SO
computes its own internally.

## Static optimisation
Per frame, OpenSim StaticOptimization solves

$$\min_{a}\ \sum_m a_m^2 + \sum_k u_k^2 \quad \text{s.t.}\quad \sum_m a_m F^{max}_m f(l,v)\, r_{m,j} + \sum_k u_k\,F^{opt}_k\,\delta_{kj} = \tau^{ID}_j \ \ \forall j$$

with muscle activations $a_m\in[0,1]$ and actuator controls $u_k$ (reserves
on joint coordinates, residuals on the pelvis). An actuator's
`optimal_force` is both its **price** in the cost ($(\tau/F^{opt})^2$) and,
with controls bounded to ±1, its **cap**. See {doc}`so-actuators`.

After SO, `muscle_analysis/_MuscleMoments_<dof>_so.sto` = SO force × moment
arm per muscle: the part of the ID moment the muscles carry; the rest is the
reserves'.

## Joint reaction analysis
OpenSim JointReaction with the SO forces (muscles **and** every
reserve/residual column, else the system does not balance and the force is
~100× too large — bioscout refuses to run it unbalanced). Output:
`joint_contact_forces/output_so.sto`, the force each joint transmits (child on
parent, expressed in the frames set in `setup_JRA.xml`). Peaks are reported
as the interior 99th percentile because the first/last frames carry
spline-edge spikes.

## JCF contributions
See {doc}`jcf-contributions`.
