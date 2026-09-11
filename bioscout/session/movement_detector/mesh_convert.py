"""
mesh_convert — turn scanned / exported surface meshes into STL.

Photogrammetry and phone-scan apps hand you an ``.obj`` (plus an ``.mtl`` and a
texture), but every mesh consumer downstream of BioScout — OpenSim body
geometry, ``tps_personalise``'s bone warping, the model report — wants
``.stl`` or ``.vtp``. This module is the small bridge.

The ``.obj`` reader is pure Python + stdlib, so it works in any environment
BioScout runs in. Other input formats (``.ply``, ``.vtp``, ``.vtk``, ``.stl``)
are delegated to ``pyvista`` if it happens to be installed.

Typical use::

    from bioscout.session.movement_detector import convert_to_stl
    out = convert_to_stl("3DModel.obj")                    # -> 3DModel.stl
    out = convert_to_stl("3DModel.obj", scale=0.001)       # mm -> m (OpenSim)

Command line::

    python -m bioscout.session.movement_detector.mesh_convert 3DModel.obj --scale 0.001

Notes
-----
* STL carries geometry only — materials, textures and vertex colours in the
  source (``.mtl`` / ``.jpg``) are dropped. That is a property of the format,
  not of this converter.
* OpenSim geometry is expressed in **metres**. Scan exports are usually
  millimetres or arbitrary units, so pass ``scale`` (or use ``--scale``) rather
  than discovering a 1000x-too-large femur inside the model.
* Faces with more than three vertices are fan-triangulated, which is correct
  for convex polygons (what mesh exporters emit) and adequate otherwise.
"""
from __future__ import annotations

import logging
import struct
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)

__all__ = ["read_obj", "write_stl", "obj_to_stl", "convert_to_stl", "convert_dir"]

Vec3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]

MESH_SUFFIXES = (".obj", ".ply", ".stl", ".vtp", ".vtk")


# --------------------------------------------------------------------------- #
# reading
# --------------------------------------------------------------------------- #
def read_obj(path: str | Path) -> Tuple[List[Vec3], List[Tri]]:
    """Read a Wavefront ``.obj`` into ``(vertices, triangles)``.

    Only ``v`` and ``f`` records matter for a surface mesh; normals (``vn``),
    texture coordinates (``vt``), groups, smoothing and material directives are
    ignored. Face indices may be 1-based (normal) or negative (relative to the
    vertices seen so far) — both are handled, as are ``v/vt/vn`` triplets.

    Parameters
    ----------
    path : str or Path
        Source ``.obj`` file.

    Returns
    -------
    (vertices, triangles)
        ``vertices`` is a list of ``(x, y, z)``; ``triangles`` a list of
        0-based index triples.
    """
    path = Path(path)
    verts: List[Vec3] = []
    tris: List[Tri] = []
    with open(path, "r", errors="ignore") as fh:
        for lineno, line in enumerate(fh, 1):
            if line.startswith("v "):
                parts = line.split()
                try:
                    verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except (IndexError, ValueError):
                    logger.warning("%s:%d: unparsable vertex, skipped", path.name, lineno)
            elif line.startswith("f "):
                idx: List[int] = []
                for tok in line.split()[1:]:
                    try:
                        i = int(tok.split("/")[0])
                    except ValueError:
                        continue
                    idx.append(i - 1 if i > 0 else len(verts) + i)
                for k in range(1, len(idx) - 1):          # fan-triangulate
                    tris.append((idx[0], idx[k], idx[k + 1]))
    if not verts:
        raise ValueError(f"no vertices found in {path} — is it really a Wavefront OBJ?")
    if not tris:
        raise ValueError(f"no faces found in {path} — point cloud, not a surface?")
    n = len(verts)
    bad = [t for t in tris if any(not 0 <= i < n for i in t)]
    if bad:
        logger.warning("%s: %d faces reference missing vertices, dropped", path.name, len(bad))
        tris = [t for t in tris if all(0 <= i < n for i in t)]
    return verts, tris


# --------------------------------------------------------------------------- #
# writing
# --------------------------------------------------------------------------- #
def _normal(a: Vec3, b: Vec3, c: Vec3) -> Vec3:
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1],
         u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0])
    mag = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    return (n[0] / mag, n[1] / mag, n[2] / mag) if mag else (0.0, 0.0, 0.0)


