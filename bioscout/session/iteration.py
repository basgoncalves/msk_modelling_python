"""Iteration — one model iteration of a recording session: the runnable unit.

``Session(path).iteration("gpk")`` returns one. It resolves the iteration's
models from session.yaml and runs the pipeline stages over the session's
trials: :meth:`Iteration.scale_model`, :meth:`Iteration.run`
(exbiomec / muscle_analysis / so / mew / ceinms), EMG normalisation, CEINMS
calibration, plots.
"""
from __future__ import annotations

import os
import glob
import shutil
import time
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from xml.etree import ElementTree as ET
from pathlib import Path

try:
    import yaml  # PyYAML
except Exception:
    yaml = None

from bioscout.core.analysis import Analyse
from . import layout as _layout
from .layout import experimental_dir, iteration_dir, _RAW_ATTR_FILES
from .config import (
    yaml_bool, load_session_yaml, body_mass_from_static,
    _iteration_blocks, calibration_trial_names, normalisation_trial_names,
    emg_map_name_for, resolve_emg_map, resolve_emg_gain,
    calibration_name_for, resolve_calibration, iteration_is_calibrated,
    ITERATION_KEYS, ITERATION_FILE_KEYS, normalise_iterations, IterationKeys,
)

# ---------------------------------------------------------------------------
# Does the CEINMS stage repair its own inputs?
#
# False (default): `do_ceinms` runs CEINMS and NOTHING else. If a calibration
# trial's IK/ID/MA are missing or stale it reports an error naming the trial and
# what to run, then skips calibration. A stage that silently runs three other
# stages is a stage you cannot time, cannot reason about, and cannot use in a
# sandbox -- a t10 calibration sweep re-solved IK->ID->MA before every
# configuration, minutes each, for outputs that could not change.
#
# True: the previous behaviour -- re-solve IK->ID->MA for any stale calibration
# trial before calibrating. Set it if you have a caller that relies on
# `do_ceinms` self-healing after a re-scale.
#
# The staleness TEST is unchanged either way, and it is the right test: never
# reuse a stale IK/ID solved over a DIFFERENT window than MA, because the CEINMS
# inputData window then inherits that span, has no muscle-length data there, and
# calibration dies silently -- reads its inputs, writes no subjectCalibrated.xml.
CEINMS_AUTOPREP = False



