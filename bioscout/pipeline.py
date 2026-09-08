"""
bioscout.pipeline — project-level orchestration driven by settings flags.

This folds the old per-project driver scripts (redo_pipeline.py, run_pipeline.py,
redo_ceinms.py, summarize_results.py) into the package so a project is run with a
single command::

    python -m bioscout -b settings.py

The settings module controls what runs via module-level flags::

    RUN_PIPELINE = True   # rebuild inputs from c3d + IK/ID/MA/SO/JRA + CEINMS
    RUN_SUMMARY  = True   # build the results/manuscript summary
    RUN_SCALING  = False  # (optional) re-scale models before the pipeline

``run_project`` reads those flags and calls the steps below. Everything operates
on a ``bioscout.Project`` rooted at the settings file's folder.
"""
import os
import sys
import shutil
import datetime
import runpy

# Files a trial folder is allowed to start with — everything else is regenerated
# from these by export_c3d. (Mirrors the canonical "raw inputs only" policy.)
RAW_INPUTS = ["c3dfile.c3d"]
C3D = "c3dfile.c3d"
TRC = "marker_experimental.trc"
GRF = "grf.mot"


def _has_raw_inputs(trial_dir):
    """True if a trial has a c3d OR marker file, in the current ``inputs/``
    layout OR the legacy flat layout (files directly in the trial folder)."""
    for name in (C3D, TRC):
        if (os.path.exists(os.path.join(trial_dir, "inputs", name))
                or os.path.exists(os.path.join(trial_dir, name))):
            return True
    return False

# Raw C3D files for a session live in <session>/c3d/ (one per trial). This folder
# is source data, so reset must never delete it.
C3D_DIRNAME = "c3d"


def _calibration_trials(settings_module, default=("Walking_02", "Squat_BW_01")):
    """Resolve CEINMS calibration trials from settings, with a safe default."""
    cs = getattr(settings_module, "CEINMSSettings", None)
    names = getattr(cs, "calibration_trial_names", None)
    if names:
        return tuple(names)
    bs = getattr(settings_module, "BatchSettings", None)
    names = getattr(bs, "calibration_trials", None)
    return tuple(names) if names else tuple(default)


# ---------------------------------------------------------------------------
# Reset a project's simulations back to inputs-only (with timestamped backup).
# ---------------------------------------------------------------------------

# Per-trial files KEPT on reset: raw experimental inputs + the per-trial config
# the pipeline reads. Everything else in a trial folder is a generated output.
TRIAL_KEEP = {
    # subfoldered layout: keep the whole inputs/ folder + the trial manifest
    "inputs", "trial_settings.xml",
    # flat layout (pre-migration): keep the individual raw input files too
    "c3dfile.c3d", "marker_experimental.trc", "grf.mot",
    "GRF.xml", "emg.mot", "analog.csv",
}
# Session-level files KEPT on reset: none. All CEINMS calibration files now live
# in the session's ceinms_calibration/ folder (a non-trial dir that is removed and
# regenerated), so nothing at the session root needs preserving.
SESSION_KEEP = set()


def _is_trial_dir(path):
    """A trial folder holds raw motion inputs — flat (c3d/markers at root) OR the
    subfoldered layout (an inputs/ folder or a trial_settings.xml manifest)."""
    return (os.path.exists(os.path.join(path, C3D))
            or os.path.exists(os.path.join(path, TRC))
            or os.path.isdir(os.path.join(path, "inputs"))
            or os.path.exists(os.path.join(path, "trial_settings.xml")))


