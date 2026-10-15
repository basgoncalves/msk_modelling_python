"""Per-trial ``time_range`` and ``side`` in session.yaml, from the exported data.

    from bioscout.session import windows as W

    W.set_time_ranges(session_dir)                      # report, write nothing
    W.set_time_ranges(session_dir, apply=True)          # write the windows
    W.set_sides(session_dir, apply=True)                # which leg is loaded
    W.set_trial_keys(yaml_path, {"RunA1": {"side": "r"}})

    bioscout session windows PATH --apply
    bioscout session sides   PATH --apply

WHY A WINDOW AT ALL. Without ``time_range`` IK is solved over the WHOLE
capture, of which the participant is in the volume for a second or two; the
solve then fails on the frames nothing observed and the session produces
nothing. ``bioscout.session.motion_detect`` finds the window from the movement
itself (bar or pelvis height, GRF as a fallback), which is what a lift or a
squat needs. This module is the other preference: for a trial that STRIKES A
PLATE -- running, cutting, a landing -- the window that matters is the stance
phase, so the loaded run on the plates is taken first and the movement
detector is the fallback. Pick with ``source=``.

Every window is then CLIPPED to the span the markers actually support (the
same test the IK preflight applies) and floored at zero: a window the markers
do not cover is the failure above, whatever produced it.

THE WRITE IS A TEXT EDIT. ``set_trial_keys`` patches the lines under each
trial and leaves the rest of session.yaml -- comments, key order, line endings
-- exactly as it was, and only writes when the edited text re-reads as the
configuration intended. Re-dumping the file through yaml.safe_dump loses the
comment block that explains the study, and has silently corrupted a
hand-written session.yaml before (a block-list ``time_range`` whose key was
removed and whose ``- 0.03`` items were left behind).
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

__all__ = ["set_trial_keys", "grf_window", "marker_span", "trial_window",
           "set_time_ranges", "detect_side", "set_sides"]

DEFAULT_PAD = 0.10
DEFAULT_GRF_THRESHOLD = 20.0       # N on any plate to count as loaded
DEFAULT_MIN_DURATION = 0.05        # s; shorter loaded runs are crosstalk


# ---------------------------------------------------------------- yaml text
def _read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("session.yaml", b"", 0, 1, f"cannot decode {path}")


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_scalar(x) for x in v) + "]"
    if isinstance(v, float):
        return repr(round(v, 6))
    return str(v)


def set_trial_keys(yaml_path, updates, *, dry_run=False, log=print):
    """Set ``key: value`` under named trials, editing the TEXT.

    ``updates`` is ``{trial: {key: value}}``; a value of None removes the key.
    Handles both block-style trials (``  RunA1:`` + indented keys) and flow
    style (``  RunA1: {type: running}``), and replaces a block-list value
    (``time_range:`` followed by ``- a`` / ``- b``) whole. Returns the trials
    that were not found. Nothing is written unless the result re-reads as
    exactly the intended configuration.
    """
    import yaml
    yaml_path = str(yaml_path)
    raw = _read_text(yaml_path)
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.replace("\r\n", "\n").split("\n")
    top = next((i for i, ln in enumerate(lines) if re.match(r"^trials:\s*$", ln)), None)
    if top is None:
        raise ValueError(f"{yaml_path}: no block-style top-level `trials:` line")
    end = top + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0] in " \t#"):
        end += 1
    hdr = re.compile(r"^(\s+)([A-Za-z0-9_.\-]+):\s*(\{.*\})?\s*(#.*)?$")
    headers = [(i, m) for i in range(top + 1, end) for m in [hdr.match(lines[i])] if m]
    if not headers:
        return list(updates)
    tind = min(len(m.group(1)) for _, m in headers)
    headers = [(i, m) for i, m in headers if len(m.group(1)) == tind]
    spans = {m.group(2): (i, (headers[k + 1][0] if k + 1 < len(headers) else end), m)
             for k, (i, m) in enumerate(headers)}
    missing = [t for t in updates if t not in spans]

    for t in sorted((t for t in updates if t in spans),
                    key=lambda t: spans[t][0], reverse=True):   # bottom-up
        i, j, m = spans[t]
        kv = updates[t]
        if m.group(3):                                          # flow style
            d = yaml.safe_load(m.group(3)) or {}
            for k, v in kv.items():
                d.pop(k, None) if v is None else d.__setitem__(k, v)
            flow = "{" + ", ".join(f"{k}: {_scalar(v)}" for k, v in d.items()) + "}"
            lines[i] = (f"{m.group(1)}{t}: {flow}"
                        + (f"  {m.group(4)}" if m.group(4) else ""))
            continue
        body = list(range(i + 1, j))
        while body and not lines[body[-1]].strip():
            body.pop()
        bind = next((len(lines[b]) - len(lines[b].lstrip(" ")) for b in body
                     if lines[b].strip() and not lines[b].lstrip().startswith("#")),
                    tind + 2)
        new_body = [lines[b] for b in body]
        for k, v in kv.items():
            kre = re.compile(rf"^ {{{bind}}}{re.escape(k)}:(.*)$")
            at = next((n for n, ln in enumerate(new_body) if kre.match(ln)), None)
            if at is not None:
                stop = at + 1
                while stop < len(new_body) and re.match(rf"^ {{{bind}}}(\s*)- ",
                                                        new_body[stop]):
                    stop += 1                                   # its list items
                new_body[at:stop] = [] if v is None else [f"{' ' * bind}{k}: {_scalar(v)}"]
            elif v is not None:
                new_body.append(f"{' ' * bind}{k}: {_scalar(v)}")
        lines[i + 1:i + 1 + len(body)] = new_body

    text = nl.join(lines)
    before = yaml.safe_load(raw) or {}
    after = yaml.safe_load(text) or {}
    want = json.loads(json.dumps(before, default=str))
    for t, kv in updates.items():
        if t in missing:
            continue
        meta = want["trials"].get(t) or {}
        for k, v in kv.items():
            meta.pop(k, None) if v is None else meta.__setitem__(
                k, list(v) if isinstance(v, tuple) else v)
        want["trials"][t] = meta
    if json.loads(json.dumps(after, default=str)) != want:
        raise RuntimeError(f"{yaml_path}: the edited text did not re-read as "
                           f"intended -- nothing was written")
    if not dry_run and text != raw:
        tmp = yaml_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, yaml_path)
    return missing


# ------------------------------------------------------------------ windows
def _read_mot(path):
    """(columns, rows) of a .mot/.sto -- no pandas, no bioscout.utils."""
    import numpy as np
    with open(path, errors="ignore") as fh:
        lines = fh.read().splitlines()
    i = next((k + 1 for k, ln in enumerate(lines) if ln.strip().lower() == "endheader"),
             None)
    if i is None:
        i = next(k for k, ln in enumerate(lines)
                 if ln.split() and ln.split()[0].lower() == "time")
    cols = lines[i].split()
    rows = []
    for ln in lines[i + 1:]:
        tok = ln.split()
        if len(tok) != len(cols):
            continue
        try:
            rows.append([float(x) for x in tok])
        except ValueError:
            continue
    return cols, np.asarray(rows, dtype=float)


def _longest_run(times, mask, min_duration=0.0):
    best = cur = None
    for i, on in enumerate(list(mask) + [False]):
        if on and cur is None:
            cur = i
        elif not on and cur is not None:
            if best is None or i - cur > best[1] - best[0] + 1:
                best = (cur, i - 1)
            cur = None
    if best is None:
        return None
    t0, t1 = float(times[best[0]]), float(times[best[1]])
    return (t0, t1) if t1 - t0 >= min_duration else None


def grf_window(mot, threshold=DEFAULT_GRF_THRESHOLD, min_duration=DEFAULT_MIN_DURATION):
    """(t0, t1) of the longest run in which ANY plate carries more than
    ``threshold`` newtons -- the stance phase for a trial that strikes one."""
    import numpy as np
    if not os.path.isfile(str(mot)):
        return None
    try:
        cols, d = _read_mot(mot)
    except Exception:                                          # noqa: BLE001
        return None
    if not len(d):
        return None
    vy = [i for i, c in enumerate(cols) if c.endswith("_vy")]
    if not vy or cols[0].lower() != "time":
        return None
    return _longest_run(d[:, 0], (np.abs(d[:, vy]) > threshold).any(axis=1), min_duration)


def marker_span(trc, min_frac=0.90):
    """(t0, t1) of the longest run of frames carrying at least ``min_frac`` of
    the markers -- the span IK can fit a pose to."""
    import numpy as np
    if not os.path.isfile(str(trc)):
        return None
    try:
        with open(trc, errors="ignore") as fh:
            lines = fh.read().splitlines()
        rows = [ln.split("\t") if "\t" in ln else ln.split() for ln in lines[5:] if ln.strip()]
    except OSError:
        return None
    times, frac = [], []
    ncol = None
    for tok in rows:
        if len(tok) < 3:
            continue
        try:
            times.append(float(tok[1]))
        except ValueError:
            continue
        vals = tok[2:]
        ncol = ncol or len(vals)
        frac.append(sum(1 for v in vals if v.strip() not in ("", "nan", "NaN"))
                    / max(ncol, 1))
    if not times:
        return None
    return _longest_run(np.asarray(times), [f >= min_frac for f in frac])


def _classifier_window(row):
    """(t0, t1) spanning every task `session classify` found in this trial."""
    def nums(pat):
        out = []
        for k, v in (row or {}).items():
            if k and re.fullmatch(pat, k) and str(v) not in ("", "nan", "NaN", "None"):
                try:
                    out.append(float(v))
                except ValueError:
                    pass
        return out
    starts, ends = nums(r"task_[a-z]_start"), nums(r"task_[a-z]_end")
    return (min(starts), max(ends)) if starts and ends else None


def _classification(session_dir):
    p = Path(session_dir) / "movement_detection" / "classification.csv"
    if not p.is_file():
        return {}
    with open(p, newline="", errors="ignore") as fh:
        return {r["trial"]: r for r in csv.DictReader(fh) if r.get("trial")}


def _clamp(win, span, pad):
    if win is None:
        return None
    a, b = win[0] - pad, win[1] + pad
    if span:
        a, b = max(a, span[0]), min(b, span[1])
    a = max(a, 0.0)
    return (round(a, 3), round(b, 3)) if b > a else None


def trial_window(trial_export_dir, *, source="grf", pad=DEFAULT_PAD,
                 threshold=DEFAULT_GRF_THRESHOLD, min_duration=DEFAULT_MIN_DURATION,
                 classifier_row=None):
    """(window, how) for one exported trial folder, or (None, why).

    ``source="grf"``   plates first, movement detector second (running, cuts)
    ``source="motion"`` movement detector first, plates second (lifts, squats)
    """
    d = Path(trial_export_dir)
    trc = d / "marker_experimental.trc"
    if not trc.is_file():
        return None, "not exported (no marker_experimental.trc)"

    def _grf():
        w = grf_window(d / "grf.mot", threshold, min_duration)
        return (w, "grf") if w else (None, None)

    def _motion():
        try:
            from bioscout.session.motion_detect import detect_time_range
            tr = detect_time_range(d, threshold=0.10, min_duration=min_duration)
        except Exception:                                      # noqa: BLE001
            return None, None
        if tr.method == "full":
            return None, None
        return (tr.start, tr.end), f"motion:{tr.method}"

    order = (_grf, _motion) if source == "grf" else (_motion, _grf)
    win = how = None
    for f in order:
        win, how = f()
        if win:
            break
    if win is None and classifier_row:
        win, how = _classifier_window(classifier_row), "classifier"
    win = _clamp(win, marker_span(trc), pad)
    return (win, how) if win else (None, "no window from the plates, the "
                                         "movement detector or the classifier")


def set_time_ranges(session_dir, *, trials=None, source="grf", pad=DEFAULT_PAD,
                    threshold=DEFAULT_GRF_THRESHOLD, min_duration=DEFAULT_MIN_DURATION,
                    force=False, apply=False, skip_types=("static",), log=print):
    """Give each exported trial a ``time_range``. Existing windows are kept
    unless ``force``; nothing is written unless ``apply``. Returns
    ``{trial: {"window", "source", "note"}}``."""
    import yaml
    session_dir = Path(session_dir)
    ypath = session_dir / "session.yaml"
    cfg = yaml.safe_load(_read_text(ypath)) or {}
    tcfg = cfg.get("trials") or {}
    static = cfg.get("static_trial")
    cls = _classification(session_dir)
    exp = session_dir / "2_experimental"
    try:                                        # honour a non-standard layout
        from bioscout.session import layout as _layout
        exp = Path(_layout.experimental_root(str(session_dir)))
    except Exception:                                          # noqa: BLE001
        pass

    out, picked = {}, {}
    for name, blk in tcfg.items():
        blk = blk or {}
        if trials and name not in trials:
            continue
        if name == static or str(blk.get("type", "")).lower() in skip_types:
            continue
        if blk.get("time_range") and not force:
            out[name] = dict(window=list(blk["time_range"]), source="kept", note="")
            continue
        win, how = trial_window(exp / name, source=source, pad=pad, threshold=threshold,
                                min_duration=min_duration, classifier_row=cls.get(name))
        out[name] = dict(window=list(win) if win else None,
                         source=how if win else None, note="" if win else how)
        if win:
            picked[name] = {"time_range": [win[0], win[1]]}
            log(f"[windows] {name:22s} {win[0]:6.2f}-{win[1]:6.2f} s  via {how}")
        else:
            log(f"[windows] {name:22s} --  {how}")
    if picked and apply:
        set_trial_keys(ypath, picked)
        log(f"[windows] wrote {len(picked)} time_range entr{'y' if len(picked) == 1 else 'ies'}"
            f" to {ypath}")
    elif picked:
        log(f"[windows] {len(picked)} window(s) found -- pass apply=True to write them")
    return out


# -------------------------------------------------------------------- sides
def _plate_bodies(grf_xml):
    """{force_identifier: 'l'|'r'} from GRF.xml's plate -> foot assignment."""
    from xml.etree import ElementTree as ET
    out = {}
    try:
        root = ET.parse(str(grf_xml)).getroot()
    except Exception:                                          # noqa: BLE001
        return out
    for ef in root.iter("ExternalForce"):
        body = (ef.findtext("applied_to_body") or "").strip().lower()
        fid = (ef.findtext("force_identifier") or "").strip()
        if fid and body.startswith("calcn_"):
            out[fid] = "l" if body.endswith("_l") else "r"
    return out


