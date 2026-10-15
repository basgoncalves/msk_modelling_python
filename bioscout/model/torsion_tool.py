"""Impose target femoral and tibial torsion on an OpenSim model.

A model scaled from a generic skeleton carries the template's neck-shaft angle,
anteversion and tibial torsion no matter how the subject is built -- scaling
stretches a bone, it does not twist it (see
:mod:`bioscout.model.measure`, which reports those angles). This module twists
it, in the spirit of the Torsion Tool (Veerkamp et al., J Biomech 2021):

* **anteversion (AVA)** -- rotation about the femoral shaft axis, ramping from
  0 at the base of the neck to the full angle at the knee.
* **neck-shaft angle (NSA)** -- rotation of the head and neck about the axis
  perpendicular to the neck/shaft plane, ramping from 0 at the neck base to the
  full angle at the head.
* **tibial torsion (TT)** -- rotation about the tibial long axis, ramping from
  0 at the knee to the full angle at the ankle.

Everything riding on the bone is carried along: the joint frames, muscle and
ligament path points, wrap objects, and the bone meshes themselves (written out
deformed, so the model draws -- and re-measures -- as the angles you asked for).

Markers are deliberately NOT moved: after a twist the marker set no longer
matches the skin, so re-register it from a static trial rather than trusting
rotated landmarks.

The targets are absolute. The model is measured, a twist is applied, and the
result is measured again; a secant correction and a final check mean the output
is verified rather than assumed -- ``--tol`` sets how close is close enough.

CLI::

    python -m bioscout.model.torsion_tool IN.osim -o OUT.osim \\
        [--nsa 125] [--ava 20] [--tt 30] [--side r l] [--tol 0.5] [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence

from .measure import (MEASURE_TIERS, _axis_in, _knee_joint, _joint_between,
                      _model_state, _perp, _point_in, _side_body, _unit,
                      _vec_in, body_mesh, femoral_geometry, fit_head_sphere,
                      joint_rotation_axis, joint_table, neck_axis_from_mesh,
                      shaft_axis_from_mesh, tibial_geometry)

__all__ = ["Twist", "femur_twists", "tibia_twist", "apply_torsion",
           "build_parser", "main"]


# --------------------------------------------------------------------------- #
# the twist itself
# --------------------------------------------------------------------------- #
def _rot(axis, angle_deg):
    """Rodrigues rotation matrix about a unit ``axis``."""
    import numpy as np
    k = _unit(axis)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    t = math.radians(angle_deg)
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * (K @ K)


class Twist:
    """A tapered rotation about a line, as a callable on points.

    The rotation angle ramps linearly from 0 where a point projects onto
    ``start`` along ``ramp_axis`` to ``angle_deg`` at ``end``, and is held
    constant outside that span -- so the proximal fragment stays put, the
    shaft twists gradually, and the distal fragment moves as one piece.

    origin: a point on the rotation axis (it, and the whole axis, stay fixed).
    """

    def __init__(self, origin, axis, angle_deg: float, start, end,
                 ramp_axis=None):
        import numpy as np
        self.origin = np.asarray(origin, float)
        self.axis = _unit(axis)
        self.angle = float(angle_deg)
        self.ramp = _unit(ramp_axis if ramp_axis is not None else axis)
        self.s0 = float(np.asarray(start, float) @ self.ramp)
        self.s1 = float(np.asarray(end, float) @ self.ramp)

    def fraction(self, p) -> float:
        import numpy as np
        if self.s1 == self.s0:
            return 1.0
        f = (float(np.asarray(p, float) @ self.ramp) - self.s0) / (self.s1 - self.s0)
        return min(1.0, max(0.0, f))

    def rotation_at(self, p):
        return _rot(self.axis, self.angle * self.fraction(p))

    def __call__(self, p):
        """Move a point (given, and returned, in the body frame)."""
        import numpy as np
        p = np.asarray(p, float)
        return self.origin + self.rotation_at(p) @ (p - self.origin)

    def points(self, P):
        """Move an (N, 3) array, one rotation per point (vectorised)."""
        import numpy as np
        P = np.asarray(P, float)
        if abs(self.angle) < 1e-12:
            return P.copy()
        f = np.clip((P @ self.ramp - self.s0) / (self.s1 - self.s0 or 1.0), 0, 1)
        k, rel = self.axis, P - self.origin
        cos, sin = np.cos(np.radians(self.angle * f)), np.sin(np.radians(self.angle * f))
        # Rodrigues, per point
        return (self.origin + rel * cos[:, None]
                + np.cross(k, rel) * sin[:, None]
                + np.outer((rel @ k) * (1 - cos), k))


class _Chain:
    """Several twists applied in order (NSA then AVA on the femur)."""

    def __init__(self, *twists):
        self.twists = [t for t in twists if t is not None]

    def __call__(self, p):
        for t in self.twists:
            p = t(p)
        return p

    def rotation_at(self, p):
        import numpy as np
        R = np.eye(3)
        for t in self.twists:
            R = t.rotation_at(p) @ R
            p = t(p)
        return R

    def points(self, P):
        for t in self.twists:
            P = t.points(P)
        return P


# --------------------------------------------------------------------------- #
# where each bone's twists live
# --------------------------------------------------------------------------- #
def femur_twists(model, side: str, state, model_path=None, mesh=None,
                 d_nsa: float = 0.0, d_ava: float = 0.0, search=None):
    """``(_Chain, geometry dict)`` for one femur, for the given angle changes.

    The neck axis and the shaft axis come from the femur mesh (the same fit
    :func:`bioscout.model.measure.femoral_geometry` measures with), so the
    twist is defined on the bone rather than on the joint frames alone.
    """
    import numpy as np
    femur = _side_body(model, "femur", side)
    tibia = _side_body(model, "tibia", side)
    body = model.getBodySet().get(femur)
    table = joint_table(model)
    hip = _joint_between(table, child=femur)["joint"]
    knee = _knee_joint(table, femur, tibia)["joint"]

    head0 = _point_in(state, hip.getChildFrame(), body)
    knee_c = _point_in(state, knee.getParentFrame(), body)
    if mesh is None:
        mesh = body_mesh(model, femur, model_path, state=state, search=search)
    if mesh is None:
        raise FileNotFoundError(f"no femur mesh for {femur}: the twist needs the "
                                f"bone, not just the joint frames")
    v = np.asarray(mesh.vertices, float)
    d = np.linalg.norm(v - head0, axis=1)
    c, r, _ = fit_head_sphere(v, seed_points=v[d < np.percentile(d, 3)])
    neck_c, neck_ax, _ = neck_axis_from_mesh(mesh, c, knee_c - c, r)
    shaft = shaft_axis_from_mesh(mesh, c, knee_c)          # proximal -> distal

    # NSA: swing the head about the normal of the neck/shaft plane, ramping
    # along the neck from its base (0) to the head centre (1).
    nsa_twist = None
    if abs(d_nsa) > 1e-9:
        normal = _unit(np.cross(neck_ax, shaft))
        nsa_twist = Twist(neck_c, normal, d_nsa, neck_c, c, ramp_axis=neck_ax)

    # AVA: twist about the shaft, ramping from below the neck to the knee. It
    # starts clear of the neck on purpose -- a ramp that runs through the neck
    # twists the neck itself, so the neck axis the angle is measured from moves
    # while you are trying to rotate the condyles relative to it.
    ava_twist = None
    if abs(d_ava) > 1e-9:
        ava_start = neck_c + 0.15 * (knee_c - neck_c)
        ava_twist = Twist(knee_c, shaft, d_ava, ava_start, knee_c, ramp_axis=shaft)

    return _Chain(nsa_twist, ava_twist), {
        "body": femur, "head_centre": c, "head_radius": r,
        "neck_centre": neck_c, "neck_axis": neck_ax, "shaft_axis": shaft,
        "knee_centre": knee_c, "mesh": mesh}


def tibia_twist(model, side: str, state, d_tt: float = 0.0):
    """``(Twist | None, geometry dict)`` for one tibia."""
    import numpy as np
    femur = _side_body(model, "femur", side)
    tibia = _side_body(model, "tibia", side)
    body = model.getBodySet().get(tibia)
    table = joint_table(model)
    knee = _knee_joint(table, femur, tibia)["joint"]
    ankle = _joint_between(table, parent=tibia)["joint"]
    knee_c = _point_in(state, knee.getChildFrame(), body)
    ankle_c = _point_in(state, ankle.getParentFrame(), body)
    long_axis = _unit(ankle_c - knee_c)                     # proximal -> distal
    twist = None
    if abs(d_tt) > 1e-9:
        twist = Twist(ankle_c, long_axis, d_tt, knee_c, ankle_c,
                      ramp_axis=long_axis)
    return twist, {"body": tibia, "knee_centre": knee_c, "ankle_centre": ankle_c,
                   "long_axis": long_axis}


# --------------------------------------------------------------------------- #
# applying a twist to everything that rides on the bone
# --------------------------------------------------------------------------- #
def _euler_xyz(R):
    """Body-fixed XYZ Euler angles (rad) of a rotation matrix.

    The inverse of :func:`_rot_from_euler`, i.e. OpenSim's convention
    ``R = Rx(a) @ Ry(b) @ Rz(c)`` -- not the Rz-Ry-Rx one, which looks almost
    identical and silently mis-orients every frame it touches.
    """
    import numpy as np
    sb = max(-1.0, min(1.0, R[0, 2]))
    if abs(sb) < 1 - 1e-9:
        return np.array([math.atan2(-R[1, 2], R[2, 2]), math.asin(sb),
                         math.atan2(-R[0, 1], R[0, 0])])
    return np.array([math.atan2(R[2, 1], R[1, 1]), math.asin(sb), 0.0])


def _frames_on(model, body_name: str, state):
    """Offset frames whose own parent is this body (the ones we can rewrite)."""
    import opensim
    out = []
    for f in model.getComponentsList():
        pof = opensim.PhysicalOffsetFrame.safeDownCast(f)
        if pof is None:
            continue
        try:
            if pof.getParentFrame().getName() != body_name:
                continue
        except Exception:
            continue
        out.append(pof)
    return out


def _twist_offset_frame(pof, twist, opensim):
    """Rotate and move one PhysicalOffsetFrame inside its parent body."""
    import numpy as np
    t = pof.get_translation()
    p = np.array([t.get(0), t.get(1), t.get(2)])
    o = pof.get_orientation()
    from .measure import _unit  # noqa: F401  (keep the import local and explicit)
    R_old = _rot_from_euler(np.array([o.get(0), o.get(1), o.get(2)]))
    R_new = twist.rotation_at(p) @ R_old
    p_new = twist(p)
    pof.set_translation(opensim.Vec3(*[float(x) for x in p_new]))
    e = _euler_xyz(R_new)
    pof.set_orientation(opensim.Vec3(*[float(x) for x in e]))


def _rot_from_euler(e):
    """Body-fixed XYZ Euler angles (rad) -> rotation matrix."""
    import numpy as np
    cx, cy, cz = np.cos(e)
    sx, sy, sz = np.sin(e)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rx @ Ry @ Rz


def twist_body(model, state, body_name: str, twist, *, model_path=None,
               geometry_dir: Optional[Path] = None, report: Optional[dict] = None,
               search=None, require_mesh: bool = False):
    """Apply ``twist`` to everything attached to ``body_name``.

    Moves, in the body's own frame: offset frames (so joint centres and their
    orientations follow the bone), muscle and ligament path points attached
    directly to the body, wrap objects, and the attached meshes -- the deformed
    meshes are written into ``geometry_dir`` and the model repointed at them.

    Markers are left where they are on purpose: re-register them from a static
    trial instead.
    """
    import numpy as np
    import opensim
    counts = {"frames": 0, "path_points": 0, "wrap_objects": 0, "meshes": 0,
              "skipped_points": 0}
    body = model.getBodySet().get(body_name)

    for pof in _frames_on(model, body_name, state):
        _twist_offset_frame(pof, twist, opensim)
        counts["frames"] += 1

    for comp in model.getComponentsList():
        pp = opensim.PathPoint.safeDownCast(comp)
        if pp is not None:
            try:
                same = pp.getParentFrame().getName() == body_name
            except Exception:
                continue
            if not same:
                continue
            loc = pp.get_location()
            p = twist(np.array([loc.get(0), loc.get(1), loc.get(2)]))
            pp.set_location(opensim.Vec3(*[float(x) for x in p]))
            counts["path_points"] += 1
            continue
        moving = opensim.MovingPathPoint.safeDownCast(comp)
        if moving is not None:
            try:
                if moving.getParentFrame().getName() == body_name:
                    counts["skipped_points"] += 1
            except Exception:
                pass

    wraps = body.getWrapObjectSet()
    for i in range(wraps.getSize()):
        w = wraps.get(i)
        t, r = w.get_translation(), w.get_xyz_body_rotation()
        p = np.array([t.get(0), t.get(1), t.get(2)])
        R_new = twist.rotation_at(p) @ _rot_from_euler(
            np.array([r.get(0), r.get(1), r.get(2)]))
        w.set_translation(opensim.Vec3(*[float(x) for x in twist(p)]))
        w.set_xyz_body_rotation(opensim.Vec3(*[float(x) for x in _euler_xyz(R_new)]))
        counts["wrap_objects"] += 1

    if geometry_dir is not None:
        counts["meshes"] += _twist_meshes(model, state, body_name, twist,
                                          model_path, Path(geometry_dir),
                                          search=search, require=require_mesh)
    if report is not None:
        report.update(counts)
    return counts


def _twist_meshes(model, state, body_name: str, twist, model_path, geometry_dir: Path,
                  search=None, require: bool = False) -> int:
    """Deform every mesh on the body and repoint the model at the new files."""
    import numpy as np
    import opensim
    import trimesh
    from .io import load_mesh
    from .measure import resolve_mesh_path

    body = model.getBodySet().get(body_name)
    geometry_dir.mkdir(parents=True, exist_ok=True)
    skipped = []
    meshes = [m for m in (opensim.Mesh.safeDownCast(g)
                          for g in model.getComponentsList()) if m is not None]
    done = 0
    for mesh in meshes:
        frame = mesh.getFrame()
        try:
            if frame.findBaseFrame().getName() != body_name:
                continue
        except Exception:
            continue
        raw = mesh.get_mesh_file()
        # the same resolution the measurement uses, or the twist would deform
        # one file while the angles are read off another
        path, tier = resolve_mesh_path(raw, model_path, search)
        if path is None or tier not in MEASURE_TIERS or not Path(path).is_file():
            skipped.append(f"{raw} ({tier})")
            continue
        m = load_mesh(path)
        sf = mesh.get_scale_factors()
        scale = np.array([sf.get(0), sf.get(1), sf.get(2)])
        R = np.column_stack([_axis_in(state, frame, body, k) for k in range(3)])
        o = _point_in(state, frame, body)

        v_body = (np.asarray(m.vertices, float) * scale) @ R.T + o   # -> body
        v_body = twist.points(v_body)                                # twisted
        v_file = ((v_body - o) @ R)                                  # -> frame
        out = geometry_dir / f"{Path(path).stem}_torsion.stl"
        trimesh.Trimesh(vertices=v_file, faces=np.asarray(m.faces),
                        process=False).export(out)
        # absolute while we work (the output model is not written yet, so a
        # relative path would not resolve on the next measurement pass); made
        # relative again just before the model is saved
        mesh.set_mesh_file(str(out.resolve()))
        mesh.set_scale_factors(opensim.Vec3(1.0, 1.0, 1.0))          # baked in
        done += 1
    if done == 0 and skipped and require:
        # for the femur, twisting the frames while the bone stays put makes
        # every later measurement meaningless (the angles are read off the
        # mesh), so stop rather than produce a model whose joints and mesh
        # disagree. The tibia's angle comes from the joints, so a missing
        # tibia mesh only costs the visual.
        raise FileNotFoundError(
            f"no usable mesh for {body_name} to deform: " + "; ".join(skipped)
            + ". Pass --search with the folder holding this model's bones.")
    return done


# --------------------------------------------------------------------------- #
# hitting absolute targets
# --------------------------------------------------------------------------- #
def _relativise_meshes(model, geometry_dir: Path) -> None:
    """Point the written meshes at ``<model>_Geometry/x.stl``, not at absolute
    paths, so the model still finds its bones on another machine."""
    import opensim
    for g in model.getComponentsList():
        mesh = opensim.Mesh.safeDownCast(g)
        if mesh is None:
            continue
        raw = Path(mesh.get_mesh_file())
        if raw.is_absolute() and raw.parent.name == geometry_dir.name:
            mesh.set_mesh_file(f"{geometry_dir.name}/{raw.name}")


def _ava_from_frames(model, side: str, state, geom) -> float:
    """Anteversion from the stored neck landmarks and the knee's flexion axis.

    The solver uses this rather than re-detecting the neck on the freshly
    deformed mesh: the AVA twist leaves the neck alone by construction, so the
    only thing that moves is the condylar axis, and reading it from the joint
    makes the step exact instead of noisy. The mesh-based measurement still has
    the last word in the report.
    """
    from .measure import femoral_anteversion
    femur = _side_body(model, "femur", side)
    tibia = _side_body(model, "tibia", side)
    body = model.getBodySet().get(femur)
    knee = _knee_joint(joint_table(model), femur, tibia)["joint"]
    cond = joint_rotation_axis(state, knee, body)
    knee_c = _point_in(state, knee.getParentFrame(), body)
    return femoral_anteversion(geom["head_centre"], geom["neck_centre"], knee_c,
                               cond, side)


def _femur_geom(model, side: str, state, model_path, search=None):
    """The femur's head/neck/shaft landmarks, from its mesh (metres)."""
    _, geom = femur_twists(model, side, state, model_path=model_path, search=search)
    return geom


