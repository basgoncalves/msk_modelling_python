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
              mrs           muscle redundancy solver -- now `openSim mrs`.
                            No `bioscout mrs` alias kept; the old top-level
                            shortcut is just gone once this ships.
              model         check, edit, compare and validate .osim models
                              check          can every model still find its bone meshes?
                              edit           scale, set mass, change forces, moment arms, markers
                              compare        dimensions and segment masses across models
                              tune-ma        adjust a muscle's moment arm, interactively
                                             (renamed from `ma` -- collided with
                                             `openSim ma`, the muscle-analysis stage)
                              validate       moment arms, fibre lengths, strength vs literature
                              joint-centres  (jc)
                              tps            build an MRI-personalised model (interactive)
  session   create, export, classify, scale or reset a session; batches
            openSim's steps across subjects/iterations and makes it easy to
            compare between iterations                  [absorbs old `run`/`run --batch`]
  plot      figures from the results on disk (incl. the project figure
            catalogue, moved in from `bioscout/figures.py`, and the Collings
            muscle-ranking figure, moved in from `utils/collings.py`)
  utils     environment, dependencies, docs, editor setup
  lab       EXPERIMENTAL (3.0): video and wearable tracking
```

Dropped as top-level verbs: `run`, `scale` (folded into `openSim`), `project`
(folded into `init`), `model` and `tps` (nested under `openSim`, since both
operate on .osim models — `tps` moves a level deeper still, under `model`,
since what it produces IS a model), `mrs` (nested under `openSim`, no
compat alias).

There's no `openSim run` subcommand and no top-level "run the whole
single-subject pipeline" command — `session` calls the individual `openSim`
steps in sequence itself when it batches across subjects/iterations, rather
than that sequencing being its own user-facing verb.

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
                          keeps using it via an import, same as gui/ does today)
  tests/             unchanged
  gui/               unchanged (the `gui` verb)
  emg/               NEW, top-level, NOT its own CLI verb -- a domain package
                     that `session/` (export, channel mapping) and
                     `opensim/ceinms/` (excitation QC) both import from, the
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
                          change_moment_arms/ (-> opensim/model/moment_arms/, backs `model tune-ma`)
                          muscle_inspect/ (-> opensim/model/inspect/, backs `model validate`)
      opensim/model/tps/  RENAMED from tps_personalise/ (backs `openSim model tps`)
  session/           NEW — everything `bioscout session` backs
                       <- utils/session.py (258KB), utils/session_form.py,
                          utils/session_layout.py, utils/session_paths.py,
                          utils/exportC3D.py (backs `session export` directly --
                          it exists FOR that verb, more than it's a generic
                          openSim-input converter; imports from `emg/` for
                          channel resolution, which is a normal cross-package
                          dependency, same as session already needing opensim/
                          for `session scale`),
                          movement_detector/ (backs `session classify`)
  plot/              grows: figures.py moves in (-> plot/catalog.py or
                     similar), collings.py moves in (-> plot/collings.py --
                     it's the literal implementation behind `plot collings`)
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
                       PLUS two modules that don't exist yet and would need
                       writing, not just moving:
                         utils/filters.py       generic signal filtering
                                                 (consolidated out of whatever
                                                 is duplicated today across
                                                 emg_filter.py, gapfill.py,
                                                 openSim.py, etc. — needs an
                                                 actual duplication audit first)
                         utils/text_prints.py    console/log formatting
                                                 helpers (today ad hoc print()
                                                 calls scattered per module)
  devtools/          NEW, small — the `utils` VERB's own implementation
                     (env/deps/docs/editor-setup). Named `devtools/` rather
                     than `utils/` specifically so it stops colliding with
                     "utils" meaning generic shared code everywhere else in
                     the codebase -- that clash was the actual problem, not
                     which folder holds which five files:
                       <- envcheck.py (from bioscout/ root), dependency_installer.py,
                          md2pdf.py, settings_updater.py, run_check.py
                     (Naming bikeshed: `devtools/`, `toolkit/`, `env/` all
                     work equally well here -- pick whichever reads best.)
```

