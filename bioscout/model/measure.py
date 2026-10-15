"""Measurements from bone meshes (STL) — model-independent building blocks.

Everything here takes plain meshes / arrays and returns numbers, so it can be
used on raw MRI segmentations or on the meshes behind an ``.osim`` model.
:class:`bioscout.model.geometry.Measure` wraps these per model.

Acetabular coverage
-------------------
1. Fit a sphere to the femoral head (least squares, iterative outlier trim).
2. Sample directions on the head sphere and decide which are covered. A
   direction counts as covered when the acetabulum is within ``threshold_mm``
   of the head surface there (default 2.5 mm), by one of two methods:
   ``nearest`` (default) measures the distance to the nearest acetabulum
   vertex -- fast; ``rays`` casts a ray from the head centre and takes the hit
   distance -- exact, but slow, because trimesh casts rays in pure python
   unless embree is installed. ``min_f``/``max_f`` (rays only) give the hit
   window directly instead of deriving it from ``threshold_mm``.
3. Report covered area on the head sphere (mm^2) and % of the full sphere.
   With a pelvic frame (landmarks: ASIS_R, ASIS_L, PUBIC_SYMPHYSIS) also:
   % of the superior hemisphere, anterior/superior/posterior sectors, and
   lateral/anterior centre-edge angles (LCEA/ACEA).

Torsional geometry (from an ``.osim`` model)
-------------------------------------------
Neck-shaft angle, femoral anteversion and tibial torsion of the model that is
actually simulated. Joint centres and the medio-lateral axes come from the
model's own joint frames (expressed in the femur/tibia body frames); the
femoral neck axis comes from the femur mesh the model draws, by finding the
smallest neck cross-section (the isthmus). Any of these can be replaced with
digitised landmarks. Angles in degrees, distances in mm; positive anteversion
= neck anterior to the posterior condylar axis, positive tibial torsion =
external.

CLI::

    bioscout model measure coverage FOLDER [--method nearest|rays] [--threshold MM]
        [--side r l] [--landmarks CSV] [-o CSV]
        [--plots DIR | --no-plots]   (per-hip 3D figure + summary dot plot)
    bioscout model measure coverage --acetabulum A.stl --femoral-head F.stl --side l
    bioscout model measure jcf-coverage FOLDER --model m.osim --jra jra.sto --ik ik.mot
        --side r --mass 80        (peak contact force heat map on the head)

    bioscout model measure markups FOLDER_OR_FILES [-o CSV] [--json]
        (neck-shaft angle + anteversion straight from the MRI landmarks)

    bioscout model measure torsion MODEL.osim [--side r l] [--landmarks CSV]
        [--json] [-o CSV] [--json-out FILE | --no-json-file]
        (also writes <model>_torsion_angles.json next to each model)

File loading comes from :mod:`bioscout.model.io`. Heavy deps (numpy, trimesh, scipy) are imported inside functions, so importing
this module is cheap.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Sequence

from .io import load_mesh, read_landmarks  # noqa: F401  (re-exported)

__all__ = [
    "load_mesh", "fit_sphere", "fit_head_sphere", "pelvic_frame",
    "fibonacci_directions", "covered_directions", "centre_edge_angle",
    "acetabular_coverage", "plot_hip_coverage", "plot_coverage_summary",
    "jcf_coverage", "plot_jcf_coverage", "hip_force_in_pelvis",
    "mri_to_pelvis_rotation",
    "find_hip_meshes", "Acetabular_Coverage",
    "neck_shaft_angle", "femoral_anteversion", "tibial_torsion",
    "neck_axis_from_mesh", "shaft_axis_from_mesh", "MEASURE_TIERS",
    "resolve_mesh_path", "body_mesh", "joint_table",
    "femoral_geometry", "tibial_geometry", "model_torsion",
    "read_slicer_markups", "markup_femoral_geometry", "MARKUP_LABELS",
    "joint_rotation_axis",
    "main",
]


# --------------------------------------------------------------------------- #
# basics  (loading lives in bioscout.model.io)
# --------------------------------------------------------------------------- #
def fit_sphere(points):
    """Algebraic least-squares sphere. Returns ``(centre, radius, rms)``."""
    import numpy as np
    p = np.asarray(points, float)
    A = np.c_[2 * p, np.ones(len(p))]
    sol, *_ = np.linalg.lstsq(A, (p ** 2).sum(1), rcond=None)
    c = sol[:3]
    r = float(np.sqrt(sol[3] + c @ c))
    rms = float(np.sqrt(np.mean((np.linalg.norm(p - c, axis=1) - r) ** 2)))
    return c, r, rms


def fit_head_sphere(vertices, seed_points=None, n_iter=5, keep_tol=0.08):
    """Femoral head sphere from a head mesh (or a whole femur + seed points).

    ``seed_points``: vertices known to lie on the head (e.g. the femur vertices
    nearest the acetabulum). Needed when ``vertices`` is a whole femur.
    Each iteration keeps vertices within ``keep_tol*r`` of the current sphere.
    """
    import numpy as np
    v = np.asarray(vertices, float)
    c, r, rms = fit_sphere(v if seed_points is None else seed_points)
    for _ in range(n_iter):
        d = np.abs(np.linalg.norm(v - c, axis=1) - r)
        sel = v[d < keep_tol * r]
        if len(sel) < 50:
            break
        c, r, rms = fit_sphere(sel)
    return c, r, rms


def pelvic_frame(asis_r, asis_l, pubic_symphysis):
    """Anterior pelvic plane. Returns ``(origin, R)``; rows of R are
    anterior (x), superior (y), right (z) in image coordinates."""
    import numpy as np
    ar, al, ps = (np.asarray(a, float) for a in (asis_r, asis_l, pubic_symphysis))
    origin = (ar + al) / 2
    z = (ar - al) / np.linalg.norm(ar - al)
    x = np.cross(z, ps - origin)
    x /= np.linalg.norm(x)
    return origin, np.vstack([x, np.cross(z, x), z])


def fibonacci_directions(n):
    """~Uniform unit vectors on the sphere."""
    import numpy as np
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.cos(phi), np.sin(th) * np.sin(phi)]


def covered_directions(mesh, centre, directions, radius, method="nearest",
                       threshold_mm=5.0, min_f=None, max_f=None):
    """Bool per direction: is the head sphere covered by ``mesh`` there?

    method="nearest" (default, fast): the point on the head sphere is within
        ``threshold_mm`` of the acetabulum surface.
    method="rays" (exact, slow without embree): a ray from ``centre`` hits the
        mesh between ``min_f*r`` and ``max_f*r`` -- by default the window
        implied by ``threshold_mm`` (``r ± threshold_mm``).
    """
    import numpy as np

    d = np.asarray(directions, float)
    c = np.asarray(centre, float)
    if method == "nearest":
        from scipy.spatial import cKDTree
        pts = c + d * radius
        dist, _ = cKDTree(mesh.vertices).query(pts, k=1)
        return dist <= threshold_mm
    if method != "rays":
        raise ValueError(f"unknown method: {method}")
    if min_f is None:
        min_f = max(0.0, 1 - threshold_mm / radius)
    if max_f is None:
        max_f = 1 + threshold_mm / radius
    origins = np.repeat(c[None], len(d), axis=0)
    locs, idx, _ = mesh.ray.intersects_location(origins, d, multiple_hits=True)
    hit = np.zeros(len(d), bool)
    if len(idx):
        dd = np.linalg.norm(locs - c, axis=1)
        ok = (dd > min_f * radius) & (dd < max_f * radius)
        hit[idx[ok]] = True
    return hit


def centre_edge_angle(mesh, centre, radius, R, toward, step=0.5, **kw):
    """Angle (deg) from superior toward local unit vector ``toward`` at which
    coverage ends. Negative if the superior direction is itself uncovered."""
    import numpy as np
    ang = np.arange(-60, 90 + step, step)
    rad = np.deg2rad(ang)
    local = np.outer(np.cos(rad), [0, 1, 0]) + np.outer(np.sin(rad), toward)
    hit = covered_directions(mesh, centre, local @ R, radius, **kw)
    j = int(np.searchsorted(ang, 0))
    if hit[j]:
        while j + 1 < len(ang) and hit[j + 1]:
            j += 1
        return float(ang[j])
    while j > 0 and not hit[j]:
        j -= 1
    return float(ang[j]) if hit[j] else float("nan")


def crop_near(mesh, centre, radius):
    """Faces of ``mesh`` whose centroid is within ``radius`` of ``centre``."""
    import numpy as np
    d = np.linalg.norm(mesh.triangles_center - centre, axis=1)
    return mesh.submesh([np.where(d < radius)[0]], append=True)


# --------------------------------------------------------------------------- #
# acetabular coverage
# --------------------------------------------------------------------------- #
def acetabular_coverage(acetabulum, femoral_head, *, side: str = "r",
                        landmarks: Optional[dict] = None, whole_femur: bool = False,
                        crop_factor: Optional[float] = None, n_dirs: int = 20000,
                        method: str = "nearest", threshold_mm: float = 5.0,
                        min_f: Optional[float] = None, max_f: Optional[float] = None,
                        return_details: bool = False) -> dict:
    """Coverage of the femoral head by the acetabulum.

    acetabulum, femoral_head: path or ``trimesh.Trimesh`` (same coordinates).
    whole_femur: femoral_head is a full femur -> head seeded from the vertices
        nearest the acetabulum.
    crop_factor: crop the acetabulum mesh to ``crop_factor*r`` around the head
        (use ~1.5 when passing a whole pelvis).
    landmarks: {"ASIS_R","ASIS_L","PUBIC_SYMPHYSIS"} -> adds frame-based metrics.
    method: "nearest" (fast, default) or "rays" (exact, slow).
    threshold_mm: how close the acetabulum must be to the head surface to count
        as covered (mm). The head-acetabulum gap (cartilage + segmentation) is
        typically 3.5-5 mm, so a threshold under ~4 mm finds nothing; the
        reported ``gap_min_mm`` says what it is for this hip.
    min_f, max_f: rays only -- give the hit window directly, as multiples of r,
        instead of deriving it from threshold_mm.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    t0 = time.time()
    acet = acetabulum if hasattr(acetabulum, "vertices") else load_mesh(acetabulum)
    fem = femoral_head if hasattr(femoral_head, "vertices") else load_mesh(femoral_head)

    seed = None
    if whole_femur:
        dist, _ = cKDTree(acet.vertices).query(fem.vertices, k=1)
        seed = fem.vertices[dist < np.percentile(dist, 2)]
    c, r, rms = fit_head_sphere(fem.vertices, seed_points=seed)
    if crop_factor:
        acet = crop_near(acet, c, crop_factor * r)
    if threshold_mm <= 0:
        raise ValueError(f"threshold_mm must be > 0, got {threshold_mm}")
    if (min_f is not None or max_f is not None) and method != "rays":
        raise ValueError("min_f/max_f apply to method='rays' only")
    if min_f is not None and max_f is not None and not 0 <= min_f < 1 < max_f:
        raise ValueError(f"need 0 <= min_f < 1 < max_f, got {min_f}, {max_f}")
    kw = dict(method=method, threshold_mm=threshold_mm, min_f=min_f, max_f=max_f)

    dirs = fibonacci_directions(n_dirs)
    hit = covered_directions(acet, c, dirs, r, **kw)

    # how far the acetabulum sits off the head surface: sets the useful
    # threshold range, and a large value means a bad fit or the wrong meshes
    gap, _ = cKDTree(np.asarray(acet.vertices)).query(c + dirs * r, k=1)
    gap_min, gap_p5 = (float(x) for x in np.percentile(gap, [0.5, 5]))
    out = {
        "side": side,
        "method": method,
        "head_centre_x": float(c[0]), "head_centre_y": float(c[1]),
        "head_centre_z": float(c[2]),
        "head_radius_mm": r, "sphere_rms_mm": rms,
        "gap_min_mm": round(gap_min, 2), "gap_p5_mm": round(gap_p5, 2),
        "covered_area_mm2": float(hit.mean() * 4 * math.pi * r ** 2),
        "coverage_sphere_pct": float(100 * hit.mean()),
        "threshold_mm": threshold_mm,
    }

    if landmarks:
        _, R = pelvic_frame(landmarks["ASIS_R"], landmarks["ASIS_L"],
                            landmarks["PUBIC_SYMPHYSIS"])
        local = dirs @ R.T                      # world -> pelvic frame
        sup = local[:, 1] > 0
        th = np.degrees(np.arctan2(local[:, 0], local[:, 1]))
        out["coverage_superior_hemisphere_pct"] = float(100 * hit[sup].mean())
        for name, m in (("anterior", th > 30), ("superior", abs(th) <= 30),
                        ("posterior", th < -30)):
            out[f"coverage_{name}_pct"] = float(100 * hit[sup & m].mean())
        lat = 1.0 if side.lower().startswith("r") else -1.0
        out["lcea_deg"] = centre_edge_angle(acet, c, r, R, np.array([0, 0, lat]), **kw)
        out["acea_deg"] = centre_edge_angle(acet, c, r, R, np.array([1.0, 0, 0]), **kw)

    out["time_s"] = round(time.time() - t0, 2)
    if return_details:
        out["_details"] = {"acetabulum": acet, "centre": c, "radius": r,
                           "directions": dirs, "covered": hit}
    return out




