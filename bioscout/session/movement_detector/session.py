"""Run movement detection over a whole exported session.

One implementation, two callers: ``bioscout --classifier <session>`` and a
project pipeline that sets ``DO_DETECT``. They used to be the same code copied
twice, which is the sort of thing that agrees on the day it is written and
disagrees three commits later.
"""
from __future__ import annotations

import os
import sys


def _short_report(sess, mside, val_rows, disagree, det_dir, cycle_rows):
    """The default terminal output: one row per trial, then where the rest is.

        H3L/11_11_14  measured side: left
          trial      type     valid  why not
          Gehen_01   walking  NO     plate shared with the other foot; step spans two plates
          Gehen_03   walking  yes
          2 valid, 1 not valid  ->  <session>/movement_detection

    The full reason (times, forces) is in trials_valid.csv; ``--verbose``
    prints everything the detector did.
    """
    _name = "/".join(os.path.normpath(sess).split(os.sep)[-2:])
    _leg = {"l": "left", "r": "right"}.get(mside, "both legs")
    print(f"{_name}  measured side: {_leg}")
    _cj = {}
    for _c in cycle_rows:
        _cj.setdefault(_c.get("trial", ""), []).append(_c)
    _w = max([len("trial")] + [len(str(_r["trial"])) for _r in val_rows])
    _wt = max([len("type")] + [len(str(_r["type"])) for _r in val_rows])
    print(f"  {'trial':<{_w}}  {'type':<{_wt}}  valid  why not")
    for _r in val_rows:
        _why = ""
        if not _r["valid"]:
            _bits = []
            for _c in _cj.get(_r["trial"], []):
                for _flag, _txt in (("shared_plate", "plate shared with the other foot"),
                                    ("straddled", "step spans two plates"),
                                    ("cop_jump", "second foot landed on the plate")):
                    if _truthy(_c.get(_flag, False)) and _txt not in _bits:
                        _bits.append(_txt)
            _why = "; ".join(_bits) or str(_r["reason"]).split(" (")[0]
        print(f"  {_r['trial']:<{_w}}  {_r['type']:<{_wt}}  "
              f"{'yes' if _r['valid'] else 'NO ':<5}  {_why}".rstrip())
    for _d in disagree:
        print(f"  ! {_d['trial']}: detected {_d['detected']}, session.yaml says "
              f"{_d.get('session_yaml_type') or '(unset)'}")
    _nv = sum(1 for _r in val_rows if _r["valid"])
    print(f"  {_nv} valid, {len(val_rows) - _nv} not valid  ->  {det_dir}")


def _truthy(v) -> bool:
    """A flag that may have come back from a CSV as the string "False"."""
    return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "1", "yes")


def _plate_cop_jumps(exp_dir, body_mass, cfg, min_jump_m=0.10):
    """Moments where a LOADED plate's centre of pressure jumps in one frame.

    One foot rolls its CoP forward a few millimetres per frame. A jump of
    10 cm or more while the plate already carries real load means a second
    foot has just landed on it -- typically the previous foot's toes were
    still on the plate's edge. The contact detector splits a plate between
    feet only when each takes a clear turn; this catches the partial overlap
    it misses (Charite H3L Gehen_02: 193 N of the right forefoot on plate 2
    when the left heel lands, CoP jumps 15 cm in one frame).

    "Real load" is 10 % of body weight (at least 50 N), so the few newtons a
    plate reads before a clean heel strike do not count.
    Returns ``[{"plate", "t", "load_n", "jump_m"}]``.
    """
    import numpy as np
    from .mocap import read_grf
    try:
        t, cols = read_grf(os.path.join(exp_dir, "grf.mot"))
    except Exception:
        return []
    if not len(t):
        return []
    _v = str(getattr(cfg, "vertical_axis", "Y")).lower()[-1]
    _h = [_a for _a in "xyz" if _a != _v]
    try:
        _thr = max(50.0, 0.10 * float(body_mass) * 9.81)
    except (TypeError, ValueError):
        _thr = 50.0
    out = []
    for _c in cols:
        if not _c.endswith(f"_v{_v}"):
            continue
        pre = _c[:-3]
        try:
            f = np.abs(cols[_c])
            p = np.stack([cols[f"{pre}_p{_a}"] for _a in _h], axis=1)
        except KeyError:
            continue
        d = np.linalg.norm(np.diff(p, axis=0), axis=1)
        for k in np.flatnonzero((d >= min_jump_m) & (f[:-1] >= _thr)
                                & (f[1:] >= _thr)):
            out.append({"plate": pre, "t": round(float(t[k + 1]), 3),
                        "load_n": round(float(f[k]), 1),
                        "jump_m": round(float(d[k]), 3)})
    return out


