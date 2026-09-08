# bioscout CLI + package restructure — plan

Goal: the package tree under `bioscout/` should mirror the verb tree of
`bioscout -h`, so "where does the `session` code live?" always has the same
answer: `bioscout/session/`. Today it doesn't — `session.py` (258KB) lives in
`bioscout/utils/`, `openSim.py` (233KB) and `ceinms/` live in `bioscout/utils/`,
and the `model` verb's actions are spread across four unrelated top-level
folders (`model/`, `model_edit/`, `change_moment_arms/`, `muscle_inspect/`).

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
                            complete marker data -- tentative placement, see
                            open questions
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
                     code. Open sub-question: emg_filter.py's actual filter
                     function might still be generic enough to also live in
                     `utils/filters.py` (see below) with emg/ calling it --
                     needs a closer read to split "generic filter" from
                     "EMG-specific use of a filter."
  model/             the WHOLE `model` verb, un-nested and top-level (not
                     under `simulate` -- see CLI tree above):
                       <- model/ (already: check, geometry, verify)
                          model_edit/ (-> model/edit/, backs `model edit`)
                          change_moment_arms/ (-> model/moment_arms/, backs `model tune-ma`)
                          muscle_inspect/ (-> model/inspect/, backs `model validate`)
                          tps_personalise/ (-> model/tps/, backs `model tps`)
                          utils/model_report.py (-> model/report.py -- this is
                          NOT one of figures.py's dispatch targets like I'd
                          guessed earlier; it's the direct implementation
                          behind `model compare`, model_edit/ops/inspect.py
                          literally says `delegates_to=
                          "bioscout.utils.model_report.compare_models"`)
                          utils/scale_measurements.py, utils/model_scaler.py
                          (-> model/scale/ -- these back `scale`, which now
                          lives under `model` too, see CLI tree)
  simulate/          NEW — everything under the `simulate` verb
                     (ik/id/ma/so/cmc/ceinms/jra/mrs/gapfill). Named to match
                     the verb exactly, now that `model` (and `scale`) are out
                     of it: what's left really is just "run a simulation on
                     an existing model," so `simulate/` needs no broader
                     umbrella name like `msk/` any more.
                       <- utils/openSim.py (233KB) -- MINUS whatever inside it
                          is actually the ScaleTool wrapper (that part goes to
                          `model/scale/` instead, see open questions -- this
                          233KB file almost certainly needs an internal split,
                          not a clean single-destination move)
    simulate/ceinms/   <- utils/ceinms/ (moved as a subpackage, unchanged inside)
    simulate/mrs/      <- mrs/ (moved as a subpackage, same shape as ceinms/ —
                          it already has its own cli.py/config.py/runner.py/io.py,
                          just relocated rather than staying top-level)
    simulate/gapfill.py  <- utils/gapfill.py (marker gap-filling -- runs
                          BEFORE ik needs complete marker data, same
                          input-prep role as exportC3D.py, just simulate's
                          side of it rather than session's)
                       pipeline.py's single-subject run_subject() logic
                       (IK->ID->MA->SO->CEINMS->JRA) moves in here too, as a
                       plain function `session/` calls for its batch runs —
                       it stops being reachable as its own CLI subcommand.
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
                                                 start with the simple stuff;
                                                 candidates to migrate in
                                                 later: emg_filter.py,
                                                 gapfill.py, openSim.py
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

## 3. Open questions I couldn't resolve by reading code alone

- **`utils/openSim.py`'s internal scale/simulate split** — the real
  complexity the `model`/`simulate` split adds: this 233KB file is the
  OpenSim API wrapper for everything (scale, ik, id, ma, so, jra all
  together, near as I can tell without reading the whole thing), so moving
  it needs an actual read to find the ScaleTool-wrapping code and split it
  out to `model/scale/`, leaving the rest for `simulate/`. Not a clean
  single-destination move like most of this plan.
  `utils/file_edit.py` — resolved, stays in `utils/`, per your call.
  `record/` folding into `lab/` — confirmed; the one concrete fix needed is
  `gui/widgets/recording.py`'s `from record.video import ...`, which needs
  to become `from bioscout.lab.record.video import ...` (or whatever the
  final import style is -- worth checking why it's a bare `record.video`
  import today rather than `bioscout.record.video`, in case that's an
  existing quirk rather than something this move should copy forward).

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
6. **Split `openSim.py` and extract `simulate/`**: this is the stage that
   changed shape the most -- read `openSim.py` closely enough to separate
   its ScaleTool-wrapping code (-> `model/scale/`, joining stage 3's files)
   from everything else (-> `simulate/`, with `ceinms/`, `gapfill.py`
   alongside it). ~27+ import sites combined — an actual find/replace pass
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