def reset_simulations(project_dir=None, backup=True, dry_run=False,
                      subjects=None, session=None, trials=None,
                      trial_keep=None, session_keep=None, raw_inputs=False,
                      extra_backup=("results", os.path.join("manuscript", "figures")),
                      verbose=True):
    """Back up and reset a project's simulations tree to inputs-only.

    For each ``simulations/<subject>/<session>``:
      * every trial folder is reduced to ``trial_keep`` (raw inputs + trial
        settings); all generated outputs — IK/ID/MA/SO/JRA results, ``setup_*.xml``,
        ``MuscleAnalysis/``, ``Execution*/``, plots, filtered EMG, ... — are deleted;
      * session-level CEINMS *inputs* (``session_keep``) are kept; calibration
        *outputs* (``subjectCalibrated*``, ``*_parameters.png``, ``*_vs_uncalibrated.png``)
        and any non-trial sub-folder (``calibrationOutput*``, old run backups) are deleted.

    Before deleting anything, ``simulations/`` and every existing path in
    ``extra_backup`` (project-relative, e.g. ``results/`` and ``manuscript/figures/``)
    are copied to timestamped siblings ``<name>_backup_<YYYYmmdd_HHMMSS>`` that all
    share one timestamp. Use ``dry_run=True`` to preview without touching disk.

    Pass ``subjects`` (name or list), ``session`` (name or list) and/or ``trials``
    (name or list) to scope the reset to just those; the backup is then limited to
    the selected subtree too. When ``trials`` is given, only matching trial folders
    are reset — non-trial dirs and session-level files in that session are left
    untouched. With no scope, every subject/session is reset and the whole tree is
    backed up.

    Returns a dict: ``{"timestamp", "backups": [...], "trials_reset", "removed"}``.
    """
    import bioscout
    project_dir = os.path.abspath(project_dir or os.getcwd())
    proj = bioscout.Project(project_dir)
    sim = proj.utils.SIMULATIONS_DIR or os.path.join(project_dir, "simulations")
    tkeep = set(trial_keep) if trial_keep is not None else set(TRIAL_KEEP)
    skeep = set(session_keep) if session_keep is not None else set(SESSION_KEEP)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log = print if verbose else (lambda *a, **k: None)

    if not os.path.isdir(sim):
        raise FileNotFoundError(f"no simulations folder at {sim}")
    info = {"timestamp": ts, "backups": [], "trials_reset": 0, "removed": 0}

    # Optional scoping: restrict the reset (and backup) to specific subject(s) /
    # session(s). None = every subject / every session.
    subj_filter = ({subjects} if isinstance(subjects, str)
                   else set(subjects) if subjects else None)
    sess_filter = ({session} if isinstance(session, str)
                   else set(session) if session else None)
    trial_filter = ({trials} if isinstance(trials, str)
                    else set(trials) if trials else None)
    scoped = (subj_filter is not None or sess_filter is not None
              or trial_filter is not None)

    # ---- 1. backups (shared timestamp) ----
    if backup and not dry_run:
        dst = f"{sim}_backup_{ts}"
        if scoped:
            # Back up only the selected subject/session subtree(s), preserving the
            # simulations/<subject>/<session> layout so a restore is a plain copy.
            n = 0
            for subject in sorted(os.listdir(sim)):
                if subj_filter is not None and subject not in subj_filter:
                    continue
                sub_dir = os.path.join(sim, subject)
                if not os.path.isdir(sub_dir):
                    continue
                for sess_name in sorted(os.listdir(sub_dir)):
                    if sess_filter is not None and sess_name not in sess_filter:
                        continue
                    s = os.path.join(sub_dir, sess_name)
                    if not os.path.isdir(s):
                        continue
                    if trial_filter is not None:
                        # Back up only the selected trial folder(s).
                        for tname in sorted(os.listdir(s)):
                            if tname not in trial_filter:
                                continue
                            tsrc = os.path.join(s, tname)
                            if not os.path.isdir(tsrc):
                                continue
                            d = os.path.join(dst, subject, sess_name, tname)
                            log(f"[reset] backup {subject}/{sess_name}/{tname} -> "
                                f"{os.path.relpath(d, project_dir)}")
                            shutil.copytree(tsrc, d); n += 1
                    else:
                        d = os.path.join(dst, subject, sess_name)
                        log(f"[reset] backup {subject}/{sess_name} -> {os.path.relpath(d, project_dir)}")
                        shutil.copytree(s, d); n += 1
            if n:
                info["backups"].append(dst)
        else:
            log(f"[reset] backup {sim} -> {dst}  (can take a while)")
            shutil.copytree(sim, dst); info["backups"].append(dst)
            for rel in extra_backup:
                src = os.path.join(project_dir, rel)
                if os.path.isdir(src):
                    d = os.path.join(os.path.dirname(src),
                                     f"{os.path.basename(src)}_backup_{ts}")
                    log(f"[reset] backup {src} -> {d}")
                    shutil.copytree(src, d); info["backups"].append(d)
        log("[reset] backups done")
    elif backup:
        log(f"[reset] (dry-run) would back up "
            f"{'selected subject/session' if scoped else sim} with ts={ts}")

    def _remove(path):
        info["removed"] += 1
        if dry_run:
            log(f"    would remove {os.path.relpath(path, sim)}")
            return
        try:
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        except Exception as e:
            log(f"    [warn] could not remove {path}: {e}")

    # ---- 2. walk subjects / sessions and strip to inputs ----
    for subject in sorted(os.listdir(sim)):
        if subj_filter is not None and subject not in subj_filter:
            continue
        sub_dir = os.path.join(sim, subject)
        if not os.path.isdir(sub_dir):
            continue
        for sess_name in sorted(os.listdir(sub_dir)):
            if sess_filter is not None and sess_name not in sess_filter:
                continue
            sess_dir = os.path.join(sub_dir, sess_name)
            if not os.path.isdir(sess_dir):
                continue
            for entry in sorted(os.listdir(sess_dir)):
                p = os.path.join(sess_dir, entry)
                if os.path.isdir(p):
                    if _is_trial_dir(p):
                        if trial_filter is not None and entry not in trial_filter:
                            continue
                        # Subfoldered trial (has inputs/): keep ONLY inputs/ +
                        # trial_settings.xml, so stale root-level files (e.g. a
                        # leftover flat emg_ceinms.mot / grf.mot) are stripped.
                        # Flat trial (no inputs/): fall back to keeping the raw
                        # input files so un-migrated raw data isn't deleted.
                        # An explicit trial_keep=... always overrides.
                        if trial_keep is not None:
                            tkeep_eff = tkeep
                        elif os.path.isdir(os.path.join(p, "inputs")):
                            tkeep_eff = {"inputs", "trial_settings.xml"}
                        else:
                            tkeep_eff = tkeep
                        kept = 0
                        for item in sorted(os.listdir(p)):
                            if item in tkeep_eff:
                                kept += 1
                            else:
                                _remove(os.path.join(p, item))
                        # raw_inputs: additionally prune inside inputs/ down to just
                        # the raw C3D (RAW_INPUTS), so only c3dfile.c3d + trial_settings.xml
                        # remain. Derived files (markers/grf/emg/GRF.xml/plots) are
                        # regenerated on the next --export run.
                        if raw_inputs:
                            _inp = os.path.join(p, "inputs")
                            if os.path.isdir(_inp):
                                for item in sorted(os.listdir(_inp)):
                                    if item not in RAW_INPUTS:
                                        _remove(os.path.join(_inp, item))
                        info["trials_reset"] += 1
                        log(f"[reset] trial {subject}/{sess_name}/{entry}: kept {kept} input(s)"
                            f"{' (raw c3d only)' if raw_inputs else ''}")
                    else:
                        # The raw-C3D folder (<session>/c3d/) holds source data and
                        # is never removed by reset.
                        if entry == C3D_DIRNAME:
                            continue
                        # When scoped to specific trials, leave non-trial dirs alone.
                        if trial_filter is not None:
                            continue
                        log(f"[reset] remove non-trial dir {subject}/{sess_name}/{entry}")
                        _remove(p)
                elif entry not in skeep:
                    # When scoped to specific trials, leave session-level files alone.
                    if trial_filter is not None:
                        continue
                    _remove(p)

    log(f"[reset] {'DRY-RUN ' if dry_run else ''}done (ts={ts}): "
        f"{info['trials_reset']} trials reset, {info['removed']} item(s) "
        f"{'to remove' if dry_run else 'removed'}; backups: {info['backups']}")
    return info


