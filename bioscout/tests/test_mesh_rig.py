"""Tests for the STL -> OSIM auto-rig.

Everything here is built from primitives, so nothing depends on anyone's scan.
The synthetic figure is a box trunk on two tapered legs with the landmark
heights *chosen*, which is what makes the landmark assertions meaningful: we
know where the knee is because we put it there.

The properties worth pinning hardest are the ones whose failure is silent:

* landmarks coming back in the wrong order (a pelvis cut below the knee still
  writes ten STLs and a valid model, it is just nonsense);
* a cut left open (invisible until a joint flexes in a viewer);
* the base model's joints or coordinates changing (every existing .mot file
  quietly stops meaning what it did).
"""
from __future__ import annotations

import numpy as np
import pytest

from bioscout.session.movement_detector import mesh_rig as mr

H = 1.80
CROTCH = 0.470 * H
_LEG_Y0 = 0.02 * H
ANKLE = _LEG_Y0 + 0.125 * (CROTCH - _LEG_Y0)      # station 1 of the leg profile
KNEE = _LEG_Y0 + 0.625 * (CROTCH - _LEG_Y0)       # station 5


# --------------------------------------------------------------------------- #
# synthetic geometry
# --------------------------------------------------------------------------- #


def _tube(centre_xz, y0, y1, radii, n_side=24, n_ring=14):
    """A closed vertical tube with per-level radii — a leg, or a trunk."""
    ys = np.linspace(y0, y1, n_ring)
    r = np.interp(ys, np.linspace(y0, y1, len(radii)), radii)
    a = np.linspace(0, 2 * np.pi, n_side, endpoint=False)
    V = np.stack([np.outer(r, np.cos(a)) + centre_xz[0],
                  np.repeat(ys[:, None], n_side, axis=1),
                  np.outer(r, np.sin(a)) + centre_xz[1]], axis=-1).reshape(-1, 3)
    F = []
    for i in range(n_ring - 1):
        for j in range(n_side):
            a0, b0 = i * n_side + j, i * n_side + (j + 1) % n_side
            a1, b1 = a0 + n_side, b0 + n_side
            F += [(a0, b0, b1), (a0, b1, a1)]
    lo, hi = len(V), len(V) + 1
    V = np.vstack([V, [centre_xz[0], y0, centre_xz[1]], [centre_xz[0], y1, centre_xz[1]]])
    for j in range(n_side):
        F.append((lo, (j + 1) % n_side, j))
        top = (n_ring - 1) * n_side
        F.append((hi, top + j, top + (j + 1) % n_side))
    return V, np.asarray(F, dtype=np.int64)


def _figure(height=H, foot_forward=True):
    """A standing humanoid with known ankle, knee and crotch heights."""
    parts = []
    for sgn in (1, -1):
        z = sgn * 0.09
        # Leg profile, sampled at nine evenly spaced stations between the
        # bottom of the tube and the crotch. Station 1 (12.5 % of the way up,
        # y = ANKLE) is the ankle waist and station 5 (62.5 %, just above KNEE)
        # is the knee waist, with the calf and thigh bulging either side — so
        # the girth search has a real interior minimum to find at each.
        parts.append(_tube((0.0, z), _LEG_Y0, CROTCH,
                           radii=[0.055, 0.030, 0.048, 0.055, 0.052,
                                  0.044, 0.055, 0.065, 0.070]))
        # foot, sticking forward of the ankle so the facing sign is decidable
        fx = 0.09 if foot_forward else -0.09
        parts.append(_tube((fx, z), 0.0, 0.05 * height, radii=[0.055, 0.05]))
    parts.append(_tube((0.0, 0.0), CROTCH - 0.02, 0.82 * height,
                       radii=[0.13, 0.14, 0.15, 0.13]))            # trunk
    parts.append(_tube((0.0, 0.0), 0.82 * height, height,
                       radii=[0.055, 0.09, 0.085]))                # neck + head
    V, F, n = [], [], 0
    for v, f in parts:
        V.append(v)
        F.append(f + n)
        n += len(v)
    return np.vstack(V), np.vstack(F)


