"""Everything ``bioscout session`` backs: a capture session on disk.

    session.py          Session / Iteration -- the session.yaml object model
    form.py             the session.yaml form/scaffold
    layout.py           where things live inside a session folder
    paths.py            path resolution helpers
    exportC3D.py        `session export` -- c3d -> markers/GRF/EMG
    motion_detect.py    find a capture's actual movement window
    movement_detector/  `session classify`

``Session``/``Iteration``/``open_session`` are re-exported lazily so
``from bioscout.session import Session`` works without importing the whole
scientific stack at package import time.
"""
_LAZY = {
    "Session": "session", "Iteration": "session", "open_session": "session",
    "find_session_dir": "session", "read_session_yaml": "session",
    "write_session_yaml": "session", "scaffold_session_yaml": "session",
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
# ordering reason bioscout/core/__init__.py does it: `session.py` needs Analyse
# from bioscout.core.analysis, and bioscout.core.analysis re-exports Session
# from `session.py`. That knot only unties if bioscout.utils goes first (it
# loads core.analysis fully, whose Session re-export is lazy). While session.py
# lived in utils/ the parent-package rule guaranteed that for free.
import bioscout.utils as _utils_first   # noqa: F401  (import for ordering)
