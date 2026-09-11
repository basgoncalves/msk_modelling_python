"""
mesh_rig — turn a single whole-body surface mesh into a rigged OpenSim model.

``mesh_convert`` gets a scan into STL. This module takes it the rest of the way:
one closed human-shaped mesh in, a segmented, un-posed, joint-filled STL set
plus a ready-to-open ``.osim`` out, with the base model's kinematics untouched.

    from bioscout.session.movement_detector import rig_mesh
    res = rig_mesh("3DModel.obj", out_dir="subject01", name="bas",
                   config=RigConfig(target_height=1.81))
    print(res.model_path)        # subject01/bas.osim
    print(res.landmarks)         # ankle/knee/hip/lumbar/neck heights, metres

Command line::

    python -m bioscout.session.movement_detector.mesh_rig scan.stl -o out --height 1.81

What it does, in order
----------------------
1. **Load and weld.** Binary/ASCII STL and Wavefront OBJ. STL stores three
   loose vertices per triangle, so vertices are welded by position — without
   that there is no connectivity and no boundary loop to cap.
2. **Decimate** by vertex clustering (``config.grid``). A 1 M-triangle sculpt
   drops to a few hundred thousand in about a second; everything downstream is
   then linear in a much smaller number.
3. **Orient.** The mesh is rotated into the anatomical frame the model uses
   (+x anterior, +y up, +z to the subject's right), scaled to
   ``config.target_height`` and dropped onto y = 0. The medio-lateral axis is
   the major horizontal principal axis of the trunk band; anterior is the
   remaining horizontal axis, signed by where the feet point.
4. **Landmarks.** Ankle, knee and neck are the narrowest girth of the limb
   inside anthropometric search bands; the hip is found from the crotch — the
   highest level at which the two legs are still separated by a gap. These
   reproduce the values that were read off ruler renders by hand in the
   original per-character build scripts (see ``examples`` in the tests).
5. **Cut** into the base model's bodies, per triangle centroid.
6. **Un-pose.** Each segment is rotated so the line between its own two joint
   centres lands on the body's long axis, then scaled axially to the model's
   segment length. Hip and ankle centres are *imposed* from the model rather
   than measured — fitting splayed legs or a foot slab centroid is much less
   reliable than trusting the skeleton.
7. **Close.** Every plane cut leaves an open shell, which reads as a hole the
   moment the joint flexes. Boundary loops are fanned to their centroid, and a
   filler blob at each joint centre — carried by the *proximal* body, sized
   from the distal segment's cut — fills the wedge that opens under flexion.
8. **Write.** One STL per body per region, and a copy of the base ``.osim``
   whose ``attached_geometry`` is replaced. Joints, coordinates, constraints,
   forces and markers are copied verbatim, so existing ``.mot``/``.sto`` files
   and IK/ID/SO setups keep working against the result.

Only numpy is required. Pillow is used, if present, to carry a textured OBJ's
colours into per-region meshes.

Caveats worth knowing before trusting a result
----------------------------------------------
* Segments are rigid, so loose clothing shows a seam at the knee and hip.
* Arms and head ride on ``torso`` unless the base model has arm/skull bodies.
* Masses and inertias come from the base model and are NOT rescaled to the
  subject. The output is display geometry on someone else's dynamics: fine for
  visualisation and IK, not validated for ID/SO without a scaling pass.
"""
from __future__ import annotations

import logging
import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "RigConfig",
    "RigResult",
    "ModelLandmarks",
    "rig_mesh",
    "load_mesh",
    "weld",
    "decimate",
    "orient_mesh",
    "body_landmarks",
    "read_model_landmarks",
    "cap_open_boundaries",
    "write_stl_fast",
    "write_osim",
    "GPK_LANDMARKS",
]

Array = np.ndarray

# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #


@dataclass
class RigConfig:
    """Everything tunable about a rig, with defaults that work on a standing scan.

    Attributes
    ----------
    target_height : float
        Finished stature in metres. A scan is rarely metric; this is what sets
        the scale, so it is the single most important number to get right.
    grid : float
        Vertex-clustering cell size for decimation, in *source* units. ``None``
        or 0 disables decimation. The default is chosen relative to the mesh
        height at run time if left at ``None``.
    facing_yaw : float or None
        Anterior direction in degrees about the up axis, measured from +x.
        ``None`` auto-detects, which is right for any scan whose feet point
        forwards. Give it explicitly for a lunge or a twisted sculpt, where the
        line between the legs no longer carries the facing.
    up : str
        Which source axis is up: ``"y"`` (default, OpenSim and most scanners)
        or ``"z"`` (CAD exports).
    ankle_h, knee_h, hip_h, lumbar_h, neck_h : float or None
        Landmark heights as a *fraction of stature*. ``None`` auto-detects.
        Override one when a garment hides the cue — baggy trousers are the
        usual reason.
    cap_cuts : bool
        Fan every open boundary loop to its centroid, making each piece a
        closed solid. Leave this on for anything animated.
    joint_fillers : bool
        Add a blob at each joint centre, on the proximal body, so the joint
        stays covered under flexion.
    filler_scale : float
        Filler radius as a multiple of the distal segment's own cut radius.
    smooth : int
        Taubin smoothing passes applied after decimation. Takes scanner noise
        off without the shrinkage a plain Laplacian causes. 0 disables.
    fit_legs : bool
        Ignore ``target_height`` and scale the mesh so its **hip height**
        matches the base model's instead. Use it whenever the figure's
        proportions differ from the skeleton's — a child, a stylised character,
        anyone long or short in the leg. Scaling by stature onto a mismatched
        skeleton stretches the limbs to the model's segment lengths and leaves
        a figure with a small torso on stilts. The finished height is then
        whatever the model implies, and the OpenSim Scale Tool is the right
        place to bring the model (and its geometry with it) back down.
    keep_bones : bool
        Also write an x-ray model that keeps the base model's bone geometry
        under a translucent skin. Handy for checking the fit.
    skin_colour : str
        OpenSim ``<color>`` triple used for untextured meshes.
    opacity : float
        Skin opacity in the main model.
    """

    target_height: float = 1.80
    grid: float | None = None
    facing_yaw: float | None = None
    up: str = "y"

    ankle_h: float | None = None
    knee_h: float | None = None
    hip_h: float | None = None
    lumbar_h: float | None = None
    neck_h: float | None = None

    cap_cuts: bool = True
    joint_fillers: bool = True
    filler_scale: float = 1.05
    smooth: int = 0

    fit_legs: bool = False
    keep_bones: bool = False
    skin_colour: str = "0.89 0.71 0.60"
    opacity: float = 1.0

    # anthropometric search bands, as fractions of stature
    ankle_band: Tuple[float, float] = (0.030, 0.120)
    knee_band: Tuple[float, float] = (0.200, 0.360)
    crotch_band: Tuple[float, float] = (0.350, 0.620)
    neck_band: Tuple[float, float] = (0.790, 0.900)

    def resolved_grid(self, height: float) -> float:
        """Decimation cell, defaulting to 1/700 of the mesh height."""
        if self.grid is None:
            return height / 700.0
        return float(self.grid)


@dataclass
class ModelLandmarks:
    """Joint geometry read out of the base ``.osim``, in each body's own frame.

    All lengths are metres. ``hip`` is the right hip in the pelvis frame;
    the left is its mirror in z.
    """

    hip: Array = field(default_factory=lambda: np.array([-0.056276, -0.078490, 0.077260]))
    lumbar: Array = field(default_factory=lambda: np.array([-0.1007, 0.0815, 0.0]))
    femur_len: float = 0.404
    tibia_len: float = 0.400
    ankle: Array = field(default_factory=lambda: np.array([-0.010, -0.400, 0.0]))
    calcn: Array = field(default_factory=lambda: np.array([-0.04877, -0.04195, 0.00792]))
    mtp: Array = field(default_factory=lambda: np.array([0.1788, -0.002, 0.00108]))
    neck: Array | None = None          # torso -> skull chain, when the model has one
    source: str = "GPK_v3 defaults"


#: Landmarks of the GPK skeleton, used when the base model cannot be parsed.
GPK_LANDMARKS = ModelLandmarks()