def _run_scaling(subj, sdir, session, config, u, replace=True):
    """Scale a subject's generic model for ONE session, producing the models the
    Subject references. Three stages, matching the naming convention:

        generic  --scale-->  scaled.osim
                 --Modenese2015 muscle-opt (N_eval)-->  scaled_opt_N<N>.osim   (= model_ceinms)
                 --isometric-force x factor-->            <model_so>            (e.g. *_mvicx3.00.osim)

    The static trial is taken from ``BatchSettings.static_trials[session]`` (a
    ``{session: static_trial_name}`` map), else the Subject's ``static_trial``,
    else the first trial folder whose name starts with 'static'. Outputs go to
    ``models/<subject>/<session>/``. Returns the final model path, or None."""
    from bioscout.model.edit.osim_ops import increase_isometric_force
    from bioscout.model.muscle_optimize import muscle_optimimizer_Modenese2015
    from bioscout.model.scale.osim_scale import scale_model
    import shutil

    generic = subj.generic_model_path()
    if not generic or not os.path.exists(generic):
        print(f"  [scale ERROR] generic model not found for {subj.name}: "
              f"{subj.generic_model!r} -> {generic}")
        return None

    # Resolve the static trial for this session.
    smap = getattr(config, "static_trials", None) or {}
    static_name = smap.get(session) or getattr(subj, "static_trial", None)
    if not static_name:
        static_name = next((d for d in sorted(os.listdir(sdir))
                            if d.lower().startswith("static")
                            and os.path.isdir(os.path.join(sdir, d))), None)
    if not static_name:
        print(f"  [scale ERROR] no static trial for {subj.name}/{session} "
              f"(set BatchSettings.static_trials['{session}'])")
        return None
    static_dir = os.path.join(sdir, static_name)
    trc = os.path.join(static_dir, "inputs", TRC)
    if not os.path.exists(trc):
        try:
            subj.make_trial(static_dir).export_c3d()
        except Exception as e:
            print(f"  [scale] static export failed: {e}")
    if not os.path.exists(trc):
        print(f"  [scale ERROR] static TRC not found: {trc}")
        return None

    model_dir = os.path.join(str(u.MODELS_DIR), subj.name, session)
    os.makedirs(model_dir, exist_ok=True)
    final = os.path.join(model_dir, subj.model_so or f"{subj.name}.osim")
    if os.path.exists(final) and not replace:
        print(f"  [skip] scaled model already exists: {final}")
        return final

    markerset = getattr(config, "markerset", None)
    print(f"  [scale] {subj.name}/{session}: {os.path.basename(generic)} "
          f"+ static '{static_name}' -> {os.path.basename(final)}")

    # Scaling-stage toggles (per-subject; map to OpenSim ScaleTool stages).
    linear_scaling = bool(getattr(subj, "linear_scaling", True))
    marker_placer  = bool(getattr(subj, "marker_placer", False))
    prescaled      = getattr(subj, "prescaled_model", None)

    def _resolve_model(pth):
        if not pth:
            return None
        if os.path.isabs(pth) and os.path.exists(pth):
            return pth
        pd = getattr(u, "PROJECT_DIR", None) or os.getcwd()
        for base in (str(u.MODELS_DIR), os.path.join(pd, "generic models"), pd):
            cand = os.path.join(base, pth)
            if os.path.exists(cand):
                return cand
        return pth

    # 1) build the model that muscle-opt starts from. A prescaled/MRI model is
    #    already geometry-personalised → never dimensionally scale it; only the
    #    marker placer may run. Otherwise honour linear_scaling/marker_placer.
    scaled = os.path.join(model_dir, "scaled.osim")
    if prescaled:
        scale_input = _resolve_model(prescaled)
        linear_scaling = False
        print(f"  [scale] {subj.name}: prescaled model (no geometric scaling): "
              f"{os.path.basename(scale_input or prescaled)}")
    else:
        scale_input = generic
    scale_model(scale_input, trc, scaled, scale_setup_output_dir=model_dir,
                marker_set_file=markerset,
                linear_scaling=linear_scaling, marker_placer=marker_placer)

    # 2) muscle-parameter optimisation (Modenese 2015) -> scaled_opt_N<N>.osim
    #    Reference is the generic template even for a prescaled model (preserves
    #    the template's muscle operating range in the personalised geometry).
    n_eval = int(getattr(config, "muscle_opt_neval", 10) or 10)
    opt = os.path.join(model_dir, f"scaled_opt_N{n_eval}.osim")
    muscle_optimimizer_Modenese2015(scaled, save_path=opt,
                                    ref_model_path=generic, N_eval=n_eval)

    # 3) isometric-force scaling x factor -> final (named as subj.model_so)
    factor = float(getattr(config, "muscle_force_factor", 1.0) or 1.0)
    if factor and factor != 1.0:
        increase_isometric_force(opt, muscleList="all", factor=factor)
        produced = opt.replace(".osim", f"_increased_{factor:.2f}.osim")
        if os.path.exists(produced) and os.path.abspath(produced) != os.path.abspath(final):
            shutil.copyfile(produced, final)
    elif os.path.abspath(opt) != os.path.abspath(final):
        shutil.copyfile(opt, final)

    print(f"  [scale OK] {subj.name}/{session} -> {final}")
    return final


