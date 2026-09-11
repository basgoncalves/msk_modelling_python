"""Where things live inside a session folder — old and new layouts.

A session used to be a flat pile of folders::

    <session>/
        c3dfiles/            raw captures
        experimental/        model-independent exports (markers, GRF, EMG)
        cateli/              model iteration
        gpk/                 model iteration
        logs/  results/  ...

which sorts alphabetically into an order that says nothing about the pipeline,
and mixes iterations in with shared inputs. The numbered layout fixes both::

    <session>/
        1_c3dfiles/
        2_experimental/
        3_iterations/
            cateli/
            gpk/
        logs/  results/  ...

**Both are supported.** Every resolver here prefers whichever form already
exists on disk and falls back to the numbered name when creating something new,
so existing sessions (and other projects, and collaborators' copies) keep
working untouched while new output adopts the numbered names. Nothing here
renames anything — migration is a deliberate, separate act.

Call the resolvers rather than joining these names by hand; that is the only
thing keeping the two layouts from drifting apart.
"""
from __future__ import annotations

import os
from typing import Iterable, Optional

__all__ = [
    "C3D_DIRS", "EXPERIMENTAL_DIRS", "ITERATIONS_DIRS", "NON_ITERATION_DIRS",
    "c3d_root", "experimental_root", "iterations_root", "iteration_path",
    "is_numbered_layout",
]

#: Accepted names per role, **preferred first**. The first entry is what gets
#: created; later entries are recognised for back-compatibility.
C3D_DIRS = ("1_c3dfiles", "c3dfiles")
EXPERIMENTAL_DIRS = ("2_experimental", "experimental")
ITERATIONS_DIRS = ("3_iterations",)

#: Folders directly under a session that are never model iterations. Includes
#: both spellings of the shared dirs plus the iteration parent itself.
NON_ITERATION_DIRS = frozenset(
    set(C3D_DIRS) | set(EXPERIMENTAL_DIRS) | set(ITERATIONS_DIRS)
    | {"logs", "results", "manuscript", "recordings", "models", "setup_files",
       "setupFiles"}
)


def _first_existing(session_dir: str, names: Iterable[str]) -> Optional[str]:
    for n in names:
        p = os.path.join(session_dir, n)
        if os.path.isdir(p):
            return p
    return None


def _resolve(session_dir: str, names, create: bool = False) -> str:
    """Existing folder for a role, else the preferred (numbered) name."""
    found = _first_existing(session_dir, names)
    if found:
        return found
    path = os.path.join(session_dir, names[0])
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def is_numbered_layout(session_dir: str) -> bool:
    """True when this session already uses the numbered folder names."""
    return any(
        os.path.isdir(os.path.join(session_dir, n))
        for n in (C3D_DIRS[0], EXPERIMENTAL_DIRS[0], ITERATIONS_DIRS[0])
    )


def c3d_root(session_dir: str, create: bool = False) -> str:
    """Folder holding this session's raw ``.c3d`` captures."""
    return _resolve(session_dir, C3D_DIRS, create)


def experimental_root(session_dir: str, subdir: Optional[str] = None,
                      create: bool = False) -> str:
    """Folder holding model-independent exports (markers, GRF, EMG).

    ``subdir`` overrides the name entirely — that is how a downsample run
    redirects to e.g. ``experimental_ds10``. An override is used verbatim
    (no numbered/plain resolution), since it names one specific variant.
    """
    if subdir and subdir not in EXPERIMENTAL_DIRS:
        path = os.path.join(session_dir, subdir)
        if create:
            os.makedirs(path, exist_ok=True)
        return path
    return _resolve(session_dir, EXPERIMENTAL_DIRS, create)


def iterations_root(session_dir: str, create: bool = False) -> str:
    """Parent folder of the model iterations.

    Resolution order:
      1. ``<session>/3_iterations`` if it exists;
      2. ``<session>/3_iterations`` if the session is otherwise numbered
         (``1_c3dfiles``/``2_experimental`` present) — a numbered session
         should not start dropping iterations at the top level;
      3. the session folder itself if the session is in the old flat layout;
      4. ``<session>/3_iterations`` for a session with nothing in it yet, so
         new sessions get the numbered layout.
    """
    found = _first_existing(session_dir, ITERATIONS_DIRS)
    if found:
        return found
    numbered = os.path.join(session_dir, ITERATIONS_DIRS[0])
    if not is_numbered_layout(session_dir) and _first_existing(
        session_dir, C3D_DIRS[1:] + EXPERIMENTAL_DIRS[1:]
    ):
        return session_dir                      # established old-layout session
    if create:
        os.makedirs(numbered, exist_ok=True)
    return numbered


