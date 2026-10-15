"""Vertical trial figures with the TASK on top.

Every per-trial figure with a handful of time-series panels uses the same
layout, so they can be read against each other:

    row 0   the posed skeleton (both legs) at the foot-strike / foot-off events,
            each pose centred (on the pelvis) above its event line, with the GRF
            of each loaded plate drawn as an arrow from its COP
    row 1   vertical GRF of both feet, stance shaded, events dashed and named
    rows    the figure's own panels, one per row, sharing the time axis, with
            the same event lines

    from bioscout.plot.task_figure import TaskStrip
    ts = TaskStrip(trial_folder)                      # 3_iterations/<it>/<trial>
    ts.figure([dict(draw=lambda ax: ax.plot(...), title="..."), ...],
              out="...png", legend=[Line2D handles])

Without a model (session.yaml -> iteration ``model_scaled``) or its Geometry
the pose row is left out; without ``2_experimental/<trial>/grf.mot`` the GRF
row is left out. The panels are always drawn. Used by kinematics_moments,
residuals, _ik_marker_errors_plot, muscle_moments_<side>, muscle_groups and
jrf_<origin> and emg_processing (bioscout.plot.emg_figure); figures with many
panels (inverse_dynamics, muscle_individual) keep their grids.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SIDE_COLOR = {"r": "#c0392b", "l": "#2a78d6"}
EVENT_KW = dict(color="#555", lw=0.7, ls="--", zorder=1)


# ----------------------------------------------------------------- readers
def read_sto(path):
    """(DataFrame, in_degrees) of an OpenSim .sto/.mot."""
    import pandas as pd
    with open(path) as f:
        lines = f.read().splitlines()
    h = next(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    deg = any("indegrees=yes" in l.replace(" ", "").lower() for l in lines[:h])
    return pd.read_csv(path, sep=r"\s+", skiprows=h + 1), deg


def model_for(trial: Path):
    """The iteration's scaled model, from session.yaml (bioscout >= 3.0 layout)."""
    import yaml
    trial = Path(trial)
    sess = trial.parents[2]
    try:
        cfg = yaml.safe_load((sess / "session.yaml").read_text()) or {}
    except Exception:                                    # noqa: BLE001
        return None
    it = (cfg.get("iterations") or {}).get(trial.parent.name) or {}
    rel = it.get("model_scaled") or it.get("so_model")
    if not rel:
        return None
    rel = (str(rel).replace("<subject>", str(cfg.get("subject", sess.parent.name)))
           .replace("<session>", str(cfg.get("session", sess.name))))
    project = sess.parents[2]
    for base in (project / (cfg.get("models_dir") or "models"), project,
                 project / "models" / "personalised" / sess.parent.name / sess.name):
        p = (base / rel).resolve()
        if p.is_file():
            return p
    return None


def events_from_grf(tg, vy_by_side, t0, t1, thr=20.0):
    """[(name, time)] foot strike / foot off of each foot inside [t0, t1]."""
    ev = []
    for sd, vy in vy_by_side.items():
        m = (tg >= t0) & (tg <= t1)
        on = (vy > thr) & m
        d = np.diff(on.astype(int))
        for i in np.flatnonzero(d == 1):
            ev.append((f"{sd.upper()} foot strike", float(tg[i + 1])))
        for i in np.flatnonzero(d == -1):
            ev.append((f"{sd.upper()} foot off", float(tg[i])))
    return sorted(ev, key=lambda e: e[1])


def grf_vectors(trial: Path):
    """(time, [(side, F (n,3) N, COP (n,3) m), ...]) from grf.mot, ground frame."""
    trial = Path(trial)
    exp = trial.parents[2] / "2_experimental" / trial.name
    mot, xml = exp / "grf.mot", exp / "GRF.xml"
    if not mot.is_file():
        return None
    df, _ = read_sto(mot)
    sides = {}
    if xml.is_file():
        try:
            from bioscout.session.movement_detector.mocap import _plate_sides
            sides = _plate_sides(str(xml))
        except Exception:                                # noqa: BLE001
            sides = {}
    out = []
    for c in df.columns:
        if not c.endswith("_vx"):
            continue
        base = c[:-1]                                    # ground_force_1_v
        cols_f = [base + a for a in "xyz"]
        cols_p = [base[:-1] + "p" + a for a in "xyz"]
        if all(k in df.columns for k in cols_f + cols_p):
            out.append((sides.get(base, "?"), df[cols_f].to_numpy(float),
                        df[cols_p].to_numpy(float)))
    return df["time"].to_numpy(float), out


