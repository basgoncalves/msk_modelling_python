"""Two failures the overnight bench found (2026-09-11), both silent until a
worker process or a settings-less project hit them.

* TestNoOpensimShadow -- simulate/ceinms/shared.py put bioscout/simulate on
  sys.path, so bioscout/simulate/opensim.py was importable as a top-level
  ``opensim``. Harmless in the process that did it; fatal in every spawned
  child (they inherit sys.path): "module 'opensim' has no attribute 'Model'".
  Needs OpenSim; skips without it.
* TestSetupDir -- Iteration._resolve_setup_dir returned settings.SETUP_DIR even
  when that folder does not exist (the package default for a project without
  settings.py), so no setup template was ever found. Stdlib + bioscout only.
"""
import multiprocessing as mp
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

_PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

try:
    import opensim as _osim
    _HAS_OSIM = hasattr(_osim, "Model")
except Exception:                                   # noqa: BLE001
    _HAS_OSIM = False


def _child_opensim(q):
    """Runs in a SPAWNED process: which `opensim` does it get?"""
    try:
        import opensim
        q.put((getattr(opensim, "__file__", "?"), hasattr(opensim, "Model")))
    except Exception as e:                          # noqa: BLE001
        q.put((f"import failed: {e}", False))


@unittest.skipUnless(_HAS_OSIM, "OpenSim not installed")
class TestNoOpensimShadow(unittest.TestCase):
    def setUp(self):
        import bioscout.utils                       # noqa: F401  (inserts its paths)
        import bioscout.simulate.ceinms             # noqa: F401  (shared.py ran)

    def test_ceinms_imports_on_its_own(self):
        """`import openSim` in shared.py must not depend on sys.path (it
        failed once bioscout/simulate left sys.path)."""
        import bioscout.simulate.ceinms.shared as sh
        self.assertEqual(sh.openSim.__name__, "bioscout.simulate.opensim")

    def test_no_package_folder_with_opensim_py_on_sys_path(self):
        pkg = os.path.normcase(_PKG)
        bad = [p for p in sys.path
               if os.path.normcase(os.path.abspath(p or ".")).startswith(pkg)
               and os.path.isfile(os.path.join(p, "opensim.py"))]
        self.assertEqual(bad, [], "a bioscout folder holding opensim.py is on "
                                  "sys.path: child processes import it as `opensim`")

    def test_spawned_child_imports_real_opensim(self):
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        p = ctx.Process(target=_child_opensim, args=(q,))
        p.start()
        try:
            where, has_model = q.get(timeout=120)
        finally:
            p.join(30)
        self.assertTrue(has_model, f"child imported the wrong opensim: {where}")


class TestSetupDir(unittest.TestCase):
    def setUp(self):
        from bioscout.session.iteration import Iteration
        self.tmp = tempfile.TemporaryDirectory()
        self.proj = self.tmp.name
        proj = self.proj

        class _Stub:                      # just what _resolve_setup_dir touches
            _resolve_setup_dir = Iteration._resolve_setup_dir
            _cfg = {}

            def _project_dir(self):
                return proj
        if hasattr(Iteration, "_setup_dir_candidates"):
            _Stub._setup_dir_candidates = Iteration._setup_dir_candidates
        self.stub = _Stub()
        self.resolve = lambda stub: stub._resolve_setup_dir()

    def _why(self):
        if hasattr(self.stub, "_setup_dir_candidates"):
            return "; ".join(f"{c} (dir={os.path.isdir(c)})"
                             for c in self.stub._setup_dir_candidates())
        return f"project folder holds {sorted(os.listdir(self.proj))}"

    def tearDown(self):
        self.tmp.cleanup()

    def _settings(self, setup_dir):
        s = types.SimpleNamespace(SETUP_DIR=setup_dir, BatchSettings=None)
        import bioscout.utils as _u
        return mock.patch.object(_u, "settings", s, create=True)

    def test_missing_settings_dir_falls_back_to_project_setupFiles(self):
        os.makedirs(os.path.join(self.proj, "setupFiles"))
        with self._settings(os.path.join(self.proj, "no_such_folder")):
            got = self.resolve(self.stub)
            why = self._why()
        self.assertEqual(os.path.normcase(got),
                         os.path.normcase(os.path.join(self.proj, "setupFiles")),
                         f"candidates: {why}")

    def test_existing_settings_dir_wins(self):
        mine = os.path.join(self.proj, "my_templates")
        os.makedirs(mine)
        os.makedirs(os.path.join(self.proj, "setupFiles"))
        with self._settings(mine):
            got = self.resolve(self.stub)
        self.assertEqual(os.path.normcase(got), os.path.normcase(mine))

    def test_package_templates_are_the_last_resort(self):
        with self._settings(os.path.join(self.proj, "no_such_folder")):
            got = self.resolve(self.stub)
        self.assertEqual(os.path.normcase(got),
                         os.path.normcase(os.path.join(_PKG, "setup_files")))
        self.assertTrue(os.path.isfile(os.path.join(got, "setup_JRA.xml")))

    def test_decompose_names_a_missing_template(self):
        from bioscout.core import jcf_contributions as jc
        with self.assertRaises(FileNotFoundError) as cm:
            jc.decompose("m.osim", "ik.mot", "grf.xml", "forces.sto",
                         out_dir=os.path.join(self.proj, "out"), jra_columns={},
                         setup_template=os.path.join(self.proj, "nope", "setup_JRA.xml"))
        self.assertIn("setup template", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