# --------------------------------------------------------------------------- #
# torsional geometry: neck-shaft angle, femoral anteversion, tibial torsion
# --------------------------------------------------------------------------- #
def _unit(v):
    import numpy as np
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n == 0:
        raise ValueError("zero-length vector")
    return v / n


def _perp(v, axis):
    """Component of ``v`` perpendicular to unit vector ``axis``."""
    import numpy as np
    v, a = np.asarray(v, float), _unit(axis)
    return v - (v @ a) * a


def _signed_angle(a, b, axis) -> float:
    """Signed angle (deg) from ``a`` to ``b`` about ``axis`` (right-hand rule).

    Both vectors are projected onto the plane perpendicular to ``axis`` first.
    """
    import numpy as np
    n = _unit(axis)
    x, y = _unit(_perp(a, n)), _unit(_perp(b, n))
    return float(np.degrees(np.arctan2(np.cross(x, y) @ n, x @ y)))


def neck_shaft_angle(head_centre, neck_centre, knee_centre, shaft_axis=None) -> float:
    """Femoral neck-shaft angle (deg): neck axis vs shaft axis.

    ``neck_centre`` is the centre of the narrowest neck cross-section, so the
    neck axis is ``neck_centre`` -> ``head_centre``. The shaft axis is
    ``shaft_axis`` when given (the anatomical axis of the diaphysis, from
    :func:`shaft_axis_from_mesh` -- it is oriented distally here), otherwise the
    line from the neck centre to ``knee_centre``. Prefer the fitted axis: the
    line through the neck centre swings by degrees with the few millimetres of
    uncertainty in where the isthmus sits.
    Typical adult value ~125 deg; < 120 is coxa vara, > 135 coxa valga. Points
    may be in any consistent frame.
    """
    import numpy as np
    head, neck_c = np.asarray(head_centre, float), np.asarray(neck_centre, float)
    knee = np.asarray(knee_centre, float)
    neck = _unit(head - neck_c)
    if shaft_axis is None:
        shaft = _unit(knee - neck_c)
    else:
        shaft = _unit(shaft_axis)
        if shaft @ (knee - neck_c) < 0:             # orient proximal -> distal
            shaft = -shaft
    return float(np.degrees(np.arccos(np.clip(neck @ shaft, -1, 1))))


def shaft_axis_from_mesh(mesh, proximal, distal, span=(0.3, 0.7)):
    """Anatomical shaft axis (unit, pointing distally) from the diaphysis.

    Takes the mesh vertices whose position along ``proximal`` -> ``distal``
    falls inside ``span`` (fractions of that length, the straight middle of the
    diaphysis: away from the trochanters and the condyles) and returns the first
    principal axis of that cloud.
    """
    import numpy as np
    p0, p1 = np.asarray(proximal, float), np.asarray(distal, float)
    d = _unit(p1 - p0)
    L = float(np.linalg.norm(p1 - p0))
    v = np.asarray(mesh.vertices, float)
    f = (v - p0) @ d / L
    sel = v[(f > span[0]) & (f < span[1])]
    if len(sel) < 20:
        raise ValueError("too few shaft vertices -- check the mesh and the span")
    sel = sel - sel.mean(0)
    ax = np.linalg.svd(sel, full_matrices=False)[2][0]
    return ax if ax @ d > 0 else -ax


def _lateral(axis, prox, side: str):
    """``axis`` projected perpendicular to ``prox`` and oriented laterally.

    Laterality follows the OpenSim body-frame convention (+z to the subject's
    right), so the sign of the axis given does not matter.
    """
    import numpy as np
    a = _unit(_perp(axis, prox))
    s = 1.0 if side.lower().startswith("r") else -1.0
    return a if s * a[2] >= 0 else -a


def femoral_anteversion(head_centre, neck_centre, knee_centre, condylar_axis,
                        side: str = "r") -> float:
    """Femoral anteversion / torsion (deg), positive = anteverted.

    Angle in the transverse plane (perpendicular to the shaft axis) between the
    neck axis (``neck_centre`` -> ``head_centre``) and the medial direction of
    the posterior condylar axis. ``condylar_axis``: the femoral medio-lateral
    axis at the knee -- its sign does not matter, it is oriented with
    :func:`_lateral`, which assumes an OpenSim-style frame (+z to the subject's
    right, +y proximal, +x anterior).
    Typical adult value ~10-20 deg; a negative value is retroversion.
    """
    import numpy as np
    head, neck_c = np.asarray(head_centre, float), np.asarray(neck_centre, float)
    knee = np.asarray(knee_centre, float)
    prox = _unit(neck_c - knee)                     # distal -> proximal
    lat = _lateral(condylar_axis, prox, side)
    med = -lat
    ant = np.cross(prox, lat) * (1.0 if side.lower().startswith("r") else -1.0)
    neck = _perp(head - neck_c, prox)
    return float(np.degrees(np.arctan2(neck @ ant, neck @ med)))


def tibial_torsion(knee_centre, ankle_centre, knee_axis, ankle_axis,
                   side: str = "r") -> float:
    """Tibial torsion (deg), positive = external (lateral malleolus posterior).

    Angle about the tibial long axis between the proximal medio-lateral axis
    (``knee_axis``, e.g. the tibial plateau / knee flexion axis) and the distal
    one (``ankle_axis``, e.g. the transmalleolar or talocrural axis). Axis signs
    do not matter -- both are oriented laterally with :func:`_lateral`, which
    assumes an OpenSim-style frame (+z to the subject's right).
    Typical adult value ~20-35 deg external.
    """
    import numpy as np
    prox = _unit(np.asarray(knee_centre, float) - np.asarray(ankle_centre, float))
    turn = _signed_angle(_lateral(knee_axis, prox, side),
                         _lateral(ankle_axis, prox, side), prox)
    # the same anatomical torsion turns the opposite way on the two sides
    return -turn if side.lower().startswith("r") else turn


# --------------------------------------------------------------------------- #
# femoral neck axis from a mesh
# --------------------------------------------------------------------------- #
def _section_area(mesh, origin, normal, min_area: float = 0.0,
                  max_dist: float = float("inf"),
                  max_radius: float = float("inf"),
                  min_aspect: float = 0.0):
    """Area and centroid of the cross-section loop nearest ``origin``.

    Returns ``(area, centroid)`` or ``(inf, None)`` when the plane misses the
    mesh. Several loops are common (neck + greater trochanter): the one whose
    centroid is closest to ``origin`` is the neck. ``min_area`` drops the
    slivers a plane grazing the head or the trochanter produces, ``max_dist``
    drops loops whose centre is too far off the axis to be the neck, and
    ``max_radius`` drops loops too wide to be one (the shaft, the trochanter),
    and ``min_aspect`` (shortest/longest radius from the loop centre) drops the
    lens-shaped loops a self-intersecting, not-quite-watertight mesh produces
    where two surfaces cross.
    """
    import numpy as np
    try:
        sec = mesh.section(plane_origin=np.asarray(origin, float),
                           plane_normal=np.asarray(normal, float))
    except Exception:
        sec = None
    if sec is None:
        return float("inf"), None
    best = (float("inf"), float("inf"), None)       # (distance, area, centroid)
    n = _unit(normal)
    for line in sec.discrete:
        p = np.asarray(line, float)
        if len(p) < 4:
            continue
        c = p[:-1].mean(0)
        area = float(abs(np.cross(p[:-1] - c, p[1:] - c).sum(0) @ n) / 2)
        d = float(np.linalg.norm(c - origin))
        if area < min_area or d > max_dist:
            continue
        rad = np.linalg.norm(p[:-1] - c, axis=1)
        if float(rad.max()) > max_radius or float(rad.min()) < min_aspect * float(rad.max()):
            continue
        if d < best[0]:
            best = (d, area, c)
    return best[1], best[2]


