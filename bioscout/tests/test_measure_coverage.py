import numpy as np
import trimesh

from bioscout.model.measure import acetabular_coverage, fit_sphere, pelvic_frame


def cup(radius, half_angle_deg):
    """Spherical cap around +y (superior) with given half-angle."""
    s = trimesh.creation.icosphere(subdivisions=5, radius=radius)
    ang = np.degrees(np.arccos(s.triangles_center[:, 1] / radius))
    s.update_faces(ang <= half_angle_deg)
    s.remove_unreferenced_vertices()
    return s


def test_sphere_fit():
    rng = np.random.default_rng(0)
    d = rng.normal(size=(500, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
    c, r, rms = fit_sphere(d * 24 + [10, -5, 3])
    assert np.allclose(c, [10, -5, 3], atol=1e-6) and abs(r - 24) < 1e-6


def test_frame_identity():
    _, R = pelvic_frame([0, 0, 100], [0, 0, -100], [0, -80, 0])
    assert np.allclose(R, np.eye(3))


def test_nearest_needs_a_big_enough_threshold():
    """The head-acetabulum gap sets the useful threshold range."""
    head = trimesh.creation.icosphere(subdivisions=4, radius=25)
    tight = acetabular_coverage(cup(27, 60), head, side="r", method="nearest",
                                threshold_mm=1, n_dirs=4000)
    loose = acetabular_coverage(cup(27, 60), head, side="r", method="nearest",
                                threshold_mm=4, n_dirs=4000)
    assert tight["coverage_sphere_pct"] == 0
    assert loose["coverage_sphere_pct"] > 10
    assert 1.5 < tight["gap_min_mm"] < 2.5      # 27 - 25


def test_cup_60deg_rays():
    """A 60-degree spherical cap covers 1 - cos(60) = 50% of the hemisphere."""
    lm = {"ASIS_R": np.array([0, 0, 100.0]), "ASIS_L": np.array([0, 0, -100.0]),
          "PUBIC_SYMPHYSIS": np.array([0, -80.0, 0])}
    head = trimesh.creation.icosphere(subdivisions=4, radius=25)
    res = acetabular_coverage(cup(27, 60), head, side="r", landmarks=lm,
                              method="rays", threshold_mm=4, n_dirs=6000)
    assert abs(res["coverage_superior_hemisphere_pct"] - 50) < 4
    assert abs(res["lcea_deg"] - 60) < 3
    assert abs(res["acea_deg"] - 60) < 3
