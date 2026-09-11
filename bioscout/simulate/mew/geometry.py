"""MTU geometry: moment arms r(q) and MTU length l_mt(q).

Three providers behind one interface, in increasing speed and decreasing
fidelity:

    OpenSimGeometry    live OpenSim API   accurate, slow, needs opensim
    TableGeometry      MuscleAnalysis     accurate, fast, needs a prior MA run
    SurrogateGeometry  fitted polynomial  fast enough for real time

``OpenSimGeometry`` is also where MuscleParameters are read off the .osim, and
where the XML fallback lives so parameters can be read with no opensim install.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from .mtu import MuscleParameters


class GeometryProvider:
    """Interface. ``muscles`` and ``dofs`` fix the array ordering everywhere."""

    source = "abstract"
    muscles: List[str] = []
    dofs: List[str] = []

    def moment_arms(self, q: pd.DataFrame) -> np.ndarray:
        """(nt, ndof, nm) moment arms in metres."""
        raise NotImplementedError

    def mtu_lengths(self, q: pd.DataFrame) -> np.ndarray:
        """(nt, nm) musculotendon lengths in metres."""
        raise NotImplementedError

    def parameters(self) -> MuscleParameters:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
#  Parameters straight off the .osim  (no opensim needed)
# --------------------------------------------------------------------------- #
_PARAM_TAGS = {
    "f_max": ("max_isometric_force", 1000.0),
    "l_opt": ("optimal_fiber_length", 0.10),
    "l_ts": ("tendon_slack_length", 0.20),
    "alpha_0": ("pennation_angle_at_optimal", 0.0),
    "v_max": ("max_contraction_velocity", 10.0),
}
_MUSCLE_TAGS = ("Thelen2003Muscle", "Millard2012EquilibriumMuscle",
                "Millard2012AccelerationMuscle", "RigidTendonMuscle",
                "DeGrooteFregly2016Muscle", "Schutte1993Muscle_Deprecated")


def read_model_parameters(osim_path, muscles: Optional[Sequence[str]] = None
                          ) -> MuscleParameters:
    """Parse MTU parameters out of an .osim by XML. No OpenSim import required.

    This is deliberately not routed through the OpenSim API: reading a model's
    numbers should never depend on a DLL loading.
    """
    root = ET.parse(str(osim_path)).getroot()
    found: Dict[str, Dict[str, float]] = {}
    for tag in _MUSCLE_TAGS:
        for el in root.iter(tag):
            name = el.get("name")
            if not name:
                continue
            vals = {}
            for key, (xml_tag, default) in _PARAM_TAGS.items():
                node = el.find(xml_tag)
                try:
                    vals[key] = float(node.text.strip()) if node is not None else default
                except (AttributeError, ValueError):
                    vals[key] = default
            found[name] = vals
    if not found:
        raise ValueError(f"no muscles found in {osim_path}")

    names = list(muscles) if muscles else sorted(found)
    missing = [m for m in names if m not in found]
    if missing:
        raise KeyError(f"{len(missing)} muscle(s) not in the model, e.g. {missing[:5]}")

    def col(key):
        return np.array([found[m][key] for m in names], dtype=float)

    n = len(names)
    return MuscleParameters(
        names=names, f_max=col("f_max"), l_opt=col("l_opt"), l_ts=col("l_ts"),
        alpha_0=col("alpha_0"), v_max=col("v_max"),
        tau_act=np.full(n, 0.015), tau_deact=np.full(n, 0.050),
        shape_A=np.full(n, -1.0), strength=np.ones(n),
        source=f"model:{os.path.basename(str(osim_path))}")


# --------------------------------------------------------------------------- #
#  Tables from a bioscout MuscleAnalysis run
# --------------------------------------------------------------------------- #
class TableGeometry(GeometryProvider):
    """Moment arms and lengths from OpenSim MuscleAnalysis .sto output.

    A bioscout trial that has run ``run_ma`` already has this directory:
    ``<trial>/muscle_analysis/`` with ``*_MomentArm_<dof>.sto`` and
    ``*_Length.sto``. Reusing it costs one file read instead of thousands of
    API calls, and it is the SAME geometry the CEINMS run used -- which is what
    makes the tier-2/3 comparison against CEINMS a like-for-like test.
    """

    source = "ma_tables"

    def __init__(self, ma_dir, muscles=None, dofs=None):
        from .io_ports import read_storage
        self.dir = str(ma_dir)
        files = os.listdir(self.dir)

        length_file = next((f for f in files if f.lower().endswith("_length.sto")), None)
        if length_file is None:
            raise FileNotFoundError(f"no *_Length.sto in {self.dir}")
        self._len = read_storage(os.path.join(self.dir, length_file))

        self._ma: Dict[str, pd.DataFrame] = {}
        for f in files:
            low = f.lower()
            if "_momentarm_" not in low or not low.endswith(".sto"):
                continue
            dof = f[low.index("_momentarm_") + len("_momentarm_"):-4]
            self._ma[dof] = read_storage(os.path.join(self.dir, f))

        avail = [c for c in self._len.columns if c != "time"]
        self.muscles = list(muscles) if muscles else avail
        self.dofs = list(dofs) if dofs else sorted(self._ma)
        unknown = [d for d in self.dofs if d not in self._ma]
        if unknown:
            raise KeyError(f"no moment-arm table for DOF(s) {unknown}")

    def _sample(self, df, times, cols):
        t_src = df["time"].to_numpy(float)
        out = np.zeros((len(times), len(cols)))
        for j, c in enumerate(cols):
            if c in df.columns:
                out[:, j] = np.interp(times, t_src, df[c].to_numpy(float))
        return out

    def moment_arms(self, q: pd.DataFrame) -> np.ndarray:
        t = q["time"].to_numpy(float)
        return np.stack([self._sample(self._ma[d], t, self.muscles)
                         for d in self.dofs], axis=1)

    def mtu_lengths(self, q: pd.DataFrame) -> np.ndarray:
        return self._sample(self._len, q["time"].to_numpy(float), self.muscles)

    def parameters(self) -> MuscleParameters:
        raise NotImplementedError(
            "TableGeometry has no model file -- pass the .osim to "
            "read_model_parameters(), or use OpenSimGeometry.")


# --------------------------------------------------------------------------- #
#  Live OpenSim
# --------------------------------------------------------------------------- #
class OpenSimGeometry(GeometryProvider):
    """Query the model directly. Accurate and slow; the reference implementation.

    Imports opensim lazily so the rest of the package stays importable without it.
    """

    source = "opensim_api"

    def __init__(self, osim_path, muscles=None, dofs=None):
        try:
            import opensim as osim                          # noqa: WPS433
        except ImportError as exc:
            raise ImportError(
                "OpenSimGeometry needs the opensim python package. Use "
                "TableGeometry (from a MuscleAnalysis run) or SurrogateGeometry "
                "instead.") from exc
        self._osim = osim
        self.path = str(osim_path)
        self.model = osim.Model(self.path)
        self.state = self.model.initSystem()

        force_set = self.model.getMuscles()
        all_m = [force_set.get(i).getName() for i in range(force_set.getSize())]
        self.muscles = list(muscles) if muscles else all_m
        cs = self.model.getCoordinateSet()
        all_d = [cs.get(i).getName() for i in range(cs.getSize())]
        self.dofs = list(dofs) if dofs else all_d
        self._coords = {n: cs.get(n) for n in all_d}
        self._muscle_objs = [force_set.get(m) for m in self.muscles]

    def _pose(self, row, columns):
        for name in columns:
            if name == "time" or name not in self._coords:
                continue
            c = self._coords[name]
            v = float(row[name])
            if c.getMotionType() == 1:            # rotational: .mot is in degrees
                v = np.deg2rad(v)
            c.setValue(self.state, v, False)
        self.model.assemble(self.state)
        self.model.realizePosition(self.state)

    def _sweep(self, q: pd.DataFrame, want_ma: bool):
        cols = list(q.columns)
        nt, nm, nd = len(q), len(self.muscles), len(self.dofs)
        ma = np.zeros((nt, nd, nm)) if want_ma else None
        lengths = np.zeros((nt, nm))
        for i in range(nt):
            self._pose(q.iloc[i], cols)
            for j, mus in enumerate(self._muscle_objs):
                lengths[i, j] = mus.getLength(self.state)
                if want_ma:
                    for k, d in enumerate(self.dofs):
                        ma[i, k, j] = mus.computeMomentArm(self.state, self._coords[d])
        return ma, lengths

    def moment_arms(self, q):
        return self._sweep(q, True)[0]

    def mtu_lengths(self, q):
        return self._sweep(q, False)[1]

    def parameters(self) -> MuscleParameters:
        return read_model_parameters(self.path, self.muscles)


# --------------------------------------------------------------------------- #
#  Surrogate  --  the real-time path
# --------------------------------------------------------------------------- #
class SurrogateGeometry(GeometryProvider):
    """Polynomial surrogate of r(q) and l_mt(q), fitted from any other provider.

    Fitting is a one-off cost per model; evaluation is a matrix product, which
    is what puts the camera-driven pipeline inside a frame budget. Fit quality
    is reported per muscle so a bad fit is visible rather than silent.
    """

    source = "surrogate"

    def __init__(self, muscles, dofs, degree=3):
        self.muscles, self.dofs, self.degree = list(muscles), list(dofs), int(degree)
        self._coef_len = None
        self._coef_ma = None
        self._q_cols: List[str] = []
        self.fit_r2: Dict[str, float] = {}

    # -- design matrix -----------------------------------------------------
    def _design(self, Q: np.ndarray) -> np.ndarray:
        """[1, q, q^2, ..., q^degree] per DOF. No cross terms: cheap, and the
        dominant curvature in r(q) is single-joint."""
        cols = [np.ones((Q.shape[0], 1))]
        for d in range(1, self.degree + 1):
            cols.append(Q ** d)
        return np.hstack(cols)

    def _q_matrix(self, q: pd.DataFrame) -> np.ndarray:
        return np.column_stack([q[c].to_numpy(float) if c in q.columns
                                else np.zeros(len(q)) for c in self._q_cols])

    # -- fitting -----------------------------------------------------------
    def fit(self, provider: GeometryProvider, q_samples: pd.DataFrame
            ) -> "SurrogateGeometry":
        self._q_cols = [c for c in q_samples.columns if c != "time"]
        X = self._design(self._q_matrix(q_samples))
        L = provider.mtu_lengths(q_samples)                    # (nt, nm)
        R = provider.moment_arms(q_samples)                    # (nt, nd, nm)
        self._coef_len, *_ = np.linalg.lstsq(X, L, rcond=None)
        nd, nm = R.shape[1], R.shape[2]
        self._coef_ma = np.zeros((X.shape[1], nd, nm))
        for k in range(nd):
            self._coef_ma[:, k, :] = np.linalg.lstsq(X, R[:, k, :], rcond=None)[0]

        pred = X @ self._coef_len
        for j, m in enumerate(self.muscles):
            ss_res = float(np.sum((L[:, j] - pred[:, j]) ** 2))
            ss_tot = float(np.sum((L[:, j] - L[:, j].mean()) ** 2))
            self.fit_r2[m] = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
        return self

    def poor_fits(self, threshold=0.99) -> Dict[str, float]:
        return {m: r for m, r in self.fit_r2.items() if r < threshold}

    # -- evaluation --------------------------------------------------------
    def _check(self):
        if self._coef_len is None:
            raise RuntimeError("SurrogateGeometry.fit() has not been called")

    def mtu_lengths(self, q):
        self._check()
        return self._design(self._q_matrix(q)) @ self._coef_len

    def moment_arms(self, q):
        self._check()
        X = self._design(self._q_matrix(q))
        return np.einsum("tp,pdm->tdm", X, self._coef_ma)


def build_geometry(*, osim=None, ma_dir=None, muscles=None, dofs=None,
                   prefer="auto") -> GeometryProvider:
    """Pick a provider: MA tables if present (fast + identical to the CEINMS run),
    else the OpenSim API, and say which was chosen."""
    if prefer in ("auto", "tables") and ma_dir and os.path.isdir(str(ma_dir)):
        try:
            return TableGeometry(ma_dir, muscles=muscles, dofs=dofs)
        except (FileNotFoundError, KeyError):
            if prefer == "tables":
                raise
    if osim is None:
        raise ValueError("no moment-arm tables and no .osim -- cannot build geometry")
    return OpenSimGeometry(osim, muscles=muscles, dofs=dofs)
