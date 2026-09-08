# bioscout CLI + package restructure — plan

Goal: the package tree under `bioscout/` should mirror the verb tree of
`bioscout -h`, so "where does the `session` code live?" always has the same
answer: `bioscout/session/`. Today it doesn't — `session.py` (258KB) lives in
`bioscout/utils/`, `openSim.py` (233KB) and `ceinms/` live in `bioscout/utils/`,
and the `model` verb's actions are spread across four unrelated top-level
folders (`model/`, `model_edit/`, `change_moment_arms/`, `muscle_inspect/`).

## 0. Status (as of 2026-09-08)

**Shipped** — CLI-layer part of stage 1 only, no file moves yet, so the
package tree in section 2 is still entirely aspirational:
- `bioscout simulate exbiomec|ma|so|ceinms SESSION_PATH` added, wrapping
  `Iteration.run()` directly (needs `session.yaml`). Covers the stage
  groupings that already existed as separate switches; still no honest
  standalone `ik`/`id`/`jra`/`cmc`.
- `run` and `pipeline.run_subject()` (+ the dead `run_subject_mode()` and
  the now-orphaned `_run_session_ceinms()`) were **deleted outright**, not
  kept as a hidden alias like stage 1 originally proposed — an explicit
  decision, not a plan change of heart. Net effect: no single CLI call
  currently batches a pipeline run across subjects or does
  export/scale/reset in one step; `bioscout -b settings.py` still drives
  `run_project()`/`run_pipeline()` for multi-subject batches in the
  meantime. Rebuilding that sequencing under `session`/`simulate` is
  unstarted.
- `compare_osim_models` (dead code) and `export_c3d` -> `c3d_to_trc`
  (rename) from section 3's open items are both done.

**Not started**: `project` folding into `init`; stages 2-12 below (no files
have moved — `openSim.py`/`session.py`/`model_edit/`/`change_moment_arms/`/
`muscle_inspect/`/`figures.py`/etc. are all still exactly where section 2
says they are "today"). Some of this work looks to be happening already but
outside this plan's stages — `bioscout/mrs/` and a `scale_interactive.py`
exist in the working tree — worth reconciling against stage 4/3 before
either goes further, so the two don't diverge from what's written here.

## 1. Target CLI tree

```
bioscout -h
  gui       launch the GUI (also the default with no verb)
  init      create a project: folders, models, templates and project-level
            config (project.yaml)                       [merges old init + project]
  model     check, edit, compare and validate .osim models -- stays a
            top-level verb, unchanged in name; NOT nested under `simulate`,
            because nothing under it simulates anything, it creates/edits a
            model:
              check          can every model still find its bone meshes?
              edit           scale, set mass, change forces, moment arms, markers
              compare        dimensions and segment masses across models
              tune-ma        adjust a muscle's moment arm, interactively
                             (renamed from `ma` -- would otherwise collide
                             with `simulate ma`, the muscle-analysis stage;
                             the two aren't nested under the same parent
                             any more either, so this rename is now belt
                             and braces rather than load-bearing)
              validate       moment arms, fibre lengths, strength vs literature
              joint-centres  (jc)
              tps            build an MRI-personalised model (interactive)
              scale          scale a model by answering questions (interactive)
                             -- moved here FROM the old openSim/msk group:
                             scaling produces the personalised model, which
                             is model creation, not a simulation step
  simulate  run an OpenSim/CEINMS simulation on an existing model, usable
            standalone from the terminal (renamed from `openSim`/the `msk`
            package -- these all consume a model and produce results,
            unlike anything under `model` above):
              ik            inverse kinematics
              id            inverse dynamics
              ma            muscle analysis
              so            static optimisation
              cmc           (if/when supported)
              ceinms        calibrate / execute CEINMS
              jra           joint reaction analysis
              mrs           muscle redundancy solver -- now `simulate mrs`.
                            No `bioscout mrs` alias kept; the old top-level
                            shortcut is just gone once this ships.
              gapfill       marker gap-filling, immediately before `ik` needs
                            complete marker data
  session   create, export, classify, scale or reset a session; batches
            `simulate`'s steps across subjects/iterations and makes it easy
            to compare between iterations          [absorbs old `run`/`run --batch`]
  plot      figures from the results on disk (incl. the project figure
            catalogue, moved in from `bioscout/figures.py`, and the Collings
            muscle-ranking figure, moved in from `utils/collings.py`)
  utils     environment, dependencies, docs, editor setup
  lab       EXPERIMENTAL (3.0): video and wearable tracking
```

