"""Static-optimisation output names, in ONE place.

The SO folder (``<trial>/static_optimisation/``) already says what its files
are, so they carry no ``SO_`` prefix (changed 2026-10-01):

    StaticOptimization_force.sto        was SO_StaticOptimization_force.sto
    StaticOptimization_activation.sto   was SO_StaticOptimization_activation.sto
    StaticOptimization_controls.xml     was SO_StaticOptimization_controls.xml
    muscle_individual.png               was SO_results.png
    muscle_groups.png                   was SO_muscle_groups.png
    muscle_moments_<side>.png / muscle_moments.csv
                                        replace SO_reserves_inspection.png / .csv
                                        (task layout, bioscout.plot.muscle_moments_task;
                                        the grid muscle_moments.png and
                                        muscle_moments_task_<side>.png are gone)

OpenSim's AnalyzeTool still writes ``<toolname>_StaticOptimization_*``; the SO
stage renames them straight after the run (:func:`migrate_dir`). Folders from
before the change are renamed the first time a trial is opened, and every reader
goes through :func:`pick`, which falls back to the legacy name, so old sessions
keep working without a migration step. :func:`migrate` renames a whole tree.

Light on purpose: numpy/pandas/matplotlib only, no OpenSim.
"""
from __future__ import annotations

import os

FORCE = "StaticOptimization_force.sto"
ACTIVATION = "StaticOptimization_activation.sto"
CONTROLS = "StaticOptimization_controls.xml"
FIG_INDIVIDUAL = "muscle_individual.png"
FIG_GROUPS = "muscle_groups.png"
FIG_MOMENTS = "muscle_moments_{side}.png"     # one per leg
CSV_MOMENTS = "muscle_moments.csv"

#: legacy name -> current name
LEGACY = {
    "SO_StaticOptimization_force.sto": FORCE,
    "SO_StaticOptimization_activation.sto": ACTIVATION,
    "SO_StaticOptimization_controls.xml": CONTROLS,
    "SO_results.png": FIG_INDIVIDUAL,
    "SO_muscle_groups.png": FIG_GROUPS,
}
#: superseded outputs with no current equivalent (removed by migrate(..., remove_obsolete=True))
OBSOLETE = ("SO_reserves_inspection.png", "SO_reserves_inspection.csv",
            "muscle_moments.png", "muscle_moments_task_r.png", "muscle_moments_task_l.png")
_CURRENT_TO_LEGACY = {v: k for k, v in LEGACY.items()}


def pick(path):
    """``path`` if it exists, else its legacy/current twin if THAT exists, else ``path``.

    Use for every READ of an SO output, so sessions written before the rename
    still resolve. Writers use the current names.
    """
    path = os.fspath(path)
    if os.path.exists(path):
        return path
    d, b = os.path.split(path)
    alt = _CURRENT_TO_LEGACY.get(b) or LEGACY.get(b)
    if alt and os.path.exists(os.path.join(d, alt)):
        return os.path.join(d, alt)
    return path


def migrate_dir(so_dir, remove_obsolete=False, dry=False):
    """Rename legacy outputs in ONE static_optimisation folder to the current names.

    A legacy file replaces a current one only if it is newer (OpenSim has just
    written it); an older legacy file next to a current one is stale and is
    removed. Returns [(old, new), ...].
    """
    done = []
    if not os.path.isdir(so_dir):
        return done
    for old, new in LEGACY.items():
        po, pn = os.path.join(so_dir, old), os.path.join(so_dir, new)
        if not os.path.exists(po):
            continue
        if os.path.exists(pn) and os.path.getmtime(pn) > os.path.getmtime(po):
            if not dry:
                try:
                    os.remove(po)               # stale legacy copy
                except OSError:
                    pass
            continue
        if not dry:
            os.replace(po, pn)
        done.append((po, pn))
    if remove_obsolete:
        for old in OBSOLETE:
            po = os.path.join(so_dir, old)
            if os.path.exists(po):
                if not dry:
                    try:
                        os.remove(po)
                    except OSError:
                        pass
                done.append((po, None))
    return done


def migrate(root, remove_obsolete=False, dry=False, log=print):
    """migrate_dir() on every ``static_optimisation`` folder under ``root``."""
    n = 0
    for dirpath, dirnames, _ in os.walk(root):
        if os.path.basename(dirpath) == "static_optimisation":
            n += len(migrate_dir(dirpath, remove_obsolete, dry))
            dirnames[:] = []
    if log:
        log(f"[so_files] {'would rename/remove' if dry else 'renamed/removed'} {n} file(s) under {root}")
    return n


