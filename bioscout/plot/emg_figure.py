"""emg_processing.png in the vertical task layout (vGRF on top).

    from bioscout.plot.emg_figure import emg_task_figure
    emg_task_figure(exp_dir, out=exp_dir / "emg_processing.png")

``exp_dir`` is ``<session>/2_experimental/<trial>``. The figure is

    row 0   vertical GRF per foot, events dashed and named
            (no poses / kinematics: EMG is processed at export, before IK)
    rows    one row per EMG channel: filtered + normalised envelope (thick,
            shaded) on the left axis, raw signal faint grey on a twin axis.

Each EMG channel is coloured by the SIDE of the muscles session.yaml's
``emg_map`` assigns it (all ``*_r`` -> right red, all ``*_l`` -> left blue);
a channel with no mapping, or mixed sides, is grey -- e.g. a reference
electrode on the arm. The row title lists the model muscles it drives.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from bioscout.plot.task_figure import SIDE_COLOR, TaskStrip, read_sto

UNMAPPED = "0.45"
KIN_DOFS = (("hip_flexion", "hip flexion"), ("knee_angle", "knee angle"),
            ("ankle_angle", "ankle dorsiflexion"))


def _session_cfg(sess: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load((sess / "session.yaml").read_text()) or {}
    except Exception:                                    # noqa: BLE001
        return {}


def _flat_emg_map(cfg: dict, iteration: str | None = None) -> dict:
    """{channel: [muscles]}; a NAMED map set resolves to the iteration's choice
    (``emg_map: <name>`` on the iteration), else the first map."""
    m = cfg.get("emg_map") or {}
    if m and all(isinstance(v, dict) for v in m.values()):        # named maps
        it = ((cfg.get("iterations") or {}).get(iteration) or {}) if iteration else {}
        name = it.get("emg_map") if isinstance(it.get("emg_map"), str) else None
        m = m.get(name) or next(iter(m.values()))
    return {str(k): list(v or []) for k, v in m.items()}


def channel_side(channel: str, muscles) -> str | None:
    """'r' / 'l' when every mapped muscle is on that side, else None. Without a
    mapping, fall back to a trailing _r/_l in the channel name."""
    sides = {str(mu).lower()[-2:] for mu in (muscles or [])}
    if sides == {"_r"}:
        return "r"
    if sides == {"_l"}:
        return "l"
    if not muscles:
        low = channel.lower()
        if low.endswith("_r"):
            return "r"
        if low.endswith("_l"):
            return "l"
    return None


def _iteration_trial(sess: Path, trial: str, prefer: str | None = None) -> Path:
    """A 3_iterations/<it>/<trial> folder for the task strip: ``prefer`` when it
    has IK, else the first iteration with IK, else ``prefer``/first/any path."""
    root = sess / "3_iterations"
    cands = []
    if prefer:
        cands.append(root / prefer / trial)
    if root.is_dir():
        cands += sorted(p / trial for p in root.iterdir() if p.is_dir())
    for c in cands:
        if (c / "external_biomechanics" / "joint_angles.mot").is_file():
            return c
    return cands[0] if cands else root / "_none" / trial


def emg_task_figure(exp_dir, out=None, raw=None, norm=None, emg_map=None,
                    norm_source=None, iteration=None, channels=None, log=print):
    """Write emg_processing.png in the task layout. ``raw``/``norm`` are
    DataFrames (read from exp_dir/emg.mot and the best processed file when
    None). Returns the saved path."""
    import matplotlib.pyplot as plt
    import pandas as pd

    exp_dir = Path(exp_dir)
    sess = exp_dir.parents[1]
    trial = exp_dir.name
    out = Path(out) if out else exp_dir / "emg_processing.png"
    cfg = _session_cfg(sess)
    if emg_map is None:
        emg_map = _flat_emg_map(cfg, iteration)

    def _read(name):
        p = exp_dir / name
        return read_sto(p)[0] if p.is_file() else None

    if raw is None:
        raw = _read("emg.mot")
    if norm is None:
        for nm in ("emg_filtered_normalised.mot", "emg_filtered.mot"):
            norm = _read(nm)
            if norm is not None:
                break
    if raw is None and norm is None:
        raise FileNotFoundError(f"no emg.mot in {exp_dir}")

    base = norm if norm is not None else raw
    def _is_emg(c):
        return str(c).lower() != "time" and "emg" in str(c).lower()
    chans = list(channels or [])
    if not chans:
        # session order of the emg_map first, then whatever else the file holds
        chans = [c for c in emg_map if c in base.columns]
        chans += [c for c in base.columns if _is_emg(c) and c not in chans]
        if not chans:
            chans = [c for c in base.columns if str(c).lower() != "time"]
    # right-side channels, then left, then unmapped
    order = {"r": 0, "l": 1, None: 2}
    chans.sort(key=lambda c: order[channel_side(c, emg_map.get(c))])

    t_n = pd.to_numeric(base["time"], errors="coerce").to_numpy(float)
    t_r = (pd.to_numeric(raw["time"], errors="coerce").to_numpy(float)
           if raw is not None else None)
    t_rng = (float(np.nanmin(t_n)), float(np.nanmax(t_n)))

    it_trial = _iteration_trial(sess, trial, iteration)
    # EMG is processed at export, before IK: GRF + events only, no poses/kinematics
    strip = TaskStrip(it_trial, t_range=t_rng, poses=False, log=log)

    rows = []

    # ------------------------------------------------------------------ EMG
    def _num(df, c):
        return pd.to_numeric(df[c], errors="coerce").to_numpy(float)

    normalised = norm is not None and all(
        float(np.nanmax(_num(norm, c))) <= 1.5 for c in chans if c in norm.columns)

    for ch in chans:
        mus = emg_map.get(ch) or []
        sd = channel_side(ch, mus)
        col = SIDE_COLOR.get(sd, UNMAPPED)

        def _draw(ax, ch=ch, col=col):
            if raw is not None and ch in raw.columns:
                a2 = ax.twinx()
                a2.plot(t_r, _num(raw, ch), color="0.55", lw=0.35, alpha=0.6, zorder=0)
                a2.set_yticks([])
                a2.set_zorder(ax.get_zorder() - 1)
                ax.patch.set_visible(False)
            if norm is not None and ch in norm.columns:
                y = _num(norm, ch)
                ax.fill_between(t_n, 0, y, color=col, alpha=0.18, lw=0)
                ax.plot(t_n, y, color=col, lw=1.5)
                if normalised:
                    ax.set_ylim(0, 1.05)
        name = str(ch).replace("EMG_Channels_", "")
        ttl = name + ("  →  " + ", ".join(mus) if mus else "  (not in emg_map)")
        ref = norm_source.get(ch) if isinstance(norm_source, dict) else None
        if ref:
            ttl += f"   [norm: {ref}]"
        rows.append(dict(draw=_draw, title=ttl, title_color=col if sd else "0.3",
                         ylabel="0-1" if normalised else "V", height=0.62))

    h = [plt.Line2D([], [], color=SIDE_COLOR["r"], lw=1.5, label="right (emg_map)"),
         plt.Line2D([], [], color=SIDE_COLOR["l"], lw=1.5, label="left (emg_map)"),
         plt.Line2D([], [], color=UNMAPPED, lw=1.5, label="unmapped"),
         plt.Line2D([], [], color="0.55", lw=0.6,
                    label="raw EMG (own axis)"),
         ]
    path = strip.figure(rows, out, legend=h, row_height=1.5, legend_ncol=4)
    return path
