"""Joint angles and IK marker errors, compared across a session's iterations.

    bioscout plot kinematics <session path>
    bioscout plot kinematics <session path> --skip thesis_manual ast
    bioscout plot kinematics . --trial Bare1_Right,Bare2_Right --reference kainz_pwph

`bioscout plot collings` answers "which muscles does each model rank
differently"; this answers the question that comes before it: do the model
iterations even agree on the KINEMATICS, and how well does each one track the
markers. Same grammar — one session, every iteration under ``3_iterations/``,
output in ``<session>/4_outputs/`` — and, like collings, plain text readers
only, so it runs without OpenSim on the path.

WHAT IT READS  (per iteration, per trial; written by `bioscout simulate exbiomec`)

    3_iterations/<iteration>/<trial>/external_biomechanics/
        joint_angles.mot             IK result            (``ik.mot`` also accepted)
        _ik_marker_errors.sto        per frame: RMS and max marker error
        _ik_marker_errors_all.sto    per frame, per marker

WHAT IT WRITES  (``<session>/4_outputs/kinematics/``)

    joint_angles_<trial>.png     one panel per coordinate, one line per iteration
    marker_errors_<trial>.png    RMS and max error over time + marker x iteration map
    marker_errors_overview.png   every iteration, every trial, on one page
    joint_angles.csv             min / max / range per coordinate, and the
                                 difference from the reference iteration
    marker_errors.csv            mean / peak RMS and max error, worst marker

COLOUR IS THE ITERATION'S OWN
    Lines and bars take ``color:`` and ``label:`` from session.yaml, so an
    iteration looks the same here as in every other bioscout figure. Only
    iterations without a colour fall back to a fixed palette. The marker map
    is the exception: it shows a magnitude, so it is one hue, light to dark.

THE DASHED LINES ARE GUIDANCE, NOT A VERDICT
    20 mm RMS and 40 mm max are OpenSim's rule-of-thumb limits for IK. They
    are drawn so a figure can be read without the documentation open, and
    they move with ``--rms-limit`` / ``--max-limit``.

ANGLES ARE UNWRAPPED BEFORE THEY ARE COMPARED
    A pelvis rotation that crosses +/-180 deg is one smooth curve drawn as a
    full-height jump, and the "range" of such a curve is 360. Rotations are
    unwrapped and re-centred into (-180, 180] first, otherwise a participant
    who walks the lab in the other direction dominates every statistic.
"""
import argparse
import csv
import io
import os

import numpy as np

from .collings import find_iterations, find_trials, iterations_root

ANGLE_FILES = ("joint_angles.mot", "ik.mot")
ERR_FILE = "_ik_marker_errors.sto"
ERR_ALL_FILE = "_ik_marker_errors_all.sto"
SUBDIRS = ("external_biomechanics", "")

#: (row title, coordinates). A coordinate ending in ``_?`` is drawn once per
#: side; the others (pelvis) once.
DEFAULT_DOFS = ("pelvis_tilt", "pelvis_list", "pelvis_rotation",
                "hip_flexion_?", "hip_adduction_?", "hip_rotation_?",
                "knee_angle_?", "ankle_angle_?", "subtalar_angle_?")
SIDES = (("r", "right"), ("l", "left"))
TRANSLATIONS = ("_tx", "_ty", "_tz")

#: Fallback for iterations session.yaml gives no colour. Fixed order, never
#: cycled by rank: past the end the same hues return with another dash.
FALLBACK = ("#2a78d6", "#c0392b", "#1b7a3d", "#7b3294", "#e66101",
            "#008080", "#8c564b", "#555555")
DASHES = ("-", "--", ":", "-.")

RMS_LIMIT_MM = 20.0
MAX_LIMIT_MM = 40.0


# ------------------------------------------------------------------ reading
def read_table(path):
    """(names, array, in_degrees) of an OpenSim .mot/.sto. Whitespace split:
    OpenSim writes tabs, MATLAB-written files add trailing ones, and neither
    puts a space inside a column name."""
    with io.open(path, encoding="utf-8", errors="replace") as f:
        L = f.read().splitlines()
    hit = [k for k, x in enumerate(L) if x.strip().lower() == "endheader"]
    if not hit:
        return [], np.zeros((0, 0)), True
    i = hit[0]
    head = "".join(L[:i]).replace(" ", "").lower()
    deg = "indegrees=no" not in head and "in_degrees=no" not in head
    names = L[i + 1].split()
    rows = []
    for ln in L[i + 2:]:
        f = ln.split()
        if len(f) != len(names):
            continue
        try:
            rows.append([float(x) for x in f])
        except ValueError:
            pass
    A = np.array(rows, dtype=float) if rows else np.zeros((0, len(names)))
    return names, A, deg