def neck_axis_from_mesh(mesh, head_centre, shaft_axis, head_radius, *,
                        n_dirs: int = 600, t_steps: int = 9,
                        t_range=(1.1, 2.6), refine: int = 2):
    """Femoral neck axis by the minimal cross-section (isthmus) of a femur mesh.

    Scans candidate axes through the head centre that make 15-85 deg with the
    proximal shaft direction, and along each one the planes between
    ``t_range`` x head radius from the centre; the plane with the smallest neck
    cross-section defines the axis and the neck centre. Planes are kept clear of
    the head itself (``t_range`` starts past the head surface), because a cap cut
    off the head is smaller than any neck section and would win every time.

    mesh: ``trimesh.Trimesh`` of the (proximal) femur, same units/frame as
        ``head_centre``; shaft_axis: proximal -> distal; head_radius: from
        :func:`fit_head_sphere`.
    Returns ``(neck_centre, neck_axis, area)`` -- ``neck_axis`` points from the
    neck towards the head, ``area`` is the isthmus area in the mesh's units^2.
    """
    import numpy as np

    head_centre = np.asarray(head_centre, float)
    up = -_unit(shaft_axis)                          # distal -> proximal
    cand = fibonacci_directions(int(n_dirs))
    ang = np.degrees(np.arccos(np.clip(cand @ up, -1, 1)))
    cand = cand[(ang > 15) & (ang < 85)]             # plausible neck directions
    if not len(cand):
        raise ValueError("no candidate neck directions")
    ts = np.linspace(t_range[0], t_range[1], int(t_steps))
    # a real neck section is a sizeable closed loop: this floor drops the
    # slivers a plane grazing the head or the greater trochanter cuts out
    min_area = 0.15 * math.pi * head_radius ** 2

    best = (float("inf"), None, None)                # (area, centre, axis)
    spread = None
    for it in range(int(refine) + 1):
        for d in cand:
            for t in ts:
                o = head_centre - d * (t * head_radius)
                a, c = _section_area(mesh, o, d, min_area=min_area,
                                     max_dist=0.35 * head_radius,
                                     max_radius=1.5 * head_radius,
                                     min_aspect=0.25)
                if c is not None and a < best[0]:
                    best = (a, c, d.copy())
        if best[1] is None:
            raise ValueError(
                "no neck cross-section found -- the mesh, the head centre or "
                "the units do not line up (a femur deformed without its mesh "
                "looks like this)")
        if it == int(refine):
            break
        # refine: tighter cone about the best axis, finer steps along it
        spread = (12.0 if spread is None else spread / 3)
        d0 = best[2]
        cand = fibonacci_directions(int(n_dirs))
        keep = np.degrees(np.arccos(np.clip(cand @ d0, -1, 1))) < spread
        cand = np.vstack([d0[None], cand[keep]])
        t0 = float(np.linalg.norm(best[1] - head_centre) / head_radius)
        ts = np.linspace(max(1.05, t0 - 0.3), t0 + 0.3, int(t_steps))
    area, centre, axis = best
    if centre is None:
        raise ValueError("no cross-section found -- check mesh, centre and units")
    return centre, _unit(axis), float(area)


# --------------------------------------------------------------------------- #
# the same measurements, from 3D Slicer markups (MRI landmarks)
# --------------------------------------------------------------------------- #
#: labels a femoral markup file is expected to carry (3D Slicer, LPS, mm)
MARKUP_LABELS = ("HJC", "GT", "PS", "LC", "MC", "DS")

#: LPS (Slicer) -> the femur-frame convention the angle functions assume
#: (x anterior, y superior, z to the subject's right). Rows map LPS x, y, z.
_LPS_TO_BODY = ((0.0, -1.0, 0.0),      # anterior  = -y (posterior) in LPS
                (0.0, 0.0, 1.0),       # superior  = +z in LPS
                (-1.0, 0.0, 0.0))      # right     = -x (left) in LPS


def read_slicer_markups(path) -> dict:
    """A ``.mrk.json`` fiducial list -> ``{label: xyz}`` (as stored, LPS mm).

    Every control point of every markup in the file is returned, so a file with
    the points split across lists still loads.
    """
    import numpy as np
    with open(path, encoding="utf-8-sig") as f:
        doc = json.load(f)
    out = {}
    for markup in doc.get("markups", ()):
        if markup.get("coordinateSystem", "LPS").upper() not in ("LPS", ""):
            raise ValueError(f"{path}: coordinate system "
                             f"{markup.get('coordinateSystem')} is not LPS")
        for cp in markup.get("controlPoints", ()):
            out[str(cp.get("label", "")).strip()] = np.asarray(cp["position"], float)
    return out


def markup_femoral_geometry(markups, side: str = "r") -> dict:
    """Neck-shaft angle and anteversion from MRI landmarks.

    markups: a ``.mrk.json`` path or a ``{label: xyz}`` dict, in Slicer's LPS
    millimetres, carrying :data:`MARKUP_LABELS`:

    ====  =========================================================
    HJC   femoral head centre (the hip joint centre)
    GT    greater trochanter -- the lateral end of the neck axis
    PS    proximal shaft point
    LC    lateral femoral condyle
    MC    medial femoral condyle
    DS    distal shaft point
    ====  =========================================================

    The neck axis is ``GT`` -> ``HJC``, the shaft axis ``PS`` -> ``DS`` and the
    condylar axis ``MC`` -> ``LC``; anteversion is measured in the plane
    perpendicular to the shaft, positive anterior. This reproduces the angles
    the Slicer measurement script writes for these files.
    """
    import numpy as np
    src = markups if isinstance(markups, dict) else read_slicer_markups(markups)
    missing = [k for k in MARKUP_LABELS if k not in src]
    if missing:
        raise KeyError(f"markups are missing {', '.join(missing)} "
                       f"(found {', '.join(sorted(src)) or 'nothing'})")
    R = np.asarray(_LPS_TO_BODY, float)
    p = {k: R @ np.asarray(src[k], float) for k in MARKUP_LABELS}

    shaft = p["DS"] - p["PS"]                      # proximal -> distal
    cond = p["LC"] - p["MC"]
    prox = _unit(-shaft)
    neck = _perp(p["HJC"] - p["GT"], prox)
    # The condylar line is oriented by the neck rather than by the side label:
    # the neck runs medially, so the end it points to is the medial one. That
    # keeps the angle right even when LC/MC or the file's side are swapped --
    # which happens, so it is reported as a warning instead of silently
    # changing the number.
    med = _unit(_perp(cond, prox))
    if neck @ med < 0:
        med = -med
    # the in-plane basis must be orthonormal, so the anterior axis is built
    # from the medial one (+x is anterior in this frame, which only fixes its
    # sign)
    ant = _unit(np.cross(prox, med))
    if ant[0] < 0:
        ant = -ant
    out = {
        "side": side.lower()[0],
        "neck_shaft_angle_deg": neck_shaft_angle(p["HJC"], p["GT"], p["DS"], shaft),
        "anteversion_deg": float(np.degrees(np.arctan2(neck @ ant, neck @ med))),
        "neck_length_mm": float(np.linalg.norm(p["HJC"] - p["GT"])),
        "shaft_length_mm": float(np.linalg.norm(shaft)),
        "condylar_width_mm": float(np.linalg.norm(cond)),
    }
    lat_by_side = _lateral(cond, prox, side)
    if lat_by_side @ (-med) < 0:
        out["warning"] = ("LC/MC point the other way than side "
                          f"'{out['side']}' implies -- check the labels or the "
                          "file's side; the angles were measured from the neck's "
                          "own medial direction")
    return out


# --------------------------------------------------------------------------- #
# the same measurements, from an .osim model
# --------------------------------------------------------------------------- #
def _model_state(model, state=None):
    """``(opensim.Model, State, Path|None)`` from a path or a live Model.

    Pass ``state`` back in to reuse a model that is already loaded and
    realised -- loading an ``.osim`` is by far the slowest step here, so every
    entry point threads the same model and state through.
    """
    import opensim  # noqa: F401
    if hasattr(model, "initSystem"):
        return model, (state if state is not None else model.initSystem()), None
    path = Path(model)
    from .io import load_model
    m = load_model(path)
    return m, m.initSystem(), path


def _point_in(state, frame, other, p=(0.0, 0.0, 0.0)):
    """Station ``p`` of ``frame`` expressed in ``other`` (model units, m)."""
    import numpy as np
    import opensim
    v = frame.findStationLocationInAnotherFrame(state, opensim.Vec3(*p), other)
    return np.array([v.get(0), v.get(1), v.get(2)])


def _axis_in(state, frame, other, axis: int = 2):
    """Unit basis vector ``axis`` (0=x, 1=y, 2=z) of ``frame``, in ``other``."""
    import numpy as np
    import opensim
    e = [0.0, 0.0, 0.0]
    e[axis] = 1.0
    v = frame.expressVectorInAnotherFrame(state, opensim.Vec3(*e), other)
    return _unit(np.array([v.get(0), v.get(1), v.get(2)]))


def _vec_in(state, frame, other, v):
    """Vector ``v`` of ``frame`` expressed in ``other`` (unit)."""
    import numpy as np
    import opensim
    w = frame.expressVectorInAnotherFrame(state, opensim.Vec3(*[float(x) for x in v]), other)
    return _unit(np.array([w.get(0), w.get(1), w.get(2)]))


