"""The bioscout seam. The ONLY module that imports bioscout, and lazily.

Two entry points:

* :func:`analyser_from_trial_dir` -- pure path convention, no bioscout import.
  Works on any folder that follows bioscout's LAYOUT_DIRS.
* :func:`analyser_from_iteration` -- takes a live ``bioscout.session``
  Iteration and pulls body mass, emg_map, side and time_range from session.yaml.

Output goes where bioscout already looks: ``<trial>/ceinms/Optimised/
MuscleForces.sto``. ``ml_model.ceinms_forces_path()``, the plotting code and
``summarize_results.py`` then work unchanged.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

# bioscout.core.analysis.LAYOUT_DIRS, duplicated so this module is importable
# with no bioscout. Verified against bioscout/core/analysis.py (2026-09-10).
LAYOUT_DIRS = {
    "inputs": "inputs",
    "extbio": "external_biomechanics",
    "muscle_analysis": "muscle_analysis",
    "static_optimisation": "static_optimisation",
    "ceinms": "ceinms",
    "joint_contact_forces": "joint_contact_forces",
}

TRIAL_FILES = {
    "kinematics": ("extbio", "joint_angles.mot"),
    "moments":    ("extbio", "inverse_dynamics.sto"),
    "grf":        ("inputs", "grf.mot"),
    "emg":        ("inputs", "emg_filtered_normalised.mot"),
}
MA_DIR = LAYOUT_DIRS["muscle_analysis"]
CEINMS_FORCES = os.path.join(LAYOUT_DIRS["ceinms"], "Optimised", "MuscleForces.sto")


OUTPUT_DIR = "mew"
SO_FORCES = os.path.join(LAYOUT_DIRS["static_optimisation"],
                         "SO_StaticOptimization_force.sto")
CEINMS_FORCES_REL = os.path.join(LAYOUT_DIRS["ceinms"], "Optimised", "MuscleForces.sto")
#  CEINMS output dirs. `Execution` is where CEINMS.exe writes and `Optimised`
#  where CEINMSoptimise writes; bioscout's execution modes (simulate/ceinms/modes.py)
#  TAG each non-production arm with its weights -- `Execution_a10_b1_g1000` --
#  so a bounds/full_loop/lcurve run leaves several arms side by side and the
#  plain untagged name may not exist at all. Looking only for `Optimised/` finds
#  nothing on a perfectly normal trial (FAIS 022/Run_baselineA1, 2026-09-02).
CEINMS_OUT_PREFIXES = ("Optimised", "Execution")
EXPERIMENTAL_DIRS = ("2_experimental", "experimental")


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def find_session_dir(trial_dir) -> Optional[str]:
    """Walk up from a trial folder to the session dir (the one with session.yaml).

    Layout is ``<session>/3_iterations/<iteration>/<trial>``, so it is normally
    three levels up -- but the search is by CONTENT (session.yaml or an
    experimental root), not by depth, so a flat or renamed layout still works.
    """
    d = os.path.abspath(str(trial_dir))
    for _ in range(5):
        d = os.path.dirname(d)
        if not d or d == os.path.dirname(d):
            break
        if os.path.exists(os.path.join(d, "session.yaml")):
            return d
        if any(os.path.isdir(os.path.join(d, e)) for e in EXPERIMENTAL_DIRS):
            return d
    return None


def experimental_dir(trial_dir) -> Optional[str]:
    """``<session>/2_experimental/<trial>`` -- where the RAW inputs live once.

    bioscout keeps grf.mot / emg / GRF.xml at the SESSION level and shares them
    across iterations; only derived output lives under the trial. Missing this
    is the difference between reaching tier 2 and silently running tier 1.
    """
    session = find_session_dir(trial_dir)
    if not session:
        return None
    trial = os.path.basename(os.path.normpath(str(trial_dir)))
    for e in EXPERIMENTAL_DIRS:
        cand = os.path.join(session, e, trial)
        if os.path.isdir(cand):
            return cand
    return None


def read_session_yaml(trial_dir) -> Dict:
    """body_mass, emg_map, per-trial side/type from session.yaml. No bioscout needed.

    Returns ``{}`` when there is no session.yaml or no pyyaml -- every caller
    treats the contents as optional refinement, never as a requirement.
    """
    session = find_session_dir(trial_dir)
    if not session:
        return {}
    path = os.path.join(session, "session.yaml")
    if not os.path.exists(path):
        return {}
    try:
        import yaml                                        # noqa: WPS433
        with open(path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception:
        return {}

    trial = os.path.basename(os.path.normpath(str(trial_dir)))
    meta = ((cfg.get("trials") or {}).get(trial) or {})
    emg_map = cfg.get("emg_map") or {}
    # a session may carry SEVERAL NAMED maps; without an iteration to pick one,
    # take the single map if there is only one, else leave it to the caller.
    if emg_map and all(isinstance(v, dict) for v in emg_map.values()):
        emg_map = next(iter(emg_map.values())) if len(emg_map) == 1 else {}
    return {
        "body_mass": cfg.get("body_mass"),
        "subject": str(cfg.get("subject") or ""),
        "emg_map": emg_map,
        "time_range": meta.get("time_range"),
        "side": meta.get("side", "both"),
        "trial_type": meta.get("type"),
        "ceinms": cfg.get("ceinms") or {},
        "session_dir": session,
    }


def _fmt_weight(v):
    """modes.fmt: 10.0 -> "10", 0.5 -> "0.5" -- the tag must match byte for byte."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return str(int(f)) if f == int(f) else str(f)


