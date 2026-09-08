"""Path helpers for the setup files bioscout writes.

OpenSim resolves a relative path in a setup XML against the setup file's own
directory, so a setup that names its inputs relatively is portable: move the
session folder, put it on a colleague's machine, open it in the OpenSim GUI --
it still resolves. A setup full of ``C:\\Users\\<you>\\...`` only ever works on
one machine, and silently stops working when the project moves.

Every tool that writes a setup should therefore run :func:`relativise_xml` over
it before handing it back. Two rules make that safe to do blindly:

* a path that CANNOT be made relative (a different drive on Windows, a UNC
  share) is left absolute rather than mangled -- ``os.path.relpath`` raises
  ``ValueError`` across drives, and a wrong relative path is worse than an
  honest absolute one;
* only values that actually look like absolute paths are touched, so numbers,
  names and flags in the same file are never rewritten.

    from bioscout.utils.paths import relativise_xml, to_relative

    relativise_xml("scale_setup.xml")            # in place, against its own dir
    to_relative("C:/proj/s1/x.trc", "C:/proj")   # -> "s1/x.trc"

Standard library only.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as _ET

__all__ = ["looks_absolute", "path_root", "to_relative", "relativise_xml",
           "relativise_value"]

#: Values OpenSim uses for "no file". Never rewritten.
_SENTINELS = {"", "unassigned", "Unassigned", "none", "None"}


def looks_absolute(text):
    """True when ``text`` looks like an absolute path.

    Drive-letter (``C:\\x``, ``C:/x``), UNC (``\\\\server\\share``) or
    POSIX-absolute (``/x``). Deliberately textual: the path need not exist, and
    a Windows path is recognised while running on Linux (that is the normal
    case when inspecting someone else's setup file).
    """
    t = (text or "").strip()
    if len(t) < 2:
        return False
    return t[1:3] in (":\\", ":/") or t.startswith("/") or t.startswith("\\\\")


def path_root(text):
    """The root ``text`` hangs off: ``"c:"``, ``"//server/share"``, ``"/"``, or "".

    Used to decide whether two paths CAN be relative to each other. Textual on
    purpose: ``os.path.relpath`` only raises across drives when it is running
    on Windows -- on Linux it happily returns ``../D:\\models\\x.osim`` for two
    different Windows drives, which is nonsense that would then be written
    into a setup file.
    """
    t = (text or "").strip().replace("\\", "/")
    if len(t) >= 2 and t[1:2] == ":":
        return t[:2].lower()
    if t.startswith("//"):
        parts = [p for p in t.split("/") if p]
        return "//" + "/".join(parts[:2]) if len(parts) >= 2 else "//"
    if t.startswith("/"):
        return "/"
    return ""


def to_relative(path, base, sep=None):
    """``path`` relative to ``base``, or ``path`` unchanged if that is impossible.

    Args:
        path: the path to rewrite.
        base: the directory to make it relative to (a setup file's folder).
        sep: separator for the result. ``None`` keeps whatever ``os.path``
            produces; pass ``"/"`` for forward slashes (OpenSim accepts them on
            every platform) or ``"\\\\"`` for Windows-style.

    A different drive or a UNC share has no relative form, so the absolute path
    is returned as-is -- correct, if not portable.
    """
    if path is None or base is None:
        return path
    if path_root(path) != path_root(base):
        return path                             # no relative form exists
    try:
        rel = os.path.relpath(str(path).replace("\\", "/"),
                              str(base).replace("\\", "/"))
    except (ValueError, TypeError):
        return path
    if sep:
        rel = rel.replace("\\", "/").replace("/", sep) if sep != "/" \
            else rel.replace("\\", "/")
    return rel


def relativise_value(text, base, sep=None):
    """Relativise one XML value: a single path, or a space-separated list.

    Returns ``(new_text, changed)``. A single path that CONTAINS spaces is
    handled before the list case, so ``C:\\Digital Athlete\\x.osim`` is
    rewritten rather than shredded into fragments -- the bug that made the
    older per-tool copy of this silently skip any path with a space in it.
    """
    t = (text or "").strip()
    if not t or t in _SENTINELS:
        return text, False
    # A LIST of paths first: every part absolute means it cannot be one path
    # with spaces in it. A single path containing spaces fails that test (its
    # tail is not absolute) and falls through to the single-path branch below.
    parts = t.split()
    if len(parts) > 1 and all(looks_absolute(p) for p in parts):
        new = " ".join(to_relative(p, base, sep) for p in parts)
        return (new, True) if new != t else (text, False)
    if looks_absolute(t):                       # whole value is ONE path
        rel = to_relative(t, base, sep)
        return (rel, True) if rel != t else (text, False)
    return text, False


def relativise_xml(xml_path, base=None, sep="/"):
    """Rewrite absolute paths in an OpenSim/CEINMS setup XML to relative ones.

    In place, best-effort: a file that will not parse is left alone rather than
    truncated. Returns the number of values rewritten (0 when nothing needed
    it, or on failure), so a caller can report honestly.

    ``base`` defaults to the XML's own directory, which is what OpenSim
    resolves against.
    """
    try:
        xml_path = os.path.abspath(xml_path)
        base = base or os.path.dirname(xml_path)
        tree = _ET.parse(xml_path)
        root = tree.getroot()
    except Exception:                           # noqa: BLE001 - best effort
        return 0
    changed = 0
    for el in root.iter():
        new, did = relativise_value(el.text, base, sep)
        if did:
            el.text = new
            changed += 1
    if changed:
        try:
            tree.write(xml_path)
        except Exception:                       # noqa: BLE001 - best effort
            return 0
    return changed