def joint_rotation_axis(state, joint, other, pattern=("angle", "flex")):
    """The joint's main rotation axis, expressed in body ``other``.

    For a ``CustomJoint`` this is the rotation ``TransformAxis`` driven by a
    coordinate (preferring one named like a flexion angle) -- NOT the joint
    frame's z. The two differ: a gait2392-style knee rotates about the frame's
    z, while Rajagopal's ``walker_knee`` rotates about its x, so reading z as
    the medio-lateral axis silently turns anteversion into a number ~90 deg
    off. Falls back to the frame's z for joints with no spatial transform
    (a ``PinJoint``, where z IS the axis by definition).
    """
    import opensim
    cj = opensim.CustomJoint.safeDownCast(joint)
    if cj is not None:
        best = None
        for i in range(3):                      # 0-2 are the rotations
            ax = cj.getSpatialTransform().getTransformAxis(i)
            prop = ax.getCoordinateNames()          # PropertyStringList
            n_names = prop.size() if hasattr(prop, "size") else prop.getSize()
            names = [prop.getValue(k) for k in range(n_names)]
            if not names or ax.getFunction().getConcreteClassName() == "Constant":
                continue                        # not driven by a coordinate
            named = any(pat in n.lower() for n in names for pat in pattern)
            if best is None or (named and not best[0]):
                best = (named, ax)
        if best is not None:
            a = best[1].get_axis()
            return _vec_in(state, joint.getParentFrame(), other,
                           (a.get(0), a.get(1), a.get(2)))
    return _axis_in(state, joint.getParentFrame(), other, 2)


def joint_table(model) -> list:
    """``[{"joint", "parent", "child"}]`` -- joints with their two base bodies."""
    import opensim
    out = []
    for i in range(model.getJointSet().getSize()):
        j = model.getJointSet().get(i)
        try:
            out.append({"joint": j,
                        "name": j.getName(),
                        "parent": j.getParentFrame().findBaseFrame().getName(),
                        "child": j.getChildFrame().findBaseFrame().getName()})
        except Exception:
            continue
    return out


def _side_body(model, stem: str, side: str) -> str:
    """Body whose name looks like ``femur_r`` / ``tibia_l`` / ``r_femur`` ..."""
    s = side.lower()[0]
    names = [model.getBodySet().get(i).getName()
             for i in range(model.getBodySet().getSize())]
    lo = [n.lower() for n in names]
    for want in (f"{stem}_{s}", f"{s}_{stem}", f"{stem}{s}"):
        if want in lo:
            return names[lo.index(want)]
    cand = [n for n, l in zip(names, lo)
            if stem in l and (f"_{s}" in l or l.startswith(f"{s}_") or l.endswith(s))]
    if len(cand) == 1:
        return cand[0]
    raise LookupError(f"no unique {stem} body for side {s!r} in {names}")


def _joint_between(table, parent=None, child=None):
    for r in table:
        if (parent is None or r["parent"] == parent) and \
           (child is None or r["child"] == child):
            return r
    raise LookupError(f"no joint with parent={parent} child={child}")


def _body_path(table, start: str, end: str) -> list:
    """Joints along the kinematic chain from body ``start`` to body ``end``."""
    from collections import deque
    edges = {}
    for r in table:
        edges.setdefault(r["parent"], []).append((r["child"], r))
        edges.setdefault(r["child"], []).append((r["parent"], r))
    q, seen = deque([(start, [])]), {start}
    while q:
        b, path = q.popleft()
        if b == end:
            return path
        for nxt, r in edges.get(b, ()):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, path + [r]))
    raise LookupError(f"no kinematic path from {start} to {end}")


def _knee_joint(table, femur: str, tibia: str):
    """The knee joint between a femur and a tibia body.

    Knee models often insert extra bodies and welds between the two (a
    condylar body, an articulation frame, a tibial plateau), so the joint is
    found along the kinematic chain rather than by assuming femur -> tibia. The
    one carrying the knee's degrees of freedom wins; ``knee`` in the name breaks
    a tie.
    """
    path = _body_path(table, femur, tibia)
    named = [r for r in path if "knee" in r["name"].lower()]
    if named:
        return named[0]
    moving = [r for r in path if r["joint"].numCoordinates() > 0]
    if not moving:
        raise LookupError(f"only welds between {femur} and {tibia}")
    return max(moving, key=lambda r: r["joint"].numCoordinates())


def resolve_mesh_path(raw: str, model_path=None, search: Optional[Sequence] = None):
    """``(Path | None, tier)`` for one ``mesh_file`` value.

    A folder passed in ``search`` wins over every resolver tier: bioscout's
    resolver tries its own bundled Geometry first, so without this a model
    whose bones live elsewhere in the project silently resolves to the generic
    bone. Every caller that reads or rewrites a model's meshes goes through
    here, so measuring and deforming can never pick different files.
    """
    from .geometry import GeometryRef, resolve_ref

    q = Path(str(raw).replace("\\", "/"))
    for root in (search or ()):
        root = Path(root)
        for cand in ((root / q), (root / q.name),
                     *(sorted(root.rglob(q.name)) if root.is_dir() else ())):
            if cand.is_file():
                return cand, "search"
    if q.is_file():
        return q, "absolute"
    if model_path is None:
        return None, "missing"
    ref = resolve_ref(GeometryRef(raw=str(raw), tag="mesh_file"), model_path,
                      extra=search)
    return (ref.resolved if ref.resolved else None), ref.tier


#: geometry tiers a measurement may use. ``bundled`` (bioscout's own generic
#: Geometry folder) is excluded on purpose: silently measuring the generic bone
#: when a model's own mesh is missing returns the same numbers for every model
#: and looks like a working result.
MEASURE_TIERS = ("local", "parent", "search", "absolute")


def body_mesh(model, body_name: str, model_path=None, *, state=None,
              tiers: Sequence[str] = MEASURE_TIERS, info: Optional[dict] = None,
              search: Optional[Sequence] = None):
    """Every mesh attached to ``body_name``, merged, in that body's frame (m).

    Mesh files are located with :mod:`bioscout.model.geometry`'s resolver, then
    scaled by the model's ``scale_factors`` and moved by the attachment frame's
    offset, so the vertices line up with joint centres from the same model.
    Returns ``None`` when the body has no mesh from an accepted tier.

    tiers: which resolver tiers count as "this model's own geometry".
        The default leaves out ``bundled`` -- a mesh found only in bioscout's
        generic Geometry folder is not this model's bone, and measuring it
        quietly gives every model the same shape (see ``MEASURE_TIERS``).
    info: filled in with ``{"files": [...], "tiers": [...], "rejected": [...]}``
        so a caller can report which mesh the numbers came from.
    search: extra geometry folders to look in (the ``search`` tier), for models
        whose bones live somewhere else in the project.
    """
    import numpy as np
    import opensim
    import trimesh
    from .geometry import GeometryRef, resolve_ref

    state = state if state is not None else model.initSystem()
    body = model.getBodySet().get(body_name)

    # collect first: raising (or doing file IO) inside OpenSim's component
    # generator leaves it half-iterated and turns any error into a confusing
    # "generator ignored GeneratorExit"
    found = []
    for g in model.getComponentsList():
        mesh = opensim.Mesh.safeDownCast(g)
        if mesh is None:
            continue
        try:
            if mesh.getFrame().findBaseFrame().getName() != body_name:
                continue
        except Exception:
            continue
        found.append(mesh)

    seen = {"files": [], "tiers": [], "rejected": []}
    parts = []
    for mesh in found:
        frame = mesh.getFrame()
        raw = mesh.get_mesh_file()
        path, tier = resolve_mesh_path(raw, model_path, search)
        if not path or not Path(path).is_file():
            seen["rejected"].append(f"{raw} (not found)")
            continue
        if tier not in tiers:
            seen["rejected"].append(f"{raw} -> {path} ({tier})")
            continue
        seen["files"].append(str(path))
        seen["tiers"].append(tier)
        m = load_mesh(path)
        sf = mesh.get_scale_factors()
        v = np.asarray(m.vertices, float) * np.array([sf.get(0), sf.get(1), sf.get(2)])
        R = np.column_stack([_axis_in(state, frame, body, k) for k in range(3)])
        o = _point_in(state, frame, body)
        parts.append(trimesh.Trimesh(vertices=v @ R.T + o, faces=np.asarray(m.faces),
                                     process=False))
    if info is not None:
        info.update(seen)
    if not parts:
        return None
    return trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]


