"""File I/O and resampling — the only place that touches disk formats.

Prefers ``bioscout.utils.io`` when bioscout is importable (so headers, column
handling and quirks stay identical to the rest of the pipeline), and falls back
to a self-contained OpenSim .sto/.mot parser so the package runs standalone.
"""
from __future__ import annotations

import os
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
#  bioscout passthrough (optional)
# --------------------------------------------------------------------------- #
def _bioscout_io():
    try:
        from bioscout.utils import io as _io   # noqa: WPS433
        return _io
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Reading
# --------------------------------------------------------------------------- #
def read_storage(path) -> pd.DataFrame:
    """Read an OpenSim .sto / .mot into a DataFrame with a ``time`` column."""
    bio = _bioscout_io()
    if bio is not None:
        try:
            df = bio.load_sto(str(path))
            if isinstance(df, pd.DataFrame) and len(df.columns):
                return _ensure_time(df)
        except Exception:
            pass   # fall through to the local parser
    return _ensure_time(_read_storage_local(path))


def _read_storage_local(path) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    start = 0
    for i, line in enumerate(lines):
        if line.strip().lower() == "endheader":
            start = i + 1
            break
    else:                                        # no header block: assume row 0
        start = 0
    header = [c.strip() for c in lines[start].rstrip("\n").split("\t") if c.strip()]
    rows = []
    for line in lines[start + 1:]:
        parts = [p for p in line.replace("\r", "").rstrip("\n").split("\t") if p != ""]
        if len(parts) < len(header):
            continue
        try:
            rows.append([float(p) for p in parts[:len(header)]])
        except ValueError:
            continue
    return pd.DataFrame(rows, columns=header)


def _ensure_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = {c.lower(): c for c in df.columns}
    if "time" not in cols:
        raise ValueError(f"no 'time' column in {list(df.columns)[:6]}...")
    if cols["time"] != "time":
        df = df.rename(columns={cols["time"]: "time"})
    return df


def as_frame(obj, what="signal") -> Optional[pd.DataFrame]:
    """Accept a path, a DataFrame or None and return a DataFrame or None."""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return _ensure_time(obj)
    if isinstance(obj, (str, os.PathLike)):
        if not os.path.exists(obj):
            raise FileNotFoundError(f"{what}: {obj}")
        return read_storage(obj)
    raise TypeError(f"{what}: expected path or DataFrame, got {type(obj).__name__}")


# --------------------------------------------------------------------------- #
#  Resampling / alignment
# --------------------------------------------------------------------------- #
def resample(df: pd.DataFrame, times: np.ndarray) -> pd.DataFrame:
    """Linear-interpolate every non-time column onto ``times``."""
    t_src = df["time"].to_numpy(dtype=float)
    out = {"time": np.asarray(times, dtype=float)}
    for col in df.columns:
        if col == "time":
            continue
        out[col] = np.interp(times, t_src, df[col].to_numpy(dtype=float))
    return pd.DataFrame(out)


def common_time(frames: Iterable[pd.DataFrame], base: pd.DataFrame,
                time_range: Optional[Sequence[float]] = None) -> np.ndarray:
    """The ``base`` time axis, clipped to the window every frame covers."""
    frames = [f for f in frames if f is not None]
    t = base["time"].to_numpy(dtype=float)
    lo = max([f["time"].min() for f in frames] + [t.min()])
    hi = min([f["time"].max() for f in frames] + [t.max()])
    if time_range is not None and len(time_range) == 2:
        lo, hi = max(lo, float(time_range[0])), min(hi, float(time_range[1]))
    sel = t[(t >= lo) & (t <= hi)]
    if len(sel) < 2:
        raise ValueError(
            f"inputs do not overlap in time (window {lo:.3f}-{hi:.3f} s). "
            "Check time_range and that every signal covers the trial.")
    return sel


def derivative(y: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Central-difference d/dt along axis 0, edge-safe."""
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=float)
    if y.ndim == 1:
        return np.gradient(y, t)
    return np.gradient(y, t, axis=0)


# --------------------------------------------------------------------------- #
#  Writing
# --------------------------------------------------------------------------- #
def write_sto(path, times, columns: List[str], data: np.ndarray, name="Data"):
    """Write an OpenSim .sto with the header CEINMS/bioscout readers expect."""
    path = str(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    data = np.atleast_2d(np.asarray(data, dtype=float))
    nrows, ncols = data.shape
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(f"{name}\n")
        fh.write("version=1\n")
        fh.write(f"nRows={nrows}\n")
        fh.write(f"nColumns={ncols + 1}\n")
        fh.write("inDegrees=no\n")
        fh.write("endheader\n")
        fh.write("time\t" + "\t".join(columns) + "\n")
        for i in range(nrows):
            fh.write(f"{times[i]:.8f}\t" +
                     "\t".join(f"{v:.8f}" for v in data[i]) + "\n")
    return path
