"""Tests for :mod:`bioscout.cli` — the verb surface and its legacy translation.

The translation table is the risky part of this refactor: a wrong entry does not
crash, it silently runs the wrong command. So every verb is pinned to the exact
legacy argv it produces.

Stdlib only, no filesystem, no OpenSim — like the CLI itself.
"""
from __future__ import annotations

import argparse
import ast
import io
import contextlib
import sys
import unittest
from pathlib import Path

from bioscout import cli


class TestParser(unittest.TestCase):
    def test_root_help_is_ten_verbs(self):
        p = cli.build_parser()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            p.print_help()
        text = out.getvalue()
        for verb in cli.VERBS:
            self.assertIn(verb, text, f"{verb} missing from root help")

    def test_every_verb_has_its_own_help(self):
        """`bioscout <verb> --help` must work for all of them, and exit 0."""
        p = cli.build_parser()
        for verb in cli.VERBS:
            if verb == "help":
                continue
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
                p.parse_args([verb, "--help"])
            self.assertEqual(cm.exception.code, 0, verb)

    def test_verbs_with_actions_show_help_when_given_none(self):
        for verb in ("session", "model", "utils", "lab"):
            with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
                cli.route([verb])
            self.assertEqual(cm.exception.code, 0, verb)

    def test_help_verb(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.route(["help"]), ("exit", 0))
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            cli.route(["help", "session"])

    def test_unknown_verb_is_rejected(self):
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stderr(io.StringIO()):
            cli.route(["frobnicate"])
        self.assertNotEqual(cm.exception.code, 0)

    def test_simulate_shows_help_when_given_no_action(self):
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(io.StringIO()):
            cli.route(["simulate"])
        self.assertEqual(cm.exception.code, 0)

    def test_simulate_actions_parse(self):
        """simulate is direct-dispatched (Session() -> Iteration.run), not
        translated to a legacy flag -- there is no flat-flag equivalent of a
        single stage. Pin the argparse shape instead of the (nonexistent)
        legacy argv."""
        p = cli.build_parser()
        for action in ("exbiomec", "ma", "so", "mew", "ceinms"):
            ns = p.parse_args(["simulate", action, "some/session",
                               "--iteration", "gpk", "--trial", "Walk01,Walk02",
                               "--replace"])
            self.assertEqual(ns.verb, "simulate")
            self.assertEqual(ns.action, action)
            self.assertEqual(ns.path, "some/session")
            self.assertEqual(ns.iteration, "gpk")
            self.assertEqual(ns.trial, "Walk01,Walk02")
            self.assertTrue(ns.replace)

    def test_simulate_defaults(self):
        p = cli.build_parser()
        ns = p.parse_args(["simulate", "so", "some/session"])
        self.assertIsNone(ns.iteration)
        self.assertIsNone(ns.trial)
        self.assertFalse(ns.replace)

    def test_simulate_needs_a_session_path(self):
        p = cli.build_parser()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.parse_args(["simulate", "ma"])