def ik_file(session, iteration, trial, names):
    """First of ``names`` that exists for this iteration/trial, or None."""
    base = os.path.join(iterations_root(session), iteration, trial)
    for sub in SUBDIRS:
        for n in ((names,) if isinstance(names, str) else names):
            p = os.path.join(base, sub, n)
            if os.path.isfile(p):
                return p
    return None


def unwrap_deg(y):
    """A rotation in degrees without the +/-180 jumps, centred in (-180, 180]."""
    y = np.asarray(y, dtype=float)
    if y.size == 0 or not np.isfinite(y).all():
        return y
    u = np.degrees(np.unwrap(np.radians(y)))
    return u - 360.0 * np.round(np.mean(u) / 360.0)


def load_angles(path):
    """{coordinate: degrees (metres for translations)} plus ``time``."""
    names, A, deg = read_table(path)
    if not len(A) or "time" not in names:
        return None
    out = {"time": A[:, names.index("time")]}
    for k, n in enumerate(names):
        if n == "time" or n in out:
            continue
        y = A[:, k]
        if not n.endswith(TRANSLATIONS):
            y = unwrap_deg(y if deg else np.degrees(y))
        out[n] = y
    return out


def load_errors(session, iteration, trial):
    """dict(time, rms, max [mm], markers {name: mean mm}) or None."""
    p = ik_file(session, iteration, trial, ERR_FILE)
    if not p:
        return None
    names, A, _ = read_table(p)
    if not len(A) or "marker_error_RMS" not in names:
        return None
    e = {"time": A[:, names.index("time")],
         "rms": A[:, names.index("marker_error_RMS")] * 1e3,
         "max": A[:, names.index("marker_error_max")] * 1e3,
         "markers": {}}
    q = ik_file(session, iteration, trial, ERR_ALL_FILE)
    if q:
        n2, B, _ = read_table(q)
        for k, n in enumerate(n2):
            if n != "time" and len(B) and n not in e["markers"]:
                e["markers"][n] = float(np.nanmean(B[:, k])) * 1e3
    return e


# ------------------------------------------------------------------- styling
def _yaml_iterations(session):
    """session.yaml's ``iterations:`` block ({} when unreadable)."""
    try:
        import yaml
        with io.open(os.path.join(session, "session.yaml"), encoding="utf-8") as f:
            return (yaml.safe_load(f) or {}).get("iterations") or {}
    except Exception:                                          # noqa: BLE001
        return {}


def session_order(session, iterations):
    """``iterations`` in the order session.yaml lists them (the order their
    author chose, which keeps a sweep together); the rest follow, sorted."""
    order = list(_yaml_iterations(session))
    known = [i for i in order if i in iterations]
    return known + [i for i in iterations if i not in known]


def iteration_styles(session, iterations):
    """{iteration: (label, colour, dash)} — session.yaml first, palette after."""
    cfg = _yaml_iterations(session)
    out, k = {}, 0
    for it in iterations:
        b = cfg.get(it) or {}
        col = b.get("color")
        dash = "-"
        if not col:
            col = FALLBACK[k % len(FALLBACK)]
            dash = DASHES[(k // len(FALLBACK)) % len(DASHES)]
            k += 1
        out[it] = (str(b.get("label") or it), str(col), dash)
    return out


def expand_dofs(dofs):
    """[(row, title, [coordinate, ...])]: pelvis row, then one row per side."""
    single = [d for d in dofs if not d.endswith("_?")]
    sided = [d[:-2] for d in dofs if d.endswith("_?")]
    rows = []
    if single:
        rows.append(("pelvis" if all(d.startswith("pelvis") for d in single)
                     else "", single))
    for s, name in SIDES:
        if sided:
            rows.append((name, ["%s_%s" % (d, s) for d in sided]))
    return rows


def _unit(coord):
    return "m" if coord.endswith(TRANSLATIONS) else "deg"


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _soften(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("0.6")
    ax.tick_params(labelsize=7, colors="0.3", length=2.5)
    ax.grid(True, color="0.9", lw=0.6)
    ax.set_axisbelow(True)


def _legend(fig, styles, its, **kw):
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], color=styles[i][1], ls=styles[i][2], lw=2,
                label=styles[i][0]) for i in its]
    return fig.legend(handles=h, frameon=False, fontsize=7.5,
                      ncol=max(1, min(6, int(np.ceil(len(its) / 6.0)))), **kw)