# ---------------------------------------------------------------------- figure
def _read(path):
    """OpenSim .sto/.mot -> DataFrame (header up to ``endheader`` skipped)."""
    import pandas as pd
    with open(path) as f:
        lines = f.read().splitlines()
    h = next(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    return pd.read_csv(path, sep=r"\s+", skiprows=h + 1)


def moment_table(so_forces, id_file, t_range=None, order=None):
    """Per reserved coordinate: ID range, peak reserve, RMSE(muscles, ID) -- the
    last two also in % of the ID moment's RANGE over the window (never of its
    instantaneous value, which blows up at every zero crossing; the old
    SO_reserves_inspection read a 0.5 N·m reserve as 476 %). SO enforces
    ID = muscles + reserve at every frame, so RMSE(muscles, ID) = RMS(reserve).
    Same numbers as bioscout.plot.summary's ``moment_RMSE_pct``."""
    import numpy as np
    import pandas as pd
    so, idm = _read(pick(so_forces)), _read(os.fspath(id_file))
    reserves = [c for c in so.columns if str(c).endswith("_reserve")]
    if order:
        reserves.sort(key=lambda c: (order.index(c[:-8]) if c[:-8] in order else len(order), c))
    ts = so["time"].to_numpy(float)
    ti = idm["time"].to_numpy(float)
    m = np.ones_like(ts, bool) if not t_range else (ts >= t_range[0]) & (ts <= t_range[1])
    rows = []
    for rc in reserves:
        base = rc[:-len("_reserve")]
        mcol = base + "_moment"
        if mcol not in idm.columns:
            continue
        res = pd.to_numeric(so[rc], errors="coerce").to_numpy(float)[m]
        mom = np.interp(ts[m], ti, pd.to_numeric(idm[mcol], errors="coerce").to_numpy(float))
        ok = np.isfinite(mom) & np.isfinite(res)
        if not ok.any():
            continue
        rng = float(np.ptp(mom[ok]))
        rmse = float(np.sqrt(np.mean(res[ok] ** 2)))
        pk = float(np.max(np.abs(res[ok])))
        rows.append(dict(coordinate=base, id_range_Nm=round(rng, 2),
                         reserve_peak_Nm=round(pk, 2), rmse_Nm=round(rmse, 2),
                         rmse_pct_range=round(100 * rmse / rng, 1) if rng else np.nan,
                         peak_pct_range=round(100 * pk / rng, 1) if rng else np.nan))
    return rows


def plot_muscle_moments(so_forces, id_file, out_dir=None, t_range=None,
                        order=None, log=print):
    """ID moment vs the moment the muscles carry, per reserved coordinate.

    Writes ``muscle_moments.csv`` (:func:`moment_table`) and, per leg,
    ``muscle_moments_<side>.png`` in the vertical task layout (poses + vGRF on
    top, one row per coordinate; bioscout.plot.muscle_moments_task) to
    ``out_dir`` (default: the force file's folder). Returns (fig_paths, rows).
    """
    import pandas as pd
    so_forces = pick(so_forces)
    out_dir = out_dir or os.path.dirname(so_forces)
    rows = moment_table(so_forces, id_file, t_range=t_range, order=order)
    if not rows:
        if log:
            log("[muscle_moments] no reserve columns with an ID moment")
        return [], []
    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, CSV_MOMENTS), index=False)
    for old in ("muscle_moments.png", "muscle_moments_task_r.png", "muscle_moments_task_l.png"):
        try:
            os.remove(os.path.join(out_dir, old))
        except OSError:
            pass
    figs = []
    try:
        from bioscout.plot.muscle_moments_task import muscle_moments
        trial = os.path.dirname(os.path.dirname(os.path.abspath(so_forces)))
        figs = muscle_moments(trial, out_dir=out_dir, log=log)
    except Exception as e:                               # noqa: BLE001
        if log:
            log(f"[Warning] muscle_moments figure failed: {type(e).__name__}: {e}")
    return figs, rows


def tidy(root, plots=True, log=print):
    """migrate() a tree (removing obsolete outputs), then (re)draw muscle_moments_<side>.png
    (+ .csv) in every static_optimisation folder that has a force file and an ID next door."""
    migrate(root, remove_obsolete=True, log=log)
    n = 0
    if plots:
        import matplotlib
        matplotlib.use("Agg")
        for dp, dn, _ in os.walk(root):
            if os.path.basename(dp) != "static_optimisation":
                continue
            dn[:] = []
            so = os.path.join(dp, FORCE)
            idf = os.path.join(os.path.dirname(dp), "external_biomechanics",
                               "inverse_dynamics.sto")
            if os.path.exists(so) and os.path.exists(idf):
                try:
                    figs, _ = plot_muscle_moments(so, idf, log=None)
                    n += bool(figs)
                except Exception as e:                     # noqa: BLE001
                    if log:
                        log(f"[so_files] {dp}: {type(e).__name__}: {e}")
        if log:
            log(f"[so_files] muscle_moments_<side>.png written in {n} folder(s)")
    return n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Rename SO outputs to the un-prefixed names, "
                                 "remove obsolete figures, draw muscle_moments_<side>.png")
    ap.add_argument("roots", nargs="+", help="folders to walk (e.g. simulations/)")
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="rename nothing, only count")
    a = ap.parse_args()
    for r in a.roots:
        if a.dry_run:
            migrate(r, remove_obsolete=True, dry=True)
        else:
            tidy(r, plots=not a.no_plots)
