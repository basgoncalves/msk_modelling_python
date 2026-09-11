"""Everything ``bioscout session`` backs: a capture session on disk.

    recording.py        Session   -- one recording-session folder (bs.Session)
    iteration.py        Iteration -- one model iteration: the runnable unit
    config.py           session.yaml: read / write / scaffold, EMG maps, calibration
    layout.py           where things live inside a session folder
    validation.py       trial-folder checks (GUI)
    form.py             the session.yaml form/scaffold
    paths.py            path resolution helpers
    exportC3D.py        `session export` -- c3d -> markers/GRF/EMG
    motion_detect.py    find a capture's actual movement window
    movement_detector/  `session classify`

``Session``/``Iteration``/... are re-exported lazily so
``from bioscout.session import Session`` works without importing the whole
scientific stack at package import time.
"""
_LAZY = {
    "Session": "recording", "find_session_dir": "recording",
    "Iteration": "iteration",
    "read_session_yaml": "config", "write_session_yaml": "config",
    "scaffold_session_yaml": "config", "load_session_yaml": "config",
}


def __getattr__(name):                       # PEP 562
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    return getattr(importlib.import_module(f"{__name__}.{mod}"), name)


def __dir__():
    return sorted(list(globals()) + list(_LAZY))

# bioscout.utils is imported before anything in this package runs, for the same
# ordering reason bioscout/core/__init__.py does it: `iteration.py` needs Analyse
# from bioscout.core.analysis, and bioscout.core.analysis re-exports Session
# from this package. That knot only unties if bioscout.utils goes first (it
# loads core.analysis fully, whose Session re-export is lazy). While session.py
# lived in utils/ the parent-package rule guaranteed that for free.
import bioscout.utils as _utils_first   # noqa: F401  (import for ordering)