@dataclass
class RigResult:
    """What :func:`rig_mesh` produced."""

    model_path: Path
    xray_path: Path | None
    stl_dir: Path
    meshes: Dict[str, List[Path]]
    landmarks: Dict[str, float]
    joint_centres: Dict[str, Array]
    n_triangles_in: int
    n_triangles_out: int
    seconds: float

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return (f"{self.model_path.name}: {len(self.meshes)} bodies, "
                f"{self.n_triangles_out} triangles "
                f"(from {self.n_triangles_in}) in {self.seconds:.1f}s")


# --------------------------------------------------------------------------- #
# mesh I/O
# --------------------------------------------------------------------------- #

_STL_DTYPE = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")])


def _read_stl(path: Path) -> Tuple[Array, Array]:
    raw = path.read_bytes()
    n_binary = -1
    if len(raw) >= 84:
        n_binary = int(np.frombuffer(raw[80:84], dtype="<u4")[0])
    if len(raw) == 84 + 50 * n_binary:                      # binary
        rec = np.frombuffer(raw, dtype=_STL_DTYPE, count=n_binary, offset=84)
        V = rec["v"].reshape(-1, 3).astype(np.float64)
        F = np.arange(len(V), dtype=np.int64).reshape(-1, 3)
        return V, F
    # ASCII
    verts = []
    for line in raw.decode("ascii", "ignore").splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            verts.append([float(x) for x in s.split()[1:4]])
    if not verts:
        raise ValueError(f"{path}: neither a valid binary nor ASCII STL")
    V = np.asarray(verts, dtype=np.float64)
    if len(V) % 3:
        raise ValueError(f"{path}: {len(V)} vertices is not a whole number of triangles")
    return V, np.arange(len(V), dtype=np.int64).reshape(-1, 3)


def _read_obj(path: Path) -> Tuple[Array, Array]:
    from .mesh_convert import read_obj          # stdlib reader, already ours
    verts, tris = read_obj(path)
    return np.asarray(verts, dtype=np.float64), np.asarray(tris, dtype=np.int64)


def load_mesh(path: str | Path) -> Tuple[Array, Array]:
    """Read ``.stl`` (binary or ASCII) or ``.obj`` into ``(V, F)`` numpy arrays.

    ``V`` is ``(n, 3)`` float64 vertices, ``F`` is ``(m, 3)`` int64 triangle
    indices. STL vertices come back unwelded — call :func:`weld` before doing
    anything that needs connectivity.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".stl":
        return _read_stl(path)
    if suffix == ".obj":
        return _read_obj(path)
    try:                                        # anything else, if pyvista is around
        import pyvista as pv
    except ImportError as exc:
        raise ValueError(
            f"unsupported mesh format '{suffix}'; .stl and .obj are built in, "
            "other formats need pyvista (pip install pyvista)") from exc
    surf = pv.read(str(path)).extract_surface().triangulate()
    faces = surf.faces.reshape(-1, 4)[:, 1:]
    return np.asarray(surf.points, dtype=np.float64), np.asarray(faces, dtype=np.int64)


def weld(V: Array, F: Array, tol: float | None = None) -> Tuple[Array, Array]:
    """Merge vertices that share a position, dropping the faces that collapse.

    STL has no vertex sharing at all, so every mesh read from one is a pile of
    loose triangles: no edge is shared, no boundary loop can be found, and
    smoothing does nothing. ``tol`` defaults to 1e-6 of the bounding box, which
    is well below any real feature and well above float32 STL round-off.
    """
    span = float(np.ptp(V, axis=0).max()) or 1.0
    tol = tol if tol is not None else span * 1e-6
    keys = np.round(V / tol).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    Vw = V[first]
    Fw = inverse[F]
    good = (Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])
    return Vw, Fw[good]


def decimate(V: Array, F: Array, grid: float) -> Tuple[Array, Array]:
    """Vertex-cluster decimation: one representative vertex per ``grid`` cell.

    Crude next to quadric edge collapse, but it is O(n), needs no neighbour
    structure, and preserves the silhouette — which is all the downstream cuts
    and girth profiles care about. A 1 M-triangle sculpt takes about a second.
    """
    if not grid or grid <= 0:
        return V, F
    keys = np.floor(V / grid).astype(np.int64)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    n = len(counts)
    Vd = np.zeros((n, 3))
    np.add.at(Vd, inverse, V)                    # cluster centroid, not an arbitrary member
    Vd /= counts[:, None]
    Fd = inverse[F]
    good = (Fd[:, 0] != Fd[:, 1]) & (Fd[:, 1] != Fd[:, 2]) & (Fd[:, 0] != Fd[:, 2])
    Fd = Fd[good]
    # drop duplicate faces created by the collapse
    key = np.sort(Fd, axis=1)
    _, uniq = np.unique(key, axis=0, return_index=True)
    return Vd, Fd[np.sort(uniq)]


def taubin_smooth(V: Array, F: Array, passes: int = 8,
                  lam: float = 0.5, mu: float = -0.53) -> Array:
    """Taubin lambda/mu smoothing — takes scan noise off without shrinking.

    A plain Laplacian pass pulls every vertex inwards; alternating a positive
    and a slightly larger negative step is what keeps the volume. Returns new
    vertices; ``F`` is unchanged.
    """
    if passes <= 0:
        return V
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.vstack([E, E[:, ::-1]])
    deg = np.bincount(E[:, 0], minlength=len(V)).astype(np.float64)
    deg[deg == 0] = 1.0
    V = V.copy()
    for i in range(passes * 2):
        acc = np.zeros_like(V)
        np.add.at(acc, E[:, 0], V[E[:, 1]])
        delta = acc / deg[:, None] - V
        V += (lam if i % 2 == 0 else mu) * delta
    return V


def write_stl_fast(V: Array, F: Array, path: str | Path, name: str = "bioscout") -> Path:
    """Write a binary STL from numpy arrays in one buffer write.

    Facet normals are recomputed from the winding, so a piece whose stored
    normals disagreed with its triangles comes out self-consistent.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tri = V[F]                                          # (m, 3, 3)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    mag = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, mag, out=np.zeros_like(n), where=mag > 0)
    rec = np.zeros(len(F), dtype=_STL_DTYPE)
    rec["n"] = n
    rec["v"] = tri
    with open(path, "wb") as fh:
        fh.write(name.encode("ascii", "replace")[:79].ljust(80, b"\0"))
        fh.write(np.uint32(len(F)).tobytes())
        fh.write(rec.tobytes())
    return path


# --------------------------------------------------------------------------- #
# orientation
# --------------------------------------------------------------------------- #


def _unit(v: Array) -> Array:
    n = float(np.linalg.norm(v))
    return v / n if n else v


def _slab(V: Array, y: float, half: float, mask: Array | None = None) -> Array:
    sel = np.abs(V[:, 1] - y) <= half
    if mask is not None:
        sel &= mask
    return V[sel]


def _two_means(P: Array, iters: int = 12) -> Tuple[Array, Array] | None:
    """Split 2-D points into two clusters, seeded at the extremes of their spread."""
    if len(P) < 20:
        return None
    d = P - P.mean(0)
    w, vec = np.linalg.eigh(np.cov(d.T))
    axis = vec[:, int(np.argmax(w))]
    proj = d @ axis
    c = np.stack([P[int(np.argmin(proj))], P[int(np.argmax(proj))]])
    for _ in range(iters):
        which = np.argmin(((P[:, None, :] - c[None]) ** 2).sum(-1), axis=1)
        if not which.any() or which.all():
            return None
        c = np.stack([P[which == 0].mean(0), P[which == 1].mean(0)])
    return c[0], c[1]