def run_pipeline(project_dir=None, scale=False, ceinms=True, replace=True,
                 calibration_trials=("Walking_02", "Squat_BW_01"),
                 backup=True, normalise_inputs=None):
    """Full-resolution, non-destructive run of the whole pipeline.

    For every subject/session/trial: export_c3d (regenerates markers/grf/emg/
    trial_settings from the C3D at native sampling — no downsampling and no
    destructive strip), then run IK -> ID -> MA -> SO -> muscle moments -> JRA,
    and finally CEINMS per session (normalise EMG + calibrate + execute). Model
    scaling is intentionally NOT performed (existing scaled models are reused);
    pass ``scale=True`` only once that is wired up.

    Trials with no c3d but an existing .trc (template/MRI subjects) are analysed
    from their existing markers/grf as-is. ``backup`` and ``normalise_inputs``
    are accepted for backwards compatibility but no longer used.
    """
    import bioscout

    project_dir = project_dir or os.getcwd()
    proj = bioscout.Project(project_dir)
    u = proj.utils
    sim = u.SIMULATIONS_DIR

    # Honour BatchSettings switches. ``replace_existing=False`` makes every stage
    # SKIP trials that already have their outputs (resume a partial run without
    # redoing finished trials).
    _bs = getattr(getattr(proj, "settings", None), "BatchSettings", None)
    replace   = bool(getattr(_bs, "replace_existing", replace))
    do_export = bool(getattr(_bs, "enable_c3d_export", True))
    do_norm   = bool(getattr(_bs, "enable_emg_normalise", True))
    # Per-stage switches (external biomechanics = IK + ID; SO implies muscle
    # moments + JRA). Any stage left True runs; set the rest False to stop early.
    do_ik = bool(getattr(_bs, "enable_inverse_kinematics", True))
    do_id = bool(getattr(_bs, "enable_inverse_dynamics", True))
    do_ma = bool(getattr(_bs, "enable_muscle_analysis", True))
    do_so = bool(getattr(_bs, "enable_static_optimization", True))
    # Scaling runs only when BOTH the run flag (RUN_SCALING -> `scale`) and the
    # per-project enable_scale_model switch are on.
    do_scale = bool(scale) and bool(getattr(_bs, "enable_scale_model", True))
    print(f"[pipeline] full-resolution, non-destructive run; "
          f"project={project_dir}; scale={do_scale}; ceinms={ceinms}; "
          f"replace={replace}; export_c3d={do_export}; emg_normalise={do_norm}; "
          f"IK={do_ik} ID={do_id} MA={do_ma} SO={do_so}")

    for subj in proj.subjects:
        if not subj.sessions:
            continue
        sess = subj.sessions[0]
        session = sess.name
        sdir = os.path.join(sim, subj.name, session)
        if not os.path.isdir(sdir):
            print(f"[skip] {subj.name}/{session} — no folder")
            continue
        trials = [d for d in sorted(os.listdir(sdir))
                  if os.path.isdir(os.path.join(sdir, d))
                  and _has_raw_inputs(os.path.join(sdir, d))]
        # Honour BatchSettings.trial_list if the project restricts the run to a
        # subset (e.g. walks first). Empty/None = run every trial found on disk.
        _wanted = getattr(getattr(proj, "settings", None), "BatchSettings", None)
        _wanted = getattr(_wanted, "trial_list", None)
        if _wanted:
            trials = [t for t in trials if t in set(_wanted)]
        print(f"\n==================  {subj.name}/{session}: {len(trials)} trials  ==================")
        if not trials:
            print(f"  [skip] {subj.name}/{session}: no trials with raw inputs "
                  f"(inputs/{C3D} or inputs/{TRC}) — skipping SO + CEINMS.")
            continue

        # A subject/session runs as a CLEAR, LINEAR sequence of named stages.
        # Each stage is gated by its enable flag and skips finished work when
        # replace=False. Order matters (each stage consumes the previous output).
        def _mk(tr):
            return subj.make_trial(os.path.join(sdir, tr))

        # ---- STAGE 1 · export_c3d (raw c3d -> markers/GRF/EMG per trial) ----
        if do_export:
            print(f"\n---- export_c3d · {subj.name}/{session} ----")
            for tr in trials:
                tp = os.path.join(sdir, tr)
                if not (os.path.exists(os.path.join(tp, "inputs", C3D))
                        or os.path.exists(os.path.join(tp, C3D))):
                    continue
                if not replace and all(os.path.exists(os.path.join(tp, "inputs", f))
                                       for f in (TRC, "emg_filtered.mot")):
                    print(f"  [skip] {tr}: already exported"); continue
                try:
                    _mk(tr).export_c3d(); print(f"  [ok] {tr}")
                except Exception as e:
                    print(f"  [ERROR] export_c3d {tr}: {e}")

        # ---- STAGE 2 · run_scale_model (scale -> muscle-opt -> MVIC) --------
        if do_scale:
            print(f"\n---- run_scale_model · {subj.name}/{session} ----")
            try:
                _run_scaling(subj, sdir, session, _bs, u, replace=replace)
            except Exception as e:
                print(f"  [ERROR] scale_model: {e}")

        # ---- STAGE 3 · run_emg_normalise (session-wide MVC normalisation) ---
        if do_norm:
            _all_norm = bool(trials) and all(
                os.path.exists(os.path.join(sdir, tr, "inputs",
                               "emg_filtered_normalised.mot")) for tr in trials)
            if not replace and _all_norm:
                print(f"\n---- run_emg_normalise · [skip] all trials normalised ----")
            else:
                print(f"\n---- run_emg_normalise · {subj.name}/{session} ----")
                try:
                    sess.normalise_emg(replace=replace)
                except Exception as e:
                    print(f"  [ERROR] emg_normalise: {e}")

        # ---- STAGE 4 · run_external_biomechanics (IK + ID) ------------------
        if do_ik or do_id:
            print(f"\n---- run_external_biomechanics (IK+ID) · {subj.name} ----")
            for tr in trials:
                try:
                    t = _mk(tr)
                    if do_ik: t.run_ik(replace=replace)
                    if do_id: t.run_id(replace=replace)
                except Exception as e:
                    print(f"  [ERROR] external_biomechanics {tr}: {e}")

        # ---- STAGE 5 · run_muscle_analysis ----------------------------------
        if do_ma:
            print(f"\n---- run_muscle_analysis · {subj.name} ----")
            for tr in trials:
                try:
                    _mk(tr).run_ma(replace=replace)
                except Exception as e:
                    print(f"  [ERROR] muscle_analysis {tr}: {e}")

        # ---- STAGE 6 · run_static_optimisation (+ JRA on SO forces) ---------
        if do_so:
            print(f"\n---- run_static_optimisation (+JRA) · {subj.name} ----")
            for tr in trials:
                try:
                    t = _mk(tr)
                    t.run_so(replace=replace)
                    t.calculate_muscle_moments(forces_type="so")
                    t.run_jra(replace=replace)
                except Exception as e:
                    print(f"  [ERROR] static_optimisation {tr}: {e}")

        # ---- STAGE 7 · run_ceinms_calibration (once per session) ------------
        if ceinms:
            print(f"\n---- run_ceinms_calibration · {subj.name}/{session} ----")
            try:
                sess.calibrate(replace=replace, calibration_trials=(
                    list(calibration_trials) if calibration_trials else None))
            except Exception as e:
                print(f"  [ERROR] ceinms_calibration: {e}")

        # ---- STAGE 8 · run_ceinms (per-trial execution + JRA on CEINMS) -----
        if ceinms:
            print(f"\n---- run_ceinms (+JRA) · {subj.name} ----")
            for tr in trials:
                try:
                    t = subj.make_trial(os.path.join(sdir, tr), force_type="CEINMS")
                    t.run_ceinms_exe()
                    t.calculate_muscle_moments(forces_type="ceinms")
                    t.run_jra_ceinms(replace=replace)
                except Exception as e:
                    print(f"  [ERROR] ceinms {tr}: {e}")

    print("\n==================  PIPELINE DONE  ==================")
    return True