def detect_side(trial_export_dir, body_mass=None, window=None):
    """('l'|'r'|'both'|None, why) -- which foot is loaded in this trial.

    ``window`` (the trial's ``time_range``) restricts the search to the frames
    that are actually solved. Without it a running capture that also catches
    the NEXT footfall on another plate reads as "both".

    Read from the plate-to-foot assignment bioscout worked out at export time
    (GRF.xml, CoP against the foot markers), cross-checked against which plates
    actually carry load: a plate mapped to a foot but never loaded does not
    count. The threshold is 10 % of body weight, floored at 50 N.
    """
    d = Path(trial_export_dir)
    gx, gm = d / "GRF.xml", d / "grf.mot"
    if not (gx.is_file() and gm.is_file()):
        return None, "no GRF export"
    bodies = _plate_bodies(gx)
    if not bodies:
        return None, "GRF.xml maps no plate to a foot"
    try:
        cols, data = _read_mot(gm)
    except Exception:                                          # noqa: BLE001
        return None, "grf.mot unreadable"
    if window and len(data):
        keep = (data[:, 0] >= float(window[0])) & (data[:, 0] <= float(window[1]))
        if keep.any():
            data = data[keep]
    peaks = {c[:-1]: float(data[:, i].max()) for i, c in enumerate(cols)
             if c.endswith("_vy") and len(data)}
    thr = max(50.0, 0.10 * float(body_mass) * 9.81) if body_mass else 50.0
    loaded = {}
    for fid, side in bodies.items():
        pk = peaks.get(fid, 0.0)
        if pk >= thr:
            loaded[side] = max(loaded.get(side, 0.0), pk)
    if not loaded:
        return None, f"no plate above {thr:.0f} N"
    if len(loaded) == 2:
        return "both", f"L {loaded['l']:.0f} N + R {loaded['r']:.0f} N"
    s = next(iter(loaded))
    return s, f"{s.upper()} {loaded[s]:.0f} N (threshold {thr:.0f} N)"


