"""Put the captures a session needs into ``1_c3dfiles/``.

    from bioscout.session import stage
    stage.stage_c3d(session_dir)                     # report, copy nothing
    stage.stage_c3d(session_dir, apply=True)

    bioscout session stage PATH --apply

bioscout resolves a capture from ``<session>/1_c3dfiles/<trial>.c3d`` and
NOWHERE else: ``c3d_source:`` in session.yaml is the pointer for this copy,
not a read path, so a session that was never staged solves nothing and says
so. ``session ingest`` files a folder of loose captures into a session;
this is the other direction -- session.yaml already names the trials, and
these are the files it names, wherever they sit under ``c3d_source``.

What is needed is more than the trials being solved: the STATIC trial (there
is no .trc to scale from without it), the CEINMS calibration trials, and every
EMG-normalisation capture -- the session-wide MVC maximum spans all of them,
so leaving one out changes every excitation in the session.

Hard links, not copies, where the filesystem allows: same disk, instant, and
the capture is never edited in place.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

__all__ = ["source_index", "needed_trials", "stage_c3d"]

#: Folders under the source that are never a source of trials.
SKIP_DIRS = {"badtrials", "badtirals", "badtrialsc3d", "allvicon", "exported",
             "_to_delete"}


def source_index(source, skip_dirs=SKIP_DIRS):
    """``{trial name: path}`` for every .c3d under ``source``. A name already
    taken by a shallower file is suffixed ``_NU`` (the convention for the same
    capture re-exported into a "not used" folder), so the deeper copy is still
    reachable instead of silently shadowed."""
    root = Path(source)
    out, seen = {}, set()
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*.c3d"), key=lambda p: (len(p.relative_to(root).parts), str(p))):
        if any(part.lower() in skip_dirs for part in p.relative_to(root).parts[:-1]):
            continue
        name, n = p.stem, 1
        while name in seen:
            name = f"{p.stem}_NU{'' if n == 1 else n}"
            n += 1
        seen.add(name)
        out[name] = p
    return out


def needed_trials(cfg, trials=None):
    """Every trial a session must have staged: the scope, the static trial,
    the calibration trials and every EMG-normalisation capture."""
    tcfg = cfg.get("trials") or {}
    need = set(trials or tcfg)
    if cfg.get("static_trial"):
        need.add(cfg["static_trial"])
    need |= {t for t, m in tcfg.items() if isinstance(m, dict) and m.get("calibration")}
    need |= {t for t, m in tcfg.items() if isinstance(m, dict) and m.get("emg_normalisation")}
    need |= set(cfg.get("calibration_trials") or [])
    need |= set(cfg.get("normalisation_trials") or [])
    return sorted(need & set(tcfg)) if tcfg else sorted(need)


def stage_c3d(session_dir, *, trials=None, source=None, apply=False, log=print):
    """Link/copy the captures this session names into ``1_c3dfiles/``.

    ``source`` defaults to session.yaml's ``c3d_source`` (relative to the
    session folder). Returns ``{"staged", "present", "missing"}``; a trial with
    no capture anywhere under the source is named rather than skipped quietly,
    and a missing STATIC trial raises -- nothing in the session can be scaled
    without it.
    """
    import yaml
    session_dir = Path(session_dir)
    ypath = session_dir / "session.yaml"
    if not ypath.is_file():
        raise FileNotFoundError(f"no session.yaml in {session_dir}")
    cfg = yaml.safe_load(ypath.read_text(encoding="utf-8", errors="ignore")) or {}
    src = source or cfg.get("c3d_source")
    if not src:
        raise ValueError(f"{ypath}: no `c3d_source:` and no source= given -- "
                         f"nothing to stage from")
    src = Path(os.path.normpath(session_dir / src)) if not os.path.isabs(str(src)) else Path(src)
    if not src.is_dir():
        raise FileNotFoundError(f"c3d_source {src} does not exist")

    index = source_index(src)
    dst_root = session_dir / "1_c3dfiles"
    if apply:
        dst_root.mkdir(parents=True, exist_ok=True)
    staged, present, missing = [], [], []
    for t in needed_trials(cfg, trials):
        dst = dst_root / f"{t}.c3d"
        if dst.is_file():
            present.append(t)
            continue
        s = index.get(t)
        if s is None:
            missing.append(t)
            continue
        if apply:
            try:
                os.link(s, dst)
            except OSError:
                shutil.copy2(s, dst)
        staged.append(t)
    log(f"[stage] {len(staged)} {'staged' if apply else 'to stage'}, "
        f"{len(present)} already there"
        + (f", MISSING {len(missing)}: {', '.join(missing[:6])}"
           f"{' ...' if len(missing) > 6 else ''}" if missing else "")
        + ("" if apply else "  (pass apply=True to copy)"))
    static = cfg.get("static_trial")
    if static and static in missing:
        raise FileNotFoundError(
            f"{session_dir.name}: the static trial {static!r} has no capture under "
            f"{src} -- nothing in this session can be scaled without it")
    return {"staged": staged, "present": present, "missing": missing, "source": str(src)}