def find_ceinms_forces(trial_dir, ceinms_cfg=None) -> Optional[str]:
    """The CEINMS MuscleForces.sto for a trial, across every output layout.

    Preference order, and the reason for it:

    1. the arm whose tag matches ``session.yaml``'s ``ceinms: alpha/beta/gamma``
       -- on a multi-arm run that is the PRODUCTION result, and picking it by
       name beats picking by timestamp (a later sweep arm is not the answer)
    2. the untagged ``Optimised/`` then ``Execution/`` -- a single-mode run
    3. legacy ``<trial>/Optimised/`` from before the ceinms/ subfolder
    4. any tagged arm, most recently written -- with nothing to disambiguate,
       newest is the least surprising guess
    """
    trial_dir = str(trial_dir)
    ce_dir = os.path.join(trial_dir, LAYOUT_DIRS["ceinms"])
    name = "MuscleForces.sto"

    cfg = ceinms_cfg or {}
    a, b, g = (_fmt_weight(cfg.get(k)) for k in ("alpha", "beta", "gamma"))
    if a and b and g:
        tag = f"a{a}_b{b}_g{g}"
        hit = _first_existing(*[os.path.join(ce_dir, f"{p}_{tag}", name)
                                for p in CEINMS_OUT_PREFIXES])
        if hit:
            return hit

    hit = _first_existing(
        *[os.path.join(ce_dir, p, name) for p in CEINMS_OUT_PREFIXES],
        os.path.join(trial_dir, "Optimised", name),
        os.path.join(trial_dir, "Execution", name))
    if hit:
        return hit

    if not os.path.isdir(ce_dir):
        return None
    arms = [os.path.join(ce_dir, d, name) for d in sorted(os.listdir(ce_dir))
            if d.startswith(CEINMS_OUT_PREFIXES)
            and os.path.exists(os.path.join(ce_dir, d, name))]
    if not arms:
        return None
    return max(arms, key=os.path.getmtime)


