"""bioscout.simulate.mrs.runner -- call MATLAB, run the solver, export the results.

BioScout owns the inputs and the outputs; MATLAB only runs the KU Leuven code.
The whole exchange is two files: mrs_config.json in, MRS_Results.mat out.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, Optional

from .config import MRSConfig
from . import io as mrs_io

DRIVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_mrs.m")


# ---------------------------------------------------------------- environment
def find_matlab(exe: Optional[str] = None) -> Optional[str]:
    """Absolute path to the MATLAB executable, or None."""
    for cand in (exe, os.environ.get("BIOSCOUT_MATLAB"), "matlab"):
        if not cand:
            continue
        if os.path.isfile(cand):
            return os.path.abspath(cand)
        found = shutil.which(cand)
        if found:
            return found
    for root in (r"C:\Program Files\MATLAB", r"C:\Program Files (x86)\MATLAB"):
        if os.path.isdir(root):
            for rel in sorted(os.listdir(root), reverse=True):   # newest first
                p = os.path.join(root, rel, "bin", "matlab.exe")
                if os.path.isfile(p):
                    return p
    return None


def find_mrs_dir(path: Optional[str] = None) -> Optional[str]:
    """The MuscleRedundancySolver checkout, or None."""
    for cand in (path, os.environ.get("BIOSCOUT_MRS_DIR")):
        if cand and os.path.isfile(os.path.join(cand, "solveMuscleRedundancy.m")):
            return os.path.abspath(cand)
    return None


def check(matlab_exe: Optional[str] = None, mrs_dir: Optional[str] = None) -> Dict[str, Optional[str]]:
    """What is installed. Printed by `bioscout simulate mrs check`."""
    return {"matlab": find_matlab(matlab_exe), "mrs_dir": find_mrs_dir(mrs_dir),
            "driver": DRIVER if os.path.isfile(DRIVER) else None}


# ------------------------------------------------------------------- the run
def run(cfg: MRSConfig, replace: bool = True, verbose: bool = True) -> Dict[str, str]:
    """Write the config, run MATLAB, export .sto files. Returns {key: path}."""
    matlab = find_matlab(cfg.matlab_exe)
    if not matlab:
        raise RuntimeError("MATLAB not found. Set BIOSCOUT_MATLAB or pass --matlab.")
    mrs_dir = find_mrs_dir(cfg.mrs_dir)
    if not mrs_dir:
        raise RuntimeError(
            "MuscleRedundancySolver not found. Clone "
            "https://github.com/KULeuvenNeuromechanics/MuscleRedundancySolver "
            "and set BIOSCOUT_MRS_DIR or pass --mrs-dir.")
    cfg.mrs_dir = mrs_dir

    out = os.path.abspath(cfg.out_path)
    os.makedirs(out, exist_ok=True)
    mat = os.path.join(out, "MRS_Results.mat")
    if os.path.isfile(mat) and not replace:
        if verbose:
            print(f"[MRS] results already exist: {mat}")
        return mrs_io.export(mat, out)

    cfg_file = cfg.to_json(os.path.join(out, "mrs_config.json"))
    cmd = [matlab, "-batch",
           f"addpath('{os.path.dirname(DRIVER)}'); run_mrs('{cfg_file}')"]
    if verbose:
        print(f"[MRS] {' '.join(cmd)}")

    log = os.path.join(out, "mrs_matlab.log")
    with open(log, "w", errors="replace") as fh:
        proc = subprocess.Popen(cmd, cwd=out, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in proc.stdout:                      # stream and log
            fh.write(line)
            if verbose:
                print(line.rstrip())
        proc.wait()

    if proc.returncode != 0 or not os.path.isfile(mat):
        raise RuntimeError(f"MRS failed (exit {proc.returncode}). See {log}")

    files = mrs_io.export(mat, out)
    if verbose:
        print(f"[MRS] wrote {len(files)} result file(s) in {out}")
    return files