# ===========================================================================
# The runnable Iteration  —  ONE model iteration of a recording session on disk.
#
# Layout:  simulations/<athlete>/<session>/<iteration>/<trial>/...
# An Iteration is scoped to ONE model iteration; trials are discovered from the
# session's session.yaml. Raw model-INDEPENDENT inputs (markers/grf/emg) are
# SHARED across iterations and live in <session>/experimental/<trial>/.
# It is the runnable unit: scale_model / run / plot_summary all live here. Get
# one from a Session:  Session(path).iteration("gpk_mri").
# ===========================================================================
class Iteration(IterationKeys):
    """One (model-iteration, recording-session) on disk — the RUNNABLE unit.

    ``session_dir`` is the athlete/session folder holding ``session.yaml``
    (e.g. ``simulations/Athlete_03/25_03_31``); ``iteration`` is the model
    sub-folder (``gpk``, ``gpk_mri``, ``cateli`` ...). Trials come from
    ``session.yaml`` (``type: static`` entries skipped), restricted to those
    present under this iteration.

    Roles:
      * navigation — ``.path``, ``.trials``, ``.trial(name)``
      * analysis — ``scale_model``, session-wide EMG normalisation, CEINMS
        calibration, ``plot_summary``, and the ``run()`` orchestrator
        (export -> external biomechanics -> SO -> CEINMS).

    Usually obtained from a :class:`Session` rather than built directly::

        s  = Session(r"...\\simulations\\Athlete_03\\25_03_31")
        it = s.iteration("gpk_mri")
        it.run(trials=["Squat_BW_01", "Walking_02"],
               do_exbiomec=True, do_so=True, do_ceinms=True, replace=True)
    """

    def __init__(self, session_dir, iteration):
        self.session_dir = os.path.abspath(session_dir)
        self.iteration = iteration
        self.name = os.path.basename(self.session_dir)      # session id, e.g. "25_03_31"
        self._cfg = self._read_yaml(os.path.join(self.session_dir, "session.yaml"))
        self._setup_dir = self._resolve_setup_dir()

    @staticmethod
    def _read_yaml(path):
        if not os.path.exists(path):
            return {}
        try:
            import yaml
        except Exception:
            return {}
        # Duplicate keys are checked on the TEXT: by the time the loader has
        # run they are gone — yaml.safe_load keeps the last value in silence,
        # which is how a generated file with `Voltage_1:` twice calibrated on
        # the wrong data without a word (IMPLEMENTATIONS §1).
        try:
            from bioscout.devtools import run_check as _rc
            with open(path, "r", encoding="utf-8", errors="replace") as _fh:
                _dups = _rc.duplicate_yaml_keys(_fh.read())
            for _k, _a, _b in _dups:
                print(f"[session.yaml WARNING] {path}: duplicate key {_k!r} "
                      f"(lines {_a} and {_b}) — YAML silently keeps line {_b} "
                      f"and DISCARDS line {_a}. Fix the file.")
        except Exception:                                      # noqa: BLE001
            pass
        return normalise_iterations(load_session_yaml(path), path)

    def _resolve_setup_dir(self):
        """Absolute path to the shared OpenSim setup templates (setup_JRA.xml ...).

        First folder that EXISTS, in order: settings SETUP_DIR / SETUP_FILES;
        that path with the pre-3.x name ``setupFiles`` swapped for
        ``setup_files``; the project's own ``setup_folder`` from session.yaml,
        then ``<project>/setup_files`` and ``<project>/setupFiles``; bioscout's
        bundled ``setup_files/``. The existence check is the fix
        (2026-09-11): bioscout 3.x renamed setupFiles/ -> setup_files/ while
        settings.py still named the old folder, so every trial got a setup_dir
        that did not exist and the JRA stage died on a missing setup_JRA.xml
        after IK/ID/MA/SO had all succeeded.
        """
        cands = []
        try:
            from bioscout import utils as _u
            s = getattr(_u, "settings", None)
            for obj in (getattr(s, "BatchSettings", None), s):
                v = getattr(obj, "SETUP_DIR", None) or getattr(obj, "SETUP_FILES", None)
                if v:
                    cands.append(str(v))
                    cands.append(os.path.join(os.path.dirname(str(v)), "setup_files"))
        except Exception:
            pass
        try:
            root = self._project_dir()
        except Exception:
            root = None
        if root:
            sf = (getattr(self, "_cfg", None) or {}).get("setup_folder")
            if sf:
                cands.append(str(sf) if os.path.isabs(str(sf))
                             else os.path.join(root, str(sf)))
            cands += [os.path.join(root, "setup_files"), os.path.join(root, "setupFiles")]
        cands.append(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "setup_files"))
        for c in cands:
            if c and os.path.isdir(c):
                return os.path.abspath(c)
        return None

    # -- navigation ---------------------------------------------------------
    @property
    def path(self):
        return _layout.iteration_path(self.session_dir, self.iteration)

    @property
    def tag(self):
        """``<session>/<iteration>`` -- the prefix of every log line."""
        return f"{self.name}/{self.iteration}"

    def __repr__(self):
        return f"<Iteration {self.subject_name}/{self.tag}  model_scaled={os.path.basename(str(self._rel('model_scaled')))}>"

    def describe(self, log=print, trials=None):
        """Print this iteration: its session.yaml keys (model files resolved,
        found or MISSING) and which stage outputs each trial has on disk
        (``trials``: restrict the table; ``[]`` leaves it out)."""
        cfg = self.config
        log(f"iteration {self.iteration!r}  ({self.subject_name}/{self.name})   label={self.label!r}"
            f"   {self.source()}")                     # clickable: its block in session.yaml
        rows = [(k, cfg.get(k), getattr(self, k)) for k in ITERATION_FILE_KEYS]
        if self.mvic_factor != 1.0 and self.model_so:
            rows.append(("model_so", f"(model_scaled x {self.mvic_factor:g})", self.model_so))
        for key, rel, path in rows:
            if not rel:
                continue
            ok = bool(path) and os.path.exists(str(path))
            try:                              # shown project-relative when inside it
                where = os.path.relpath(str(path), self._project_dir())
                where = str(path) if where.startswith("..") else "<project>/" + where
            except ValueError:                # other drive (Windows)
                where = str(path)
            log(f"  {key:<14}: {'ok     ' if ok else 'MISSING'}  {where.replace(os.sep, '/')}")
        if not cfg.get("model_generic"):
            log(f"  {'model_generic':<14}: -        (model_scaled is given, not scaled here)")
        if not cfg.get("markerset"):
            log(f"  {'markerset':<14}: -        (the generic model's own markers)")
        rec = [f"static_trial={self.static_trial}",
               f"linear_scaling={self.linear_scaling}", f"marker_placer={self.marker_placer}",
               f"muscle_opt={self.muscle_opt}" + (f" (opt_neval={self.opt_neval})" if self.muscle_opt else ""),
               f"mvic_factor={self.mvic_factor:g}"]
        log("  scaling       : " + ", ".join(rec))
        if self.marker_aliases:
            log(f"  marker_aliases: {len(self.marker_aliases)}")
        try:
            emg = self.emg_map
        except ValueError as e:
            emg = f"ERROR: {e}"
        log(f"  ceinms        : calibrated={self.calibrated}"
            + (f", calibration={self.calibration}" if self.calibration else "")
            + (f", emg_map={emg}" if emg else ""))
        rows = {} if trials == [] else self.stage_status(trials)
        if rows:
            stages = list(next(iter(rows.values())))
            w = max(len(t) for t in rows)
            log(f"  trials        : {len(rows)}   " + "  ".join(stages))
            for tn, st in rows.items():
                log(f"    {tn:<{w}}  " + "  ".join(("x" if st[k] else ".").center(len(k))
                                                  for k in stages))
        return None

    def stage_status(self, trials=None):
        """``{trial: {stage: bool}}`` -- which stage outputs exist on disk
        (the same check ``run()`` reports at the end, devtools.run_check)."""
        from bioscout.devtools.run_check import verify_run, STAGE_OUTPUTS
        rep = verify_run(self.path, list(trials or self._trial_names()),
                         list(STAGE_OUTPUTS),
                         experimental_dir=os.path.dirname(
                             experimental_dir(self.session_dir, "_")))
        return rep["trials"]

    def _trial_names(self):
        """Non-static trials for this iteration.

        session.yaml is the source of truth, so a configured trial counts even
        when its folder does not exist yet — export creates it on demand. That
        keeps a project from having to carry thousands of empty placeholder
        directories just to be enumerable. Falls back to what is on disk when
        session.yaml lists no trials (legacy sessions with only
        trial_settings.xml).
        """
        trials_cfg = (self._cfg.get("trials") or {})
        out = [tr for tr, meta in trials_cfg.items()
               if str((meta or {}).get("type", "")).lower() != "static"]
        if out:
            return out
        if not os.path.isdir(self.path):
            return []
        return sorted(d for d in os.listdir(self.path)
                      if os.path.isdir(os.path.join(self.path, d))
                      and (os.path.exists(os.path.join(self.path, d, "trial_settings.xml"))
                           or os.path.isdir(os.path.join(self.path, d, "inputs"))))

    def trial(self, name, force_type="SO"):
        """Return an Analyse for one trial, with shared experimental inputs bound.

        Raw inputs (markers/grf/emg/GRF.xml) live once in
        ``<session>/experimental/<trial>/`` and are shared by every iteration.
        Setting ``experimental_dir`` makes Analyse redirect them there on every
        settings reload; derived outputs still write under this iteration's own
        trial folder."""
        _tp = os.path.join(self.path, name)
        # session.yaml is the trial list, so a configured trial may have no folder
        # yet (see _trial_names). Create it on demand — Analyse chdir's into it.
        if not os.path.isdir(_tp):
            try:
                from bioscout import utils as _u
                _auto = getattr(_u.settings.BatchSettings, 'auto_create_dirs', True)
            except Exception:
                _auto = True
            if _auto:
                os.makedirs(_tp, exist_ok=True)
        t = Analyse(_tp)
        t.experimental_dir = experimental_dir(self.session_dir, name)
        if self._setup_dir:
            t._session_setup_dir = self._setup_dir
        # EMG-only normalisation trials never produce iteration outputs — they
        # only feed the session MVC maximum from experimental/. Suppress the
        # output-stage scaffolding for them and prune anything the Analyse
        # constructor already created, so 20+ MVIC captures do not each leave
        # an empty {external_biomechanics, ceinms, ...} tree per iteration
        # (reported 2026-08-17, FAIS 022).
        _norm_only = (name in set(normalisation_trial_names(self._cfg))
                      and name not in set(calibration_trial_names(self._cfg)))
        t._scaffold_output_dirs = not _norm_only
        t._apply_inputs_layout()
        self._apply_session_config(t, name, force_type)     # session.yaml is the source of truth
        if _norm_only:
            try:
                from bioscout.core.analysis import LAYOUT_DIRS as _LD
                os.chdir(self.session_dir)          # cannot rmdir the cwd on Windows
                for _d in _LD.values():
                    _p2 = os.path.join(_tp, _d)
                    if os.path.isdir(_p2) and not os.listdir(_p2):
                        os.rmdir(_p2)
                if os.path.isdir(_tp) and not os.listdir(_tp):
                    os.rmdir(_tp)
            except OSError:
                pass
        return t

    def get_trial(self, name, force_type="SO"):
        """The Analyse (trial) object for the session trial ``name`` — explicit
        alias for :meth:`trial`::

            a = Session(session_path).iteration("gpk_mri").get_trial("Walking_02")
            a.run_ik(); a.plot_jra_comparison()
        """
        return self.trial(name, force_type=force_type)

    def plot_summary(self, trials=None, dofs=None, figures=None, **opts):
        """Regenerate the per-trial summary figures for this iteration's trials
        from data already on disk (no re-solve):

          * ``kinematics_moments.png``     — plot_kin_mom_summary (IK angles + ID moments)
          * ``summary``                    — plot_summary (angles + SO/CEINMS muscle moments)
          * ``JRA_SO_vs_CEINMS.png``       — plot_jra_comparison (joint contact forces)

        Defaults come from ``settings.SummarySettings`` (dofs, analysis_leg,
        algorithms, joints, ...). ``figures`` selects which to make — any of
        ``{"kin_mom", "summary", "jra"}`` (default: kin_mom + jra). ``trials``
        defaults to every trial in this iteration. Extra ``SummarySettings``
        keywords are accepted and ignored where they only apply to the
        cross-model overlay figure (that multi-model comparison is
        ``summary_figures.py`` / a future session-level overlay).

            it = Session(session_path).iteration("gpk_mri")
            it.plot_summary(trials=["Walking_03", "Squat_BW_01", "Squat_BW_02"])
        """
        from bioscout import utils as _u
        ss = getattr(getattr(_u, "settings", None), "SummarySettings", None)
        if dofs is None and ss is not None:
            dofs = list(getattr(ss, "dofs", []) or []) or None
        if figures is None:
            figures = getattr(ss, "figures", None) or ("kin_mom", "jra")
        figs = {str(x).lower() for x in figures}
        trial_names = ([trials] if isinstance(trials, str)
                 else list(trials)) if trials else self._trial_names()
        made = []
        for tn in trial_names:
            try:
                t = self.trial(tn)
                os.chdir(t.path)
                if figs & {"kin_mom", "kinematics", "kin_mom_summary"}:
                    try:
                        t.plot_kin_mom_summary(dofs=dofs)
                    except Exception as e:
                        print(f"[Session] {self.tag}/{tn} kin_mom: {e}")
                if "summary" in figs:
                    try:
                        t.plot_summary()
                    except Exception as e:
                        print(f"[Session] {self.tag}/{tn} summary: {e}")
                if figs & {"jra", "jcf"}:
                    try:
                        t.plot_jra_comparison()
                    except Exception as e:
                        print(f"[Session] {self.tag}/{tn} jra: {e}")
                made.append(tn)
                print(f"[Session] {self.tag}: plotted {tn}")
            except Exception as e:
                print(f"[Session] {self.tag}: plot failed for {tn}: {e}")
        return made

    def resolve_model_file(self, mfile):
        """Find a configured model file. -> absolute path or None.

        Search order (2026-08-17 — models used to HAVE to be copied into every
        iteration folder, so the same scaled model existed 3x per subject):
          1. an absolute path, as given
          2. relative to THIS iteration folder        (the classic location)
          3. relative to the session folder            (explicit ../ paths)
          4. the project models library, in order:
             ``<project>/<mfile>`` verbatim (project-relative paths),
             ``models/personalised/<subject>/<name>``,
             ``models/generic/<name>`` and one level of family subfolders,
             ``models/<name>`` (flat legacy layout, kept working)
        A session.yaml can therefore keep just the filename and store the model
        once in the project's models/ folder, shared by every session and
        iteration of that subject.
        """
        if not mfile:
            return None
        if os.path.isabs(mfile):
            return mfile if os.path.exists(mfile) else None
        for base in (self.path, self.session_dir):
            p = os.path.normpath(os.path.join(base, mfile))
            if os.path.exists(p):
                return p
        try:
            from bioscout import utils as _u
            roots = [getattr(_u, "PROJECT_DIR", None)]
        except Exception:
            roots = []
        # session assumed at <project>/simulations/<subject>/<session>
        roots.append(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(self.session_dir)))))
        subject = os.path.basename(os.path.dirname(
            os.path.abspath(self.session_dir)))
        name = os.path.basename(mfile)
        for root in roots:
            if not root:
                continue
            root = str(root)
            # 4a. A project-relative path, verbatim — session.yaml can say
            #     models/personalised/021/021_Rajagopal2015_FAI.osim and mean
            #     exactly that, whichever session reads it.
            p = os.path.normpath(os.path.join(root, mfile))
            if os.path.exists(p):
                return p
            # 4b. Bare filename against the ORGANISED library:
            #     personalised/<subject>/ first (a subject model belongs to a
            #     subject), then generic/ and one level of family subfolders
            #     (generic/Rajagopal_FAIS/, generic/Catelli/, ...), then the
            #     flat legacy models/ root last so old projects keep working.
            # personalised/<subject>/<session>/ first (the scaled model belongs
            # to the session that built it), then the flat personalised/<subject>/
            # for anything scaled before 2026-08-31.
            _sess = os.path.basename(os.path.abspath(self.session_dir))
            candidates = [
                os.path.join(root, "models", "personalised", subject, _sess, name),
                os.path.join(root, "models", "personalised", subject, name),
                os.path.join(root, "models", "generic", name),
            ]
            gen_dir = os.path.join(root, "models", "generic")
            if os.path.isdir(gen_dir):
                try:
                    for fam in sorted(os.listdir(gen_dir)):
                        candidates.append(os.path.join(gen_dir, fam, name))
                except OSError:
                    pass
            candidates.append(os.path.join(root, "models", name))
            for p in candidates:
                if os.path.exists(p):
                    return p
        return None

    def trial_config(self, name, force_type="SO"):
        """FULL config for one (trial, iteration) from session.yaml.

        ``side`` / ``time_range`` / ``trial_type`` from ``trials.<name>``;
        ``body_mass`` session-wide; ``emg_map`` (resolved), CEINMS weights and
        calibration flattened as ``ceinms_*`` / ``calibration_*``; the model
        file as ``model_scaled`` (absolute path, the same name as in
        session.yaml). Which model a trial loads: :meth:`model_file`.
        """
        meta = (self._cfg.get("trials") or {}).get(name) or {}
        ce = (self._cfg.get("ceinms") or {})
        cfg = {}
        tr = meta.get("time_range")
        if isinstance(tr, (list, tuple)) and len(tr) == 2:
            try:
                cfg["time_range"] = [float(tr[0]), float(tr[1])]
            except Exception:
                pass
        if meta.get("side") is not None:
            cfg["side"] = str(meta["side"])
            # FAIS patch 2026-08-12: session.yaml's `side` is the LOADED limb,
            # and that is the limb the per-trial figures should show. But
            # plot_kin_mom_summary reads `analysis_leg`, which only ever came
            # from trial_settings.xml (disabled here) or the project-wide
            # SummarySettings default of "both" — so every single-leg squat was
            # plotted with both legs. Derive it from `side`; "both" stays both.
            _s = cfg["side"].strip().lower()
            if _s.startswith(("r", "l")):
                cfg["analysis_leg"] = _s[0]
        if meta.get("type") is not None:
            cfg["trial_type"] = str(meta["type"])
        if self._cfg.get("body_mass") is not None:
            cfg["body_mass"] = self._cfg["body_mass"]
        # Channel -> muscles for THIS session's electrode set. Sessions captured
        # months apart label and place channels differently, so the session file
        # outranks the project-wide settings.BatchSettings.emg_muscle_mapping.
        # A session may carry SEVERAL named maps (`emg_map: {narrow: {...}}`)
        # with each iteration naming the one it runs with — that is how three
        # electrode-grouping variants share one set of experimental inputs
        # instead of three copied sessions.
        try:
            _emn = emg_map_name_for(self._cfg, self.iteration)
        except ValueError as e:
            if self.iteration in _iteration_blocks(self._cfg):
                raise
            raise ValueError(
                f"{e} (iteration {self.iteration!r} is a folder on disk but is "
                "not declared in session.yaml, so it has no emg_map selector "
                "-- add it to `iterations:`)") from None
        if _emn is not None:
            # set even when the selected map is EMPTY: "this iteration has no
            # channels" must not silently fall back to the project-wide map.
            cfg["emg_map"] = resolve_emg_map(self._cfg, self.iteration)
            cfg["emg_map_name"] = _emn
        # CEINMS calibration bounds, same shape as emg_map: several named
        # configs with each iteration naming one, so a bound sweep becomes
        # iterations of one session rather than copied sessions plus a runtime
        # monkeypatch of settings.CEINMSSettings.
        _caln = None
        try:
            if iteration_is_calibrated(self._cfg, self.iteration):
                _caln = calibration_name_for(self._cfg, self.iteration)
        except ValueError as e:
            if self.iteration in _iteration_blocks(self._cfg):
                raise
            raise ValueError(
                f"{e} (iteration {self.iteration!r} is a folder on disk but is "
                "not declared in session.yaml, so it has no calibration "
                "selector -- add it to `iterations:`)") from None
        if _caln is not None:
            cfg["calibration_params"] = resolve_calibration(self._cfg,
                                                            self.iteration)
            cfg["calibration_name"] = _caln
        # Execution weights, and everything the CEINMS execution MODE needs.
        # `mode` is copied under the name `ceinms_mode`: a trial already has a
        # `mode` attribute in other contexts, and a silent collision here would
        # select the wrong execution strategy without raising.
        for k in ("alpha", "beta", "gamma"):
            if ce.get(k) is not None:
                cfg[k] = ce[k]
        if ce.get("mode") is not None:
            cfg["ceinms_mode"] = str(ce["mode"])
        # `calibrated: false` drives EXECUTION with the UNCALIBRATED subject
        # model (subjectUncalibrated.xml, written straight from the .osim).
        # Declared in session.yaml rather than passed at the call site so the
        # session that produced a result records which subject model made it --
        # the same reason `calibration:` and `emg_map` live there.
        if ce.get("calibrated") is not None:
            cfg["ceinms_calibrated"] = yaml_bool(ce["calibrated"])
        # ...and per ITERATION, so an uncalibrated CONTROL can sit in the same
        # session as the calibrated arms it is the control for. Session-level
        # `ceinms.calibrated` sets the default; the iteration overrides it. A
        # separate copied session for the control would reintroduce exactly the
        # drift `emg_map` and `calibration:` were moved into the file to end.
        _itb = _iteration_blocks(self._cfg).get(self.iteration) or {}
        if _itb.get("calibrated") is not None:
            cfg["ceinms_calibrated"] = yaml_bool(_itb["calibrated"])
        for k in ("gamma_bounds", "alpha_range", "beta_range", "gamma_range",
                  "lcurve_betas", "lcurve_gammas"):
            if ce.get(k) is not None:
                cfg[k] = ce[k]
        # The model, under its session.yaml name, as an absolute path. What a
        # trial LOADS depends on the force type: model_file().
        if _itb.get("model_scaled"):
            cfg["model_scaled"] = self.model_scaled
        if self._setup_dir:
            cfg["setup_dir"] = self._setup_dir
        return cfg

    def model_file(self, force_type="SO", trial=None):
        """The .osim a trial of this iteration loads (Analyse.model_dir).

        CEINMS: ``model_scaled`` as is. Everything else (IK, ID, MA, SO, mew,
        JRA): :attr:`model_so` -- the same geometry, max isometric force x
        ``mvic_factor``; built from ``model_scaled`` here if it is missing.
        None when the iteration names no model."""
        m = self.model_scaled
        if not m:
            print(f"[Session] {self.tag}: [warn] no model_scaled in session.yaml "
                  f"(iterations.{self.iteration}) for {trial or force_type}")
            return None
        if not os.path.exists(m):
            print(f"[Session] {self.tag}: [warn] model_scaled not found: {m} "
                  f"(iterations.{self.iteration}.model_scaled = "
                  f"{self.config.get('model_scaled')!r}, relative to {self.path}). "
                  f"Scale first: it.scale_model()")
            return m
        if str(force_type).upper().startswith("C"):
            return m
        return self._ensure_model_so()

    def _ensure_model_so(self):
        """Write :attr:`model_so` from ``model_scaled`` when it is missing or older."""
        so, m = self.model_so, self.model_scaled
        if so == m or (os.path.exists(so) and os.path.getmtime(so) >= os.path.getmtime(m)):
            return so
        from bioscout.model.edit.osim_ops import increase_isometric_force
        import shutil
        increase_isometric_force(m, muscleList="all", factor=self.mvic_factor)
        produced = m.replace(".osim", f"_increased_{self.mvic_factor:.2f}.osim")
        if os.path.exists(produced) and os.path.abspath(produced) != os.path.abspath(so):
            shutil.move(produced, so)
        print(f"[Session] {self.tag}: SO model = model_scaled x {self.mvic_factor:g} "
              f"-> {os.path.basename(so)}")
        return so

    def _apply_session_config(self, t, name, force_type="SO"):
        """Inject session.yaml config onto the Analyse as authoritative overrides
        (_overrides), plus pin + persist the analysis window."""
        cfg = self.trial_config(name, force_type)
        # Analyse knows ONE model, as `model_dir`; the yaml names stay out of it.
        ov = {k: v for k, v in cfg.items() if k != "model_scaled"}
        _m = self.model_file(force_type, trial=name)
        if _m:
            ov["model_dir"] = _m
        t._overrides = ov
        for k, v in ov.items():
            setattr(t, k, v)
        tr = cfg.get("time_range")
        if isinstance(tr, (list, tuple)) and len(tr) == 2:
            t0, t1 = float(tr[0]), float(tr[1])
            # window authority now comes from _overrides (get_time_range reads it)
            try:
                t.update_trial_attribute("start_time", f"{t0:.4f}")
                t.update_trial_attribute("end_time", f"{t1:.4f}")
            except Exception:
                t.start_time, t.end_time = f"{t0:.4f}", f"{t1:.4f}"

    @property
    def trials(self):
        return [self.trial(n) for n in self._trial_names()]

    @property
    def iterations(self):
        """Model-iteration folders configured for this session (session.yaml)."""
        return list((self._cfg.get("iterations") or {}).keys())

    # -- analysis / orchestration -----------------------------------------
    def _project_dir(self):
        """Project root: session.yaml's ``project_dir`` (relative to the session
        folder), else 3 levels above it (simulations/<subject>/<session>)."""
        pd = self._cfg.get("project_dir")
        if pd:
            return os.path.abspath(os.path.join(self.session_dir, str(pd)))
        return os.path.abspath(os.path.join(self.session_dir, os.pardir, os.pardir, os.pardir))

    # -- CEINMS / EMG / model-scaling (single-iteration operations) --------
    # These operate on THIS iteration's own folder (self.path) and its shared
    # experimental/ inputs. They used to live on a combined god-class; they are
    # Iteration methods now (the pipeline in run()/scale_model() calls them
    # directly — no session_layout indirection).
    @property
    def calibration_trials(self):
        """CEINMS calibration trial names (settings.CEINMSSettings) present here."""
        from bioscout import utils
        cs = getattr(getattr(utils, "settings", None), "CEINMSSettings", None)
        names = getattr(cs, "calibration_trial_names", None) or []
        here = set(self._trial_names())
        return [n for n in names if n in here]

    def _resolve_calibration_trials(self):
        """Calibration trial folders for THIS session: settings names matched to
        real folders (case-insensitive); falls back to squats, then all trials."""
        here = self._trial_names()
        lower = {t.lower(): t for t in here}
        from bioscout import utils
        cs = getattr(getattr(utils, "settings", None), "CEINMSSettings", None)
        wanted = list(getattr(cs, "calibration_trial_names", None) or [])
        matched = [lower[w.lower()] for w in wanted if w.lower() in lower]
        if matched:
            return matched
        if wanted:
            print(f"[Session] {self.tag}: calibration trials {wanted} not found; falling back.")
        squats = [t for t in here if "squat" in t.lower()]
        return squats or here

    def ingest_c3d(self, source=None, dry_run=False, trials=None):
        """Distribute loose ``*.c3d`` into per-trial ``<trial>/inputs/c3dfile.c3d``
        under this iteration. ``source`` defaults to the session folder. ``trials``
        (name or list) restricts distribution to those c3d (matched by file stem), so
        only the selected trials' folders are touched; default: every loose ``*.c3d``."""
        import shutil
        from .layout import c3d_root as _c3d_root
        src = source or self.session_dir
        _tset = ({trials} if isinstance(trials, str) else set(trials)) if trials else None
        # In the session-centric layout the c3d already lives at its canonical
        # address, 1_c3dfiles/<trial>.c3d, and the trial reads it from there.
        # Copying it into <iteration>/<trial>/inputs/ is pure duplication.
        try:
            _canon = _c3d_root(self.session_dir)
        except Exception:
            _canon = None
        made = []
        for c in sorted(glob.glob(os.path.join(src, "*.c3d"))):
            stem = os.path.splitext(os.path.basename(c))[0]
            if _tset is not None and stem not in _tset:
                continue
            if _canon and os.path.isfile(os.path.join(_canon, stem + ".c3d")):
                continue                      # already canonical — do not copy
            dst = os.path.join(self.path, stem, "inputs", "c3dfile.c3d")
            if os.path.exists(dst):
                continue
            made.append(stem)
            if dry_run:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(c, dst)
        if made:
            print(f"[Session] {self.tag}: "
                  f"{'would ingest' if dry_run else 'ingested'} "
                  f"{len(made)} c3d -> trial folders")
        return made

    def run_emg_normalise(self, replace=None, write_trials=None):
        """Session-wide EMG normalisation. The per-channel session-max (MVC-style)
        reference is computed across ALL of the session's trials; then each written
        trial's inputs/emg_filtered_normalised.mot is scaled into [0, 1]. ``write_trials``
        (name or list) restricts which trials have their normalised file (re)written
        and their ``replace`` flag touched — the MVC reference STILL spans every trial.
        Default: write all."""
        from bioscout import utils as _u
        _wset = ({write_trials} if isinstance(write_trials, str)
                 else set(write_trials)) if write_trials else None
        envelopes = {}
        for t in self.trials:
            try:
                env = t._emg_envelope()
            except Exception as e:
                print(f"[Session] {self.tag}: EMG envelope failed for "
                      f"{os.path.basename(t.path)}: {e}")
                env = None
            if env is not None:
                envelopes[t] = env
        if not envelopes:
            print(f"[Session] {self.tag}: no EMG to normalise.")
            return []
        chans = set()
        for env in envelopes.values():
            chans |= {c for c in env.columns if c != 'time'}

        # -- VALIDATE the emg_map against the labels that actually exist.
        # The FAIS trap: every electrode exported twice (bare Voltage_N + the
        # conditioned Voltage_N-VM); a map keyed on the bare names normalised
        # and CALIBRATED CEINMS on the raw columns without one warning. A
        # mapped channel that exists nowhere is a hard refusal — normalising
        # would silently produce nothing for it; a bare name shadowed by a
        # tagged sibling is a loud warning, because only the rig's owner
        # knows which column is the signal.
        try:
            from bioscout.devtools import run_check as _rc
        except Exception:                                      # noqa: BLE001
            _rc = None
        if _rc is not None:
            try:
                _map = resolve_emg_map(self._cfg,
                                       getattr(self, "iteration", None),
                                       strict=False) or {}
            except Exception:                                  # noqa: BLE001
                _map = {}
            if _map:
                _v = _rc.validate_emg_map(_map.keys(), chans)
                for _bare, _tag in _v["suspicious"]:
                    print(f"[Session] {self.tag}: EMG MAP WARNING — map "
                          f"keys {_bare!r} but the recording also has "
                          f"{_tag!r}; if the tagged column is the "
                          f"conditioned signal, the map normalises the RAW "
                          f"one. Check session.yaml's emg_map.")
                if _v["missing"]:
                    raise RuntimeError(
                        f"emg_map channels not present in any trial's EMG: "
                        f"{_v['missing']} — available: {sorted(chans)[:12]}"
                        f"{'...' if len(chans) > 12 else ''}. Fix "
                        f"session.yaml's emg_map; refusing to normalise "
                        f"against columns that do not exist.")
        session_max, session_max_trial = {}, {}
        for c in chans:
            best_m, best_t = 0.0, None
            for t, env in envelopes.items():
                if c in env:
                    m = float(env[c].max())
                    if m > best_m:
                        best_m, best_t = m, os.path.basename(t.path)
            session_max[c] = best_m if best_m > 1e-9 else 1.0
            session_max_trial[c] = best_t
        done = []
        chans_sorted = sorted(chans)      # canonical EMG order for CEINMS
        # session.yaml `emg_gain`, applied AFTER the session-max division --
        # scaling the RAW signal would be an exact no-op (see resolve_emg_gain).
        # Raises on a channel name that is not in the data.
        gains = resolve_emg_gain(self._cfg, channels=chans)
        if gains:
            print(f"[Session] {self.tag}: emg_gain "
                  + ", ".join(f"{c} x{g:g}" for c, g in sorted(gains.items())))
        for t, env in envelopes.items():
            if _wset is not None and os.path.basename(t.path) not in _wset:
                continue                  # reference-only: feeds session-max, not (re)written
            if replace is not None:
                t.update_trial_attribute("replace", replace)
            out = env[['time']].copy()
            for c in chans_sorted:
                if c in env:
                    out[c] = (env[c] / session_max[c]).clip(0.0, 1.0)
                    g = gains.get(c, 1.0)
                    if g != 1.0:
                        # clipped again: CEINMS only accepts [0, 1], and a gain
                        # above 1 would otherwise hand it excitations > 1.
                        out[c] = (out[c] * g).clip(0.0, 1.0)
            try:
                _exc_rel = t.emg_filtered_normalised
                _exc_abs = os.path.join(t.path, _exc_rel)
                os.makedirs(os.path.dirname(_exc_abs), exist_ok=True)
                _u.emg_normalise.write_sto_file(out, _exc_abs)
                t.update_trial_attribute('ceinms_excitations', _exc_rel)
                done.append(t)
            except Exception as e:
                print(f"[Session] {self.tag}: EMG normalise failed for "
                      f"{os.path.basename(t.path)}: {e}")
        print(f"[Session] {self.tag}: wrote emg_filtered_normalised.mot for "
              f"{len(done)} trials (session-max normalised, [0,1]).")
        for t in done:
            try:
                if os.environ.get("BIOSCOUT_QC_PLOTS", "1").strip().lower() not in ("0", "false", "off", "no"):   # BIOSCOUT_QC_PLOTS=0 skips the per-trial png
                    t.plot_emg_processing(norm_source=session_max_trial)
            except Exception as e:
                print(f"[Session] EMG figure failed for {os.path.basename(t.path)}: {e}")
        return done

    # clean alias
    def normalise_emg(self, replace=None, write_trials=None):
        return self.run_emg_normalise(replace=replace, write_trials=write_trials)

    def run_ceinms_calibration(self, replace=None, prefer_trial=None):
        """Calibrate CEINMS once for THIS session, driven off the first
        calibration trial (dynamic, never the static trial)."""
        names = self._resolve_calibration_trials()
        here = self._trial_names()
        if prefer_trial and prefer_trial in here:
            names = [prefer_trial] + [n for n in names if n != prefer_trial]
        names = [n for n in names if n in here]
        if not names:
            print(f"[Session] {self.tag}: no calibration trials to calibrate.")
            return None
        host = self.trial(names[0], force_type="CEINMS")
        if host is None:
            print(f"[Session] {self.tag}: could not load calibration trial {names[0]!r}.")
            return None
        if replace is not None:
            host.update_trial_attribute("replace", replace)
        print(f"[Session] {self.tag}: CEINMS calibration (driver={names[0]}, trials={names})")
        return host.run_ceinms_calibration()

    def calibrate(self, replace=None, calibration_trials=None):
        """Calibrate CEINMS for THIS session (settings names, or explicit ones)."""
        names = list(calibration_trials) if calibration_trials else self._resolve_calibration_trials()
        if not names:
            print(f"[Session] {self.tag}: no calibration trials found.")
            return None
        from bioscout import utils
        cs = getattr(getattr(utils, "settings", None), "CEINMSSettings", None)
        old = getattr(cs, "calibration_trial_names", None) if cs is not None else None
        try:
            if cs is not None:
                cs.calibration_trial_names = names
            print(f"[Session] {self.tag}: calibrating CEINMS on {names}")
            return self.run_ceinms_calibration(replace=replace, prefer_trial=names[0])
        finally:
            if cs is not None:
                cs.calibration_trial_names = old

    def prepare_ceinms(self, replace=None, calibration_trials=None):
        """Session EMG normalisation, then CEINMS calibration. ``calibration_trials``
        restricts which trials the calibration objective uses (e.g. walking-only
        when you'll execute on walking); default = settings.CEINMSSettings."""
        self.normalise_emg(replace=replace)
        return self.calibrate(replace=replace, calibration_trials=calibration_trials)

    def prepare_uncalibrated_ceinms(self, replace=None, host_trial=None):
        """Everything CEINMS execution needs EXCEPT a calibration.

        Calibration produces three things execution depends on: the session's
        normalised EMG, the excitation generator, and a subject XML. An
        UNCALIBRATED run still needs the first two -- excitations are what
        execution solves against, calibrated or not. The third is the
        uncalibrated subject: optimal fibre lengths, tendon slack lengths,
        pennation angles and max isometric forces exactly as the OpenSim model
        states them, nothing fitted.

        This builds those three and stops. No calibration executable runs, so
        an uncalibrated arm costs execution time only.

        -> the uncalibrated subject XML path, or None.
        """
        self.normalise_emg(replace=replace)
        here = self._trial_names()
        order = ([host_trial] if host_trial else []) \
            + list(self._resolve_calibration_trials() or []) + here
        names = [n for n in order if n in here]
        if not names:
            print(f"[Session] {self.tag}: no trials to build an uncalibrated "
                  f"CEINMS model from.")
            return None
        host = self.trial(names[0], force_type="CEINMS")
        if host is None:
            print(f"[Session] {self.tag}: could not load {names[0]!r}.")
            return None
        if replace is not None:
            host.update_trial_attribute("replace", replace)
        print(f"[Session] {self.tag}: building UNCALIBRATED CEINMS subject "
              f"model (driver={names[0]})")
        host.create_ceinms_model()
        host.create_excitation_generator()
        return host.ceinms_uncalibrated_model

    # -- model scaling ------------------------------------------------------
    def _resolve_model_file(self, rel, key="so_model", quiet=False):
        """Resolve a session.yaml path through the one shared rule.

        ``key`` selects the base order (see :mod:`bioscout.session.paths`).
        It matters: a markerset is a project asset and a model is searched from
        the iteration folder outward. Everything used to go through the model
        search, so ``markerset: setup_files/markers_FAIS.xml`` resolved
        correctly only because that search's last fallback happened to be the
        project root — right answer, wrong reason, and no way to tell.

        Unresolvable values are returned unchanged, as before, so a caller that
        wants to raise its own error still can.
        """
        if not rel:
            return None
        from bioscout import utils as _u
        from bioscout.session.paths import resolve as _resolve_path
        md = str(getattr(_u, "MODELS_DIR", "") or "")
        # session.yaml's project_dir, else <project>/simulations/<subject>/<session>
        # when that layout is there, else the bootstrapped project
        _own = self._project_dir()
        pd = (_own if (self._cfg.get("project_dir")
                       or os.path.isdir(os.path.join(_own, "simulations"))) else
              str(getattr(_u, "PROJECT_DIR", None)
                  or (os.path.dirname(md) if md else _own)))
        got = _resolve_path(key, rel, session_dir=self.session_dir, project_dir=pd,
                            iteration_dir=iteration_dir(self.session_dir, self.iteration))
        note = None if quiet else got.note()
        if note:
            print(f"[paths] {note}")
        return str(got) if got.ok else rel

    @property
    def subject_name(self):
        """This session's subject id — the folder above the session."""
        return os.path.basename(os.path.dirname(os.path.abspath(self.session_dir)))

    @property
    def session_name(self):
        """This session's id — the session folder itself."""
        return os.path.basename(os.path.abspath(self.session_dir))

    def models_dir(self, create=False):
        """Where THIS session's personalised models are written and read:
        ``<project>/models/personalised/<subject>/<session>/``.

        The anatomy does not change between a morning and an afternoon
        session, but the SCALED MODEL does: it is built from that session's
        static trial and its marker set, so two sessions of one subject
        produce two different ``<generic>_scaled.osim``. Sharing one
        ``personalised/<subject>/`` folder between them meant the second
        session silently overwrote the first, and neither session could be
        re-analysed afterwards without rescaling.

        Kept from the 2026-08-19 change: models still live in the models tree
        rather than scattered through ``3_iterations/``, which is what made
        them impossible to find. Only the subject folder gained a session
        level underneath it.

        Backwards compatible on READ: if the session folder does not exist yet
        but the flat ``personalised/<subject>/`` does and holds models, that
        one is returned, so sessions scaled before this change keep working
        until they are next rescaled. ``create=True`` always makes and returns
        the session folder.
        """
        from bioscout import utils as _u
        md = (os.path.join(self._project_dir(), "models") if self._cfg.get("project_dir")
              else str(getattr(_u, "MODELS_DIR", "") or ""))
        if not md:
            pd = str(getattr(_u, "PROJECT_DIR", None) or os.getcwd())
            md = os.path.join(pd, "models")
        flat = os.path.join(md, "personalised", self.subject_name)
        out = os.path.join(flat, self.session_name)
        if create:
            os.makedirs(out, exist_ok=True)
            return out
        if not os.path.isdir(out) and os.path.isdir(flat):
            try:
                if any(f.lower().endswith(".osim") for f in os.listdir(flat)):
                    return flat
            except OSError:
                pass
        return out

    def model_output_path(self, name, default_stem=None, create=True):
        """Absolute path to WRITE a model named ``name`` to.

        The mirror of :meth:`_resolve_model_file` (which finds a model to
        READ), so a model lands exactly where session.yaml says it will be
        looked for:

        * absolute path            -> used as given
        * contains a separator     -> project-relative, e.g.
          ``models/personalised/023/023_Rajagopal2015_FAI.osim``
        * bare filename            -> ``models/personalised/<subject>/``

        The bare-filename case is the one that changed: it used to mean the
        iteration folder.
        """
        if not name:
            name = default_stem or "scaled.osim"
        name = str(name)
        if os.path.isabs(name):
            return name
        if os.sep in name or "/" in name:
            from bioscout import utils as _u
            md = str(getattr(_u, "MODELS_DIR", "") or "")
            pd = str(getattr(_u, "PROJECT_DIR", None)
                     or (os.path.dirname(md) if md else os.getcwd()))
            return os.path.abspath(os.path.join(pd, name))
        return os.path.join(self.models_dir(create=create), name)

    def link_geometry(self, generic_model_path, name="Geometry", dest_dir=None):
        """Link the generic model's ``Geometry/`` beside the scaled model.

        A scaled .osim keeps the generic's relative mesh references
        (``r_femur.vtp`` ...), but it is written into the iteration folder,
        which has no ``Geometry/``. OpenSim's GUI then loads the model with no
        bones and no muscle paths — "Couldn't find file 'r_femur.vtp'" — and
        the model looks broken when it is fine.

        A LINK, not a copy: the mesh set is tens of megabytes and identical for
        every iteration and every subject that shares the generic, so copying
        it would multiply it across the whole simulations tree. On Windows this
        is a directory JUNCTION, which needs no elevation and no developer
        mode, unlike a true symlink. Never fails the scaling — if the link
        cannot be made, it says so and moves on, because a missing mesh affects
        only what you can SEE, never what is computed.

        Returns the link path, or None.
        """
        if not generic_model_path:
            return None
        src_geo = os.path.join(os.path.dirname(os.path.abspath(generic_model_path)), name)
        if not os.path.isdir(src_geo):
            # Some model families keep the meshes one level up, shared by
            # several .osim in sibling folders.
            _up = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(generic_model_path))), name)
            if os.path.isdir(_up):
                src_geo = _up
            else:
                return None
        dst = os.path.join(dest_dir or self.path, name)
        if os.path.isdir(dst) or os.path.islink(dst):
            return dst                      # already linked (or a real folder)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(src_geo, dst)
            else:
                os.symlink(src_geo, dst, target_is_directory=True)
            print(f"[Session] {self.tag}: linked {name}/ -> {src_geo}")
            return dst
        except Exception as e:
            print(f"[Session] {self.tag}: could not link {name}/ "
                  f"({type(e).__name__}: {e}). The model still runs; the GUI "
                  f"will show it without bones. Link it by hand with:\n"
                  f'    mklink /J "{dst}" "{src_geo}"')
            return None

    def scale_model(self, static_trial=None, n_eval=None,
                    mass=None, replace=True, muscle_opt=None, marker_placer=None,
                    linear_scaling=None):
        """Build THIS iteration's ONE scaled model, driven by session.yaml.

        Pipeline (each keyword overrides the matching ``session.yaml`` value)::

            generic + static  --ScaleTool-->  scaled.osim
                                   (MarkerPlacer registers markers to the static
                                    pose; dimensional scaling only if linear_scaling)
                              --Modenese2015 muscle-opt-->  scaled_opt_N<n>.osim   (= CEINMS model)
                              -> model_scaled   (CEINMS uses it as is)
                              --isometric force x mvic_factor-->  model_so (SO, derived)

        No ``model_generic`` in the iteration means ``model_scaled`` is a given
        (MRI/TPS) model: nothing is scaled, only the SO copy is written.

        Parameters
        ----------
        static_trial : str, optional
            Name of the static trial whose markers drive scaling/registration.
            Read from the SHARED ``experimental/<static_trial>/marker_experimental.trc``.
            Defaults to session.yaml's ``static_trial:`` — NOT to a hardcoded
            name. It used to default to ``"Static_01"``, so a session whose
            static trial is called anything else (``static1``, the FAIS
            convention) scaled against a trial that does not exist: "static
            TRC not found", no model, and every downstream stage failing for
            every trial, with the session file naming the right trial all
            along.
        n_eval : int, optional
            Number of Modenese2015 muscle-optimisation evaluations. Defaults to
            this iteration's ``opt_neval`` in session.yaml (or 10). Ignored when
            ``muscle_opt=False``.
        mass : float, optional
            Target total body mass (kg) for ScaleTool. Defaults to session.yaml
            ``body_mass``.
        replace : bool
            If False and both output models already exist, skip and return the SO
            model path. If True, rebuild.
        muscle_opt : bool, optional
            True  -> run the (slow, minutes) Modenese2015 muscle-parameter
                     optimisation, producing ``<subject>_scaled_opt_N<n>.osim``
                     as the force model. Needed for SO/CEINMS.
            False -> stop after the scaled model and use it directly as the
                     force model (keeps the generic's OFL/TSL — right for a
                     validated MRI/personalised model). Fast; enough for
                     external biomechanics (IK/ID/MA).
            Defaults to this iteration's ``muscle_opt:`` in session.yaml
            (True when absent), so "this model is not re-fit" is recorded with
            the model rather than retyped at every call site.
        marker_placer : bool, optional
            Override ScaleTool's MarkerPlacer stage. Default: session.yaml
            ``marker_placer`` (else False).
        linear_scaling : bool, optional
            Override dimensional (segment) scaling. Default: session.yaml
            ``linear_scaling`` (else True). Set False to keep MRI segment geometry.

        Returns
        -------
        str or None
            Absolute path to the SO model (``it.model_so``; ``None`` if the
            generic/static is missing). ``model_scaled`` is written where
            session.yaml says (relative to the iteration folder); unset, it goes
            to ``models/personalised/<subject>/<session>/<iteration>_scaled.osim``
            and the line to add is printed. A different ``mvic_factor`` is a
            different iteration (session.add_iteration)."""
        import shutil
        from bioscout.model.edit.osim_ops import increase_isometric_force
        from bioscout.model.muscle_optimize import muscle_optimimizer_Modenese2015
        from bioscout.model.scale.osim_scale import scale_model
        # session.yaml owns the static trial's NAME (see the parameter docs).
        if not static_trial:
            static_trial = str(self.static_trial or "Static_01")
        it = self.config
        mvic_factor = self.mvic_factor
        if not it.get("model_generic"):
            m = self.model_scaled
            if m and os.path.exists(m):
                print(f"[Session] {self.tag}: no model_generic -- model_scaled is used as "
                      f"given ({self.relpath(m)}); nothing to scale.")
                return self._ensure_model_so()
            print(f"[Session] [ERROR] {self.tag}: iterations.{self.iteration} has no "
                  f"model_generic to scale, and model_scaled "
                  f"{it.get('model_scaled')!r} does not exist.")
            return None
        generic = self.model_generic
        if not os.path.exists(generic):
            print(f"[Session] [ERROR] {self.tag}: model_generic not found: {generic} "
                  f"({it.get('model_generic')!r}, relative to {self.path}) — nothing "
                  f"downstream can run.")
            return None
        trc = os.path.join(experimental_dir(self.session_dir, static_trial),
                           "marker_experimental.trc")
        if not os.path.exists(trc):
            try:
                self.trial(static_trial).export_c3d()
            except Exception as e:
                print(f"[Session] {self.tag}: static export failed: {e}")
        if not os.path.exists(trc):
            print(f"[Session] [ERROR] {self.tag}: static TRC not found: {trc}\n"
                  f"[Session]         Export the static trial FIRST — it is usually "
                  f"absent from the analysis trial list:\n"
                  f"[Session]         Session.export(trials=['{static_trial}'] + TRIALS, "
                  f"export_src=<abs 1_c3dfiles>)\n"
                  f"[Session]         Without a scaled model, IK/MA/SO/CEINMS will all "
                  f"fail for every trial.")
            return None

        # The marker set belongs to the model it scales (GPK_v3 is lower-limb
        # only, so pyCGM's torso markers reference a body it does not have):
        # iterations.<name>.markerset. A session-level one is moved in with a
        # warning when session.yaml is read (config.normalise_iterations).
        markerset = self.markerset
        if it.get("markerset") and not markerset:
            print(f"[Session] [ERROR] {self.tag}: markerset not found: "
                  f"{it.get('markerset')!r}")
            return None
        linear = bool(it.get("linear_scaling", True) if linear_scaling is None else linear_scaling)
        mplace = bool(it.get("marker_placer", False) if marker_placer is None else marker_placer)
        # Modenese2015 muscle optimisation is the slow step (minutes per
        # subject), and it is a MODELLING decision, not a run-time one: whether
        # this iteration's force model is re-fit to the generic's muscle-tendon
        # operating ranges, or keeps what the generic carries. So it reads from
        # session.yaml like its siblings above (`muscle_opt: false`), with the
        # keyword still overriding for a one-off.
        muscle_opt = bool(it.get("muscle_opt", True) if muscle_opt is None
                          else muscle_opt)
        n_eval = int(n_eval if n_eval is not None else (it.get("opt_neval", 10) or 10))
        if mass is None:
            mass = self._cfg.get("body_mass")
            # The force plates measured this subject on this day. Prefer that over a
            # typed-in body_mass, which drifts (Athlete_03: 89.9 typed vs 91.0
            # measured) and silently biases every mass-normalised result. Opt out
            # with `body_mass_from_grf: false` in session.yaml.
            if self._cfg.get("body_mass_from_grf", True):
                try:
                    from bioscout.model.scale import measurements as _sm
                    _grf = os.path.join(experimental_dir(self.session_dir, static_trial),
                                        "grf.mot")
                    _m = _sm.mass_from_static_grf(_grf, verbose=False)
                except Exception:
                    _m = None
                if _m:
                    if mass and abs(_m - float(mass)) > 0.05:
                        print(f"[Session] {self.tag}: body mass from the static GRF is "
                              f"{_m:.2f} kg; session.yaml says {float(mass):.2f} kg. "
                              f"Using the measured value.")
                    mass = _m

        # Everything this method writes goes to models/personalised/<subject>/,
        # which is where session.yaml already says the models are (see
        # models_dir / model_output_path). Until 2026-08-19 they were written
        # into the ITERATION folder while session.yaml named
        # models/personalised/<subject>/... — so scaling "succeeded", the run
        # then could not find the model it had just built, and the loud
        # no-model-found warning fired for every trial.
        _mdir = self.models_dir(create=True)
        os.makedirs(self.path, exist_ok=True)
        # The intermediate ScaleTool output is subject-prefixed: a subject's
        # sessions share one models folder, and a bare "scaled.osim" from
        # `pre` would be silently overwritten by `post`.
        scaled = os.path.join(_mdir, f"{self.subject_name}_scaled.osim")

        # THE output: session.yaml's model_scaled (relative to the iteration
        # folder), or a default beside the session's other models.
        target = self.model_scaled
        if not target:
            target = os.path.join(_mdir, f"{self.iteration}_scaled.osim")
            print(f"[Session] {self.tag}: no model_scaled in session.yaml -- writing "
                  f"{target}. Add under iterations.{self.iteration}:\n"
                  f"    model_scaled: {self.relpath(target)}")
        _stem, _ext = os.path.splitext(target)
        so_path = target if mvic_factor == 1.0 else f"{_stem}_mvicx{mvic_factor:.2f}{_ext}"
        if os.path.exists(target) and os.path.exists(so_path) and not replace:
            print(f"[Session] {self.tag}: model exists: {self.relpath(target)} (replace=True rebuilds)")
            return so_path

        # 1) ScaleTool -> scaled.osim (marker registration; dimensional scaling only
        #    if linear_scaling).
        print(f"[Session] {self.tag}: scale {os.path.basename(generic)} "
              f"(linear_scaling={linear}, marker_placer={mplace}) + static '{static_trial}'")
        # Make the meshes reachable from the folder the scaled model is
        # written to, before anything tries to open it. The iteration folder
        # is linked too: older models still sit there, and OpenSim resolves
        # meshes relative to whichever .osim is opened.
        self.link_geometry(generic, dest_dir=_mdir)
        self.link_geometry(generic)
        # The ScaleTool setup XML travels WITH the model it produced rather
        # than staying in the iteration folder — it is the record of how that
        # .osim was made, and it is what "View setup XML" should find beside it.
        # Marker names this lab spells differently, from session.yaml. The
        # iteration's own map wins over the session-wide one. Without it a lab
        # that does not use the Vicon-CGM spellings gets NO joint centre and
        # almost no measurements -- ScaleTool then scales every body by 1.0 and
        # returns generic geometry wearing the subject's mass, which nothing
        # downstream can detect. `bioscout scale` works the map out by asking.
        _aliases = self.marker_aliases
        if _aliases:
            print(f"[Session] {self.tag}: marker aliases from session.yaml: "
                  + ", ".join(f"{k}->{v}" for k, v in sorted(_aliases.items())))

        scale_model(generic, trc, scaled, scale_setup_output_dir=_mdir,
                    mass=(float(mass) if mass else None), marker_set_file=markerset,
                    linear_scaling=linear, marker_placer=mplace,
                    marker_aliases=_aliases or None)

        # Name the model after what it IS. OpenSim's ScaleTool names its output
        # after the tool, and openSim.scale_model calls the tool "ModelScaling",
        # so every scaled model in every project ends up as
        # <Model name="ModelScaling">. Load two in the GUI to compare and the
        # Navigator shows the same word twice. The linear_scaling=False branch is
        # no better: it copies the generic through, so all subjects inherit the
        # generic's name instead. Rewrite the attribute on the written file, which
        # covers both branches and the marker-placer pass.
        #
        # Cosmetic ONLY - nothing reads this name. It appears in a couple of log
        # lines and in the Navigator; JRA_COLUMNS keys off the SUBJECT, not the
        # model name. Failure here must never sink a scaling run, hence the
        # blanket except.
        try:
            import re as _re
            _mname = "%s_scaled_%s_%s" % (
                os.path.splitext(os.path.basename(generic))[0],
                os.path.basename(os.path.dirname(self.session_dir)),
                os.path.basename(self.session_dir))
            # BYTES, not text. These models are CRLF; text mode would turn
            # every CRLF into LF on read and write them back as LF, so a
            # 33-character rename would also rewrite ~15000 line endings and
            # shrink the file by ~15 kB. surrogateescape round-trips anything
            # the decoder dislikes, so only the name attribute changes.
            with open(scaled, "rb") as _fh:
                _txt = _fh.read().decode("utf-8", "surrogateescape")
            _txt, _n = _re.subn(r'(<Model\s+name=")([^"]*)(")',
                               lambda m: m.group(1) + _mname + m.group(3),
                               _txt, count=1)
            if _n:
                with open(scaled, "wb") as _fh:
                    _fh.write(_txt.encode("utf-8", "surrogateescape"))
                print("[Session] %s: model named '%s'" % (self.tag, _mname))
        except Exception as _e:
            print("[Session] %s: [WARNING] could not name the scaled model: %s"
                  % (self.tag, _e))

        # 2) Force model = Modenese2015 muscle-opt output, OR (muscle_opt=False) the
        #    marker-registered scaled.osim itself — use the latter when the generic
        #    already carries personalised muscle-tendon parameters (validated MRI
        #    model), so its OFL/TSL are kept instead of being re-fit to a reference.
        if muscle_opt:
            print(f"[Session] {self.tag}: muscle optimisation (Modenese2015, N={n_eval}) — slow ...")
            base = os.path.join(
                _mdir, f"{self.subject_name}_scaled_opt_N{n_eval}.osim")
            muscle_optimimizer_Modenese2015(scaled, save_path=base,
                                            ref_model_path=generic, N_eval=n_eval)
        else:
            base = scaled
            print(f"[Session] {self.tag}: muscle-opt skipped — "
                  f"{os.path.basename(scaled)} is the force model "
                  f"(generic's muscle-tendon params kept).")

        # 3) model_scaled = base. Before the isometric boost, so it is never boosted.
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.abspath(target) != os.path.abspath(base):
            shutil.copyfile(base, target)

        # 4) SO model = model_scaled with isometric force x mvic_factor, beside it.
        #    increase_isometric_force writes <target>_increased_X.osim.
        if mvic_factor != 1.0:
            increase_isometric_force(target, muscleList="all", factor=mvic_factor)
            produced = target.replace(".osim", f"_increased_{mvic_factor:.2f}.osim")
            if os.path.exists(produced) and os.path.abspath(produced) != os.path.abspath(so_path):
                shutil.move(produced, so_path)

        print(f"[Session] {self.tag}: model_scaled -> {os.path.abspath(target)}")
        if so_path != target:
            print(f"[Session] {self.tag}: model_so (x{mvic_factor:.2f}) -> {os.path.abspath(so_path)}")
        return so_path

    def export_trials(self, trials=None, export_src=None, *,
                      replace=False, normalise=True, detect=True, log=print):
        """Model-INDEPENDENT c3d export for this session's trials: ingest loose c3d ->
        markers/GRF/EMG into the SHARED ``experimental/<trial>/`` folder, filter EMG,
        then (``normalise``) run the session-wide EMG normalise. The raw inputs are
        shared by every iteration, so this writes ONCE regardless of which iteration
        anchors it — prefer :meth:`Session.export` over per-iteration ``run(export=True)``.

        ``detect`` (default True) then runs movement detection over what was just
        exported, writing ``movement_detection.yaml`` and ``movement_detection.png``
        into each trial folder, beside the data they describe. It reads the markers
        and GRF the export just wrote, so this is the moment where it is cheapest —
        and it never touches ``session.yaml``: a disagreement is reported, not
        applied. Set ``detect=False`` to skip it. Returns the list of trials
        exported."""
        names = ([trials] if isinstance(trials, str)
                 else list(trials)) if trials else self._trial_names()
        if export_src:
            self.ingest_c3d(source=export_src, trials=names)
        done = []
        import time as _time
        _t_all = _time.time()
        for tn in names:
            _t_one = _time.time()
            try:
                t = self.trial(tn)
                t.export_c3d()
                # export_c3d writes into the SHARED 2_experimental/<trial>/, so
                # the ITERATION's own trial folder need not exist yet — and for
                # a trial that has never been analysed it does not. chdir into a
                # missing folder raised WinError 2 and the whole export of that
                # trial was reported as failed, on a session where nothing was
                # actually wrong. Create the bare folder (no stage scaffolding —
                # the stages make their own).
                os.makedirs(t.path, exist_ok=True)
                os.chdir(t.path)
                tr = t.get_time_range()
                if tr:
                    t.time_range = tr
                    t.update_trial_attribute('time_range', tr)
                try:
                    t.run_emg_filter()
                except Exception as ee:
                    log(f"  [export] EMG filter warn {tn}: {ee}")
                done.append(tn)
                log(f"  [export ok] {tn}  ({_time.time() - _t_one:.1f} s)")
            except Exception as e:
                log(f"  [export ERROR] {tn}: {e}")
        _dt = _time.time() - _t_all
        log(f"  [export] {len(done)}/{len(names)} trial(s) in "
            f"{int(_dt // 60)}m{int(_dt % 60):02d}s "
            f"({_dt / max(len(names), 1):.1f} s/trial)")
        if normalise:
            try:
                self.run_emg_normalise(replace=replace, write_trials=names)
            except Exception as e:
                log(f"  [emg normalise ERROR]: {e}")
        if detect and done:
            # Weigh the participant BEFORE classifying. The detector's force
            # thresholds are in body weights; with body_mass unset it falls back
            # to a fraction of peak, which is weaker. The static trial has only
            # just been exported, so this is the first moment the plates can be
            # read — and the last moment before anything needs the number.
            try:
                import yaml as _y
                _yp = os.path.join(self.session_dir, "session.yaml")
                _c = _y.safe_load(open(_yp, encoding="utf-8")) or {}
                if _c.get("body_mass") in (None, "", 0):
                    _m = body_mass_from_static(self.session_dir,
                                               _c.get("static_trial"))
                    if _m:
                        _c["body_mass"] = _m
                        _ORDER = ["subject", "session", "static_trial", "body_mass"]
                        _o = {_k: _c[_k] for _k in _ORDER if _k in _c}
                        _o.update({_k: _v for _k, _v in _c.items() if _k not in _o})
                        with open(_yp, "w", encoding="utf-8") as _fh:
                            _y.safe_dump(_o, _fh, sort_keys=False, allow_unicode=True)
                        log(f"  [export] body_mass was unset -> {_m} kg "
                            f"(weighed on the plates, not entered)")
                    else:
                        log("  [export] body_mass unset and not measurable from "
                            "the static trial — detection thresholds will be "
                            "relative, not in body weights.")
            except Exception as e:
                log(f"  [export] body_mass warn: {type(e).__name__}: {e}")
            # Movement detection is part of the export, not a separate command
            # you have to remember to run: it needs exactly the markers and GRF
            # that were just written, and its answer belongs in the trial folder
            # next to them. A failure here warns — the export itself succeeded
            # and the pipeline can run without a classification.
            try:
                os.chdir(self.session_dir)      # the loop above chdir'd into a trial
            except Exception:
                pass
            try:
                from bioscout.session.movement_detector.session import classify_session
                classify_session(self.session_dir, per_trial=True, quiet=True)
            except Exception as e:
                log(f"  [detect WARN] movement detection skipped: "
                    f"{type(e).__name__}: {e}")
        return done

    def run(self, trials=None,
            export=False, export_src=None, *,
            detect=True,
            do_scale=False,
            do_exbiomec=False,
            do_muscle_analysis=False,
            do_so=False,
            do_mew=False,
            do_ceinms=False,
            calibrate=False, calibration_trials=None,
            replace=False,
            mew_opts=None,
            log=print, **_ignored):
        """Run the pipeline for THIS iteration.

        Stages (each optional, run in this order):
          do_scale    : build this iteration's scaled models first (delegates to
                        :meth:`scale_model`, reading session.yaml). Does not need
                        trials. Use when you want scale + analysis in one call.
          export      : (re)build inputs from c3d + refresh window + filter EMG,
                        then session-wide EMG normalise, then movement detection
                        into each ``2_experimental/<trial>/`` (``detect=False``
                        skips that last part). ``export_src`` first distributes
                        loose ``*.c3d`` into each trial's inputs/.
          do_exbiomec : external biomechanics only (IK -> ID). Muscle Analysis
                        is its own stage — see ``do_muscle_analysis``.
          do_muscle_analysis : Muscle Analysis (muscle lengths + moment arms).
                        Required by ``do_so``; when do_so runs without it, any
                        missing MA output is filled in without overwriting.
          do_so       : SO stage (SO -> muscle moments -> JRA), needs IK/ID/MA.
          do_mew      : mew (bioscout.simulate.mew, the Python muscle solver)
                        -> JRA, into ``<trial>/mew/``. Needs IK/ID/MA and the SO
                        force file (its residual/reserve columns balance the
                        JRA); missing prerequisites are filled, never
                        overwritten. ``mew_opts`` is passed to
                        :func:`bioscout.simulate.mew.analyse_trial` (``tier``,
                        ``smoothing``, ``filter_hz``, ``jcf``, ``plot``).
          do_ceinms   : CEINMS calibration (once) + per-trial execution -> JRA.

        ``replace`` overwrites existing outputs. ``trials`` defaults to all trials.
        ``calibrate`` (default True) — when do_ceinms is on, calibrate once first;
        set ``calibrate=False`` to SKIP calibration and run only execution -> JRA
        against the existing ``ceinms_calibration/subjectCalibrated.xml``.

        ``ceinms: {calibrated: false}`` in session.yaml overrides both: the
        iteration executes against ``subjectUncalibrated.xml`` (built straight
        from the .osim, nothing fitted), no calibration runs whatever
        ``calibrate`` says, and every execution folder is tagged ``_uncal`` so
        it cannot be mistaken for — or overwrite — a calibrated result. The same
        key on an ITERATION overrides the session-wide one, so an uncalibrated
        control can live beside the calibrated arms it is the control for.

        Unknown keyword arguments are ignored (forward-compat). Returns a dict
        of trials that completed each stage.
        """

        # `skip_done` was accepted for years but never read — the skip/reuse
        # decision is a per-stage MTIME question (each gate logs its own
        # reason, e.g. the CEINMS prep "muscle lengths newer than the model"
        # check), not a run-level flag. A documented parameter that silently
        # does nothing is a silent failure of its own, so say so.
        # Any other unknown stage flag (`do_muscle_analyser=True`, a typo) used
        # to vanish into **_ignored and the call returned having run nothing.
        _bad = sorted(k for k in _ignored if k.startswith("do_"))
        if _bad:
            log(f"  [run] WARNING: unknown stage flag(s) {_bad} IGNORED -- stages are "
                f"do_exbiomec, do_muscle_analysis, do_so, do_mew, do_ceinms "
                f"(plus export, do_scale)")
        if "skip_done" in _ignored:
            _ignored.pop("skip_done")
            log("  [run] note: `skip_done` is ignored — stages decide to skip "
                "on their own (existing/newer-than-model output) and log why; "
                "use replace=True to force a re-run.")
        if do_scale:
            try:
                self.scale_model(replace=replace)
            except Exception as e:
                log(f"  [scale ERROR] {self.tag}: {e}")
        # The analysis stages os.chdir() into each trial folder and never restore.
        # Capture the caller's cwd now and restore it on EVERY exit (finally at the
        # end) so a run never leaves the process cwd inside a trial dir — otherwise
        # a later relative path (e.g. Session("simulations/...")) resolves
        # against the trial folder and fails.
        _cwd0 = os.getcwd()
        try:                                    # start (and keep) the run quiet
            from bioscout.model.opensim_base import _quiet_osim
            _quiet_osim()
        except Exception:
            pass
        names = ([trials] if isinstance(trials, str)
                 else list(trials)) if trials else self._trial_names()
        res = {"export": [], "exbiomec": [], "muscle_analysis": [], "so": [],
               "mew": [], "ceinms": [], "skipped": []}
        log(f"=== {self.tag}  trials={names}  export={export} exbiomec={do_exbiomec} "
            f"ma={do_muscle_analysis} so={do_so} mew={do_mew} ceinms={do_ceinms} "
            f"replace={replace} ===")

        # -- Preflight: drop "ghost" trials with no raw experimental inputs. The
        # marker TRC is the fundamental input every stage (IK/ID/MA/SO/CEINMS)
        # depends on; without it there is nothing to run, and proceeding only
        # creates empty output folders and a garbage inputData.xml before failing.
        # The C3D export stage is exempt — it is what CREATES those inputs.
        if not export:
            _marker = _RAW_ATTR_FILES["markers"]
            _real = []
            for tn in names:
                if os.path.exists(os.path.join(experimental_dir(self.session_dir, tn), _marker)):
                    _real.append(tn)
                else:
                    res["skipped"].append(tn)
                    log(f"  [skip] {tn} — no experimental inputs "
                        f"({_marker} not found); nothing to run.")
            names = _real
            if not names:
                log("  [run] no trials with experimental inputs — nothing to do.")
                os.chdir(_cwd0)
                return res

        # -- Preflight: Windows MAX_PATH. Session trees + CEINMS execution
        # folder names blow past 260 chars at ~220-char roots, and the
        # failure surfaces as "file not found" deep inside OpenSim, hours in
        # (IMPLEMENTATIONS §1). Warn NOW, with the worst offenders named.
        if os.name == "nt":
            try:
                from bioscout.devtools import run_check as _rc
                _hits = _rc.long_paths(self.path)
                if _hits:
                    log(f"  [preflight WARNING] {len(_hits)}+ path(s) within "
                        f"~40 chars of the Windows 260-char limit — CEINMS "
                        f"execution folders WILL exceed it. Worst: "
                        f"({_hits[0][0]} chars) {_hits[0][1]}")
                    log("  [preflight] shorten the project root path or "
                        "enable Windows long paths.")
            except Exception:                                  # noqa: BLE001
                pass

        _itc = self.config
        _ce = (self._cfg.get("ceinms") or {})

        def _model_disp(force_type="SO"):
            """The .osim a stage will use, for the stage banner."""
            try:
                return self.model_file(force_type) or "(no model_scaled)"
            except Exception as e:                             # noqa: BLE001
                return f"(model: {e})"

        def _stage(title, **info):
            """Log a section header for a pipeline stage + the settings it uses."""
            log("")
            log("=" * 72)
            log(f"=== STAGE — {title}   [{self.tag}]")
            for k, v in info.items():
                if v not in (None, "", [], {}):
                    log(f"       {k}: {v}")
            log("=" * 72)

        if export:
            _stage("C3D export -> EMG filter -> session EMG normalise -> "
                   "movement detection", trials=names)
            res["export"] = self.export_trials(names, export_src=export_src,
                                               replace=replace, log=log,
                                               detect=detect)

        def _close_figs():
            """Drop every pyplot figure created by the last trial.

            pyplot keeps a global registry, so a figure that is savefig'd but
            never closed is retained for the life of the process. Ten plotting
            helpers in analysis/openSim/ceinms savefig without closing, and a
            full 6-iteration run writes ~1600 figures — measured at ~22 MB of
            retained memory each, i.e. gigabytes, which is what makes a long run
            crawl. Closing at the trial boundary bounds it regardless of which
            helper leaked. Figures stay usable after close; nothing in the batch
            path reads them back.
            """
            try:
                import matplotlib.pyplot as _plt
                _plt.close("all")
            except Exception:
                pass

        def _exbio(t, force=None):
            # ``force`` overrides ``replace``: prerequisite runs (before SO/CEINMS)
            # pass force=False so IK/ID are only computed when MISSING and are
            # reused otherwise — ``replace`` overwrites only the requested stage.
            from bioscout.core.analysis import Analyse
            _r = replace if force is None else force
            if not isinstance(t, Analyse):
                print(f"[Session] {self.tag}: _exbio expects an Analyse, got {type(t)}")
                return
                
            t.run_ik(replace=_r)
            _warn_frozen_ik(t)
            t.run_id(replace=_r)

        def _warn_frozen_ik(t):
            """Loud warning if IK produced near-static kinematics (broken marker
            registration / stale result) — else SO/CEINMS/JRA are garbage."""
            try:
                import numpy as _np
                p = os.path.join(t.path, "external_biomechanics", "joint_angles.mot")
                if not os.path.exists(p):
                    return
                L = open(p, errors="replace").read().splitlines()
                i = next(k for k, l in enumerate(L) if l.strip().lower() == "endheader")
                hdr = L[i + 1].split()
                d = _np.array([[float(x) for x in ln.split()] for ln in L[i + 2:]
                               if len(ln.split()) == len(hdr)])
                bad = {}
                for c in ("knee_angle_r", "hip_flexion_r", "knee_angle_l", "hip_flexion_l"):
                    if c in hdr:
                        v = d[:, hdr.index(c)]
                        rom = float(v.max() - v.min())
                        if rom < 5.0:
                            bad[c] = round(rom, 1)
                if bad:
                    log(f"  [WARN] {os.path.basename(t.path)}: IK looks FROZEN (ROM° {bad}) — "
                        f"kinematics broken; SO/CEINMS/JRA will be garbage. Re-run exbiomec / "
                        f"check marker registration for this model.")
            except Exception:
                pass

        def _log_inputs(tn, t, stage):
            """Indented per-trial line listing the input files/window for this stage,
            logged BEFORE the results."""
            def _b(attr):
                v = getattr(t, attr, None)
                return os.path.basename(str(v)) if v else "-"
            try:
                tr = t.get_time_range()
            except Exception:
                tr = None
            log(f"    [{tn}] inputs — model={_b('model_dir')}  markers={_b('markers')}  "
                f"grf={_b('setup_grf')}  time_range={tr}")

        if do_exbiomec:
            _stage("External biomechanics (IK -> ID)",
                   trials=names,
                   model=_model_disp("SO"))
            for tn in names:
                try:
                    log(f"  [exbiomec] {tn} — running (IK -> ID) ...")
                    _t = self.trial(tn)
                    _log_inputs(tn, _t, "exbiomec")
                    _exbio(_t)
                    res["exbiomec"].append(tn)
                    log(f"  [exbiomec ok] {tn}")
                    _close_figs()
                except Exception as e:
                    log(f"  [exbiomec ERROR] {tn}: {e}")

        if do_muscle_analysis:
            _stage("Muscle Analysis",
                   trials=names,
                   model=_model_disp("SO"))
            for tn in names:
                try:
                    log(f"  [MA] {tn} — running (Muscle Analysis) ...")
                    t = self.trial(tn)
                    _log_inputs(tn, t, "MA")
                    t.run_ma(replace=replace)
                    res["muscle_analysis"].append(tn)
                    # Say WHERE, per trial. The old line was just "[MA ok] <trial>",
                    # so a stage that wrote eight folders named none of them.
                    _ma_dir = os.path.abspath(os.path.join(t.path, t.ma))
                    log(f"  [MA ok] {tn} -> {_ma_dir}")
                    _close_figs()
                except Exception as e:
                    log(f"  [MA ERROR] {tn}: {e}")

        if do_so:
            _stage("Static Optimisation (SO -> muscle moments -> JRA)",
                   trials=names,
                   model=_model_disp("SO"))
            for tn in names:
                try:
                    log(f"  [SO] {tn} — running (SO -> muscle moments -> JRA) ...")
                    t = self.trial(tn)
                    _log_inputs(tn, t, "SO")
                    if not do_exbiomec:
                        _exbio(t, force=False)      # reuse existing IK/ID; only fill gaps
                    if not do_muscle_analysis:
                        # SO's muscle moments need moment arms, and exbiomec no
                        # longer produces them — fill the gap without overwriting.
                        t.run_ma(replace=False)
                    t.run_so(replace=replace)
                    t.calculate_muscle_moments(forces_type="so")
                    t.run_jra(replace=replace)
                    res["so"].append(tn)
                    log(f"  [SO ok] {tn}")
                    _close_figs()
                except Exception as e:
                    log(f"  [SO ERROR] {tn}: {e}")

        if do_mew:
            _stage("mew (Python muscle solver -> JRA)",
                   trials=names,
                   model=_model_disp("SO"),
                   opts=mew_opts)
            from bioscout.simulate.mew import analyse_trial as _mew
            for tn in names:
                try:
                    t = self.trial(tn)
                    _out = os.path.join(t.path, "mew", "JRA_ReactionLoads.sto")
                    if os.path.exists(_out) and not replace:
                        log(f"  [mew skip] {tn} -- {_out} exists (replace=True to re-run)")
                        res["mew"].append(tn)
                        continue
                    log(f"  [mew] {tn} -- running (solve -> JRA) ...")
                    _log_inputs(tn, t, "mew")
                    if not (do_exbiomec or do_so):
                        _exbio(t, force=False)          # reuse IK/ID; only fill gaps
                    if not (do_muscle_analysis or do_so):
                        t.run_ma(replace=False)         # moment arms + lengths
                    _so_f = os.path.join(t.path, "static_optimisation",
                                         "SO_StaticOptimization_force.sto")
                    if not os.path.exists(_so_f):
                        log(f"  [mew] {tn}: no SO force file -- running SO first "
                            f"(its residual/reserve columns balance the JRA)")
                        t.run_so(replace=False)
                    _cfg = self.trial_config(tn)
                    _o = dict(jcf=True, plot=True)
                    _o.update(mew_opts or {})
                    _r = _mew(t.path, t.model_dir,
                              mass=_cfg.get("body_mass"), **_o)
                    if _o.get("jcf") and _r.get("jcf_error"):
                        log(f"  [mew JRA ERROR] {tn}: {_r['jcf_error']}")
                    res["mew"].append(tn)
                    log(f"  [mew ok] {tn} -> {_r['out_dir']}")
                    _close_figs()
                except Exception as e:
                    log(f"  [mew ERROR] {tn}: {e}")

        if do_ceinms:
            try:
                # An UNCALIBRATED iteration has nothing to calibrate. `calibrate`
                # is forced off HERE rather than left to the caller because
                # calibrating and then executing against subjectUncalibrated.xml
                # would burn the calibration entirely -- ten minutes producing a
                # file nothing downstream reads, and a run that looks like a
                # calibrated one in every log.
                # the iteration's own flag wins over the session default
                _uncal = not yaml_bool(
                    _itc.get("calibrated", _ce.get("calibrated", True)))
                if _uncal:
                    if calibrate:
                        log("  [CEINMS] ceinms.calibrated=false — SKIPPING "
                            "calibration; execution uses the uncalibrated "
                            "subject model")
                    calibrate = False
                    _stage("CEINMS uncalibrated setup (session level)",
                           model=_model_disp("CEINMS"),
                           subject="subjectUncalibrated.xml")
                    self.prepare_uncalibrated_ceinms(replace=replace)
                if calibrate:
                    cal = (list(calibration_trials) if calibration_trials
                           else (self._resolve_calibration_trials() or []))
                    _stage("CEINMS calibration (session level)",
                           calibration_trials=cal, model=_model_disp("CEINMS"),
                           alpha=_ce.get("alpha"), beta=_ce.get("beta"), gamma=_ce.get("gamma"))
                    _prep_failed = []
                    for cn in cal:
                        try:
                            ct = self.trial(cn)
                            ma_len = os.path.join(ct.path, ct.ma, "_MuscleAnalysis_Length.sto")
                            # Recompute IK->ID->MA when the muscle-length file is MISSING
                            # or STALE. Never reuse a stale IK/ID that was solved over a
                            # DIFFERENT window than MA: the CEINMS inputData window then
                            # inherits the stale IK/ID span, which has no muscle-length
                            # data, and calibration dies SILENTLY (reads inputs, writes no
                            # subjectCalibrated.xml). Keep all three consistent over the
                            # trial's current window.
                            #
                            # Staleness is a MTIME question, not a flag question. Keying
                            # this off `replace` alone re-solved IK/ID/MA on every CEINMS
                            # run even when the stages earlier in the SAME run had just
                            # produced them -- identical output, minutes per iteration. The
                            # model is the thing MA is derived from, so compare against it.
                            _mdl = self.model_scaled or ""
                            _stale = (not os.path.exists(ma_len)) or (
                                os.path.exists(_mdl)
                                and os.path.getmtime(ma_len) < os.path.getmtime(_mdl))
                            if _stale and not CEINMS_AUTOPREP:
                                _why = ("missing" if not os.path.exists(ma_len)
                                        else "older than " + os.path.basename(_mdl))
                                log(f"  [CEINMS ERROR] calibration trial {cn}: "
                                    f"{os.path.basename(ma_len)} is {_why}. "
                                    f"do_ceinms does not solve IK/ID/MA -- run that "
                                    f"stage first:")
                                log(f"      it.run(trials=['{cn}'], do_exbiomec=True, "
                                    f"do_muscle_analysis=True)")
                                log(f"    (or set bioscout.session.iteration.CEINMS_AUTOPREP "
                                    f"= True to restore the old self-repairing behaviour)")
                                _prep_failed.append(cn)
                            elif _stale:
                                log(f"  [CEINMS prep] IK->ID->MA for calibration trial {cn}"
                                    f"  (CEINMS_AUTOPREP is on)")
                                ct.run_ik(replace=replace)
                                ct.run_id(replace=replace)
                                ct.run_ma(replace=replace)
                            else:
                                log(f"  [CEINMS prep] reusing IK/ID/MA for {cn} "
                                    f"(muscle lengths newer than the model)")
                        except Exception as e:
                            log(f"  [CEINMS prep ERROR] {cn}: {e}")
                    if _prep_failed:
                        # Calibrating on a trial whose inputs are stale is the
                        # silent-failure path this guard exists to close: it reads
                        # the inputs, writes no subjectCalibrated.xml, and the run
                        # continues against whatever calibration was there before.
                        raise RuntimeError(
                            "CEINMS calibration aborted: "
                            + ", ".join(_prep_failed)
                            + " lack usable IK/ID/MA. Run that stage first, or set "
                              "CEINMS_AUTOPREP = True.")
                    log(f"  [CEINMS] calibrating (trials={calibration_trials or cal}) — slow ...")
                    self.prepare_ceinms(replace=replace, calibration_trials=calibration_trials)
                elif _uncal:
                    _unc_subj = os.path.join(self.path, "ceinms_calibration",
                                             "subjectUncalibrated.xml")
                    if not os.path.exists(_unc_subj):
                        log(f"  [CEINMS ERROR] uncalibrated run but no subject at "
                            f"{_unc_subj}; the model could not be built from the .osim.")
                        os.chdir(_cwd0)
                        return res
                    log(f"  [CEINMS] executing against the UNCALIBRATED "
                        f"{os.path.basename(_unc_subj)} — output folders are tagged _uncal")
                else:
                    _cal_subj = os.path.join(self.path, "ceinms_calibration", "subjectCalibrated.xml")
                    if not os.path.exists(_cal_subj):
                        log(f"  [CEINMS ERROR] calibrate=False but no calibrated subject at {_cal_subj}; "
                            f"run once with calibrate=True first.")
                        os.chdir(_cwd0)
                        return res
                    log(f"  [CEINMS] skipping calibration; using existing {os.path.basename(_cal_subj)}")
                _stage("CEINMS execution (per trial -> muscle moments -> JRA)",
                       trials=names, model=_model_disp("CEINMS"),
                       alpha=_ce.get("alpha"), beta=_ce.get("beta"), gamma=_ce.get("gamma"),
                       calibrate=calibrate)
                for tn in names:
                    try:
                        log(f"  [CEINMS 6/6] {tn} — execution -> muscle moments -> JRA ...")
                        t = self.trial(tn, force_type="CEINMS")
                        t.run_ceinms_exe()
                        t.calculate_muscle_moments(forces_type="ceinms")
                        t.run_jra_ceinms(replace=replace)
                        res["ceinms"].append(tn)
                        log(f"  [CEINMS ok] {tn}")
                        _close_figs()
                    except Exception as e:
                        log(f"  [CEINMS ERROR] {tn}: {e}")
            except Exception as e:
                log(f"  [CEINMS calibration ERROR]: {e}")

        # -- VERIFY: did every requested stage actually produce output?
        # A run used to be able to end "[settings] done" with export failed on
        # every trial — the errors scrolled past and later stages just found
        # nothing to do (IMPLEMENTATIONS §1). The log says what was ATTEMPTED;
        # this says what EXISTS, per trial per stage, and the difference is
        # printed as a table that cannot scroll past unnoticed.
        try:
            from bioscout.devtools import run_check as _rc
            _req = [st for st, on in (("export", export),
                                      ("exbiomec", do_exbiomec),
                                      ("muscle_analysis", do_muscle_analysis),
                                      ("so", do_so), ("mew", do_mew),
                                      ("ceinms", do_ceinms))
                    if on]
            if _req and names:
                _rep = _rc.verify_run(
                    self.path, names, _req,
                    experimental_dir=os.path.join(self.session_dir,
                                                  "2_experimental"))
                log("  [verify] stage outputs on disk:")
                for _ln in _rc.format_report(_rep):
                    log("  " + _ln)
                _rc.write_report(_rep, os.path.join(self.path,
                                                    "run_report.json"))
                res["report"] = _rep
                res["ok"] = _rep["ok"]
                if not _rep["ok"]:
                    log(f"  [verify] RUN INCOMPLETE — {len(_rep['missing'])} "
                        f"trial-stage(s) produced no output (see "
                        f"run_report.json). Fix and re-run those stages.")
        except Exception as _ve:                               # noqa: BLE001
            log(f"  [verify] could not verify stage outputs: {_ve}")

        os.chdir(_cwd0)
        return res