MINIMAL_OSIM = """<?xml version="1.0" encoding="UTF-8"?>
<OpenSimDocument Version="40000"><Model name="tiny">
<BodySet><objects>
<Body name="pelvis"><attached_geometry/></Body>
<Body name="femur_r"><attached_geometry/></Body>
<Body name="femur_l"><attached_geometry/></Body>
<Body name="tibia_r"><attached_geometry/></Body>
<Body name="tibia_l"><attached_geometry/></Body>
<Body name="calcn_r"><attached_geometry/></Body>
<Body name="calcn_l"><attached_geometry/></Body>
<Body name="toes_r"><attached_geometry/></Body>
<Body name="toes_l"><attached_geometry/></Body>
<Body name="torso"><attached_geometry/></Body>
</objects></BodySet>
<JointSet><objects>
<CustomJoint name="hip_r"><socket_parent_frame>pelvis_offset</socket_parent_frame>
 <socket_child_frame>femur_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="pelvis_offset">
  <translation>-0.0563 -0.0785 0.0773</translation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="femur_r_offset"><translation>0 0 0</translation>
 </PhysicalOffsetFrame></frames>
 <coordinates><Coordinate name="hip_flexion_r"/></coordinates></CustomJoint>
<CustomJoint name="ankle_r"><socket_parent_frame>tibia_r_offset</socket_parent_frame>
 <socket_child_frame>talus_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="tibia_r_offset">
  <translation>-0.01 -0.40 0</translation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="talus_r_offset"><translation>0 0 0</translation>
 </PhysicalOffsetFrame></frames>
 <coordinates><Coordinate name="ankle_angle_r"/></coordinates></CustomJoint>
<CustomJoint name="subtalar_r"><socket_parent_frame>talus_r_offset</socket_parent_frame>
 <socket_child_frame>calcn_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="talus_r_offset">
  <translation>-0.0488 -0.0420 0.0079</translation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="calcn_r_offset"><translation>0 0 0</translation>
 </PhysicalOffsetFrame></frames>
 <coordinates><Coordinate name="subtalar_angle_r"/></coordinates></CustomJoint>
<CustomJoint name="mtp_r"><socket_parent_frame>calcn_r_offset</socket_parent_frame>
 <socket_child_frame>toes_r_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="calcn_r_offset">
  <translation>0.1788 -0.002 0.0011</translation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="toes_r_offset"><translation>0 0 0</translation>
 </PhysicalOffsetFrame></frames>
 <coordinates><Coordinate name="mtp_angle_r"/></coordinates></CustomJoint>
<CustomJoint name="back"><socket_parent_frame>pelvis_offset</socket_parent_frame>
 <socket_child_frame>torso_offset</socket_child_frame>
 <frames><PhysicalOffsetFrame name="pelvis_offset">
  <translation>-0.1007 0.0815 0</translation></PhysicalOffsetFrame>
 <PhysicalOffsetFrame name="torso_offset"><translation>0 0 0</translation>
 </PhysicalOffsetFrame></frames>
 <coordinates><Coordinate name="lumbar_extension"/></coordinates></CustomJoint>
</objects></JointSet>
</Model></OpenSimDocument>
"""


@pytest.fixture
def base_osim(tmp_path):
    p = tmp_path / "tiny.osim"
    p.write_text(MINIMAL_OSIM)
    return p


@pytest.fixture
def scan(tmp_path):
    V, F = _figure()
    return mr.write_stl_fast(V, F, tmp_path / "scan.stl")


# --------------------------------------------------------------------------- #
# mesh primitives
# --------------------------------------------------------------------------- #


