"""
movement_detector — detecting and segmenting sports movements.

Two independent paths, for two kinds of input:

**Video / 2-D pose** — frame-level segmentation of running, walking, jumping,
squatting, side-step cut, shuffle, deceleration and backward gait from pose
landmark time-series::

    from bioscout.session.movement_detector import detect_segments, DetectorConfig
    segments = detect_segments(landmarks)

**Marker-based mocap** — whole-TRIAL classification from the markers and
ground reaction forces BioScout exports into
``<session>/2_experimental/<trial>/``. Answers "what task is this trial?"
rather than "what is happening in this frame", so a project can check its
trials against their filenames::

    from bioscout.session.movement_detector import classify_trial
    label, conf, why, feats = classify_trial(exp_dir, body_mass=61.3)

Thresholds for the mocap path are SI (m, s, body weights) and live in
``MocapConfig``; the video path's are pixels/frame in ``DetectorConfig``.

**Mesh conversion** — a small utility for the surface meshes that come out of
phone scans and photogrammetry, so they can be used as OpenSim geometry::

    from bioscout.session.movement_detector import convert_to_stl
    convert_to_stl("3DModel.obj", scale=0.001)   # mm -> m, writes 3DModel.stl

See ``bioscout.session.movement_detector.mesh_convert``.

**Body mesh from video** — a fixed camera, a subject turning on the spot, and a
shape-from-silhouette carve gives the closed mesh that ``mesh_rig`` rigs::

    from bioscout.session.movement_detector import carve_from_video, rig_mesh
    res = carve_from_video("turn.mp4", "subject01/body.stl",
                           "front=0,right=3.1,back=6.4,left=9.2",
                           CarveConfig(target_height=1.81))
    rig_mesh(res.mesh_path, out_dir="subject01", name="bas")

See ``bioscout.session.movement_detector.mesh_from_video``.
"""

from .detector import MotionSegment, DetectorConfig, detect_segments
from .gap_fill import fill_pose_gaps
from .mocap import (
    detect_window,
    segment_trial,
    TaskSegment,
    contact_feet,
    foot_events_from_markers,
    gait_cycles,
    plot_trial_tasks,
    TASK_COLOURS,
    FOOT_COLOURS,
    MOCAP_TASK_LABELS,
    MocapConfig,
    TrialFeatures,
    classify_trial,
    classify_features,
    extract_trial_features,
    read_trc,
    read_grf,
)

__all__ = [
    # video / 2-D pose
    "MotionSegment",
    "DetectorConfig",
    "detect_segments",
    "fill_pose_gaps",
    # marker-based mocap
    "MOCAP_TASK_LABELS",
    "MocapConfig",
    "classify_session",
    "TrialFeatures",
    "classify_trial",
    "classify_features",
    "extract_trial_features",
    "detect_window",
    "segment_trial",
    "TaskSegment",
    "contact_feet",
    "foot_events_from_markers",
    "gait_cycles",
    "prepare_cycle_runs",
    "write_cycle_files",
    "plot_trial_tasks",
    "TASK_COLOURS",
    "FOOT_COLOURS",
    "read_trc",
    "read_grf",
    # mesh conversion
    "convert_to_stl",
    "obj_to_stl",
    "convert_dir",
    "read_obj",
    "write_stl",
    # body mesh from a turntable video
    "carve_from_video",
    "CarveConfig",
    "CarveResult",
    "ViewSpec",
    "STANDARD_VIEWS",
    "parse_views",
    "hull_bias",
    "silhouette",
    "carve_visual_hull",
    "surface_nets",
    "regularise_occupancy",
    "is_watertight",
    "make_segmenter",
]


def prepare_cycle_runs(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.cycle_runs."""
    from .cycle_runs import prepare_cycle_runs as _f
    return _f(*a, **k)


def write_cycle_files(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.cycle_runs."""
    from .cycle_runs import write_cycle_files as _f
    return _f(*a, **k)


def classify_session(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.session."""
    from .session import classify_session as _f
    return _f(*a, **k)


# --- mesh conversion (lazy: pyvista is only needed for non-OBJ inputs) -------
def convert_to_stl(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_convert."""
    from .mesh_convert import convert_to_stl as _f
    return _f(*a, **k)


def obj_to_stl(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_convert."""
    from .mesh_convert import obj_to_stl as _f
    return _f(*a, **k)


def convert_dir(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_convert."""
    from .mesh_convert import convert_dir as _f
    return _f(*a, **k)


def read_obj(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_convert."""
    from .mesh_convert import read_obj as _f
    return _f(*a, **k)


def write_stl(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_convert."""
    from .mesh_convert import write_stl as _f
    return _f(*a, **k)


# --- STL -> OSIM auto-rig ---------------------------------------------------
# Lazy again: mesh_rig imports numpy and parses OpenSim XML, and most callers
# of this package only want the detectors.
__all__ += [
    "rig_mesh",
    "RigConfig",
    "RigResult",
    "ModelLandmarks",
    "read_model_landmarks",
    "default_base_model",
    "write_osim",
]


def rig_mesh(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_rig."""
    from .mesh_rig import rig_mesh as _f
    return _f(*a, **k)


def read_model_landmarks(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_rig."""
    from .mesh_rig import read_model_landmarks as _f
    return _f(*a, **k)


def default_base_model(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_rig."""
    from .mesh_rig import default_base_model as _f
    return _f(*a, **k)


def write_osim(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_rig."""
    from .mesh_rig import write_osim as _f
    return _f(*a, **k)


#: attribute name -> submodule it lives in. One dict, one ``__getattr__``:
#: a module may define only one, and a second definition silently shadows the
#: first, which is how ``RigConfig`` stops resolving.
_LAZY_CLASSES = {
    "RigConfig": "mesh_rig",
    "RigResult": "mesh_rig",
    "ModelLandmarks": "mesh_rig",
    "CarveConfig": "mesh_from_video",
    "CarveResult": "mesh_from_video",
    "ViewSpec": "mesh_from_video",
    "STANDARD_VIEWS": "mesh_from_video",
}


def __getattr__(name):
    """Expose the submodules' dataclasses without importing them at package import."""
    mod = _LAZY_CLASSES.get(name)
    if mod is not None:
        import importlib
        return getattr(importlib.import_module(f".{mod}", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_LAZY_CLASSES))


# --- body mesh from a turntable video (lazy: opencv + mediapipe at call time) -
def carve_from_video(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import carve_from_video as _f
    return _f(*a, **k)


def parse_views(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import parse_views as _f
    return _f(*a, **k)


def hull_bias(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import hull_bias as _f
    return _f(*a, **k)


def silhouette(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import silhouette as _f
    return _f(*a, **k)


def carve_visual_hull(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import carve_visual_hull as _f
    return _f(*a, **k)


def surface_nets(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import surface_nets as _f
    return _f(*a, **k)


def regularise_occupancy(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import regularise_occupancy as _f
    return _f(*a, **k)


def is_watertight(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import is_watertight as _f
    return _f(*a, **k)


def make_segmenter(*a, **k):
    """Lazy re-export; see bioscout.session.movement_detector.mesh_from_video."""
    from .mesh_from_video import make_segmenter as _f
    return _f(*a, **k)