# ------------------------------------------------------------------- figures
def joint_angle_figure(data, styles, path, title, dofs=DEFAULT_DOFS):
    """``data``: {iteration: load_angles(...)}, in drawing order."""
    plt = _plt()
    rows = expand_dofs(dofs)
    ncol = max(len(c) for _, c in rows)
    its = list(data)
    fig, axes = plt.subplots(len(rows), ncol, squeeze=False,
                             figsize=(2.6 * ncol + 0.6, 2.25 * len(rows) + 0.6))
    t0 = min(float(d["time"][0]) for d in data.values())
    for r, (rname, coords) in enumerate(rows):
        for c in range(ncol):
            ax = axes[r][c]
            if c >= len(coords):
                ax.set_visible(False)
                continue
            coord, drawn = coords[c], 0
            for it in its:
                d = data[it]
                if coord not in d:
                    continue
                ax.plot(d["time"] - t0, d[coord], color=styles[it][1],
                        ls=styles[it][2], lw=1.3, alpha=0.9)
                drawn += 1
            _soften(ax)
            stem = coord[:-2] if coord.endswith(("_r", "_l")) and rname in ("right", "left") else coord
            ax.set_title(stem.replace("_", " "), fontsize=8.5, color="0.15")
            if c == 0:
                ax.set_ylabel(("%s\n" % rname if rname else "") + "(%s)" % _unit(coord),
                              fontsize=8, color="0.2")
            if r == len(rows) - 1 or c >= len(rows[min(r + 1, len(rows) - 1)][1]):
                ax.set_xlabel("time (s)", fontsize=7.5, color="0.3")
            if not drawn:
                ax.text(0.5, 0.5, "not in any model", transform=ax.transAxes,
                        ha="center", va="center", fontsize=7.5, color="0.5")
    fig.suptitle(title, fontsize=10.5, x=0.01, ha="left", y=0.995, va="top")
    # The pelvis row is shorter than the limb rows, so its empty right-hand
    # corner holds the legend; only a full grid pushes it below the panels.
    free = ncol - len(rows[0][1])
    if free >= 2:
        fig.tight_layout(rect=(0, 0, 1, 0.965))
        box = axes[0][len(rows[0][1])].get_position()
        _legend(fig, styles, its, loc="upper left", bbox_to_anchor=(box.x0, box.y1))
    else:
        lg = _legend(fig, styles, its, loc="lower center", bbox_to_anchor=(0.5, 0.0))
        lines = int(np.ceil(len(its) / float(getattr(lg, "_ncols", 4))))
        fig.tight_layout(rect=(0, (0.15 + 0.17 * lines) / fig.get_figheight(), 1, 0.965))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def marker_error_figure(errs, styles, path, title,
                        rms_limit=RMS_LIMIT_MM, max_limit=MAX_LIMIT_MM):
    """``errs``: {iteration: load_errors(...)}, in drawing order."""
    plt = _plt()
    its = list(errs)
    markers = []
    for it in its:
        for m in errs[it]["markers"]:
            if m not in markers:
                markers.append(m)
    has_map = bool(markers)
    h_map = 0.24 * len(its) + 1.3 if has_map else 0.0
    fig = plt.figure(figsize=(max(9.0, 0.27 * len(markers) + 3.2), 5.4 + h_map))
    gs = fig.add_gridspec(3 if has_map else 2, 1,
                          height_ratios=[2.2, 2.2] + ([h_map] if has_map else []))
    t0 = min(float(e["time"][0]) for e in errs.values())
    for k, (key, lab, lim) in enumerate((("rms", "RMS marker error (mm)", rms_limit),
                                         ("max", "max marker error (mm)", max_limit))):
        ax = fig.add_subplot(gs[k])
        for it in its:
            e = errs[it]
            ax.plot(e["time"] - t0, e[key], color=styles[it][1], ls=styles[it][2],
                    lw=1.3, alpha=0.9)
        if lim:
            ax.axhline(lim, color="0.35", lw=0.8, ls=(0, (4, 3)))
            ax.annotate("%g mm guide" % lim, xy=(1, lim), xycoords=("axes fraction", "data"),
                        xytext=(-3, 3), textcoords="offset points", ha="right",
                        fontsize=7, color="0.35")
        ax.set_ylim(bottom=0)
        ax.set_ylabel(lab, fontsize=8, color="0.2")
        _soften(ax)
        if k == 1:
            ax.set_xlabel("time (s)", fontsize=7.5, color="0.3")
    if has_map:
        ax = fig.add_subplot(gs[2])
        M = np.array([[errs[it]["markers"].get(m, np.nan) for m in markers] for it in its])
        cmap = plt.get_cmap("Blues").copy()
        cmap.set_bad("0.93")
        im = ax.imshow(np.ma.masked_invalid(M), aspect="auto", cmap=cmap, vmin=0,
                       vmax=max(float(np.nanmax(M)), 1e-9))
        ax.set_xticks(range(len(markers)))
        ax.set_xticklabels(markers, rotation=90, fontsize=6.5)
        ax.set_yticks(range(len(its)))
        ax.set_yticklabels([styles[i][0] for i in its], fontsize=7)
        ax.set_xticks(np.arange(-.5, len(markers)), minor=True)
        ax.set_yticks(np.arange(-.5, len(its)), minor=True)
        ax.grid(which="minor", color="white", lw=1.2)
        ax.tick_params(which="both", length=0, colors="0.3")
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_title("mean error per marker (mm); grey = not tracked by that model",
                     fontsize=8.5, color="0.15", loc="left")
        cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
        cb.ax.tick_params(labelsize=7, colors="0.3")
        cb.outline.set_visible(False)
    fig.suptitle(title, fontsize=10.5, x=0.01, ha="left", y=0.995, va="top")
    lg = _legend(fig, styles, its, loc="upper right", bbox_to_anchor=(0.995, 0.975))
    lines = int(np.ceil(len(its) / float(getattr(lg, "_ncols", 4))))
    fig.tight_layout(rect=(0, 0, 1, 1 - (0.35 + 0.17 * lines) / fig.get_figheight()))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def overview_figure(rows, styles, its, path, title,
                    rms_limit=RMS_LIMIT_MM, max_limit=MAX_LIMIT_MM):
    """Every iteration on one page: bar = mean over trials, dots = each trial."""
    plt = _plt()
    its = [i for i in its if any(r["iteration"] == i for r in rows)]
    fig, axes = plt.subplots(1, 2, sharey=True,
                             figsize=(9.5, 0.3 * len(its) + 1.7))
    y = np.arange(len(its))
    for ax, key, lab, lim in ((axes[0], "rms_mean_mm", "RMS marker error, mean over the trial (mm)", rms_limit),
                              (axes[1], "max_peak_mm", "largest single marker error in the trial (mm)", max_limit)):
        for k, it in enumerate(its):
            v = [r[key] for r in rows if r["iteration"] == it]
            ax.barh(k, np.mean(v), height=0.62, color=styles[it][1], alpha=0.85)
            ax.plot(v, [k] * len(v), ls="", marker="o", ms=3.6, mfc="white",
                    mec="0.2", mew=0.8, zorder=3)
            ax.text(max(v), k, "  %.0f" % np.mean(v), va="center", fontsize=7, color="0.25")
        if lim:
            ax.axvline(lim, color="0.35", lw=0.8, ls=(0, (4, 3)))
            ax.annotate("%g mm guide" % lim, xy=(lim, 1), xycoords=("data", "axes fraction"),
                        xytext=(3, 2), textcoords="offset points", fontsize=7,
                        color="0.35", va="bottom")
        ax.set_xlabel(lab, fontsize=8, color="0.2")
        _soften(ax)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(left=0)
        ax.margins(x=0.12)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([styles[i][0] for i in its], fontsize=7.5)
    axes[0].set_ylim(len(its) - 0.4, -0.6)
    fig.suptitle(title + "   (bar = mean of trials, dots = each trial)",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


# -------------------------------------------------------------------- tables
def angle_rows(trial, data, coords, reference=None):
    """One row per iteration and coordinate; differences are against
    ``reference`` (interpolated onto its time base)."""
    out = []
    ref = data.get(reference) if reference else None
    for it, d in data.items():
        for c in coords:
            if c not in d:
                continue
            y = d[c]
            row = {"trial": trial, "iteration": it, "coordinate": c, "unit": _unit(c),
                   "min": float(np.min(y)), "max": float(np.max(y)),
                   "mean": float(np.mean(y)), "range": float(np.ptp(y)),
                   "reference": reference or "", "mean_diff_vs_ref": "", "rmsd_vs_ref": ""}
            if ref is not None and c in ref and it != reference:
                lo, hi = max(d["time"][0], ref["time"][0]), min(d["time"][-1], ref["time"][-1])
                m = (ref["time"] >= lo) & (ref["time"] <= hi)
                if m.sum() > 1:
                    diff = np.interp(ref["time"][m], d["time"], y) - ref[c][m]
                    if not c.endswith(TRANSLATIONS):
                        diff = (diff + 180.0) % 360.0 - 180.0
                    row["mean_diff_vs_ref"] = float(np.mean(diff))
                    row["rmsd_vs_ref"] = float(np.sqrt(np.mean(diff ** 2)))
            out.append(row)
    return out


def error_row(trial, it, e):
    worst = max(e["markers"].items(), key=lambda kv: kv[1]) if e["markers"] else ("", float("nan"))
    return {"trial": trial, "iteration": it, "n_frames": int(len(e["time"])),
            "rms_mean_mm": float(np.mean(e["rms"])), "rms_peak_mm": float(np.max(e["rms"])),
            "max_mean_mm": float(np.mean(e["max"])), "max_peak_mm": float(np.max(e["max"])),
            "worst_marker": worst[0], "worst_marker_mean_mm": worst[1]}


def _write_csv(path, rows):
    if not rows:
        return None
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: ("%.4f" % v if isinstance(v, float) else v) for k, v in r.items()})
    return path