class TestRestructureStages1to4(unittest.TestCase):
    """The verb tree after stages 1-4 of docs/RESTRUCTURE_PLAN.md."""

    def test_project_and_mrs_are_not_top_level(self):
        for gone in ("project", "mrs", "run", "scale"):
            self.assertNotIn(gone, cli.VERBS, gone)

    def test_init_from_settings_parses(self):
        ns = cli.build_parser().parse_args(["init", "proj", "--from-settings", "--force"])
        self.assertEqual((ns.verb, ns.path, ns.from_settings, ns.force),
                         ("init", "proj", True, True))
        ns = cli.build_parser().parse_args(["init"])
        self.assertFalse(ns.from_settings)

    def test_model_tune_ma_replaces_ma(self):
        p = cli.build_parser()
        p.parse_args(["model", "tune-ma"])
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                p.parse_args(["model", "ma"])

    def test_simulate_mrs_is_listed_and_intercepted(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                cli.build_parser().parse_args(["simulate", "--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("mrs", out.getvalue())
        # route() hands `simulate mrs ...` to bioscout.simulate.mrs.cli before
        # argparse ever sees the tail.
        import sys, types
        fake = types.ModuleType("bioscout.simulate.mrs.cli")
        seen = []
        fake.main = lambda argv: seen.append(list(argv)) or 7
        saved = {k: sys.modules.get(k) for k in ("bioscout.simulate", "bioscout.simulate.mrs",
                                                  "bioscout.simulate.mrs.cli")}
        sys.modules["bioscout.simulate.mrs.cli"] = fake
        try:
            kind, code = cli.route(["simulate", "mrs", "check", "--x"])
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        self.assertEqual((kind, code), ("exit", 7))
        self.assertEqual(seen, [["check", "--x"]])


    def test_verb_order_puts_simulate_before_session(self):
        """`session` reads what `simulate` writes, so it is listed after it."""
        order = [v for v in cli.VERBS if v in ("model", "simulate", "session")]
        self.assertEqual(order, ["model", "simulate", "session"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit):
                cli.build_parser().parse_args(["--help"])
        text = out.getvalue()
        self.assertLess(text.index("simulate "), text.index("session "))

    def test_tps_is_nested_under_model(self):
        self.assertNotIn("tps", cli.VERBS)
        cli.build_parser().parse_args(["model", "tps"])
        self.assertIn("bioscout model tps", cli.legacy_hint(["--tps"]))

class TestTranslation(unittest.TestCase):
    """Each verb -> the exact legacy argv. Pinned, because a wrong entry is silent."""

    def legacy(self, argv):
        kind, value = cli.route(argv)
        self.assertEqual(kind, "legacy", f"{argv} did not translate")
        return value

    def test_init_and_gui(self):
        self.assertEqual(self.legacy(["init", "myproj"]), ["--init", "myproj"])
        self.assertEqual(self.legacy(["init"]), ["--init", "."])

    def test_session_new(self):
        """--no-gui, so the test never tries to open a window.

        Without it this verb goes to the dialog on a machine with a display and
        to the flag path on one without, which is a test that depends on where
        it runs.
        """
        self.assertEqual(self.legacy(["session", "new", "s/021/pre", "--no-gui"]),
                         ["--new-session", "s/021/pre"])
        self.assertEqual(
            self.legacy(["session", "new", "s/022/pre", "--no-gui", "--from",
                         "s/021/pre", "--body-mass", "61.3"]),
            ["--new-session", "s/022/pre", "--from-session", "s/021/pre",
             "--body-mass", "61.3"])

    def test_gui_points_to_bioscout_web(self):
        """The desktop GUI is gone: `bioscout gui` prints where the interface is."""
        import io, contextlib
        import bioscout.cli as _c
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            kind, value = _c.route(["gui"])
        self.assertIn("bioscout-web", buf.getvalue())
        self.assertEqual(value, 0)

    def test_session(self):
        self.assertEqual(self.legacy(["session", "export", "s/021/pre"]),
                         ["--c3d-export", "s/021/pre"])
        self.assertEqual(
            self.legacy(["session", "classify", "s/021/pre", "--no-plots", "--write-yaml"]),
            ["--classifier", "s/021/pre", "--no-plots", "--write-session-yaml"])
        self.assertEqual(
            self.legacy(["session", "ingest", "raw/", "--subject", "022", "--session", "pre"]),
            ["--ingest-c3d", "raw/", "--subject", "022", "--session", "pre"])
        self.assertEqual(
            self.legacy(["session", "reset", "--subject", "021", "--dry-run", "--raw"]),
            ["--reset", "--subject", "021", "--reset-dry-run", "--reset-raw"])

    def test_model_edit_ma_compare_jc(self):
        self.assertEqual(self.legacy(["model", "edit"]), ["--model-edit"])
        self.assertEqual(self.legacy(["model", "edit", "proj"]), ["--model-edit", "proj"])
        self.assertEqual(self.legacy(["model", "tune-ma", "proj"]), ["--change-moment-arms", "proj"])
        self.assertEqual(self.legacy(["model", "compare", "a.osim", "b.osim"]),
                         ["--compare-models", "a.osim", "b.osim"])
        self.assertEqual(
            self.legacy(["model", "compare", "models/", "-o", "t.xlsx", "--figures"]),
            ["--compare-models", "models/", "-o", "t.xlsx", "--figures"])
        self.assertEqual(
            self.legacy(["model", "compare", "models/", "--figures", "figs/"]),
            ["--compare-models", "models/", "--figures", "figs/"])
        self.assertEqual(self.legacy(["model", "joint-centres", "static.trc"]),
                         ["--joint-centres", "static.trc"])
        self.assertEqual(self.legacy(["model", "jc", "static.trc", "-o", "out.trc"]),
                         ["--joint-centres", "static.trc", "-o", "out.trc"])

    def test_tps_and_plot(self):
        self.assertEqual(self.legacy(["model", "tps"]), ["--tps"])
        self.assertEqual(self.legacy(["model", "tps", "proj"]), ["--tps", "proj"])
        self.assertEqual(self.legacy(["plot", "summary", "proj"]), ["--summary", "proj"])
        self.assertEqual(
            self.legacy(["plot", "summary", "--subject", "021", "--overall"]),
            ["--summary", "-overall", "-s", "021"])
        self.assertEqual(
            self.legacy(["plot", "collings", "sess/", "--top", "12", "--side", "_l"]),
            ["--collings", "sess/", "--side", "_l", "--top", "12"])

    def test_utils(self):
        self.assertEqual(self.legacy(["utils", "install"]), ["--install"])
        self.assertEqual(self.legacy(["utils", "pylance"]), ["--pylance-fix"])
        self.assertEqual(
            self.legacy(["utils", "md2pdf", "a.md", "b.md", "--toc", "--outdir", "pdf/"]),
            ["--md2pdf", "a.md", "b.md", "--outdir", "pdf/", "--toc"])

    def test_lab(self):
        got = self.legacy(["lab", "shots", "clip.mp4", "--shooting-hand", "left"])
        self.assertEqual(got[:2], ["--shots", "clip.mp4"])
        self.assertIn("--shooting-hand", got)
        self.assertEqual(got[got.index("--shooting-hand") + 1], "left")
        got = self.legacy(["lab", "load-report", "exports/", "--age", "34", "--zepp-pull"])
        self.assertEqual(got[:2], ["--load-report", "exports/"])
        self.assertIn("--zepp-pull", got)
        self.assertEqual(self.legacy(["lab", "add-subject"]), ["--add_subject"])

    def test_optional_flags_are_omitted_when_unset(self):
        """An unset option must not reach the legacy argv as an empty string."""
        for argv in (["model", "compare", "a.osim"],
                     ["plot", "collings"], ["utils", "md2pdf", "a.md"]):
            for token in self.legacy(argv):
                self.assertNotEqual(token, "", argv)
                self.assertNotEqual(token, "None", argv)


class TestLegacyHint(unittest.TestCase):
    def test_names_the_replacement(self):
        self.assertIn("bioscout model edit", cli.legacy_hint(["--model-edit"]))
        self.assertIn("bioscout utils env", cli.legacy_hint(["--env"]))
        self.assertIn("bioscout plot collings", cli.legacy_hint(["--collings", "s/"]))

    def test_silent_for_unmapped_and_new_style(self):
        self.assertIsNone(cli.legacy_hint(["--REPLACE"]))
        self.assertIsNone(cli.legacy_hint(["simulate", "so", "some/session"]))
        self.assertIsNone(cli.legacy_hint([]))

    def test_handles_equals_form(self):
        self.assertIn("bioscout init", cli.legacy_hint(["--init=proj"]))

    def test_every_mapped_flag_names_a_real_verb(self):
        for flag, new in cli._LEGACY.items():
            verb = new.split()[1]
            self.assertIn(verb, cli.VERBS, f"{flag} -> {new}: '{verb}' is not a verb")


class TestStaysLight(unittest.TestCase):
    """`bioscout -h` must not need the scientific stack.

    Checked structurally rather than by import side effects, because by the time
    this test runs numpy is loaded anyway — the question is whether *this module*
    pulls it in at import time.
    """

    STDLIB_OK = {"argparse", "sys", "os", "typing", "__future__", "runpy",
                 "pathlib", "re", "json", "textwrap", "shutil"}

    def test_module_level_imports_are_stdlib(self):
        src = Path(cli.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        offenders = []
        for node in tree.body:                      # module level only
            if isinstance(node, ast.Import):
                offenders += [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                offenders.append(node.module.split(".")[0])
        bad = [m for m in offenders if m not in self.STDLIB_OK]
        self.assertEqual(bad, [], f"bioscout.cli imports {bad} at module level")

    def test_bioscout_is_not_imported_at_module_level(self):
        src = Path(cli.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in tree.body:
            mod = getattr(node, "module", None) or ""
            names = [a.name for a in getattr(node, "names", [])]
            self.assertNotIn("bioscout", mod.split("."),
                             "bioscout.cli must import bioscout lazily")
            for n in names:
                self.assertFalse(n.startswith("bioscout"),
                                 "bioscout.cli must import bioscout lazily")


if __name__ == "__main__":
    unittest.main(verbosity=2)
