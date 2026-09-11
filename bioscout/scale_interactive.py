"""`bioscout scale` — scale a model by answering questions, no project needed.

    bioscout scale
    bioscout scale --model generic.osim --static static.trc --mass 78.4
    bioscout scale --dry-run          # decide everything, run nothing

Scaling fails in one of two ways, and only one of them is loud:

  * ScaleTool refuses — a missing file, a marker set naming a body the model
    does not have. Annoying, but it tells you.
  * ScaleTool succeeds on almost no measurements. An empty or near-empty
    MeasurementSet scales every body by 1.0, so the output is generic geometry
    wearing the subject's mass. Nothing downstream can tell, and joint moments
    computed on it look perfectly reasonable.

The second is what this command exists to prevent. It reads the model, the
marker set and the TRC, works out which measurements can actually be built,
shows you that table BEFORE anything runs, and refuses if the segments that
carry the joint moments are not measured.

Marker naming is the usual reason a measurement cannot be built: the defaults
are the Vicon-CGM/powerlifting spellings, and a lab recording ``LSACR`` where
those say ``LPSI``, or ``RLFC`` where they say ``RKNEL``, gets no hip or knee
joint centre and therefore no femur or tibia scaling. Rather than carry a table
of every lab's names, this asks — offering the markers your TRC actually
contains, best guesses first. The answers are printed as a reusable alias map.

Nothing is written until you confirm the summary.
"""
from __future__ import annotations

import glob
import os
import sys

_CANCEL = "\n[scale] cancelled."