# --------------------------------------------------------------- entry point
def kinematics_session(session, skip=(), trials=None, iterations=None,
                       dofs=DEFAULT_DOFS, reference=None, out_dir=None,
                       rms_limit=RMS_LIMIT_MM, max_limit=MAX_LIMIT_MM, log=print):
    """Compare joint angles and marker errors across iterations, one pair of
    figures per trial plus an overview and two tables. Returns the files
    written (empty when no iteration has IK results)."""
    session = os.path.abspath(session)
    if not os.path.isdir(session):
        raise NotADirectoryError(session)
    low = {s.lower() for s in (skip or ())}
    its = [i for i in (iterations or session_order(session, find_iterations(session, skip)))
           if i.lower() not in low]
    if not its:
        log("[kinematics] no iterations under %s" % session)
        return []
    styles = iteration_styles(session, its)
    want = list(trials) if trials else None
    seen = []
    for it in its:
        for t in find_trials(session, it):
            if (want is None or t in want) and t not in seen:
                seen.append(t)
    if reference and reference not in its:
        log("[kinematics] reference %r is not one of the iterations — ignored" % reference)
        reference = None

    out_dir = out_dir or os.path.join(session, "4_outputs", "kinematics")
    coords = [c for _, cs in expand_dofs(dofs) for c in cs]
    written, a_rows, e_rows = [], [], []
    name = os.path.basename(os.path.dirname(session)) + " / " + os.path.basename(session)
    for trial in seen:
        ang, err = {}, {}
        for it in its:
            p = ik_file(session, it, trial, ANGLE_FILES)
            d = load_angles(p) if p else None
            if d is not None:
                ang[it] = d
            e = load_errors(session, it, trial)
            if e is not None:
                err[it] = e
        if not ang and not err:
            continue
        os.makedirs(out_dir, exist_ok=True)
        if ang:
            ref = reference if reference in ang else next(iter(ang))
            a_rows += angle_rows(trial, ang, coords, ref)
            f = os.path.join(out_dir, "joint_angles_%s.png" % trial)
            joint_angle_figure(ang, styles, f, "Joint angles — %s — %s" % (trial, name), dofs)
            log("[kinematics] %s  (%d iterations)" % (os.path.relpath(f, session), len(ang)))
            written.append(f)
        if err:
            e_rows += [error_row(trial, it, e) for it, e in err.items()]
            f = os.path.join(out_dir, "marker_errors_%s.png" % trial)
            marker_error_figure(err, styles, f, "IK marker errors — %s — %s" % (trial, name),
                                rms_limit, max_limit)
            log("[kinematics] %s  (%d iterations)" % (os.path.relpath(f, session), len(err)))
            written.append(f)
        missing = [it for it in its if it not in ang and it not in err]
        if missing:
            log("[kinematics] %s: no IK results for %s" % (trial, ", ".join(missing)))
    if not written:
        log("[kinematics] nothing written — no iteration has %s or %s under "
            "3_iterations/<iteration>/<trial>/external_biomechanics/. "
            "Run `bioscout simulate exbiomec` first." % (ANGLE_FILES[0], ERR_FILE))
        return []
    if e_rows:
        f = os.path.join(out_dir, "marker_errors_overview.png")
        overview_figure(e_rows, styles, its, f, "IK marker errors — %s" % name,
                        rms_limit, max_limit)
        written.append(f)
    for fn, rows in (("joint_angles.csv", a_rows), ("marker_errors.csv", e_rows)):
        p = _write_csv(os.path.join(out_dir, fn), rows)
        if p:
            written.append(p)
    log("[kinematics] %d file(s) in %s" % (len(written), out_dir))
    return written