Dropped as top-level verbs: `run`, `project` (folded into `init`), `tps`
(nested under `model`, since what it produces IS a model), `mrs` (nested
under `simulate`, no compat alias). `scale` also disappears as a bare
top-level verb but resurfaces as `model scale`. `model` itself is NOT
dropped -- it stays top-level, per the split above.

There's no `simulate run`/`openSim run` subcommand and no top-level "run the
whole single-subject pipeline" command — `session` calls the individual
`simulate` steps in sequence itself when it batches across subjects/
iterations, rather than that sequencing being its own user-facing verb.

## 2. Target package tree

```
bioscout/
  __init__.py, __main__.py, cli.py
  config/            unchanged — GUI's config_manager.py + default_config.yaml
  core/              Project/Subject/Trial + the analysis engine
                       <- utils/analysis.py (357KB), core/analysis_runner.py,
                          core/project_analysis.py (already here),
                          utils/subject_registry.py (per-project subjects.json
                          -- analysis.py's own Subject class reads it directly,
                          so it belongs with core, not lab; load_tracking/
                          keeps using it via an import, same as gui/ does today),
                          utils/jcf_contributions.py (muscle contributions to
                          joint contact force by force superposition -- a
                          computation only analysis.py calls, not a figure
                          builder despite living near the plot dispatchers)
  tests/             unchanged
  gui/               unchanged (the `gui` verb)
  emg/               NEW, top-level, NOT its own CLI verb -- a domain package
                     that `session/` (export, channel mapping) and
                     `simulate/ceinms/` (excitation QC) both import from, the
                     same way everything already imports `core/`:
                       <- utils/emg.py, utils/emg_analysis.py,
                          utils/emg_channels.py, utils/emg_filter.py,
                          utils/emg_normalise.py
                     Reasoning: emg_filter.py alone is imported from gui/,
                     pipeline.py, session.py AND analysis.py -- it's not
                     narrowly an openSim concern, and it's too domain-specific
                     (rectify/envelope/MVC-normalise, NMF muscle synergies,
                     CEINMS-readiness frequency QC) to call "shared" generic
                     code. emg_filter.py itself needs no split: it's purely
                     filter-SETTINGS resolution (session.yaml -> BatchSettings
                     -> defaults), not signal processing, so it stays whole
                     here. The actual generic signal-processing primitives
                     (butter+filtfilt band-pass/low-pass) live inline in
                     emg_normalise.filter_emg() today -- those get pulled out
                     into utils/filters.py as bandpass()/lowpass(), with
                     filter_emg() becoming a thin EMG-specific caller (see
                     utils/ below). NOTE: `simulate/`'s run_emg_normalise
                     (the pipeline STAGE that calls this normalisation on a
                     session's trials) stays in `simulate/`, not here -- see
                     below; it's a pipeline stage, not EMG domain logic.
  model/             the WHOLE `model` verb, un-nested and top-level (not
                     under `simulate` -- see CLI tree above):
                       <- model/ (already: check, geometry, verify)
                          model_edit/ (-> model/edit/, backs `model edit`)
                          change_moment_arms/ (-> model/moment_arms/, backs `model tune-ma`)
                          muscle_inspect/ (-> model/inspect/, backs `model validate`)
                          tps_personalise/ (-> model/tps/, backs `model tps`)
                          utils/model_report.py (-> model/report.py -- the
                          direct implementation behind `model compare`,
                          model_edit/ops/inspect.py literally says
                          `delegates_to="bioscout.utils.model_report.compare_models"`)
                          utils/scale_measurements.py, utils/model_scaler.py
                          (-> model/scale/ -- these back `scale`, which now
                          lives under `model` too, see CLI tree)

                     PLUS its share of `utils/openSim.py` (233KB), now fully
                     categorised by reading the file and grepping every
                     caller (see "The openSim.py split" below):

                       model/opensim_base.py  -- shared low-level OpenSim
                         wrapper plumbing that BOTH model/ and simulate/
                         need (simulate/ imports from here; model doesn't
                         need anything back from simulate/, so this is the
                         natural place for it -- "loading a model" is
                         fundamentally about the model object):
                           load_model, _assembly_accuracy, _quiet_model,
                           _quiet_osim, _osim_quiet_ctx, _quiet_console,
                           terminal_warnings

                       model/edit/ (additions to the existing model_edit/ops/
                         functions, same file or split further later):
                           scale_body_masses, add_mass_to_body,
                           print_body_mass_per_segment, increase_isometric_force
                           [delegates_to-confirmed], lock_model_coordinates
                           [delegates_to-confirmed], coord_moment_arms,
                           add_wrapping_surfaces, edit_model_range_coordinates
                           [delegates_to-confirmed], add_wrapping_surface_to_model,
                           add_muscles_to_model, copy_model_coordinate,
                           checkMuscleMomentArms, muscles_per_coordinate,
                           sampleMuscleQuantities, edit_pelvis_com_actuators,
                           normalise_muscle, _strip_trailing_nulls

                       model/muscle_optimize.py -- the Modenese-2015 muscle
                         parameter optimiser, its own cluster:
                           muscle_optimimizer_Modenese2015
                           [delegates_to-confirmed], _apply_muscle_opt_settings,
                           optimMuscleParams, plot_optimization_results,
                           optimize_moment_arms, mean_squared_error (its only
                           caller anywhere in the repo is optimMuscleParams)

                       model/scale/ (joining scale_measurements.py/
                         model_scaler.py already slated here):
                           scale_model_from_xml, _sanitize_markerset_xml,
                           scale_model [delegates_to-confirmed],
                           place_markers_via_ik [delegates_to-confirmed --
                           despite the "via_ik" name this edits the model's
                           marker placements, it doesn't run a simulation]

                       DEAD CODE FLAG, not migrated anywhere: compare_osim_models
                         (line ~1734) has zero callers anywhere in the repo --
                         grep confirms nothing calls it, including tests. This
                         is separate from model_report.compare_models, which
                         IS the live `model compare` implementation. Recommend
                         deleting it rather than moving it, but flagging here
                         instead of just doing it, since it's still a judgment
                         call, not a mechanical move.

  simulate/          NEW — everything under the `simulate` verb
                     (ik/id/ma/so/cmc/ceinms/jra/mrs/gapfill). Named to match
                     the verb exactly, now that `model` (and `scale`) are out
                     of it: what's left really is just "run a simulation on
                     an existing model," so `simulate/` needs no broader
                     umbrella name like `msk/` any more.
                       <- utils/openSim.py -- the simulation-stage and
                          input-prep functions (everything NOT listed under
                          model/ above):

                       Pipeline stages (imports model/opensim_base.py for
                       load_model etc.):
                         create_setup_IK, run_ik, _sanitize_ik_leading_frames,
                         _check_ik_prerequisites, create_analysis_tool,
                         create_iaa_tool, create_setup_ID, run_id, run_ma,
                         reserve_actuator_plan, run_so, run_jra, run_iaa,
                         run_rra, run_cmc, run_energetics, run_body_kinematics,
                         run_emg_normalise (confirmed a pipeline stage, not
                         emg/ domain logic -- pipeline.py's comment literally
                         says "STAGE 3 . run_emg_normalise (session-wide MVC
                         normalisation)", called in the same sequence as
                         run_ik/run_id/etc.)

                       Simulation-input prep (trc/mot/grf/xml wrangling that
                       feeds the stages above -- not model edits, since none
                       of these touch the .osim file itself):
                         export_c3d [NAME COLLISION FLAG: there's also
                         `utils/exportC3D.py` -> `session/exportC3D.py` (the
                         session-level export orchestrator, which calls a
                         Trial.export_c3d() method that in turn calls THIS
                         function). Not a literal duplicate, but similar
                         enough names in adjacent packages that this one
                         should probably be renamed on the move, e.g. to
                         `c3d_to_trc()`, to stop them being confused],
                         convert_trc_os3_to_os4, add_joint_centers_to_trc,
                         validate_markers_used (called internally by
                         create_setup_IK), compare_marker_locations (called
                         by analysis.py as a post-IK QC step),
                         assign_grfs_to_feet (called internally by
                         create_grf_xml), create_grf_xml (called by
                         analysis.py ahead of ID), convert_mot_to_sto,
                         relativise_setup_xml (called internally by run_cmc)

                       Results-analysis helper (operates on MA results, not
                       the model or the setup -- belongs next to run_ma, not
                       in model/edit/):
                         find_non_zero_mom_arm_muscles (called from
                         analysis.py and summary.py after run_ma, despite
                         sitting near the marker-placement code in the
                         original file)

    simulate/ceinms/   <- utils/ceinms/ (moved as a subpackage, unchanged inside)
    simulate/mrs/      <- mrs/ (moved as a subpackage, same shape as ceinms/ —
                          it already has its own cli.py/config.py/runner.py/io.py,
                          just relocated rather than staying top-level)
    simulate/gapfill.py  <- utils/gapfill.py (marker gap-filling -- runs
                          BEFORE ik needs complete marker data, same
                          input-prep role as exportC3D.py, just simulate's
                          side of it rather than session's)
                       pipeline.py's single-subject run_subject() logic
                       (IK->ID->MA->SO->CEINMS->JRA) was PLANNED to move in
                       here as a plain function `session/` calls for its
                       batch runs, no longer reachable as its own CLI
                       subcommand — instead it (and run_subject_mode() /
                       _run_session_ceinms()) was deleted outright, not
                       migrated. Rebuilding that batch-across-subjects
                       sequencing (now missing entirely) is still open work,
                       whenever `session`/`simulate` grow to cover it.
  session/           NEW — everything `bioscout session` backs
                       <- utils/session.py (258KB), utils/session_form.py,
                          utils/session_layout.py, utils/session_paths.py,
                          utils/exportC3D.py (backs `session export` directly --
                          it exists FOR that verb, more than it's a generic
                          simulate-input converter; imports from `emg/` for
                          channel resolution, which is a normal cross-package
                          dependency, same as session already needing
                          `model` for `session scale`),
                          utils/motion_detect.py (finds a capture's actual
                          movement window -- same domain as
                          movement_detector/'s classification, just a
                          different question; belongs alongside it here,
                          not in plot/ despite the name suggesting a figure),
                          movement_detector/ (backs `session classify`)
  plot/              grows: figures.py moves in (-> plot/catalog.py or
                     similar), collings.py moves in (-> plot/collings.py --
                     it's the literal implementation behind `plot collings`),
                     summary.py moves in (-> plot/summary.py -- pipeline.py's
                     run_summary() falls back to it for the project's
                     results/manuscript summary; genuinely a report/figure
                     builder, unlike its three siblings above)
  lab/               NEW — the `lab` verb's home
                       <- load_tracking/ (backs `lab load-report`, `lab add-subject`,
                          `lab shots` via shot_analysis.py), record/ (video capture,
                          currently GUI-only — folds in since lab = "video and
                          wearable tracking"), utils/subject_profile.py
                          (per-subject video-analysis profiles under
                          ~/.powerlifting_app/subjects -- only load_tracking/
                          and the video-analysis GUI widgets touch this one,
                          unlike subject_registry.py above)
  init/              NEW, small — the `init` verb
                       <- utils/project_config.py
  utils/             becomes the generic, dependency-light helper library --
                     its NATURAL meaning, not a dumping ground and not
                     renamed to `shared/`:
                       <- utils/io.py, utils/helpers.py, utils/shared.py,
                          utils/xml_utils.py, utils/logger.py, utils/stats.py,
                          utils/resource_cleanup.py
                       PLUS two modules that don't exist yet, built
                       incrementally rather than gated on a full audit:
                       start with whatever's simple and obviously shared,
                       migrate bigger modules' duplicated logic in over time
                       as it's found, not all at once:
                         utils/filters.py       generic signal filtering --
                                                 starts with bandpass()/
                                                 lowpass() pulled out of
                                                 emg_normalise.filter_emg()'s
                                                 inline scipy butter+filtfilt
                                                 calls; candidates to migrate
                                                 in later: gapfill.py
                         utils/text_prints.py    console/log formatting
                                                 helpers -- same approach;
                                                 today it's ad hoc print()
                                                 calls scattered per module
  devtools/          NEW, small — the `utils` VERB's own implementation
                     (env/deps/docs/editor-setup). Named `devtools/` rather
                     than `utils/` specifically so it stops colliding with
                     "utils" meaning generic shared code everywhere else in
                     the codebase -- that clash was the actual problem, not
                     which folder holds which five files:
                       <- envcheck.py (from bioscout/ root), dependency_installer.py,
                          md2pdf.py, settings_updater.py, run_check.py
```