def _trial_validity(rows, cycle_rows, measured_side="both"):
    """One row per trial: is it usable, and if not, why.

    ``valid`` is about the MEASUREMENT, not the movement:

    * a trial the detector could not type (``unknown``) is not valid;
    * a gait trial is valid when at least one stride was measured cleanly --
      its plate took that foot only (``shared_plate`` False), the step did
      not span two plates (``straddled`` False) and the centre of pressure
      did not jump under load (``cop_jump`` False). ``valid_left`` /
      ``valid_right`` say which leg that holds for, because a study of one
      limb needs that leg and not "any";
    * a gait trial with no stride on a plate at all is not valid;
    * anything else (static, squat, jump...) has no per-foot plate check and
      is valid as long as it was typed.

    ``measured_side`` ``"l"`` / ``"r"`` (session.yaml) makes the session about
    that leg alone: only its strides are looked at, ``valid`` is that leg's
    answer, and the other leg's column is left empty.

    Flag, not filter: nothing downstream skips a trial because of this file.
    """
    _want = {"l": "left", "r": "right"}.get(str(measured_side).lower())
    _gait = ("walking", "running", "cut")
    _by = {}
    for _c in cycle_rows:
        _by.setdefault(_c.get("trial", ""), []).append(_c)
    out = []
    for _r in rows:
        _t, _typ = _r.get("trial", ""), str(_r.get("detected", ""))
        _cs = [_c for _c in _by.get(_t, [])
               if not _want or str(_c.get("side", "")) == _want]
        _ok = {"left": False, "right": False}
        _why = []
        for _c in _cs:
            _sh, _st = _truthy(_c.get("shared_plate")), _truthy(_c.get("straddled"))
            _cj = _truthy(_c.get("cop_jump", False))
            _sd = str(_c.get("side", ""))
            if not _sh and not _st and not _cj:
                if _sd in _ok:
                    _ok[_sd] = True
                continue
            _p = [_x for _x, _f in (("plate shared with the other foot", _sh),
                                    ("step spans two plates", _st),
                                    ("a second foot landed on its plate ("
                                     + str(_c.get("cop_jump_note", "")) + ")", _cj))
                  if _f]
            _why.append(f"{_c.get('cycle', _sd)}: {' and '.join(_p)}")
        if _typ == "unknown" or not _typ:
            _valid, _reason = False, f"not classified ({_r.get('reason', '')})"
        elif _typ in _gait:
            _valid = _ok[_want] if _want else (_ok["left"] or _ok["right"])
            if not _cs:
                _reason = (f"no {_want} stride found on a force plate" if _want
                           else "no stride found on a force plate")
            elif _valid:
                _good = [_s for _s in ("left", "right") if _ok[_s]]
                _reason = ("clean plate contact: " + " and ".join(_good)
                           + ("; " + "; ".join(_why) if _why else ""))
            else:
                _reason = "; ".join(_why) or "no clean plate contact"
        else:
            _valid, _reason = True, f"{_typ}: no per-foot plate check"
        out.append({"trial": _t, "type": _typ,
                    "measured_side": str(measured_side).lower(),
                    "valid": bool(_valid),
                    "valid_left": (_ok["left"] if _typ in _gait
                                   and _want in (None, "left") else ""),
                    "valid_right": (_ok["right"] if _typ in _gait
                                    and _want in (None, "right") else ""),
                    "n_cycles": len(_cs), "reason": _reason})
    return out