def femoral_geometry(model, side: str = "r", *, mesh=None, model_path=None,
                     landmarks: Optional[dict] = None, state=None,
                     tiers: Sequence[str] = MEASURE_TIERS,
                     search: Optional[Sequence] = None, **neck_kw) -> dict:
    """Neck-shaft angle and anteversion for one femur of an ``.osim`` model.

    The hip and knee joint centres come from the model's own joint frames
    (expressed in the femur body frame), the medio-lateral axis from the knee
    joint frame on the femur, and the neck axis from the femur mesh
    (:func:`neck_axis_from_mesh`) -- so the numbers describe the model that is
    actually simulated, scaling and personalisation included.

    model: path to an ``.osim`` or a live ``opensim.Model``.
    mesh: femur mesh to use instead of the model's own geometry (femur frame).
    landmarks: optional overrides in the femur frame (metres), any of
        ``HEAD_CENTRE``, ``NECK_CENTRE``, ``KNEE_CENTRE``, ``CONDYLE_MED``,
        ``CONDYLE_LAT`` (the two condyles replace the knee-frame axis).
    Extra kwargs go to :func:`neck_axis_from_mesh`.
    """
    import numpy as np

    m, state, path = _model_state(model, state)
    model_path = model_path or path
    lm = {k: np.asarray(v, float) for k, v in (landmarks or {}).items()}
    shaft_ax = None                                  # set when a mesh is used
    femur = _side_body(m, "femur", side)
    tibia = _side_body(m, "tibia", side)
    table = joint_table(m)
    body = m.getBodySet().get(femur)

    hip = _joint_between(table, child=femur)["joint"]
    knee = _knee_joint(table, femur, tibia)["joint"]
    head_c = lm.get("HEAD_CENTRE", _point_in(state, hip.getChildFrame(), body))
    knee_c = lm.get("KNEE_CENTRE", _point_in(state, knee.getParentFrame(), body))
    if "CONDYLE_MED" in lm and "CONDYLE_LAT" in lm:
        cond = lm["CONDYLE_LAT"] - lm["CONDYLE_MED"]
    else:
        cond = joint_rotation_axis(state, knee, body)   # the knee flexion axis

    out = {"model": Path(model_path).stem if model_path else m.getName(),
           "side": side.lower()[0], "femur_body": femur,
           "hip_centre_mm": [float(x) * 1000 for x in head_c],
           "knee_centre_mm": [float(x) * 1000 for x in knee_c],
           "femur_length_mm": float(np.linalg.norm(knee_c - head_c) * 1000)}

    neck_c = lm.get("NECK_CENTRE")
    if neck_c is None:
        info = {}
        if mesh is None:
            mesh = body_mesh(m, femur, model_path, state=state, tiers=tiers,
                             info=info, search=search)
        if mesh is None:
            why = "; ".join(info.get("rejected", ())) or "no mesh attached to the body"
            out["error"] = (f"no usable femur mesh for {femur} ({why}). The neck "
                            f"axis needs this model's own bone: put its Geometry "
                            f"next to the model, pass mesh=... / --mesh, or give "
                            f"landmarks={{'NECK_CENTRE': ...}}. Measuring the "
                            f"bundled generic femur instead would give every "
                            f"model the same angles.")
            return out
        if info.get("files"):
            out["femur_mesh_file"] = info["files"][0] if len(info["files"]) == 1 \
                else info["files"]
            out["femur_mesh_tier"] = info["tiers"][0]
            if info["tiers"][0] != "local":
                out["warning"] = (f"the femur mesh was found via the "
                                  f"'{info['tiers'][0]}' tier, not next to the model")
        head_pts = np.asarray(mesh.vertices, float)
        d = np.linalg.norm(head_pts - head_c, axis=1)
        seed = head_pts[d < np.percentile(d, 3)]
        c_fit, r, rms = fit_head_sphere(head_pts, seed_points=seed)
        if np.linalg.norm(c_fit - head_c) > 0.5 * r:
            out["warning"] = ("the fitted head centre is far from the hip joint "
                              "centre -- check the mesh and the model's frames")
        neck_c, neck_axis, area = neck_axis_from_mesh(mesh, c_fit, knee_c - c_fit,
                                                      r, **neck_kw)
        head_c = c_fit
        out.update({"head_radius_mm": float(r * 1000),
                    "head_sphere_rms_mm": float(rms * 1000),
                    "neck_min_area_mm2": float(area * 1e6)})
        try:
            shaft_ax = shaft_axis_from_mesh(mesh, head_c, knee_c)
        except Exception:
            shaft_ax = None                          # fall back to the joint line
    neck_c = np.asarray(neck_c, float)

    out.update({
        "neck_centre_mm": [float(x) * 1000 for x in neck_c],
        "neck_length_mm": float(np.linalg.norm(head_c - neck_c) * 1000),
        "neck_shaft_angle_deg": neck_shaft_angle(head_c, neck_c, knee_c, shaft_ax),
        "anteversion_deg": femoral_anteversion(head_c, neck_c, knee_c, cond, side),
    })
    return out


def tibial_geometry(model, side: str = "r", *, landmarks: Optional[dict] = None,
                    model_path=None, state=None) -> dict:
    """Tibial torsion for one leg of an ``.osim`` model.

    Proximal axis: the knee joint frame on the tibia; distal axis: the ankle
    joint frame on the tibia (the talocrural axis, the model's stand-in for the
    transmalleolar axis). Both expressed in the tibia body frame.

    landmarks: optional overrides in the tibia frame (metres):
        ``KNEE_CENTRE``, ``ANKLE_CENTRE``, ``MALLEOLUS_MED``, ``MALLEOLUS_LAT``
        (the two malleoli replace the ankle-frame axis), ``PLATEAU_MED``,
        ``PLATEAU_LAT`` (replace the knee-frame axis).
    """
    import numpy as np

    m, state, path = _model_state(model, state)
    model_path = model_path or path
    lm = {k: np.asarray(v, float) for k, v in (landmarks or {}).items()}
    femur = _side_body(m, "femur", side)
    tibia = _side_body(m, "tibia", side)
    table = joint_table(m)
    body = m.getBodySet().get(tibia)

    knee = _knee_joint(table, femur, tibia)["joint"]
    ankle = _joint_between(table, parent=tibia)["joint"]
    knee_c = lm.get("KNEE_CENTRE", _point_in(state, knee.getChildFrame(), body))
    ankle_c = lm.get("ANKLE_CENTRE", _point_in(state, ankle.getParentFrame(), body))
    knee_ax = (lm["PLATEAU_LAT"] - lm["PLATEAU_MED"]) if "PLATEAU_LAT" in lm and \
        "PLATEAU_MED" in lm else joint_rotation_axis(state, knee, body)
    ankle_ax = (lm["MALLEOLUS_LAT"] - lm["MALLEOLUS_MED"]) if "MALLEOLUS_LAT" in lm \
        and "MALLEOLUS_MED" in lm else joint_rotation_axis(state, ankle, body)

    return {"model": Path(model_path).stem if model_path else m.getName(),
            "side": side.lower()[0], "tibia_body": tibia,
            "ankle_joint": ankle.getName(),
            "tibia_length_mm": float(np.linalg.norm(knee_c - ankle_c) * 1000),
            "tibial_torsion_deg": tibial_torsion(knee_c, ankle_c, knee_ax, ankle_ax, side)}


def model_torsion(model, side: str = "r", *, mesh=None, landmarks: Optional[dict] = None,
                  model_path=None, state=None, tiers: Sequence[str] = MEASURE_TIERS,
                  search: Optional[Sequence] = None, **neck_kw) -> dict:
    """Neck-shaft angle, anteversion and tibial torsion for one leg.

    ``landmarks`` is passed to both halves; keys that do not apply are ignored.
    Returns one flat dict (an ``error``/``warning`` key is set rather than
    raised when only one half fails).

    The model is loaded once here and the same model and state go to both
    halves. Pass the ``opensim.Model`` itself (plus ``model_path`` for the mesh
    lookup, and ``state``) to measure both sides off a single load.
    """
    t0 = time.time()
    m, state, path = _model_state(model, state)
    model_path = model_path or path
    out = {}
    for fn in (femoral_geometry, tibial_geometry):
        kw = dict(landmarks=landmarks, model_path=model_path, state=state)
        if fn is femoral_geometry:
            kw.update(mesh=mesh, tiers=tiers, search=search, **neck_kw)
        try:
            out.update(fn(m, side, **kw))
        except Exception as e:
            out.setdefault("error", "")
            out["error"] = (out["error"] + "; " if out["error"] else "") + _err(e)
    out.setdefault("model", Path(model_path).stem if model_path else m.getName())
    out["time_s"] = round(time.time() - t0, 2)
    return out


# --------------------------------------------------------------------------- #
# plots  (matplotlib, imported lazily; files only — never plt.show())
# --------------------------------------------------------------------------- #
#: categorical slots 1-2 (validated palette) + neutral for "not covered"
_C_COVERED, _C_SECOND, _C_NEUTRAL, _C_BONE = "#2a78d6", "#eb6834", "#c3c2b7", "#6f6e69"


def plot_hip_coverage(res: dict, path, title: str = "") -> Path:
    """Two 3D views of one hip: acetabulum + head sphere coloured by coverage.

    ``res`` must come from ``acetabular_coverage(..., return_details=True)``.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    d = res["_details"]
    c, r = d["centre"], d["radius"]
    pts = c + d["directions"] * r
    hit = d["covered"]
    av = d["acetabulum"].vertices
    if len(av) > 6000:
        av = av[np.random.default_rng(0).choice(len(av), 6000, replace=False)]
    step = max(1, len(pts) // 4000)
    pts, hit = pts[::step], hit[::step]

    fig = plt.figure(figsize=(10, 5), dpi=150)
    for k, (elev, azim, name) in enumerate(((10, -60, "view 1"), (70, -90, "view 2"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        ax.scatter(*av.T, s=0.4, c=_C_BONE, alpha=0.15, linewidths=0, label="acetabulum")
        ax.scatter(*pts[~hit].T, s=3, c=_C_NEUTRAL, linewidths=0, label="head – not covered")
        ax.scatter(*pts[hit].T, s=3, c=_C_COVERED, linewidths=0, label="head – covered")
        lim = 1.8 * r
        for set_lim, ci in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), c):
            set_lim(ci - lim, ci + lim)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlabel("x (mm)", fontsize=7); ax.set_ylabel("y (mm)", fontsize=7)
        ax.set_zlabel("z (mm)", fontsize=7); ax.tick_params(labelsize=6)
        ax.set_title(name, fontsize=9, color="#555")
        if k == 0:
            ax.legend(loc="upper left", fontsize=7, markerscale=4, frameon=False)
    fig.suptitle(f"{title}  coverage {res['coverage_sphere_pct']:.1f}%  ·  "
                 f"area {res['covered_area_mm2']:.0f} mm²  ·  r {r:.1f} mm  ·  "
                 f"fit RMS {res['sphere_rms_mm']:.2f} mm", fontsize=10)
    fig.tight_layout()
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path); plt.close(fig)
    return path


def plot_coverage_summary(rows, path) -> Optional[Path]:
    """Dot plot: coverage % per subject, right vs left."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ok = [r for r in rows if not r.get("error")]
    if not ok:
        return None
    subjects = list(dict.fromkeys(r["subject"] for r in ok))
    y = {s: i for i, s in enumerate(subjects)}
    fig, ax = plt.subplots(figsize=(6, 0.45 * len(subjects) + 1.5), dpi=150)
    for side, colour, marker, dy in (("r", _C_COVERED, "o", -0.12), ("l", _C_SECOND, "s", 0.12)):
        sel = [r for r in ok if r["side"] == side]
        ax.scatter([r["coverage_sphere_pct"] for r in sel], [y[r["subject"]] + dy for r in sel],
                   s=40, c=colour, marker=marker, edgecolors="white", linewidths=1,
                   label="right" if side == "r" else "left", zorder=3)
    ax.set_yticks(range(len(subjects)), subjects)
    ax.set_ylim(len(subjects) - 0.5, -0.5)
    xs = [r["coverage_sphere_pct"] for r in ok]
    pad = max(2.0, 0.1 * (max(xs) - min(xs)))
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    m = ok[0].get("method", "nearest")
    thr = ok[0].get("threshold_mm")
    ax.set_xlabel("head sphere covered by acetabulum (%)"
                  + (f"   [{m}, {thr} mm]" if thr else f"   [{m}]"))
    ax.grid(axis="x", color="#e5e5e0", linewidth=0.8, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1), ncol=2,
              fontsize=8, handletextpad=0.3)
    ax.set_title("Acetabular coverage", loc="left", fontsize=11)
    fig.tight_layout()
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path); plt.close(fig)
    return path



