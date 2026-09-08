# bioscout CLI + package restructure — plan

Goal: the package tree under `bioscout/` should mirror the verb tree of
`bioscout -h`, so "where does the `session` code live?" always has the same
answer: `bioscout/session/`. Today it doesn't — `session.py` (258KB) lives in
`bioscout/utils/`, `openSim.py` (233KB) and `ceinms/` live in `bioscout/utils/`,
and the `model` verb's four actions are spread across four unrelated
top-level folders.

## 1. Target CLI tree

```
bioscout -h
  gui       launch the GUI (also the default with no verb)
  init      create a project: folders, models, templates and project-level
            config (project.yaml)                       [merges old init + project]
  openSim   OpenSim/CEINMS tools, usable standalone from the terminal:
              scale       scale a model by answering questions (interactive)
              ik          inverse kinematics
              id          inverse dynamics
              ma          muscle analysis
              so          static optimisation
              cmc         (if/when supported)
              ceinms      calibrate / execute CEINMS
              jra         joint reaction analysis
              run         the full single-subject pipeline (old `run` verb:
                           export -> scale -> IK -> ID -> MA -> SO -> CEINMS -> JRA)
  session   create, export, classify, scale or reset a session; batches
            `openSim run` across subjects/iterations and makes it easy to
            compare between iterations                  [absorbs old `run --batch`]
  model     check, edit, compare and validate .osim models
  tps       build an MRI-personalised model (interactive)
  plot      figures from the results on disk (incl. the project figure
            catalogue, moved in from `bioscout/figures.py`)
  utils     environment, dependencies, docs, editor setup
  lab       EXPERIMENTAL (3.0): video and wearable tracking
  mrs       (unchanged — already its own verb + package)
```

Dropped as top-level verbs: `run`, `scale`, `project` (folded into `init`,
whose description already grows to mention project.yaml).

## 2. Target package tree

```
bioscout/
  __init__.py, __main__.py, cli.py, pipeline.py*, envcheck.py
  config/            unchanged — GUI's config_manager.py + default_config.yaml
  core/              Project/Subject/Trial + the analysis engine
                       <- utils/analysis.py (357KB), core/analysis_runner.py,
                          core/project_analysis.py (already here)
  tests/             unchanged
  gui/               unchanged (the `gui` verb)
  opensim/           NEW — everything `bioscout openSim` backs
                       <- utils/openSim.py (233KB), utils/ceinms/ (whole dir),
                          utils/scale_measurements.py, utils/model_scaler.py,
                          pipeline.py's single-subject run_subject() logic
  session/           NEW — everything `bioscout session` backs
                       <- utils/session.py (258KB), utils/session_form.py,
                          utils/session_layout.py, utils/session_paths.py,
                          movement_detector/ (backs `session classify`)
  model/             grows to be the WHOLE `model` verb, not just check/verify
                       <- model/ (already: check, geometry, verify)
                          model_edit/ (-> model/edit/, backs `model edit`)
                          change_moment_arms/ (-> model/moment_arms/, backs `model ma`)
                          muscle_inspect/ (-> model/inspect/, backs `model validate`)
  tps/               RENAMED from tps_personalise/ (backs `tps`)
  plot/              grows: figures.py moves in (-> plot/catalog.py or similar)
  lab/               NEW — the `lab` verb's home
                       <- load_tracking/ (backs `lab load-report`, `lab add-subject`,
                          `lab shots` via shot_analysis.py), record/ (video capture,
                          currently GUI-only — folds in since lab = "video and
                          wearable tracking")
  init/              NEW, small — the `init` verb
                       <- utils/project_config.py
  utils/             SLIMS DOWN to true cross-cutting helpers + the `utils`
                     verb's own implementation:
                       io.py, helpers.py, shared.py, xml_utils.py, logger.py,
                       stats.py, resource_cleanup.py, dependency_installer.py,
                       md2pdf.py, settings_updater.py, run_check.py
  mrs/               unchanged
```

`*` `pipeline.py` at the root today does project-level orchestration
(`run_project`, reading settings.py flags). Its single-subject step
(`run_subject`, the old IK->ID->MA->SO->CEINMS->JRA sequence) is the same
thing `openSim run` needs, so that part moves into `opensim/pipeline.py`;
`run_project` itself becomes `session`'s batch driver and can move into
`session/pipeline.py`, calling into `opensim`.

## 3. Open questions I couldn't resolve by reading code alone

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
- Should `tps_personalise` really rename to `tps/`, given `tps_personalise`
  is also a public name referenced in its own README and possibly external
  docs/scripts?

## 4. Why this can't be a single sed pass

- `utils/analysis.py` (357KB), `utils/session.py` (258KB) and
  `utils/openSim.py` (233KB) are the three biggest files in the repo, imported
  from ~30+ places combined (gui/, pipeline.py, model_edit/, muscle_inspect/,
  tps_personalise/, tests/, and each other).
- The working tree already has substantial uncommitted work-in-progress on
  `implementations-c1` (CHANGELOG.md, cli.py, settings.py, several utils/*.py,
  a deleted model file) unrelated to this restructuring — moving files under
  it risks conflating unrelated diffs and makes any mistake harder to isolate.
- There's no test-suite run baked into this plan yet — `bioscout/tests/`
  exists and `bioscout.test()` is the entry point; running it before/after
  each stage is how we catch a broken import before it reaches a real
  analysis run.

## 5. Proposed staged rollout (each stage its own commit, tests run in between)

1. **CLI-only, zero file moves**: add the `openSim` verb group to `cli.py`
   wrapping the existing `utils/openSim.py`/`ceinms/` functions in place;
   retire `run`/`scale`/`project` as top-level (keep them as hidden aliases
   for one release so nothing breaks silently); fold `project` into `init`.
   Lowest risk, delivers the UX improvement immediately.
2. **Move `figures.py` into `plot/`**, update its two import sites in `cli.py`.
   Small, self-contained.
3. **Consolidate the `model` verb**: move `model_edit/`, `change_moment_arms/`,
   `muscle_inspect/` under `model/`, update their ~handful of cross-imports
   and `cli.py`'s four `_direct()`/routing entries.
4. **Extract `opensim/`**: move `openSim.py`, `ceinms/`, `scale_measurements.py`,
   `model_scaler.py` out of `utils/`; this is the big one (~27 import sites) —
   do it with an actual find/replace pass plus a full `bioscout.test()` run,
   not by hand.
5. **Extract `session/`**: move `session.py` + friends; same treatment.
6. **Extract `core/`**: move `analysis.py` into the existing `core/`.
7. **`lab/` and `init/`**: lowest urgency, smallest blast radius — last.

I'd suggest starting at stage 1 (the part you actually asked for — nicer
`bioscout -h`) and treating 2 onward as separate, reviewable pieces of work
rather than one big-bang move.
