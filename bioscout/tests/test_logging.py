"""bioscout.tests.test_logging — the stdout tee, and the ways it ate output.

The first two bugs here were found in a Jupyter notebook (2026-08-18): a cell
ran `bs.Project(...)`, the next cell called `print()`, the cell reported
success in 0.0s and displayed NOTHING. Neither failure raises, so only a test
keeps them fixed.

The third (2026-09-10, ipykernel 7.3) had the same symptom with both of those
fixed: the tee hid ipykernel's ``set_parent``, so output stayed addressed to
the cell that started logging. The fix for the CLASS of bug is the library
convention -- imported as a library, bioscout does not replace sys.stdout at
all; only its own CLI/GUI, or an explicit opt-in, captures print() output.

Pure stdlib — no OpenSim, no scipy, no ipykernel.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest

try:
    from bioscout.utils import shared
    HAVE = True
except Exception:                                              # noqa: BLE001
    HAVE = False


class _Reset:
    """start_logging is idempotent per PROCESS, so each test has to put the
    module's globals back or only the first one would do anything."""

    def __enter__(self):
        self.out, self.err = sys.stdout, sys.stderr
        self.state = (shared._LOG_STARTED, shared._LOG_HANDLE,
                      shared._LOG_FINISHED, shared._OSIM_SINK,
                      shared._SAVED_STREAMS)
        shared._LOG_STARTED = False
        shared._LOG_HANDLE = None
        shared._LOG_FINISHED = False
        shared._SAVED_STREAMS = None
        self.env = os.environ.pop("BIOSCOUT_LOG_FILTER", None)
        self.dir = tempfile.mkdtemp(prefix="bs_log_")
        return self

    def __exit__(self, *exc):
        h = shared._LOG_HANDLE
        sys.stdout, sys.stderr = self.out, self.err
        (shared._LOG_STARTED, shared._LOG_HANDLE, shared._LOG_FINISHED,
         shared._OSIM_SINK, shared._SAVED_STREAMS) = self.state
        if self.env is None:
            os.environ.pop("BIOSCOUT_LOG_FILTER", None)
        else:
            os.environ["BIOSCOUT_LOG_FILTER"] = self.env
        try:
            if h:
                h.close()
        except Exception:
            pass
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


@unittest.skipUnless(HAVE, "bioscout.utils.shared not importable")
class TestTee(unittest.TestCase):
    def test_raw_passes_everything_through(self):
        buf = io.StringIO()
        t = shared._Tee(buf, raw=True)
        t.write("nothing here is on any whitelist\n")
        self.assertIn("nothing here is on any whitelist", buf.getvalue())

    def test_filtered_drops_unwhitelisted_under_minimal(self):
        # the behaviour `raw` exists to switch off — pinned so the fix cannot be
        # "solved" by deleting the filter
        buf = io.StringIO()
        t = shared._Tee(buf, raw=False)
        real = shared._log_verbosity
        shared._log_verbosity = lambda: "minimal"
        try:
            t.write("some ordinary sentence a user printed\n")
        finally:
            shared._log_verbosity = real
        self.assertEqual(buf.getvalue(), "")

    def test_stream_probes_do_not_raise(self):
        t = shared._Tee(io.StringIO())
        self.assertIsInstance(t.isatty(), bool)
        self.assertTrue(isinstance(t.encoding, str))
        t.flush()

    def test_unknown_attributes_reach_the_real_stream(self):
        """THE 2026-09-10 bug. ipykernel re-targets output at each new cell
        with ``if hasattr(sys.stdout, "set_parent"): sys.stdout.set_parent(p)``.
        A tee that hid the method left every later print() addressed to the
        cell that started logging, where the frontend dropped it."""
        class _OutStream(io.StringIO):
            parent = None

            def set_parent(self, parent):
                self.parent = parent
        cell = _OutStream()
        t = shared._Tee(cell, io.StringIO(), raw=True)
        self.assertTrue(hasattr(t, "set_parent"))
        t.set_parent({"msg_id": "cell-2"})
        self.assertEqual(cell.parent, {"msg_id": "cell-2"})
        self.assertFalse(hasattr(t, "no_such_attribute"))


