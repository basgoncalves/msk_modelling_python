"""bioscout.simulate.mrs.cli -- `bioscout simulate mrs check` and `bioscout simulate mrs run <trial>`."""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence

from .config import MRSConfig
from . import runner


# ------------------------------------------------------------------ helpers
def _sto_labels(path: str) -> List[str]:
    """Column labels of a .mot/.sto (the row after endheader)."""
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.strip().lower() == "endheader":
                return next(fh).split()
    return []


def _time_range(path: str):
    """(first, last) time value of a .mot/.sto."""
    rows = []
    with open(path, errors="replace") as fh:
        seen = False
        for line in fh:
            if seen:
                parts = line.split()
                if parts:
                    rows.append(float(parts[0]))
            elif line.strip().lower() == "endheader":
                seen = True
                next(fh)                       # skip the label row
    return (rows[0], rows[-1]) if rows else (0.0, 1.0)


# Coordinates MRS must not be given: the pelvis is driven by residuals, the
# trunk/arms by torque actuators, and `*_beta` is a knee constraint coordinate,
# not a DOF a muscle spans. Passing any of them makes the solve unsolvable
# (a moment with no muscle to produce it). Override with --dofs.
_SKIP_DOFS = ("pelvis_", "lumbar_", "arm_", "elbow_", "wrist_", "pro_sup",
              "shoulder_", "thorax_")


def _dofs_from_id(id_file: str, muscle_only: bool = True) -> List[str]:
    """Coordinate names behind the ID moment/force columns.

    With `muscle_only` (the default) the non-muscle-driven coordinates are
    dropped -- what is left is the lower limb, which is what MRS can solve."""
    out = []
    for lab in _sto_labels(id_file):
        if lab.lower() == "time":
            continue
        for suffix in ("_moment", "_force"):
            if lab.endswith(suffix):
                out.append(lab[: -len(suffix)])
                break
    if muscle_only:
        out = [d for d in out
               if not d.endswith("_beta") and not d.startswith(_SKIP_DOFS)]
    return out


def config_for_trial(trial_dir: str, dofs: Optional[Sequence[str]] = None,
                     muscles: Optional[Sequence[str]] = None,
                     time: Optional[Sequence[float]] = None,
                     out_dir: Optional[str] = None,
                     model: Optional[str] = None,
                     ik: Optional[str] = None, id_file: Optional[str] = None,
                     **kw) -> MRSConfig:
    """Build an MRSConfig from a BioScout trial folder."""
    trial_dir = os.path.abspath(trial_dir)
    E = "external_biomechanics"
    ik = ik or os.path.join(trial_dir, E, "joint_angles.mot")
    id_file = id_file or os.path.join(trial_dir, E, "inverse_dynamics.sto")
    for f in (ik, id_file):
        if not os.path.isfile(f):
            raise FileNotFoundError(f"missing input: {f} (run IK/ID first)")
    if not model:
        from glob import glob
        hits = sorted(glob(os.path.join(trial_dir, "*.osim"))) or \
               sorted(glob(os.path.join(trial_dir, "..", "*.osim")))
        if not hits:
            raise FileNotFoundError("no .osim found -- pass --model")
        model = hits[0]

    return MRSConfig(
        model_path=os.path.abspath(model),
        ik_files=[ik], id_files=[id_file],
        time=list(time) if time else list(_time_range(ik)),
        out_path=out_dir or os.path.join(trial_dir, "mrs"),
        dof_names=list(dofs) if dofs else _dofs_from_id(id_file),
        muscle_names=list(muscles) if muscles else None,
        **kw)


# --------------------------------------------------------------------- main
def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="bioscout simulate mrs",
        description="Muscle Redundancy Solver (KU Leuven) via MATLAB.")
    sub = p.add_subparsers(dest="action")

    sub.add_parser("check", help="is MATLAB + the toolbox reachable?")

    r = sub.add_parser("run", help="solve one trial")
    r.add_argument("trial", help="trial folder")
    r.add_argument("--model", help=".osim (default: found in the trial folder)")
    r.add_argument("--dofs", nargs="+", help="coordinates (default: all in the ID file)")
    r.add_argument("--muscles", nargs="+", help="muscles (default: all spanning the DOFs)")
    r.add_argument("--time", nargs=2, type=float, metavar=("T0", "T1"))
    r.add_argument("--out", help="output folder (default: <trial>/mrs)")
    r.add_argument("--mesh", type=int, default=100, help="mesh points per second")
    r.add_argument("--emg", help="EMG .mot -> EMG-constrained solve")
    r.add_argument("--emg-muscles", nargs="+", help="muscles driven by EMG")
    r.add_argument("--calibrate", nargs="*", metavar="MUSCLE",
                   help="estimate lMo + lTs (no names = every included muscle)")
    r.add_argument("--estimate-kT", nargs="*", metavar="MUSCLE",
                   help="also estimate tendon stiffness")
    r.add_argument("--matlab", help="path to matlab.exe")
    r.add_argument("--mrs-dir", help="MuscleRedundancySolver checkout")
    r.add_argument("--replace", action="store_true", help="rerun even if results exist")

    ns = p.parse_args(list(argv) if argv is not None else sys.argv[1:])
    if not ns.action:
        p.print_help()
        return 0

    if ns.action == "check":
        st = runner.check()
        for k, v in st.items():
            print(f"{k:8s}: {v or 'NOT FOUND'}")
        return 0 if all(st.values()) else 1

    cfg = config_for_trial(
        ns.trial, dofs=ns.dofs, muscles=ns.muscles, time=ns.time,
        out_dir=ns.out, model=ns.model, mesh_frequency=ns.mesh,
        matlab_exe=ns.matlab or "matlab", mrs_dir=ns.mrs_dir or "")

    if ns.emg:
        cfg.emg_constr = True
        cfg.emg_files = [os.path.abspath(ns.emg)]
        cfg.emg_selection = ns.emg_muscles or None
        cfg.emg_bounds = [-0.1, 0.1]
        cfg.bounds_scale_emg = [0.5, 2.0]

    if ns.calibrate is not None:
        names = ns.calibrate or (cfg.muscle_names or [])
        if not names:
            p.error("--calibrate needs muscle names (or set --muscles): MRS "
                    "estimates parameters for named muscles only")
        cfg.estimate_optimal_fibre_length = names
        cfg.estimate_tendon_slack_length = names
        cfg.lb_lMo_scaling, cfg.ub_lMo_scaling = 0.7, 1.5
        cfg.lb_lTs_scaling, cfg.ub_lTs_scaling = 0.7, 1.5
    if ns.estimate_kT is not None:
        names = ns.estimate_kT or (cfg.muscle_names or [])
        if not names:
            p.error("--estimate-kT needs muscle names (or set --muscles)")
        cfg.estimate_tendon_stiffness = names
        cfg.lb_kT_scaling, cfg.ub_kT_scaling = 0.2, 1.2

    files = runner.run(cfg, replace=ns.replace)
    for k, v in sorted(files.items()):
        print(f"  {k:28s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
