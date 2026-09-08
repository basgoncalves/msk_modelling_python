# bioscout CLI + package restructure — plan

Goal: the package tree under `bioscout/` should mirror the verb tree of
`bioscout -h`, so "where does the `session` code live?" always has the same
answer: `bioscout/session/`. Today it doesn't — `session.py` (258KB) lives in
`bioscout/utils/`, `openSim.py` (233KB) and `ceinms/` live in `bioscout/utils/`,
and the `model`/`tps` verbs are four unrelated top-level folders even though
all of them are fundamentally OpenSim-model concerns.

## 1. Target CLI tree

```
bioscout -h
  gui       launch the GUI (also the default with no verb)
  init      create a project: folders, models, templates and project-level
            config (project.yaml)                       [merges old init + project]
  openSim   OpenSim/CEINMS tools, usable standalone from the terminal:
              scale         scale a model by answering questions (interactive)
              ik            inverse kinematics
              id            inverse dynamics
              ma            muscle analysis
              so            static optimisation
              cmc           (if/when supported)
              ceinms        calibrate / execute CEINMS
              jra           joint reaction analysis
              mrs           muscle redundancy solver (was its own top-level
                            verb; now `openSim mrs`, a hidden `bioscout mrs`
                            alias kept for one release)
              model         check, edit, compare and validate .osim models
                              check          can every model still find its bone meshes?
                              edit           scale, set mass, change forces, moment arms, markers
                              compare        dimensions and segment masses across models
                              ma             adjust a muscle's moment arm, interactively
                              validate       moment arms, fibre lengths, strength vs literature
                              joint-centres  (jc)
                              tps            build an MRI-personalised model (interactive)
  session   create, export, classify, scale or reset a session; batches
            openSim's steps across subjects/iterations and makes it easy to
            compare between iterations                  [absorbs old `run`/`run --batch`]
  plot      figures from the results on disk (incl. the project figure
            catalogue, moved in from `bioscout/figures.py`)
  utils     environment, dependencies, docs, editor setup
  lab       EXPERIMENTAL (3.0): video and wearable tracking
```

Dropped as top-level verbs: `run`, `scale` (folded into `openSim`), `project`
(folded into `init`), `model` and `tps` (nested under `openSim`, since both
operate on .osim models — `tps` moves a level deeper still, under `model`,
since what it produces IS a model).

Changed from the last draft: no `openSim run` subcommand. There's no
top-level "run the whole single-subject pipeline" command anymore —
`session` calls the individual `openSim` steps in sequence itself when it
batches across subjects/iterations, rather than that sequencing being its
own user-facing verb.

**Naming collision to flag, not silently resolve:** `openSim ma` (muscle
analysis, a pipeline stage) and `openSim model ma` (adjust one muscle's
moment arm interactively) are two different actions that happen to share
the short name `ma`, one level apart. Not a technical conflict — argparse
handles it fine, they're different subparsers — but worth a second look
before committing to it, since it reads as confusing on paper.

## 2. Target package tree

```
bioscout/
  __init__.py, __main__.py, cli.py, envcheck.py
  config/            unchanged — GUI's config_manager.py + default_config.yaml
  core/              Project/Subject/Trial + the analysis engine
                       <- utils/analysis.py (357KB), core/analysis_runner.py,
                          core/project_analysis.py (already here)
  tests/             unchanged
  gui/               unchanged (the `gui` verb)
  opensim/           NEW — everything under `openSim` (scale/ik/id/ma/so/ceinms/jra)
                       <- utils/openSim.py (233KB), utils/scale_measurements.py,
                          utils/model_scaler.py
    opensim/ceinms/    <- utils/ceinms/ (moved as a subpackage, unchanged inside)
    opensim/mrs/       <- mrs/ (moved as a subpackage, same shape as ceinms/ —
                          it already has its own cli.py/config.py/runner.py/io.py,
                          just relocated rather than staying top-level)
                       pipeline.py's single-subject run_subject() logic
                       (IK->ID->MA->SO->CEINMS->JRA) moves in here too, as a
                       plain function `session/` calls for its batch runs —
                       it stops being reachable as its own CLI subcommand.
    opensim/model/     the WHOLE `openSim model` verb
                       <- model/ (already: check, geometry, verify)
                          model_edit/ (-> opensim/model/edit/, backs `model edit`)
                          change_moment_arms/ (-> opensim/model/moment_arms/, backs `model ma`)
                          muscle_inspect/ (-> opensim/model/inspect/, backs `model validate`)
      opensim/model/tps/  RENAMED from tps_personalise/ (backs `openSim model tps`)
  session/           NEW — everything `bioscout session` backs
                       <- utils/session.py (258KB), utils/session_form.py,
                          utils/session_layout.py, utils/session_paths.py,
                          movement_detector/ (backs `session classify`)
  plot/              grows: figures.py moves in (-> plot/catalog.py or similar)
  lab/               NEW — the `lab` verb's home
                       <- load_tracking/ (backs `lab load-report`, `lab add-subject`,
                          `lab shots` via shot_analysis.py), record/ (video capture,
                          currently GUI-only — folds in since lab = "video and
                          wearable tracking")
  init/              NEW, small — the `init` verb
                       <- utils/project_config.py
  shared/            NEW — generic, dependency-light helpers used across every
                     package (not tied to any one CLI verb):
                       <- utils/io.py, utils/helpers.py, utils/shared.py,
                          utils/xml_utils.py, utils/logger.py, utils/stats.py,
                          utils/resource_cleanup.py
                       PLUS two modules that don't exist yet and would need
                       writing, not just moving:
                         shared/filters.py      generic signal filtering
                                                 (consolidated out of whatever
                                                 is duplicated today across
                                                 emg_filter.py, gapfill.py,
                                                 openSim.py, etc. — needs an
                                                 actual duplication audit first)
                         shared/text_prints.py   console/log formatting
                                                 helpers (today ad hoc print()
                                                 calls scattered per module)
  utils/             SHRINKS to ONLY the `utils` verb's own implementation —
                     no longer a dumping ground:
                       <- envcheck.py (from bioscout/ root), dependency_installer.py,
                          md2pdf.py, settings_updater.py, run_check.py
```