def estimate_facing(V: Array, height: float) -> Array:
    """Horizontal unit vector pointing where the figure faces.

    Taken from the **ankles**: split the points in a thin slab at ankle height
    into two clusters and the line between them is the medio-lateral axis, so
    anterior is its perpendicular. Each ankle is a small isolated blob at that
    height, which makes the split unambiguous.

    A trunk-band principal axis is the obvious alternative and is what this did
    first. It is worse: shoulders, arms and any lean or twist all load the
    horizontal covariance, and being a few degrees out rotates the whole figure
    so that the head no longer sits over the feet. The ankles have none of that
    on them.

    The sign comes from the feet: toes stick out in front of the ankle, so the
    footprint is lopsided along the anterior axis.

    This still assumes the feet are planted roughly side by side — a lunge, a
    seated pose or a sculpt mid-kick breaks it. Pass ``RigConfig.facing_yaw``
    there instead; reading it off an eight-view render takes a minute and is
    not a guess.
    """
    y0 = V[:, 1].min()
    axis = None
    ankles = _slab(V, y0 + 0.07 * height, 0.012 * height)
    pair = _two_means(ankles[:, [0, 2]]) if len(ankles) >= 40 else None
    if pair is not None:
        d = pair[1] - pair[0]
        if float(np.hypot(*d)) > 0.05 * height:            # really two ankles apart
            ml = _unit(np.array([d[0], 0.0, d[1]]))
            axis = _unit(np.cross(np.array([0.0, 1.0, 0.0]), ml))

    if axis is None:                                        # fall back to the trunk
        trunk = _slab(V, y0 + 0.62 * height, 0.10 * height)
        P = (trunk if len(trunk) >= 20 else V)[:, [0, 2]]
        P = P - P.mean(0)
        w, vec = np.linalg.eigh(np.cov(P.T))
        ap = vec[:, int(np.argmin(w))]
        axis = _unit(np.array([ap[0], 0.0, ap[1]]))

    feet = _slab(V, y0 + 0.03 * height, 0.03 * height)
    if len(feet) >= 20:
        proj = feet @ axis
        centre = np.median(proj)          # the ankle; the toes are the long tail
        if abs(proj.max() - centre) < abs(centre - proj.min()):
            axis = -axis
    return axis


def orient_mesh(V: Array, cfg: RigConfig) -> Tuple[Array, Dict[str, float]]:
    """Rotate, scale and centre a mesh into the anatomical frame.

    Output convention matches OpenSim: **+x anterior, +y up, +z to the
    subject's right**, ground at ``y = 0``, the midsagittal plane at ``z = 0``
    and the trunk centred at ``x = 0``. Stature becomes
    ``cfg.target_height``.

    Returns the transformed vertices and a dict recording what was applied
    (``scale``, ``yaw_deg``, ``height_in``), which is what you check first when
    a result comes out mirrored or lying down.
    """
    V = np.asarray(V, dtype=np.float64)
    if cfg.up.lower() == "z":                    # CAD export: z up, y forward
        V = V[:, [0, 2, 1]] * np.array([1.0, 1.0, -1.0])
    elif cfg.up.lower() != "y":
        raise ValueError(f"config.up must be 'y' or 'z', got {cfg.up!r}")

    h_in = float(V[:, 1].max() - V[:, 1].min())
    if h_in <= 0:
        raise ValueError("mesh has no vertical extent — is the up axis right?")

    if cfg.facing_yaw is None:
        ant = estimate_facing(V, h_in)
    else:
        a = math.radians(cfg.facing_yaw)
        ant = np.array([math.cos(a), 0.0, math.sin(a)])
    up = np.array([0.0, 1.0, 0.0])
    right = _unit(np.cross(ant, up))              # +x cross +y = +z, i.e. subject's right
    R = np.stack([ant, up, right])                # rows: world -> anatomical

    V = V @ R.T
    scale = cfg.target_height / h_in
    V *= scale

    V[:, 1] -= V[:, 1].min()
    H = cfg.target_height
    # Centre z on the LOWER LEGS, not the trunk or the whole mesh. Between the
    # ankles and the knees there is nothing but two shanks, symmetric about the
    # midline; a trunk band has arms in it and a global centroid has everything,
    # and either can be off by 10 cm on an A-pose scan — which then puts the
    # left/right split through a leg instead of between them.
    shanks = V[(V[:, 1] > 0.10 * H) & (V[:, 1] < 0.25 * H)]
    V[:, 2] -= np.median(shanks[:, 2]) if len(shanks) >= 50 else np.median(V[:, 2])
    trunk = _slab(V, 0.62 * H, 0.10 * H)
    V[:, 0] -= np.median(trunk[:, 0]) if len(trunk) >= 20 else np.median(V[:, 0])

    yaw = math.degrees(math.atan2(ant[2], ant[0]))
    return V, {"scale": scale, "yaw_deg": yaw, "height_in": h_in}


# --------------------------------------------------------------------------- #
# landmarks
# --------------------------------------------------------------------------- #


def _girth_profile(V: Array, lo: float, hi: float, n: int, half: float,
                   side: int = 0) -> Tuple[Array, Array]:
    """Sampled horizontal girth between two heights: ``(levels, girth)``.

    Girth here is the anterior-posterior span plus the medio-lateral span of a
    slab — a cheap stand-in for a perimeter that behaves the same way at a
    minimum, which is all that is asked of it.

    ``side`` restricts the measurement to one leg (``+1`` right, ``-1`` left).
    That is not optional below the crotch: the span across *both* legs is
    dominated by how far apart the feet are planted, and its minimum has
    nothing to do with a knee. Measured per leg, the knee really is the
    narrowest point between calf and thigh.

    ``half`` is the slab half-thickness. Make it a real thickness (about 1 % of
    stature): a paper-thin slab holds a handful of vertices and its girth is
    sampling noise, which reads as a spurious minimum wherever the scan happens
    to be sparse.
    """
    levels = np.linspace(lo, hi, n)
    out = np.full(n, np.inf)
    Vm = V
    if side:
        Vm = V[np.sign(V[:, 2]) == side]
    if len(Vm) == 0:
        return levels, out
    order = np.argsort(Vm[:, 1])
    ys = Vm[order, 1]
    for i, y in enumerate(levels):
        a, b = np.searchsorted(ys, [y - half, y + half])
        if b - a < 20:
            continue
        s = Vm[order[a:b]]
        out[i] = float(np.ptp(s[:, 0]) + np.ptp(s[:, 2]))
    return levels, out


def _narrowest(levels: Array, girth: Array) -> float | None:
    ok = np.isfinite(girth)
    if ok.sum() < 3:
        return None
    return float(levels[ok][int(np.argmin(girth[ok]))])


def _interior_min(levels: Array, girth: Array, margin: float = 0.12) -> float | None:
    """Narrowest level, but only if the minimum is genuinely *inside* the band.

    A minimum sitting on a band edge means the profile was still falling when
    the search ran out of room — the real feature is somewhere else entirely,
    and taking the edge would silently return the edge of a guess. Returning
    ``None`` there lets the caller fall back to something honest.
    """
    ok = np.isfinite(girth)
    if ok.sum() < 5:
        return None
    lv, g = levels[ok], girth[ok]
    i = int(np.argmin(g))
    edge = max(1, int(margin * len(g)))
    if i < edge or i >= len(g) - edge:
        return None
    return float(lv[i])


def _narrowest_limb(V: Array, band: Tuple[float, float], H: float,
                    n: int = 80) -> float | None:
    """Narrowest level of the limb, averaged over the two sides.

    Averaging is deliberate. One leg is often part-occluded in a scan, or
    carries a trouser fold the other does not; taking the mean of two
    independent minima is far steadier than either alone, and the two cuts have
    to be at the same height anyway — the model's segments are symmetric.
    """
    got = []
    for side in (1, -1):
        lv, g = _girth_profile(V, band[0] * H, band[1] * H, n, half=0.010 * H, side=side)
        y = _interior_min(lv, g)
        if y is not None:
            got.append(y)
    if len(got) < 2:                       # one side alone is not evidence
        return None
    return float(np.mean(got))