# --------------------------------------------------------------- prompting
def ask(prompt, default=None, choices=None):
    """One prompt. Empty input takes the default; Ctrl-C/EOF exits cleanly."""
    while True:
        suffix = f" [{default}]" if default not in (None, "") else ""
        try:
            ans = input(f"  {prompt}{suffix}: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            print(_CANCEL)
            raise SystemExit(1)
        if not ans and default is not None:
            ans = str(default)
        if not ans:
            print("      (required)")
            continue
        if choices and ans not in choices:
            print(f"      pick one of: {', '.join(choices)}")
            continue
        return ans


def pick(prompt, options, default=None, allow_other=True, allow_skip=False):
    """Numbered menu. Accepts the number, the value, 'o' for a free answer, or
    's' to skip. Returns None when skipped."""
    if not options:
        return None if allow_skip else ask(prompt, default)
    print(f"  {prompt}")
    for i, o in enumerate(options, 1):
        print(f"      {i}. {o}")
    extra = []
    if allow_other:
        extra.append("o = type another name")
    if allow_skip:
        extra.append("s = skip this one")
    if extra:
        print(f"      ({'; '.join(extra)})")
    while True:
        try:
            ans = input(f"  choice{f' [{default}]' if default else ''}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(_CANCEL)
            raise SystemExit(1)
        if not ans and default:
            return default
        if allow_skip and ans.lower() == "s":
            return None
        if allow_other and ans.lower() == "o":
            return ask("name")
        if ans.isdigit() and 1 <= int(ans) <= len(options):
            return options[int(ans) - 1]
        if ans in options:
            return ans
        print("      not one of the options")


def confirm(prompt, default=True):
    d = "Y/n" if default else "y/N"
    try:
        ans = input(f"  {prompt} [{d}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(_CANCEL)
        raise SystemExit(1)
    return default if not ans else ans.startswith("y")


def _find(patterns, root=".", limit=12):
    """Files matching any pattern, nearest first — the prompt defaults."""
    hits = []
    for pat in patterns:
        hits += glob.glob(os.path.join(root, pat))
        hits += glob.glob(os.path.join(root, "*", pat))
        hits += glob.glob(os.path.join(root, "*", "*", pat))
    seen, out = set(), []
    for h in sorted(hits, key=lambda p: (p.count(os.sep), p)):
        a = os.path.abspath(h)
        if a not in seen:
            seen.add(a)
            out.append(os.path.relpath(h, root))
    return out[:limit]


# ------------------------------------------------------------ marker names
def resolve_marker_names(trc_markers, model_markers=None, interactive=True,
                         aliases=None, log=print):
    """Ask which of THIS lab's markers stand in for the ones the defaults name.

    Returns ``{expected: actual}`` for every expected marker that is missing and
    was answered. Only asks about markers that are genuinely absent, so a lab
    using the default names is never prompted at all.
    """
    from bioscout.model.scale import measurements as sm

    aliases = dict(aliases or {})
    have = set(trc_markers)
    if model_markers:
        have &= set(model_markers) | set(trc_markers)   # TRC is the binding one
    missing = [m for m in sm.EXPECTED_MARKERS
               if m not in have and aliases.get(m) not in have]
    if not missing:
        log("  marker names: all expected markers present, nothing to map")
        return aliases

    log(f"\n  {len(missing)} marker(s) the defaults expect are not in this TRC.")
    log("  These build the joint centres, so the femur and tibia cannot be")
    log("  measured without them. Pick the equivalent, or skip it.\n")
    for m in missing:
        if not interactive:
            continue
        opts = sm.suggest_alias(m, sorted(trc_markers))
        got = pick(f"{m} — which marker is this?", opts, allow_skip=True)
        if got:
            aliases[m] = got
    chosen = {k: v for k, v in aliases.items() if k != v}
    if chosen:
        log("\n  alias map (reusable — keep it):")
        for k, v in sorted(chosen.items()):
            log(f"      {k}: {v}")
    return aliases


# ------------------------------------------------------------------- floor
#: Without these the segments carrying the joint moments keep their generic
#: size, and nothing downstream can tell.
REQUIRED = {"pelvis": ("pelvis_x", "pelvis_y", "pelvis_z"),
            "right femur": ("femur_r",), "left femur": ("femur_l",),
            "right tibia": ("tibia_r",), "left tibia": ("tibia_l",)}


def floor_gaps(kept):
    """Which required groups the surviving measurements do not cover."""
    names = {k.split(":")[0].strip() for k in kept}
    return [what for what, want in REQUIRED.items()
            if not any(w in n for n in names for w in want)]


# --------------------------------------------------------------------- run
def run(model=None, static=None, markerset=None, mass=None, out=None,
        aliases=None, dry_run=False, yes=False, linear=True, placer=True,
        grf=None):
    """The `bioscout scale` command. Returns a process exit code."""
    print(__doc__.split("Nothing is written")[0].rstrip())
    print("\n" + "=" * 66)

    interactive = not yes
    # -- inputs ----------------------------------------------------------
    if not model:
        opts = _find(["*.osim"])
        model = pick("Generic (unscaled) model .osim", opts) if opts \
            else ask("Generic (unscaled) model .osim")
    if not os.path.isfile(model):
        print(f"[scale] no such model: {model}")
        return 1
    if not static:
        opts = _find(["*.trc"])
        static = pick("Static-trial .trc", opts) if opts else ask("Static-trial .trc")
    if not os.path.isfile(static):
        print(f"[scale] no such TRC: {static}")
        return 1
    if markerset is None and interactive:
        opts = _find(["*marker*.xml", "*Marker*.xml"])
        if opts and confirm("Use a marker-set .xml instead of the model's own markers?",
                            default=False):
            markerset = pick("Marker set .xml", opts)
    if markerset and not os.path.isfile(markerset):
        print(f"[scale] no such marker set: {markerset}")
        return 1

    from bioscout.model.scale import measurements as sm
    _, trc_names, _, _ = sm.read_trc(static)
    model_markers = sm.markerset_file_names(markerset) if markerset else None

    print(f"\n  model      {model}")
    print(f"  static     {static}   ({len(trc_names)} markers)")
    print(f"  marker set {markerset or '(the model’s own)'}")

    # -- mass: prefer what the plates measured ----------------------------
    # The force plates weighed this subject on this day, in what they wore for
    # the trial. A typed-in mass is a different number from a different day and
    # every result normalised to body weight carries the difference.
    measured = None
    if grf is None:
        beside = os.path.join(os.path.dirname(os.path.abspath(static)), "grf.mot")
        grf = beside if os.path.isfile(beside) else None
        if grf:
            print(f"  grf        {grf}   (found beside the static trial)")
    if grf and os.path.isfile(grf):
        measured = sm.mass_from_static_grf(grf, verbose=True)
    elif grf:
        print(f"  [warn] no such GRF file: {grf}")

    if not mass:
        if measured:
            mass = float(ask("Subject mass, kg", f"{measured:.2f}"))
        else:
            mass = float(ask("Subject mass, kg"))
    elif measured and abs(measured - float(mass)) > 0.5:
        print(f"  [note] you gave {float(mass):.2f} kg; the static plates read "
              f"{measured:.2f} kg. Using {float(mass):.2f} kg as asked.")
    if not out:
        stem = os.path.splitext(os.path.basename(model))[0]
        out = ask("Output .osim",
                  os.path.join(os.path.dirname(os.path.abspath(static)),
                               f"{stem}_scaled.osim"))

    # -- marker names ----------------------------------------------------
    aliases = resolve_marker_names(trc_names, model_markers,
                                   interactive=interactive, aliases=aliases)

    # -- what can actually be measured ------------------------------------
    try:
        import opensim as osim
    except Exception as e:
        print(f"\n[scale] cannot import opensim ({e}).")
        return 1
    osim_model = osim.Model(model)
    spec = sm.resolve_spec(sm.DEFAULT_SPEC, aliases)
    trc_for_scaling = static
    if linear:
        aug = os.path.join(os.path.dirname(os.path.abspath(out)),
                           os.path.basename(static).replace(".trc", "_jc.trc"))
        os.makedirs(os.path.dirname(aug), exist_ok=True)
        trc_for_scaling = sm.augment_static_trc(static, aug, aliases=aliases)

    print("\n  measurements that can be built:")
    _, report, skipped = sm.build_measurement_set(
        osim_model, trc_for_scaling, spec=spec, verbose=False,
        model_markers=model_markers)
    for r in report:
        print(f"      ok   {r}")
    for s_ in skipped:
        print(f"      --   {s_}")
    print(f"  {len(report)} of {len(spec)} measurements")

    gaps = floor_gaps(report)
    if gaps:
        print(f"\n[scale] REFUSING: nothing measures {', '.join(gaps)}.")
        print("[scale] Those segments would keep their GENERIC size while the")
        print("[scale] model still loads and solves — the failure no result")
        print("[scale] can show you. Map the missing markers, or use a marker")
        print("[scale] set and static trial that carry them.")
        return 2

    print(f"\n  output     {out}")
    print(f"  mass       {mass} kg    scaling={linear}  marker placement={placer}")
    if dry_run:
        print("\n[scale] --dry-run: nothing written.")
        return 0
    if interactive and not confirm("\n  Scale now?"):
        print(_CANCEL)
        return 1

    # -- run --------------------------------------------------------------
    from bioscout.model.scale import osim_scale as _os
    _os.scale_model(model, static, out, mass=mass, marker_set_file=markerset,
                    linear_scaling=linear, marker_placer=placer,
                    marker_aliases=aliases)
    if not os.path.isfile(out):
        print(f"\n[scale] ScaleTool wrote no model at {out}.")
        return 1
    print(f"\n[scale] wrote {out}")
    try:
        sm.verify_scaled(model, out)
    except Exception as e:                                     # noqa: BLE001
        print(f"[scale] (verification unavailable: {type(e).__name__}: {e})")
    if aliases:
        print("\n[scale] reuse these marker names next time with:")
        print("        bioscout scale " + " ".join(
            f"--alias {k}={v}" for k, v in sorted(aliases.items()) if k != v))
    return 0
