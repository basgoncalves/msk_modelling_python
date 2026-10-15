"""Sphinx config for the bioscout docs (concepts + guides + API reference).

    pip install sphinx myst-parser furo
    sphinx-build -b html docs docs/site        # from the repo root
    open docs/site/index.html
"""
import os
import sys

sys.path.insert(0, os.path.abspath(".."))          # the repo root: import bioscout

project = "bioscout"
author = "Basilio Goncalves"
copyright = "2026, Basilio Goncalves"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
]
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence", "deflist", "tasklist"]
myst_heading_anchors = 3

# the docs folder also holds history notes, figure sources and this build
exclude_patterns = ["site", "_build", "_figures", "README.md", "**/.ipynb_checkpoints"]

# --- API reference ----------------------------------------------------------
autosummary_generate = True
autosummary_imported_members = False
autodoc_default_options = {"members": True, "undoc-members": False,
                           "show-inheritance": True, "member-order": "bysource"}
autodoc_typehints = "description"
autoclass_content = "both"
# Heavy / optional dependencies: imported lazily at run time, mocked for the docs
autodoc_mock_imports = [
    "opensim", "PyQt5", "PyQt6", "PySide2", "PySide6", "pyqtgraph", "ezc3d", "c3d",
    "btk", "cv2", "torch", "casadi", "msk_modelling_python", "vtk", "pyvista",
    "trimesh", "open3d", "mediapipe", "skimage", "sklearn", "spm1d", "tkinter",
    "win32com", "pythoncom", "pywinauto", "docx", "reportlab", "fitz",
]
suppress_warnings = ["autosummary", "autodoc.import_object", "myst.header",
                     "myst.xref_missing", "toc.not_included"]

html_theme = "furo"
html_title = "bioscout"
html_static_path = []
