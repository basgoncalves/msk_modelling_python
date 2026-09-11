"""Compare mew output against Static Optimisation and CEINMS.

This is DESIGN.md section 10, items 3 and 4, made runnable. Tier 1 should agree
closely with OpenSim SO -- systematic disagreement there is a geometry or
parameter bug, not a modelling choice. Tier 2/3 should NOT agree exactly with
SO (that would mean the EMG changed nothing), but should track CEINMS.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .io_ports import read_storage, resample
from .types import MuscleForceResult


def _lowpass(x: np.ndarray, times: np.ndarray, cutoff=15.0) -> np.ndarray:
    """Zero-lag 4th-order Butterworth. Returns x unchanged if scipy is absent."""
    try:
        from scipy.signal import butter, filtfilt
    except ImportError:
        return x
    if len(times) < 20:
        return x
    fs = 1.0 / float(np.median(np.diff(times)))
    wn = cutoff / (0.5 * fs)
    if not 0 < wn < 1:
        return x
    b, a = butter(4, wn, btype="low")
    return filtfilt(b, a, x)


def compare_arrays(times, muscles, new: np.ndarray, ref: pd.DataFrame,
                   smooth_cutoff=15.0) -> pd.DataFrame:
    """Core comparison: an (nt, nm) array against a reference DataFrame."""
    rows = []
    for j, m in enumerate(muscles):
        if m not in ref.columns:
            continue
        a = np.asarray(new)[:, j]
        b = ref[m].to_numpy(float)
        af, bf = _lowpass(a, times, smooth_cutoff), _lowpass(b, times, smooth_cutoff)

        def _r2(x, y):
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            return (1.0 - float(np.sum((x - y) ** 2)) / ss_tot
                    if ss_tot > 1e-9 else np.nan)

        pk_ref, pk_new = float(np.max(np.abs(b))), float(np.max(np.abs(a)))
        rows.append({
            "muscle": m,
            "peak_ref_N": pk_ref,
            "peak_new_N": pk_new,
            "rmse_N": float(np.sqrt(np.mean((a - b) ** 2))),
            "r2": _r2(a, b),
            "r2_smooth": _r2(af, bf),
            "peak_ratio": pk_new / pk_ref if pk_ref > 1e-6 else np.nan,
        })
    return pd.DataFrame(rows).sort_values("peak_ref_N", ascending=False)


def compare_files(path_new, path_ref, times, label="reference",
                  smooth_cutoff=15.0) -> pd.DataFrame:
    """Compare two force .sto files on a common time base.

    Used to measure how far the EXISTING references (SO and CEINMS) sit from
    each other. Without that baseline, "mew disagrees with SO by X"
    is a number with nothing to compare it to.
    """
    a = resample(read_storage(path_new), times)
    b = resample(read_storage(path_ref), times)
    muscles = [c for c in a.columns if c != "time" and c in b.columns]
    df = compare_arrays(times, muscles, a[muscles].to_numpy(float), b,
                        smooth_cutoff=smooth_cutoff)
    df.attrs["label"] = label
    return df


def compare_forces(result: MuscleForceResult, reference_path, label="reference",
                   smooth_cutoff=15.0) -> pd.DataFrame:
    """Per-muscle R2, RMSE and peak error against a reference force .sto.

    Reports R2 twice: raw, and after low-pass filtering BOTH signals identically.

    That second column is not cosmetic. OpenSim's Static Optimisation solves
    each frame independently with no temporal coupling, so its force traces
    chatter between adjacent frames; this solver carries a smoothing term
    (``SolverWeights.delta``) and does not. Raw R2 therefore charges this
    solver for SO's frame-to-frame noise. ``r2_smooth`` compares what the two
    methods actually disagree about -- the shape of the force over time --
    rather than which one is noisier.

    Sorted by the reference's peak force, so the muscles that carry real load
    appear first rather than the alphabetically lucky ones.
    """
    ref = resample(read_storage(reference_path), result.times)
    df = compare_arrays(result.times, result.muscles, result.forces, ref,
                        smooth_cutoff=smooth_cutoff)
    df.attrs["label"] = label
    return df


def summarise(df: pd.DataFrame, top=15) -> str:
    """Readable digest, weighted towards the muscles that carry real force."""
    if df.empty:
        return "  (no muscles in common with the reference)"
    big = df.head(top)
    lines = [f"  {'muscle':16s} {'peak ref':>9s} {'peak new':>9s} {'ratio':>6s} "
             f"{'RMSE':>8s} {'R2':>6s} {'R2smth':>7s}"]
    for _, r in big.iterrows():
        lines.append(f"  {r['muscle']:16s} {r['peak_ref_N']:9.0f} "
                     f"{r['peak_new_N']:9.0f} {r['peak_ratio']:6.2f} "
                     f"{r['rmse_N']:8.1f} {r['r2']:6.2f} {r['r2_smooth']:7.2f}")
    lines.append("\n" + aggregate_line(df))
    return "\n".join(lines)


def aggregate(df: pd.DataFrame, load_fraction=0.05, r2_floor=-1.0) -> dict:
    """Robust summary of a comparison table.

    Two guards, both learned the hard way on FAIS 022:

    * **Only muscles carrying real load count.** A muscle whose reference peak
      is under ``load_fraction`` of the largest peak is mostly noise; including
      it measures agreement about nothing.
    * **R2 is floored.** R2 is unbounded below, so ONE muscle whose reference
      is nearly constant can return -10000 and swamp a weighted mean -- a
      force-weighted R2 of -1066 on this trial came from exactly that. Floored
      at ``r2_floor``, the aggregate says "no better than the mean" instead of
      reporting a meaningless magnitude. The median is reported alongside
      because it needs no floor at all.
    """
    if df.empty:
        return {"n": 0}
    cut = float(df["peak_ref_N"].max()) * load_fraction
    d = df[df["peak_ref_N"] >= cut]
    if d.empty:
        d = df
    w = d["peak_ref_N"].to_numpy()
    w = w / w.sum() if w.sum() > 0 else np.ones(len(d)) / len(d)

    def _wm(col):
        v = np.clip(d[col].to_numpy(float), r2_floor, 1.0)
        return float(np.nansum(w * np.nan_to_num(v, nan=r2_floor)))

    return {
        "n": int(len(df)), "n_load_bearing": int(len(d)),
        "load_threshold_N": cut,
        "wR2": _wm("r2"), "wR2_smooth": _wm("r2_smooth"),
        "medianR2": float(d["r2"].median()),
        "medianR2_smooth": float(d["r2_smooth"].median()),
        "median_peak_ratio": float(d["peak_ratio"].median()),
    }


def aggregate_line(df: pd.DataFrame) -> str:
    a = aggregate(df)
    if not a.get("n"):
        return "  (nothing to compare)"
    return (f"  {a['n_load_bearing']}/{a['n']} load-bearing muscles "
            f"(peak >= {a['load_threshold_N']:.0f} N) | "
            f"weighted R2 {a['wR2']:+.2f} raw / {a['wR2_smooth']:+.2f} filtered "
            f"(floored at -1) | median R2 {a['medianR2']:+.2f} / "
            f"{a['medianR2_smooth']:+.2f} | median peak ratio "
            f"{a['median_peak_ratio']:.2f}")


def plot_comparison(result: MuscleForceResult, references: Dict[str, str],
                    out_png, muscles: Optional[List[str]] = None, n=9) -> Optional[str]:
    """Grid of force traces: this solve against each reference. Needs matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if muscles is None:
        peaks = np.max(np.abs(result.forces), axis=0)
        muscles = [result.muscles[i] for i in np.argsort(-peaks)[:n]]

    refs = {k: resample(read_storage(v), result.times)
            for k, v in references.items() if v and os.path.exists(str(v))}

    ncol = 3
    nrow = int(np.ceil(len(muscles) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 2.6 * nrow),
                             sharex=True, squeeze=False)
    for ax, m in zip(axes.ravel(), muscles):
        j = result.muscles.index(m)
        ax.plot(result.times, result.forces[:, j], lw=2,
                label=f"mew ({result.tier.label})")
        for name, ref in refs.items():
            if m in ref.columns:
                ax.plot(result.times, ref[m].to_numpy(float), lw=1.2, ls="--",
                        label=name)
        ax.set_title(m, fontsize=9)
        ax.set_ylabel("force (N)", fontsize=8)
        ax.tick_params(labelsize=7)
    for ax in axes.ravel()[len(muscles):]:
        ax.axis("off")
    axes[0, 0].legend(fontsize=7)
    for ax in axes[-1]:
        ax.set_xlabel("time (s)", fontsize=8)
    fig.suptitle(f"{result.provenance.trial} -- muscle forces "
                 f"(tier {result.tier.label}, confidence {result.confidence:.2f})",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return str(out_png)
