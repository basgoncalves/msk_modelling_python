# bioscout docs

Two kinds of document, kept apart on purpose.

**`guide/`** — evergreen reference. Describes how something works *now*; edit
in place when the behaviour changes. No dates in the filenames.

**`history/`** — dated records: a bug found, a fix, a plan. Written once and
then superseded, never rewritten. Filenames carry the date of the event, so
`ls history/` is the timeline.

---

## guide/

| file | what it covers |
|---|---|
| [project-setup.md](guide/project-setup.md) | the session folder layout, `session.yaml`, creating a session, `settings.py`, the test fixture |
| [plotting.md](guide/plotting.md) | `bioscout.plot` — the comparison-figure builder, and the 62-figure catalogue |
| [jcf-contributions.md](guide/jcf-contributions.md) | muscle contributions to the joint contact force (`run_jra_contributions`) |
| [jcf-direction.md](guide/jcf-direction.md) | `bioscout plot jcf` — the JCF direction/magnitude polar plot |
| [model-ma-check.md](guide/model-ma-check.md) | `mi_check` — moment-arm discontinuity check straight from a model |
| [mrs.md](guide/mrs.md) | `bioscout simulate mrs` — the KU Leuven Muscle Redundancy Solver wrapper |
| [releasing.md](guide/releasing.md) | building and uploading the package to PyPI |

## history/

| date | file | what happened |
|---|---|---|
| (inherited) | [2026-08-11-bops-issues.md](history/2026-08-11-bops-issues.md) | OpenSim import / C3D export / CEINMS troubleshooting carried over from the predecessor `bops` project. Date is the file's timestamp, not a content date. |
| 2026-08-11 | *(folded into `guide/project-setup.md`)* | the numbered session layout landed |
| 2026-08-17 | [2026-08-17-implementations.md](history/2026-08-17-implementations.md) | what bioscout needs to serve labs beyond us — field bugs, the settings.py retirement design, the stage registry, the model axis |
| 2026-08-24 | [2026-08-24-proposal-models-and-cwd.md](history/2026-08-24-proposal-models-and-cwd.md) | models layout, opt-in `muscle_opt`, and making the working directory stop moving (+ the 2026-09-08 second-IK-call-site fix as an appendix) |
| 2026-08-25 | [2026-08-25-gui-fixes.md](history/2026-08-25-gui-fixes.md) | GUI round 1 and 2 — settings.py discovery, font rescaling, C3D export layout |
| 2026-09-07 | [2026-09-07-scaling-marker-names.md](history/2026-09-07-scaling-marker-names.md) | scaling assumed the powerlifting marker set; the alias map, `bioscout scale`, and the 1-of-13 floor |
| 2026-09-08 | [2026-09-08-v3-restructure-plan.md](history/2026-09-08-v3-restructure-plan.md) | the CLI + package restructure to v3.0.3 — all 12 stages done |
| — | [settings-py-annotated.md](history/settings-py-annotated.md) | every explanatory comment from the pre-streamline `settings.py`, kept verbatim. Archived: it documents a file [2026-08-17-implementations.md](history/2026-08-17-implementations.md) §2.9 proposes retiring in favour of `project.yaml` + `session.yaml`. |

`_figures/` holds the SVG sources referenced by the 2026-08-17 implementations doc.