def _crotch_height(V: Array, H: float, band: Tuple[float, float]) -> float | None:
    """Highest level at which the two legs are still separated.

    A level counts as separated when there is a real hole straddling the
    midsagittal plane: sort the slab's medio-lateral coordinates and measure
    the gap between the last point left of the midline and the first point
    right of it. Below the crotch that gap is the space between the thighs;
    above it, pelvis fills the midline and the gap collapses to the spacing
    between neighbouring vertices.

    Measuring the gap rather than counting midline occupancy is what makes this
    independent of how finely the mesh is tessellated. An occupancy fraction
    needs a threshold that is right for one vertex density and wrong for
    another — too strict and touching thighs read as pelvis, too loose and the
    crotch climbs into the abdomen.

    The search walks down from the top of the band and wants three consecutive
    separated levels before it believes one, so a thin patch in the scan cannot
    put the crotch in the middle of the abdomen.
    """
    lo, hi = band[0] * H, band[1] * H
    n = 200
    levels = np.linspace(hi, lo, n)
    half = 0.008 * H
    min_gap = 0.012 * H
    sep = np.zeros(n, dtype=bool)
    for i, y in enumerate(levels):
        s = _slab(V, y, half)
        if len(s) < 20:
            # Too few points to judge. Carrying the level above forward is the
            # right call rather than scoring it "not separated": a sparse mesh
            # has empty levels scattered everywhere, and treating each as
            # evidence of a pelvis walks the crotch down to the knees.
            sep[i] = sep[i - 1] if i else False
            continue
        z = np.sort(s[np.abs(s[:, 2]) < 0.16 * H, 2])   # hands hang outboard
        if len(z) < 10:
            sep[i] = True
            continue
        k = int(np.searchsorted(z, 0.0))
        if k == 0 or k == len(z):        # nothing on one side of the midline
            sep[i] = True
            continue
        sep[i] = (z[k] - z[k - 1]) >= min_gap
    for i in range(n - 2):
        if sep[i] and sep[i + 1] and sep[i + 2]:
            return float(levels[i])
    return None


def body_landmarks(V: Array, cfg: RigConfig,
                   ml: ModelLandmarks | None = None) -> Dict[str, float]:
    """Find the heights the cuts are made at, in metres above the floor.

    Everything the caller pinned in ``cfg`` is honoured as-is (as a fraction of
    stature); the rest is measured.

    ``hip`` is the anchor, and the only leg landmark measured outright: it is
    the crotch — the highest level at which the two legs are still separate —
    plus 2 % of stature. A hip joint centre cannot be seen on a surface (the
    greater trochanter is buried under muscle), but the crotch is sharp,
    unambiguous, and a fixed distance below the joint across adults.

    ``knee`` and ``ankle`` then **split the measured hip height in the base
    model's own proportions** — femur : tibia : ankle-height. Girth minima are
    the obvious alternative and were tried first: they do not survive contact
    with real scans. Trousers, socks and a calf that tapers smoothly into the
    ankle leave a profile that falls monotonically with no interior minimum at
    all, and a search that takes the band edge anyway returns a confident
    number that is 6 cm wrong. A girth minimum is used only when there is a
    real interior one on *both* legs and it agrees with the proportional
    estimate to within 12 % of stature — that is, only when it confirms.

    ``lumbar`` is fixed at 0.63 stature (roughly L5-S1). ``neck`` is the
    narrowest girth above the shoulders, which is one place the girth search
    does work: the neck is a genuine waist between head and trunk.

    The MTP cut is not here at all — it comes from the model's own foot
    geometry later. A scan foot is usually shorter ahead of the ankle than the
    model's, so cutting the toes at a fraction of foot length puts the joint in
    the wrong place.
    """
    H = cfg.target_height
    ml = ml or GPK_LANDMARKS
    out: Dict[str, float] = {}

    if cfg.hip_h:
        out["hip"] = cfg.hip_h * H
    else:
        crotch = _crotch_height(V, H, cfg.crotch_band)
        if crotch is None:
            out["hip"] = 0.500 * H
        else:
            out["crotch"] = crotch
            hip = crotch + 0.02 * H
            # A crotch outside the anthropometric range means the gap search
            # found something else — a lunge keeps the legs apart to the waist,
            # a long coat closes them at the knee. Clamp and say so rather than
            # cutting a pelvis in half on the strength of it.
            lo, hi = 0.44 * H, 0.56 * H
            if not lo <= hip <= hi:
                logger.warning("crotch at %.3f m (%.2f of stature) is implausible — "
                               "clamping the hip; pin RigConfig.hip_h if this matters",
                               crotch, crotch / H)
                hip = float(np.clip(hip, lo, hi))
            out["hip"] = hip

    # model leg proportions: femur, tibia, and the model's own ankle height
    ankle_h_model = abs(float(ml.calcn[1])) + 0.030      # calcn origin to sole
    leg = ml.femur_len + ml.tibia_len + ankle_h_model
    knee_p = out["hip"] * (ml.tibia_len + ankle_h_model) / leg
    ankle_p = out["hip"] * ankle_h_model / leg

    if cfg.knee_h:
        out["knee"] = cfg.knee_h * H
    else:
        measured = _narrowest_limb(V, cfg.knee_band, H)
        out["knee"] = measured if (measured is not None
                                   and abs(measured - knee_p) < 0.12 * H) else knee_p
    if cfg.ankle_h:
        out["ankle"] = cfg.ankle_h * H
    else:
        measured = _narrowest_limb(V, cfg.ankle_band, H, n=60)
        out["ankle"] = measured if (measured is not None
                                    and abs(measured - ankle_p) < 0.04 * H) else ankle_p

    # The lumbar cut is the model's own hip-to-L5S1 rise above the hip, not a
    # stature fraction: tied to the hip it can never end up below it, which a
    # fixed fraction does the moment the hip estimate moves.
    out["lumbar"] = (cfg.lumbar_h * H if cfg.lumbar_h
                     else out["hip"] + float(ml.lumbar[1] - ml.hip[1]))

    lv, g = _girth_profile(V, cfg.neck_band[0] * H, cfg.neck_band[1] * H,
                           n=60, half=0.008 * H)
    out["neck"] = cfg.neck_h * H if cfg.neck_h else (_narrowest(lv, g) or 0.855 * H)

    # sanity: the cuts must stay in order, or the segments come out inside out
    order = ["ankle", "knee", "hip", "lumbar", "neck"]
    hs = [out[k] for k in order]
    if any(b <= a for a, b in zip(hs, hs[1:])):
        raise ValueError(f"landmarks out of order: {dict(zip(order, hs))} — "
                         "check the up axis and target height, or pin them in RigConfig")
    return out


def joint_centres(V: Array, lm: Dict[str, float], ml: ModelLandmarks,
                  cfg: RigConfig) -> Dict[str, Array]:
    """Joint centres in the oriented mesh frame, metres.

    Knees are measured (the slab centroid at knee height is a good estimate of
    a knee centre). Hips and ankles are *imposed*:

    * Hip separation comes from the model, about the trunk's own centre at hip
      height. A measured separation follows however the legs happen to be
      splayed, and the hands hang at exactly that height and drag a naive
      centroid sideways.
    * The ankle sits 27 % of the foot length back from the toe, on the model's
      own medio-lateral line for that leg. A foot slab centroid drifts onto the
      instep and lands the ankle half-way along the foot.
    """
    H = cfg.target_height
    out: Dict[str, Array] = {}

    # The midline is z = 0 by construction (orient_mesh centred on the shanks),
    # so do not re-measure it here: at hip height the hands hang beside the
    # thighs and a median over that slab lands 20 cm off to one side, which
    # then puts the whole pelvis — and everything referenced to it — there too.
    cz = 0.0
    trunk = _slab(V, lm["hip"], 0.02 * H)
    trunk = trunk[np.abs(trunk[:, 2]) < 0.10 * H] if len(trunk) else trunk
    cx = float(np.median(trunk[:, 0])) if len(trunk) else 0.0

    for side, sgn in (("r", 1.0), ("l", -1.0)):
        hip = np.array([cx, lm["hip"], cz + sgn * abs(ml.hip[2])])
        out[f"hip_{side}"] = hip

        leg = V[(np.abs(V[:, 1] - lm["knee"]) < 0.015 * H) & (np.sign(V[:, 2] - cz) == sgn)]
        if len(leg) >= 10:
            knee = np.array([float(np.median(leg[:, 0])), lm["knee"],
                             float(np.median(leg[:, 2]))])
        else:
            knee = np.array([hip[0], lm["knee"], hip[2]])
        out[f"knee_{side}"] = knee

        foot = V[(V[:, 1] < lm["ankle"]) & (np.sign(V[:, 2] - cz) == sgn)]
        if len(foot) >= 20:
            x0, x1 = float(foot[:, 0].min()), float(foot[:, 0].max())
            ankle = np.array([x1 - 0.73 * (x1 - x0), lm["ankle"],
                              float(np.median(foot[:, 2]))])
        else:
            ankle = np.array([knee[0], lm["ankle"], knee[2]])
        out[f"ankle_{side}"] = ankle

    hip_mid = 0.5 * (out["hip_r"] + out["hip_l"])
    # pelvis origin is wherever the model says the hip sits relative to it
    out["pelvis"] = hip_mid - np.array([ml.hip[0], ml.hip[1], 0.0])
    out["lumbar"] = out["pelvis"] + ml.lumbar
    return out