def write_stl(vertices: Sequence[Vec3], triangles: Iterable[Tri],
              out_path: str | Path, *, ascii_stl: bool = False,
              name: str = "bioscout") -> Path:
    """Write ``vertices``/``triangles`` to an STL file.

    Binary by default (roughly 5x smaller and faster to load in OpenSim);
    ``ascii_stl=True`` produces the text form, which is useful only for
    diffing or debugging.

    Facet normals are recomputed from the vertex winding, so a source whose
    normals disagreed with its winding comes out self-consistent.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tris = list(triangles)

    if ascii_stl:
        with open(out_path, "w") as fh:
            fh.write(f"solid {name}\n")
            for t in tris:
                a, b, c = (vertices[i] for i in t)
                nx, ny, nz = _normal(a, b, c)
                fh.write(f"  facet normal {nx:e} {ny:e} {nz:e}\n    outer loop\n")
                for p in (a, b, c):
                    fh.write(f"      vertex {p[0]:e} {p[1]:e} {p[2]:e}\n")
                fh.write("    endloop\n  endfacet\n")
            fh.write(f"endsolid {name}\n")
        return out_path

    with open(out_path, "wb") as fh:
        fh.write(name.encode("ascii", "replace")[:79].ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(tris)))
        for t in tris:
            a, b, c = (vertices[i] for i in t)
            fh.write(struct.pack("<12fH", *_normal(a, b, c), *a, *b, *c, 0))
    return out_path


# --------------------------------------------------------------------------- #
# conversion
# --------------------------------------------------------------------------- #
def obj_to_stl(obj_path: str | Path, out_path: str | Path | None = None, *,
               scale: float = 1.0, ascii_stl: bool = False) -> Path:
    """Convert a Wavefront ``.obj`` to STL.

    Parameters
    ----------
    obj_path : str or Path
        Source mesh.
    out_path : str or Path, optional
        Destination. Defaults to ``obj_path`` with an ``.stl`` suffix, written
        beside the source.
    scale : float
        Multiply every coordinate by this. Use ``0.001`` for a millimetre scan
        destined for OpenSim (metres).
    ascii_stl : bool
        Write text STL instead of binary.

    Returns
    -------
    Path
        The file written.
    """
    obj_path = Path(obj_path)
    out_path = Path(out_path) if out_path else obj_path.with_suffix(".stl")
    verts, tris = read_obj(obj_path)
    if scale != 1.0:
        verts = [(x * scale, y * scale, z * scale) for x, y, z in verts]
    write_stl(verts, tris, out_path, ascii_stl=ascii_stl, name=obj_path.stem)
    logger.info("%s -> %s (%d vertices, %d triangles)",
                obj_path.name, out_path.name, len(verts), len(tris))
    return out_path


def convert_to_stl(src: str | Path, out_path: str | Path | None = None, *,
                   scale: float = 1.0, ascii_stl: bool = False) -> Path:
    """Convert any supported surface mesh to STL, dispatching on the suffix.

    ``.obj`` uses the stdlib reader above. ``.ply`` / ``.vtp`` / ``.vtk`` /
    ``.stl`` are read with ``pyvista``, which BioScout already depends on for
    the ``tps_personalise`` bone warping; if it is not installed those formats
    raise :class:`ImportError` with the pip hint.
    """
    src = Path(src)
    if not src.exists():
        raise FileNotFoundError(src)
    suffix = src.suffix.lower()
    if suffix == ".obj":
        return obj_to_stl(src, out_path, scale=scale, ascii_stl=ascii_stl)
    if suffix not in MESH_SUFFIXES:
        raise ValueError(f"unsupported mesh format '{suffix}'; expected one of {MESH_SUFFIXES}")

    out_path = Path(out_path) if out_path else src.with_suffix(".stl")
    if out_path.resolve() == src.resolve():
        raise ValueError(f"{src} is already STL — give an explicit out_path to rewrite it")

    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover - env dependent
        raise ImportError(
            f"reading '{suffix}' needs pyvista (pip install pyvista); "
            "only .obj is supported without it"
        ) from exc

    surf = pv.read(str(src)).extract_surface().triangulate()
    if scale != 1.0:
        surf = surf.scale(scale, inplace=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    surf.save(str(out_path))
    logger.info("%s -> %s (%d points, %d cells)",
                src.name, out_path.name, surf.n_points, surf.n_cells)
    return out_path


def convert_dir(folder: str | Path, pattern: str = "*.obj", *,
                out_dir: str | Path | None = None, scale: float = 1.0,
                ascii_stl: bool = False) -> List[Path]:
    """Convert every mesh matching ``pattern`` in ``folder`` to STL.

    Failures are logged and skipped rather than aborting the batch; the return
    value lists only the files actually written.
    """
    folder = Path(folder)
    out_dir = Path(out_dir) if out_dir else folder
    written: List[Path] = []
    for src in sorted(folder.glob(pattern)):
        try:
            written.append(convert_to_stl(src, out_dir / f"{src.stem}.stl",
                                          scale=scale, ascii_stl=ascii_stl))
        except Exception as exc:
            logger.warning("skipped %s: %s", src.name, exc)
    return written


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m bioscout.session.movement_detector.mesh_convert",
        description="Convert a surface mesh (.obj, .ply, .vtp, .vtk) to STL.")
    p.add_argument("src", help="mesh file, or a folder to convert in batch")
    p.add_argument("-o", "--out", default=None,
                   help="output .stl file (or folder, when src is a folder)")
    p.add_argument("--scale", type=float, default=1.0,
                   help="multiply coordinates, e.g. 0.001 for mm -> m (OpenSim)")
    p.add_argument("--pattern", default="*.obj",
                   help="glob used when src is a folder (default: *.obj)")
    p.add_argument("--ascii", dest="ascii_stl", action="store_true",
                   help="write text STL instead of binary")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[mesh] %(message)s")
    src = Path(a.src)
    try:
        if src.is_dir():
            out = convert_dir(src, a.pattern, out_dir=a.out,
                              scale=a.scale, ascii_stl=a.ascii_stl)
            print(f"[mesh] wrote {len(out)} STL file(s) to {Path(a.out or src)}")
        else:
            print(f"[mesh] wrote {convert_to_stl(src, a.out, scale=a.scale, ascii_stl=a.ascii_stl)}")
    except Exception as exc:
        print(f"[mesh] ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