def output_dir(trial_dir, create=True) -> str:
    """``<trial>/mew/`` -- this package's own output folder.

    Kept separate from ``ceinms/`` and ``static_optimisation/`` so a
    mew run never overwrites a CEINMS or SO result. Writing into
    ``ceinms/Optimised/`` is opt-in (``--ceinms-compat``) for when you WANT the
    existing plotting and summary code to pick these forces up.
    """
    d = os.path.join(str(trial_dir), OUTPUT_DIR)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def discover_trial(trial_dir) -> Dict[str, Optional[str]]:
    """Which canonical inputs this trial folder actually has."""
    trial_dir = str(trial_dir)
    found: Dict[str, Optional[str]] = {}
    for key, (folder, fname) in TRIAL_FILES.items():
        found[key] = _first_existing(
            os.path.join(trial_dir, LAYOUT_DIRS[folder], fname),
            os.path.join(trial_dir, fname),                     # flat legacy layout
        )
    # the FAIS training layout calls them ik.mot / id.sto / emg.mot
    found["kinematics"] = found["kinematics"] or _first_existing(
        os.path.join(trial_dir, "ik.mot"))
    found["moments"] = found["moments"] or _first_existing(
        os.path.join(trial_dir, "id.sto"))
    found["emg"] = found["emg"] or _first_existing(os.path.join(trial_dir, "emg.mot"))

    # Raw inputs live ONCE at <session>/2_experimental/<trial>/ and are shared
    # by every iteration -- the trial folder holds only derived output.
    exp = experimental_dir(trial_dir)
    if exp:
        found["grf"] = found["grf"] or _first_existing(os.path.join(exp, "grf.mot"))
        found["emg"] = found["emg"] or _first_existing(
            os.path.join(exp, "emg_filtered_normalised.mot"),
            os.path.join(exp, "emg_filtered.mot"))
        found["grf_xml"] = _first_existing(os.path.join(exp, "GRF.xml"))
    else:
        found["grf_xml"] = None

    ma = os.path.join(trial_dir, MA_DIR)
    found["moment_arms"] = ma if os.path.isdir(ma) and os.listdir(ma) else None
    found["so_forces"] = _first_existing(os.path.join(trial_dir, SO_FORCES))
    found["ceinms_forces"] = find_ceinms_forces(
        trial_dir, (read_session_yaml(trial_dir) or {}).get("ceinms"))
    return found


def forces_output_path(trial_dir) -> str:
    """Where to write, matching what bioscout/ml_model already read."""
    return os.path.join(str(trial_dir), CEINMS_FORCES)


# --------------------------------------------------------------------------- #
#  Constructors
# --------------------------------------------------------------------------- #
def analyser_from_trial_dir(trial_dir, model, *, height=None, mass=None,
                            emg_map=None, theta_file=None, **kw):
    """Build a Mew from a bioscout-layout trial folder."""
    from .analyser import Mew

    trial_dir = str(trial_dir)
    f = discover_trial(trial_dir)
    if not f["kinematics"]:
        raise FileNotFoundError(
            f"no joint_angles.mot / ik.mot under {trial_dir} -- run IK first")

    # session.yaml is the source of truth for body mass and the electrode map;
    # explicit arguments still win.
    sess = read_session_yaml(trial_dir)
    return Mew(
        model=model, height=height,
        mass=mass if mass is not None else sess.get("body_mass"),
        name=sess.get("subject") or "subject",
        kinematics=f["kinematics"], moments=f["moments"], grf=f["grf"],
        emg=f["emg"], moment_arms=f["moment_arms"],
        emg_map=emg_map if emg_map is not None else (sess.get("emg_map") or {}),
        time_range=sess.get("time_range"), side=sess.get("side", "both"),
        trial_type=sess.get("trial_type"),
        trial_name=os.path.basename(os.path.normpath(trial_dir)),
        theta_file=theta_file, **kw)


