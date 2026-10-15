"""`bioscout plot kinematics` — joint angles and IK marker errors across iterations.

numpy + matplotlib only: the module reads .mot/.sto as text, so none of this
needs OpenSim. The session is built on disk in the numbered layout because the
file discovery IS the thing most likely to break.
"""
import csv
import os
import shutil
import tempfile
import unittest

import numpy as np

from bioscout import cli
from bioscout.plot import kinematics as K


def _sto(path, names, A, degrees=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x\nversion=1\nnRows=%d\nnColumns=%d\ninDegrees=%s\nendheader\n"
                % (len(A), len(names), "yes" if degrees else "no"))
        f.write("\t".join(names) + "\n")
        for r in A:
            f.write("\t".join("%.8f" % v for v in r) + "\n")


def _trial(session, iteration, trial, offset=0.0, rms=0.01, angle_name="joint_angles.mot",
           markers=("RASI", "LASI", "RTH1")):
    d = os.path.join(session, "3_iterations", iteration, trial, "external_biomechanics")
    t = np.linspace(0.0, 1.0, 51)
    knee = 30 + 30 * np.sin(2 * np.pi * t) + offset
    rot = ((170 + 20 * t + 180) % 360) - 180          # crosses +180 -> -180
    _sto(os.path.join(d, angle_name),
         ["time", "pelvis_tilt", "pelvis_rotation", "pelvis_tx", "knee_angle_r", "knee_angle_l"],
         np.column_stack([t, 0 * t + 5 + offset, rot, 0 * t + 0.1, knee, knee[::-1]]))
    _sto(os.path.join(d, "_ik_marker_errors.sto"),
         ["time", "total_squared_error", "marker_error_RMS", "marker_error_max"],
         np.column_stack([t, 0 * t, 0 * t + rms, 0 * t + 3 * rms]), degrees=False)
    _sto(os.path.join(d, "_ik_marker_errors_all.sto"), ["time"] + list(markers),
         np.column_stack([t] + [0 * t + rms * (k + 1) for k in range(len(markers))]))


class TestPlotKinematics(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bs_kin_")
        self.s = os.path.join(self.root, "simulations", "S01", "sess")
        os.makedirs(self.s)
        with open(os.path.join(self.s, "session.yaml"), "w") as f:
            f.write("subject: S01\nsession: sess\niterations:\n"
                    "  zeta: {label: Zeta model, color: '#E66101'}\n"
                    "  alpha: {color: '#1B7A3D'}\n")
        _trial(self.s, "alpha", "Walk_01", offset=0.0, rms=0.010)
        _trial(self.s, "zeta", "Walk_01", offset=4.0, rms=0.030, angle_name="ik.mot",
               markers=("RASI", "LASI"))
        _trial(self.s, "alpha", "Walk_02", rms=0.012)
        os.makedirs(os.path.join(self.s, "3_iterations", "empty"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _csv(self, name):
        with open(os.path.join(self.s, "4_outputs", "kinematics", name)) as f:
            return list(csv.DictReader(f))

    def test_writes_into_4_outputs(self):
        log = []
        w = K.kinematics_session(self.s, log=log.append)
        names = sorted(os.path.basename(p) for p in w)
        self.assertEqual(names, ["joint_angles.csv", "joint_angles_Walk_01.png",
                                 "joint_angles_Walk_02.png", "marker_errors.csv",
                                 "marker_errors_Walk_01.png", "marker_errors_Walk_02.png",
                                 "marker_errors_overview.png"])
        for p in w:
            self.assertTrue(p.startswith(os.path.join(self.s, "4_outputs", "kinematics")))
            self.assertGreater(os.path.getsize(p), 0)
        # an iteration with no results is reported, not silently dropped
        self.assertTrue(any("empty" in m and "no IK results" in m for m in log))

    def test_marker_error_table_is_in_mm(self):
        K.kinematics_session(self.s, log=lambda *_: None)
        rows = {(r["trial"], r["iteration"]): r for r in self._csv("marker_errors.csv")}
        z = rows[("Walk_01", "zeta")]
        self.assertAlmostEqual(float(z["rms_mean_mm"]), 30.0, places=3)
        self.assertAlmostEqual(float(z["max_peak_mm"]), 90.0, places=3)
        self.assertEqual(z["worst_marker"], "LASI")
        self.assertAlmostEqual(float(z["worst_marker_mean_mm"]), 60.0, places=3)

    def test_session_yaml_order_and_reference(self):
        self.assertEqual(K.session_order(self.s, ["alpha", "empty", "zeta"]),
                         ["zeta", "alpha", "empty"])
        K.kinematics_session(self.s, reference="alpha", log=lambda *_: None)
        rows = [r for r in self._csv("joint_angles.csv")
                if r["trial"] == "Walk_01" and r["iteration"] == "zeta"]
        knee = next(r for r in rows if r["coordinate"] == "knee_angle_r")
        self.assertEqual(knee["reference"], "alpha")
        self.assertAlmostEqual(float(knee["mean_diff_vs_ref"]), 4.0, places=3)
        self.assertAlmostEqual(float(knee["rmsd_vs_ref"]), 4.0, places=3)

    def test_rotation_is_unwrapped(self):
        d = K.load_angles(K.ik_file(self.s, "alpha", "Walk_01", K.ANGLE_FILES))
        self.assertAlmostEqual(float(np.ptp(d["pelvis_rotation"])), 20.0, places=4)
        self.assertLess(abs(float(np.mean(d["pelvis_rotation"]))), 180.0 + 1e-9)
        self.assertAlmostEqual(float(d["pelvis_tx"][0]), 0.1)        # translations untouched

    def test_radians_become_degrees(self):
        p = os.path.join(self.root, "rad.mot")
        _sto(p, ["time", "knee_angle_r"], np.array([[0, np.pi / 2], [1, np.pi / 2]]),
             degrees=False)
        self.assertAlmostEqual(float(K.load_angles(p)["knee_angle_r"][0]), 90.0, places=4)

    def test_styles_come_from_session_yaml(self):
        st = K.iteration_styles(self.s, ["zeta", "alpha", "empty"])
        self.assertEqual(st["zeta"][:2], ("Zeta model", "#E66101"))
        self.assertEqual(st["alpha"][:2], ("alpha", "#1B7A3D"))
        self.assertEqual(st["empty"][1], K.FALLBACK[0])

    def test_filters_and_nothing_to_draw(self):
        w = K.kinematics_session(self.s, trials=["Walk_02"], log=lambda *_: None)
        self.assertFalse(any("Walk_01" in os.path.basename(p) for p in w))
        out = os.path.join(self.root, "elsewhere")
        self.assertEqual(K.kinematics_session(self.s, skip=["ALPHA", "zeta"], out_dir=out,
                                              log=lambda *_: None), [])
        self.assertFalse(os.path.exists(out))

    def test_cli_route_and_session_discovery(self):
        kind, code = cli.route(["plot", "kinematics", self.root, "--trial", "Walk_01"])
        self.assertEqual((kind, code), ("exit", 0))
        self.assertTrue(os.path.isfile(os.path.join(
            self.s, "4_outputs", "kinematics", "marker_errors_Walk_01.png")))
        self.assertEqual(K.main([os.path.join(self.root, "nope")]), 2)

    def test_kinematics_is_not_swallowed_as_a_figure_key(self):
        """`plot <anything>` defaults to `plot figures <anything>`; the action
        names are the exceptions and this one must be among them."""
        kind, _ = cli.route(["plot", "kinematics", os.path.join(self.root, "nope")])
        self.assertEqual(kind, "exit")


if __name__ == "__main__":
    unittest.main()
