# Data layout

```
<project>/
  setupFiles/                     OpenSim setup templates (setup_IK/ID/SO/JRA.xml), actuator sets,
                                  markersets, scale setups
  models/
    generic/<model>/              unscaled models (+ Geometry)
    personalised/<subj>/<ses>/    scaled models, one per iteration that scales
  simulations/<subj>/<ses>/
    session.yaml                  trials, iterations, emg_map, body mass, measured side ...
    1_c3dfiles/                   raw captures (staged; hard links where possible)
    2_experimental/<trial>/       MODEL-INDEPENDENT inputs, shared by all iterations
        marker_experimental.trc   markers
        grf.mot, GRF.xml          ground reaction forces + which body each plate loads
        emg.mot                   raw EMG
        emg_filtered_normalised.mot  envelope, normalised to the session max (0-1)
        invivo_jcf.mot            instrumented-implant force (Charité / OrthoLoad data)
        grf_events.png, emg_processing.png, movement_detection.*   QC
      maxemg.txt                  per-channel session max (and which trial set it)
    3_iterations/<iteration>/<trial>/
        external_biomechanics/    IK (joint_angles.mot), ID (inverse_dynamics.sto)
        muscle_analysis/          MuscleAnalysis: lengths, moment arms; _MuscleMoments_<dof>_so.sto
        static_optimisation/      SO forces / activations, actuators_so.xml actually used
        joint_contact_forces/     output_so.sto (JRA), jrf_so.png, contributions_so/
        residual_reduction/, forward_simulation/, ceinms/ ...  (optional stages)
    4_outputs/                    cross-iteration comparison figures for the session
  logs/                           one log per run
```

Resolvers in {py:mod}`bioscout.session.layout` (`experimental_root`,
`iteration_path`, ...) accept both this numbered layout and the older flat one
(`experimental/`, `c3dfiles/`, iteration folders beside them); always go
through them rather than joining names by hand.

`Analyse` knows every file of one iteration × trial as an attribute
(`ik`, `id`, `so_forces`, `jra`, `emg`, `emg_filtered_normalised`, ...);
paths that point at shared inputs resolve into `2_experimental/<trial>/`.