def iteration_path(session_dir: str, iteration: str) -> str:
    """Folder for one model iteration.

    Looks under ``3_iterations/`` first, then directly under the session, so a
    half-migrated session still resolves. Falls back to the layout's canonical
    location when neither exists yet (i.e. for a folder about to be created).

    The session-level fallback takes only a folder whose name matches EXACTLY
    and is not one of the shared folders. Windows compares names without case,
    so ``isdir(<session>/gpk)`` is True for a ``GPK/`` folder of generic-model
    files, and that folder became iteration ``gpk``: every iteration-relative
    path (model_scaled, markerset, ...) resolved one level too high, and new
    outputs would have gone into the model folder (found 2026-09-11, the
    TestIterationKeys fixture on Windows; Linux never saw it).
    """
    p = os.path.join(iterations_root(session_dir), iteration)
    if os.path.isdir(p):
        return p
    if iteration.lower() not in {n.lower() for n in NON_ITERATION_DIRS}:
        try:
            names = os.listdir(session_dir)
        except OSError:
            names = []
        if iteration in names and os.path.isdir(os.path.join(session_dir, iteration)):
            return os.path.join(session_dir, iteration)
    return p


# =========================================================================
# Trial / iteration path helpers and experimental-input utilities
# (moved here from session/session.py, 2026-09-10)
# =========================================================================
# =========================================================================
# LAYOUT  (inlined from utils/session_layout.py)
# =========================================================================
"""Session-centric layout runner (new YAML layout).

Drives a session from its ``session.yaml`` over the SHARED ``experimental/``
inputs and per-ITERATION output folders::

    <session>/c3dfiles/<trial>.c3d                 # raw captures
    <session>/experimental/<trial>/...             # processed inputs, model-independent, ONCE
    <session>/<iteration>/model.osim               # this iteration's scaled model (CEINMS/base)
    <session>/<iteration>/model_so.osim            # + isometric x factor (SO)
    <session>/<iteration>/<trial>/...              # IK/ID/MA/SO/CEINMS/JCF (model-dependent)
    <session>/<iteration>/ceinms_calibration/      # model-specific

The trick that avoids rewriting ``Analyse``: an Analyse resolves every path as
``os.path.join(self.path, <relative>)``. If we set its RAW-input attributes to
ABSOLUTE paths under ``experimental/<trial>/``, they resolve there, while every
DERIVED output stays under the iteration's trial folder (``self.path``). So one
Analyse per (iteration, trial) reads shared raw inputs and writes model-specific
results — no duplication.
"""

import os
import shutil
import time



def grf_events_cropped(session_path, trials=None):
    """For each trial with a ``time_range`` in session.yaml, write a
    ``experimental/<trial>/grf_events_cropped.png`` = per-foot vertical GRF
    limited to that window (full-trial trace greyed, window shaded/coloured).
    Returns the list of figures written."""
    import numpy as _np, pandas as _pd, xml.etree.ElementTree as _ET, re as _re
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as _plt
    from bioscout import utils as _u
    session_path = os.path.abspath(session_path)
    from .config import read_session_yaml as read_session
    spec = read_session(session_path)
    made = []
    for tn, meta in (spec.trials or {}).items():
        tr = (meta or {}).get("time_range")
        if not (isinstance(tr, (list, tuple)) and len(tr) == 2):
            continue
        tdir = experimental_dir(session_path, tn)
        gp = os.path.join(tdir, "grf.mot")
        if not os.path.exists(gp) or (trials and tn not in trials):
            continue
        try:
            grf = _u.load_any_data_file(gp)
            t = _pd.to_numeric(grf["time"], errors="coerce").to_numpy(float)
            foot = {}
            try:
                root = _ET.parse(os.path.join(tdir, "GRF.xml")).getroot()
                for ef in root.iter("ExternalForce"):
                    body = (ef.findtext("applied_to_body") or "").strip()
                    m = _re.search(r"(\d+)", (ef.findtext("force_identifier") or ""))
                    if m and body.startswith("calcn_"):
                        foot[int(m.group(1))] = body.split("_")[-1]
            except Exception:
                pass
            def _sum(side):
                cols = [f"ground_force_{p}_vy" for p, s in foot.items()
                        if s == side and f"ground_force_{p}_vy" in grf.columns]
                return (_np.sum([_pd.to_numeric(grf[c], errors="coerce").to_numpy(float)
                                 for c in cols], axis=0) if cols else _np.zeros_like(t))
            vyR, vyL = _sum("r"), _sum("l")
            t0, t1 = float(tr[0]), float(tr[1])
            fig, ax = _plt.subplots(figsize=(11, 5.2))
            ax.plot(t, vyR, color="0.75", lw=1.0); ax.plot(t, vyL, color="0.85", lw=1.0)
            _in = (t >= t0) & (t <= t1)
            ax.plot(t[_in], vyR[_in], color="tab:red", lw=2.0, label="Right foot Fy")
            ax.plot(t[_in], vyL[_in], color="tab:blue", lw=2.0, label="Left foot Fy")
            ax.axvspan(t0, t1, color="tab:green", alpha=0.10, label=f"analysis window [{t0:.2f}, {t1:.2f}] s")
            ax.axvline(t0, color="tab:green", ls="--", lw=1); ax.axvline(t1, color="tab:green", ls="--", lw=1)
            ax.set_xlim(max(t.min(), t0 - 0.15), min(t.max(), t1 + 0.15))
            ax.set_xlabel("Time (s)"); ax.set_ylabel("Vertical GRF Fy (N)")
            ax.set_title(f"{tn} — vertical GRF (analysis window {t0:.2f}-{t1:.2f} s)")
            ax.legend(fontsize=9)
            fig.tight_layout()
            out = os.path.join(tdir, "grf_events_cropped.png")
            fig.savefig(out, dpi=130); _plt.close(fig); made.append(out)
            print(f"  [ok] {tn} grf_events_cropped saved: {out}", flush=True)
        except Exception as e:
            print(f"  [grf_events_cropped] {tn}: warn — {e}", flush=True)
    return made