## 3. Remaining open items

The `openSim.py` scale/simulate split (the last real open question) is now
resolved -- every one of its ~65 functions is categorised into `model/` or
`simulate/` above, grounded in the `delegates_to=` map plus a grep of every
caller, not guesswork. Two small judgment calls fell out of that pass and
have since been actioned (see section 0):

- ~~**`compare_osim_models`** (in `openSim.py`) has zero callers repo-wide —
  candidate for deletion rather than migration.~~ **Done** — deleted.
- ~~**`export_c3d`** (in `openSim.py`) should probably be renamed on the move
  (e.g. `c3d_to_trc`) since `session/exportC3D.py` is right next door and the
  names are easy to confuse, even though they aren't literal duplicates.~~
  **Done** — renamed to `c3d_to_trc`, its one call site updated.

Everything else previously open is resolved: `utils/file_edit.py` stays in
`utils/`; `record/` folding into `lab/` is confirmed, with
`gui/widgets/recording.py`'s `from record.video import ...` needing to
become a proper `bioscout.lab.record.video` import as part of that move.
Neither of those two moves (or any other file move in section 2) has
happened yet — only the naming/dead-code decision has, ahead of the actual
`openSim.py` split in stage 6.

## 4. Why this can't be a single sed pass

- `utils/analysis.py` (357KB), `utils/session.py` (258KB) and
  `utils/openSim.py` (233KB) are the three biggest files in the repo, imported
  from ~30+ places combined (gui/, pipeline.py, model_edit/, muscle_inspect/,
  tps_personalise/, tests/, and each other).
