"""bioscout.simulate.mrs.io -- MRS_Results.mat -> OpenSim .sto + a parameter JSON.

MRS returns one struct per sub-problem (`genericMRS`, `MTE`, `validationMRS`,
...). Every one of them is exported, so the file name tells you which solve it
came from: MRS_<problem>_activation.sto, MRS_<problem>_force.sto.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

# numpy/scipy are imported inside the functions so that `bioscout simulate mrs check`
# works in an environment where the scientific stack is not installed.


def _load(mat_path: str):
    from scipy.io import loadmat
    return loadmat(mat_path, struct_as_record=False, squeeze_me=True)


def _fields(obj) -> List[str]:
    return list(getattr(obj, "_fieldnames", []))


def _muscle_names(mat) -> List[str]:
    """Muscle order from DatStore (first trial)."""
    import numpy as np
    ds = mat.get("DatStore")
    ds = ds[0] if isinstance(ds, np.ndarray) and ds.size else ds
    names = getattr(ds, "MuscleNames", None)
    return [str(n) for n in np.atleast_1d(names)] if names is not None else []


def write_sto(path: str, time: np.ndarray, data: np.ndarray, labels: List[str],
              name: str = "MRS") -> str:
    """data: (nRows, nCols) aligned with `labels`."""
    import numpy as np
    data = np.atleast_2d(np.asarray(data, dtype=float))
    time = np.asarray(time, dtype=float).ravel()
    if data.shape[0] != time.size and data.shape[1] == time.size:
        data = data.T                                   # MRS is nMuscles x nMesh
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(f"{name}\nversion=1\nnRows={data.shape[0]}\n"
                 f"nColumns={data.shape[1] + 1}\ninDegrees=no\nendheader\n")
        fh.write("time\t" + "\t".join(labels) + "\n")
        for i, t in enumerate(time):
            fh.write(f"{t:.8f}\t" + "\t".join(f"{v:.8f}" for v in data[i]) + "\n")
    return path


def export(mat_path: str, out_dir: str | None = None) -> Dict[str, str]:
    """Export every solved problem in MRS_Results.mat. Returns {key: file}."""
    import numpy as np
    out_dir = out_dir or os.path.dirname(os.path.abspath(mat_path))
    mat = _load(mat_path)
    res = mat["Results"]
    muscles = _muscle_names(mat)
    written: Dict[str, str] = {}

    time_by_problem = {p: np.atleast_1d(getattr(res.Time, p)).ravel()
                       for p in _fields(getattr(res, "Time", object()))}

    for src, tag, unit_labels in (("MActivation", "activation", muscles),
                                  ("MExcitation", "excitation", muscles),
                                  ("TForce", "force", muscles),
                                  ("lMtildeopt", "fibre_length_norm", muscles),
                                  ("RActivation", "reserves", None)):
        block = getattr(res, src, None)
        if block is None:
            continue
        for problem in _fields(block):
            arr = np.asarray(getattr(block, problem), dtype=float)
            if arr.size == 0:
                continue
            t = time_by_problem.get(problem)
            if t is None:
                continue
            n = arr.shape[0] if arr.shape[0] != t.size else arr.shape[1] if arr.ndim > 1 else 1
            labels = list(unit_labels) if unit_labels else [f"reserve_{i+1}" for i in range(n)]
            if len(labels) != n:
                labels = [f"col_{i+1}" for i in range(n)]
            # MRS gives mesh points for states and one fewer for controls
            if arr.shape[-1] != t.size and arr.shape[0] != t.size:
                t = t[:arr.shape[-1]]
            f = os.path.join(out_dir, f"MRS_{problem}_{tag}.sto")
            written[f"{problem}_{tag}"] = write_sto(f, t, arr, labels, name=f"MRS {problem}")

    # calibrated parameters (only present when estimating)
    par = getattr(res, "Param", None)
    if par is not None:
        out = {}
        for p in _fields(par):
            v = getattr(par, p)
            out[p] = np.asarray(v).tolist() if not hasattr(v, "_fieldnames") else \
                {k: np.asarray(getattr(v, k)).tolist() for k in _fields(v)}
        out["muscle_names"] = muscles
        f = os.path.join(out_dir, "MRS_parameters.json")
        with open(f, "w") as fh:
            json.dump(out, fh, indent=2)
        written["parameters"] = f

    return written
