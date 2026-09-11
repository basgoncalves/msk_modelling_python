"""One call, one folder: muscle forces + joint contact forces + comparisons.

    from bioscout.simulate.mew import analyse_trial
    out = analyse_trial(trial_dir, model="022_Rajagopal2015_FAI.osim", jcf=True)

Everything lands in ``<trial>/mew/`` so nothing a CEINMS or SO run
produced is ever overwritten. Pass ``ceinms_compat=True`` to ALSO write
``ceinms/Optimised/MuscleForces.sto``, which is what the existing bioscout
plotting and ``summarize_results.py`` read.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import numpy as np

from . import compare as _compare, jcf as _jcf
from .bioscout_adapter import (analyser_from_trial_dir, discover_trial,
                               forces_output_path, output_dir, read_session_yaml)
from .types import Tier


def analyse_trial(trial_dir, model, *, height=None, mass=None, tier=None,
                  smoothing=None, filter_hz=None,
                  jcf=False, jcf_joints=("hip_r", "hip_l", "knee_r", "knee_l"),
                  compare=True, plot=True, ceinms_compat=False,
                  theta_file=None, verbose=True) -> Dict[str, object]:
    """Solve a trial and write every output into ``<trial>/mew/``.

    Returns a dict with the result, the paths written, the comparison tables and
    the JCF report. Joint contact forces need bioscout + opensim importable;
    without them the muscle forces are still written and ``jcf_error`` says why
    that step was skipped -- a missing OpenSim must never cost you the part that
    did work.
    """
    trial_dir = os.path.abspath(str(trial_dir))
    out_dir = output_dir(trial_dir)
    found = discover_trial(trial_dir)
    sess = read_session_yaml(trial_dir)
    body_mass = mass if mass is not None else sess.get("body_mass")
    written: List[str] = []

    def say(*a):
        if verbose:
            print(*a)

    # ---- 1. muscle forces -------------------------------------------------
    say(f"\n[1/4] solving {os.path.basename(trial_dir)}")
    ma = analyser_from_trial_dir(trial_dir, model, height=height, mass=body_mass,
                                 theta_file=theta_file)
    result = ma.run(tier=Tier(tier) if tier is not None else None,
                    smoothing=smoothing, filter_hz=filter_hz)
    say(f"      {result.summary()}")
    for w in result.provenance.warnings:
        say(f"      ! {w}")

    # One quantity per file: forces (total / active / passive), activations,
    # fibre and tendon lengths (raw and normalised), fibre velocities,
    # pennation, and the reserves -- which get their own file because they are
    # indexed by COORDINATE, not by muscle.
    _prune_legacy(out_dir)
    written += result.write_outputs(out_dir)
    forces_path = os.path.join(out_dir, "MuscleForces.sto")
    say(f"      wrote {len(written)} output files "
        f"(forces, activations, fibre/tendon lengths, reserves)")

    if ceinms_compat:
        p = result.write_sto(forces_output_path(trial_dir))
        written.append(p)
        say(f"      also wrote {os.path.relpath(p, trial_dir)} (CEINMS-compatible)")

    # ---- 2. comparison against SO / CEINMS --------------------------------
    tables = {}
    if compare:
        say("\n[2/4] comparing against existing results")
        for label, path in (("static_optimisation", found.get("so_forces")),
                            ("ceinms", found.get("ceinms_forces"))):
            if not path:
                say(f"      {label}: not present in this trial, skipped")
                continue
            df = _compare.compare_forces(result, path, label=label)
            tables[label] = df
            csv = os.path.join(out_dir, f"comparison_vs_{label}.csv")
            df.to_csv(csv, index=False)
            written.append(csv)
            say(f"      vs {label}:")
            say(_compare.summarise(df))

        # How far apart are the EXISTING references? Without this, "we disagree
        # with SO by X" has nothing to be measured against -- and on this trial
        # SO and CEINMS disagree with each other more than either does with us.
        so_p, ce_p = found.get("so_forces"), found.get("ceinms_forces")
        if so_p and ce_p:
            try:
                base = _compare.compare_files(so_p, ce_p, result.times,
                                              label="SO_vs_CEINMS")
                tables["so_vs_ceinms"] = base
                base.to_csv(os.path.join(out_dir, "baseline_so_vs_ceinms.csv"),
                            index=False)
                written.append(os.path.join(out_dir, "baseline_so_vs_ceinms.csv"))
                say("      BASELINE -- your existing SO vs your existing CEINMS:")
                say(_compare.aggregate_line(base))
            except Exception as exc:
                say(f"      baseline SO-vs-CEINMS failed: {exc}")

    if plot:
        png = _compare.plot_comparison(
            result,
            {"static optimisation": found.get("so_forces"),
             "CEINMS": found.get("ceinms_forces")},
            os.path.join(out_dir, "muscle_forces.png"))
        if png:
            written.append(png)
            say(f"      figure: {os.path.relpath(png, trial_dir)}")

    # ---- 3. JointReaction forces file ------------------------------------
    jcf_report, jra_path, jcf_error = None, None, None
    if jcf:
        say("\n[3/4] building the JointReaction forces file")
        try:
            jra_forces = os.path.join(out_dir, "JRA_forces.sto")
            jra_forces, jcf_report = _jcf.build_forces_file(
                result, found.get("so_forces"), jra_forces)
            written.append(jra_forces)
            say(f"      merged {jcf_report['n_added']} residual/reserve/GRF columns "
                f"from Static Optimisation")
            say(f"      {len(jcf_report['reserves_from_own_solve'])} reserve column(s) "
                f"replaced with this solve's own moment residual")
            if not jcf_report["balanced"]:
                say("      ! forces file may still be unbalanced -- see warnings")
        except Exception as exc:
            jcf_error = f"{type(exc).__name__}: {exc}"
            say(f"      FAILED: {jcf_error}")

        # ---- 4. run the analysis -----------------------------------------
        if jcf_error is None:
            say("\n[4/4] running JointReaction (needs opensim + bioscout)")
            try:
                jra_path = _jcf.run_joint_reaction(
                    model=ma.subject.model, kinematics=found["kinematics"],
                    grf_xml=found.get("grf_xml"), forces_file=jra_forces,
                    out_dir=out_dir, verbose=verbose)
                written.append(jra_path)
                say(f"      wrote {os.path.relpath(jra_path, trial_dir)}")
                for joint in jcf_joints:
                    try:
                        chk = _jcf.sanity_check(jra_path, body_mass, joint=joint)
                        say(f"      {joint:8s} peak {chk['peak_BW']:5.1f} BW  "
                            f"-> {chk['verdict']}")
                    except KeyError:
                        pass
            except Exception as exc:
                jcf_error = f"{type(exc).__name__}: {exc}"
                say(f"      SKIPPED: {jcf_error}")
                say("      (the muscle forces above are written and unaffected)")

    manifest = {
        "trial": os.path.basename(trial_dir),
        "tier": result.tier.label,
        "confidence": round(result.confidence, 3),
        "model": str(ma.subject.model),
        "body_mass": body_mass,
        "n_muscles": len(result.muscles),
        "n_frames": len(result.times),
        "mean_abs_reserve": float(np.mean(np.abs(result.reserves))),
        "peak_abs_reserve": float(np.max(np.abs(result.reserves))),
        "smoothing": result.provenance.weights.get("delta"),
        "filter_hz": result.provenance.weights.get("filter_hz"),
        "files": [os.path.relpath(p, trial_dir) for p in written],
        "jcf": jcf_report,
        "jcf_error": jcf_error,
        "warnings": result.provenance.warnings,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, default=str)

    say(f"\n  -> {out_dir}")
    return {"result": result, "out_dir": out_dir, "written": written,
            "comparisons": tables, "jcf": jcf_report, "jra": jra_path,
            "jcf_error": jcf_error, "manifest": manifest}


#: Output names this package used BEFORE the one-quantity-per-file layout.
#: Left on disk they look like current results and would be read as such.
_LEGACY_OUTPUTS = ("MomentResidual.sto", "MuscleForces_activations.sto",
                   "MuscleForces_provenance.json")


def _prune_legacy(out_dir) -> None:
    """Remove superseded output names from a previous version of this package.

    Best effort: a filesystem that refuses the delete is not a reason to fail a
    run, and the files are this package's own output, never the user's inputs.
    """
    for name in _LEGACY_OUTPUTS:
        p = os.path.join(str(out_dir), name)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
