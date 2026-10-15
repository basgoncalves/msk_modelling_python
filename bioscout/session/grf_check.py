"""Audit each trial's force-plate -> foot assignment in GRF.xml.

WHY THIS EXISTS
---------------
``GRF.xml`` names which OpenSim body each force plate pushes on. It is written
once by ``session export`` and then never revisited, so it silently goes stale
in two ways:

* ``grf.mot`` is re-exported (new filtering, new plate set) and the XML still
  describes the old force data;
* the assignment logic itself is fixed -- as it was on 2026-08-12, when scoring
  plates on the horizontal plane was found to collapse every plate onto ONE
  foot -- and files written before the fix keep the wrong answer.

Either way the failure is quiet and expensive: a bilateral trial with both
plates on ``calcn_l`` gives that leg the whole body weight and the other leg
none, so its ID, SO and JRA are wrong while every file still looks valid. A
static standing trial with both plates on one foot is the clearest tell.

This module re-derives the assignment from the CURRENT grf.mot + TRC and
reports what would change. It is read-only unless ``write=True``.
"""
import contextlib
import csv
import glob
import io
import os
import re

#: trial names that are BILATERAL by nature -- if one of these comes back with
#: every plate on one foot, that is a bug, not a finding. Single-leg names
#: (SLS..., single...) are excluded because one-sided is correct for them.
_BILATERAL = re.compile(r"squat|static|stand|cmj|jump|^sj", re.I)
_UNILATERAL = re.compile(r"sls|single|hop", re.I)


def read_assignment(xml_path):
    """{plate_number: body_name} as the EXISTING GRF.xml has it, or {}."""
    if not os.path.isfile(xml_path):
        return {}
    try:
        s = open(xml_path, errors="replace").read()
    except OSError:
        return {}
    return {m.group(2): m.group(3) for m in
            re.finditer(r'name="grf_([rl])_(\d+)".*?<applied_to_body>\s*([^<\s]+)',
                        s, re.S)}


def _short(assign):
    """{'2': 'calcn_l', '3': 'calcn_r'} -> '2:l,3:r' for a readable table."""
    return ",".join(f"{k}:{v[-1]}" for k, v in sorted(assign.items(), key=lambda kv: int(kv[0])))


def check_session(root=".", subject="*", session="*", write=False, csv_path=None,
                  log=print):
    """Re-derive plate->foot for every trial under ``root``/simulations.

    Returns (rows, n_changed, n_onesided). ``write=True`` regenerates the
    GRF.xml of every trial whose assignment changed; nothing else is touched.
    """
    from bioscout.simulate import opensim as _os

    pat = os.path.join(root, "simulations", subject, session, "2_experimental", "*")
    rows, changed, onesided = [], 0, 0

    for tdir in sorted(glob.glob(pat)):
        mot = os.path.join(tdir, "grf.mot")
        trc = os.path.join(tdir, "marker_experimental.trc")
        xml = os.path.join(tdir, "GRF.xml")
        if not (os.path.isfile(mot) and os.path.isfile(trc)):
            continue
        parts = tdir.replace("\\", "/").split("/")
        subj, sess, trial = parts[-4], parts[-3], parts[-1]

        before = read_assignment(xml)
        try:
            # assign_grfs_to_feet prints a dozen diagnostic lines per trial;
            # useful when one trial is wrong, unreadable across 600.
            _buf = io.StringIO()
            with contextlib.redirect_stdout(_buf):
                after = _os.assign_grfs_to_feet(grf_mot_path=mot, marker_trc_path=trc)
        except Exception as e:                                   # noqa: BLE001
            rows.append(dict(subject=subj, session=sess, trial=trial, before=_short(before),
                             after="", status=f"ERROR {type(e).__name__}: {e}"))
            log(f"{subj:>4} {sess:<9} {trial:<22} [ERROR] {type(e).__name__}: {e}")
            continue

        b, c = _short(before), _short(after)
        one = len(after) >= 2 and len(set(after.values())) == 1
        suspect = one and _BILATERAL.search(trial) and not _UNILATERAL.search(trial)
        status = "SAME" if b == c else "CHANGED"
        if suspect:
            status += " [SUSPECT: bilateral trial, all plates one foot]"
            onesided += 1
        elif one:
            status += " [one-sided -- expected for a single-leg trial]"

        if b != c:
            changed += 1
            if write:
                try:
                    _buf = io.StringIO()
                    with contextlib.redirect_stdout(_buf):
                        _os.create_grf_xml(grf_mot_path=mot, output_xml_path=xml,
                                           marker_trc_path=trc)
                    status += " -> REWRITTEN"
                except Exception as e:                           # noqa: BLE001
                    status += f" -> WRITE FAILED {type(e).__name__}: {e}"

        rows.append(dict(subject=subj, session=sess, trial=trial,
                         before=b, after=c, status=status))
        log(f"{subj:>4} {sess:<9} {trial:<22} {b:<14} -> {c:<14} {status}")

    if csv_path:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(csv_path)) or ".", exist_ok=True)
            with open(csv_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["subject", "session", "trial",
                                                  "before", "after", "status"])
                w.writeheader()
                w.writerows(rows)
            log(f"\n[OUTPUTS]:\n    {os.path.abspath(csv_path)}")
        except OSError as e:
            log(f"[WARNING] could not write {csv_path}: {e}")

    log(f"\n{len(rows)} trial(s) checked -- {changed} would change, "
        f"{onesided} suspect (bilateral trial with every plate on one foot)")
    if changed and not write:
        log("re-run with --write to regenerate those GRF.xml files")
    if changed:
        log("[WARNING] a changed GRF.xml invalidates that trial's ID / SO / JRA "
            "(IK is unaffected -- it never sees the GRF). Re-run those stages.")
    return rows, changed, onesided