# --------------------------------------------------------------------------- #
# base model
# --------------------------------------------------------------------------- #


def _joint_by_name(model: ET.Element, *names: str) -> ET.Element | None:
    js = model.find("JointSet/objects")
    if js is None:
        return None
    lookup = {j.get("name", "").lower(): j for j in js}
    for n in names:
        if n in lookup:
            return lookup[n]
    for n in names:                                    # substring fallback
        for k, j in lookup.items():
            if n in k:
                return j
    return None


def _frame_translation(joint: ET.Element, which: str) -> Array | None:
    """``which`` is 'parent' or 'child'; returns that offset frame's translation."""
    want = joint.findtext(f"socket_{which}_frame", "").strip().lstrip("/").split("/")[-1]
    for f in joint.iter("PhysicalOffsetFrame"):
        if f.get("name") == want or want.endswith(f.get("name", "\0")):
            t = f.findtext("translation")
            if t:
                return np.array([float(x) for x in t.split()])
    frames = list(joint.iter("PhysicalOffsetFrame"))
    if frames:
        idx = 0 if which == "parent" else min(1, len(frames) - 1)
        t = frames[idx].findtext("translation")
        if t:
            return np.array([float(x) for x in t.split()])
    return None


def read_model_landmarks(osim: str | Path) -> ModelLandmarks:
    """Read hip / knee / ankle / MTP geometry out of a base ``.osim``.

    Falls back to :data:`GPK_LANDMARKS` for anything the file does not name in
    a way this can recognise, so an unusual model degrades to slightly-wrong
    segment lengths rather than an exception. ``ModelLandmarks.source`` records
    which happened — check it when a limb comes out the wrong length.
    """
    ml = ModelLandmarks(source=str(osim))
    try:
        root = ET.parse(str(osim)).getroot()
    except (ET.ParseError, OSError) as exc:
        logger.warning("could not parse %s (%s) — using GPK defaults", osim, exc)
        return ModelLandmarks()
    model = root.find("Model") if root.find("Model") is not None else root

    j = _joint_by_name(model, "hip_r")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None:
        ml.hip = t

    j = _joint_by_name(model, "back", "lumbar", "back_joint")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None:
        ml.lumbar = t

    # A knee that is one offset from the femur origin gives the femur length
    # directly. GPK's is not: the Lerner mechanism puts the tibia on a chain of
    # welds and condyle joints whose first offset is zero, so a naive read
    # returns a 0 m femur. Keep the default when that happens rather than
    # believing it.
    j = _joint_by_name(model, "walker_knee_r", "knee_r", "lerner_knee_r")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None and abs(t[1]) > 0.05:
        ml.femur_len = float(abs(t[1]))

    j = _joint_by_name(model, "ankle_r")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None:
        ml.ankle = t
        ml.tibia_len = float(abs(t[1])) or ml.tibia_len

    # subtalar's PARENT offset (talus -> calcn) is the one that carries the
    # foot; the child offset is zero in every model that follows the
    # convention, and reading it lands the ankle on the floor.
    j = _joint_by_name(model, "subtalar_r", "calcn_r")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None and abs(t[1]) > 1e-6:
        ml.calcn = t

    j = _joint_by_name(model, "mtp_r")
    t = _frame_translation(j, "parent") if j is not None else None
    if t is not None:
        ml.mtp = t
    return ml


def _body_names(osim: str | Path) -> List[str]:
    try:
        root = ET.parse(str(osim)).getroot()
    except (ET.ParseError, OSError):
        return []
    model = root.find("Model") if root.find("Model") is not None else root
    bs = model.find("BodySet/objects")
    if bs is not None:
        return [b.get("name", "") for b in bs]
    return [b.get("name", "") for b in model.iter("Body") if b.get("name")]


def default_base_model(search: Sequence[str | Path] = ()) -> Path:
    """Locate a base skeleton: the highest-versioned GPK model that exists.

    Looks in the given directories, then in ``bioscout/models``, then the
    working directory, preferring ``GPK_v4`` over ``v3`` over an unversioned
    ``GPK_*``. Raises :class:`FileNotFoundError` listing where it looked, which
    is more useful than silently rigging onto the wrong skeleton.
    """
    roots: List[Path] = [Path(p) for p in search]
    roots.append(Path(__file__).resolve().parent.parent / "models")
    roots.append(Path.cwd())
    roots.append(Path.cwd() / "GPK")
    candidates: List[Tuple[int, Path]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.glob("*.osim")):
            n = p.name.lower()
            if "gpk" not in n:
                continue
            rank = 0
            for v in range(9, 0, -1):
                if f"v{v}" in n:
                    rank = v
                    break
            candidates.append((rank, p))
    if not candidates:
        raise FileNotFoundError(
            "no GPK base model found; pass base_model=<path to an .osim>. "
            f"Looked in: {', '.join(str(r) for r in roots)}")
    candidates.sort(key=lambda c: (-c[0], len(str(c[1]))))
    return candidates[0][1]


# --------------------------------------------------------------------------- #
# segmentation
# --------------------------------------------------------------------------- #

#: Which body each cut region rides on, and which model bodies it needs.
SEGMENTS = ("toes_r", "toes_l", "calcn_r", "calcn_l", "tibia_r", "tibia_l",
            "femur_r", "femur_l", "pelvis", "torso", "skull")


def segment_triangles(V: Array, F: Array, lm: Dict[str, float], jc: Dict[str, Array],
                      ml: ModelLandmarks, cfg: RigConfig,
                      bodies: Sequence[str]) -> Array:
    """Label every triangle with the body it belongs to (index into SEGMENTS).

    Cuts are horizontal planes on the triangle centroid, with the side decided
    by z. The hip cut is deliberately horizontal rather than perpendicular to
    the thigh: a perpendicular cut on a splayed leg climbs up the outside of
    the hip and takes a wedge of pelvis with it.
    """
    C = V[F].mean(axis=1)
    labels = np.full(len(F), SEGMENTS.index("torso"), dtype=np.int8)
    has_skull = "skull" in bodies

    right = C[:, 2] >= 0.5 * (jc["hip_r"][2] + jc["hip_l"][2])

    above_ankle = C[:, 1] >= lm["ankle"]
    labels[C[:, 1] < lm["hip"]] = -1                     # placeholder, refined below

    # legs
    leg = C[:, 1] < lm["hip"]
    thigh = leg & (C[:, 1] >= lm["knee"])
    shank = leg & (C[:, 1] < lm["knee"]) & above_ankle
    foot = leg & ~above_ankle

    labels[thigh & right] = SEGMENTS.index("femur_r")
    labels[thigh & ~right] = SEGMENTS.index("femur_l")
    labels[shank & right] = SEGMENTS.index("tibia_r")
    labels[shank & ~right] = SEGMENTS.index("tibia_l")

    for side, sel in (("r", right), ("l", ~right)):
        ank = jc[f"ankle_{side}"]
        mtp_x = ank[0] + ml.calcn[0] + ml.mtp[0]         # model's own MTP, not a fraction
        f_side = foot & sel
        labels[f_side & (C[:, 0] >= mtp_x)] = SEGMENTS.index(f"toes_{side}")
        labels[f_side & (C[:, 0] < mtp_x)] = SEGMENTS.index(f"calcn_{side}")

    # trunk
    labels[(C[:, 1] >= lm["hip"]) & (C[:, 1] < lm["lumbar"])] = SEGMENTS.index("pelvis")
    labels[C[:, 1] >= lm["lumbar"]] = SEGMENTS.index("torso")
    if has_skull:
        labels[C[:, 1] >= lm["neck"]] = SEGMENTS.index("skull")

    if (labels < 0).any():                               # nothing should be left over
        labels[labels < 0] = SEGMENTS.index("pelvis")

    # A hand resting against the thigh is CONNECTED to it, so the island test
    # below cannot see it — but it is a long way off the leg's own axis, and
    # nothing that is really thigh is. Cap the radius first, islands second.
    torso = SEGMENTS.index("torso")
    pelvis = SEGMENTS.index("pelvis")
    r_max = 0.075 * cfg.target_height
    for side in ("r", "l"):
        for seg, (a, b) in ((f"femur_{side}", (f"hip_{side}", f"knee_{side}")),
                            (f"tibia_{side}", (f"knee_{side}", f"ankle_{side}"))):
            i = SEGMENTS.index(seg)
            sel = labels == i
            if not sel.any():
                continue
            far = _dist_to_segment(C[sel], jc[a], jc[b]) > r_max
            idx = np.where(sel)[0][far]
            # Two very different things sit off a thigh's axis: a hand, which
            # hangs lateral to the leg, and a skirt or coat, which surrounds
            # the midline. Send the lateral ones to the torso with the arm they
            # belong to, and the central ones to the pelvis — a skirt that
            # swings with a femur looks far worse than one rigid to the hips.
            central = np.abs(C[idx][:, 2]) < 0.15 * cfg.target_height
            labels[idx[central]] = pelvis
            labels[idx[~central]] = torso
    return _reassign_islands(F, labels)


