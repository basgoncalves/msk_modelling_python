"""Muscle vs ID moments in the context of the task: poses, GRF and joint angles.

``static_optimisation/muscle_moments_<side>.png`` -- one figure per leg, in the
vertical task layout of :mod:`bioscout.plot.task_figure` (poses and vGRF on
top), then one row per reserved coordinate of that leg:

    ID moment (black), muscles = ID - reserve (blue dashed), reserve (purple),
    in N·m, left axis; joint angle (grey dotted, right axis)
    title: RMSE(muscles, ID) and peak |reserve|, both in % of the ID moment's
    RANGE (the numbers in muscle_moments.csv); green < 5 %, orange < 10 %, red

Trial data only: the point is to see WHEN in the task each reserve works.

    python -m bioscout.plot.muscle_moments_task <trial folder> [--sides r l]

Called after SO by ``Analyse.plot_muscle_moments`` (via
``bioscout.simulate.so_files.plot_muscle_moments``).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bioscout.plot.task_figure import TaskStrip, read_sto

ORDER = ("hip_flexion", "hip_adduction", "hip_rotation", "knee_angle",
         "knee_adduction", "ankle_angle", "subtalar_angle", "mtp_angle")
FIG = "muscle_moments_{side}.png"


def _rmse_color(p):
    return "tab:green" if p < 5 else "darkorange" if p < 10 else "tab:red"


def muscle_moments(trial, sides=None, out_dir=None, log=print, strip=None):
    """Draw muscle_moments_<side>.png for ``trial`` (a 3_iterations/<it>/<trial>
    folder). Returns the list of figure paths."""
    import matplotlib.pyplot as plt
    from bioscout.simulate import so_files as sof

    trial = Path(trial).resolve()
    if trial.name == "static_optimisation":
        trial = trial.parent
    so_dir = trial / "static_optimisation"
    out_dir = Path(out_dir or so_dir)
    so, _ = read_sto(sof.pick(so_dir / sof.FORCE))
    idm, _ = read_sto(trial / "external_biomechanics" / "inverse_dynamics.sto")
    ik, deg = read_sto(trial / "external_biomechanics" / "joint_angles.mot")
    ts = so["time"].to_numpy(float)
    ti = idm["time"].to_numpy(float)
    tik = ik["time"].to_numpy(float)
    strip = strip or TaskStrip(trial, t_range=(float(ts[0]), float(ts[-1])), log=log)

    res_cols = [c for c in so.columns if c.endswith("_reserve")]
    sides = sides or sorted({c[:-len("_reserve")][-1] for c in res_cols
                             if c[:-len("_reserve")][-2:] in ("_r", "_l")})
    made = []
    for sd in sides:
        dofs = [d for d in ORDER if f"{d}_{sd}_reserve" in so.columns
                and f"{d}_{sd}_moment" in idm.columns]
        if not dofs:
            continue
        rows = []
        for d in dofs:
            mom = np.interp(ts, ti, idm[f"{d}_{sd}_moment"].to_numpy(float))
            res = so[f"{d}_{sd}_reserve"].to_numpy(float)
            rng = float(np.ptp(mom)) or np.nan
            rmse_pct = 100 * float(np.sqrt(np.mean(res ** 2))) / rng
            peak_pct = 100 * float(np.max(np.abs(res))) / rng
            col = f"{d}_{sd}"
            ang = (np.interp(ts, tik, ik[col].to_numpy(float)) if col in ik.columns
                   else None)
            if ang is not None and not deg:
                ang = np.degrees(ang)

            def draw(a, mom=mom, res=res, ang=ang):
                a.plot(ts, mom, color="k", lw=1.7, zorder=3)
                a.plot(ts, mom - res, color="tab:blue", lw=1.1, ls="--", zorder=4)
                a.plot(ts, res, color="tab:purple", lw=1.2, zorder=5)
                a.axhline(0, color="0.7", lw=0.5)
                if ang is not None:
                    a2 = a.twinx()
                    a2.plot(ts, ang, color="0.55", lw=1.0, ls=":")
                    a2.set_ylabel("angle (°)", fontsize=7, color="0.45")
                    a2.tick_params(labelsize=6, colors="0.45")

            rows.append(dict(draw=draw, ylabel="N·m", title_color=_rmse_color(rmse_pct),
                             title=f"{col}   RMSE {rmse_pct:.1f} % · peak "
                                   f"{peak_pct:.0f} % of ID range"))
        h = [plt.Line2D([], [], color="k", lw=1.7, label="ID moment"),
             plt.Line2D([], [], color="tab:blue", lw=1.1, ls="--",
                        label="muscles (ID - reserve)"),
             plt.Line2D([], [], color="tab:purple", lw=1.2, label="reserve"),
             plt.Line2D([], [], color="0.55", lw=1.0, ls=":",
                        label="joint angle (right axis)")]
        out = strip.figure(rows, out_dir / FIG.format(side=sd), legend=h)
        made.append(out)
        if log:
            log(f"Saved muscle moments figure: {out}")
    return made


#: back-compat name (the figure used to be muscle_moments_task_<side>.png)
muscle_moments_task = muscle_moments


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trial", help="3_iterations/<iteration>/<trial> folder "
                                  "(or its static_optimisation subfolder)")
    ap.add_argument("--sides", nargs="+", choices=("r", "l"))
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    muscle_moments(a.trial, sides=a.sides)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