def run_summary(project_dir=None):
    """Build the project's results/manuscript summary.

    The summary is intentionally project-specific (manuscript figures, metric &
    curve CSVs), so it lives in the project as ``summarize_results.py`` and is
    executed here. Falls back to the package summary (``utils.summary``) if the
    project script is absent.
    """
    project_dir = project_dir or os.getcwd()
    script = os.path.join(project_dir, "summarize_results.py")
    if os.path.exists(script):
        print(f"[summary] running {script}")
        runpy.run_path(script, run_name="__main__")
        return True
    try:
        from bioscout.plot.summary import run_summary as _pkg_summary
        print("[summary] project summarize_results.py not found — using package summary")
        return bool(_pkg_summary())
    except Exception as e:
        print(f"[summary] no summary available: {e}")
        return False


def run_project(project_dir, settings_module):
    """Dispatcher for ``python -m bioscout -b settings.py``.

    Reads RUN_PIPELINE / RUN_SUMMARY / RUN_SCALING from the settings module and
    runs the requested stages. Returns True if everything requested succeeded.
    """
    run_pipe = bool(getattr(settings_module, "RUN_PIPELINE", False))
    run_summ = bool(getattr(settings_module, "RUN_SUMMARY", False))
    run_scale = bool(getattr(settings_module, "RUN_SCALING", False))
    run_ceinms_flag = bool(getattr(settings_module, "RUN_CEINMS", True))
    calib = _calibration_trials(settings_module)

    print("=" * 70)
    print(f"[bioscout] project run: pipeline={run_pipe} summary={run_summ} "
          f"scaling={run_scale} ceinms={run_ceinms_flag}")
    print("=" * 70)

    ok = True
    if run_pipe:
        ok = run_pipeline(project_dir, scale=run_scale, ceinms=run_ceinms_flag,
                          calibration_trials=calib) and ok
    if run_summ:
        ok = run_summary(project_dir) and ok
    if not run_pipe and not run_summ:
        print("[bioscout] nothing to do — set RUN_PIPELINE and/or RUN_SUMMARY "
              "in settings.py.")
    return ok
