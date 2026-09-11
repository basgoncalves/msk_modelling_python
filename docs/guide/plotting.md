# Plotting — `bioscout.plot`

Merged 2026-09-08 from `PLOTTING.md` (part 1, the comparison-figure
builder) and `figures.md` (part 2, the figure catalogue).

## Part 1 — the comparison figure

One comparison figure, driven by one table, configured at run time.

```python
import bioscout as bs

(bs.plot("results/master_results.csv")
   .where(Variable="muscle_work_total", Algo="SO")
   .compare("Condition", order=["pre-fatigue", "post-fatigue"])
   .facet("Task", icons=TASK_ICONS)
   .group(bs.plot.MUSCLE_GROUPS)
   .top(8)
   .title("total muscle work ranks")
   .save("results/group/work_ranks.png"))
```

## Why it exists

The ranked muscle-work figure had been written three times, in three projects,
each time from scratch:

| project | columns | rows |
|---|---|---|
| Powerlifting `results.py:fig_muscle_work_ranks` | generic models | algorithm |
| FAIS `figure_muscle_work.py` | task | pre-/post-fatigue |
| FAIS `results.py:fig_work_rank` | pre-/post-fatigue | task |

The drawing was never the difficult part — the three versions differ only in
**what the columns are**. So the columns and rows became arguments. Swap
`.compare("Condition")` for `.compare("Algo")` and the same table answers "does
static optimisation reorder the leg" instead of "does fatigue".

## The three layers

```
bioscout.plot.work      .sto files  ->  work in joules      work_table()
bioscout.plot.tidy      numbers     ->  one long table      read(), from_mapping()
bioscout.plot.compare   table       ->  a figure            Compare
```

The **middle layer is the contract**. A bioscout session goes through all
three. A project whose numbers came from somewhere else builds the table itself
and uses only the last one. Nothing in the drawing code knows what a session
is, and nothing knows what fatigue is.

### The table

One row per number. `Value` holds it; every other column is a key that
describes it:

```
Subject Session Iteration Trial Task Condition Fatigue Side Algo Model
Variable Channel Metric  Value
```

None of the keys are required and none are special-cased — you name the column
to compare across and the column to facet by, and any column present can play
either role. `Variable`/`Metric` is the convention for *which quantity is this*
(`muscle_work_total` / `work_J`), so one table can hold every figure's inputs.
FAIS's `results/master_results.csv` and Powerlifting's `master_discrete.csv`
are already exactly this shape and drop straight in.

Add an `x` column (`Percent`, `Time`) and each row becomes a sample of a curve
instead of a summary number — the same selection then feeds `.curves()`.

## Reading a rank figure

Bar colour is the item's rank in the **first** compared column, carried into
every column to its right. The left panel is therefore always a clean
dark-to-pale ramp *by construction*, so any colour disorder further right **is**
a re-ranking — no tracing of lines needed.

- `style="delta"` (default) — ▲/▼ after the label, places gained/lost
- `style="connector"` — the Collings et al. (2025) arrows
- `style="both"`

Normalisation is the other decision worth making on purpose:

- `normalise="reference"` (default) — every panel in a row is scaled to the
  **first column's** leader. A panel that shrank did less work, and a bar may
  legitimately pass 100 %.
- `normalise="panel"` — each panel scaled to its own leader. A pure ranking
  with the magnitudes thrown away. Sometimes what you want; never what you want
  by accident.

## Settings live in bioscout, not in your project

There is no figure config file to copy into a project. The defaults are in
`bioscout/plot/config.py`, and a script or notebook overrides what it cares
about:

```python
bs.plot.configure(dpi=300, top=10, cmap="viridis")     # for this process

with bs.plot.using(dpi=600, save_pdf=True):            # for one export
    fig.save("results/figure_3.png")

.set(panel_w_in=4.2, fs_label=11)                      # for one figure
```

Precedence: defaults → `configure()` → per-call keywords. An unknown setting
name raises; a silently ignored `dpi=600` is a figure that went to a journal at
200 dpi.

## Muscle work

```python
rows = bs.plot.work_table([
    {"Task": "run", "Condition": "pre", "Trial": "RunL1",
     "force":  ".../static_optimisation/SO_StaticOptimization_force.sto",
     "length": ".../muscle_analysis/_MuscleAnalysis_Length.sto"},
    ...
], phase="total")
```

`W = ∫ F·v dt`, with `v` the negated derivative of muscle–tendon length. That
length comes from the kinematics alone, so it is identical for every algorithm
run on the same trial — the algorithms differ only in the force, which is
exactly the comparison worth making.

Four phases, and the phase goes into the table (`Variable =
"muscle_work_<phase>"`) rather than being left to memory, because they rank
muscles differently:

| phase | integral | |
|---|---|---|
| `total` | `∫\|F·v\| dt` | concentric + eccentric — the default |
| `concentric` | `∫ F·v dt`, `v > 0` | |
| `eccentric` | `∫ F\|v\| dt`, `v < 0` | |
| `net` | `∫ F·v dt` | signed; the other three are its parts |

For a bioscout session, `session_records()` walks the trials and
`trial_inputs()` finds the two .sto files; a project supplies a
`label=lambda trial: {...}` callable to say which task and condition a trial
name means. That callable is the only project-specific thing in the path, and
it stays in the project.

Everything here reads .sto as plain text — no OpenSim, no scipy — so it runs on
a bare checkout and in CI.

## Relationship to the other figure code

- `bioscout.plot.collings` keeps the **fixed published layout**
  (`rank_shift_figure`, and the `--collings` CLI). Use it when you want that
  exact figure.
