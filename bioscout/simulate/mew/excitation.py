"""EMG -> muscle excitation.

Takes bioscout's already-normalised ``emg_filtered_normalised.mot`` when it
exists (the preferred path -- MVC normalisation belongs to the session, not to
this solver), and can do the filtering itself when handed raw EMG.

The channel->muscle mapping is bioscout's ``emg_map`` format verbatim::

    {"RF": ["recfem_r"], "VAS": ["vasmed_r", "vaslat_r", "vasint_r"]}

One channel can drive several muscles (a shared excitation), which is exactly
what CEINMS does and what makes 16 electrodes able to inform 80 muscles.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .mtu import MuscleParameters, activation_dynamics, emg_to_activation


# --------------------------------------------------------------------------- #
#  Signal conditioning (only needed for RAW emg)
# --------------------------------------------------------------------------- #
def process_raw(df: pd.DataFrame, *, band=(30.0, 400.0), lowpass=6.0,
                mvc: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """band-pass -> rectify -> low-pass -> normalise. Needs scipy."""
    from scipy.signal import butter, filtfilt

    t = df["time"].to_numpy(float)
    fs = 1.0 / np.median(np.diff(t))
    nyq = 0.5 * fs
    bh, ah = butter(4, [band[0] / nyq, min(band[1] / nyq, 0.99)], btype="bandpass")
    bl, al = butter(4, lowpass / nyq, btype="low")

    out = {"time": t}
    for c in df.columns:
        if c == "time":
            continue
        x = df[c].to_numpy(float)
        x = filtfilt(bl, al, np.abs(filtfilt(bh, ah, x)))
        denom = (mvc or {}).get(c) or np.percentile(np.abs(x), 99.5) or 1.0
        out[c] = np.clip(x / denom, 0.0, 1.5)
    return pd.DataFrame(out)


def apply_delay(df: pd.DataFrame, delay_s=0.045) -> pd.DataFrame:
    """Electromechanical delay: shift excitation forward in time."""
    if not delay_s:
        return df
    out = df.copy()
    out["time"] = out["time"].to_numpy(float) + float(delay_s)
    return out


# --------------------------------------------------------------------------- #
#  Mapping channels onto muscles
# --------------------------------------------------------------------------- #
def map_to_muscles(emg: pd.DataFrame, emg_map: Dict[str, List[str]],
                   muscles: Sequence[str],
                   gains: Optional[Dict[str, float]] = None
                   ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Spread channels over muscles.

    Returns ``(u, mask, used_channels)`` where ``u`` is (nt, nm) excitation and
    ``mask`` is (nm,) bool marking which muscles an electrode actually informs.
    Unmapped muscles keep u=0 and mask=False -- the solver must be free to
    choose their activation, so it is important the mask is honest here.
    """
    muscles = list(muscles)
    nt, nm = len(emg), len(muscles)
    u = np.zeros((nt, nm))
    mask = np.zeros(nm, dtype=bool)
    used: List[str] = []
    index = {m: i for i, m in enumerate(muscles)}

    for channel, targets in (emg_map or {}).items():
        if channel not in emg.columns:
            continue
        sig = np.clip(emg[channel].to_numpy(float), 0.0, 1.0)
        sig = sig * float((gains or {}).get(channel, 1.0))
        hit = False
        for m in (targets if isinstance(targets, (list, tuple)) else [targets]):
            if m in index:
                u[:, index[m]] = sig
                mask[index[m]] = True
                hit = True
        if hit:
            used.append(channel)
    return np.clip(u, 0.0, 1.0), mask, used


def excitation_to_activation(u: np.ndarray, times: np.ndarray,
                             params: MuscleParameters) -> np.ndarray:
    """Full neural pathway: excitation -> activation dynamics -> nonlinearity."""
    dt = float(np.median(np.diff(times))) if len(times) > 1 else 0.01
    a_lin = activation_dynamics(u, dt, params)
    return emg_to_activation(a_lin, params.shape_A)


def emg_targets(emg: Optional[pd.DataFrame], emg_map, muscles, params,
                times: np.ndarray, gains=None, delay_s=0.0):
    """Convenience: EMG frame -> ``(a_emg (nt,nm), mask (nm,), channels)``.

    Returns zeros and an all-False mask when there is no usable EMG, so callers
    never need to branch on ``emg is None``.
    """
    nm = len(muscles)
    if emg is None or not emg_map:
        return np.zeros((len(times), nm)), np.zeros(nm, dtype=bool), []
    from .io_ports import resample
    if delay_s:
        emg = apply_delay(emg, delay_s)
    emg = resample(emg, times)
    u, mask, channels = map_to_muscles(emg, emg_map, muscles, gains)
    return excitation_to_activation(u, times, params), mask, channels