# --------------------------------------------------------------------------- #
# JCF coverage: where the hip contact force actually passes through the head
# --------------------------------------------------------------------------- #
def mri_to_pelvis_rotation(landmarks) -> "object":
    """Rotation from MRI/scanner coordinates to the model's PELVIS frame.

    OpenSim pelvis frames (Rajagopal, GPK, Catelli) use the ISB convention:
    x anterior, y superior, z right — which is exactly the anterior pelvic
    plane frame :func:`pelvic_frame` builds from ASIS_R, ASIS_L and
    PUBIC_SYMPHYSIS picked on the MRI. So the landmarks ARE the registration:
    no ICP, and no need to read the model's geometry (whose ``.vtp`` files are
    often compressed, and whose pelvis mesh may be far too coarse to register
    against anyway).

    Returns R with rows [anterior, superior, right] in MRI coordinates, so
    ``R @ v_mri`` is in the pelvis frame and ``R.T @ v_pelvis`` back in MRI.
    """
    if isinstance(landmarks, (str, Path)):
        landmarks = read_landmarks(landmarks)
    missing = [k for k in ("ASIS_R", "ASIS_L", "PUBIC_SYMPHYSIS") if k not in landmarks]
    if missing:
        raise ValueError("landmarks missing: " + ", ".join(missing))
    _, R = pelvic_frame(landmarks["ASIS_R"], landmarks["ASIS_L"],
                        landmarks["PUBIC_SYMPHYSIS"])
    return R


def hip_force_in_pelvis(osim, jra, ik, joint=None, side="r", geometry=None):
    """Hip contact force ON the acetabulum IN the pelvis frame.

    Returns ``(F (3, N), joint_name)`` in newtons, reusing the conversion in
    :mod:`bioscout.plot.jcf_direction` (Newton's third law + the hip joint's
    own rotation), so this matches the ``bioscout plot jcf`` figures.
    """
    import numpy as np
    from bioscout.plot.jcf_direction import (OsimModel, force_triplets,
                                             hip_to_pelvis, read_sto)

    names, data = read_sto(jra)
    trips = force_triplets(names)
    if joint is None:
        cands = [j for j in trips if "hip" in j and j.endswith("_" + side.lower()[0])]
        if not cands:
            cands = [j for j in trips if "hip" in j]
        if not cands:
            raise ValueError(f"no hip *_on_*_in_*_f{{x,y,z}} columns in {jra}")
        joint = cands[0]
    _, _, idx = trips[joint]
    F = data[:, idx].T                                   # (3, N), on femur
    ik_names, ik_data = read_sto(ik)
    with open(ik) as fh:
        degrees = "indegrees=yes" in fh.read(2000).replace(" ", "").lower()
    Fp = hip_to_pelvis(OsimModel(osim, geometry), joint, F, ik_names, ik_data, degrees)
    if Fp is None:
        raise ValueError(f"{joint}: no IK columns for its coordinates in {ik}")
    return Fp, joint


def jcf_coverage(acetabulum, femoral_head, osim, jra, ik, *, side="r",
                 geometry=None, bodyweight=None, threshold_mm=5.0,
                 method="nearest", n_dirs=20000, spread_deg=20.0,
                 landmarks=None, rotation=None, frames=None) -> dict:
    """Peak contact force per region of the femoral head, over a task.

    Geometry from the MRI meshes, load from an OpenSim JointReaction run:
    each time frame's force direction (pelvis frame) is mapped onto the head
    sphere and every surface direction within ``spread_deg/2`` of it takes that
    frame's magnitude. The map is therefore the PEAK force that passed through
    each region during the task (N, or body weights with ``bodyweight``).

    Adds the load-side metrics coverage alone cannot give:
    Alignment: MRI meshes are put into the pelvis frame from the pelvic
    landmarks (see :func:`mri_to_pelvis_rotation`); pass ``rotation`` to supply
    one, or neither when the model is MRI-personalised in the same frame.

      peak_force_covered      was the peak load on covered acetabulum?
      load_bearing_coverage_pct   % of frames whose force points at covered surface
      rim_margin_deg_min      smallest angle from the load direction to the
                              nearest UNCOVERED direction (small = edge loading)
      rim_margin_deg_at_peak  the same at the instant of peak force
    """
    import numpy as np

    lm = read_landmarks(landmarks) if isinstance(landmarks, (str, Path)) else landmarks
    base = acetabular_coverage(acetabulum, femoral_head, side=side,
                               threshold_mm=threshold_mm, method=method,
                               n_dirs=n_dirs, landmarks=lm, return_details=True)
    det = base["_details"]
    acet, c, r = det["acetabulum"], det["centre"], det["radius"]
    dirs, hit = det["directions"], det["covered"]

    if rotation is not None:
        Rm = np.asarray(rotation, float)
        how = "given"
    elif lm:
        Rm = mri_to_pelvis_rotation(lm)
        how = "landmarks (anterior pelvic plane)"
    else:
        Rm = np.eye(3)
        how = "none (meshes assumed already in the pelvis frame)"

    F, joint = hip_force_in_pelvis(osim, jra, ik, side=side, geometry=geometry)
    if frames:                          # (start, stop) frame window
        F = F[:, frames[0]:frames[1]]
    mag = np.linalg.norm(F, axis=0)
    ok = mag > 1e-6
    u_pelvis = F[:, ok] / mag[ok]
    mag = mag[ok]
    unit, scale = ("BW", float(bodyweight)) if bodyweight else ("N", 1.0)
    mag_plot = mag / scale

    # load directions back into the MRI frame the meshes live in
    u = Rm.T @ u_pelvis                                  # (3, T)
    cos_lim = math.cos(math.radians(spread_deg / 2))

    # peak force per surface direction, in chunks (dirs x frames can be large)
    peak = np.zeros(len(dirs))
    for i in range(0, u.shape[1], 200):
        blk = u[:, i:i + 200]
        cos = dirs @ blk                                 # (n_dirs, blk)
        m = cos >= cos_lim
        if m.any():
            peak = np.maximum(peak, (m * mag_plot[i:i + 200]).max(axis=1))

    # is the load pointing at covered surface? and how close to the rim?
    nearest = np.argmax(dirs @ u, axis=0)                # closest sampled dir
    on_covered = hit[nearest]
    unc = dirs[~hit]
    if len(unc):
        rim = np.degrees(np.arccos(np.clip((u.T @ unc.T).max(axis=1), -1, 1)))
    else:
        rim = np.full(u.shape[1], np.nan)
    i_peak = int(np.argmax(mag_plot))

    out = {k: v for k, v in base.items() if k != "_details"}
    out.update({
        "joint": joint, "force_unit": unit,
        "n_frames": int(u.shape[1]),
        "alignment": how,
        "peak_force": round(float(mag_plot[i_peak]), 3),
        "peak_force_covered": bool(on_covered[i_peak]),
        "mean_force": round(float(mag_plot.mean()), 3),
        "load_bearing_coverage_pct": round(100 * float(on_covered.mean()), 1),
        "rim_margin_deg_min": round(float(np.nanmin(rim)), 1),
        "rim_margin_deg_at_peak": round(float(rim[i_peak]), 1),
        "rim_margin_deg_mean": round(float(np.nanmean(rim)), 1),
        "peak_load_map_max": round(float(peak.max()), 3),
        "spread_deg": spread_deg,
    })
    out["_details"] = {**det, "peak_map": peak, "load_dirs": u,
                       "load_mag": mag_plot, "i_peak": i_peak, "unit": unit}
    return out