def test_stl_roundtrip(tmp_path):
    V, F = _figure()
    p = mr.write_stl_fast(V, F, tmp_path / "a.stl")
    V2, F2 = mr.load_mesh(p)
    assert len(F2) == len(F)
    V2, F2 = mr.weld(V2, F2)
    # welding an STL must recover roughly the original vertex count, not 3x the
    # face count; the figure's own tubes share a coincident pole or two
    assert len(V) - 5 <= len(V2) <= len(V)


def test_weld_is_required_for_connectivity():
    V, F = _figure()
    loose = V[F].reshape(-1, 3)
    loose_F = np.arange(len(loose)).reshape(-1, 3)
    # unwelded: every edge is its own boundary, so a closed solid looks holed
    assert len(mr.boundary_loops(loose_F)) > 0
    Vw, Fw = mr.weld(loose, loose_F)
    assert mr.boundary_loops(Fw) == []


def test_decimate_preserves_extent():
    V, F = _figure()
    Vd, Fd = mr.decimate(V, F, 0.02)
    assert len(Vd) < len(V)
    assert np.allclose(Vd.min(0), V.min(0), atol=0.03)
    assert np.allclose(Vd.max(0), V.max(0), atol=0.03)


def test_cap_closes_a_cut():
    V, F = _tube((0, 0), 0.0, 1.0, [0.1, 0.1])
    keep = V[F].mean(axis=1)[:, 1] < 0.5           # slice it in half: now open
    Vc, Fc = mr.cap_open_boundaries(V, F[keep])
    assert len(mr.boundary_loops(Fc)) == 0


def test_ellipsoid_is_closed_and_outward():
    V, F = mr.ellipsoid(np.zeros(3), np.array([0.1, 0.2, 0.1]))
    assert mr.boundary_loops(F) == []
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    # a correctly wound closed surface has every normal pointing away from the
    # centre; the pole caps are where this silently goes wrong
    assert (np.einsum("ij,ij->i", n, tri.mean(1)) > 0).all()


# --------------------------------------------------------------------------- #
# orientation and landmarks
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("yaw", [0.0, 37.0, 120.0, -95.0])
def test_orientation_recovers_an_arbitrary_yaw(yaw):
    V, _ = _figure()
    a = np.radians(yaw)
    R = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
    Vo, applied = mr.orient_mesh(V @ R.T, mr.RigConfig(target_height=H))
    assert applied["height_in"] == pytest.approx(H, abs=0.01)
    # feet must end up in front (+x) of the ankles again, whatever the input yaw
    feet = Vo[Vo[:, 1] < 0.05 * H]
    assert feet[:, 0].max() > 0.04


def test_landmarks_match_the_figure_they_were_built_into(scan):
    V, F = mr.load_mesh(scan)
    V, F = mr.weld(V, F)
    cfg = mr.RigConfig(target_height=H)
    Vo, _ = mr.orient_mesh(V, cfg)
    lm = mr.body_landmarks(Vo, cfg, mr.GPK_LANDMARKS)
    assert lm["hip"] == pytest.approx(CROTCH + 0.02 * H, abs=0.05)
    assert lm["knee"] == pytest.approx(KNEE, abs=0.06)
    assert lm["ankle"] == pytest.approx(ANKLE, abs=0.04)
    assert lm["ankle"] < lm["knee"] < lm["hip"] < lm["lumbar"] < lm["neck"]


def test_landmarks_out_of_order_is_an_error_not_a_model():
    V, F = _figure()
    cfg = mr.RigConfig(target_height=H, ankle_h=0.60, knee_h=0.20)
    Vo, _ = mr.orient_mesh(V, cfg)
    with pytest.raises(ValueError, match="out of order"):
        mr.body_landmarks(Vo, cfg, mr.GPK_LANDMARKS)


def test_pinned_landmarks_are_honoured(scan):
    V, F = mr.weld(*mr.load_mesh(scan))
    cfg = mr.RigConfig(target_height=H, knee_h=0.31, hip_h=0.49)
    Vo, _ = mr.orient_mesh(V, cfg)
    lm = mr.body_landmarks(Vo, cfg, mr.GPK_LANDMARKS)
    assert lm["knee"] == pytest.approx(0.31 * H)
    assert lm["hip"] == pytest.approx(0.49 * H)


