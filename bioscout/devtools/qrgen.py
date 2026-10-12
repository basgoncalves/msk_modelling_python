"""Make a QR code for a link — ``bioscout utils qr_code``.

Interactive by default: asks for the link, then where to save. Uses ``segno``
(pure Python, no Pillow needed for PNG/SVG); installs it with pip on first use.
Each output is verified by checking the file was written and is non-empty.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional


def _segno():
    try:
        import segno
    except ImportError:
        print("segno not installed - installing it (pip install segno) ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "segno"])
        import segno
    return segno


def _ask(prompt: str) -> str:
    v = input(prompt).strip().strip('"').strip("'")
    return v


def make_qr(link: Optional[str] = None, out: Optional[str] = None,
            scale: int = 10, border: int = 4) -> int:
    segno = _segno()
    while not link:
        link = _ask("Paste the link to encode: ")
    qr = segno.make(link, error="m", micro=False)
    print(f"QR ready (version {qr.version}, {qr.designator}) for: {link}")
    if not out:
        out = _ask("Paste the path to save (file .png/.svg/.pdf, or a folder) "
                   "[qr_code.png]: ") or "qr_code.png"
    out = os.path.expanduser(out)
    if os.path.isdir(out) or out.endswith(("/", "\\")):
        os.makedirs(out, exist_ok=True)
        out = os.path.join(out, "qr_code.png")
    if not os.path.splitext(out)[1]:
        out += ".png"
    d = os.path.dirname(os.path.abspath(out))
    os.makedirs(d, exist_ok=True)
    if os.path.exists(out):
        if _ask(f"{out} exists - overwrite? [y/N]: ").lower() != "y":
            print("Not saved.")
            return 1
    qr.save(out, scale=scale, border=border)
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        print(f"Failed to write {out}")
        return 1
    print(f"Saved: {os.path.abspath(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(make_qr(*(sys.argv[1:3])))
