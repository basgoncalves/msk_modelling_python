"""bioscout.simulate.mrs.config -- the Misc struct for the KU Leuven Muscle Redundancy
Solver, built in Python and handed to MATLAB as JSON.

One dataclass, one JSON file. Every field maps 1:1 onto a `Misc.<Field>` of
`solveMuscleRedundancy`, so the MATLAB README is the reference for all of them.
Fields left as None are simply not written -- MRS then applies its own default.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Sequence

# python field name -> MATLAB Misc field name
_MISC_MAP = {
    "dof_names": "DofNames_Input",
    "muscle_names": "MuscleNames_Input",
    "ik_files": "IKfile",
    "id_files": "IDfile",
    "analysis_id": "AnalysisID",
    "out_name": "OutName",
    "new_model_file": "newModelFile",
    "mrs_bool": "MRSbool",
    "validation_bool": "ValidationBool",
    "plot_bool": "PlotBool",
    "mesh_frequency": "Mesh_Frequency",
    "f_cutoff_ID": "f_cutoff_ID", "f_order_ID": "f_order_ID",
    "f_cutoff_IK": "f_cutoff_IK", "f_order_IK": "f_order_IK",
    "f_cutoff_LMT": "f_cutoff_LMT", "f_order_LMT": "f_order_LMT",
    "f_cutoff_dM": "f_cutoff_dM", "f_order_dM": "f_order_dM",
    "kT": "kT",
    # weights
    "wlM": "wlM", "wEMG": "wEMG", "wA": "wA", "wTres": "wTres", "wVm": "wVm",
    # EMG-constrained mode
    "emg_constr": "EMGconstr",
    "emg_files": "EMGfile",
    "emg_selection": "EMGSelection",
    "emg_headers": "EMGheaders",
    "emg_correspondence": "EMGFileHeaderCorrespondence",
    "emg_muscle_copies": "EMG_MuscleCopies",
    "emg_bounds": "EMGbounds",
    "bounds_scale_emg": "BoundsScaleEMG",
    # parameter estimation
    "estimate_optimal_fibre_length": "Estimate_OptimalFiberLength",
    "lb_lMo_scaling": "lb_lMo_scaling", "ub_lMo_scaling": "ub_lMo_scaling",
    "estimate_tendon_slack_length": "Estimate_TendonSlackLength",
    "lb_lTs_scaling": "lb_lTs_scaling", "ub_lTs_scaling": "ub_lTs_scaling",
    "estimate_tendon_stiffness": "Estimate_TendonStiffness",
    "lb_kT_scaling": "lb_kT_scaling", "ub_kT_scaling": "ub_kT_scaling",
    "coupled_fibre_length": "Coupled_fiber_length",
    "coupled_slack_length": "Coupled_slack_length",
    "coupled_tendon_stiffness": "Coupled_TendonStiffness",
    # ultrasound tracking
    "us_tracking": "UStracking", "us_files": "USfile", "us_selection": "USSelection",
}


@dataclass
class MRSConfig:
    """Everything one `solveMuscleRedundancy` call needs."""
    # --- required ---------------------------------------------------------
    model_path: str = ""
    ik_files: List[str] = field(default_factory=list)
    id_files: List[str] = field(default_factory=list)
    time: List[float] = field(default_factory=list)       # [t0, t1] (or 2*nTrials)
    out_path: str = ""
    dof_names: List[str] = field(default_factory=list)
    # --- where the toolbox and MATLAB live --------------------------------
    mrs_dir: str = ""
    matlab_exe: str = "matlab"
    # --- optional ---------------------------------------------------------
    muscle_names: Optional[List[str]] = None
    analysis_id: Optional[str] = None
    out_name: Optional[str] = None
    new_model_file: Optional[str] = None
    mrs_bool: bool = True
    validation_bool: bool = False
    plot_bool: bool = False
    mesh_frequency: Optional[int] = 100
    f_cutoff_ID: Optional[float] = None
    f_order_ID: Optional[int] = None
    f_cutoff_IK: Optional[float] = None
    f_order_IK: Optional[int] = None
    f_cutoff_LMT: Optional[float] = None
    f_order_LMT: Optional[int] = None
    f_cutoff_dM: Optional[float] = None
    f_order_dM: Optional[int] = None
    kT: Optional[float] = None
    wlM: Optional[float] = None
    wEMG: Optional[float] = None
    wA: Optional[float] = None
    wTres: Optional[float] = None
    wVm: Optional[float] = None
    # EMG-constrained
    emg_constr: bool = False
    emg_files: Optional[List[str]] = None
    emg_selection: Optional[List[str]] = None
    emg_headers: Optional[List[str]] = None
    emg_correspondence: Optional[List[Sequence[str]]] = None   # n x 2
    emg_muscle_copies: Optional[List[Sequence[str]]] = None    # n x 2
    emg_bounds: Optional[List[float]] = None
    bounds_scale_emg: Optional[List[float]] = None
    # parameter estimation (calibration)
    estimate_optimal_fibre_length: Optional[List[str]] = None
    lb_lMo_scaling: Optional[float] = None
    ub_lMo_scaling: Optional[float] = None
    estimate_tendon_slack_length: Optional[List[str]] = None
    lb_lTs_scaling: Optional[float] = None
    ub_lTs_scaling: Optional[float] = None
    estimate_tendon_stiffness: Optional[List[str]] = None
    lb_kT_scaling: Optional[float] = None
    ub_kT_scaling: Optional[float] = None
    coupled_fibre_length: Optional[List[Sequence[str]]] = None
    coupled_slack_length: Optional[List[Sequence[str]]] = None
    coupled_tendon_stiffness: Optional[List[Sequence[str]]] = None
    # ultrasound
    us_tracking: bool = False
    us_files: Optional[List[str]] = None
    us_selection: Optional[List[str]] = None

    # ----------------------------------------------------------------- API
    @property
    def calibrating(self) -> bool:
        """True when any muscle parameter is being estimated."""
        return any(bool(getattr(self, k)) for k in
                   ("estimate_optimal_fibre_length", "estimate_tendon_slack_length",
                    "estimate_tendon_stiffness"))

    def misc(self) -> dict:
        """The MATLAB `Misc` struct as a plain dict (None fields dropped)."""
        out = {}
        for py_name, mat_name in _MISC_MAP.items():
            v = getattr(self, py_name, None)
            if v is None or (isinstance(v, (list, tuple)) and len(v) == 0):
                continue
            out[mat_name] = list(v) if isinstance(v, tuple) else v
        return out

    def to_json(self, path: str) -> str:
        """Write the config MATLAB reads. Returns the path."""
        payload = {
            "model_path": os.path.abspath(self.model_path),
            "out_path": os.path.abspath(self.out_path),
            "mrs_dir": os.path.abspath(self.mrs_dir) if self.mrs_dir else "",
            "time": [float(t) for t in self.time],
            "Misc": self.misc(),
        }
        for key in ("IKfile", "IDfile", "EMGfile", "USfile"):
            if key in payload["Misc"]:
                payload["Misc"][key] = [os.path.abspath(p) for p in payload["Misc"][key]]
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)
        return path

    def as_dict(self) -> dict:
        return asdict(self)
