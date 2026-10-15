"""Joint-reaction (contact-force) output names, in ONE place.

The folder (``<trial>/joint_contact_forces/``) already says what its files are,
so they are named by the ORIGIN of the muscle forces only (changed 2026-10-01):

    output_so.sto                       was Analyse_JRA_ReactionLoads_SO.sto
    output_ceinms.sto                   was Analyse_JRA_ReactionLoads_CEINMS.sto
    output_ml.sto                       was Analyse_JRA_ReactionLoads_ML.sto
    jrf_so.png                          was JRA_SO.png (now the vertical task layout)
    jrf_so_vs_ceinms.png                was JRA_SO_vs_CEINMS.png
    jrf_<origin>_coverage_<plane>.png   was JRA_<ORIGIN>_coverage_<plane>.png

Every reader goes through :func:`pick`, which falls back to the legacy name, so
old sessions keep working; :func:`migrate_dir` / :func:`migrate` rename them.
Light on purpose: no OpenSim, no matplotlib.
"""
from __future__ import annotations

import os
import re

DIR = "joint_contact_forces"


def output(origin):
    """``output_<origin>.sto`` (origin: SO, CEINMS, ML, ...)."""
    return f"output_{str(origin).lower()}.sto"


def figure(*origins):
    """``jrf_so.png``, ``jrf_so_vs_ceinms.png``, ..."""
    return "jrf_" + "_vs_".join(str(o).lower() for o in origins) + ".png"


def coverage(origin, plane):
    return f"jrf_{str(origin).lower()}_coverage_{plane}.png"


_LEGACY_RE = (
    (re.compile(r"^Analyse_JRA_ReactionLoads_([A-Za-z0-9]+)\.sto$"),
     lambda m: output(m.group(1))),
    (re.compile(r"^JRA_([A-Za-z0-9]+)_coverage_([a-z]+)\.png$"),
     lambda m: coverage(m.group(1), m.group(2))),
    (re.compile(r"^JRA_([A-Za-z0-9]+)_vs_([A-Za-z0-9]+)\.png$"),
     lambda m: figure(m.group(1), m.group(2))),
    (re.compile(r"^JRA_([A-Za-z0-9]+)\.png$"),
     lambda m: figure(m.group(1))),
)


def current_name(legacy):
    """Current name for a legacy file name, or None."""
    for rx, fn in _LEGACY_RE:
        m = rx.match(legacy)
        if m:
            return fn(m)
    return None


def legacy_name(current):
    """Legacy name for a current OUTPUT name (``output_so.sto`` ->
    ``Analyse_JRA_ReactionLoads_SO.sto``), or None."""
    m = re.match(r"^output_([a-z0-9]+)\.sto$", current)
    return f"Analyse_JRA_ReactionLoads_{m.group(1).upper()}.sto" if m else None


def pick(path):
    """``path`` if it exists, else its legacy/current twin if THAT exists, else
    ``path``. Use for every READ of a JRA output."""
    path = os.fspath(path)
    if os.path.exists(path):
        return path
    d, b = os.path.split(path)
    alt = legacy_name(b) or current_name(b)
    if alt and os.path.exists(os.path.join(d, alt)):
        return os.path.join(d, alt)
    return path


def migrate_dir(jcf_dir, dry=False):
    """Rename legacy outputs in ONE joint_contact_forces folder. A legacy file
    replaces a current one only if it is newer; an older legacy copy is stale and
    removed. Returns [(old, new), ...]."""
    done = []
    if not os.path.isdir(jcf_dir):
        return done
    for b in sorted(os.listdir(jcf_dir)):
        new = current_name(b)
        if not new:
            continue
        po, pn = os.path.join(jcf_dir, b), os.path.join(jcf_dir, new)
        if os.path.exists(pn) and os.path.getmtime(pn) > os.path.getmtime(po):
            if not dry:
                try:
                    os.remove(po)
                except OSError:
                    pass
            done.append((po, None))
            continue
        if not dry:
            os.replace(po, pn)
        done.append((po, pn))
    return done


def migrate(root, dry=False, log=print):
    """migrate_dir() on every ``joint_contact_forces`` folder under ``root``."""
    n = 0
    for dirpath, dirnames, _ in os.walk(root):
        if os.path.basename(dirpath) == DIR:
            n += len(migrate_dir(dirpath, dry))
            dirnames[:] = []
    if log:
        log(f"[jra_files] {'would rename' if dry else 'renamed'} {n} file(s) under {root}")
    return n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Rename JRA outputs to output_<origin>.sto / "
                                 "jrf_*.png under the given folders")
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for r in a.roots:
        migrate(r, dry=a.dry_run)
