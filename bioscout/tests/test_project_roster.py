"""bioscout.tests.test_project_roster — whose subjects does a Project report?

2026-09-10: a project with no settings.py of its own (running on bioscout's
bundled template) reported the TEMPLATE's example roster -- the six
Athlete_03_<model> rows of the powerlifting study, none of which existed in
that project's simulations/ -- because the example roster filled SUBJECTS and
the simulations/ discovery only ran when SUBJECTS was empty.

A subject is a participant, and participants are the folders in simulations/.
"""
import os
import shutil
import sys
import tempfile
import unittest

try:
    import bioscout
    from bioscout.core import analysis as _analysis        # noqa: F401
    HAVE = True
except Exception:                                              # noqa: BLE001
    HAVE = False


@unittest.skipUnless(HAVE, "bioscout.core.analysis not importable")
class TestBundledProjectRoster(unittest.TestCase):
    def setUp(self):
        self.cwd, self.path = os.getcwd(), list(sys.path)
        self.env = os.environ.get("BIOSCOUT_LOG")
        os.environ["BIOSCOUT_LOG"] = "0"          # no run log for a test project
        self.dir = tempfile.mkdtemp(prefix="bs_roster_")
        sim = os.path.join(self.dir, "simulations")
        for d in ("Athlete_03/25_03_31", "H1_orthoload/s1", "K8_orthoload",
                  "_to_delete/old", ".hidden"):
            os.makedirs(os.path.join(sim, d))
        os.makedirs(os.path.join(self.dir, "models"))

    def tearDown(self):
        os.chdir(self.cwd)
        sys.path[:] = self.path
        if self.env is None:
            os.environ.pop("BIOSCOUT_LOG", None)
        else:
            os.environ["BIOSCOUT_LOG"] = self.env
        shutil.rmtree(self.dir, ignore_errors=True)

    def _project(self):
        return bioscout.Project(self.dir, verbose=False, setup_editor=False)

    def test_subjects_are_the_simulations_folders(self):
        p = self._project()
        self.assertEqual([s.name for s in p.subjects],
                         ["Athlete_03", "H1_orthoload", "K8_orthoload"])

    def test_no_value_derived_from_the_example_roster_survives(self):
        bs = self._project().settings.BatchSettings
        names = {"Athlete_03", "H1_orthoload", "K8_orthoload"}
        self.assertEqual(set(bs.SUBJECTS_BY_NAME), names)
        self.assertEqual(set(bs.MODEL_FILES), names)
        self.assertFalse(any("Cateli" in k for k in bs.model_config))
        sessions = {os.path.relpath(k, os.path.join(self.dir, "simulations"))
                    for k in bs.sessions}
        self.assertEqual(sessions, {os.path.join("Athlete_03", "25_03_31"),
                                    os.path.join("H1_orthoload", "s1")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
