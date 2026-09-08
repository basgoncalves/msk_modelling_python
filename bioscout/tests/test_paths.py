"""bioscout.utils.paths -- relative paths in the setup files we write.

A setup XML full of absolute paths works on exactly one machine. These check
the two things that make relativising safe to do blindly: a path that has no
relative form is left ALONE, and a path with a space in it is rewritten rather
than shredded (the bug in the per-tool copy this replaced).

Standard library only.
"""
from __future__ import annotations

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from bioscout.utils.paths import (looks_absolute, path_root, relativise_value,
                                  relativise_xml, to_relative)


class TestLooksAbsolute(unittest.TestCase):
    def test_absolute_forms(self):
        for t in (r"C:\proj\x.trc", "C:/proj/x.trc", "/home/b/x.trc",
                  r"\\server\share\x.trc"):
            self.assertTrue(looks_absolute(t), t)

    def test_relative_and_junk(self):
        for t in ("x.trc", "sub/x.trc", r"sub\x.trc", "", "  ", "unassigned",
                  "66.63", "true", "a"):
            self.assertFalse(looks_absolute(t), repr(t))


class TestPathRoot(unittest.TestCase):
    def test_roots(self):
        self.assertEqual(path_root(r"C:\proj\x"), "c:")
        self.assertEqual(path_root("c:/proj/x"), "c:")
        self.assertEqual(path_root("/home/b/x"), "/")
        self.assertEqual(path_root(r"\\srv\share\x"), "//srv/share")
        self.assertEqual(path_root("sub/x"), "")

    def test_drive_letters_compare_case_insensitively(self):
        self.assertEqual(path_root(r"C:\a"), path_root(r"c:\b"))


class TestToRelative(unittest.TestCase):
    def test_posix(self):
        self.assertEqual(to_relative("/p/s1/x.trc", "/p/s1"), "x.trc")
        self.assertEqual(to_relative("/p/gen.osim", "/p/s1", sep="/"), "../gen.osim")

    def test_impossible_relpath_is_left_absolute(self):
        """Different Windows drives have no relative form. Better absolute than wrong."""
        out = to_relative(r"D:\models\gen.osim", r"C:\proj\s1")
        self.assertEqual(out, r"D:\models\gen.osim")

    def test_sep_normalises(self):
        self.assertEqual(to_relative("/p/a/b/x.trc", "/p", sep="/"), "a/b/x.trc")


class TestRelativiseValue(unittest.TestCase):
    def test_single_path_with_spaces(self):
        v, did = relativise_value("/p/Digital Athlete/gen.osim", "/p", sep="/")
        self.assertTrue(did)
        self.assertEqual(v, "Digital Athlete/gen.osim")

    def test_space_separated_list(self):
        v, did = relativise_value("/p/a.xml /p/b.xml", "/p", sep="/")
        self.assertTrue(did)
        self.assertEqual(v, "a.xml b.xml")

    def test_sentinels_and_relative_are_untouched(self):
        for t in ("unassigned", "Unassigned", "x.trc", "66.63", ""):
            v, did = relativise_value(t, "/p")
            self.assertFalse(did, t)
            self.assertEqual(v, t)

    def test_none_text_is_safe(self):
        v, did = relativise_value(None, "/p")
        self.assertFalse(did)


class TestRelativiseXml(unittest.TestCase):
    def _write(self, body):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "scale_setup.xml")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        return d, p

    def test_rewrites_paths_and_leaves_the_rest(self):
        d, p = self._write("<A/>")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<OpenSimDocument><ScaleTool>"
                     "<mass>66.63</mass>"
                     f"<model_file>{os.path.join(d, 'gen.osim')}</model_file>"
                     f"<marker_file>{os.path.join(d, 'sub', 'static.trc')}</marker_file>"
                     "<apply>true</apply>"
                     "<output_model_file>unassigned</output_model_file>"
                     "</ScaleTool></OpenSimDocument>")
        n = relativise_xml(p)
        self.assertEqual(n, 2)
        root = ET.parse(p).getroot()
        self.assertEqual(root.find(".//model_file").text, "gen.osim")
        self.assertEqual(root.find(".//marker_file").text, "sub/static.trc")
        self.assertEqual(root.find(".//mass").text, "66.63")
        self.assertEqual(root.find(".//apply").text, "true")
        self.assertEqual(root.find(".//output_model_file").text, "unassigned")

    def test_idempotent(self):
        d, p = self._write("<A><f>PLACEHOLDER</f></A>")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<A><f>{}</f></A>".format(os.path.join(d, "sub", "x.trc")))
        self.assertEqual(relativise_xml(p), 1)
        first = ET.parse(p).getroot().find("f").text
        self.assertEqual(first, "sub/x.trc")
        self.assertEqual(relativise_xml(p), 0)
        self.assertEqual(ET.parse(p).getroot().find("f").text, first)

    def test_unparseable_file_is_left_alone(self):
        d, p = self._write("this is not xml <<<")
        before = open(p, encoding="utf-8").read()
        self.assertEqual(relativise_xml(p), 0)
        self.assertEqual(open(p, encoding="utf-8").read(), before)

    def test_missing_file_is_a_no_op(self):
        self.assertEqual(relativise_xml("/nope/does/not/exist.xml"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