## 3. Open questions I couldn't resolve by reading code alone

- **The `ma` name collision** noted above — worth deciding on a
  disambiguating name for one of the two before this ships (e.g. `openSim
  model tune-ma` or similar) rather than shipping it as-is.
- **EMG files** (`utils/emg.py`, `emg_analysis.py`, `emg_channels.py`,
  `emg_filter.py`, `emg_normalise.py`) — used by both the OpenSim pipeline
  (JRA needs EMG-driven CEINMS) and session export. Proposal: `opensim/emg/`,
  since CEINMS is the main consumer, but session/export.py would import from
  there.
- **`utils/collings.py`**, **`utils/model_report.py`**, **`utils/summary.py`**,
  **`utils/jcf_contributions.py`**, **`utils/motion_detect.py`** — figure/report
  builders that `figures.py` dispatches to. Likely `plot/` or stay put and get
  imported from there; need a closer read before deciding.
- **`utils/subject_registry.py`**, **`subject_profile.py`** — subject-level
  metadata, used by `core` (Subject class) AND `session`. Probably `core/`.
- **`utils/exportC3D.py`**, **`file_edit.py`**, **`gapfill.py`** — export
  step used by `session export`; likely move to `session/`.
- **`record/`** folding into `lab/` needs confirming the GUI's recording
  widget import path gets updated too (`gui/widgets/recording.py`).
- **Keeping a top-level `bioscout mrs` alias.** `mrs` currently bypasses the
  main verb tree entirely (`route()` special-cases `argv[:1] == ["mrs"]`,
  same trick as `plot jcf`). Moving its package under `opensim/` doesn't
  force the CLI surface to change too — but for the same reason `model`/`tps`
  move in both package AND command tree, `mrs` probably should too
  (`bioscout openSim mrs ...`), with the old `bioscout mrs ...` kept as a
  hidden alias for one release rather than dropped outright.
- **`shared/filters.py` and `shared/text_prints.py` are new modules, not
  moves.** Worth an actual audit of what's duplicated (signal filtering
  shows up in `emg_filter.py`, `gapfill.py`, possibly `openSim.py`; print/log
  formatting is ad hoc per-file today) before deciding what goes in vs. gets
  left alone — scope this as its own small stage, not folded into the bigger
  `shared/` extraction.

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

1. **CLI-only, zero file moves**: add the `openSim` verb group to `cli.py`
   (scale/ik/id/ma/so/ceinms/jra) wrapping the existing `utils/openSim.py`/
   `ceinms/` functions in place; retire `run`/`scale`/`project` as top-level
   (keep them as hidden aliases for one release so nothing breaks silently);
   fold `project` into `init`. Lowest risk, delivers the UX improvement
   immediately.
2. **Move `figures.py` into `plot/`**, update its two import sites in `cli.py`.
   Small, self-contained.
3. **Nest `model` (and `tps`) under `openSim`**: move `model/`, `model_edit/`,
   `change_moment_arms/`, `muscle_inspect/` under a new `model/` sub-package,
   and `tps_personalise/` under `model/tps/`; update `cli.py`'s routing so
   `openSim model ...` and `openSim model tps` resolve there. Resolve the
   `ma` naming collision as part of this stage.
   Same stage, same shape: move `mrs/` under `opensim/mrs/` and wire
   `openSim mrs` into the routing (keep `bioscout mrs` as a hidden alias).
4. **Extract `opensim/` for real**: move `openSim.py`, `ceinms/`,
   `scale_measurements.py`, `model_scaler.py` (and the `model/` sub-package
   from stage 3) out of `utils/` into `bioscout/opensim/`; this is the big
   one (~27 import sites) — do it with an actual find/replace pass plus a
   full `bioscout.test()` run, not by hand.
5. **Extract `session/`**: move `session.py` + friends; same treatment.
6. **Extract `core/`**: move `analysis.py` into the existing `core/`.
7. **Extract `shared/`**: audit for real duplication first (see open
   questions), then move the true cross-cutting helpers out of `utils/` and
   write `filters.py`/`text_prints.py` as their own reviewable change —
   this one is partly new code, not a pure move, so it gets its own stage
   rather than riding along with anything else.
8. **`lab/` and `init/`**: lowest urgency, smallest blast radius — last.

I'd suggest starting at stage 1 (the part you actually asked for — nicer
`bioscout -h`) and treating 2 onward as separate, reviewable pieces of work
rather than one big-bang move.