def _dist_to_segment(P: Array, a: Array, b: Array) -> Array:
    """Perpendicular distance from each point to the line segment ``a``-``b``."""
    d = b - a
    L2 = float(d @ d) or 1e-12
    t = np.clip(((P - a) @ d) / L2, 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * d), axis=1)


def _face_components(F: Array, n_vertices: int) -> Array:
    """Connected-component id per face, by shared vertices. Union-find, O(n a(n))."""
    parent = np.arange(n_vertices, dtype=np.int64)

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for tri in F:
        r = find(int(tri[0]))
        for v in tri[1:]:
            s = find(int(v))
            if s != r:
                parent[s] = r
    return np.array([find(int(t[0])) for t in F], dtype=np.int64)


def _reassign_islands(F: Array, labels: Array, min_frac: float = 0.25) -> Array:
    """Send a leg body's disconnected offcuts to the torso.

    In an A-pose scan the hands hang at exactly hip height, so a horizontal hip
    cut hands each thigh a free-floating lump of fingers several centimetres
    outboard of the leg. Nothing about the cut can tell them apart — but they
    are not *connected* to the leg, and the leg's own piece is always the big
    one. Anything under ``min_frac`` of a body's largest component goes to the
    torso, which is where an arm belongs on a model with no arm bodies.

    Deleting the offcuts instead would leave holes where the hands were; the
    torso carries them, still in the right place, still rigid to the trunk.
    """
    torso = SEGMENTS.index("torso")
    n_v = int(F.max()) + 1 if len(F) else 0
    out = labels.copy()
    for seg in ("femur_r", "femur_l", "tibia_r", "tibia_l", "pelvis"):
        i = SEGMENTS.index(seg)
        sel = np.where(labels == i)[0]
        if len(sel) < 50:
            continue
        comp = _face_components(F[sel], n_v)
        ids, counts = np.unique(comp, return_counts=True)
        biggest = counts.max()
        drop = set(ids[counts < min_frac * biggest].tolist())
        if drop:
            out[sel[np.isin(comp, list(drop))]] = torso
    return out


# --------------------------------------------------------------------------- #
# closing the cuts
# --------------------------------------------------------------------------- #


def boundary_loops(F: Array) -> List[List[int]]:
    """Ordered vertex loops around every hole in a triangle soup.

    An edge used by exactly one triangle is on a boundary. Chaining those edges
    head-to-tail gives the loops; the winding is inherited from the faces, so
    fanning a loop in the order returned produces outward-facing caps.
    """
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(E, axis=1)
    _, idx, counts = np.unique(key, axis=0, return_index=True, return_counts=True)
    border = E[idx[counts == 1]]
    if len(border) == 0:
        return []
    nxt: Dict[int, List[int]] = {}
    for a, b in border:
        nxt.setdefault(int(a), []).append(int(b))
    loops: List[List[int]] = []
    while nxt:
        start = next(iter(nxt))
        loop = [start]
        cur = start
        while True:
            opts = nxt.get(cur)
            if not opts:
                break
            nxt_v = opts.pop()
            if not opts:
                nxt.pop(cur, None)
            if nxt_v == start:
                break
            if nxt_v in loop:                 # self-intersecting chain, bail out
                break
            loop.append(nxt_v)
            cur = nxt_v
        if len(loop) >= 3:
            loops.append(loop)
    return loops


def cap_open_boundaries(V: Array, F: Array, min_len: int = 3,
                        passes: int = 4) -> Tuple[Array, Array]:
    """Close every hole by fanning its loop to the loop's centroid.

    A plane cut leaves an open shell. In a viewer with back-face culling that
    is not a subtle artefact — flex the knee and you are looking straight into
    the inside of the thigh. Loops shorter than ``min_len`` are skipped; the
    default of 3 caps everything, because a stray triangle costs nothing and a
    hole left in a small piece is still a hole.

    Fanning is exact for a convex loop and acceptable for the mildly concave
    ones a joint cut produces. A deeply concave loop (a cut through splayed
    fingers) gets a slightly bulged cap, not a self-intersecting one.
    """
    for _ in range(passes):
        loops = [lp for lp in boundary_loops(F) if len(lp) >= min_len]
        if not loops:
            return V, F
        Vn, Fn, n = [V], [F], len(V)
        for lp in loops:
            centroid = V[lp].mean(axis=0)
            Vn.append(centroid[None, :])
            c = n
            n += 1
            ring = np.asarray(lp, dtype=np.int64)
            tri = np.stack([np.full(len(ring), c), ring, np.roll(ring, -1)], axis=1)
            Fn.append(tri)
        V, F = np.vstack(Vn), np.vstack(Fn).astype(np.int64)
        # A loop-tracing walk can break on a self-touching chain and leave a
        # short new boundary behind, so cap again rather than assume one pass
        # closed the piece.
    if boundary_loops(F):
        logger.debug("piece still open after %d capping passes", passes)
    return V, F


def ellipsoid(centre: Array, radii: Array, nu: int = 24, nv: int = 16) -> Tuple[Array, Array]:
    """A closed, outward-wound ellipsoid — the shape used for joint fillers.

    Written out explicitly rather than taken from a library because the pole
    caps are where a naive UV sphere goes wrong: shared pole vertices are easy
    to wind inside out, which is invisible to a signed-volume check and shows
    up as a small hole at each pole in any back-face-culling viewer.
    """
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    v = np.linspace(0, np.pi, nv + 2)[1:-1]
    uu, vv = np.meshgrid(u, v, indexing="ij")
    P = np.stack([np.sin(vv) * np.cos(uu), np.cos(vv), np.sin(vv) * np.sin(uu)], axis=-1)
    V = P.reshape(-1, 3) * radii + centre
    top = len(V)
    V = np.vstack([V, centre + np.array([0, radii[1], 0]), centre - np.array([0, radii[1], 0])])

    F: List[Tuple[int, int, int]] = []
    def vid(i, j):
        return (i % nu) * nv + j

    for i in range(nu):
        for j in range(nv - 1):
            a, b, c, d = vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)
            F.append((a, b, c))
            F.append((a, c, d))
        F.append((top, vid(i + 1, 0), vid(i, 0)))            # north cap
        F.append((top + 1, vid(i, nv - 1), vid(i + 1, nv - 1)))  # south cap
    return V, np.asarray(F, dtype=np.int64)


# --------------------------------------------------------------------------- #
# un-posing
# --------------------------------------------------------------------------- #


