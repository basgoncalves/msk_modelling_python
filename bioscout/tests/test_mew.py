"""bioscout.simulate.mew (muscle extrapolation web) -- the Python CEINMS/SO solver.

Three layers, cheapest first:

* TestSynthetic -- the package's own selftest (6 muscles, known activations)
  and its end-to-end run through files on disk. numpy/scipy only.
* TestIterationAdapter -- the seam to ``bioscout.session``. Pins the three
  places the adapter drifted from the current Iteration API when the package
  moved in from FAIS_machine_learning (2026-09-10): the model comes from
  ``Iteration.model_file()``, ``subject_name`` is a property, and
  ``Iteration.trials`` yields Analyse objects rather than names. Fake
  iterations, so no session folder, no logging side effects.
* TestPipelineWiring -- `do_mew` is a real Iteration.run stage (verified on
  disk by run_check), and an unknown stage flag is reported, not swallowed.
* TestOrtholoadWalking -- a real trial: OrthoLoad H1L level walking with the
  scaled GPK model, from ``example_data/orthoload`` beside the package.
  ``example_data/`` is gitignored, so this skips on a checkout without it.
"""
import os
import unittest

import numpy as np

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
_ORTHO = os.path.join(_REPO, "example_data", "orthoload")
_TRIAL = os.path.join(_ORTHO, "simulations", "H1_orthoload", "11_05_06",
                      "3_iterations", "gpk", "Walking_01")
_MODEL = os.path.join(_ORTHO, "models", "personalised", "H1_orthoload", "11_05_06",
                      "gpk_scaled.osim")


class TestSynthetic(unittest.TestCase):
    def test_selftest(self):
        from bioscout.simulate.mew.tests.synthetic import selftest
        self.assertEqual(selftest(verbose=False), 0)

    def test_end_to_end(self):
        from bioscout.simulate.mew.tests.test_end_to_end import test_end_to_end
        self.assertEqual(test_end_to_end(verbose=False), 0)

    def test_import_is_light(self):
        # importing the package must not drag in OpenSim or torch
        import subprocess
        import sys
        code = ("import sys, bioscout.simulate.mew; "
                "bad = [m for m in ('opensim', 'torch') if m in sys.modules]; "
                "sys.exit(1 if bad else 0)")
        r = subprocess.run([sys.executable, "-c", code], cwd=_REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class _FakeIteration:
    """The slice of bioscout.session.Iteration the adapter touches."""

    def __init__(self, path, model):
        self.path = path
        self._model = model

    subject_name = "H1_orthoload"            # a property on the real class

    def _trial_names(self):
        return ["Walking_01"]

    @property
    def trials(self):                        # Analyse objects, not names
        return [object()]

    def trial_config(self, name, force_type="SO"):
        return {"so_model": self._model, "body_mass": 77.5, "side": "both"}

    def model_file(self, force_type="SO", trial=None):
        return self._model

    def resolve_model_file(self, mfile):
        return None


class TestIterationAdapter(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="ma_adapter_")
        self.osim = os.path.join(self.tmp, "scaled.osim")
        with open(self.osim, "w") as fh:
            fh.write("<OpenSimDocument/>")
        self.it = _FakeIteration(self.tmp, self.osim)

    def test_model_from_model_file(self):
        from bioscout.simulate.mew.bioscout_adapter import _resolve_model
        cfg = self.it.trial_config("Walking_01")
        self.assertEqual(_resolve_model(self.it, cfg), self.osim)

    def test_subject_name_property_or_method(self):
        from bioscout.simulate.mew.bioscout_adapter import _subject_name
        self.assertEqual(_subject_name(self.it), "H1_orthoload")

        class Old:
            def subject_name(self):
                return "legacy"
        self.assertEqual(_subject_name(Old()), "legacy")

    def test_trial_names_not_analyse_objects(self):
        from bioscout.simulate.mew.bioscout_adapter import _trial_names
        self.assertEqual(_trial_names(self.it), ["Walking_01"])


class TestPipelineWiring(unittest.TestCase):
    def test_stage_output_registered(self):
        from bioscout.devtools.run_check import STAGE_OUTPUTS
        self.assertIn("mew", STAGE_OUTPUTS)

    def test_reachable_from_the_package(self):
        import bioscout as bs
        self.assertTrue(callable(bs.mew.read_storage))
        self.assertTrue(callable(bs.mew.contact_force_magnitude))
        self.assertFalse(hasattr(bs.mew, "MuscleAnalyser"))

    def test_run_signature(self):
        import inspect
        from bioscout.session import Iteration
        params = inspect.signature(Iteration.run).parameters
        self.assertIn("do_mew", params)
        self.assertIn("mew_opts", params)

    @unittest.skipUnless(os.path.isdir(_TRIAL), "example_data/orthoload not present (gitignored)")
    def test_unknown_stage_flag_is_reported(self):
        from bioscout.session import Session
        cwd = os.getcwd()
        try:
            it = Session(os.path.dirname(os.path.dirname(os.path.dirname(_TRIAL))),
                         project_dir=_ORTHO).iteration("gpk")
            lines = []
            it.run(trials=["__no_such_trial__"], do_muscle_analyser=True, log=lines.append)
        finally:
            os.chdir(cwd)
        self.assertTrue(any("do_muscle_analyser" in ln and "IGNORED" in ln for ln in lines), lines)


@unittest.skipUnless(os.path.isdir(_TRIAL) and os.path.isfile(_MODEL),
                     "example_data/orthoload not present (gitignored)")
class TestOrtholoadWalking(unittest.TestCase):
    """Tier 1 (no EMG) on a real 100-muscle model. ~20 s."""

    @classmethod
    def setUpClass(cls):
        from bioscout.simulate.mew.bioscout_adapter import (
            analyser_from_trial_dir, discover_trial)
        cls.found = discover_trial(_TRIAL)
        cls.res = analyser_from_trial_dir(_TRIAL, _MODEL).run()

    def test_inputs_discovered(self):
        for key in ("kinematics", "moments", "grf", "grf_xml", "moment_arms", "so_forces"):
            self.assertTrue(self.found[key], f"{key} not found")
        self.assertIsNone(self.found["emg"])

    def test_solution(self):
        from bioscout.simulate.mew import Tier
        r = self.res
        self.assertEqual(r.tier, Tier.STATIC_OPT)
        self.assertEqual(len(r.muscles), 100)
        self.assertTrue(np.isfinite(r.forces).all())
        self.assertGreaterEqual(r.forces.min(), -1e-6)
        # session.yaml's body mass reached the solve
        self.assertIn("m=77.498", r.provenance.parameter_source)
        # the muscles, not reserves, carry the inverse-dynamics moments
        self.assertLess(float(np.mean(np.abs(r.moment_residual))), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