## 3. Open questions I couldn't resolve by reading code alone

- **`utils/model_report.py`**, **`utils/summary.py`**,
  **`utils/jcf_contributions.py`**, **`utils/motion_detect.py`** — the
  remaining figure/report builders `figures.py` dispatches to (collings.py
  is now resolved, above). Likely `plot/` too, same reasoning; need a closer
  read of each before deciding.
- **`utils/file_edit.py`**, **`utils/gapfill.py`** — still unresolved.
  `gapfill.py` (marker gap-filling) reads like `session/`-or-`opensim/`
  input-prep, similar to exportC3D.py; `file_edit.py` is more generic and
  might belong in `utils/` instead. Needs a closer read.
- **`record/`** folding into `lab/` needs confirming the GUI's recording
  widget import path gets updated too (`gui/widgets/recording.py`).
- **`emg_filter.py`'s split** — see the `emg/` entry above: is there a
  generic filter function inside it worth pulling out to `utils/filters.py`,
  with `emg/` becoming a thin EMG-specific caller of it? Needs a look at
  what the function actually does, not just its name.
- **`utils/filters.py` and `utils/text_prints.py` are new modules, not
  moves.** Worth an actual audit of what's duplicated (signal filtering
  shows up in `emg_filter.py`, `gapfill.py`, possibly `openSim.py`; print/log
  formatting is ad hoc per-file today) before deciding what goes in vs. gets
  left alone — scope this as its own small stage, not folded into the bigger
  `utils/` extraction.
- **`devtools/` naming** — flagged above; any name that isn't `utils` works,
  just need to pick one.

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
2. **Move `figures.py` and `collings.py` into `plot/`**, update their import
   sites in `cli.py`. Small, self-contained.
3. **Nest `model` (and `tps`) under `openSim`**: move `model/`, `model_edit/`,
   `change_moment_arms/`, `muscle_inspect/` under a new `model/` sub-package,
   and `tps_personalise/` under `model/tps/`; update `cli.py`'s routing so
   `openSim model ...` and `openSim model tps` resolve there. Rename `model
   ma` to `model tune-ma` as part of this stage.
   Same stage, same shape: move `mrs/` under `opensim/mrs/` and wire
   `openSim mrs` into the routing -- no `bioscout mrs` alias, drop the old
   top-level shortcut outright.
4. **Extract `emg/`**: move the emg*.py files out of `utils/` into their own
   top-level package; update the ~4 importers (gui/, pipeline.py, session.py,
   analysis.py). Do this before stage 5/6 since both `session/` and
   `opensim/ceinms/` will need to import from it once they move.
5. **Extract `opensim/` for real**: move `openSim.py`, `ceinms/`,
   `scale_measurements.py`, `model_scaler.py` (and the `model/` sub-package
   from stage 3) out of `utils/` into `bioscout/opensim/`; this is the big
   one (~27 import sites) — do it with an actual find/replace pass plus a
   full `bioscout.test()` run, not by hand.
6. **Extract `session/`**: move `session.py` + friends + `exportC3D.py`;
   same treatment.
7. **Extract `core/`**: move `analysis.py` into the existing `core/`, along
   with `subject_registry.py`.
8. **Extract `lab/`**: move `load_tracking/`, `record/`,
   `subject_profile.py` in together.
9. **Rename the `utils` verb's backend to `devtools/`** and write
   `utils/filters.py`/`utils/text_prints.py` as their own reviewable change
   (audit for real duplication first, see open questions) — this one is
   partly new code, not a pure move, so it gets its own stage rather than
   riding along with anything else.
10. **`init/`**: lowest urgency, smallest blast radius — last.

I'd suggest starting at stage 1 (the part you actually asked for — nicer
`bioscout -h`) and treating 2 onward as separate, reviewable pieces of work
rather than one big-bang move.