def _align_rotation(long_axis: Array, anterior: Array = np.array([1.0, 0.0, 0.0])) -> Array:
    """Rotation taking a segment's proximal->distal axis onto the body's -y.

    Rows of the result are the body's own basis expressed in mesh coordinates,
    so ``(P - origin) @ R.T`` puts mesh points in the body frame.
    """
    ey = -_unit(long_axis)
    ex = anterior - float(anterior @ ey) * ey
    if np.linalg.norm(ex) < 1e-9:                     # axis parallel to anterior
        ex = np.array([0.0, 0.0, 1.0]) - float(np.array([0.0, 0.0, 1.0]) @ ey) * ey
    ex = _unit(ex)
    ez = np.cross(ex, ey)
    return np.stack([ex, ey, ez])


def _transform_segment(P: Array, origin: Array, R: Array, axial: float = 1.0) -> Array:
    Q = (P - origin) @ R.T
    if axial != 1.0:
        Q[:, 1] *= axial
    return Q


def segment_transforms(jc: Dict[str, Array], ml: ModelLandmarks,
                       align_limbs: bool = True) -> Dict[str, Tuple[Array, Array, float]]:
    """``body -> (origin, rotation, axial scale)`` mapping mesh space to body frames.

    The axial scale is what makes a scan of one person sit on another's
    skeleton: the mesh's own hip-to-knee distance is stretched or squashed onto
    the model's femur length, and likewise knee-to-ankle onto the tibia. It is
    applied only along the segment's long axis, so girths are untouched.
    """
    I = np.eye(3)
    out: Dict[str, Tuple[Array, Array, float]] = {}

    out["pelvis"] = (jc["pelvis"], I, 1.0)
    out["torso"] = (jc["lumbar"], I, 1.0)
    out["skull"] = (jc["lumbar"], I, 1.0)          # refined by the caller if a neck exists

    for side in ("r", "l"):
        hip, knee, ankle = jc[f"hip_{side}"], jc[f"knee_{side}"], jc[f"ankle_{side}"]

        d = knee - hip
        R = _align_rotation(d) if align_limbs else I
        out[f"femur_{side}"] = (hip, R, ml.femur_len / max(float(np.linalg.norm(d)), 1e-6))

        d = ankle - knee
        R = _align_rotation(d) if align_limbs else I
        out[f"tibia_{side}"] = (knee, R, ml.tibia_len / max(float(np.linalg.norm(d)), 1e-6))

        calcn = ankle + np.array([ml.calcn[0], ml.calcn[1], 0.0])
        out[f"calcn_{side}"] = (calcn, I, 1.0)
        out[f"toes_{side}"] = (calcn + np.array([ml.mtp[0], ml.mtp[1], 0.0]), I, 1.0)
    return out


# --------------------------------------------------------------------------- #
# osim writing
# --------------------------------------------------------------------------- #


def _mesh_elem(name: str, rel_path: str, colour: str, opacity: float) -> ET.Element:
    m = ET.Element("Mesh", {"name": name})
    ET.SubElement(m, "socket_frame").text = ".."
    ET.SubElement(m, "scale_factors").text = "1 1 1"
    ap = ET.SubElement(m, "Appearance")
    ET.SubElement(ap, "visible").text = "true"
    ET.SubElement(ap, "opacity").text = f"{opacity:g}"
    ET.SubElement(ap, "color").text = colour
    ET.SubElement(m, "mesh_file").text = rel_path
    return m


def _indent(el: ET.Element, level: int = 0) -> None:
    pad = "\n" + "\t" * level
    if len(el):
        if not (el.text or "").strip():
            el.text = pad + "\t"
        for c in el:
            _indent(c, level + 1)
        if not (el[-1].tail or "").strip():
            el[-1].tail = pad
    if level and not (el.tail or "").strip():
        el.tail = pad


def write_osim(base: str | Path, out_path: str | Path, meshes: Dict[str, List[Path]],
               stl_rel: str, *, colour: str = "0.89 0.71 0.60", opacity: float = 1.0,
               keep_bones: bool = False, bone_dir: str = "Geometry",
               model_name: str | None = None) -> Path:
    """Copy a base model, swapping each body's display geometry for our meshes.

    Everything that is not ``<attached_geometry>`` — joints, coordinates,
    constraints, forces, markers, wrap objects — is copied verbatim, which is
    the whole point: the result drives from the same motion files and setup XML
    as the model it came from.

    ``keep_bones=True`` leaves the original bone meshes in place under the skin
    so you can see whether the surface actually contains the skeleton. That
    x-ray copy is the fastest check that a rig came out right.
    """
    base, out_path = Path(base), Path(out_path)
    tree = ET.parse(str(base))
    root = tree.getroot()
    model = root.find("Model") if root.find("Model") is not None else root
    if model_name:
        model.set("name", model_name)

    bodies = model.find("BodySet/objects")
    if bodies is None:
        raise ValueError(f"{base} has no BodySet — is it an OpenSim model?")

    n_skin = 0
    for body in bodies:
        name = body.get("name", "")
        groups = list(body.iter("attached_geometry"))
        ag = body.find("attached_geometry")
        if ag is None:
            ag = ET.SubElement(body, "attached_geometry")
            groups.append(ag)
        for g in groups:
            for m in list(g.findall("Mesh")):
                g.remove(m)
                if keep_bones:
                    f = m.findtext("mesh_file") or ""
                    if not f.startswith(bone_dir):
                        m.find("mesh_file").text = f"{bone_dir}/{f}"
                    ap = m.find("Appearance") or ET.SubElement(m, "Appearance")
                    for tag, val in (("visible", "true"), ("opacity", "1"),
                                     ("color", "0.93 0.91 0.85")):
                        e = ap.find(tag)
                        (e if e is not None else ET.SubElement(ap, tag)).text = val
                    g.append(m)
        for i, p in enumerate(meshes.get(name, []), 1):
            ag.append(_mesh_elem(f"{name}_skin_{i}", f"{stl_rel}/{Path(p).name}",
                                 colour, opacity))
            n_skin += 1

    _indent(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out_path), encoding="UTF-8", xml_declaration=True)
    logger.info("%s: %d meshes attached", out_path.name, n_skin)
    return out_path


def verify_kinematics(base: str | Path, out: str | Path) -> None:
    """Raise unless ``out`` still has the base model's joints and coordinates.

    Cheap, and it catches the failure mode that matters: a geometry swap that
    quietly dropped a joint would send every downstream ``.mot`` file off a
    cliff, and nothing about the rendered model would look wrong.
    """
    def names(p):
        m = ET.parse(str(p)).getroot()
        m = m.find("Model") if m.find("Model") is not None else m
        js = m.find("JointSet/objects")
        return ([j.get("name") for j in js] if js is not None else [],
                [c.get("name") for c in m.iter("Coordinate")])

    bj, bc = names(base)
    oj, oc = names(out)
    if bj != oj:
        raise AssertionError(f"joint set changed: {set(bj) ^ set(oj)}")
    if bc != oc:
        raise AssertionError(f"coordinate set changed: {set(bc) ^ set(oc)}")


# --------------------------------------------------------------------------- #
# the pipeline
# --------------------------------------------------------------------------- #