def _trial_window(trial: Path):
    for rel in ("external_biomechanics/inverse_dynamics.sto",
                "external_biomechanics/joint_angles.mot"):
        p = trial / rel
        if p.is_file():
            df, _ = read_sto(p)
            t = df["time"].to_numpy(float)
            return float(t[0]), float(t[-1])
    return None


# ------------------------------------------------------------------- poses
def _pose_axis(fig, rect, geo, q, R_ground, R_yaw, jc, grf_vec=None, pelvis_g=None,
               n_per_mm=0.6, anchor_x=None):
    """One pose: both legs, plus each loaded plate's GRF as an arrow from its
    COP. The view is centred on ``anchor_x`` (plot-x, mm from the pelvis) --
    the event foot's COP, so THAT foot sits on its event line (2026-10-15) --
    else on the pelvis."""
    axp = fig.add_axes(rect, projection="3d")
    axp.patch.set_visible(False)
    for kk, s2 in enumerate(("r", "l")):
        try:
            jc._draw_skeleton(axp, geo, q, s2, keep_axes=(kk > 0),
                              color=SIDE_COLOR[s2], R_ground=R_ground)
        except Exception:                                # noqa: BLE001
            pass
    pts = [p for p in jc._drawn]
    if grf_vec is not None and pelvis_g is not None:
        for sd, F, P in grf_vec:
            if np.linalg.norm(F) < 20.0:                 # unloaded plate
                continue
            c = (R_yaw @ (P - pelvis_g)) * 1000.0        # mm, pelvis at the origin
            v = (R_yaw @ F) * n_per_mm
            c, v = c[jc._TO_PLOT], v[jc._TO_PLOT]
            axp.quiver(*c, *v, color="0.15", lw=2.6, arrow_length_ratio=0.18, zorder=10)
            axp.quiver(*c, *v, color=SIDE_COLOR.get(sd, "k"), lw=1.4,
                       arrow_length_ratio=0.18, zorder=11)
            pts.append(np.vstack([c, c + v]))
    if pts:
        P_ = np.vstack(pts)
        lo, hi = P_.min(axis=0) - 2, P_.max(axis=0) + 2
        ax0 = float(anchor_x) if anchor_x is not None else 0.0
        hx = max(abs(lo[0] - ax0), abs(hi[0] - ax0))
        lo[0], hi[0] = ax0 - hx, ax0 + hx
        axp.set_xlim(lo[0], hi[0]); axp.set_ylim(lo[1], hi[1]); axp.set_zlim(lo[2], hi[2])
        axp.set_box_aspect(tuple(hi - lo))
    axp.view_init(elev=0, azim=-90)
    axp.set_proj_type("ortho")
    jc._bare(axp)
    return axp