# --------------------------------------------------------------------------- #
# base model parsing
# --------------------------------------------------------------------------- #


def test_model_landmarks_read_from_the_file(base_osim):
    ml = mr.read_model_landmarks(base_osim)
    assert ml.hip == pytest.approx(np.array([-0.0563, -0.0785, 0.0773]), abs=1e-4)
    assert ml.tibia_len == pytest.approx(0.40)
    # the subtalar PARENT offset is the foot; reading the child puts the ankle
    # on the floor, which is the bug this pins
    assert ml.calcn[1] == pytest.approx(-0.0420, abs=1e-4)
    assert ml.mtp[0] == pytest.approx(0.1788, abs=1e-4)


def test_unparseable_model_falls_back_rather_than_raising(tmp_path):
    p = tmp_path / "junk.osim"
    p.write_text("not xml at all")
    ml = mr.read_model_landmarks(p)
    assert ml.femur_len == mr.GPK_LANDMARKS.femur_len


# --------------------------------------------------------------------------- #
# end to end
# --------------------------------------------------------------------------- #


def test_rig_writes_a_model_that_still_has_the_base_kinematics(scan, base_osim, tmp_path):
    res = mr.rig_mesh(scan, base_model=base_osim, out_dir=tmp_path, name="s01",
                      config=mr.RigConfig(target_height=H))
    assert res.model_path.exists()
    mr.verify_kinematics(base_osim, res.model_path)          # raises if it changed

    for body in ("pelvis", "femur_r", "femur_l", "tibia_r", "tibia_l", "torso"):
        assert body in res.meshes, f"{body} got no geometry"
        assert res.meshes[body][0].exists()

    text = res.model_path.read_text()
    assert f"{res.stl_dir.name}/s01_femur_r.stl" in text


def test_every_written_piece_is_closed(scan, base_osim, tmp_path):
    res = mr.rig_mesh(scan, base_model=base_osim, out_dir=tmp_path, name="s01",
                      config=mr.RigConfig(target_height=H))
    for body, paths in res.meshes.items():
        V, F = mr.weld(*mr.load_mesh(paths[0]))
        assert mr.boundary_loops(F) == [], f"{body} has an open cut"


def test_segments_land_in_their_body_frames(scan, base_osim, tmp_path):
    """A femur mesh must span y = 0 down to -femur_len, not sit where the scan was."""
    res = mr.rig_mesh(scan, base_model=base_osim, out_dir=tmp_path, name="s01",
                      config=mr.RigConfig(target_height=H, joint_fillers=False))
    ml = mr.read_model_landmarks(base_osim)
    V, _ = mr.load_mesh(res.meshes["femur_r"][0])
    # The piece hangs from the body origin: its top is at y ~ 0 and its bottom
    # a femur length below. Not exact — the hip is imposed at the model's own
    # separation while the knee is measured, so the segment is slightly tilted
    # and the cut plane rotates a few centimetres out of y = 0.
    assert V[:, 1].max() == pytest.approx(0.0, abs=0.09)
    assert V[:, 1].min() == pytest.approx(-ml.femur_len, abs=0.09)
    assert np.ptp(V[:, 1]) == pytest.approx(ml.femur_len, rel=0.2)


def test_no_fillers_means_no_extra_geometry(scan, base_osim, tmp_path):
    kw = dict(base_model=base_osim, out_dir=tmp_path, name="s01")
    bare = mr.rig_mesh(scan, config=mr.RigConfig(target_height=H, joint_fillers=False), **kw)
    n_bare = bare.n_triangles_out
    filled = mr.rig_mesh(scan, config=mr.RigConfig(target_height=H), **kw)
    assert filled.n_triangles_out > n_bare