def find_session(path):
    """``path`` if it holds session.yaml, else the single session below it."""
    path = os.path.abspath(path)
    if os.path.isfile(os.path.join(path, "session.yaml")):
        return path, []
    hits = []
    for root, dirs, files in os.walk(path):
        depth = os.path.relpath(root, path).count(os.sep)
        if "session.yaml" in files:
            hits.append(root)
            dirs[:] = []
        elif depth >= 3:
            dirs[:] = []
    return (hits[0] if len(hits) == 1 else None), hits


def _list(v):
    return [x.strip() for part in (v or []) for x in str(part).split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="bioscout plot kinematics",
        description="Joint angles and IK marker errors compared across a session's "
                    "iterations -> <session>/4_outputs/kinematics/")
    ap.add_argument("path", nargs="?", default=".", metavar="SESSION_PATH",
                    help="session folder (holds session.yaml); default: here")
    ap.add_argument("--skip", nargs="*", metavar="ITERATION", help="iterations to leave out")
    ap.add_argument("--iteration", nargs="*", metavar="A,B",
                    help="only these iterations, in this order (default: every one on disk)")
    ap.add_argument("--trial", nargs="*", metavar="NAME[,NAME]",
                    help="only these trials (default: all)")
    ap.add_argument("--dofs", nargs="*", metavar="COORD",
                    help="coordinates to draw; end a name in _? for both sides "
                         "(default: pelvis, hip, knee, ankle, subtalar)")
    ap.add_argument("--reference", metavar="ITERATION",
                    help="iteration the angle differences in joint_angles.csv are "
                         "taken against (default: the first one drawn)")
    ap.add_argument("--rms-limit", type=float, default=RMS_LIMIT_MM, metavar="MM",
                    help="guide line on the RMS panels (default 20; 0 = none)")
    ap.add_argument("--max-limit", type=float, default=MAX_LIMIT_MM, metavar="MM",
                    help="guide line on the max panels (default 40; 0 = none)")
    ap.add_argument("-o", "--out", metavar="DIR",
                    help="output folder (default <session>/4_outputs/kinematics)")
    a = ap.parse_args(argv)
    sess, hits = find_session(a.path)
    if not sess:
        if hits:
            print("[kinematics] several sessions below that path -- name one:")
            for h in hits:
                print("    " + h)
        else:
            print("[kinematics] no session.yaml at or below %s" % os.path.abspath(a.path))
        return 2
    w = kinematics_session(
        sess, skip=_list(a.skip), trials=_list(a.trial) or None,
        iterations=_list(a.iteration) or None, dofs=tuple(_list(a.dofs)) or DEFAULT_DOFS,
        reference=a.reference, out_dir=(os.path.abspath(a.out) if a.out else None),
        rms_limit=a.rms_limit, max_limit=a.max_limit)
    return 0 if w else 1


if __name__ == "__main__":
    raise SystemExit(main())
