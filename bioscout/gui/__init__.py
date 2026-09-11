import io



def simulations_root(project_root, config_manager=None):
    """The folder holding <subject>/<session>, for THIS project.

    Resolution order, first hit wins:

      1. the Configuration tab's "Simulations Directory" (project.simulations_dir)
      2. SIMULATIONS_DIR in the project's settings.py — the project already
         states it there and the GUI should not need telling twice
      3. the first of simulations/, simulations_test/, simulations2/ that
         exists on disk
      4. <project>/simulations, so the caller still gets a path to report

    Hard-coding "simulations" here is what made the Trial Analysis tab show an
    empty Subject list for a project whose sessions live in simulations_test/,
    with nothing on screen to say why.
    """
    from pathlib import Path
    if not project_root:
        return None
    project_root = Path(project_root)

    if config_manager is not None:
        try:
            v = config_manager.get("project.simulations_dir", None)
            if v:
                p = Path(v)
                p = p if p.is_absolute() else (project_root / v)
                if p.is_dir():
                    return p
        except Exception:
            pass

    st = project_root / "settings.py"
    if st.is_file():
        try:
            import re as _re
            txt = st.read_text(encoding="utf-8", errors="replace")
            m = _re.search(r'^SIMULATIONS_DIR\s*=.*?["\']([^"\']+)["\']',
                           txt, _re.M)
            if m:
                p = project_root / m.group(1)
                if p.is_dir():
                    return p
            m = _re.search(r'^SIMULATIONS_DIR\s*=\s*PROJECT_ROOT\s*/\s*["\']([^"\']+)["\']',
                           txt, _re.M)
            if m:
                p = project_root / m.group(1)
                if p.is_dir():
                    return p
        except Exception:
            pass

    for name in ("simulations", "simulations_test", "simulations2"):
        p = project_root / name
        if p.is_dir():
            return p
    return project_root / "simulations"


def scaling_defaults(session_dir, iteration=None):
    """Everything Model Scaling needs, derived from session.yaml.

    The tab used to ask you to TYPE four paths that the session already
    states: the generic model, the markerset, the static trial's markers, and
    where the scaled model goes. Typing them invites the two failures that are
    hardest to notice — a markerset that belongs to another project, and an
    output written outside the iteration, where the pipeline will not find it.

    Returns a dict with the keys the tab fills in, plus ``errors`` naming
    anything that could not be resolved. Values are "" when unknown rather
    than guessed, so a missing piece shows as an empty field instead of a
    plausible wrong path.

        template_model   iterations.<it>.model_generic (relative to the
                         iteration folder; old bare names are still searched)
        markerset        iterations.<it>.markerset, same rule
        trc              2_experimental/<static_trial>/marker_experimental.trc
        output           iterations.<it>.model_scaled, else
                         models/personalised/<subject>/<session>/<generic>_scaled.osim
        static_trial     the session's static trial name
        iterations       every iteration the session declares
    """
    import os as _os
    out = {"template_model": "", "markerset": "", "trc": "", "output": "",
           "static_trial": "", "iterations": [], "errors": []}
    if not session_dir:
        return out
    session_dir = _os.path.abspath(str(session_dir))
    ypath = _os.path.join(session_dir, "session.yaml")
    if not _os.path.isfile(ypath):
        out["errors"].append("no session.yaml in this session")
        return out
    try:
        import yaml
        from bioscout.session.config import normalise_iterations
        with io.open(ypath, encoding="utf-8") as _fh:
            cfg = normalise_iterations(yaml.safe_load(_fh) or {}, ypath)
    except Exception as e:
        out["errors"].append(f"session.yaml unreadable: {e}")
        return out

    its = cfg.get("iterations") or {}
    out["iterations"] = sorted(its)
    if iteration is None:
        iteration = out["iterations"][0] if out["iterations"] else None
    it = (its.get(iteration) or {}) if iteration else {}

    # project root: session.yaml's project_dir, else <sims>/<subject>/<session>
    proj = (_os.path.abspath(_os.path.join(session_dir, str(cfg["project_dir"])))
            if cfg.get("project_dir")
            else _os.path.dirname(_os.path.dirname(_os.path.dirname(session_dir))))
    itdir = ""
    if iteration:
        try:
            from bioscout.session.layout import iteration_path
            itdir = iteration_path(session_dir, iteration)
        except Exception:
            itdir = _os.path.join(session_dir, "3_iterations", iteration)

    def _in_iteration(rel):
        """session.yaml rule: relative to the iteration folder."""
        if not rel or not itdir:
            return ""
        c = _os.path.normpath(_os.path.join(itdir, rel))
        return c if _os.path.isfile(c) else ""

    gen = it.get("model_generic") or ""
    if gen and _in_iteration(gen):
        out["template_model"] = _in_iteration(gen)
    elif gen:
        for base in (_os.path.join(proj, "models", "generic"),
                     _os.path.join(proj, "generic models"),
                     _os.path.join(proj, "models"), proj, session_dir):
            cand = _os.path.join(base, gen)
            if _os.path.isfile(cand):
                out["template_model"] = _os.path.normpath(cand)
                break
        if not out["template_model"]:
            out["errors"].append(f"model_generic not found: {gen}")
    elif iteration:
        out["errors"].append(f"iteration {iteration!r} has no 'model_generic'")

    ms = it.get("markerset") or cfg.get("markerset") or ""
    if ms and _in_iteration(ms):
        out["markerset"] = _in_iteration(ms)
    elif ms:
        # A Windows absolute path ("C:\\...") is not isabs() on POSIX, so a
        # naive join glues it onto the project root and produces a path that
        # exists nowhere. Treat a drive letter as absolute on every platform.
        _abs = _os.path.isabs(ms) or (len(ms) > 2 and ms[1] == ":")
        cand = ms if _abs else _os.path.join(proj, ms)
        if not _os.path.isfile(cand) and not _abs:
            # the markerset is lab equipment, not session data — it lives in
            # the models folder. Try there before declaring it missing.
            base = _os.path.basename(ms)
            for alt in (_os.path.join(proj, "models", "utils", base),
                        _os.path.join(proj, "models", "generic", base),
                        _os.path.join(proj, "models", base)):
                if _os.path.isfile(alt):
                    cand = alt
                    break
        out["markerset"] = _os.path.normpath(cand)
        if not _os.path.isfile(cand):
            out["errors"].append(f"markerset not found: {ms}")

    st = cfg.get("static_trial") or ""
    out["static_trial"] = st
    if st:
        trc = _os.path.join(session_dir, "2_experimental", st,
                            "marker_experimental.trc")
        out["trc"] = _os.path.normpath(trc)
        if not _os.path.isfile(trc):
            out["errors"].append(
                f"static trial not exported yet: {st} (run c3d export)")
    else:
        out["errors"].append("session.yaml has no static_trial")

    if iteration:
        # models/personalised/<subject>/ — ONE scaled model per subject serves
        # every session and iteration (the shared model library resolves
        # absolute paths first), instead of a copy buried inside each
        # session's 3_iterations/. Name keeps the generic's stem so the file
        # says what it was scaled from.
        subject = _os.path.basename(_os.path.dirname(session_dir))
        sess = _os.path.basename(_os.path.abspath(session_dir))
        stem = _os.path.splitext(_os.path.basename(gen))[0] if gen else "model"
        out["output"] = (_os.path.normpath(_os.path.join(itdir, it["model_scaled"]))
                         if it.get("model_scaled") and itdir else
                         _os.path.normpath(_os.path.join(
                             proj, "models", "personalised", subject, sess,
                             f"{stem}_scaled.osim")))
    return out