@unittest.skipUnless(HAVE, "bioscout.utils.shared not importable")
class TestStartLogging(unittest.TestCase):
    """Library use leaves sys.stdout alone; the CLI and explicit opt-ins tee."""

    def setUp(self):
        self._v = shared._log_verbosity
        self._nb = shared.in_notebook
        shared._log_verbosity = lambda: "minimal"   # the filter that eats prints

    def tearDown(self):
        shared._log_verbosity = self._v
        shared.in_notebook = self._nb

    def test_library_use_leaves_stdout_alone(self):
        """bs.Project()/Session in a notebook or script must not replace
        sys.stdout -- the Python library convention, and the fix for the whole
        family of 'my print() vanished' bugs above."""
        with _Reset() as r:
            cell = io.StringIO()
            sys.stdout = cell
            shared.in_notebook = lambda: False
            shared.ensure_logging("test", log_dir=r.dir)
            self.assertIs(sys.stdout, cell)
            print("run ok: False")
            self.assertIn("run ok: False", cell.getvalue())

    def test_notebook_never_captured_even_with_cli_flag(self):
        """BIOSCOUT_LOG_FILTER can leak into a kernel's environment (a kernel
        started from a shell that ran the CLI). A notebook is never the CLI."""
        with _Reset() as r:
            cell = io.StringIO()
            sys.stdout = cell
            shared.in_notebook = lambda: True
            os.environ["BIOSCOUT_LOG_FILTER"] = "1"
            shared.start_logging("test", log_dir=r.dir)
            self.assertIs(sys.stdout, cell)

    def test_cli_run_captures_and_filters(self):
        """Batch behaviour is unchanged: under bioscout's own CLI (which sets
        BIOSCOUT_LOG_FILTER=1 in __main__) print output is teed into the log
        and the console stays terse."""
        with _Reset() as r:
            console = io.StringIO()
            sys.stdout = console
            shared.in_notebook = lambda: False
            os.environ["BIOSCOUT_LOG_FILTER"] = "1"
            f = shared.start_logging("test", log_dir=r.dir)
            self.assertIsInstance(sys.stdout, shared._Tee)
            before = console.getvalue()
            print("an ordinary line nobody whitelisted")
            print("[ERROR] a line the whitelist keeps")
            f.flush()
            self.assertNotIn("nobody whitelisted", console.getvalue()[len(before):])
            with open(f.name, encoding="utf-8") as fh:
                self.assertIn("[ERROR] a line the whitelist keeps", fh.read())

    def test_explicit_capture_is_raw_and_reversible(self):
        """capture=True in library use: prints reach the cell AND the log,
        unfiltered, and stop_logging() hands the original stream back."""
        with _Reset() as r:
            cell = io.StringIO()
            sys.stdout = cell
            shared.in_notebook = lambda: True
            f = shared.start_logging("test", log_dir=r.dir, capture=True)
            print("2.0.0c1 C:/Git/bioscout/bioscout/__init__.py")
            self.assertIn("2.0.0c1", cell.getvalue())
            path = f.name
            shared.stop_logging()
            self.assertIs(sys.stdout, cell)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("2.0.0c1", text)
            self.assertIn("completed", text)            # banner written on stop

    def test_capture_output_block(self):
        with _Reset() as r:
            cell = io.StringIO()
            sys.stdout = cell
            shared.in_notebook = lambda: True
            with shared.capture_output("block", log_dir=r.dir) as f:
                print("inside the block")
            self.assertIs(sys.stdout, cell)              # restored on exit
            print("after the block")
            f.flush()
            with open(f.name, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("inside the block", text)
            self.assertNotIn("after the block", text)
            self.assertIn("inside the block", cell.getvalue())
            self.assertIn("after the block", cell.getvalue())

    def test_capture_output_restores_on_error(self):
        with _Reset() as r:
            cell = io.StringIO()
            sys.stdout = cell
            shared.in_notebook = lambda: True
            with self.assertRaises(ValueError):
                with shared.capture_output("block", log_dir=r.dir):
                    raise ValueError("boom")
            self.assertIs(sys.stdout, cell)

    def test_writes_a_log_file(self):
        with _Reset() as r:
            sys.stdout = io.StringIO()
            shared.start_logging("test", log_dir=r.dir)
            logs = [f for f in os.listdir(r.dir) if f.endswith(".log")]
            self.assertEqual(len(logs), 1)
            self.assertTrue(logs[0].startswith("bioscout_"))

    def test_same_second_runs_do_not_overwrite(self):
        with _Reset() as r:
            sys.stdout = io.StringIO()
            shared.start_logging("first", log_dir=r.dir, filename="bioscout_x.log")
            shared.start_logging("second", log_dir=r.dir, filename="bioscout_x.log")
            logs = sorted(os.listdir(r.dir))
            self.assertEqual(logs, ["bioscout_x.log", "bioscout_x_2.log"])
            with open(os.path.join(r.dir, "bioscout_x.log"), encoding="utf-8") as fh:
                self.assertIn("first", fh.read())

    def test_disabled_by_env(self):
        with _Reset() as r:
            sys.stdout = cell = io.StringIO()
            old = os.environ.get("BIOSCOUT_LOG")
            os.environ["BIOSCOUT_LOG"] = "0"
            try:
                self.assertIsNone(shared.start_logging("test", log_dir=r.dir))
                self.assertIs(sys.stdout, cell)      # stdout left alone entirely
            finally:
                if old is None:
                    os.environ.pop("BIOSCOUT_LOG", None)
                else:
                    os.environ["BIOSCOUT_LOG"] = old


@unittest.skipUnless(HAVE, "bioscout.utils.shared not importable")
class TestReachableFromThePackage(unittest.TestCase):
    """`bs.utils.capture_output` must work straight after `import bioscout as
    bs` -- before anything else has imported bioscout.utils (2026-09-10)."""

    def test_utils_is_a_lazy_submodule(self):
        import bioscout
        self.assertIn("utils", bioscout._SUBMODULES)
        self.assertIs(bioscout.__getattr__("utils"), sys.modules["bioscout.utils"])

    def test_logging_helpers_at_top_level(self):
        import bioscout
        for name in ("start_logging", "capture_output", "stop_logging"):
            self.assertIs(getattr(bioscout, name), getattr(shared, name))


class TestImportLeavesStreamsAlone(unittest.TestCase):
    """Importing utils/logger.py used to tee sys.stdout/stderr on the spot."""

    def test_importing_logger_module(self):
        import importlib.util
        mod = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "utils", "logger.py")
        out, err = sys.stdout, sys.stderr
        spec = importlib.util.spec_from_file_location("_bs_logger_probe", mod)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
        finally:
            got_out, got_err = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = out, err
        self.assertIs(got_out, out)
        self.assertIs(got_err, err)
        # ...and the app entry point can still opt in, and undo it
        m.logger.capture_std_streams()
        try:
            self.assertIsInstance(sys.stdout, m._TeeStream)
        finally:
            m.logger.release_std_streams()
            if sys.stdout is not out:
                sys.stdout, sys.stderr = out, err
            for h in list(m.logger.logger.handlers):
                m.logger.logger.removeHandler(h)
                h.close()
        self.assertIs(sys.stdout, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