def analyser_from_iteration(iteration, trial, *, height=None, theta_file=None, **kw):
    """Build from a live bioscout ``Iteration``, honouring session.yaml.

        from bioscout.session import Session
        it = Session(session_dir).iteration("rajagopal_fai")
        ma = Mew.from_bioscout(it, "Run_baselineA1")
    """
    from .analyser import Mew

    cfg = {}
    try:
        cfg = iteration.trial_config(trial) or {}
    except Exception:
        pass

    trial_dir = os.path.join(str(iteration.path), str(trial))
    f = discover_trial(trial_dir)
    if not f["kinematics"]:
        raise FileNotFoundError(
            f"no joint_angles.mot under {trial_dir} -- run IK for this trial first")

    model = _resolve_model(iteration, cfg)
    if theta_file is None:
        cand = os.path.join(str(iteration.path), "..", "mew_theta.json")
        theta_file = cand if os.path.exists(cand) else None

    return Mew(
        model=model,
        height=height,
        mass=cfg.get("body_mass"),
        name=_subject_name(iteration),
        kinematics=f["kinematics"], moments=f["moments"], grf=f["grf"],
        emg=f["emg"], moment_arms=f["moment_arms"],
        emg_map=cfg.get("emg_map") or {},
        time_range=cfg.get("time_range"),
        side=cfg.get("side", "both"),
        trial_type=cfg.get("trial_type"),
        trial_name=str(trial), theta_file=theta_file, **kw)


def _subject_name(iteration) -> str:
    """``Iteration.subject_name`` is a property; older builds had a method."""
    v = getattr(iteration, "subject_name", None)
    if callable(v):
        v = v()
    return str(v) if v else "subject"


def _trial_names(iteration):
    """Non-static trial NAMES. ``Iteration.trials`` yields Analyse objects."""
    fn = getattr(iteration, "_trial_names", None)
    if callable(fn):
        return list(fn())
    return [getattr(t, "trial_name", None) or getattr(t, "name", str(t))
            for t in (getattr(iteration, "trials", None) or [])]


def _resolve_model(iteration, cfg) -> str:
    """The .osim this iteration runs with. session.yaml is the source of truth.

    ``Iteration.model_file("SO")`` gives it: ``model_scaled`` (relative to the
    iteration folder in session.yaml), x ``mvic_factor`` when that is not 1.
    """
    fn = getattr(iteration, "model_file", None)
    if callable(fn):
        md = fn("SO")
        if md and os.path.isfile(str(md)):
            return str(md)
    for key in ("model_scaled",):
        val = cfg.get(key)
        if val:
            try:
                return iteration.resolve_model_file(val)
            except Exception:
                if os.path.exists(str(val)):
                    return str(val)
    for attr in ("model_file", "osim_model"):
        val = getattr(iteration, attr, None)
        if val and os.path.exists(str(val)):
            return str(val)
    raise ValueError(
        "could not resolve the .osim for this iteration -- pass model=... "
        "explicitly, or check the iteration's model entry in session.yaml")


# --------------------------------------------------------------------------- #
#  Batch
# --------------------------------------------------------------------------- #
def run_iteration(iteration, trials=None, *, write=True, extra=True,
                  height=None, tier=None, verbose=True) -> Dict[str, object]:
    """Solve every trial of a bioscout iteration. Returns {trial: result | Exception}.

    Never raises for one bad trial -- a batch that stops at trial 3 of 40 is the
    failure mode this whole package is reacting against.
    """
    from .analyser import Mew   # noqa: F401  (import check)

    names = list(trials) if trials else _trial_names(iteration)
    out: Dict[str, object] = {}
    for name in names:
        try:
            ma = analyser_from_iteration(iteration, name, height=height)
            res = ma.run(tier=tier)
            if write:
                res.write_sto(forces_output_path(
                    os.path.join(str(iteration.path), name)), extra=extra)
            out[name] = res
            if verbose:
                print(f"  {res.summary()}")
        except Exception as exc:
            out[name] = exc
            if verbose:
                print(f"  {name}: FAILED -- {type(exc).__name__}: {exc}")
    return out
