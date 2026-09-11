"""Data contracts for :mod:`mew`.

Everything that crosses a module boundary is one of these. They are plain
dataclasses with no dependency beyond numpy, so the contract can be read and
tested without OpenSim, torch or bioscout installed.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Dict, List, Optional, Sequence

import numpy as np


# --------------------------------------------------------------------------- #
#  Tiers
# --------------------------------------------------------------------------- #
class Tier(IntEnum):
    """How much information the solve actually had.

    Higher is better. :class:`~mew.analyser.Mew` picks
    the highest tier the inputs support unless one is pinned.
    """
    KINEMATICS_ONLY = 0    # moments from a surrogate MomentSource
    STATIC_OPT = 1         # measured GRF -> real ID, no EMG
    EMG_INFORMED = 2       # + EMG tracking, generic (height/mass-scaled) parameters
    CALIBRATED_HYBRID = 3  # + subject-calibrated MTU parameters

    @property
    def label(self) -> str:
        return {
            0: "kinematics_only",
            1: "static_optimisation",
            2: "emg_informed",
            3: "calibrated_hybrid",
        }[int(self)]

    @property
    def nominal_confidence(self) -> float:
        """Prior confidence for the tier, before residual-based adjustment."""
        return {0: 0.35, 1: 0.60, 2: 0.80, 3: 0.92}[int(self)]


# --------------------------------------------------------------------------- #
#  Subject
# --------------------------------------------------------------------------- #
@dataclass
class SubjectSpec:
    """The minimum viable description of a participant.

    ``height`` (m) and ``mass`` (kg) plus ``model`` is the whole required input
    set for tier 0 — everything else refines it.
    """
    model: str                                  # path to the base .osim
    height: Optional[float] = None              # m
    mass: Optional[float] = None                # kg
    name: str = "subject"
    sex: Optional[str] = None                   # only used by optional regressors
    theta_file: Optional[str] = None            # calibrated parameters (calibrate.py)

    def __post_init__(self):
        self.model = str(self.model)
        if self.height is not None:
            self.height = float(self.height)
            if not 0.5 < self.height < 2.6:
                raise ValueError(
                    f"height={self.height} looks wrong -- it must be in METRES")
        if self.mass is not None:
            self.mass = float(self.mass)
            if not 10.0 < self.mass < 300.0:
                raise ValueError(f"mass={self.mass} looks wrong -- it must be in KG")

    @property
    def model_hash(self) -> str:
        """Short content hash of the .osim, recorded in provenance."""
        try:
            h = hashlib.sha1()
            with open(self.model, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 16), b""):
                    h.update(chunk)
            return h.hexdigest()[:12]
        except OSError:
            return "unknown"

    @property
    def bmi(self) -> Optional[float]:
        if self.height and self.mass:
            return self.mass / (self.height ** 2)
        return None


# --------------------------------------------------------------------------- #
#  Trial inputs
# --------------------------------------------------------------------------- #
@dataclass
class TrialInputs:
    """One trial's signals. Only ``kinematics`` is required.

    Paths OR in-memory arrays are both accepted: the loader in
    :mod:`mew.io_ports` normalises either into ``(times, DataFrame)``.
    """
    kinematics: object                      # ik .mot path / DataFrame  (REQUIRED)
    moments: object = None                  # id .sto path / DataFrame  (measured ID)
    grf: object = None                      # grf .mot path / DataFrame
    emg: object = None                      # normalised emg .mot path / DataFrame
    moment_arms: object = None              # MuscleAnalysis dir / dict of DataFrames
    emg_map: Dict[str, List[str]] = field(default_factory=dict)  # channel -> [muscles]
    time_range: Optional[Sequence[float]] = None
    side: str = "both"                      # "r" | "l" | "both"
    trial_type: Optional[str] = None        # walking / running / squat ... (for templates)
    name: str = "trial"

    def available(self) -> Dict[str, bool]:
        return {
            "kinematics": self.kinematics is not None,
            "moments": self.moments is not None,
            "grf": self.grf is not None,
            "emg": self.emg is not None and bool(self.emg_map),
            "moment_arms": self.moment_arms is not None,
        }


# --------------------------------------------------------------------------- #
#  Provenance
# --------------------------------------------------------------------------- #
@dataclass
class Provenance:
    """What every input actually was. This is what makes a result defensible."""
    model: str = ""
    model_hash: str = ""
    subject: str = ""
    trial: str = ""
    tier: str = ""
    moment_source: str = ""          # measured_id | predicted_grf | scaled_template
    parameter_source: str = ""       # calibrated:<file> | scaled:height_mass | model_default
    geometry_source: str = ""        # opensim_api | ma_tables | surrogate
    emg_channels: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    solver: str = ""
    warnings: List[str] = field(default_factory=list)
    version: str = "0.1.0-draft"

    def to_json(self, indent=2) -> str:
        return json.dumps(asdict(self), indent=indent)


# --------------------------------------------------------------------------- #
#  Result
# --------------------------------------------------------------------------- #
@dataclass
class MuscleForceResult:
    """Muscle forces plus everything needed to judge them."""
    times: np.ndarray                       # (nt,)
    muscles: List[str]                      # (nm,)
    forces: np.ndarray                      # (nt, nm)  Newtons
    activations: np.ndarray                 # (nt, nm)  0-1
    tier: Tier = Tier.KINEMATICS_ONLY
    dofs: List[str] = field(default_factory=list)
    moment_residual: Optional[np.ndarray] = None   # (nt, ndof) the RESERVES: see below
    moment_target: Optional[np.ndarray] = None     # (nt, ndof) Nm
    #: Per-frame MTU state from the solve, each (nt, nm): fibre_length,
    #: norm_fibre_length, tendon_length, norm_tendon_length, mtu_length,
    #: norm_fibre_velocity, pennation, force_active, force_passive.
    series: Dict[str, np.ndarray] = field(default_factory=dict)
    provenance: Provenance = field(default_factory=Provenance)
    _confidence: Optional[float] = None

    # ---- reserves ---------------------------------------------------------
    @property
    def reserves(self) -> Optional[np.ndarray]:
        """The reserve actuators: what the muscles could NOT produce, per DOF.

        Same array as ``moment_residual``, named for what it is downstream. A
        reserve is a GENERALISED force -- a moment (Nm) at a rotational
        coordinate, a force (N) at a translational one -- which is why the file
        it is written to mixes units, exactly as OpenSim's own force files do.
        """
        return self.moment_residual

    @property
    def reserve_names(self) -> List[str]:
        return [f"{d}_reserve" for d in self.dofs]

    # ---- confidence -------------------------------------------------------
    @property
    def confidence(self) -> float:
        """0-1. Tier prior, degraded by how much moment the muscles could not explain."""
        if self._confidence is not None:
            return self._confidence
        c = self.tier.nominal_confidence
        if self.moment_residual is not None and self.moment_target is not None:
            tgt = np.abs(self.moment_target)
            scale = np.maximum(np.percentile(tgt, 95, axis=0), 1e-6)
            rel = np.mean(np.abs(self.moment_residual) / scale)
            c *= float(np.clip(1.0 - 2.0 * rel, 0.05, 1.0))
        return float(np.clip(c, 0.0, 1.0))

    @confidence.setter
    def confidence(self, v):
        self._confidence = None if v is None else float(v)

    # ---- convenience ------------------------------------------------------
    def to_dataframe(self, what="forces"):
        import pandas as pd
        arr = {"forces": self.forces, "activations": self.activations}[what]
        df = pd.DataFrame(arr, columns=self.muscles)
        df.insert(0, "time", self.times)
        return df

    def peak_forces(self) -> Dict[str, float]:
        return dict(zip(self.muscles, np.max(self.forces, axis=0).tolist()))

    def summary(self) -> str:
        res = ""
        if self.moment_residual is not None:
            res = f", mean |residual| {np.mean(np.abs(self.moment_residual)):.2f} Nm"
        return (f"{self.provenance.trial or 'trial'}: {len(self.muscles)} muscles, "
                f"{len(self.times)} frames, tier {self.tier.label} "
                f"(confidence {self.confidence:.2f}){res}")

    #: filename -> (series key, header name). One concern per file, named the
    #: way CEINMS names them so existing eyes and scripts recognise them.
    OUTPUT_FILES = (
        ("MuscleForces.sto", "forces", "MuscleForces"),
        ("MuscleForcesActive.sto", "force_active", "MuscleForcesActive"),
        ("MuscleForcesPassive.sto", "force_passive", "MuscleForcesPassive"),
        ("Activations.sto", "activations", "Activations"),
        ("FibreLengths.sto", "fibre_length", "FibreLengths"),
        ("NormFibreLengths.sto", "norm_fibre_length", "NormFibreLengths"),
        ("NormFibreVelocities.sto", "norm_fibre_velocity", "NormFibreVelocities"),
        ("TendonLengths.sto", "tendon_length", "TendonLengths"),
        ("NormTendonLengths.sto", "norm_tendon_length", "NormTendonLengths"),
        ("MTULengths.sto", "mtu_length", "MTULengths"),
        ("PennationAngles.sto", "pennation", "PennationAngles"),
    )

    def array(self, key) -> Optional[np.ndarray]:
        """One output array by name, whether it is a field or a series entry."""
        if key == "forces":
            return self.forces
        if key == "activations":
            return self.activations
        return self.series.get(key)

    def write_outputs(self, out_dir, *, include=None, provenance=True) -> List[str]:
        """Write every output as its own .sto in ``out_dir``. Returns the paths.

        One quantity per file rather than one wide file: that is how CEINMS and
        OpenSim's MuscleAnalysis both do it, it keeps units consistent within a
        file, and it means a downstream reader never has to know which columns
        of a mixed file it wants.

        Reserves get their own file too (``Reserves.sto``), because they are
        indexed by COORDINATE, not by muscle -- a different number of columns
        with different names, which is precisely why they cannot share a file
        with the muscle quantities.
        """
        import json as _json
        from .io_ports import write_sto
        out_dir = str(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        written = []

        for fname, key, header in self.OUTPUT_FILES:
            if include is not None and key not in include:
                continue
            arr = self.array(key)
            if arr is None:
                continue
            written.append(write_sto(os.path.join(out_dir, fname), self.times,
                                     self.muscles, arr, name=header))

        if self.reserves is not None and (include is None or "reserves" in include):
            written.append(write_sto(
                os.path.join(out_dir, "Reserves.sto"), self.times,
                self.reserve_names, self.reserves, name="Reserves"))
        if self.moment_target is not None and (include is None or "moments" in include):
            written.append(write_sto(
                os.path.join(out_dir, "MomentsTracked.sto"), self.times,
                list(self.dofs), self.moment_target, name="MomentsTracked"))

        if provenance:
            p = os.path.join(out_dir, "provenance.json")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(self.provenance.to_json())
            written.append(p)
        return written

    def write_sto(self, path, extra=False):
        """Write forces in the CEINMS-compatible .sto that bioscout already reads."""
        from .io_ports import write_sto
        write_sto(path, self.times, self.muscles, self.forces, name="MuscleForces")
        if extra:
            stem, _ = os.path.splitext(str(path))
            write_sto(stem + "_activations.sto", self.times, self.muscles,
                      self.activations, name="Activations")
            with open(stem + "_provenance.json", "w", encoding="utf-8") as fh:
                fh.write(self.provenance.to_json())
        return str(path)