def rig_mesh(src: str | Path, *, base_model: str | Path | None = None,
             out_dir: str | Path = ".", name: str = "subject",
             config: RigConfig | None = None) -> RigResult:
    """Rig a whole-body surface mesh onto an OpenSim skeleton.

    Parameters
    ----------
    src : str or Path
        The scan or sculpt: ``.stl``, ``.obj``, or anything pyvista reads.
        One connected human-shaped surface, standing, arms clear of the body.
    base_model : str or Path, optional
        Skeleton to rig onto. Defaults to the highest-versioned GPK model
        :func:`default_base_model` can find. Any ``.osim`` works; body names
        are matched against it, so a model with ``skull`` gets a head that
        follows the neck and one without carries the head on ``torso``.
    out_dir : str or Path
        Written to as ``<out_dir>/<name>.osim`` plus ``<out_dir>/stl_<name>/``.
    name : str
        Stem for the model and its STL folder.
    config : RigConfig, optional
        See :class:`RigConfig`. The one field worth setting on every run is
        ``target_height``.

    Returns
    -------
    RigResult
        Paths written, the landmarks and joint centres that were used, and
        timing. Print ``result.landmarks`` before believing any output — a rig
        that came out wrong almost always has one landmark obviously off.

    Raises
    ------
    ValueError
        If the landmarks come out in the wrong vertical order, which means the
        mesh is not a standing human in the orientation the config claims.
    """
    t0 = time.perf_counter()
    cfg = config or RigConfig()
    src = Path(src)
    out_dir = Path(out_dir)
    base = Path(base_model) if base_model else default_base_model([src.parent])

    V, F = load_mesh(src)
    n_in = len(F)
    V, F = weld(V, F)
    height_raw = float(V[:, 1].max() - V[:, 1].min()) if cfg.up == "y" else \
        float(V[:, 2].max() - V[:, 2].min())
    V, F = decimate(V, F, cfg.resolved_grid(height_raw))
    if cfg.smooth:
        V = taubin_smooth(V, F, cfg.smooth)
    logger.info("%s: %d -> %d triangles", src.name, n_in, len(F))

    V, applied = orient_mesh(V, cfg)
    ml = read_model_landmarks(base)
    bodies = _body_names(base)
    lm = body_landmarks(V, cfg, ml)

    model_leg = ml.femur_len + ml.tibia_len + abs(float(ml.calcn[1])) + 0.030
    if cfg.fit_legs:
        k = model_leg / lm["hip"]
        if abs(k - 1.0) > 1e-3:
            cfg = replace(cfg, target_height=cfg.target_height * k)
            V *= k
            V[:, 1] -= V[:, 1].min()
            lm = body_landmarks(V, cfg, ml)
            applied["scale"] *= k
            logger.info("fit_legs: rescaled by %.3f, finished height %.2f m",
                        k, cfg.target_height)
    elif not 0.88 <= lm["hip"] / model_leg <= 1.14:
        logger.warning(
            "the figure's hip is %.2f m but the model's is %.2f m — the limbs "
            "will be stretched by %.0f%% to fit. Use fit_legs=True (--fit-legs) "
            "to scale by leg length instead, or rig at about %.2f m.",
            lm["hip"], model_leg, 100 * abs(model_leg / lm["hip"] - 1),
            cfg.target_height * model_leg / lm["hip"])

    jc = joint_centres(V, lm, ml, cfg)
    logger.info("landmarks (m): %s", {k: round(v, 3) for k, v in lm.items()})

    labels = segment_triangles(V, F, lm, jc, ml, cfg, bodies)
    xforms = segment_transforms(jc, ml)

    stl_dir = out_dir / f"stl_{name}"
    stl_dir.mkdir(parents=True, exist_ok=True)
    meshes: Dict[str, List[Path]] = {}
    n_out = 0

    # a joint's filler is carried by the PROXIMAL body and sized from the
    # DISTAL one's cut, so gather the cut radii first
    cut_radius: Dict[str, float] = {}
    for i, seg in enumerate(SEGMENTS):
        sel = labels == i
        if sel.sum() < 4:
            continue
        P = V[np.unique(F[sel])]
        cut_radius[seg] = float(np.linalg.norm(P[:, [0, 2]] - P[:, [0, 2]].mean(0),
                                               axis=1).mean())

    fillers = {"femur_r": ("hip_r", "femur_r"), "femur_l": ("hip_l", "femur_l"),
               "tibia_r": ("knee_r", "tibia_r"), "tibia_l": ("knee_l", "tibia_l"),
               "calcn_r": ("ankle_r", "calcn_r"), "calcn_l": ("ankle_l", "calcn_l")}
    proximal_of = {"femur_r": "pelvis", "femur_l": "pelvis",
                   "tibia_r": "femur_r", "tibia_l": "femur_l",
                   "calcn_r": "tibia_r", "calcn_l": "tibia_l"}

    for i, seg in enumerate(SEGMENTS):
        if seg not in bodies:
            continue
        sel = labels == i
        if sel.sum() < 4:
            continue
        used = np.unique(F[sel])
        remap = np.full(len(V), -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        Vs, Fs = V[used], remap[F[sel]]
        if cfg.cap_cuts:
            Vs, Fs = cap_open_boundaries(Vs, Fs)

        origin, R, axial = xforms[seg]
        Vs = _transform_segment(Vs, origin, R, axial)

        if cfg.joint_fillers:
            for distal, (jname, _d) in fillers.items():
                if proximal_of.get(distal) != seg or distal not in cut_radius:
                    continue
                r = cut_radius[distal] * cfg.filler_scale
                c = _transform_segment(jc[jname][None, :], origin, R, axial)[0]
                Vb, Fb = ellipsoid(c, np.array([r, r, r]))
                Fs = np.vstack([Fs, Fb + len(Vs)])
                Vs = np.vstack([Vs, Vb])

        p = write_stl_fast(Vs, Fs, stl_dir / f"{name}_{seg}.stl", name=f"{name}_{seg}")
        meshes.setdefault(seg, []).append(p)
        n_out += len(Fs)

    # head and arms have no bodies of their own in a GPK-style model: whatever
    # was labelled torso already contains them, so nothing extra to do here.

    model_path = write_osim(base, out_dir / f"{name}.osim", meshes, stl_dir.name,
                            colour=cfg.skin_colour, opacity=cfg.opacity,
                            model_name=name)
    verify_kinematics(base, model_path)

    xray_path = None
    if cfg.keep_bones:
        xray_path = write_osim(base, out_dir / f"{name}_xray.osim", meshes, stl_dir.name,
                               colour=cfg.skin_colour, opacity=0.45, keep_bones=True,
                               model_name=f"{name}_xray")
        verify_kinematics(base, xray_path)

    return RigResult(model_path=model_path, xray_path=xray_path, stl_dir=stl_dir,
                     meshes=meshes, landmarks={**lm, **applied}, joint_centres=jc,
                     n_triangles_in=n_in, n_triangles_out=n_out,
                     seconds=time.perf_counter() - t0)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m bioscout.session.movement_detector.mesh_rig",
        description="Rig a whole-body surface mesh (.stl/.obj) onto an OpenSim skeleton.")
    p.add_argument("src", help="scan or sculpt to rig")
    p.add_argument("-o", "--out", default=".", help="output folder (default: .)")
    p.add_argument("-n", "--name", default=None, help="model name (default: source stem)")
    p.add_argument("-b", "--base", default=None,
                   help="base .osim (default: the newest GPK model found)")
    p.add_argument("--height", type=float, default=1.80,
                   help="finished stature in metres (default: 1.80)")
    p.add_argument("--yaw", type=float, default=None,
                   help="anterior direction in degrees about up; omit to auto-detect")
    p.add_argument("--up", default="y", choices=["y", "z"], help="source up axis")
    p.add_argument("--grid", type=float, default=None,
                   help="decimation cell in source units (default: height/700)")
    p.add_argument("--smooth", type=int, default=0, help="Taubin smoothing passes")
    p.add_argument("--fit-legs", action="store_true",
                   help="scale to the model's leg length instead of --height; use "
                        "when the figure's proportions differ from the skeleton's")
    p.add_argument("--no-caps", action="store_true", help="leave cut faces open")
    p.add_argument("--no-fillers", action="store_true", help="skip joint filler blobs")
    p.add_argument("--xray", action="store_true", help="also write a bones-visible model")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO,
                        format="[rig] %(message)s")
    cfg = RigConfig(target_height=a.height, facing_yaw=a.yaw, up=a.up, grid=a.grid,
                    smooth=a.smooth, cap_cuts=not a.no_caps, fit_legs=a.fit_legs,
                    joint_fillers=not a.no_fillers, keep_bones=a.xray)
    try:
        res = rig_mesh(a.src, base_model=a.base, out_dir=a.out,
                       name=a.name or Path(a.src).stem, config=cfg)
    except Exception as exc:
        print(f"[rig] ERROR: {exc}")
        return 1
    print(f"[rig] {res}")
    print(f"[rig] landmarks (m): "
          + ", ".join(f"{k}={v:.3f}" for k, v in sorted(res.landmarks.items())))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