# ------------------------------------------------------------------- strip
class TaskStrip:
    """The task context of one trial (window, GRF, events, poses), drawn on top
    of any stack of time-series panels by :meth:`figure`."""

    def __init__(self, trial, t_range=None, poses=True, n_min_poses=3, log=print):
        self.trial = Path(trial).resolve()
        if self.trial.name in ("static_optimisation", "external_biomechanics",
                               "joint_contact_forces", "muscle_analysis"):
            self.trial = self.trial.parent
        self.log = log
        self.t_range = tuple(t_range) if t_range else _trial_window(self.trial)
        t0, t1 = self.t_range or (0.0, 1.0)

        self.grf = None
        try:
            from bioscout.plot.jcf_coverage import grf_for
            self.grf = grf_for({"trial": self.trial})
        except Exception as e:                           # noqa: BLE001
            self._say(f"no GRF: {type(e).__name__}: {e}")
        self.events = (events_from_grf(self.grf[0], self.grf[1], t0, t1)
                       if self.grf else [])
        self.pose_t = ([x for _, x in self.events]
                       or list(np.linspace(t0, t1, n_min_poses + 2)[1:-1]))

        self.geo = self.q_at = self.R_yaw = None
        if poses:
            self._load_poses(t0, t1)

    def _say(self, msg):
        if self.log:
            self.log(f"[task_figure] {msg}")

    def _load_poses(self, t0, t1):
        ja = self.trial / "external_biomechanics" / "joint_angles.mot"
        model = model_for(self.trial)
        if model is None or not ja.is_file():
            self._say("no model in session.yaml or no IK -- no poses")
            return
        try:
            from bioscout.plot import jcf_coverage as jc
            from bioscout.plot.jcf_direction import OsimModel, read_sto as _rs
            sess = self.trial.parents[2]
            _, deg = read_sto(ja)
            self.geo = OsimModel(str(model), jc._geometry_dirs(self.trial.parent,
                                                               sess.parents[2]))
            ikn, ikd = _rs(str(ja))
            self.q_at = jc._q_maker(ikn, ikd, deg, str(model))
            self.R_yaw = jc._lab_yaw(self.geo, self.q_at, np.linspace(t0, t1, 25))
        except Exception as e:                           # noqa: BLE001
            self.geo = None
            self._say(f"no poses ({type(e).__name__}: {e})")

    # .............................................................. figure
    def figure(self, rows, out, legend=None, width=10.5, row_height=1.45,
               xlabel="time (s)", grf_row=True, dpi=150, legend_ncol=None,
               legend_loc="bottom"):
        """Draw ``rows`` under the pose strip and the vGRF row and save ``out``.

        rows    list of dicts: ``draw`` (callable(ax) -> None), optional
                ``title`` (left-aligned), ``title_color``, ``height`` (relative,
                default 1) and ``ylabel``. A row's draw() may add a twin axis.
        legend  list of matplotlib handles for a shared legend at the bottom,
                or -- ``legend_loc="top"`` -- right-aligned just above the first
                data row (under the vGRF row), without the GRF-at-COP entry.
        """
        import matplotlib.pyplot as plt
        t0, t1 = self.t_range or (None, None)
        has_pose = self.geo is not None
        has_grf = bool(self.grf) and grf_row
        hr = ([2.0] if has_pose else []) + ([1.0] if has_grf else []) \
            + [float(r.get("height", 1.0)) * row_height for r in rows]
        H = sum(hr) * 1.05 + 1.0                         # inches
        fig = plt.figure(figsize=(width, H), dpi=dpi)
        gs = fig.add_gridspec(len(hr), 1, height_ratios=hr, hspace=0.45,
                              top=1 - (0.08 if has_pose else 0.4) / H, bottom=0.85 / H,
                              left=0.09, right=0.88)
        k = 1 if has_pose else 0
        axes = []
        axg = None
        if has_grf:
            axg = fig.add_subplot(gs[k]); k += 1
            tg = self.grf[0]
            m = (tg >= t0) & (tg <= t1) if t0 is not None else np.ones_like(tg, bool)
            for s2, vy in self.grf[1].items():
                c = SIDE_COLOR.get(s2, "k")
                axg.plot(tg[m], vy[m], color=c, lw=1.5,
                         label=f"{'right' if s2 == 'r' else 'left'} foot")
                axg.fill_between(tg[m], 0, vy[m], color=c, alpha=0.08)
            axg.legend(fontsize=7, frameon=False, loc="center left",
                       bbox_to_anchor=(1.01, 0.5))
            axg.set_ylabel("vGRF (N)", fontsize=7)
            axg.tick_params(labelsize=6)
            axes.append(axg)
        for r in rows:
            a = fig.add_subplot(gs[k], sharex=axes[0] if axes else None); k += 1
            axes.append(a)
            r["draw"](a)
            if r.get("title"):
                a.set_title(r["title"], fontsize=7.5, loc="left",
                            color=r.get("title_color", "k"))
            if r.get("ylabel"):
                a.set_ylabel(r["ylabel"], fontsize=7)
            a.tick_params(labelsize=6)
        # kinematics only (no GRF -> no events): the poses sit at evenly spaced
        # instants; mark those so each pose can still be read against the rows
        pose_lines = [] if self.events or not has_pose else self.pose_t
        for a in axes:
            for _, x in self.events:
                a.axvline(x, **EVENT_KW)
            for x in pose_lines:
                a.axvline(x, color="0.6", lw=0.7, ls=":", zorder=1)
            if t0 is not None:
                a.set_xlim(t0, t1)
            a.margins(x=0)
            if a is not axes[-1]:
                plt.setp(a.get_xticklabels(), visible=False)
        if axes:
            axes[-1].set_xlabel(xlabel, fontsize=8)
            top = axg or axes[0]
            for nm, x in self.events:
                top.text(x, 1.02, nm, transform=top.get_xaxis_transform(),
                         ha="center", va="bottom", fontsize=6, color="#333")
            if pose_lines:
                fig.text(0.99, 1 - 0.05 / H, "no GRF: poses at evenly spaced instants (dotted)",
                         ha="right", va="top", fontsize=6, color="0.45")
        if has_pose:
            self._draw_poses(fig, gs[0], axes[0])
        hs = list(legend or [])
        _first_row = axes[1] if (has_grf and len(axes) > 1) else (axes[0] if axes else None)
        if legend_loc == "top" and hs and _first_row is not None:
            _first_row.legend(handles=hs, loc="lower right", bbox_to_anchor=(1.0, 1.02),
                              ncol=legend_ncol or min(len(hs), 5), fontsize=7,
                              frameon=False, borderaxespad=0.0)
        else:
            if has_pose and self.grf:
                hs.insert(0, plt.Line2D([], [], color="0.3", lw=1.6, marker=">", markersize=4,
                                        label="GRF at the COP (pose row)"))
            if hs:
                fig.legend(handles=hs, loc="lower center", ncol=legend_ncol or min(len(hs), 5),
                           fontsize=7, frameon=False, bbox_to_anchor=(0.5, 0.0))
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=dpi)
        plt.close(fig)
        return str(out)

    def _draw_poses(self, fig, cell, ax_time):
        from bioscout.plot import jcf_coverage as jc
        gv = grf_vectors(self.trial)
        row = cell.get_position(fig)
        w = min(0.16, row.width / max(len(self.pose_t), 1) * 1.3)
        ev_side = {round(x, 6): nm[0].lower() for nm, x in (self.events or [])}
        for tt in self.pose_t:
            xf = fig.transFigure.inverted().transform(
                ax_time.transData.transform((tt, 0)))[0]
            q_t = self.q_at(tt)
            Rg = self.R_yaw @ jc._pelvis_in_ground(self.geo, q_t)
            vecs = pel = None
            if gv is not None:
                i = int(np.argmin(np.abs(gv[0] - tt)))
                vecs = [(sd, F[i], P[i]) for sd, F, P in gv[1]]
                pel = np.array([q_t.get("pelvis_tx", 0.0), q_t.get("pelvis_ty", 0.0),
                                q_t.get("pelvis_tz", 0.0)], float)
            anchor = None
            sd_ev = ev_side.get(round(tt, 6))
            if gv is not None and sd_ev in ("l", "r"):
                # the event foot's COP at the nearest LOADED frame (+-0.1 s): at the
                # strike/off frame itself the plate force is ~0 and the COP undefined
                for sd, F, P in gv[1]:
                    if sd != sd_ev:
                        continue
                    ok = np.flatnonzero((np.linalg.norm(F, axis=1) > 20.0)
                                        & (np.abs(gv[0] - tt) < 0.1))
                    if len(ok):
                        j = ok[np.argmin(np.abs(gv[0][ok] - tt))]
                        c = (self.R_yaw @ (P[j] - pel)) * 1000.0
                        anchor = float(c[jc._TO_PLOT][0])
                        break
            _pose_axis(fig, [xf - w / 2, row.y0, w, row.height], self.geo, q_t, Rg,
                       self.R_yaw, jc, grf_vec=vecs, pelvis_g=pel, anchor_x=anchor)


def strip_for(trial, t_range=None, log=print):
    """TaskStrip or None (never raises) -- for figure code with a grid fallback."""
    try:
        return TaskStrip(trial, t_range=t_range, log=log)
    except Exception as e:                               # noqa: BLE001
        if log:
            log(f"[task_figure] no task strip: {type(e).__name__}: {e}")
        return None
