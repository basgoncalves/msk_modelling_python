"""The bioscout command line: ten verbs instead of sixty-six flags.

    bioscout                 launch the GUI (unchanged)
    bioscout help [VERB]     this, or one verb's detail
    bioscout init            start a project (folders, models, project.yaml)
    bioscout gui             launch the GUI
    bioscout model           check / edit / compare / tune-ma / scale / tps
    bioscout simulate        run an OpenSim/CEINMS stage on a session (or mrs)
    bioscout session         new / export / classify / ingest / reset -- reads
                             the results `simulate` writes, so it comes after it
    bioscout plot            figures, summaries, Collings ranking
    bioscout utils           env / install / md2pdf / pylance
    bioscout lab             EXPERIMENTAL 3.0: shots, load reports

Why this module exists
----------------------
The flat parser had grown to 66 options. Nineteen of them were basketball shot
detection and fitness-tracker imports; of the remaining forty-seven, **twenty-five
existed only to modify another flag** — their help text literally began
``With --X:``. ``--top``, ``--side``, ``--metric`` and ``--skip`` mean nothing
without ``--collings``; ``--toc``, ``--bib`` and ``--keep-docx`` mean nothing
without ``--md2pdf``. A subcommand tree makes all twenty-five disappear from the
root help without deleting a single one: they live under the verb they belong to.

Two design rules, both load-bearing:

1. **This module imports nothing but the standard library.** ``bioscout -h`` used
   to run the conda env check and import ``utils.openSim`` before it could print
   a help screen. Help must be instant and must work in a broken environment —
   it is what you reach for when nothing else runs.
2. **The old flags still work.** They are hidden from help and print one line
   naming the new form. Two real projects drive bioscout by flag from shell
   scripts; breaking them to tidy a help screen is a bad trade. Drop the aliases
   one release after everything has migrated.

How a verb reaches the old code
-------------------------------
Most verbs are *translated*: the parsed subcommand is rewritten into the legacy
flag argv, and ``__main__.py`` proceeds exactly as before, reading it off the
module-global ``args`` the same way it always did. Verbs whose implementation
is already self-contained and dependency-light (``model check``, ``utils env``)
are dispatched directly and never load the scientific stack at all.
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence, Tuple

__all__ = ["VERBS", "build_parser", "route", "main", "legacy_hint"]

#: Root verbs. ``__main__`` checks this before it builds the legacy parser.
VERBS = ("help", "init", "gui", "model", "simulate", "session",
         "plot", "utils", "lab")

#: Subcommand -> the verb it lives under. These are the words people reach for
#: at the top level because that is where the old flags were (`bioscout --env`),
#: so a bare `bioscout env` should say where it went rather than "unknown".
NESTED = {
    "env": "utils env", "install": "utils install", "md2pdf": "utils md2pdf",
    "pylance": "utils pylance",
    "new": "session new", "edit": "session edit", "export": "session export",
    "classify": "session classify", "ingest": "session ingest",
    "reset": "session reset",
    "check": "model check", "compare": "model compare", "tune-ma": "model tune-ma",
    "scale": "model scale", "tps": "model tps", "mrs": "simulate mrs", "project": "init --from-settings",
    "validate": "model validate", "joint-centres": "model joint-centres",
    "jc": "model jc",
    "summary": "plot summary", "jcf": "plot jcf", "figures": "plot figures",
}

_EPILOG = """\
examples:
  bioscout simulate so simulations/023/pre --replace
  bioscout model check models --strict
  bioscout session new simulations/022/pre
  bioscout plot --list
  bioscout help session