def plot_jcf_coverage(res: dict, path, title: str = "") -> Path:
    """Head sphere heat-mapped by peak contact force, with the covered rim."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    d = res["_details"]
    c, r = d["centre"], d["radius"]
    peak, dirs, hit = d["peak_map"], d["directions"], d["covered"]
    pts = c + dirs * r
    step = max(1, len(pts) // 6000)
    pts_s, peak_s, hit_s = pts[::step], peak[::step], hit[::step]
    av = d["acetabulum"].vertices
    if len(av) > 5000:
        av = av[np.random.default_rng(0).choice(len(av), 5000, replace=False)]
    track = c + d["load_dirs"].T * r * 1.02
    unit = d["unit"]

    fig = plt.figure(figsize=(11, 5), dpi=150)
    sc = None
    for k, (elev, azim, name) in enumerate(((10, -60, "view 1"), (70, -90, "view 2"))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        ax.scatter(*av.T, s=0.4, c=_C_BONE, alpha=0.12, linewidths=0, label="acetabulum")
        vmax = max(float(peak.max()), 1e-9)
        cold = peak_s <= 0.02 * vmax
        ax.scatter(*pts_s[cold].T, s=1.2, c=_C_NEUTRAL, linewidths=0, alpha=0.2,
                   label="head – unloaded")
        edge = pts_s[hit_s & cold]
        if len(edge):
            ax.scatter(*edge.T, s=1.2, c="#1baf7a", linewidths=0, alpha=0.25,
                       label="covered, unloaded")
        # loaded region last and larger, so the heat map is never buried
        sc = ax.scatter(*pts_s[~cold].T, s=14, c=peak_s[~cold], cmap="Blues",
                        vmin=0.02 * vmax, vmax=vmax, linewidths=0, depthshade=False,
                        label="head – peak force")
        ax.plot(*track.T, color=_C_SECOND, lw=1.2, alpha=0.9, label="load direction")
        lim = 1.8 * r
        for set_lim, ci in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), c):
            set_lim(ci - lim, ci + lim)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim)
        ax.set_xlabel("x (mm)", fontsize=7); ax.set_ylabel("y (mm)", fontsize=7)
        ax.set_zlabel("z (mm)", fontsize=7); ax.tick_params(labelsize=6)
        ax.set_title(name, fontsize=9, color="#555")
        if k == 0:
            ax.legend(loc="upper left", fontsize=7, markerscale=3, frameon=False)
    cb = fig.colorbar(sc, ax=fig.axes, shrink=0.65, pad=0.02)
    cb.set_label(f"peak contact force ({unit})", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.suptitle(f"{title}  peak {res['peak_force']} {unit}  ·  "
                 f"load on covered surface {res['load_bearing_coverage_pct']}% of frames  ·  "
                 f"rim margin at peak {res['rim_margin_deg_at_peak']}°  ·  "
                 + f"aligned by {res['alignment']}", fontsize=9)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def find_hip_meshes(folder, side: str) -> dict:
    """Locate acetabulum / femoral head meshes for one side in a Meshlab folder.

    Preference: cropped ``acetabulum_{s}.stl`` + ``femoral_head_{s}.stl``;
    fallback: ``Segmentation*_{s}_pelvis|acetabulum.stl`` +
    ``Segmentation*_{s}_femur.stl`` (whole bones, cropped/seeded automatically).
    """
    folder = Path(folder)
    s = side.lower()[0]
    files = {p.name.lower(): p for p in folder.glob("*.stl")}

    def first(*patterns):
        for pat in patterns:
            for name, p in sorted(files.items()):
                if Path(name).match(pat) and "cartilage" not in name:
                    return p
        return None

    acet = first(f"acetabulum_{s}.stl")
    acet_whole = acet is None
    if acet is None:
        acet = first(f"segmentation*_{s}_acetabulum.stl", f"segmentation*_{s}_pelvis.stl")
    head = first(f"femoral_head_{s}.stl")
    fem_whole = head is None
    if head is None:
        head = first(f"segmentation*_{s}_femur.stl")
    return {"acetabulum": acet, "femoral_head": head,
            "acetabulum_whole": acet_whole, "femur_whole": fem_whole}


def Acetabular_Coverage(stl_acetabulum, stl_femoral_head, **kw):
    """Backwards-compatible wrapper: returns % coverage of the head sphere."""
    try:
        return acetabular_coverage(stl_acetabulum, stl_femoral_head, **kw)["coverage_sphere_pct"]
    except Exception as e:  # keep the old "None on failure" contract
        print(f"acetabular coverage failed: {e}", file=sys.stderr)
        return None


# --------------------------------------------------------------------------- #
# CLI:  bioscout model measure coverage ...
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bioscout model measure",
                                description="measurements from bone meshes")
    sub = p.add_subparsers(dest="what", metavar="WHAT")
    c = sub.add_parser("coverage", help="acetabular coverage of the femoral head")
    c.add_argument("folders", nargs="*", metavar="FOLDER",
                   help="Meshlab folder(s) with acetabulum_/femoral_head_ or Segmentation_ STLs")
    c.add_argument("--acetabulum", metavar="STL")
    c.add_argument("--femoral-head", metavar="STL",
                   help="head mesh (or whole femur with --whole-femur)")
    c.add_argument("--whole-femur", action="store_true")
    c.add_argument("--side", nargs="+", default=["r", "l"], choices=["r", "l"])
    c.add_argument("--subject", help="label for the output row (default: folder name)")
    c.add_argument("--landmarks", metavar="CSV", help="name,x,y,z with ASIS_R, ASIS_L, PUBIC_SYMPHYSIS")
    c.add_argument("--crop-factor", type=float, default=None,
                   help="crop acetabulum to this × head radius (auto 1.5 for whole pelvis)")
    c.add_argument("--n-dirs", type=int, default=20000)
    c.add_argument("--method", default="nearest", choices=["nearest", "rays"],
                   help="nearest = distance to the acetabulum surface (fast, default); "
                        "rays = ray casting (exact, much slower)")
    c.add_argument("--threshold", type=float, default=5.0, metavar="MM",
                   help="covered if the acetabulum is within MM of the head "
                        "surface (default 5; the real cartilage gap is ~4 mm, "
                        "see gap_min_mm in the output)")
    c.add_argument("--min-f", type=float, default=0.5,
                   help="nearest valid hit, × head radius (default 0.5)")
    c.add_argument("--max-f", type=float, default=1.5,
                   help="farthest valid hit, × head radius (default 1.5)")
    c.add_argument("-o", "--out", metavar="CSV", help="append results to this CSV")
    c.add_argument("--json", action="store_true", help="print results as JSON")
    c.add_argument("--plots", metavar="DIR",
                   help="where to save figures (default: figures/ next to -o, "
                        "else ./coverage_figures)")
    c.add_argument("--no-plots", action="store_true", help="skip the figures")

    t = sub.add_parser("torsion", help="neck-shaft angle, anteversion, tibial torsion "
                                       "from an .osim model")
    t.add_argument("models", nargs="+", metavar="OSIM", help=".osim model file(s)")
    t.add_argument("--side", nargs="+", default=["r", "l"], choices=["r", "l"])
    t.add_argument("--landmarks", metavar="CSV",
                   help="name,x,y,z overrides in the femur/tibia frame (metres): "
                        "HEAD_CENTRE, NECK_CENTRE, KNEE_CENTRE, CONDYLE_MED/LAT, "
                        "ANKLE_CENTRE, MALLEOLUS_MED/LAT, PLATEAU_MED/LAT")
    t.add_argument("--mesh", metavar="STL",
                   help="femur mesh to use instead of the model's own geometry "
                        "(one side only)")
    t.add_argument("--n-dirs", type=int, default=600,
                   help="candidate neck axes in the isthmus search (default 600)")
    t.add_argument("-o", "--out", metavar="CSV", help="append results to this CSV")
    t.add_argument("--json", action="store_true", help="print results as JSON")
    t.add_argument("--json-out", metavar="FILE",
                   help="where to write the per-model JSON (default: "
                        "<model>_torsion_angles.json next to the model)")
    t.add_argument("--no-json-file", action="store_true",
                   help="do not write <model>_torsion_angles.json")
    t.add_argument("--search", action="append", metavar="DIR",
                   help="extra folder to look for the model's bone meshes in; "
                        "repeatable (for models whose Geometry lives elsewhere)")
    t.add_argument("--allow-bundled-geometry", action="store_true",
                   help="also measure a femur mesh that only resolves through "
                        "bioscout's bundled Geometry folder. Off by default: "
                        "that is the generic bone, so every model would report "
                        "the same neck-shaft angle and anteversion")
    mk = sub.add_parser("markups", help="neck-shaft angle and anteversion from "
                                       "3D Slicer MRI markups (.mrk.json)")
    mk.add_argument("paths", nargs="+", metavar="FILE_OR_DIR",
                    help="markup files, or folders of <id>_<side>.mrk.json")
    mk.add_argument("-o", "--out", metavar="CSV", help="write results to this CSV")
    mk.add_argument("--json", action="store_true", help="print results as JSON")

    j = sub.add_parser("jcf-coverage",
                       help="peak hip contact force per region of the femoral head")
    j.add_argument("folder", nargs="?", metavar="FOLDER",
                   help="Meshlab folder with the acetabulum/femoral-head STLs")
    j.add_argument("--acetabulum", metavar="STL")
    j.add_argument("--femoral-head", metavar="STL")
    j.add_argument("--model", required=True, metavar="OSIM")
    j.add_argument("--jra", required=True, metavar="STO",
                   help="JointReaction output (reaction on the child, child frame)")
    j.add_argument("--ik", required=True, metavar="MOT",
                   help="IK angles of the same trial (needed for the pelvis frame)")
    j.add_argument("--side", default="r", choices=["r", "l"])
    j.add_argument("--subject")
    j.add_argument("--geometry", nargs="*", metavar="DIR",
                   help="extra folder(s) holding the model's .vtp meshes")
    j.add_argument("--mass", type=float, metavar="KG", help="report force in body weights")
    j.add_argument("--bw", type=float, metavar="N", help="body weight in newtons")
    j.add_argument("--threshold", type=float, default=5.0, metavar="MM")
    j.add_argument("--spread", type=float, default=20.0, metavar="DEG",
                   help="angular width of the contact patch per frame (default 20)")
    j.add_argument("--n-dirs", type=int, default=20000)
    j.add_argument("--landmarks", metavar="CSV",
                   help="name,x,y,z with ASIS_R, ASIS_L, PUBIC_SYMPHYSIS picked on "
                        "the MRI — this is what puts the meshes in the model's "
                        "pelvis frame (omit only for MRI-personalised models "
                        "already in that frame)")
    j.add_argument("--plots", metavar="DIR")
    j.add_argument("--no-plots", action="store_true")
    j.add_argument("-o", "--out", metavar="CSV")
    j.add_argument("--json", action="store_true")

    return p


def _subject_label(folder: Path) -> str:
    # .../022/Meshlab_BG -> 022  (the participant ID, as in project.yaml)
    return folder.parent.name if folder.name.lower().startswith("meshlab") else folder.name


def _write_rows(rows, out_path) -> Path:
    """Append result dicts to a CSV, keeping an existing header."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    new = not out.exists()
    old = keys
    if not new:
        with open(out, newline="") as f:
            old = next(csv.reader(f), [])
        keys = list(dict.fromkeys(old + keys))
    with open(out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys if new else old, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)
    return out


def _err(e: Exception) -> str:
    """Readable one-liner for an exception.

    ``repr`` of a ``FileNotFoundError`` is just the path, which reads as if the
    file were the problem rather than the fact that it is missing.
    """
    text = str(e) or repr(e)
    if isinstance(e, FileNotFoundError):
        return f"no such file: {text}"
    return f"{type(e).__name__}: {text}"


def _torsion_summary(model_path, rows) -> dict:
    """The short form written next to a model: the angles, per side, and the
    segment lengths -- not the frames, fits and diagnostics the CSV keeps."""
    out = {"model_file": str(Path(model_path).resolve()),
           "femoral_torsion": {}, "tibial_torsion": {}}
    for r in rows:
        s = r.get("side", "?")
        fem = {k: round(r[k], 2) for k in
               ("neck_shaft_angle_deg", "anteversion_deg", "neck_length_mm",
                "femur_length_mm") if isinstance(r.get(k), float)}
        if r.get("femur_mesh_file"):                # which bone was measured
            fem["mesh_file"] = r["femur_mesh_file"]
        if r.get("warning"):
            fem["warning"] = r["warning"]
        tib = {k: round(r[k], 2) for k in
               ("tibial_torsion_deg", "tibia_length_mm") if isinstance(r.get(k), float)}
        if r.get("error"):
            fem["error"] = tib["error"] = r["error"]
        out["femoral_torsion"][s] = fem
        out["tibial_torsion"][s] = tib
    return out