def _rm_empty_inputs(trial_path):
    """Remove an empty ``inputs/`` folder left in an iteration trial dir (raw
    inputs live in shared experimental/ now, so it should never hold anything)."""
    p = os.path.join(trial_path, "inputs")
    try:
        if os.path.isdir(p) and not os.listdir(p):
            os.rmdir(p)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# path resolver
# ---------------------------------------------------------------------------
# Folder names are resolved through `session_layout`, which understands both the
# numbered layout (1_c3dfiles / 2_experimental / 3_iterations/<name>) and the
# older flat one, preferring whatever exists on disk. Never join these names by
# hand — that is what keeps the two layouts from drifting apart.

# Which experimental subfolder the runners read raw inputs from. Normally the
# session's own (1_/2_-numbered or plain); a downsample run points this at e.g.
# "experimental_ds10", which is then used verbatim.
_EXP_SUBDIR = None

def experimental_dir(session_dir, trial):
    return os.path.join(experimental_root(session_dir, _EXP_SUBDIR), trial)

def c3d_path(session_dir, trial):
    return os.path.join(c3d_root(session_dir), f"{trial}.c3d")

def iteration_dir(session_dir, iteration):
    return iteration_path(session_dir, iteration)

def derived_trial_dir(session_dir, iteration, trial):
    return os.path.join(iteration_path(session_dir, iteration), trial)

# RAW input attribute -> filename in experimental/<trial>/. These are the
# model-INDEPENDENT files; everything else an Analyse writes is derived output.
_RAW_ATTR_FILES = {
    "markers": "marker_experimental.trc",
    "grf_mot": "grf.mot",
    "setup_grf": "GRF.xml",
    "emg": "emg.mot",
    "analog": "analog.csv",
    "emg_filtered": "emg_filtered.mot",
    "emg_filtered_normalised": "emg_filtered_normalised.mot",
    "ceinms_excitations": "emg_filtered_normalised.mot",
}

def bind_experimental(trial_obj, exp_dir):
    """Point an Analyse's raw-input attributes at ``exp_dir`` (absolute), so it
    reads shared experimental inputs but writes derived outputs under its own
    folder. Only sets attributes the object already has."""
    for attr, fname in _RAW_ATTR_FILES.items():
        if hasattr(trial_obj, attr):
            setattr(trial_obj, attr, os.path.join(exp_dir, fname))
    return trial_obj


def resolve_generic(name, project_dir, models_dir=None):
    """Resolve a `generic` value against the shared library, then models/, then root."""
    if not name:
        return None
    if os.path.isabs(name) and os.path.exists(name):
        return name
    bases = [os.path.join(project_dir, "generic models"),
             os.path.join(project_dir, "generic_models")]
    if models_dir:
        bases.append(str(models_dir))
    bases.append(project_dir)
    for b in bases:
        cand = os.path.join(b, name)
        if os.path.exists(cand):
            return cand
    return os.path.join(project_dir, "generic models", name)  # best guess


def resolve_session_model(name, session_dir, project_dir):
    """Resolve a `session_model` value (session-relative first, then generic lib)."""
    if not name:
        return None
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for b in (session_dir, os.path.join(project_dir, "generic models"), project_dir):
        cand = os.path.join(b, name)
        if os.path.exists(cand):
            return cand
    return os.path.join(session_dir, name)