def _measure(model_path, side, state=None, model=None, search=None) -> dict:
    """Current NSA / AVA / TT of a model on disk (or in memory)."""
    src = model if model is not None else model_path
    fem = femoral_geometry(src, side, model_path=model_path, state=state, search=search)
    tib = tibial_geometry(src, side, model_path=model_path, state=state)
    if fem.get("error"):
        raise RuntimeError(fem["error"])
    return {"nsa": fem["neck_shaft_angle_deg"], "ava": fem["anteversion_deg"],
            "tt": tib["tibial_torsion_deg"]}


def apply_torsion(model_path, out_path, *, nsa: Optional[float] = None,
                  ava: Optional[float] = None, tt: Optional[float] = None,
                  sides: Sequence[str] = ("r", "l"), tol: float = 0.5,
                  max_passes: int = 3, outer_passes: int = 3,
                  search: Optional[Sequence] = None, plots: bool = True,
                  name_suffix: str = "_torsion", verbose: bool = True,
                  relative: bool = False,
                  defaults: Optional[Dict[str, float]] = None) -> dict:
    """Write a copy of ``model_path`` whose torsion matches the targets.

    nsa, ava, tt: absolute targets in degrees (``None`` leaves that angle as it
        is). Signs follow :mod:`bioscout.model.measure`: anteversion positive =
        anteverted, tibial torsion positive = external.
    tol: stop once every requested angle is within this many degrees.
    max_passes: secant steps allowed per angle. The first applies the naive
        delta, later ones a correction from the gain just observed -- which is
        what makes the ramp's exact sign and gain irrelevant.
    outer_passes: how many times to run the whole NSA-AVA-TT sequence. The
        angles share the shaft axis, so one more sweep cleans up the small
        interaction between them.
    plots: also write the moment-arm comparison (original vs twisted vs
        literature) into ``<out>_moment_arms/``.
    name_suffix: appended to the model's name tag, so the GUI navigator tells
        the two models apart.

    relative: follow Veerkamp et al. (2021) instead of solving for an absolute
        target. nsa/ava/tt are then the SUBJECT's measured angles and
        ``defaults`` the GENERIC model's, measured by the SAME method; the
        difference is applied once, open loop, with no re-measurement. This is
        the procedure's own safeguard: any bias in how an angle is measured
        cancels in the subtraction, so it never matters that the tool's
        mesh-based measurement of the generic disagrees with, say, a markup
        measurement on MRI. Absolute mode (the default) instead drives the
        tool's own measurement onto the target, which mixes the two methods.
    defaults: {"nsa":..., "ava":..., "tt":...} for ``relative`` -- the generic
        model's angles. Measure them once with the same method used on the
        subjects and keep them fixed for the cohort.

    Returns a report: the angles before and after, per side, and what moved.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    geometry_dir = out_path.parent / f"{out_path.stem}_Geometry"

    model, state, src = _model_state(model_path)
    model_path = Path(model_path)
    report = {"model_in": str(model_path.resolve()), "model_out": str(out_path.resolve()),
              "targets": {"nsa": nsa, "ava": ava, "tt": tt}, "sides": {}}

    for side in sides:
        before = _measure(model_path, side, state=state, model=model, search=search)
        want = {"nsa": nsa, "ava": ava, "tt": tt}
        current, applied, moved = dict(before), {"nsa": 0.0, "ava": 0.0, "tt": 0.0}, {}

        # One angle at a time, in this order. NSA first because swinging the
        # neck also turns it about the shaft, which is what AVA measures --
        # solving the two together oscillates, solving them in sequence does
        # not. Each angle uses a secant step, so the ramp's exact sign and
        # gain (a tapered twist moves the measured axis by less than the angle
        # applied) are found from the model rather than assumed.
        rel = None
        if relative:
            # Veerkamp et al. (2021): the target is the subject's angle minus
            # the generic's, both measured the SAME way, so any bias in the
            # measurement method cancels. That makes it a RELATIVE TARGET --
            # before + delta -- and nothing else about the procedure changes.
            # Reaching it is still the solver's job: a tapered twist moves the
            # measured angle by less than the angle applied, and in the
            # opposite sense, so an open-loop delta lands short and on the
            # wrong side. One secant correction per angle is enough here
            # because the target is small (subject - generic, not an absolute
            # angle), which is also why one outer pass suffices.
            rel = {k: (None if want[k] is None
                       else float(want[k]) - float((defaults or {}).get(k, 0.0)))
                   for k in want}
            want = {k: (None if rel[k] is None else before[k] + rel[k])
                    for k in want}
            outer_passes, max_passes = 1, max(2, int(max_passes))

        for _outer in range(int(outer_passes)):
          done = all(want[k] is None or abs(current[k] - want[k]) <= tol
                     for k in want)
          if done:
              break
          for key in ("nsa", "ava", "tt"):
            if want[key] is None:
                continue
            slope, last = None, None
            geom = None
            if key == "ava":
                # landmarks fixed once, after any NSA change: the AVA twist
                # does not move them
                geom = _femur_geom(model, side, state, model_path, search=search)
                current = dict(current, ava=_ava_from_frames(model, side, state, geom))
                slope = -1.0        # a rigid distal rotation of +x lowers AVA by x
            for _pass in range(int(max_passes)):
                miss = want[key] - current[key]
                if abs(miss) <= tol:
                    break
                step = miss / (slope if slope and abs(slope) > 1e-3 else 1.0)
                step = max(-90.0, min(90.0, step))
                d = {"nsa": 0.0, "ava": 0.0, "tt": 0.0, key: step}

                if key in ("nsa", "ava"):
                    twist, _ = femur_twists(model, side, state, model_path=model_path,
                                            d_nsa=d["nsa"], d_ava=d["ava"],
                                            search=search)
                    twist_body(model, state, _side_body(model, "femur", side), twist,
                               model_path=model_path, geometry_dir=geometry_dir,
                               report=moved, search=search, require_mesh=True)
                else:
                    twist, _ = tibia_twist(model, side, state, d_tt=d["tt"])
                    if twist is not None:
                        twist_body(model, state, _side_body(model, "tibia", side),
                                   twist, model_path=model_path,
                                   geometry_dir=geometry_dir, search=search)
                state = model.initSystem()           # frames moved: re-realise
                applied[key] += step
                last = current[key]
                if key == "ava":
                    current = dict(current,
                                   ava=_ava_from_frames(model, side, state, geom))
                else:
                    current = _measure(model_path, side, state=state, model=model, search=search)
                slope = (current[key] - last) / step
                if verbose:
                    print(f"   {side} {key}: {last:+.1f} -> {current[key]:+.1f} "
                          f"(applied {step:+.1f}, gain {slope:+.2f})", flush=True)

          # the angles interact a little through the shared shaft axis, so the
          # honest, mesh-based measurement reopens the sequence if needed
          current = _measure(model_path, side, state=state, model=model, search=search)

        current = _measure(model_path, side, state=state, model=model, search=search)  # the mesh has the last word
        residual = {k: (None if want[k] is None else round(current[k] - want[k], 2))
                    for k in want}
        report["sides"][side] = {
            "before": {k: round(v, 2) for k, v in before.items()},
            "after": {k: round(v, 2) for k, v in current.items()},
            "applied_deg": {k: round(v, 2) for k, v in applied.items()},
            "residual_deg": residual,
            "within_tol": all(r is None or abs(r) <= tol for r in residual.values()),
            "moved": moved,
        }
        if rel is not None:
            report["sides"][side].update({
                "mode": "relative (Veerkamp 2021)",
                "generic_defaults": {k: v for k, v in (defaults or {}).items()
                                     if v is not None},
                "requested_delta_deg": {k: (None if v is None else round(v, 2))
                                        for k, v in rel.items()},
                "target_deg": {k: (None if v is None else round(v, 2))
                               for k, v in want.items()},
            })

    _relativise_meshes(model, geometry_dir)
    # the name tag is what the OpenSim GUI's navigator shows, so two models
    # from the same subject are otherwise both called "009"
    if not model.getName().endswith(name_suffix):
        model.setName(model.getName() + name_suffix)
    model.finalizeConnections()
    model.printToXML(str(out_path))
    report["model_name"] = model.getName()
    report["geometry_dir"] = str(geometry_dir)

    if plots:
        report["moment_arms"] = moment_arm_report(
            model_path, out_path, sides=sides,
            out_dir=out_path.parent / f"{out_path.stem}_moment_arms",
            verbose=verbose)
    report["markers"] = ("not moved on purpose -- re-register the marker set "
                         "from a static trial before scaling or IK")
    return report


# --------------------------------------------------------------------------- #
# did the twist do anything sensible? moment arms, against literature
# --------------------------------------------------------------------------- #
def moment_arm_report(before, after, out_dir, *, sides: Sequence[str] = ("r",),
                      literature_csv=None, n: int = 60, verbose: bool = True) -> dict:
    """Moment-arm figures for the two models, with the literature bands.

    A twist that leaves every moment arm untouched did nothing, and one that
    throws a muscle path through the bone shows up here as a curve that leaves
    the literature band -- so this is the check that says whether the new model
    is usable, not just whether the angles came out.

    Writes one figure per moment DOF plus ``moment_arm_curves.csv`` and
    ``validation_rmse.csv`` into ``out_dir`` (one subfolder per side).
    """
    out = {"dir": str(Path(out_dir)), "files": [], "error": ""}
    try:
        from bioscout.model.inspect.multi_model import compare_models
    except Exception as e:                      # the figures must never lose a good model
        out["error"] = f"moment-arm report unavailable: {e}"
        return out
    for side in sides:
        side_dir = Path(out_dir) / f"side_{side}"
        try:
            files = compare_models([str(before), str(after)], str(side_dir),
                                   literature_csv=literature_csv,
                                   side=f"_{side.lower()[0]}", n=n)
            out["files"] += [str(side_dir / f) for f in files]
            if verbose:
                print(f"  moment arms ({side}) → {side_dir}", flush=True)
        except Exception as e:
            out["error"] += f"{side}: {type(e).__name__}: {e}; "
            if verbose:
                print(f"  (moment-arm report failed for {side}: {e})")
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bioscout model torsion-tool",
        description="impose target femoral/tibial torsion on an .osim model")
    p.add_argument("model", metavar="OSIM")
    p.add_argument("-o", "--out", metavar="OSIM", required=True)
    p.add_argument("--nsa", type=float, help="target neck-shaft angle (deg)")
    p.add_argument("--ava", type=float, help="target anteversion (deg, + = anteverted)")
    p.add_argument("--tt", type=float, help="target tibial torsion (deg, + = external)")
    p.add_argument("--side", nargs="+", default=["r", "l"], choices=["r", "l"])
    p.add_argument("--relative", action="store_true",
                   help="Veerkamp 2021 procedure: treat --nsa/--ava/--tt as the "
                        "SUBJECT's angles and apply (subject - generic) once, "
                        "open loop. Needs --default-nsa/--default-ava/--default-tt, "
                        "the generic's angles measured the SAME way as the "
                        "subject's. No iteration, and measurement bias cancels.")
    p.add_argument("--default-nsa", type=float, metavar="DEG",
                   help="the GENERIC model's neck-shaft angle (--relative)")
    p.add_argument("--default-ava", type=float, metavar="DEG",
                   help="the GENERIC model's anteversion (--relative)")
    p.add_argument("--default-tt", type=float, default=0.0, metavar="DEG",
                   help="the GENERIC model's tibial torsion (--relative, default 0)")
    p.add_argument("--tol", type=float, default=0.5, metavar="DEG")
    p.add_argument("--passes", type=int, default=3,
                   help="secant steps per angle (default 3)")
    p.add_argument("--outer-passes", type=int, default=3,
                   help="sweeps through NSA/AVA/TT (default 3)")
    p.add_argument("--search", action="append", metavar="DIR",
                   help="extra folder to find the model's bone meshes in; repeatable")
    p.add_argument("--no-plots", action="store_true",
                   help="skip the moment-arm comparison figures")
    p.add_argument("--name-suffix", default="_torsion", metavar="TEXT",
                   help="appended to the model's name tag (default: _torsion)")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = build_parser().parse_args(argv)
    if ns.nsa is None and ns.ava is None and ns.tt is None:
        print("nothing to do: give --nsa, --ava and/or --tt")
        return 2
    print(f"… {Path(ns.model).name} -> {Path(ns.out).name}", flush=True)
    if ns.relative:
        missing = [f"--default-{k}" for k, v in (("nsa", ns.nsa), ("ava", ns.ava))
                   if v is not None and getattr(ns, f"default_{k}") is None]
        if missing:
            print("--relative needs the generic's own angles: "
                  + ", ".join(missing)
                  + "\n  measure them once with the same method you used on the "
                    "subjects, e.g.\n"
                    "  bioscout model measure torsion GENERIC.osim")
            return 2
    rep = apply_torsion(ns.model, ns.out, nsa=ns.nsa, ava=ns.ava, tt=ns.tt,
                        sides=ns.side, tol=ns.tol, max_passes=ns.passes,
                        outer_passes=ns.outer_passes, search=ns.search,
                        plots=not ns.no_plots, name_suffix=ns.name_suffix,
                        relative=ns.relative,
                        defaults={"nsa": ns.default_nsa, "ava": ns.default_ava,
                                  "tt": ns.default_tt} if ns.relative else None)
    ok = True
    for side, r in rep["sides"].items():
        b, a = r["before"], r["after"]
        ok &= r["within_tol"]
        print(f"{'✓' if r['within_tol'] else '✗'} {side}: "
              f"NSA {b['nsa']:.1f}→{a['nsa']:.1f}  "
              f"AVA {b['ava']:+.1f}→{a['ava']:+.1f}  "
              f"TT {b['tt']:+.1f}→{a['tt']:+.1f}   "
              f"({r['moved'].get('path_points', 0)} path points, "
              f"{r['moved'].get('frames', 0)} frames, "
              f"{r['moved'].get('wrap_objects', 0)} wraps, "
              f"{r['moved'].get('meshes', 0)} meshes)")
    print(f"→ {ns.out}   (model name: {rep.get('model_name')})")
    print(f"  geometry → {rep['geometry_dir']}")
    ma = rep.get("moment_arms") or {}
    if ma.get("files"):
        print(f"  moment arms → {ma['dir']}")
    elif ma.get("error"):
        print(f"  moment arms: {ma['error']}")
    print("  markers were not moved: re-register them from a static trial")
    if ns.json:
        print(json.dumps(rep, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