def set_sides(session_dir, *, trials=None, force=False, apply=False, log=print):
    """Write each trial's loaded leg as ``side:`` in session.yaml. Existing
    values are kept unless ``force``; nothing is written unless ``apply``."""
    import yaml
    session_dir = Path(session_dir)
    ypath = session_dir / "session.yaml"
    cfg = yaml.safe_load(_read_text(ypath)) or {}
    tcfg = cfg.get("trials") or {}
    mass = cfg.get("body_mass")
    static = cfg.get("static_trial")
    exp = session_dir / "2_experimental"
    out, upd = {}, {}
    for name, blk in tcfg.items():
        blk = blk or {}
        if (trials and name not in trials) or name == static:
            continue
        if str(blk.get("type", "")).lower() == "static":
            continue
        side, why = detect_side(exp / name, mass, blk.get("time_range"))
        cur = blk.get("side")
        out[name] = dict(side=side, current=cur, note=why)
        if side is None or (cur and not force) or str(cur) == side:
            continue
        upd[name] = {"side": side}
        log(f"[sides] {name:22s} {cur or '-'} -> {side}   ({why})")
    if upd and apply:
        set_trial_keys(ypath, upd)
        log(f"[sides] wrote {len(upd)} side(s) to {ypath}")
    elif upd:
        log(f"[sides] {len(upd)} side(s) to set -- pass apply=True to write them")
    return out