def first_frames_range(exp_dir, frames):
    """Return ``[t0, t_{frames-1}]`` from a trial's time column (grf/marker/emg)
    for a quick GHOST run over just the first ``frames`` samples."""
    import pandas as _pd
    from bioscout import utils as _u
    for fn in ("grf.mot", "marker_experimental.trc", "emg_filtered_normalised.mot"):
        fp = os.path.join(exp_dir, fn)
        if not os.path.exists(fp):
            continue
        try:
            df = _u.load_any_data_file(fp)
            tcol = next((c for c in df.columns if c.lower() == "time"), None)
            if tcol is None:
                continue
            tv = _pd.to_numeric(df[tcol], errors="coerce").dropna().to_numpy()
            if len(tv) >= 2:
                k = max(1, min(int(frames), len(tv)) - 1)
                return [float(tv[0]), float(tv[k])]
        except Exception:
            continue
    return None


def full_time_range(exp_dir):
    """Return ``[t0, t_last]`` — the FULL trial window from its time column.
    Used to override any stale (e.g. ghost-run) window persisted in
    trial_settings.xml when running full length."""
    import pandas as _pd
    from bioscout import utils as _u
    for fn in ("grf.mot", "marker_experimental.trc", "emg_filtered_normalised.mot"):
        fp = os.path.join(exp_dir, fn)
        if not os.path.exists(fp):
            continue
        try:
            df = _u.load_any_data_file(fp)
            tcol = next((c for c in df.columns if c.lower() == "time"), None)
            if tcol is None:
                continue
            tv = _pd.to_numeric(df[tcol], errors="coerce").dropna().to_numpy()
            if len(tv) >= 2:
                return [float(tv[0]), float(tv[-1])]
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# downsample experimental inputs (quick-look speedup)
# ---------------------------------------------------------------------------
def _decimate_storage(src, dst, factor):
    """Decimate an OpenSim .mot/.sto: keep header, every ``factor``-th data row,
    update nRows. Time column is a data column so it is preserved intact."""
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    # find endheader
    hi = next((i for i, l in enumerate(lines) if l.strip().lower() == "endheader"), None)
    if hi is None:
        shutil.copyfile(src, dst); return
    header = lines[:hi + 1]
    col_line = lines[hi + 1]
    data = lines[hi + 2:]
    data = [l for l in data if l.strip() != ""]
    kept = data[::factor]
    # update nRows in header if present
    for i, l in enumerate(header):
        if l.lower().strip().startswith("nrows"):
            header[i] = f"nRows={len(kept)}\n"
    with open(dst, "w", encoding="utf-8") as f:
        f.writelines(header); f.write(col_line); f.writelines(kept)


def _decimate_trc(src, dst, factor):
    """Decimate a .trc marker file: keep every ``factor``-th frame, renumber
    Frame#, keep the real Time values, update NumFrames / DataRate headers."""
    with open(src, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    if len(lines) < 6:
        shutil.copyfile(src, dst); return
    l0, l1, l2 = lines[0], lines[1], lines[2]          # PathFileType / hdr names / hdr values
    col1, col2 = lines[3], lines[4]                    # Frame# Time markers / X Y Z sub-cols
    # data starts at line 5 (some files have a blank line 5) — collect non-empty rows
    body = [l for l in lines[5:] if l.strip() != ""]
    kept = body[::factor]
    # renumber Frame# (col 0), keep Time (col 1) and marker columns
    out = []
    for n, row in enumerate(kept, start=1):
        parts = row.rstrip("\n").split("\t")
        if parts:
            parts[0] = str(n)
        out.append("\t".join(parts) + "\n")
    # update header value row: DataRate CameraRate NumFrames NumMarkers Units OrigDataRate ...
    hv = l2.rstrip("\n").split("\t")
    try:
        for idx in (0, 1):                              # DataRate, CameraRate -> /factor
            hv[idx] = f"{float(hv[idx]) / factor:g}"
        hv[2] = str(len(out))                           # NumFrames
    except Exception:
        pass
    l2 = "\t".join(hv) + "\n"
    with open(dst, "w", encoding="utf-8") as f:
        f.writelines([l0, l1, l2, col1, col2, "\n"]); f.writelines(out)




# ---------------------------------------------------------------------------
# scaling: build one iteration's model.osim / model_so.osim from its recipe
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# run one iteration over all trials (SO stage), reading shared experimental/
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# import already-scaled models from the OLD models/<subject>/<session>/ layout
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# CEINMS for one iteration over all trials (new layout)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# top-level driver
# ---------------------------------------------------------------------------
