"""File input/output shared across ``bioscout.model``: meshes, models, landmarks.

One place to load things, so ``measure``, ``geometry``, ``tps`` & co. don't each
grow their own reader. Heavy dependencies (trimesh, vtk, opensim) are imported
inside the functions: importing this module costs nothing.

Note: never run a file from inside ``bioscout/model`` as a plain script
(``python measure.py``) — this ``io.py`` (and the ``inspect`` package) would
shadow the standard-library modules of the same name. Use ``python -m`` or the
``bioscout`` command.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Tuple, Union

__all__ = ["load_mesh", "load_mesh_arrays", "read_vtp", "read_vtp_python",
           "read_landmarks",
           "write_landmarks", "load_model", "load_osim_model"]

PathLike = Union[str, Path]

#: formats trimesh reads directly
TRIMESH_EXT = {".stl", ".obj", ".ply", ".off", ".glb", ".gltf"}


# --------------------------------------------------------------------------- #
# meshes
# --------------------------------------------------------------------------- #
#: VTK scalar types -> numpy dtype strings, for the vtk-free .vtp reader
_VTK_DTYPES = {"Float32": "f4", "Float64": "f8", "Int8": "i1", "UInt8": "u1",
               "Int16": "i2", "UInt16": "u2", "Int32": "i4", "UInt32": "u4",
               "Int64": "i8", "UInt64": "u8"}


def _vtp_decode(el, appended, header_dtype, compressed: bool):
    """One ``<DataArray>`` -> flat numpy array, without vtk.

    Handles ``ascii``, ``binary`` and ``appended`` data, base64 or raw, plain or
    zlib-compressed. In base64 the header and the payload are two separate
    base64 streams (and an ``appended`` offset counts encoded characters, not
    bytes) -- getting that wrong is what makes hand-rolled readers fail on
    half the files VTK writes.
    """
    import base64
    import zlib
    import numpy as np

    dt = np.dtype(_VTK_DTYPES[el.get("type")]).newbyteorder("<")
    h = header_dtype.itemsize
    fmt = (el.get("format") or "ascii").lower()
    if fmt == "ascii":
        return np.array((el.text or "").split(), dtype=dt)

    if fmt == "appended":
        off = int(el.get("offset", 0))
        src = appended[off:]                      # str (base64) or bytes (raw)
    else:
        src = "".join((el.text or "").split())
    b64 = isinstance(src, str)

    def _head(nbytes):
        """First ``nbytes`` of the header, and where the payload starts."""
        if not b64:
            return src[:nbytes], nbytes
        enc = 4 * ((nbytes + 2) // 3)
        return base64.b64decode(src[:enc])[:nbytes], enc

    if not compressed:
        head, at = _head(h)
        n = int(np.frombuffer(head, header_dtype)[0])
        body = base64.b64decode(src[at:])[:n] if b64 else src[at:at + n]
        if len(body) < n and b64:                 # one stream, not two
            whole = base64.b64decode(src)
            body = whole[h:h + n]
        return np.frombuffer(body, dt)

    # compressed: header = [n_blocks, block size, last block size, sizes...]
    n_blocks = int(np.frombuffer(_head(h)[0], header_dtype)[0])
    head, at = _head((3 + n_blocks) * h)
    sizes = np.frombuffer(head[3 * h:], header_dtype)
    blob = base64.b64decode(src[at:]) if b64 else src[at:]
    data, seek = b"", 0
    for size in sizes:
        data += zlib.decompress(blob[seek:seek + int(size)])
        seek += int(size)
    return np.frombuffer(data, dt)


def read_vtp_python(path: PathLike) -> Tuple["object", "object"]:
    """``.vtp`` -> ``(vertices (N,3), triangles (M,3))`` with numpy only.

    The fallback for environments without vtk. Polygons are fan-triangulated,
    so quads and n-gons work; point data (normals, scalars) is ignored.
    """
    import xml.etree.ElementTree as ET
    import numpy as np

    root = ET.parse(str(path)).getroot()
    header_dtype = np.dtype(_VTK_DTYPES[root.get("header_type", "UInt32")]).newbyteorder("<")
    compressed = bool(root.get("compressor"))
    app = root.find("AppendedData")
    appended = b""
    if app is not None and app.text:
        raw = app.text.strip()
        raw = raw[raw.index("_") + 1:] if raw.startswith("_") or "_" in raw[:4] else raw
        # base64 stays text: the arrays' offsets count encoded characters
        appended = raw if app.get("encoding", "base64") == "base64" else raw.encode("latin-1")

    piece = root.find(".//Piece")
    if piece is None:
        raise ValueError(f"no PolyData piece in {path}")
    pts_el = piece.find("Points/DataArray")
    if pts_el is None:
        raise ValueError(f"no points in {path}")
    verts = _vtp_decode(pts_el, appended, header_dtype, compressed).astype(float).reshape(-1, 3)

    tris = []
    for tag in ("Polys", "Strips"):
        block = piece.find(tag)
        if block is None:
            continue
        arrays = {a.get("Name"): a for a in block.findall("DataArray")}
        if "connectivity" not in arrays or "offsets" not in arrays:
            continue
        conn = _vtp_decode(arrays["connectivity"], appended, header_dtype, compressed).astype(np.int64)
        offs = _vtp_decode(arrays["offsets"], appended, header_dtype, compressed).astype(np.int64)
        start = 0
        for end in offs:
            poly = conn[start:end]
            start = int(end)
            for k in range(1, len(poly) - 1):       # fan triangulation
                tris.append((poly[0], poly[k], poly[k + 1]))
    if not tris:
        raise ValueError(f"no polygons in {path}")
    return verts, np.asarray(tris, dtype=np.int64)


def read_vtp(path: PathLike) -> Tuple["object", "object"]:
    """OpenSim ``.vtp`` -> ``(vertices (N,3), triangles (M,3))``.

    Uses vtk when it is installed, otherwise :func:`read_vtp_python` (numpy
    only) -- a model's bone geometry should not need a vtk install to measure.
    Polygons are triangulated, so quads/n-gons in older OpenSim geometry work.
    """
    import numpy as np
    try:
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
    except ImportError:
        return read_vtp_python(path)

    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    tri = vtk.vtkTriangleFilter()
    tri.SetInputConnection(reader.GetOutputPort())
    tri.Update()
    poly = tri.GetOutput()
    if poly.GetNumberOfPoints() == 0:
        raise ValueError(f"no geometry in {path}")
    verts = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    faces = vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    return verts, np.asarray(faces, dtype=np.int64)


def load_mesh(path: PathLike):
    """Any bone mesh -> single ``trimesh.Trimesh``.

    STL/OBJ/PLY/... via trimesh, ``.vtp`` (OpenSim geometry) via vtk.
    Raises ``FileNotFoundError`` for a missing file (trimesh on its own gives
    an unhelpful ``ValueError``).
    """
    import trimesh

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    ext = path.suffix.lower()
    if ext == ".vtp":
        v, f = read_vtp(path)
        return trimesh.Trimesh(vertices=v, faces=f, process=False)
    if ext not in TRIMESH_EXT:
        raise ValueError(f"unsupported mesh format: {path.name}")
    return trimesh.load_mesh(str(path), force="mesh")


def load_mesh_arrays(path: PathLike):
    """Mesh as plain ``(vertices, faces)`` numpy arrays (no trimesh object)."""
    m = load_mesh(path)
    return m.vertices.view(type=__import__("numpy").ndarray), \
        m.faces.view(type=__import__("numpy").ndarray)


# --------------------------------------------------------------------------- #
# landmarks
# --------------------------------------------------------------------------- #
def read_landmarks(path: PathLike) -> Dict[str, "object"]:
    """CSV with columns ``name,x,y,z`` -> ``{name: array([x, y, z])}``.

    Blank coordinates are skipped (so a half-filled template still loads).
    """
    import numpy as np

    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                out[r["name"].strip()] = np.array([float(r["x"]), float(r["y"]), float(r["z"])])
            except (TypeError, ValueError):
                continue
    return out


def write_landmarks(path: PathLike, landmarks: Dict[str, "object"]) -> Path:
    """``{name: xyz}`` -> CSV with columns ``name,x,y,z``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "x", "y", "z"])
        for k, v in landmarks.items():
            w.writerow([k, *map(float, v)])
    return path


# --------------------------------------------------------------------------- #
# models
# --------------------------------------------------------------------------- #
def load_model(path: PathLike, accuracy=None):
    """``opensim.Model`` with bioscout's relaxed assembly accuracy.

    Thin re-export of :func:`bioscout.model.opensim_base.load_model` (the one
    implementation), imported lazily so this module does not need OpenSim.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    from bioscout.model.opensim_base import load_model as _load
    return _load(str(path), accuracy=accuracy)


#: alias, for readability at call sites that also load meshes
load_osim_model = load_model
