"""
mesh_from_video — a closed body mesh from a fixed-camera turntable video.

The capture is the cheapest one there is: put a phone on a tripod, have the
subject stand on the spot and turn through a full circle, stopping briefly at a
few known angles. This module turns that clip into one watertight STL, which
:mod:`bioscout.session.movement_detector.mesh_rig` then rigs onto an OpenSim skeleton::

    from bioscout.session.movement_detector import carve_from_video, rig_mesh
    res = carve_from_video("turn.mp4", "subject01/body.stl",
                           config=CarveConfig(target_height=1.81))
    rig_mesh(res.mesh_path, out_dir="subject01", name="bas")

Command line::

    python -m bioscout.session.movement_detector.mesh_from_video turn.mp4 \\
        --views front=0,q1@45=1.6,right=3.1,q3@135=4.7 --height 1.81 -o body.stl

Choosing views
--------------
Azimuths 180 apart are **geometrically redundant**: under orthographic
projection the silhouette at 0 and at 180 pin the body between the same pair of
planes, so front/right/back/left is only *two* distinct constraints and carves a
limb 27% too fat. Spread the views over a **half** turn instead — 0/45/90/135
costs the same four stops and cuts that to 5%. Eight stops over 180 reach 1.3%.
See :func:`hull_bias`. (Views past 180 still earn their keep for robustness,
since ``tolerance`` votes over all of them, but they add no new geometry.)

Method
------
**Shape from silhouette** (the visual hull). Each view's silhouette back-projects
to a cone containing the subject; the intersection of the cones over a full turn
is a closed solid that bounds the true body. Concretely:

1. **Grab** the frames the caller named, each with the azimuth the subject was
   facing at that moment (:class:`ViewSpec`).
2. **Segment** the person in each frame. MediaPipe is the default, but note it
   reorganised at 1.0: ``mp.solutions.selfie_segmentation`` (weights bundled in
   the wheel) was removed, and the replacement Tasks API needs a ``.tflite``
   fetched from Google. So the backend is pluggable — ``"background"`` needs no
   model at all, only a frame of the empty scene, and ``mask_dir`` accepts masks
   from any other tool. The mask is then cleaned: threshold, largest connected
   component, hole fill.
3. **Register** the views to each other. The camera never moves and the subject
   turns on the spot, so one scale (metres per pixel, from ``target_height``),
   one ground row and one rotation-axis column serve every view.
4. **Carve** a voxel grid: a voxel survives if it projects inside the silhouette
   in every view (``tolerance`` allows a few disagreements, which rescues a run
   where one mask clipped a hand).
5. **Surface** the result. A Euclidean distance transform turns the binary
   occupancy into a signed field, and naive surface nets extracts its zero level
   as a closed, manifold, quad-derived triangle mesh — smoother than a blocky
   voxel boundary and, unlike marching cubes, small enough to carry here rather
   than take on scikit-image as a dependency.
6. **Smooth and write** with ``mesh_rig``'s Taubin pass and fast STL writer, so
   the output is byte-identical in style to the rest of the mesh pipeline.

What this cannot do
-------------------
A visual hull is an *upper bound* on the body. Anything the silhouette never
reveals stays filled in:

* **Concavities never show.** The small of the back, the gap under the chin and
  the dish of the stomach come out flatter than life. This is inherent to the
  method, not a tuning problem.
* **Arms against the torso weld to it.** The subject must hold the arms clearly
  away from the body — an A-pose — or the hull bridges the gap and the rig's
  crotch/limb landmarks land on a solid slab.
* **Loose clothing is measured, not the body.** Anthropometry from the result is
  of the clothed subject. Fitted clothing, and no skirts.
* **The turn must be on the spot.** Translating across the floor breaks the
  single-axis assumption and smears the carve; so does turning the head or
  shifting the arms between views.

For segment volumes and inertial parameters the hull is nonetheless a reasonable
instrument — it is what photogrammetric anthropometry has always used — but the
numbers should be treated as an estimate and sanity-checked against a table.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

Array = np.ndarray

__all__ = [
    "hull_bias",
    "ViewSpec",
    "CarveConfig",
    "CarveResult",
    "STANDARD_VIEWS",
    "parse_views",
    "read_view_frames",
    "make_segmenter",
    "silhouette",
    "silhouettes_from_video",
    "register_views",
    "carve_visual_hull",
    "regularise_occupancy",
    "is_watertight",
    "surface_nets",
    "carve_from_video",
]


#: Conventional azimuths, in degrees, for the views a subject naturally stops at.
#: 0 is facing the camera and the angle increases as the subject turns to their
#: own left (so the camera sees their right side at 90).
STANDARD_VIEWS: Dict[str, float] = {
    "front": 0.0,
    "front_right": 45.0,
    "right": 90.0,
    "back_right": 135.0,
    "back": 180.0,
    "back_left": 225.0,
    "left": 270.0,
    "front_left": 315.0,
}


def hull_bias(angles_deg: Sequence[float]) -> float:
    """Systematic volume overestimate of a hull carved from these azimuths.

    A silhouette constrains the body to a slab, and azimuths 180 apart give the
    *same* slab, so ``n`` distinct slab orientations carve a circular
    cross-section into a circumscribed regular ``2n``-gon rather than the circle:

    .. math:: \\text{bias} = \\frac{2n \\tan(\\pi / 2n)}{\\pi}

    which is 1.27 for 2 slabs, 1.055 for 4, 1.013 for 8 and 1.006 for 12. So
    four views (front/right/back/left) overestimate a limb's volume by about 5%,
    eight views by 1.3%, and past a dozen the discretisation error dominates and
    more views stop paying. Body cross-sections are not circles, so treat this
    as the scale of the effect rather than a correction factor to divide out.
    """
    n = len({round(float(a) % 180.0, 6) for a in angles_deg})
    if n < 2:
        raise ValueError("need at least 2 distinct slab orientations")
    k = 2 * n
    return float(k * math.tan(math.pi / k) / math.pi)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
@dataclass
class ViewSpec:
    """One frame of the turn, and the azimuth the subject was at.

    Give exactly one of ``time_s`` or ``frame``. ``angle_deg`` follows
    :data:`STANDARD_VIEWS`: 0 facing the camera, increasing as the subject turns
    to their own left.
    """

    name: str
    angle_deg: float
    time_s: float | None = None
    frame: int | None = None

    def __post_init__(self) -> None:
        if (self.time_s is None) == (self.frame is None):
            raise ValueError(
                f"view '{self.name}': give exactly one of time_s or frame")


@dataclass
class CarveConfig:
    """Tunables for the carve. Defaults suit a phone clip of a standing adult.

    Attributes
    ----------
    target_height : float
        Subject's stature in metres. This is the only metric input — it sets the
        scale of everything downstream, so measure it rather than guess.
    voxels : int
        Grid resolution along the *height* axis. 192 gives roughly a centimetre
        voxel on an adult and carves in a few seconds; 320 is visibly finer and
        about five times the work. Memory grows as the cube.
    tolerance : int
        Number of views a voxel is allowed to fall outside and still survive.
        0 is the strict visual hull. 1 rescues a run where a single mask clipped
        a hand, at the cost of a slightly fatter body.
    mask_threshold : float
        Confidence above which MediaPipe's soft mask counts as person.
    erode, dilate : int
        Pixels of morphological erosion / dilation applied to each mask. Erode
        trims the halo a soft segmenter leaves around the body; dilate is the
        escape hatch if the carve comes out too thin.
    smooth : int
        Taubin smoothing passes on the finished mesh. Takes the voxel stair-step
        off without shrinking the volume the way a plain Laplacian would.
    keep_largest : bool
        Discard everything but the largest connected blob, which removes the
        floating specks a stray mask pixel leaves behind.
    regularise : bool
        Weld diagonal-only voxel contacts before surfacing, so the mesh comes
        out manifold. See :func:`regularise_occupancy`. Leave it on — a single
        non-manifold edge is enough to break ``mesh_rig``.
    close_iters : int
        Binary-closing passes on the voxel volume, to bridge pinholes before
        surfacing. Keep small; this also fills genuine detail.
    margin : float
        Fraction of the subject's width added around the grid, so the body never
        touches the boundary (which would leave an open mesh).
    backend : str
        Which segmenter to use: ``"auto"`` (MediaPipe, falling back to
        background subtraction if a ``background`` is set and the model cannot
        be reached), ``"mediapipe-legacy"``, ``"mediapipe-tasks"`` or
        ``"background"``.
    model_path : str or Path, optional
        ``.tflite`` for the Tasks backend, when it cannot be downloaded. Also
        read from ``$BIOSCOUT_SEGMENTER_MODEL``.
    background : str, Path or ndarray, optional
        Empty-scene reference for the background backend: an image path, an RGB
        array, or ``"#0"`` / seconds to take a frame from the clip itself.
    bg_threshold : int
        Per-channel intensity difference, 0-255, above which a pixel differs
        from the background. Raise it if shadows are being carved.
    mask_dir : str or Path, optional
        Skip segmentation entirely and read ``<mask_dir>/<view name>.png``.
        The way to use a better mask from any other tool.
    axis_col, ground_row, m_per_px : float or None
        Registration overrides, in pixels. ``None`` auto-detects from the
        silhouettes, which is right whenever the subject turns on the spot.
    """

    target_height: float = 1.80
    voxels: int = 192
    tolerance: int = 0

    mask_threshold: float = 0.5
    erode: int = 1
    dilate: int = 0

    smooth: int = 8
    keep_largest: bool = True
    regularise: bool = True
    close_iters: int = 1
    margin: float = 0.08

    axis_col: float | None = None
    ground_row: float | None = None
    m_per_px: float | None = None

    backend: str = "auto"
    model_path: str | Path | None = None
    background: str | Path | Array | None = None
    bg_threshold: int = 28
    mask_dir: str | Path | None = None


@dataclass
class CarveResult:
    """What a carve produced, and enough numbers to judge whether to trust it."""

    mesh_path: Path
    vertices: Array
    faces: Array
    views: List[ViewSpec] = field(default_factory=list)
    occupancy_voxels: int = 0
    volume_m3: float = 0.0
    height_m: float = 0.0
    width_m: float = 0.0
    depth_m: float = 0.0
    m_per_px: float = 0.0
    watertight: bool = False
    backend: str = ""

    def summary(self) -> str:
        """One-line sanity check.

        A standing adult lands near 60-100 L. The quoted bias is what
        :func:`hull_bias` predicts for this view set — the hull is an upper
        bound, so the true body is smaller than the number printed.
        """
        bias = ""
        if self.views:
            try:
                bias = f", hull bias +{(hull_bias([v.angle_deg for v in self.views]) - 1) * 100:.1f}%"
            except ValueError:
                bias = ""
        seal = "watertight" if self.watertight else "NOT WATERTIGHT"
        return (f"{len(self.views)} views -> {len(self.faces)} triangles, "
                f"{self.height_m:.3f} m tall, {self.width_m:.3f} x {self.depth_m:.3f} m, "
                f"{self.volume_m3 * 1000:.1f} L{bias}, {seal}")


# --------------------------------------------------------------------------- #
# view specs
# --------------------------------------------------------------------------- #
def parse_views(spec: str) -> List[ViewSpec]:
    """Parse a CLI view string into :class:`ViewSpec` objects.

    Format is comma-separated ``name=time`` or ``name@angle=time`` entries, where
    ``time`` is seconds into the clip, or ``#123`` for a frame index::

        "front=0,right=3.1,back=6.4,left=9.2"
        "front@0=0.5,q1@45=1.8,side@90=3.0"
        "front=#12,right=#96"

    A bare ``name`` must be one of :data:`STANDARD_VIEWS`; use ``name@angle`` for
    anything else.
    """
    views: List[ViewSpec] = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise ValueError(f"view '{token}': expected name=time")
        label, when = (s.strip() for s in token.split("=", 1))
        if "@" in label:
            name, angle_s = (s.strip() for s in label.split("@", 1))
            try:
                angle = float(angle_s)
            except ValueError as exc:
                raise ValueError(f"view '{token}': '{angle_s}' is not an angle") from exc
        else:
            name = label
            if name not in STANDARD_VIEWS:
                raise ValueError(
                    f"view '{name}' is not a standard view "
                    f"({', '.join(STANDARD_VIEWS)}); use name@angle=time")
            angle = STANDARD_VIEWS[name]
        try:
            if when.startswith("#"):
                views.append(ViewSpec(name, angle, frame=int(when[1:])))
            else:
                views.append(ViewSpec(name, angle, time_s=float(when)))
        except ValueError as exc:
            raise ValueError(f"view '{token}': '{when}' is not a time or #frame") from exc
    if len(views) < 3:
        raise ValueError(
            f"need at least 3 views to carve a hull, got {len(views)} — "
            "0/45/90/135 is the practical minimum, 8 over a half turn is better")
    n_slabs = len({round(v.angle_deg % 180.0, 6) for v in views})
    if n_slabs < 3:
        logger.warning(
            "these %d views give only %d distinct silhouette directions "
            "(azimuths 180 apart are redundant), so the hull will be about "
            "%.0f%% too large — spread the views over a half turn instead",
            len(views), n_slabs, (hull_bias([v.angle_deg for v in views]) - 1) * 100)
    return views


# --------------------------------------------------------------------------- #
# frames and silhouettes
# --------------------------------------------------------------------------- #
def read_view_frames(video: str | Path, views: Sequence[ViewSpec]) -> List[Array]:
    """Grab one RGB frame per view from ``video``.

    Frames are read in ascending order so the capture is walked once forwards,
    which matters for the long GOPs phone footage uses.
    """
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - env dependent
        raise ImportError("reading video needs opencv-python (pip install opencv-python)") from exc

    video = Path(video)
    if not video.exists():
        raise FileNotFoundError(video)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"could not open {video}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        wanted: List[Tuple[int, int]] = []       # (frame index, view index)
        for i, v in enumerate(views):
            idx = v.frame if v.frame is not None else int(round(v.time_s * fps))
            if idx < 0 or (n_frames and idx >= n_frames):
                raise ValueError(
                    f"view '{v.name}' asks for frame {idx}, but the clip has "
                    f"{n_frames} frames ({n_frames / fps:.1f} s at {fps:.1f} fps)")
            wanted.append((idx, i))
        out: List[Array | None] = [None] * len(views)
        for idx, i in sorted(wanted):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"view '{views[i].name}': could not read frame {idx}")
            out[i] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return [f for f in out if f is not None]
    finally:
        cap.release()


def _clean_mask(mask: Array, cfg: CarveConfig) -> Array:
    """Threshold, erode/dilate, keep the largest blob and fill its holes."""
    from scipy import ndimage as ndi

    m = mask > cfg.mask_threshold
    if cfg.erode:
        m = ndi.binary_erosion(m, iterations=cfg.erode, border_value=0)
    if cfg.dilate:
        m = ndi.binary_dilation(m, iterations=cfg.dilate, border_value=0)
    if not m.any():
        return m
    lab, n = ndi.label(m)
    if n > 1:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        m = lab == int(sizes.argmax())
    return ndi.binary_fill_holes(m)


# --- segmentation backends ------------------------------------------------- #
# Three of them, because the obvious one is not always available. MediaPipe
# reorganised at 1.0: ``mp.solutions.selfie_segmentation`` (which carried its
# weights inside the wheel) is gone, and the replacement Tasks API needs a
# .tflite downloaded from Google's servers — which fails on any machine behind a
# proxy, exactly where a lab workstation usually sits. So the module also ships
# a background-subtraction backend that needs no model at all, and accepts masks
# made elsewhere.


class _LegacySelfie:
    """``mp.solutions.selfie_segmentation`` — mediapipe < 1.0. Weights bundled."""

    name = "mediapipe-legacy"

    def __init__(self, cfg: CarveConfig) -> None:
        import mediapipe as mp
        self._seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)

    def __call__(self, frame: Array) -> Array:
        res = self._seg.process(np.ascontiguousarray(frame))
        if res.segmentation_mask is None:
            raise RuntimeError("segmenter returned no mask — is the frame RGB uint8?")
        return np.asarray(res.segmentation_mask, dtype=np.float32)

    def close(self) -> None:
        self._seg.close()


class _TasksSegmenter:
    """``mediapipe.tasks`` ImageSegmenter — mediapipe >= 0.10, needs a model file."""

    name = "mediapipe-tasks"
    #: Google's general selfie segmenter. Reachable only if the machine can talk
    #: to storage.googleapis.com; otherwise pass CarveConfig.model_path.
    MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
                 "selfie_segmenter/float16/latest/selfie_segmenter.tflite")

    def __init__(self, cfg: CarveConfig) -> None:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self._mp = mp
        model = self._resolve_model(cfg)
        self._seg = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=BaseOptions(model_asset_path=str(model)),
                output_category_mask=False, output_confidence_masks=True))

    @classmethod
    def _resolve_model(cls, cfg: CarveConfig) -> Path:
        """Find the .tflite: explicit path, then the package, then a cached download."""
        import os

        candidates: List[Path] = []
        if cfg.model_path:
            candidates.append(Path(cfg.model_path))
        env = os.environ.get("BIOSCOUT_SEGMENTER_MODEL")
        if env:
            candidates.append(Path(env))
        candidates.append(Path(__file__).resolve().parent.parent / "record" / "selfie_segmenter.tflite")
        cache = Path.home() / ".bioscout" / "selfie_segmenter.tflite"
        candidates.append(cache)
        for c in candidates:
            if c.is_file():
                return c
        if cfg.model_path:
            raise FileNotFoundError(f"segmenter model not found at {cfg.model_path}")

        import urllib.error
        import urllib.request
        cache.parent.mkdir(parents=True, exist_ok=True)
        logger.info("downloading the segmenter model to %s (once)", cache)
        try:
            urllib.request.urlretrieve(cls.MODEL_URL, cache)
        except (urllib.error.URLError, OSError) as exc:
            raise RuntimeError(
                f"this mediapipe ({cls._version()}) needs a segmenter model file and "
                f"it could not be downloaded ({exc}). Either fetch it once by hand:\n"
                f"    curl -L -o {cache} {cls.MODEL_URL}\n"
                "or point CarveConfig.model_path at a .tflite, or use "
                'CarveConfig(backend="background") with a shot of the empty scene, '
                "which needs no model at all."
            ) from exc
        return cache

    @staticmethod
    def _version() -> str:
        try:
            import mediapipe as mp
            return getattr(mp, "__version__", "unknown")
        except Exception:                                    # pragma: no cover
            return "unknown"

    def __call__(self, frame: Array) -> Array:
        img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB,
                             data=np.ascontiguousarray(frame, dtype=np.uint8))
        res = self._seg.segment(img)
        masks = getattr(res, "confidence_masks", None)
        if not masks:
            raise RuntimeError("ImageSegmenter returned no confidence mask")
        # index 0 is background for the selfie model, so person confidence is the
        # complement when only two categories come back.
        arr = np.asarray(masks[-1].numpy_view(), dtype=np.float32)
        return arr if len(masks) > 1 else 1.0 - arr

    def close(self) -> None:
        self._seg.close()


class _BackgroundSubtract:
    """No model at all: difference each frame against a shot of the empty scene.

    Sharper silhouettes than any segmenter, and completely offline — the cost is
    that the capture has to cooperate: fixed camera, unchanging light, and one
    frame with nobody in it. The natural way to get that is to start recording,
    then walk into shot, and pass ``background="#0"``.
    """

    name = "background"

    def __init__(self, cfg: CarveConfig, background: Array | None = None) -> None:
        if background is None:
            raise ValueError(
                'backend="background" needs CarveConfig.background — a path to a '
                'photo of the empty scene, or "#0"/seconds to take a frame from '
                "the clip itself before the subject steps in")
        self._bg = np.asarray(background, dtype=np.int16)
        self._thr = cfg.bg_threshold

    def __call__(self, frame: Array) -> Array:
        f = np.asarray(frame, dtype=np.int16)
        if f.shape != self._bg.shape:
            raise ValueError(
                f"background is {self._bg.shape} but the frame is {f.shape} — "
                "the background shot must come from the same camera and resolution")
        diff = np.abs(f - self._bg).max(axis=2)
        return (diff >= self._thr).astype(np.float32)

    def close(self) -> None:
        pass


def _resolve_background(cfg: CarveConfig, video: str | Path | None) -> Array | None:
    """Turn ``CarveConfig.background`` into an RGB array, if it is set."""
    bg = cfg.background
    if bg is None:
        return None
    if isinstance(bg, np.ndarray):
        return bg
    text = str(bg)
    if text.startswith("#") or _is_number(text):
        if video is None:
            raise ValueError("a background given as a time or #frame needs the video")
        spec = ViewSpec("background", 0.0,
                        **({"frame": int(text[1:])} if text.startswith("#")
                           else {"time_s": float(text)}))
        return read_view_frames(video, [spec])[0]
    path = Path(text)
    if not path.is_file():
        raise FileNotFoundError(f"background image not found: {path}")
    try:
        import cv2
    except ImportError as exc:                               # pragma: no cover
        raise ImportError("reading a background image needs opencv-python") from exc
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"could not read {path} as an image")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def make_segmenter(cfg: CarveConfig, video: str | Path | None = None):
    """Build the segmentation backend named by ``cfg.backend``.

    ``"auto"`` prefers MediaPipe and falls back to background subtraction when a
    background was supplied, so a config that names one always gets a working
    run even on a machine where the model cannot be fetched.
    """
    backend = (cfg.backend or "auto").lower()
    bg = _resolve_background(cfg, video)

    if backend == "background":
        return _BackgroundSubtract(cfg, bg)
    if backend in ("mediapipe-legacy", "legacy"):
        return _LegacySelfie(cfg)
    if backend in ("mediapipe-tasks", "tasks"):
        return _TasksSegmenter(cfg)
    if backend not in ("auto", "mediapipe"):
        raise ValueError(
            f"unknown backend '{cfg.backend}'; expected auto, mediapipe, "
            "mediapipe-legacy, mediapipe-tasks or background")

    try:
        import mediapipe as mp
    except ImportError as exc:
        if bg is not None:
            logger.warning("mediapipe is not installed; using background subtraction")
            return _BackgroundSubtract(cfg, bg)
        raise ImportError(
            "silhouette extraction needs mediapipe (pip install mediapipe), or "
            'set CarveConfig(backend="background") with a shot of the empty scene'
        ) from exc

    if hasattr(mp, "solutions") and hasattr(mp.solutions, "selfie_segmentation"):
        return _LegacySelfie(cfg)
    try:
        return _TasksSegmenter(cfg)
    except Exception as exc:
        if bg is not None:
            logger.warning("falling back to background subtraction: %s", exc)
            return _BackgroundSubtract(cfg, bg)
        raise


def silhouette(frame: Array, cfg: CarveConfig | None = None, _segmenter=None) -> Array:
    """Boolean person mask for one RGB frame.

    Pass ``_segmenter`` (from :func:`make_segmenter`) to reuse one backend across
    frames; constructing it costs far more than running it.
    """
    cfg = cfg or CarveConfig()
    if _segmenter is None:
        seg = make_segmenter(cfg)
        try:
            return _clean_mask(seg(frame), cfg)
        finally:
            seg.close()
    return _clean_mask(_segmenter(frame), cfg)


def silhouettes_from_video(video: str | Path, views: Sequence[ViewSpec],
                           cfg: CarveConfig | None = None) -> List[Array]:
    """Silhouette mask per view, opening the backend once for the whole set."""
    cfg = cfg or CarveConfig()
    if cfg.mask_dir:
        return _masks_from_dir(cfg, views)
    frames = read_view_frames(video, views)
    seg = make_segmenter(cfg, video)
    logger.info("segmenting %d views with the %s backend", len(frames), seg.name)
    try:
        masks = [_clean_mask(seg(f), cfg) for f in frames]
    finally:
        seg.close()
    for v, m in zip(views, masks):
        if not m.any():
            raise ValueError(
                f"view '{v.name}': the segmenter found no person in that frame — "
                "wrong timestamp, or the subject is out of shot")
        if m.mean() > 0.9:
            raise ValueError(
                f"view '{v.name}': the mask covers {m.mean():.0%} of the frame, "
                "which is the whole scene rather than a person — check the "
                "background shot, or raise CarveConfig.bg_threshold")
    return masks


def _masks_from_dir(cfg: CarveConfig, views: Sequence[ViewSpec]) -> List[Array]:
    """Load ``<mask_dir>/<view name>.png`` instead of segmenting.

    The escape hatch: any tool that makes a better mask than this module can —
    SAM, rembg, a rotoscope — becomes usable by writing one image per view.
    """
    try:
        import cv2
    except ImportError as exc:                               # pragma: no cover
        raise ImportError("reading masks needs opencv-python") from exc
    d = Path(cfg.mask_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"mask_dir not found: {d}")
    masks = []
    for v in views:
        hits = sorted(d.glob(f"{v.name}.*"))
        if not hits:
            raise FileNotFoundError(
                f"no mask for view '{v.name}' in {d} — expected {v.name}.png")
        img = cv2.imread(str(hits[0]), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"could not read {hits[0]}")
        masks.append(_clean_mask(img.astype(np.float32) / 255.0, cfg))
    return masks


# --------------------------------------------------------------------------- #
# registration
# --------------------------------------------------------------------------- #
def register_views(masks: Sequence[Array], cfg: CarveConfig
                   ) -> Tuple[float, float, float]:
    """Recover ``(axis_col, ground_row, m_per_px)`` from the silhouettes.

    The camera is fixed and the subject turns on the spot, so one registration
    serves every view. The ground row is the lowest foot pixel seen in any view
    and the head row the highest, which together with ``target_height`` give the
    scale. The rotation axis is the mean of the per-view bounding-box centres:
    a subject standing slightly off-axis swings left and right about the true
    axis through the turn, and over a roughly symmetric set of views that
    averages out.

    Any of the three may be pinned in the config, which is what to do when the
    subject's arms are out far enough to bias the bounding boxes.
    """
    rows_lo, rows_hi, cols = [], [], []
    for m in masks:
        ys, xs = np.nonzero(m)
        rows_lo.append(ys.min())
        rows_hi.append(ys.max())
        cols.append(0.5 * (xs.min() + xs.max()))
    head_row = float(np.mean(rows_lo))
    ground_row = float(np.mean(rows_hi))
    px_height = ground_row - head_row
    if px_height < 20:
        raise ValueError(
            f"the subject is only {px_height:.0f} px tall in frame — too small "
            "to carve; move the camera closer or crop the clip")

    m_per_px = cfg.m_per_px if cfg.m_per_px else cfg.target_height / px_height
    if cfg.ground_row is not None:
        ground_row = float(cfg.ground_row)
    axis_col = float(cfg.axis_col) if cfg.axis_col is not None else float(np.mean(cols))
    return axis_col, ground_row, m_per_px


# --------------------------------------------------------------------------- #
# the carve
# --------------------------------------------------------------------------- #
def carve_visual_hull(masks: Sequence[Array], angles_deg: Sequence[float],
                      cfg: CarveConfig) -> Tuple[Array, Array, Array]:
    """Intersect the silhouette cones into a voxel occupancy grid.

    Returns ``(occupancy, origin, spacing)`` with the grid in metres, y up, the
    feet on ``y = 0``, +x to the camera's right at the front view and +z toward
    the camera.

    Projection is orthographic. For a subject a few metres from a phone camera
    the perspective across their own depth is a couple of percent, well under
    the error the segmentation already contributes, and orthographic needs no
    calibration at all — which is the difference between a module that runs on
    any clip and one that needs a checkerboard.
    """
    from scipy import ndimage as ndi

    if len(masks) != len(angles_deg):
        raise ValueError(f"{len(masks)} masks but {len(angles_deg)} angles")
    if len(masks) < 3:
        raise ValueError("need at least 3 views to carve a hull")
    shape = masks[0].shape
    for i, m in enumerate(masks):
        if m.shape != shape:
            raise ValueError(
                f"view {i} is {m.shape}, view 0 is {shape} — all views must "
                "come from the same fixed camera")

    axis_col, ground_row, m_per_px = register_views(masks, cfg)
    H = cfg.target_height

    # half-width of the grid: the widest silhouette, plus margin
    half = 0.0
    for m in masks:
        xs = np.nonzero(m.any(axis=0))[0]
        half = max(half, abs(xs.min() - axis_col), abs(xs.max() - axis_col))
    half_m = half * m_per_px * (1.0 + cfg.margin)
    pad_y = cfg.margin * H

    spacing = H / float(cfg.voxels)
    ny = int(cfg.voxels + 2 * math.ceil(pad_y / spacing))
    nxz = int(2 * math.ceil(half_m / spacing)) + 2
    origin = np.array([-half_m - spacing, -pad_y, -half_m - spacing], dtype=np.float64)

    if nxz * ny * nxz > 400_000_000:
        raise ValueError(
            f"grid would be {nxz}x{ny}x{nxz} voxels — lower CarveConfig.voxels "
            f"(currently {cfg.voxels})")

    gx = origin[0] + spacing * np.arange(nxz)
    gy = origin[1] + spacing * np.arange(ny)
    gz = origin[2] + spacing * np.arange(nxz)
    X, Z = np.meshgrid(gx, gz, indexing="ij")            # (nxz, nxz)

    n_rows, n_cols = shape
    votes = np.zeros((nxz, ny, nxz), dtype=np.uint8)

    # v is the same for every view: the grid's own y, independent of azimuth.
    v_idx = np.rint(ground_row - gy / m_per_px).astype(np.int64)
    v_ok = (v_idx >= 0) & (v_idx < n_rows)

    for m, ang in zip(masks, angles_deg):
        th = math.radians(ang)
        # The subject rotates by +th, so a point fixed to the body appears at
        # the image abscissa of its rotation about the vertical axis.
        u_m = X * math.cos(th) - Z * math.sin(th)
        u_idx = np.rint(axis_col + u_m / m_per_px).astype(np.int64)
        u_ok = (u_idx >= 0) & (u_idx < n_cols)
        u_safe = np.clip(u_idx, 0, n_cols - 1)
        # inside[x, z, y] -> transpose into (x, y, z)
        inside = m[np.clip(v_idx, 0, n_rows - 1)[None, None, :], u_safe[:, :, None]]
        inside &= u_ok[:, :, None] & v_ok[None, None, :]
        votes += np.transpose(inside, (0, 2, 1)).astype(np.uint8)

    occ = votes >= (len(masks) - cfg.tolerance)
    if not occ.any():
        raise ValueError(
            "the carve came out empty — the views disagree completely. Check "
            "that the angles match the frames and that the subject turned on "
            "the spot; CarveConfig.tolerance=1 also loosens the intersection.")

    if cfg.close_iters:
        occ = ndi.binary_closing(occ, iterations=cfg.close_iters, border_value=0)
    if cfg.keep_largest:
        lab, n = ndi.label(occ)
        if n > 1:
            sizes = np.bincount(lab.ravel())
            sizes[0] = 0
            occ = lab == int(sizes.argmax())
    if cfg.regularise:
        occ, added = regularise_occupancy(occ)
        if added:
            logger.debug("filled %d voxel(s) to remove diagonal-only contacts", added)
    return occ, origin, np.array([spacing, spacing, spacing])


# --------------------------------------------------------------------------- #
# surfacing
# --------------------------------------------------------------------------- #
def regularise_occupancy(occ: Array, max_passes: int = 8) -> Tuple[Array, int]:
    """Remove diagonal-only contacts, so the isosurface comes out manifold.

    Surface nets places exactly one vertex per cell, which cannot represent two
    surface sheets passing through the same cell. That happens wherever the
    occupancy touches itself only across a diagonal — a 2x2 checkerboard in some
    axis-aligned plane. The result is an edge shared by four triangles instead of
    two: the mesh is no longer manifold, and ``mesh_rig``'s boundary walk and
    every downstream mesh tool treat it as broken.

    Rather than repair the triangles afterwards, fix the cause: fill one voxel of
    each checkerboard, which welds the diagonal contact into a face contact.
    Filling can create new checkerboards a cell over, so it iterates to a fixed
    point. The change is a handful of voxels on a body-sized grid — far below the
    carve's own discretisation error.

    Returns the corrected grid and how many voxels were added.
    """
    occ = occ.copy()
    added = 0
    for _ in range(max_passes):
        changed = 0
        for d1, d2 in ((0, 1), (0, 2), (1, 2)):





            def win(i, j):
                sl = [slice(None)] * 3
                sl[d1] = slice(i, occ.shape[d1] - 1 + i)
                sl[d2] = slice(j, occ.shape[d2] - 1 + j)
                return tuple(sl)
            A, B = occ[win(0, 0)], occ[win(0, 1)]
            C, D = occ[win(1, 0)], occ[win(1, 1)]
            diag1 = A & D & ~B & ~C          # fill B
            diag2 = B & C & ~A & ~D          # fill A
            if diag1.any():
                occ[win(0, 1)] |= diag1
                changed += int(diag1.sum())
            if diag2.any():
                occ[win(0, 0)] |= diag2
                changed += int(diag2.sum())
        added += changed
        if not changed:
            break
    return occ, added



_CELL_EDGES = (
    (0, 1), (2, 3), (4, 5), (6, 7),      # along x  (corner bit 4)
    (0, 2), (1, 3), (4, 6), (5, 7),      # along y  (corner bit 2)
    (0, 4), (1, 5), (2, 6), (3, 7),      # along z  (corner bit 1)
)
#: corner index -> (dx, dy, dz), bit 4 = x, bit 2 = y, bit 1 = z
_CORNER_OFF = np.array([(i >> 2 & 1, i >> 1 & 1, i & 1) for i in range(8)], dtype=np.float64)


def surface_nets(field: Array, spacing: Array, origin: Array,
                 level: float = 0.0) -> Tuple[Array, Array]:
    """Extract the ``level`` isosurface of a scalar field as a closed mesh.

    Naive surface nets: one vertex per cell that straddles the level, placed at
    the mean of that cell's edge crossings, and one quad per straddling grid
    edge joining the four cells around it. The result is manifold and closed
    provided the field is above ``level`` on the whole boundary — which is why
    the carve pads its grid.

    Chosen over marching cubes because it is a fifth of the code, has no
    256-case table to get subtly wrong, and produces far fewer, better-shaped
    triangles; the cost is slightly softer sharp edges, which a body scan does
    not have anyway.
    """
    f = np.asarray(field, dtype=np.float64) - level
    if f.ndim != 3:
        raise ValueError(f"field must be 3-D, got shape {f.shape}")
    nx, ny, nz = f.shape
    if min(nx, ny, nz) < 2:
        raise ValueError(f"field is too small to surface: {f.shape}")

    # corner values per cell, indexed [corner][i, j, k]
    corner = np.empty((8, nx - 1, ny - 1, nz - 1), dtype=np.float64)
    for c, (dx, dy, dz) in enumerate(_CORNER_OFF.astype(int)):
        corner[c] = f[dx:nx - 1 + dx, dy:ny - 1 + dy, dz:nz - 1 + dz]
    neg = corner < 0
    active = neg.any(axis=0) & (~neg).any(axis=0)
    if not active.any():
        raise ValueError("no isosurface at that level — the field never crosses it")

    # vertex per active cell: mean of the zero crossings on its 12 edges
    acc = np.zeros((3,) + active.shape, dtype=np.float64)
    cnt = np.zeros(active.shape, dtype=np.float64)
    for a, b in _CELL_EDGES:
        va, vb = corner[a], corner[b]
        cross = (va < 0) != (vb < 0)
        if not cross.any():
            continue
        denom = va - vb
        t = np.divide(va, denom, out=np.full_like(va, 0.5), where=denom != 0)
        t = np.clip(t, 0.0, 1.0)
        pa, pb = _CORNER_OFF[a], _CORNER_OFF[b]
        for d in range(3):
            acc[d] += np.where(cross, pa[d] + t * (pb[d] - pa[d]), 0.0)
        cnt += cross
    cnt_safe = np.where(cnt > 0, cnt, 1.0)
    local = np.stack([acc[d] / cnt_safe for d in range(3)], axis=-1)

    idx = np.full(active.shape, -1, dtype=np.int64)
    ai, aj, ak = np.nonzero(active)
    idx[ai, aj, ak] = np.arange(len(ai))
    verts = (np.stack([ai, aj, ak], axis=-1) + local[ai, aj, ak]) * spacing + origin

    # One quad per grid edge that straddles the level, built from the four cells
    # around that edge. Winding has to come out consistent across all three axis
    # families or the mesh is closed but not orientable, so two signs combine:
    # the handedness of (other1, other2, axis) as a permutation of (x, y, z), and
    # whether the edge runs inside-to-outside or the reverse.
    quads: List[Array] = []
    for axis in range(3):
        o1, o2 = [d for d in range(3) if d != axis]
        # (o1, o2, axis) is an even permutation for axis 0 and 2, odd for axis 1
        handed = -1 if axis == 1 else 1
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[axis] = slice(0, f.shape[axis] - 1)
        sl_b[axis] = slice(1, f.shape[axis])
        for d in (o1, o2):                      # interior grid lines only
            sl_a[d] = slice(1, f.shape[d] - 1)
            sl_b[d] = slice(1, f.shape[d] - 1)
        va, vb = f[tuple(sl_a)], f[tuple(sl_b)]
        cross = (va < 0) != (vb < 0)
        if not cross.any():
            continue
        corners_idx = []
        for du, dv in ((0, 0), (0, -1), (-1, -1), (-1, 0)):
            sl = [slice(None)] * 3
            sl[axis] = slice(0, f.shape[axis] - 1)
            sl[o1] = slice(1 + du, f.shape[o1] - 1 + du)
            sl[o2] = slice(1 + dv, f.shape[o2] - 1 + dv)
            corners_idx.append(idx[tuple(sl)])
        cells = np.stack([c[cross] for c in corners_idx], axis=-1)   # (m, 4)
        keep = (cells >= 0).all(axis=1)
        cells = cells[keep]
        if not len(cells):
            continue
        a_inside = (va[cross] < 0)[keep]
        reverse = a_inside if handed > 0 else ~a_inside
        cells = np.where(reverse[:, None], cells[:, ::-1], cells)
        quads.append(cells)

    if not quads:
        raise ValueError("isosurface produced no faces")
    Q = np.concatenate(quads, axis=0)
    faces = np.concatenate([Q[:, [0, 1, 2]], Q[:, [0, 2, 3]]], axis=0)
    return verts, faces


# --------------------------------------------------------------------------- #
# top level
# --------------------------------------------------------------------------- #
def is_watertight(faces: Array) -> bool:
    """True when every edge is shared by exactly two triangles.

    Worth checking on every carve rather than trusting the pipeline: ``mesh_rig``
    walks boundary loops to cap its cuts, and a mesh with a hole sends that walk
    somewhere meaningless instead of failing loudly.

    This tests *topology*, so it needs shared vertex indices. Faces read back
    from an STL never have them — the format stores three loose vertices per
    triangle — so a mesh loaded from disk must go through
    :func:`~bioscout.session.movement_detector.mesh_rig.weld` first, exactly as
    ``rig_mesh`` does. Called on unwelded faces this always returns False.
    """
    E = np.sort(np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(E, axis=0, return_counts=True)
    return bool((counts == 2).all())


def _signed_field(occ: Array) -> Array:
    """Signed distance (voxels) from the occupancy boundary, negative inside.

    No half-voxel offset: with ``edt(~occ) - edt(occ)`` an occupied voxel next
    to background reads -1 and its background neighbour +1, so the zero level
    falls exactly midway between the two centres — which is where the surface
    belongs, given occupancy was decided by testing voxel centres. Subtracting
    0.5 here (an easy thing to reach for) pushes the surface a quarter of a
    voxel outward and inflates every volume the module reports.
    """
    from scipy import ndimage as ndi

    padded = np.zeros(np.array(occ.shape) + 2, dtype=bool)
    padded[1:-1, 1:-1, 1:-1] = occ
    outside = ndi.distance_transform_edt(~padded)
    inside = ndi.distance_transform_edt(padded)
    return (outside - inside)[1:-1, 1:-1, 1:-1]


def carve_from_video(video: str | Path, out_path: str | Path,
                     views: Sequence[ViewSpec] | str,
                     config: CarveConfig | None = None) -> CarveResult:
    """Fixed-camera turntable video in, one closed STL out.

    Parameters
    ----------
    video : str or Path
        The clip. Fixed camera, subject turning on the spot in an A-pose.
    out_path : str or Path
        Destination ``.stl``.
    views : sequence of ViewSpec, or str
        Which frames to use and what azimuth each is. A string is passed to
        :func:`parse_views`. Spread them over a *half* turn, not a full one —
        0/45/90/135 is the practical minimum, and 8 stops over 180 is
        noticeably rounder. See :func:`hull_bias` for why front/back is a
        wasted pair.
    config : CarveConfig, optional
        See :class:`CarveConfig`. ``target_height`` is the field to set.

    Returns
    -------
    CarveResult
        Print ``result.summary()`` before trusting the mesh — a standing adult
        should come out near 60-100 litres, and a wildly different volume means
        the registration or the view angles are wrong.
    """
    from .mesh_rig import taubin_smooth, write_stl_fast

    cfg = config or CarveConfig()
    view_list = parse_views(views) if isinstance(views, str) else list(views)

    masks = silhouettes_from_video(video, view_list, cfg)
    occ, origin, spacing = carve_visual_hull(
        masks, [v.angle_deg for v in view_list], cfg)

    V, F = surface_nets(_signed_field(occ), spacing, origin)
    if cfg.smooth:
        V = taubin_smooth(V, F, passes=cfg.smooth)

    lo, hi = V.min(axis=0), V.max(axis=0)
    sealed = is_watertight(F)
    if not sealed:
        logger.warning(
            "the carved mesh is not watertight — mesh_rig's cap step needs a "
            "closed shell, so rig the result only after checking it. Raising "
            "CarveConfig.voxels or leaving regularise on usually fixes it.")
    out_path = write_stl_fast(V, F, out_path, name=Path(out_path).stem)
    res = CarveResult(
        mesh_path=out_path, vertices=V, faces=F, views=view_list,
        occupancy_voxels=int(occ.sum()),
        volume_m3=float(occ.sum()) * float(np.prod(spacing)),
        height_m=float(hi[1] - lo[1]), width_m=float(hi[0] - lo[0]),
        depth_m=float(hi[2] - lo[2]), watertight=sealed,
        m_per_px=register_views(masks, cfg)[2])
    logger.info("%s", res.summary())
    return res


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m bioscout.session.movement_detector.mesh_from_video",
        description="Carve a closed body mesh from a fixed-camera turntable video.",
        epilog="Then rig it:  python -m bioscout.session.movement_detector.mesh_rig "
               "body.stl -o subject01 --height 1.81")
    p.add_argument("video", help="clip of the subject turning on the spot")
    p.add_argument("-o", "--out", default="body.stl", help="output .stl")
    p.add_argument("--views", required=True,
                   help="name=time list, e.g. 'front=0,q1@45=1.6,right=3.1,q3@135=4.7'. "
                        "Spread views over a HALF turn: azimuths 180 apart are "
                        "geometrically redundant. Use name@angle=time for "
                        "non-standard azimuths, =#N for a frame index")
    p.add_argument("--height", type=float, default=1.80,
                   help="subject stature in metres (default 1.80)")
    p.add_argument("--voxels", type=int, default=192, help="grid resolution (default 192)")
    p.add_argument("--tolerance", type=int, default=0,
                   help="views a voxel may fall outside and survive (default 0)")
    p.add_argument("--smooth", type=int, default=8, help="Taubin passes (default 8)")
    p.add_argument("--dilate", type=int, default=0, help="mask dilation, px")
    p.add_argument("--erode", type=int, default=1, help="mask erosion, px (default 1)")
    p.add_argument("--backend", default="auto",
                   choices=["auto", "mediapipe", "mediapipe-legacy", "mediapipe-tasks", "background"],
                   help="segmenter (default auto)")
    p.add_argument("--background", default=None,
                   help="empty-scene reference for --backend background: an image "
                        "path, or '#0'/seconds to take it from the clip itself")
    p.add_argument("--model", default=None, help=".tflite for the mediapipe-tasks backend")
    p.add_argument("--masks", default=None,
                   help="directory of <view>.png masks, bypassing segmentation")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[carve] %(message)s")
    cfg = CarveConfig(target_height=a.height, voxels=a.voxels, tolerance=a.tolerance,
                      smooth=a.smooth, dilate=a.dilate, erode=a.erode,
                      backend=a.backend, background=a.background,
                      model_path=a.model, mask_dir=a.masks)
    try:
        res = carve_from_video(a.video, a.out, a.views, cfg)
    except Exception as exc:
        print(f"[carve] ERROR: {exc}")
        return 1
    print(f"[carve] {res.summary()}")
    print(f"[carve] wrote {res.mesh_path}")
    if not res.watertight:
        print("[carve] WARNING: not watertight — check it before rigging")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