every verb takes --help of its own:  bioscout model --help
"""


# --------------------------------------------------------------------------- #
# the tree
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bioscout", description="Biomechanical analysis: c3d to joint contact forces.",
        epilog=_EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="verb", metavar="VERB")

    # -- help ---------------------------------------------------------------- #
    h = sub.add_parser("help", help="show help for a verb")
    h.add_argument("topic", nargs="?", metavar="VERB")

    # -- init ---------------------------------------------------------------- #
    i = sub.add_parser(
        "init", help="create a project: folders, models, templates, project.yaml",
        description="Creates the project skeleton (simulations/, models/, "
                    "setup_files/, logs/, results/) and a starter project.yaml. "
                    "With --from-settings it instead extracts project.yaml from "
                    "the project's EXISTING settings.py (the lab facts that differ "
                    "from bioscout's defaults) -- after a review run, that "
                    "settings.py can be deleted; see docs/IMPLEMENTATIONS.md §2.9.")
    i.add_argument("path", nargs="?", default=".", metavar="PROJECT_PATH")
    i.add_argument("--from-settings", action="store_true", dest="from_settings",
                   help="generate project.yaml from an existing settings.py "
                        "instead of scaffolding a new project")
    i.add_argument("--force", action="store_true",
                   help="with --from-settings: overwrite an existing project.yaml "
                        "(a .bak is kept)")

    # -- gui ----------------------------------------------------------------- #
    sub.add_parser("gui", help="launch the GUI (also the default with no verb)")

    # -- model --------------------------------------------------------------- #
    m = sub.add_parser("model", help="check, edit, compare and validate .osim models")
    ms = m.add_subparsers(dest="action", metavar="ACTION")

    mc = ms.add_parser("check", help="can every model still find its bone meshes?")
    mc.add_argument("path", nargs="*", metavar="FOLDER_OR_OSIM")
    mc.add_argument("--strict", action="store_true",
                    help="fail on anything not resolvable from the model's own folder")
    mc.add_argument("--search", action="append", metavar="DIR")
    mc.add_argument("--json", metavar="FILE")
    mc.add_argument("--project", metavar="PATH")
    mc.add_argument("-v", "--verbose", action="store_true")
    mc.add_argument("-q", "--quiet", action="store_true")

    me = ms.add_parser("edit", help="scale, set mass, change forces, moment arms, markers")
    me.add_argument("path", nargs="?", metavar="PROJECT_PATH")

    mp = ms.add_parser("compare", help="dimensions and segment masses across models")
    mp.add_argument("models", nargs="+", metavar="FOLDER_OR_OSIM")
    mp.add_argument("--scale-setups", nargs="+", metavar="LABEL=SETUP.xml",
                    help="ScaleTool setups, to report the scaling INTENT behind each")
    mp.add_argument("-o", "--out", metavar="FILE", help="write the tables to .xlsx/.csv")
    mp.add_argument("--figures", nargs="?", const=True, metavar="DIR")

    ma = ms.add_parser("tune-ma", help="adjust a muscle's moment arm, interactively")
    ma.add_argument("path", nargs="?", metavar="PROJECT_PATH")

    mv = ms.add_parser("validate", help="moment arms, fibre lengths, strength vs literature")
    mv.add_argument("--model", required=True, metavar="OSIM")
    mv.add_argument("--out", metavar="DIR")
    mv.add_argument("--side", default="_r", choices=["_r", "_l"])

    mj = ms.add_parser("joint-centres", aliases=["jc"],
                       help="add Harrington hip / midpoint knee-ankle centres to a TRC")
    mj.add_argument("trc", metavar="TRC")
    mj.add_argument("-o", "--out", metavar="FILE")
    mj.add_argument("--alias", action="append", metavar="EXPECTED=ACTUAL",
                    help="marker this lab spells differently, e.g. "
                         "--alias LPSI=LSACR --alias RKNEL=RLFC. Without these "
                         "a lab using other names gets NO joint centres.")

    # `model scale` -- interactive, session-less; `session scale` is the
    # session.yaml-driven one.
    sc_ = ms.add_parser(
        "scale", help="scale a model by answering questions (interactive)",
        description="Needs no project and no settings.py: point it at a generic "
                    ".osim and a static .trc and it works out the rest, asking "
                    "only about what it cannot determine. Shows which "
                    "measurements it can build BEFORE running, and refuses when "
                    "the femurs or tibiae are not measured -- a near-empty "
                    "MeasurementSet scales every body by 1.0 and returns generic "
                    "geometry wearing the subject's mass, which no downstream "
                    "result can reveal.")
    sc_.add_argument("--setup", "--xml", "-xml", dest="setup", metavar="XML",
                     help="run an existing ScaleTool setup XML exactly as "
                          "written (e.g. the scale_setup.xml a previous run "
                          "left beside the model) and ask nothing. Reproduces "
                          "the DIMENSIONAL scaling; marker placement is a "
                          "separate pass, see `bioscout help model`.")
    sc_.add_argument("--model", metavar="OSIM", help="generic (unscaled) model")
    sc_.add_argument("--static", metavar="TRC", help="static-trial markers")
    sc_.add_argument("--markerset", metavar="XML",
                     help="marker set to put on the model (default: its own)")
    sc_.add_argument("--mass", type=float, metavar="KG",
                     help="subject mass; default is measured from the static "
                          "GRF when a grf.mot sits beside the .trc")
    sc_.add_argument("--grf", metavar="MOT",
                     help="static-trial grf.mot to weigh the subject from "
                          "(default: grf.mot beside the .trc)")
    sc_.add_argument("-o", "--out", metavar="OSIM", help="scaled model to write")
    sc_.add_argument("--alias", action="append", metavar="EXPECTED=ACTUAL",
                     help="marker this lab spells differently, e.g. "
                          "--alias LPSI=LSACR. Repeatable; skips the prompt.")
    sc_.add_argument("--no-placer", action="store_true",
                     help="skip marker placement (dimensional scaling only)")
    sc_.add_argument("--no-scaling", action="store_true",
                     help="place markers only, do not resize the model")
    sc_.add_argument("--dry-run", action="store_true",
                     help="decide everything and show the measurements; run nothing")
    sc_.add_argument("-y", "--yes", action="store_true",
                     help="do not prompt; fail rather than ask")

    mt = ms.add_parser("tps", help="build an MRI-personalised model (interactive)",
                       description="Warps a generic model onto MRI/3D-Slicer "
                                   "landmarks. What it produces IS a model, "
                                   "which is why it lives here rather than at "
                                   "the top level.")
    mt.add_argument("path", nargs="?", metavar="PROJECT_PATH")

    # -- simulate -------------------------------------------------------------- #
    # Only the stage groupings that actually exist as separate switches today
    # (Iteration.run() in utils/session.py): IK and ID are one atomic stage
    # there (`do_exbiomec`), and JRA is produced as part of the SO or CEINMS
    # stage, not on its own -- so there's no honest standalone `ik`/`id`/`jra`
    # yet. Splitting those apart is real surgery on code with hard-won
    # production history behind it (see docs/RESTRUCTURE_PLAN.md), left for
    # a later, separately-reviewed step rather than guessed at here.
    sm = sub.add_parser(
        "simulate", help="run an OpenSim/CEINMS stage on one session's model(s)",
        description="Runs a stage of Iteration.run() directly against an "
                    "existing session (needs session.yaml -- see `session new`). "
                    "Model creation/scaling lives under `model`, not here.")
    sms = sm.add_subparsers(dest="action", metavar="ACTION")

    def _simulate_action(name, help_text):
        act = sms.add_parser(name, help=help_text)
        act.add_argument("path", metavar="SESSION_PATH")
        act.add_argument("--iteration", metavar="NAME",
                         help="which model arm (default: every one on disk)")
        act.add_argument("--trial", metavar="NAME",
                         help="restrict to these trials (comma-separated; "
                              "default: session.yaml's own trial list)")
        act.add_argument("--replace", action="store_true",
                         help="recompute outputs that already exist")
        return act

    _simulate_action("exbiomec", "inverse kinematics -> inverse dynamics")
    _simulate_action("ma", "muscle analysis")
    _simulate_action("so", "static optimisation -> muscle moments -> joint reaction")
    _simulate_action("mew", "mew (Python muscle solver) -> joint reaction, into <trial>/mew/")
    _simulate_action("ceinms", "calibrate + execute CEINMS -> joint reaction")
    # `simulate mrs` forwards to bioscout.simulate.mrs.cli's own parser (see
    # route()); registered here only so it shows in `bioscout simulate -h`.
    sms.add_parser("mrs", help="Muscle Redundancy Solver (KU Leuven, via MATLAB): "
                               "`simulate mrs check`, `simulate mrs run TRIAL`")

    # -- session ------------------------------------------------------------- #
    s = sub.add_parser("session", help="create, export, classify or reset a session")
    ss = s.add_subparsers(dest="action", metavar="ACTION")

    sn = ss.add_parser("new", help="scaffold session.yaml (opens a dialog)")
    sn.add_argument("path", nargs="?", metavar="SESSION_PATH",
                    help="session folder holding 1_c3dfiles/*.c3d")
    sn.add_argument("--from", dest="from_session", metavar="SESSION_PATH",
                    help="existing session.yaml to copy the lab constants from "
                         "(markerset, emg_map, ceinms)")
    sn.add_argument("--body-mass", type=float, metavar="KG")
    sn.add_argument("--no-gui", action="store_true",
                    help="do not open the dialog; take the values from these flags")

    sed_ = ss.add_parser("edit", help="edit an existing session.yaml in a form")
    sed_.add_argument("path", nargs="?", metavar="SESSION_PATH")
    sed_.add_argument("--no-gui", action="store_true",
                      help="do not open the editor (there is no flag equivalent yet)")

    se = ss.add_parser(
        "export", help="1_c3dfiles/*.c3d -> 2_experimental/<trial>/ (markers, GRF, EMG)",
        description="Reads each trial's .c3d from the session's 1_c3dfiles/ and "
                    "writes, per trial, into 2_experimental/<trial>/: "
                    "marker_experimental.trc, grf.mot + GRF.xml, emg.mot and the "
                    "filtered emg_filtered.mot. These are MODEL-INDEPENDENT "
                    "inputs shared by every iteration, which is why they live "
                    "beside the session and not inside 3_iterations/.")
    se.add_argument("path", metavar="SESSION_PATH")

    sc = ss.add_parser(
        "classify", help="what is each trial? (reads 2_experimental, writes a report)",
        description="Reads the markers and GRF already exported into "
                    "2_experimental/<trial>/ — so run `session export` first — "
                    "and works out what each trial IS (walking, running, squat, "
                    "jump, static...). Writes movement_detection.yaml + .png "
                    "into each trial's folder, plus movement_detection/"
                    "classification.csv (one row per trial) and "
                    "session_auto_detection.yaml beside the session. "
                    "session.yaml is NEVER modified unless you pass "
                    "--write-yaml, and then only when the session has none: a "
                    "disagreement is reported for you to accept, not applied.")
    sc.add_argument("path", metavar="SESSION_PATH")
    sc.add_argument("--no-plots", action="store_true", help="skip the per-trial QC figures")
    sc.add_argument("--write-yaml", action="store_true",
                    help="also write session.yaml when the session has none "
                         "(an existing one is never modified)")

    si = ss.add_parser(
        "ingest", help="copy loose .c3d from a capture folder INTO a session",
        description="Takes a folder of raw captures straight off the rig "
                    "(Walk01.c3d, Squat02.c3d, ...) and files them into "
                    "simulations/<subject>/<session>/1_c3dfiles/, creating the "
                    "session folder if needed. This is the step BEFORE "
                    "`session export`: ingest puts the c3d where bioscout "
                    "looks for it, export turns it into trc/mot. Skip it if "
                    "you already copied the c3d in by hand.")
    si.add_argument("folder", metavar="C3D_FOLDER")
    si.add_argument("--subject", required=True)
    si.add_argument("--session", required=True)

    ssc = ss.add_parser(
        "scale", help="scale this session's model(s) from session.yaml",
        description="Builds the scaled model for one session, driven entirely "
                    "by its session.yaml: body_mass (the static GRF wins when "
                    "readable), static_trial, markerset, marker_aliases, and "
                    "each iteration's generic / so_model / linear_scaling / "
                    "marker_placer / mvic_factor. Nothing is typed on the "
                    "command line but WHICH session. Needs no settings.py and "
                    "no project root — just the session folder. `bioscout scale` "
                    "is the interactive, session-less equivalent.")
    ssc.add_argument("path", metavar="SESSION_PATH")
    ssc.add_argument("--iteration", metavar="NAME",
                     help="which model arm (default: every one on disk)")
    ssc.add_argument("--replace", action="store_true",
                     help="rebuild a model that already exists")

    sr = ss.add_parser("reset", help="strip trials back to inputs-only")
    sr.add_argument("--subject")
    sr.add_argument("--session")
    sr.add_argument("--trial")
    sr.add_argument("--dry-run", action="store_true", help="preview, touch nothing")
    sr.add_argument("--raw", action="store_true",
                    help="also prune inputs/ down to the raw c3d")

    # -- plot ---------------------------------------------------------------- #
    pl = sub.add_parser(
        "plot", help="figures from the results on disk",
        description="Anything that is not `summary` or `collings` is taken as "
                    "figure keys, so `bioscout plot p01 s_all` and "
                    "`bioscout plot figures p01 s_all` are the same command.")
    pls = pl.add_subparsers(dest="action", metavar="ACTION")

    import argparse as _ap
    pjc = pls.add_parser("jcf", help="polar JCF direction/magnitude on the model's bones",
                         add_help=False)
    pjc.add_argument("jcf_args", nargs=_ap.REMAINDER)

    pf = pls.add_parser("figures", help="draw catalogue figures by key (the default)")
    pf.add_argument("keys", nargs="*", metavar="KEY",
                    help="figure keys (p01, s_all, m_curves, mi_ma, ...) or a group name")
    pf.add_argument("--list", action="store_true", dest="list_figures",
                    help="print the catalogue and exit")
    pf.add_argument("--project", metavar="PATH")
    pf.add_argument("--session", metavar="PATH")
    pf.add_argument("--subject", metavar="ID")

    pm = pls.add_parser("summary", help="kinematics/kinetics summary figures")
    pm.add_argument("path", nargs="?", metavar="SETTINGS_OR_PROJECT")
    pm.add_argument("--overall", action="store_true",
                    help="only rebuild the overall plots in <project>/summary")
    pm.add_argument("--subject", metavar="ID")
    pm.add_argument("--trial", metavar="NAME")
    pm.add_argument("--project", metavar="PATH")

    pc = pls.add_parser("collings", help="Collings-style muscle ranking figure")
    pc.add_argument("path", nargs="?", metavar="SESSION_PATH")
    pc.add_argument("--skip", nargs="*", metavar="ITERATION",
                    help="iterations to leave out")
    pc.add_argument("--metric", metavar="PEAK|IMPULSE")
    pc.add_argument("--side", choices=["_r", "_l"])
    pc.add_argument("--top", type=int, metavar="N")
    pc.add_argument("-o", "--out", metavar="FILE")

    # -- utils --------------------------------------------------------------- #
    u = sub.add_parser("utils", help="environment, dependencies, docs, editor setup")
    us = u.add_subparsers(dest="action", metavar="ACTION")

    ue = us.add_parser("env", help="which conda env bioscout expects vs is running in")
    ue.add_argument("--create", action="store_true",
                    help="create the expected env and install into it")

    us.add_parser("install", help="install missing dependencies")

    um = us.add_parser("md2pdf", help="markdown -> PDF (no LaTeX needed)")
    um.add_argument("files", nargs="+", metavar="FILE.md")
    um.add_argument("--outdir", metavar="DIR")
    um.add_argument("--toc", action="store_true")
    um.add_argument("--bib", metavar="FILE.bib")
    um.add_argument("--keep-docx", action="store_true")

    up = us.add_parser("pylance", help="write .vscode/settings.json so 'import bioscout' resolves")
    up.add_argument("path", nargs="?", metavar="PROJECT_DIR")

    # -- lab ----------------------------------------------------------------- #
    lab = sub.add_parser(
        "lab", help="EXPERIMENTAL (3.0): video and wearable tracking",
        description="Not part of the OpenSim pipeline and not ready. Kept here so "
                    "the MSK verbs above stay legible.")
    ls_ = lab.add_subparsers(dest="action", metavar="ACTION")

    lsh = ls_.add_parser("shots", help="basketball shot analysis from video")
    lsh.add_argument("video", metavar="VIDEO")
    lsh.add_argument("--shooting-hand", default="right", choices=["right", "left"])
    lsh.add_argument("--poses", metavar="POSES_JSON")
    lsh.add_argument("--fps", type=float)
    lsh.add_argument("--min-gap", type=float, default=1.5)
    lsh.add_argument("--n-points", type=int, default=1000)
    lsh.add_argument("--hoop-side", default="auto", choices=["auto", "right", "left"])
    lsh.add_argument("--yolo-model", metavar="WEIGHTS.pt")
    lsh.add_argument("--hoop", metavar="CX,CY,W,H")

    llr = ls_.add_parser("load-report", help="training-load & fatigue PDF from tracker exports")
    llr.add_argument("inputs", nargs="?", metavar="FILES_OR_FOLDER")
    llr.add_argument("--out", metavar="PDF")
    llr.add_argument("--hr-max", type=float)
    llr.add_argument("--hr-rest", type=float)
    llr.add_argument("--age", type=int)
    llr.add_argument("--sex", default="M", choices=["M", "F"])
    llr.add_argument("--zepp-pull", action="store_true")
    llr.add_argument("--strava-pull", action="store_true")
    llr.add_argument("--creds", metavar="JSON")

    la = ls_.add_parser("add-subject", help="add a player-tracking subject to subjects.json")
    la.add_argument("path", nargs="?", metavar="PROJECT_PATH")

    return p


# --------------------------------------------------------------------------- #
# legacy flags -> the verb that replaced them
# --------------------------------------------------------------------------- #
_LEGACY = {
    "--init": "bioscout init", "--gui": "bioscout gui", "-g": "bioscout gui",
    "--new-session": "bioscout session new", "--c3d-export": "bioscout session export",
    "--export-session": "bioscout session export",
    "--classifier": "bioscout session classify", "--classify": "bioscout session classify",
    "--ingest-c3d": "bioscout session ingest", "--reset": "bioscout session reset",
    "--model-edit": "bioscout model edit", "--model_edit": "bioscout model edit",
    "--edit": "bioscout model edit",
    "--compare-models": "bioscout model compare",
    "--compare_models": "bioscout model compare",
    "--change-moment-arms": "bioscout model tune-ma", "--ma": "bioscout model tune-ma",
    "--joint-centres": "bioscout model joint-centres",
    "--joint-centers": "bioscout model joint-centres", "--jc": "bioscout model joint-centres",
    "--tps": "bioscout model tps",
    "--summary": "bioscout plot summary", "--collings": "bioscout plot collings",
    "--env": "bioscout utils env", "--env-check": "bioscout utils env",
    "--env-create": "bioscout utils env --create", "--install": "bioscout utils install",
    "--md2pdf": "bioscout utils md2pdf", "--pylance-fix": "bioscout utils pylance",
    "--shots": "bioscout lab shots", "--load-report": "bioscout lab load-report",
    "--add_subject": "bioscout lab add-subject",
}


def legacy_hint(argv: Sequence[str]) -> Optional[str]:
    """One-line nudge for the first legacy flag in ``argv``, or None.

    Deliberately a hint and not a warning: these still work, and a script that
    prints a WARNING on every run trains people to ignore warnings.
    """
    for a in argv:
        new = _LEGACY.get(a.split("=")[0])
        if new:
            return f"[bioscout] `{a}` still works; the new form is `{new}`."
    return None


# --------------------------------------------------------------------------- #
# verb -> legacy argv
# --------------------------------------------------------------------------- #
def _flag(out: List[str], name: str, value, *, store_true: bool = False) -> None:
    """Append ``name`` (and its value) when the option was actually given."""
    if value in (None, False, "", []):
        return
    out.append(name)
    if not store_true:
        out.extend([str(v) for v in value] if isinstance(value, list) else [str(value)])


def _to_legacy(ns: argparse.Namespace) -> List[str]:      # noqa: C901 — a flat lookup table
    v, a = ns.verb, getattr(ns, "action", None)
    out: List[str] = []

    if v == "init":
        return ["--init", ns.path]
    if v == "gui":
        return ["--gui"]

    if v == "session":
        if a == "scale":
            out = ["--scale-session", ns.path]
            _flag(out, "--iteration", ns.iteration)
            _flag(out, "--REPLACE", ns.replace, store_true=True)
            return out
        if a == "new":
            out = ["--new-session", ns.path or "."]
            _flag(out, "--from-session", ns.from_session)
            _flag(out, "--body-mass", ns.body_mass)
            return out
        if a == "edit":
            print("[session edit] needs a display — there is no flag equivalent. "
                  "Edit simulations/<subject>/<session>/session.yaml directly, or "
                  "use the GUI's File Editor tab.")
            return []
        if a == "export":
            return ["--c3d-export", ns.path]
        if a == "classify":
            out = ["--classifier", ns.path]
            _flag(out, "--no-plots", ns.no_plots, store_true=True)
            _flag(out, "--write-session-yaml", ns.write_yaml, store_true=True)
            return out
        if a == "ingest":
            return ["--ingest-c3d", ns.folder, "--subject", ns.subject,
                    "--session", ns.session]
        if a == "reset":
            out = ["--reset"]
            _flag(out, "--subject", ns.subject)
            _flag(out, "--session", ns.session)
            _flag(out, "--trial", ns.trial)
            _flag(out, "--reset-dry-run", ns.dry_run, store_true=True)
            _flag(out, "--reset-raw", ns.raw, store_true=True)
            return out

    if v == "model":
        if a == "edit":
            return ["--model-edit"] + ([ns.path] if ns.path else [])
        if a == "tune-ma":
            return ["--change-moment-arms"] + ([ns.path] if ns.path else [])
        if a == "compare":
            out = ["--compare-models"] + list(ns.models)
            _flag(out, "--scale-setups", ns.scale_setups)
            _flag(out, "-o", ns.out)
            if ns.figures is True:
                out.append("--figures")
            elif ns.figures:
                out += ["--figures", str(ns.figures)]
            return out
        if a == "tps":
            return ["--tps"] + ([ns.path] if ns.path else [])
        if a in ("joint-centres", "jc"):
            out = ["--joint-centres", ns.trc]
            _flag(out, "-o", ns.out)
            for a_ in (getattr(ns, "alias", None) or []):
                out += ["--alias", a_]
            return out

    if v == "model" and a == "scale":
        if ns.setup:
            out = ["--scale-setup", ns.setup]
            _flag(out, "--mass", ns.mass)
            return out
        out = ["--scale-model"]
        _flag(out, "--scale-generic", ns.model)
        _flag(out, "--static", ns.static)
        _flag(out, "--markerset", ns.markerset)
        _flag(out, "--mass", ns.mass)
        _flag(out, "--grf", ns.grf)
        _flag(out, "-o", ns.out)
        for a_ in (ns.alias or []):
            out += ["--alias", a_]
        _flag(out, "--no-placer", ns.no_placer, store_true=True)
        _flag(out, "--no-scaling", ns.no_scaling, store_true=True)
        _flag(out, "--dry-run", ns.dry_run, store_true=True)
        _flag(out, "-y", ns.yes, store_true=True)
        return out



    if v == "plot":
        if a == "summary":
            out = ["--summary"] + ([ns.path] if ns.path else [])
            _flag(out, "-overall", ns.overall, store_true=True)
            _flag(out, "-s", ns.subject)
            _flag(out, "-t", ns.trial)
            _flag(out, "-p", ns.project)
            return out
        if a == "collings":
            out = ["--collings"] + ([ns.path] if ns.path else [])
            _flag(out, "--skip", ns.skip)
            _flag(out, "--metric", ns.metric)
            _flag(out, "--side", ns.side)
            _flag(out, "--top", ns.top)
            _flag(out, "-o", ns.out)
            return out

    if v == "utils":
        if a == "install":
            return ["--install"]
        if a == "md2pdf":
            out = ["--md2pdf"] + list(ns.files)
            _flag(out, "--outdir", ns.outdir)
            _flag(out, "--toc", ns.toc, store_true=True)
            _flag(out, "--bib", ns.bib)
            _flag(out, "--keep-docx", ns.keep_docx, store_true=True)
            return out
        if a == "pylance":
            return ["--pylance-fix"] + ([ns.path] if ns.path else [])

    if v == "lab":
        if a == "shots":
            out = ["--shots", ns.video,
                   "--shooting-hand", ns.shooting_hand,
                   "--hoop-side", ns.hoop_side,
                   "--min-gap", str(ns.min_gap), "--n-points", str(ns.n_points)]
            _flag(out, "--poses", ns.poses)
            _flag(out, "--fps", ns.fps)
            _flag(out, "--yolo-model", ns.yolo_model)
            _flag(out, "--hoop", ns.hoop)
            return out
        if a == "load-report":
            out = ["--load-report", ns.inputs or "."]
            _flag(out, "--load-out", ns.out)
            _flag(out, "--hr-max", ns.hr_max)
            _flag(out, "--hr-rest", ns.hr_rest)
            _flag(out, "--age", ns.age)
            out += ["--sex", ns.sex]
            _flag(out, "--zepp-pull", ns.zepp_pull, store_true=True)
            _flag(out, "--strava-pull", ns.strava_pull, store_true=True)
            _flag(out, "--creds", ns.creds)
            return out
        if a == "add-subject":
            return ["--add_subject"] + ([ns.path] if ns.path else [])

    return out


# --------------------------------------------------------------------------- #
# verbs that need nothing heavy
# --------------------------------------------------------------------------- #
def _direct(ns: argparse.Namespace) -> Optional[int]:
    """Run a verb here and return its exit code, or None to fall through.

    Only for implementations that are already self-contained: running them here
    means the scientific stack is never imported, so they work on a machine where
    the environment is half-built — which is exactly when you need them.
    """
    v, a = ns.verb, getattr(ns, "action", None)

    if v == "model" and a == "check":
        from bioscout.model.cli import main as _check
        argv = ["--verify"] + list(ns.path)
        if not ns.path:
            argv += ["--project", ns.project or "."]
        for name, val in (("--strict", ns.strict), ("--verbose", ns.verbose),
                          ("--quiet", ns.quiet)):
            if val:
                argv.append(name)
        for d in (ns.search or []):
            argv += ["--search", d]
        if ns.json:
            argv += ["--json", ns.json]
        return _check(argv)

    if v == "init" and getattr(ns, "from_settings", False):
        # Imports the project's settings.py, which needs the full stack — but
        # the extraction itself is one call and prints its own verdict.
        from bioscout.init.project_config import init_project_yaml
        return init_project_yaml(ns.path, force=ns.force)

    if v == "utils" and a == "env":
        from bioscout.devtools.envcheck import ensure
        st = ensure(create=bool(ns.create))
        return 0 if (st["match"] or st["env_exists"]) else 1

    if v == "session" and a in ("new", "edit") and not getattr(ns, "no_gui", False):
        # One editor for both verbs: it detects whether session.yaml is already
        # there and offers to create it or edits it in place, which is what you
        # want when `session new` is pointed at a folder that turns out to have
        # one. --no-gui, or no display, falls through to the flag path below.
        try:
            from bioscout.gui.session_editor import gui_available, open_session_editor
        except Exception:
            return None
        if not gui_available():
            # Headless — ssh, CI, a container. Fall through to the flags rather
            # than exit 0 having written nothing, which reads as success.
            return None
        return open_session_editor(ns.path)

    if v == "plot" and a == "jcf":
        from bioscout.plot.jcf_direction import main as _jcf
        return _jcf(ns.jcf_args) or 0

    if v == "plot" and a == "figures":
        from bioscout.plot.figures import main as _figures
        argv = list(ns.keys)
        if ns.list_figures:
            argv.append("--list")
        for name, val in (("--project", ns.project), ("--session", ns.session),
                          ("--subject", ns.subject)):
            if val:
                argv += [name, val]
        return _figures(argv) or 0

    if v == "model" and a == "validate":
        from bioscout.model.inspect.__main__ import main as _mi
        argv = ["all", "--model", ns.model, "--side", ns.side]
        if ns.out:
            argv += ["--out", ns.out]
        return _mi(argv)

    if v == "simulate":
        # Direct dispatch straight to Iteration.run() via the Session it
        # belongs to -- no legacy flag translation exists for this (there is
        # no old flat-flag equivalent of a single simulate stage). Session()
        # raises a clear FileNotFoundError when session.yaml is missing rather
        # than silently doing nothing, which is exactly what a run command
        # should do on a bad path.
        from bioscout.session.recording import Session
        stage_kwarg = {"exbiomec": "do_exbiomec", "ma": "do_muscle_analysis",
                       "so": "do_so", "mew": "do_mew", "ceinms": "do_ceinms"}[a]
        try:
            s = Session(ns.path)
        except FileNotFoundError as e:
            print(f"[simulate] {e}", file=sys.stderr)
            return 1
        iterations = [ns.iteration] if ns.iteration else None
        trials = [t.strip() for t in ns.trial.split(",")] if ns.trial else None
        results = s.run(iterations=iterations, trials=trials,
                        replace=bool(ns.replace), **{stage_kwarg: True})
        print(f"[simulate {a}] {ns.path}: {results}")
        return 0

    return None


# --------------------------------------------------------------------------- #
# entry
# --------------------------------------------------------------------------- #
def route(argv: Sequence[str]) -> Tuple[str, object]:
    """Decide what a new-style argv means.

    Returns ``("exit", code)`` when the verb is finished, or
    ``("legacy", [flags])`` when ``__main__`` should carry on with the old
    machinery using the translated argv.
    """
    parser = build_parser()
    argv = list(argv)

    # `simulate mrs` owns its own parser (same forwarding trick as `plot jcf`).
    if argv[:2] == ["simulate", "mrs"]:
        from bioscout.simulate.mrs.cli import main as _mrs
        return ("exit", _mrs(argv[2:]) or 0)

    # `plot jcf` forwards its whole tail to the module's own parser (argparse
    # REMAINDER does not reliably swallow leading options like -h).
    if argv[:2] == ["plot", "jcf"]:
        from bioscout.plot.jcf_direction import main as _jcf
        return ("exit", _jcf(argv[2:]) or 0)

    # `bioscout plot p01 s_all` == `bioscout plot figures p01 s_all`. argparse
    # cannot have both a free positional list and subcommands on one parser, so
    # the default action is inserted here rather than fought for in the grammar.
    if len(argv) >= 1 and argv[0] == "plot":
        rest = argv[1:]
        # `plot --help` must show the VERB's help — the list of actions — not
        # the default action's, or summary and collings become undiscoverable.
        if rest and rest[0] in ("-h", "--help"):
            pass
        elif not rest or rest[0] not in ("figures", "summary", "collings", "jcf"):
            argv = ["plot", "figures"] + rest

    # `bioscout help [VERB]` == `bioscout [VERB] --help`
    if argv and argv[0] == "help":
        topic = argv[1] if len(argv) > 1 else None
        if topic and topic in VERBS:
            parser.parse_args([topic, "--help"])        # exits
        parser.print_help()
        return ("exit", 0)

    ns = parser.parse_args(argv)

    if not getattr(ns, "verb", None):
        parser.print_help()
        return ("exit", 0)

    # A verb with subcommands, given none: show that verb's help rather than
    # silently doing nothing.
    if ns.verb in ("session", "model", "utils", "lab", "plot", "simulate") and not getattr(ns, "action", None):
        parser.parse_args([ns.verb, "--help"])          # exits

    code = _direct(ns)
    if code is not None:
        return ("exit", code)

    return ("legacy", _to_legacy(ns))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Standalone entry: ``python -m bioscout.cli <verb> ...``."""
    kind, value = route(list(sys.argv[1:] if argv is None else argv))
    if kind == "exit":
        return int(value)                                # type: ignore[arg-type]
    import runpy
    sys.argv = [sys.argv[0]] + list(value)               # type: ignore[arg-type]
    runpy.run_module("bioscout", run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
