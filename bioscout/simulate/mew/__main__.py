"""CLI:  python -m bioscout.simulate.mew <command> ...

    analyse <trial_dir> --model M.osim [--jcf]   forces + JCF + comparisons -> <trial>/mew/
    run <trial_dir> --model M.osim [--height 1.81 --mass 78] [--tier 2] [--write]
    tiers <trial_dir> --model M.osim        solve at every supported tier
    inspect <trial_dir>                     which inputs exist, which tier they reach
    selftest                                synthetic end-to-end check, no data needed
"""
from __future__ import annotations

import argparse
import os
import sys


def _add_common(p):
    p.add_argument("trial_dir")
    p.add_argument("--model", required=True, help="path to the base .osim")
    p.add_argument("--height", type=float, default=None, help="metres")
    p.add_argument("--mass", type=float, default=None, help="kg")
    p.add_argument("--theta", default=None, help="calibrated parameters .json")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("bioscout.simulate.mew", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", metavar="COMMAND")

    r = _add_common(sub.add_parser("run", help="solve one trial"))
    r.add_argument("--tier", type=int, default=None, choices=[0, 1, 2, 3])
    r.add_argument("--write", action="store_true",
                   help="write ceinms/Optimised/MuscleForces.sto")

    a = _add_common(sub.add_parser(
        "analyse", help="forces + JCF + comparisons into <trial>/mew/"))
    a.add_argument("--tier", type=int, default=None, choices=[0, 1, 2, 3])
    a.add_argument("--jcf", action="store_true",
                   help="also run JointReaction (needs opensim + bioscout)")
    a.add_argument("--ceinms-compat", action="store_true",
                   help="ALSO write ceinms/Optimised/MuscleForces.sto")
    a.add_argument("--no-plot", action="store_true")
    a.add_argument("--smoothing", type=float, default=None, metavar="W",
                   help="solver temporal-smoothing weight (default 0.5; "
                        "0 = off, frames solved independently)")
    a.add_argument("--filter-hz", type=float, default=None, metavar="HZ",
                   help="ALSO low-pass the outputs after solving (for figures; "
                        "filtered forces no longer reproduce the moments)")

    _add_common(sub.add_parser("tiers", help="solve at every supported tier"))

    i = sub.add_parser("inspect", help="which inputs exist and what tier they reach")
    i.add_argument("trial_dir")

    sub.add_parser("selftest", help="synthetic end-to-end check")

    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 1

    if args.cmd == "selftest":
        from .tests.synthetic import selftest
        return selftest()

    if args.cmd == "inspect":
        from .bioscout_adapter import discover_trial
        found = discover_trial(args.trial_dir)
        for k, v in found.items():
            mark = "OK  " if v else "--  "
            print(f"  {mark}{k:14s} {v or '(missing)'}")
        have_m, have_e = bool(found["moments"]), bool(found["emg"])
        tier = 2 if (have_m and have_e) else (1 if have_m else 0)
        print(f"\n  reachable tier: {tier} "
              f"({'emg_informed' if tier == 2 else 'static_optimisation' if tier == 1 else 'kinematics_only'})"
              f"{'  (tier 3 also needs --theta)' if tier == 2 else ''}")
        return 0

    if args.cmd == "analyse":
        from .pipeline import analyse_trial
        out = analyse_trial(
            args.trial_dir, args.model, height=args.height, mass=args.mass,
            tier=args.tier, jcf=args.jcf, plot=not args.no_plot,
            smoothing=args.smoothing, filter_hz=args.filter_hz,
            ceinms_compat=args.ceinms_compat, theta_file=args.theta)
        return 0 if out["jcf_error"] is None or not args.jcf else 2

    from .analyser import Mew
    from .bioscout_adapter import analyser_from_trial_dir, forces_output_path

    ma = analyser_from_trial_dir(
        args.trial_dir, args.model, height=args.height, mass=args.mass,
        theta_file=args.theta)

    if args.cmd == "tiers":
        for label, res in ma.run_all_tiers().items():
            if isinstance(res, Exception):
                print(f"  {label:22s} FAILED: {res}")
            else:
                print(f"  {label:22s} {res.summary()}")
        return 0

    from .types import Tier
    res = ma.run(tier=Tier(args.tier) if args.tier is not None else None)
    print(res.summary())
    for w in res.provenance.warnings:
        print(f"  ! {w}")
    if args.write:
        out = res.write_sto(forces_output_path(args.trial_dir), extra=True)
        print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