- The working tree already has substantial uncommitted work-in-progress on
  `implementations-c1` (CHANGELOG.md, cli.py, settings.py, several utils/*.py,
  gui/ files, a deleted model file) unrelated to this restructuring — moving
  files under it risks conflating unrelated diffs and makes any mistake
  harder to isolate.
- There's no test-suite run baked into this plan yet — `bioscout/tests/`
  exists and `bioscout.test()` is the entry point; running it before/after
  each stage is how we catch a broken import before it reaches a real
  analysis run.

## 5. Proposed staged rollout (each stage its own commit, tests run in between)

1. **CLI-only, zero file moves**: add the `simulate` verb group to `cli.py`
   (ik/id/ma/so/cmc/ceinms/jra) wrapping the existing `utils/openSim.py`/
   `ceinms/` functions in place; retire `run`/`project` as top-level (keep
   them as hidden aliases for one release so nothing breaks silently); fold
   `project` into `init`. `model` and `scale` need no CLI change here --
   `model` already exists, `scale` just doesn't move to `simulate`. Lowest
   risk, delivers the UX improvement immediately.
2. **Move `figures.py` and `collings.py` into `plot/`**, update their import
   sites in `cli.py`. Small, self-contained.
3. **Fold `scale` into `model`**: `bioscout scale` -> `bioscout model scale`;
   move `scale_measurements.py`/`model_scaler.py` into `model/scale/`.
4. **Consolidate `model`**: move `model_edit/`, `change_moment_arms/`,
   `muscle_inspect/`, `tps_personalise/` (-> `model/tps/`) under `model/`;
   update `cli.py`'s routing. Rename `model ma` to `model tune-ma`.
   Same stage, same shape: move `mrs/` under `simulate/mrs/` and wire
   `simulate mrs` into the routing -- no `bioscout mrs` alias, drop the old
   top-level shortcut outright.
5. **Extract `emg/`**: move the emg*.py files out of `utils/` into their own
   top-level package; update the ~4 importers (gui/, pipeline.py, session.py,
   analysis.py). Do this before stage 6/7 since both `session/` and
   `simulate/ceinms/` will need to import from it once they move.
6. **Split `openSim.py` and extract `model/`'s and `simulate/`'s shares of
   it**: mechanical now that the split is fully mapped out (section 2) --
   `model/opensim_base.py`, `model/edit/`'s additions, `model/muscle_optimize.py`
   and `model/scale/`'s additions go with stage 3/4's `model/` work;
   everything else (the pipeline-stage functions, the input-prep cluster,
   `find_non_zero_mom_arm_muscles`) plus `ceinms/`, `mrs/`, `gapfill.py`
   becomes `simulate/`. (`compare_osim_models`/`export_c3d` -- already
   dropped/renamed, see section 0; nothing left to decide there.) ~27+
   import sites combined across both halves — an actual find/replace pass
   plus a full `bioscout.test()` run, not by hand.
7. **Extract `session/`**: move `session.py` + friends + `exportC3D.py` +
   `motion_detect.py`; same treatment.
8. **Extract `core/`**: move `analysis.py` into the existing `core/`, along
   with `subject_registry.py` and `jcf_contributions.py`.
9. **Move `summary.py` into `plot/`**, alongside `figures.py`/`collings.py`
   from stage 2 -- small, can ride along with that stage instead of getting
   its own if it's easier.
10. **Extract `lab/`**: move `load_tracking/`, `record/`,
    `subject_profile.py` in together; fix `gui/widgets/recording.py`'s
    import.
11. **Rename the `utils` verb's backend to `devtools/`**, and start
    `utils/filters.py` with the `bandpass()`/`lowpass()` primitives pulled
    out of `emg_normalise.filter_emg()`, plus `utils/text_prints.py` --
    small and simple to start, migrate bigger modules' logic in over time
    as it's found.
12. **`init/`**: lowest urgency, smallest blast radius — last.

I'd suggest starting at stage 1 (the part you actually asked for — nicer
`bioscout -h`) and treating 2 onward as separate, reviewable pieces of work
rather than one big-bang move.