def classify_session(session_path: str, settings=None, no_plots: bool = False,
                     write_session_yaml: bool = False, per_trial: bool = True,
                     quiet: bool = False, trials=None, verbose: bool = False):
    """Classify every trial in ``session_path`` and write the outputs.

    Per trial, beside the data it describes (``per_trial``, the default) —
    this is what the c3d export produces, so the detection travels with the
    trial and not in a folder somewhere else:

    * ``2_experimental/<trial>/movement_detection.yaml`` — type, confidence,
      reason, time_range, side and the task/phase breakdown for that trial
    * ``2_experimental/<trial>/movement_detection.png`` — its QC figure

    And once, beside the session:

    * ``movement_detection/movement_detection.yaml`` — every trial's
      detection and its ``valid`` flag in one file; never read by the
      pipeline and never overwriting ``session.yaml``
    * ``movement_detection/trials_valid.csv`` — trial, valid, reason
    * ``movement_detection/classification.csv`` — one row per trial, the
      only cross-trial view (which is why it stays session-level)
    * ``movement_detection/plots/<trial>.png`` — the old figure location,
      written only when ``per_trial=False``; the figures are not duplicated.

    ``settings`` is a project's ``BatchSettings`` (or anything with the same
    attribute names); it supplies the lab conventions — marker names and TRC
    axes. When omitted, the function looks for a ``settings.py`` above the
    session and falls back to the conventional defaults.

    ``write_session_yaml`` corrects ``session.yaml``'s trial types and time
    ranges from the detection and adds a ``valid`` tag per trial, backing the
    old file up first. A trial detected as "unknown" keeps its type. ``quiet`` trims the per-trial
    chatter to one summary line — the export already prints a line per trial.

    ``trials`` re-detects only the named trials. Every other trial keeps the
    result it already has, read back from its own
    ``movement_detection.yaml``, so the session-level files stay complete and
    a one-trial re-run costs one trial's work instead of the session's. Re-run
    one capture after changing a threshold, or after fixing the marker set,
    without waiting for the sixty that did not change.

    Returns the detection dict, or None when the session could not be read.
    """
    import csv as _csv
    import yaml as _yaml
    from bioscout.session.movement_detector import (classify_trial, segment_trial,
                                            gait_cycles, plot_trial_tasks,
                                            MocapConfig)

    # Three levels. `quiet` (called from an export): one summary line.
    # Default: a short table, one row per trial -- what you want on a terminal.
    # `verbose`: every convention, per-trial line and file written, as before.
    _noop = (lambda *_a, **_k: None)
    _say = print if (verbose and not quiet) else _noop
    _info = print if (verbose or quiet) else _noop

    _sess = os.path.abspath(session_path)
    if not os.path.isdir(_sess):
        print(f"[classifier] session folder not found: {_sess}"); return None

    _exp = None
    for _name in ("2_experimental", "experimental"):
        if os.path.isdir(os.path.join(_sess, _name)):
            _exp = os.path.join(_sess, _name); break
    if _exp is None:
        print(f"[classifier] no experimental folder under {_sess}\n"
              f"[classifier] export the session first: it needs "
              f"2_experimental/<trial>/marker_experimental.trc")
        return None

    _ypath = os.path.join(_sess, "session.yaml")
    _cfg = {}
    if os.path.isfile(_ypath):
        try:
            _cfg = _yaml.safe_load(open(_ypath, encoding="utf-8")) or {}
        except Exception as _e:
            print(f"[classifier] could not read session.yaml ({_e}); continuing")
    _mass = _cfg.get("body_mass")
    if _mass is None:
        print("[classifier] no body_mass in session.yaml — force thresholds fall "
              "back to a fraction of peak, which is less reliable.")

    # --- lab conventions come from the PROJECT, not from guesswork --------
    # A project already states its markerset, foot markers and TRC axes in
    # settings.py; the detector should read them rather than re-derive them
    # from marker names. Walk up from the session folder to find that file.
    # Absent or unreadable, the defaults are the conventional ones and the run
    # proceeds exactly as before.
    _mcfg, _mcfg_src = MocapConfig(), ""
    if settings is not None:
        _mcfg = MocapConfig.from_settings(settings)
        _mcfg_src = getattr(settings, '__name__', 'settings passed in')
    _probe = _sess if settings is None else None
    for _ in range(6 if _probe else 0):
        _cand = os.path.join(_probe, "settings.py")
        if os.path.isfile(_cand):
            try:
                import importlib.util as _ilu
                _spec = _ilu.spec_from_file_location("_bs_project_settings", _cand)
                _mod = _ilu.module_from_spec(_spec)
                _sys_path_added = os.path.dirname(_cand) not in sys.path
                if _sys_path_added:
                    sys.path.insert(0, os.path.dirname(_cand))
                _spec.loader.exec_module(_mod)
                _bs = getattr(_mod, "BatchSettings", None)
                if _bs is not None:
                    _mcfg = MocapConfig.from_settings(_bs)
                    _mcfg_src = _cand
            except Exception as _e:
                print(f"[classifier] settings.py found at {_cand} but not usable "
                      f"({type(_e).__name__}: {_e}); using default conventions")
            _mcfg_src = _mcfg_src or "<unusable>"
            break
        _up = os.path.dirname(_probe)
        if _up == _probe:
            break
        _probe = _up
    # session.yaml already says what this lab calls its markers
    # (`marker_aliases: {LASI: LASIS, ...}`, the same map scaling uses). With
    # no settings.py naming the pelvis, read it from there: otherwise a lab
    # that writes LASIS finds no pelvis, no speed, and every trial "unknown".
    from bioscout.session.config import measured_side_of as _msof
    _mside = _msof(_cfg)
    if _mside in ("l", "r"):
        _say(f"[classifier] measured_side: {_mside} -- strides and validity "
             f"for the {'left' if _mside == 'l' else 'right'} leg only")
    _al = _cfg.get("marker_aliases") or {}
    if not _mcfg.pelvis_markers and isinstance(_al, dict) and _al:
        _pm = [str(_al[_n]) for _n in ("LASI", "RASI", "LPSI", "RPSI", "SACR")
               if _al.get(_n)]
        if len(_pm) >= 2:
            _mcfg.pelvis_markers = tuple(_pm)
            _say(f"[classifier] pelvis markers from session.yaml "
                 f"marker_aliases: {', '.join(_pm)}")
    if _mcfg_src and _mcfg_src != "<unusable>":
        _fm = len(_mcfg.left_foot_markers or []) + len(_mcfg.right_foot_markers or [])
        _say(f"[classifier] conventions from {_mcfg_src}: "
              f"vertical={_mcfg.vertical_axis} ap={_mcfg.ap_axis} "
              f"lateral={_mcfg.lateral_axis}"
              + (f", {_fm} foot markers named" if _fm else ", foot markers by name"))
    elif _mcfg_src == "<unusable>":
        pass                       # already reported above
    else:
        _say("[classifier] no project settings.py found — using default "
              "conventions (vertical=Y, foot markers by name)")

    _trials = sorted(d for d in os.listdir(_exp)
                     if os.path.isdir(os.path.join(_exp, d)))
    _only = set(trials or ())
    _unknown = _only - set(_trials)
    if _unknown:
        print(f"[classifier] no such trial(s) under {_exp}: "
              f"{', '.join(sorted(_unknown))}")
    _todo = [_t for _t in _trials if not _only or _t in _only]
    if _only:
        _say(f"[classifier] re-detecting {len(_todo)} of {len(_trials)} "
             f"trial(s); the rest keep their existing movement_detection.yaml")
    # Everything this command produces lands together, beside the session it
    # describes, so the detection travels with the data rather than living in
    # whichever project happened to run it.
    _det = os.path.join(_sess, "movement_detection")
    _plots = os.path.join(_det, "plots")
    _do_plots = not no_plots
    _out, _n_multi, _rows, _n_png = {}, 0, [], 0
    # One row per CYCLE across the whole session. The per-trial CSV cannot
    # hold this: a walking capture has forty of them and a squat has none, so
    # they get a table of their own rather than forty more columns.
    _cycle_rows = []

    def _existing_rows(path, key="trial"):
        """Rows of a previously written CSV, grouped by trial."""
        _by = {}
        if not os.path.isfile(path):
            return _by
        try:
            with open(path, newline="", encoding="utf-8") as _fh:
                for _r in _csv.DictReader(_fh):
                    # csv gives back strings; `agrees` is read as a boolean
                    # further down and "False" is a truthy string.
                    if "agrees" in _r:
                        _r["agrees"] = str(_r["agrees"]).strip().lower() \
                            in ("true", "1", "yes")
                    _by.setdefault(_r.get(key, ""), []).append(_r)
        except Exception:
            return {}
        return _by

    _det_dir = os.path.join(_sess, "movement_detection")
    _prev_rows = _existing_rows(os.path.join(_det_dir, "classification.csv")) \
        if _only else {}
    _prev_cycles = _existing_rows(os.path.join(_det_dir, "cycles.csv")) \
        if _only else {}
    for _t in _trials:
        _d = os.path.join(_exp, _t)
        if _t not in _todo:
            # Not asked for. Keep what this trial already knows about itself:
            # the per-trial file is the authoritative record, so the session
            # aggregates stay complete without re-reading a 46 MB TRC.
            _prev = os.path.join(_d, "movement_detection.yaml")
            try:
                _pd = _yaml.safe_load(open(_prev, encoding="utf-8")) or {}
            except Exception:
                _pd = {}
            if _pd:
                _out[_t] = {_k: _v for _k, _v in _pd.items()
                            if _k not in ("trial", "generated_by",
                                          "session_yaml_type", "agrees")}
                if len(_pd.get("tasks") or []) > 1:
                    _n_multi += 1
            _rows.extend(_prev_rows.get(_t, []))
            _cycle_rows.extend(_prev_cycles.get(_t, []))
            continue
        try:
            _lab, _conf, _why, _f = classify_trial(_d, body_mass=_mass,
                                                   cfg=_mcfg)
            _segs = segment_trial(_d, body_mass=_mass, cfg=_mcfg)
            _cyc = gait_cycles(_d, body_mass=_mass, cfg=_mcfg, segments=_segs)
            if _mside in ("l", "r"):
                # The session is about ONE leg: the other leg's strides are
                # not reported, counted or allowed to make a trial "valid".
                _cyc = [_c for _c in _cyc
                        if str(_c.get("side", ""))[:1].lower() == _mside]
            _jumps = _plate_cop_jumps(_d, _mass, _mcfg)
            for _c in _cyc:
                _s0, _s1 = (_c.get("stance") or [None, None])
                _hit = [_j for _j in _jumps if _s0 is not None
                        and _j["plate"] in (_c.get("plates") or [])
                        and _s0 - 0.05 <= _j["t"] <= _s1 + 0.05]
                _c["cop_jump"] = bool(_hit)
                if _hit:
                    _j = max(_hit, key=lambda _x: _x["load_n"])
                    _c["cop_jump_note"] = (
                        f"CoP jumped {_j['jump_m']*100:.0f} cm at {_j['t']:.3f} s "
                        f"with {_j['load_n']:.0f} N already on {_j['plate']}")
        except Exception as _e:
            print(f"  {_t:24} ERROR {type(_e).__name__}: {_e}")
            continue
        if len(_segs) > 1:
            _n_multi += 1
        _entry = {"type": _lab, "confidence": round(float(_conf), 2),
                  "reason": _why}
        if getattr(_f, "cut_direction", ""):
            _entry["cut_direction"] = _f.cut_direction
            _entry["cut_angle_deg"] = _f.cut_angle_deg
        # The trial's range is the range of the TASKS that gave it its
        # label, not the modality-consensus window: on a cut capture the
        # consensus spans the whole run-up, while the finding is the 0.3 s in
        # which the turn happened. Same for the side — it is the leg the task
        # was performed on, not whichever leg happened to be single-support.
        _key = [_g for _g in _segs if _g.task == _lab] or \
               [_g for _g in _segs if _g.task not in ("static", "single_leg_stance")]
        if _key:
            _entry["time_range"] = [min(_g.t_start for _g in _key),
                                    max(_g.t_end for _g in _key)]
            _sides = {_g.side for _g in _key if _g.side}
            if len(_sides) == 1:
                _entry["side"] = next(iter(_sides))
            elif _sides:
                _entry["side"] = "both"
        elif getattr(_f, "window_consensus", ()):
            _entry["time_range"] = list(_f.window_consensus)
        if getattr(_f, "window_consensus", ()):
            _entry["modality_window"] = list(_f.window_consensus)
        if _segs:
            _entry["tasks"] = [
                {"task": _g.task, "time_range": [_g.t_start, _g.t_end],
                 **({"name": _g.name} if getattr(_g, "name", "") else {}),
                 **({"side": _g.side} if _g.side else {}),
                 **({"direction": _g.direction}
                    if getattr(_g, "direction", None) else {}),
                 **({"angle_deg": _g.angle_deg}
                    if getattr(_g, "angle_deg", None) is not None else {}),
                 **({"jump_height_m": _g.jump_height_m}
                    if getattr(_g, "jump_height_m", None) is not None else {}),
                 **({"jump_height_grf_m": _g.jump_height_grf_m}
                    if getattr(_g, "jump_height_grf_m", None) is not None else {}),
                 **({"flight_time_s": _g.flight_time_s}
                    if getattr(_g, "flight_time_s", None) is not None else {}),
                 **{_k: getattr(_g, _k) for _k in
                    ("bar_rom_m", "bar_ap_drift_m", "bar_path_deviation_m",
                     "bar_peak_velocity_ms", "bar_mean_concentric_velocity_ms")
                    if getattr(_g, _k, None) is not None},
                 **({"phases": [{"phase": _p.phase,
                                 "time_range": [_p.t_start, _p.t_end],
                                 **({"side": _p.side} if _p.side else {})}
                                for _p in _g.phases]} if _g.phases else {})}
                for _g in _segs]
        # THE CYCLES. A capture is one recording; a cycle is one thing to
        # simulate, and a long overground trial holds dozens of them. Listing
        # them here is what lets the pipeline build one run per cycle instead
        # of one run per capture, and each carries the window, the leg, the
        # plate and the events that window was cut with.
        if _cyc:
            _entry["cycles"] = _cyc
            _entry["n_cycles"] = len(_cyc)
            _entry["n_cycles_left"] = sum(1 for _c in _cyc if _c["side"] == "left")
            _entry["n_cycles_right"] = sum(1 for _c in _cyc if _c["side"] == "right")
        _out[_t] = _entry

        _yt = str(((_cfg.get("trials") or {}).get(_t) or {}).get("type", ""))
        _row = {"trial": _t, "detected": _lab, "session_yaml_type": _yt,
                "agrees": (_yt == "" or _yt == _lab),
                "confidence": round(float(_conf), 2), "n_tasks": len(_segs),
                "reason": _why,
                "cut_direction": getattr(_f, "cut_direction", ""),
                "cut_angle_deg": getattr(_f, "cut_angle_deg", ""),
                "median_speed": getattr(_f, "median_speed", ""),
                "vertical_rom_m": getattr(_f, "vertical_rom_m", ""),
                "longest_flight_s": getattr(_f, "longest_flight_s", ""),
                "peak_vgrf_bw": getattr(_f, "peak_vgrf_bw", ""),
                "single_support_frac": getattr(_f, "single_support_frac", ""),
                "n_cycles": len(_cyc),
                "n_cycles_left": sum(1 for _c in _cyc if _c["side"] == "left"),
                "n_cycles_right": sum(1 for _c in _cyc if _c["side"] == "right"),
                "cycles": " ".join(_c["name"] for _c in _cyc),
                "tasks": "; ".join(f"{_g.task}[{_g.t_start:.2f}-{_g.t_end:.2f}]"
                                   for _g in _segs)}
        for _g, _sfx in zip(_segs, "abcdefghijklmnop"):
            _row[f"task_{_sfx}"] = _g.task
            _row[f"task_{_sfx}_start"] = _g.t_start
            _row[f"task_{_sfx}_end"] = _g.t_end
            if getattr(_g, "angle_deg", None) is not None:
                _row[f"task_{_sfx}_angle_deg"] = _g.angle_deg
            for _fld in ("jump_height_m", "jump_height_grf_m", "flight_time_s",
                         "bar_rom_m", "bar_ap_drift_m", "bar_path_deviation_m",
                         "bar_peak_velocity_ms",
                         "bar_mean_concentric_velocity_ms"):
                if getattr(_g, _fld, None) is not None:
                    _row[f"task_{_sfx}_{_fld}"] = getattr(_g, _fld)
        _rows.append(_row)
        for _c in _cyc:
            _cycle_rows.append({
                "trial": _t, "cycle": _c["name"], "side": _c["side"],
                "index": _c["index"], "task": _c["task"],
                "t_start": _c["time_range"][0], "t_end": _c["time_range"][1],
                "duration_s": _c["duration_s"], "cycle_from": _c["cycle_from"],
                "stance_start": (_c["stance"] or [None, None])[0],
                "stance_end": (_c["stance"] or [None, None])[1],
                "plates": " ".join(_c.get("plates") or []),
                "peak_n": _c["peak_n"], "side_margin_m": _c["side_margin_m"],
                "shared_plate": _c["shared_plate"],
                "straddled": _c["straddled"],
                "cop_jump": _c.get("cop_jump", False),
                "cop_jump_note": _c.get("cop_jump_note", ""),
                "reason": _c["reason"]})

        # The detection belongs beside the data it describes. Written per
        # trial it survives a trial being copied, re-exported or moved, and
        # anything reading 2_experimental/<trial>/ finds it without knowing
        # the session layout.
        if per_trial:
            try:
                _tdoc = {"trial": _t,
                         "generated_by": f"bioscout {getattr(__import__('bioscout'), '__version__', 'unknown')} export",
                         **_entry}
                if _yt:
                    _tdoc["session_yaml_type"] = _yt
                    _tdoc["agrees"] = (_yt == _lab)
                with open(os.path.join(_d, "movement_detection.yaml"), "w",
                          encoding="utf-8") as _fh:
                    _yaml.safe_dump(_tdoc, _fh, sort_keys=False,
                                    default_flow_style=False, allow_unicode=True)
            except Exception as _e:
                print(f"  [detect] {_t}: could not write movement_detection.yaml "
                      f"({type(_e).__name__}: {_e})")

        if _do_plots:
            _png = (os.path.join(_d, "movement_detection.png") if per_trial
                    else os.path.join(_plots, f"{_t}.png"))
            try:
                if plot_trial_tasks(_d, _png, body_mass=_mass, cfg=_mcfg,
                                    segments=_segs):
                    _n_png += 1
            except Exception as _e:
                print(f"  [plot] {_t}: {type(_e).__name__}: {_e}")

        _old = _yt
        _flag = "" if not _old else ("  ==" if _old == _lab else f"  != session.yaml says {_old}")
        _say(f"  {_t:24} {_lab:18} {len(_segs)} task(s){_flag}")

    _ver = getattr(__import__('bioscout'), '__version__', 'unknown')
    # (session_auto_detection.yaml, a full mirror of session.yaml with the
    # detection laid over it, is no longer written: nothing read it, it
    # duplicated the per-trial files and it went stale. The session-level
    # record is movement_detection/movement_detection.yaml, written below.)
    _dst = os.path.join(_det, "movement_detection.yaml")
    _csv_path = os.path.join(_det, "classification.csv")
    if _rows:
        _keys = []
        for _r in _rows:
            for _k in _r:
                if _k not in _keys:
                    _keys.append(_k)
        os.makedirs(_det, exist_ok=True)
        with open(_csv_path, "w", newline="", encoding="utf-8") as _fh:
            _w = _csv.DictWriter(_fh, fieldnames=_keys)
            _w.writeheader(); _w.writerows(_rows)

    _cyc_path = os.path.join(_det, "cycles.csv")
    if _cycle_rows:
        os.makedirs(_det, exist_ok=True)
        with open(_cyc_path, "w", newline="", encoding="utf-8") as _fh:
            _w = _csv.DictWriter(_fh, fieldnames=list(_cycle_rows[0].keys()))
            _w.writeheader(); _w.writerows(_cycle_rows)
        if not quiet:
            _info(f"[classifier] wrote {_cyc_path} "
                  f"({len(_cycle_rows)} gait cycle(s))")

    # THE ANSWER PEOPLE OPEN THIS FOLDER FOR: can this trial be simulated?
    # classification.csv says what a trial IS and cycles.csv lists every
    # stride; neither says, in one line per trial, whether the force plates
    # measured ONE foot each. A plate that took both feet (or a step that
    # spanned two plates) gives an inverse dynamics that looks like data and
    # is not: on Charite H3L Gehen_01 it cost a two-hour sweep to find out.
    _val_path = os.path.join(_det, "trials_valid.csv")
    _val_rows = _trial_validity(_rows, _cycle_rows, measured_side=_mside)
    if _val_rows:
        os.makedirs(_det, exist_ok=True)
        with open(_val_path, "w", newline="", encoding="utf-8") as _fh:
            _w = _csv.DictWriter(_fh, fieldnames=list(_val_rows[0].keys()))
            _w.writeheader(); _w.writerows(_val_rows)
        _bad = [_r for _r in _val_rows if not _r["valid"]]
        _info(f"{'  [detect]' if quiet else '[classifier]'} wrote {_val_path} "
              f"({len(_val_rows) - len(_bad)} valid, {len(_bad)} NOT valid)")
        for _r in _bad:
            _info(f"{'  [detect]' if quiet else '[classifier]'} NOT VALID "
                  f"{_r['trial']:24} {_r['reason']}")

    # ONE FILE FOR THE SESSION: every trial's detection plus its validity, so
    # a reader (or a script) needs neither the per-trial folders nor the CSVs.
    # It describes; it is never read by the pipeline and never changes
    # session.yaml -- that is --write-yaml's job.
    _vby = {_r["trial"]: _r for _r in _val_rows}
    _sdoc = {"generated_by": f"bioscout {_ver} session classify",
             "session": os.path.basename(_sess),
             "measured_side": _mside,
             "note": ("Detected from markers/GRF. `valid` is about the "
                      "measurement: false when no stride has a force plate to "
                      "itself, or the trial could not be classified. "
                      "session.yaml is not changed by this file."),
             "trials": {}}
    for _k, _v in _out.items():
        _e = {"type": _v.get("type")}
        _vr = _vby.get(_k)
        if _vr:
            _e["valid"] = bool(_vr["valid"])
            for _s in ("valid_left", "valid_right"):
                if _vr[_s] != "":
                    _e[_s] = bool(_vr[_s])
            _e["valid_reason"] = _vr["reason"]
        _yt2 = str(((_cfg.get("trials") or {}).get(_k) or {}).get("type", ""))
        if _yt2:
            _e["session_yaml_type"] = _yt2
            _e["agrees"] = (_yt2 == _v.get("type"))
        _e.update({_a: _b for _a, _b in _v.items() if _a != "type"})
        _sdoc["trials"][_k] = _e
    if _sdoc["trials"]:
        os.makedirs(_det, exist_ok=True)
        with open(_dst, "w", encoding="utf-8") as _fh:
            _yaml.safe_dump(_sdoc, _fh, sort_keys=False,
                            default_flow_style=False, allow_unicode=True)
    _stale = os.path.join(_sess, "session_auto_detection.yaml")
    if os.path.isfile(_stale):
        _info(f"{'  [detect]' if quiet else '[classifier]'} "
              f"{os.path.basename(_stale)} is from an older bioscout and is no "
              f"longer written or read -- safe to delete")

    _dis = [_r for _r in _rows if not _r["agrees"]]
    if not quiet and not verbose:
        _want_leg = {"l": "left", "r": "right"}.get(_mside)
        _short_report(_sess, _mside, _val_rows, _dis, _det,
                      [_c for _c in _cycle_rows
                       if not _want_leg or str(_c.get("side", "")) == _want_leg])
    if quiet:
        print(f"  [detect] {len(_out)} trial(s) classified, {len(_dis)} "
              f"disagreeing with session.yaml"
              + (f", {_n_png} figure(s)" if _do_plots else ""))
        for _r in _dis:
            print(f"  [detect] {_r['trial']:24} detected {_r['detected']}"
                  f" != session.yaml {_r['session_yaml_type'] or '(unset)'}")
    else:
        _info(f"\n[classifier] {len(_out)} trial(s), {_n_multi} with more than "
              f"one task, {len(_dis)} disagreeing with session.yaml")
        _info(f"[classifier] wrote {_dst}")
        if _rows:
            _info(f"[classifier] wrote {_csv_path}")
        if not _do_plots:
            _info("[classifier] figures skipped (--no-plots)")
        elif per_trial:
            _info(f"[classifier] wrote {_n_png} figures -> "
                  f"{os.path.join('2_experimental', '<trial>', 'movement_detection.png')}")
        else:
            _info(f"[classifier] wrote {_n_png} figures -> {_plots}")
        if per_trial:
            _info(f"[classifier] wrote {len(_out)} x "
                  f"{os.path.join('2_experimental', '<trial>', 'movement_detection.yaml')}")

    if not os.path.isfile(_ypath):
        if write_session_yaml:
            _seed = {"session": os.path.basename(_sess), "body_mass": _mass,
                     "trials": {k: {"type": v["type"],
                                    **({"valid": bool(_vby[k]["valid"])}
                                       if k in _vby else {})}
                                for k, v in _out.items()}}
            with open(_ypath, "w", encoding="utf-8") as _fh:
                _yaml.safe_dump(_seed, _fh, sort_keys=False)
            print(f"[classifier] no session.yaml existed — seeded {_ypath}")
            print("[classifier] REVIEW IT: detection is a starting point, not a source of truth.")
        else:
            print("[classifier] this session has no session.yaml. "
                  "Re-run with --write-session-yaml to seed one from the detection.")
    elif write_session_yaml:
        # A session.yaml already exists. Correct the trial TYPES from the
        # detection and leave everything else alone — body mass, markerset,
        # EMG map and calibration choices are not the detector's to touch.
        # The previous file is kept, because a detector is a starting point.
        _bak = _ypath + ".pre_detection"
        if not os.path.exists(_bak):
            _shutil_ = __import__("shutil")
            _shutil_.copy2(_ypath, _bak)
            print(f"[classifier] backed up {os.path.basename(_ypath)} -> "
                  f"{os.path.basename(_bak)}")
        _tr = _cfg.setdefault("trials", {}) or {}
        _changed = []
        for _k, _v in _out.items():
            _was = str((_tr.get(_k) or {}).get("type", ""))
            _now = _v["type"]
            if _was != _now:
                _changed.append((_k, _was or "(unset)", _now))
            _entry_y = _tr.get(_k) or {}
            if _now == "unknown" and _was:
                # "could not tell" is not a finding: keep the type the file
                # had and let `valid: false` carry the message.
                if _was != _now:
                    _changed.pop()
            else:
                _entry_y["type"] = _now
                if _v.get("time_range"):
                    _entry_y["time_range"] = _v["time_range"]
            if _k in _vby:
                _entry_y["valid"] = bool(_vby[_k]["valid"])
            _tr[_k] = _entry_y
        _cfg["trials"] = _tr
        with open(_ypath, "w", encoding="utf-8") as _fh:
            _yaml.safe_dump(_cfg, _fh, sort_keys=False)
        print(f"[classifier] updated {_ypath}: {len(_changed)} trial type(s) changed")
        for _k, _was, _now in _changed:
            print(f"             {_k:24} {_was} -> {_now}")
        print("[classifier] REVIEW IT: detection is a starting point, not a source of truth.")
    return _out