def _run_markups(ns) -> int:
    """``measure markups`` -- the femoral angles from MRI landmark files."""
    files = []
    for raw in ns.paths:
        q = Path(raw)
        files += sorted(q.glob("*.mrk.json")) if q.is_dir() else [q]
    if not files:
        print("no .mrk.json files found")
        return 1

    rows, failed = [], 0
    for f in files:
        stem = f.name[:-len(".mrk.json")] if f.name.endswith(".mrk.json") else f.stem
        subject, _, side_word = stem.partition("_")
        side = (side_word or "r")[0].lower()
        if side not in ("r", "l"):
            side = "r"
        try:
            res = markup_femoral_geometry(f, side=side)
        except Exception as e:
            print(f"✗ {stem}: {_err(e)}")
            rows.append({"subject": subject, "side": side, "file": str(f),
                         "error": _err(e)})
            failed += 1
            continue
        rows.append({"subject": subject, **res, "file": str(f), "error": ""})
        print(f"✓ {stem}: NSA={res['neck_shaft_angle_deg']:.1f}°  "
              f"anteversion={res['anteversion_deg']:+.1f}°"
              + (f"  ⚠ {res['warning']}" if res.get("warning") else ""))
    if ns.json:
        print(json.dumps(rows, indent=2))
    if ns.out:
        print(f"→ {_write_rows(rows, ns.out)}")
    return 1 if failed else 0


def _run_torsion(ns) -> int:
    lm = read_landmarks(ns.landmarks) if ns.landmarks else None
    mesh = load_mesh(ns.mesh) if ns.mesh else None
    rows, failed = [], 0
    for mp in ns.models:
        model, state, model_rows = None, None, []
        for s in ns.side:
            tag = f"{Path(mp).stem} {s}"
            print(f"… {tag}", flush=True)
            try:
                if model is None:               # load the .osim once per model
                    model, state, _ = _model_state(mp)
                res = model_torsion(model, side=s, mesh=mesh, landmarks=lm,
                                    model_path=mp, state=state, n_dirs=ns.n_dirs,
                                    search=ns.search,
                                    tiers=(tuple(MEASURE_TIERS) + ("bundled",))
                                    if ns.allow_bundled_geometry else MEASURE_TIERS)
            except Exception as e:
                print(f"✗ {tag}: {_err(e)}")
                rows.append({"model": Path(mp).stem, "side": s, "error": _err(e)})
                model_rows.append(rows[-1])
                failed += 1
                continue
            model_rows.append(res)
            res.setdefault("error", "")
            rows.append(res)
            if res["error"]:
                failed += 1
                print(f"✗ {tag}: {res['error']}")
                continue
            print(f"✓ {tag}: NSA={res.get('neck_shaft_angle_deg', float('nan')):.1f}°  "
                  f"anteversion={res.get('anteversion_deg', float('nan')):+.1f}°  "
                  f"tibial torsion={res.get('tibial_torsion_deg', float('nan')):+.1f}°  "
                  f"({res.get('time_s')}s)"
                  + (f"  ⚠ {res['warning']}" if res.get("warning") else ""))
        if model_rows and not ns.no_json_file:
            out = Path(ns.json_out) if ns.json_out else \
                Path(mp).with_name(f"{Path(mp).stem}_torsion_angles.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(_torsion_summary(mp, model_rows), indent=2),
                           encoding="utf-8")
            print(f"→ {out}")
    if ns.json:
        print(json.dumps(rows, indent=2))
    if ns.out:
        print(f"→ {_write_rows(rows, ns.out)}")
    return 1 if failed else 0


def _run_jcf(p, ns) -> int:
    """`bioscout model measure jcf-coverage` — one hip, one trial."""
    if ns.folder:
        m = find_hip_meshes(ns.folder, ns.side)
        acet, head = m["acetabulum"], m["femoral_head"]
    else:
        acet, head = ns.acetabulum, ns.femoral_head
    if not (acet and head):
        p.error("give FOLDER or --acetabulum/--femoral-head")
    subj = ns.subject or (_subject_label(Path(ns.folder)) if ns.folder else "manual")
    bw = ns.bw or (ns.mass * 9.80665 if ns.mass else None)
    try:
        res = jcf_coverage(acet, head, ns.model, ns.jra, ns.ik, side=ns.side,
                           geometry=ns.geometry, bodyweight=bw,
                           threshold_mm=ns.threshold, n_dirs=ns.n_dirs,
                           spread_deg=ns.spread, landmarks=ns.landmarks)
    except Exception as e:
        print(f"\u2717 {subj} {ns.side}: {e}")
        return 1
    det = res.pop("_details")
    print(f"\u2713 {subj} {ns.side} [{res['joint']}, {res['n_frames']} frames]: "
          f"peak {res['peak_force']} {res['force_unit']}"
          f"{' on covered surface' if res['peak_force_covered'] else ' NOT on covered surface'}"
          f"  \u00b7  load on covered surface {res['load_bearing_coverage_pct']}% of frames"
          f"  \u00b7  rim margin min {res['rim_margin_deg_min']}\u00b0 / at peak "
          f"{res['rim_margin_deg_at_peak']}\u00b0")
    if res["alignment"].startswith("none"):
        print("  \u26a0 no landmarks given \u2014 the meshes are assumed to be in "
              "the model's pelvis frame already; pass --landmarks otherwise")
    if not ns.no_plots:
        d = Path(ns.plots) if ns.plots else (
            Path(ns.out).parent / "figures" if ns.out else Path("coverage_figures"))
        try:
            fig = plot_jcf_coverage({**res, "_details": det},
                                    d / f"jcf_coverage_{subj}_{ns.side}.png",
                                    title=f"{subj} {ns.side}")
            print(f"  figure \u2192 {fig}")
        except Exception as e:
            print(f"  (figure failed: {e})")
    row = {"subject": subj, **res}
    if ns.json:
        print(json.dumps(row, indent=2))
    if ns.out:
        out = Path(ns.out); out.parent.mkdir(parents=True, exist_ok=True)
        new = not out.exists()
        with open(out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row), extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow(row)
        print(f"\u2192 {out}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = build_parser()
    ns = p.parse_args(argv)
    if ns.what == "torsion":
        return _run_torsion(ns)
    if ns.what == "markups":
        return _run_markups(ns)
    if ns.what == "jcf-coverage":
        return _run_jcf(p, ns)
    if ns.what != "coverage":
        p.print_help()
        return 0

    lm = read_landmarks(ns.landmarks) if ns.landmarks else None
    jobs = []
    if ns.acetabulum or ns.femoral_head:
        if not (ns.acetabulum and ns.femoral_head):
            p.error("--acetabulum and --femoral-head go together")
        for s in ns.side[:1]:
            jobs.append((ns.subject or "manual", s, Path(ns.acetabulum), Path(ns.femoral_head),
                         False, ns.whole_femur))
    for f in ns.folders:
        f = Path(f)
        for s in ns.side:
            m = find_hip_meshes(f, s)
            jobs.append((ns.subject or _subject_label(f), s, m["acetabulum"], m["femoral_head"],
                         m["acetabulum_whole"], m["femur_whole"]))
    if not jobs:
        p.error("give FOLDER(s) or --acetabulum/--femoral-head")

    plot_dir = Path(ns.plots) if ns.plots else (
        Path(ns.out).parent / "figures" if ns.out else Path("coverage_figures"))

    rows, failed = [], 0
    for subj, s, acet, head, acet_whole, fem_whole in jobs:
        tag = f"{subj} {s}"
        missing = [n for n, v in (("acetabulum", acet), ("femoral head/femur", head)) if v is None]
        if missing:
            print(f"✗ {tag}: missing {', '.join(missing)} mesh")
            rows.append({"subject": subj, "side": s, "error": "missing " + ", ".join(missing)})
            failed += 1
            continue
        crop = ns.crop_factor or (1.5 if acet_whole else None)
        print(f"… {tag}: {acet.name} + {head.name}" + (" (whole femur)" if fem_whole else ""), flush=True)
        try:
            res = acetabular_coverage(acet, head, side=s, landmarks=lm, whole_femur=fem_whole,
                                      crop_factor=crop, n_dirs=ns.n_dirs,
                                      method=ns.method, threshold_mm=ns.threshold,
                                      min_f=getattr(ns, "min_f", None) if ns.method == "rays" else None,
                                      max_f=getattr(ns, "max_f", None) if ns.method == "rays" else None,
                                      return_details=not ns.no_plots)
        except Exception as e:
            print(f"✗ {tag}: {e}")
            rows.append({"subject": subj, "side": s, "error": repr(e)})
            failed += 1
            continue
        details = res.pop("_details", None)
        if details is not None:
            try:
                fig = plot_hip_coverage({**res, "_details": details},
                                        plot_dir / f"coverage_{subj}_{s}.png", title=tag)
                print(f"  figure → {fig}")
            except Exception as e:  # a figure must never lose the numbers
                print(f"  (figure failed: {e})")
        row = {"subject": subj, **res, "acetabulum_file": str(acet),
               "femoral_head_file": str(head), "error": ""}
        rows.append(row)
        flag = "  ⚠ sphere RMS > 1 mm" if res["sphere_rms_mm"] > 1 else ""
        if res["coverage_sphere_pct"] == 0:
            flag += (f"  ⚠ nothing covered — the acetabulum is "
                     f"{res['gap_min_mm']} mm off the head at its closest; "
                     f"raise --threshold")
        print(f"✓ {tag}: r={res['head_radius_mm']:.1f} mm  area={res['covered_area_mm2']:.0f} mm²  "
              f"coverage={res['coverage_sphere_pct']:.1f}%  ({res['time_s']}s){flag}")

    if not ns.no_plots:
        try:
            fig = plot_coverage_summary(rows, plot_dir / "coverage_summary.png")
            if fig:
                print(f"→ {fig}")
        except Exception as e:
            print(f"(summary figure failed: {e})")

    if ns.json:
        print(json.dumps(rows, indent=2))
    if ns.out:
        out = Path(ns.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        keys = list(dict.fromkeys(k for r in rows for k in r))
        new = not out.exists()
        if not new:
            with open(out, newline="") as f:
                old = next(csv.reader(f), [])
            keys = list(dict.fromkeys(old + keys))
        with open(out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys if new else old, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerows(rows)
        print(f"→ {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
