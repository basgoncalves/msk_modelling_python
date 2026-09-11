OpenSim model templates
========================
Place generic .osim model files here. They will be copied to
<project>/Models/ when you run:

    python -m bioscout --init <project_path>

Expected models
---------------
  GPK_v4_016.osim      — full-body GPK model (default assigned to new subjects)

GPK_v4_016 replaced the older GPK_v3 / GPK_generic_modWO template on
2026-09-02. Its provenance (what was edited relative to GPK_v4_015, and why)
is in GPK_v4_016.provenance.json beside it. Nothing in the package refers to
GPK_v3 as a file any more; the remaining mentions in docstrings and the
CHANGELOG are historical notes about where a measurement came from.

Geometry folders (mesh files) are gitignored via *Geometry/ in .gitignore.
Add any Geometry/ subfolder alongside its .osim file; it will be copied on
--init even though it is not tracked in git.

Each subject's generic_model field in subjects.json resolves relative to the
project root, e.g.:
  "generic_model": "Models/GPK_v4_016.osim"