- `bioscout.plot` is the **configurable grid** version: any two columns, any
  facet, either normalisation, bars or curves.
- `bioscout.plot.figures` is the **catalogue/menu** of named project figures. A
  `bioscout.plot` figure can be registered there like any other.

## Tests

`bioscout/tests/test_plot.py` — 21 tests, numpy + pandas + matplotlib only.
The work integral is pinned against cases with exact answers (constant force at
constant velocity; a shorten-then-lengthen cycle where net work is zero and
total work is not), because ranking on the wrong one of those is the easiest
mistake this module can make.


---

## Part 2 — `bioscout.plot.figures`, the catalogue

62 figures from the powerlifting scripts and from bioscout itself, registered in
one place with the inputs each one needs. **Nothing is re-implemented** — the
module finds the existing builder, asks for its inputs and calls it, so the
figures stay identical to what `results.py` / `manuscript.py` produce today.

## Run it standalone

```bash
python -m bioscout.plot.figures                 # menu: pick numbers, keys or a group
python -m bioscout.plot.figures --list          # just print the catalogue
python -m bioscout.plot.figures p04 p07jcf      # run these two, prompt for inputs
python -m bioscout.plot.figures master          # run a whole group
python -m bioscout.plot.figures p04 --session Athlete_01_S1 --subject Athlete_01
python -m bioscout.plot.figures --project C:/Users/Basilio/ucloud/Powerlifiting p01
```

At the menu you can type: `3`, `p04`, `master`, `all`, or any mix separated by
spaces. Every input a figure needs is then prompted with a default in brackets —
press Enter to take it. Trials and trial types are offered as a numbered list
built from the session on disk.

## Use it inside bioscout / a notebook

```python
from bioscout.plot import figures

figures.list_figures()                     # or figures.catalog("master")
figures.run("p04")                         # prompts for the trial
figures.run("p04", trial="Squat_BW_01")    # nothing to prompt for
figures.run_many(["p01", "p05", "s_jcf_angle"])
figures.menu()                             # the interactive picker

ctx = figures.session_ctx()                # sess / S / L / trials / tasks
figures.master()                           # the master_*.csv dataframes
```

Rule: **anything you pass is used, anything you omit is asked for.** The same
registry therefore works scripted and by hand.

## Finding the powerlifting project

Project figures import `results.py` by path. The folder is resolved from, in
order: `--project` / `figures.project_dir(path)`, `$POWERLIFTING_DIR`,
`$BIOSCOUT_PROJECT_DIR`, `~/ucloud/Powerlifiting`, the known Windows path, then
the working directory. Set it once:

```bash
export POWERLIFTING_DIR=/c/Users/Basilio/ucloud/Powerlifiting   # bash
setx POWERLIFTING_DIR "C:\Users\Basilio\ucloud\Powerlifiting"   # cmd
```

The `ceinms` and `model` groups need **no** project — they only need a file path,
so they work against any session or any `.osim`.

## The groups

| group | what | source |
|---|---|---|
| `session` | per-session report figures 01–09 (markers, kinematics + moments, moment arms, muscle dynamics, muscle moments, trial-type averages, JRF) | `results.py` |
| `summary` | session / task / kinematics / JCF-compass / muscle-moment panels, poster, and `s_all` = the full `results.py` run | `results.py` |
| `calibration` | CEINMS calibration fit + MTU parameter panels | `calibration_figures.py` |
| `master` | cross-session figures: effect heatmap and dumbbell, peak JCF, factor effects, muscle ranking, work ranks, rank shift, model effects, error by model, curve overlays and diffs | `results.py` (reads `results/master_*.csv`) |
| `manuscript` | fig01 setup, fig05 metric summary, fig07 muscle forces, task panel, model overview, quick metric/curve plots | `manuscript.py` |
| `ceinms` | calibration loop, model parameters, uncalibrated vs calibrated, moment tracking, optimisation, EMG vs excitations, muscle forces | `bioscout.utils.ceinms.plot` |
| `model` | full model validation (moment arms + fibre + strength), isokinetic, moment-arm-over-motion wrap QC, JCF vs literature | `bioscout.model.inspect` |

## Notes

- The session context (`Session`, `Series`, `Legs`) is built once and reused, so
  running several `session`/`summary` figures in a row costs one load.
- `master` figures read `results/master_*.csv`. If they are missing or stale:
  `m_rescan` (or `python results.py --master`) rewrites them; `m_all` redraws
  every master figure from the CSVs already on disk in seconds.
- Output paths are unchanged — each builder still writes where it always did
  (`results/<subject>/<session>/…`, `results/master_figures/`, or the folder you
  give a `model`/`ceinms` figure).
- A figure that fails in `run_many` prints `[FAILED] <key>: <error>` and the rest
  keep going.

## Adding a figure

One line at the bottom of the relevant section in `figures.py`:

```python
_reg("m_new", "master", "what it shows",
     _m("fig_master_new_thing", "discrete"),
     [P("metric", "metric", "peak_JCF_BW")])
```

For a figure that needs the session context, take `c` as the first argument and
pass `ctx=True`:

```python
_reg("p10", "session", "what it shows",
     lambda c, trial: c.R.fig_10_thing(c.sess, c.S, trial), [TRIAL], ctx=True)
```

`P(name, prompt, default, kind, choices)` — `kind` is
`text|path|int|float|bool|list|opt` (`opt` means blank is allowed);
`choices` is a callable `(state) -> list` and gets `state["ctx"]` for
context figures, which is how the trial list is built.
