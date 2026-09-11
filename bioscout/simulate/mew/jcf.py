"""Joint contact forces from bioscout.simulate.mew muscle forces.

JCF is not a second model -- it is OpenSim's JointReaction analysis driven by
the muscle forces this package produced. So this module's job is to hand
JointReaction a COMPLETE and BALANCED actuator set, and then call it.

THE TRAP THIS MODULE EXISTS TO AVOID
------------------------------------
JointReaction's ``forces_file`` must contain EVERY actuator in the model, not
just the muscles: the pelvis residuals (FX..MZ), the coordinate reserves, the
lumbar actuators and the external GRF columns. Feed it muscle columns alone and
the analysis cannot balance the dynamics -- it dumps the entire imbalance into
the proximal joint, producing a hip contact force roughly 100x too large that is
also IDENTICAL no matter what the muscle forces were. It looks like a result. It
is not one. bioscout learned this on the CEINMS path (see
``Analyse.add_so_columns_to_ceinms_results``); the same rule applies here.

So :func:`build_forces_file` merges the non-muscle columns from the trial's
Static Optimisation force file into our muscle forces, and REFUSES to write an
unbalanced file unless explicitly told to.

One improvement on the CEINMS path: where a ``<dof>_reserve`` column
corresponds to a DOF this solver actually tracked, we substitute OUR OWN
residual moment rather than SO's. The reserve then means what it says -- the
moment THIS solution could not produce -- instead of silently importing a
different model's leftovers.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .io_ports import read_storage, write_sto, resample
from .types import MuscleForceResult


RESERVE_SUFFIX = "_reserve"
#  Pelvis residual actuators, present in every SO force file for a free-floating
#  model. Without these the JRA is unbalanced no matter what else is right.
RESIDUAL_COLUMNS = ("FX", "FY", "FZ", "MX", "MY", "MZ")


# --------------------------------------------------------------------------- #
#  Building the forces file
# --------------------------------------------------------------------------- #
def build_forces_file(result: MuscleForceResult, so_forces_path, out_path, *,
                      use_own_reserves=True, allow_unbalanced=False
                      ) -> Tuple[str, Dict[str, object]]:
    """Write a JointReaction-ready forces file. Returns ``(path, report)``.

    Parameters
    ----------
    result            what :meth:`Mew.run` returned
    so_forces_path    ``static_optimisation/SO_StaticOptimization_force.sto`` --
                      the source of the residual / reserve / GRF columns
    use_own_reserves  replace ``<dof>_reserve`` with this solve's own moment
                      residual for every DOF we tracked (recommended)
    allow_unbalanced  write muscle columns only. The resulting JCF will be
                      wrong, usually by ~100x at the proximal joint. Only for
                      deliberately inspecting that failure.
    """
    muscles = list(result.muscles)
    df = pd.DataFrame(result.forces, columns=muscles)
    df.insert(0, "time", result.times)

    report: Dict[str, object] = {
        "n_muscle_columns": len(muscles), "n_added": 0,
        "reserves_from_own_solve": [], "balanced": False, "warnings": [],
    }

    have_so = so_forces_path and os.path.exists(str(so_forces_path))
    if not have_so:
        msg = (f"no SO force file at {so_forces_path!r}: the JointReaction "
               "forces file would have muscles only, so the contact force "
               "would be unbalanced (~100x at the hip) and identical whatever "
               "the muscle forces are.")
        if not allow_unbalanced:
            raise FileNotFoundError(
                msg + " Run Static Optimisation for this trial first, or pass "
                "allow_unbalanced=True if you really want the wrong number.")
        report["warnings"].append(msg)
        write_sto(out_path, result.times, muscles, result.forces, name="ModelForces")
        return str(out_path), report

    so = read_storage(so_forces_path)
    so = resample(so, result.times)

    # every SO column that is NOT one of our muscles: residuals, reserves,
    # lumbar actuators, GRF
    extra = [c for c in so.columns if c != "time" and c not in df.columns]
    for c in extra:
        df[c] = so[c].to_numpy(float)
    report["n_added"] = len(extra)

    missing_residuals = [c for c in RESIDUAL_COLUMNS if c not in df.columns]
    if missing_residuals:
        report["warnings"].append(
            f"pelvis residual column(s) {missing_residuals} absent from the SO "
            "force file -- the JRA may still be unbalanced")

    # substitute our own residual for the DOFs we actually solved
    if use_own_reserves and result.moment_residual is not None:
        for j, dof in enumerate(result.dofs):
            col = f"{dof}{RESERVE_SUFFIX}"
            if col in df.columns:
                df[col] = result.moment_residual[:, j]
                report["reserves_from_own_solve"].append(dof)

    report["balanced"] = not missing_residuals
    cols = [c for c in df.columns if c != "time"]
    write_sto(out_path, df["time"].to_numpy(float), cols,
              df[cols].to_numpy(float), name="ModelForces")
    return str(out_path), report


# --------------------------------------------------------------------------- #
#  Running the analysis
# --------------------------------------------------------------------------- #
def run_joint_reaction(model, kinematics, grf_xml, forces_file, out_dir, *,
                       setup_xml=None, save_name="JRA_ReactionLoads.sto",
                       verbose=True) -> str:
    """Call OpenSim's JointReaction through bioscout, writing into ``out_dir``.

    Delegates to ``bioscout.simulate.opensim.run_jra`` rather than reimplementing
    it: that function already handles the setup XML, relative-path rewriting and
    the assembly-accuracy workaround for the coupled knee. Needs opensim and
    bioscout importable -- this is the one part of the pipeline that cannot run
    in pure Python.
    """
    try:
        from bioscout.simulate import opensim as _os                # noqa: WPS433
    except ImportError as exc:
        raise ImportError(
            "joint contact forces need bioscout + opensim importable (this is "
            "the only step that does). Run it from your bioscout conda env; "
            "the muscle forces themselves are already written and need "
            "neither.") from exc

    os.makedirs(out_dir, exist_ok=True)
    setup_xml = setup_xml or os.path.join(out_dir, "setup_JRA_mew.xml")
    save_path = os.path.join(out_dir, save_name)

    if not os.path.exists(setup_xml):
        template = _find_jra_template(out_dir)
        if template:
            import shutil
            shutil.copyfile(template, setup_xml)
            if verbose:
                print(f"  JRA setup copied from {os.path.basename(template)}")

    _os.run_jra(osim_modelPath=str(model), ik_output=str(kinematics),
                grf_xml=str(grf_xml), setup_xml=setup_xml, actuators=None,
                muscle_force_path=str(forces_file), saveFileName=save_path)
    return save_path


def _find_jra_template(out_dir) -> Optional[str]:
    """Reuse the trial's existing JRA setup (SO or CEINMS) as the template."""
    trial = os.path.dirname(os.path.abspath(str(out_dir)))
    jcf_dir = os.path.join(trial, "joint_contact_forces")
    for name in ("setup_JRA_SO.xml", "setup_JRA_CEINMS.xml", "setup_JRA.xml"):
        p = os.path.join(jcf_dir, name)
        if os.path.exists(p):
            return p
    return None


# --------------------------------------------------------------------------- #
#  Reading JCF back
# --------------------------------------------------------------------------- #
def contact_force_magnitude(jra_path, joint="hip_r", body_mass=None
                            ) -> Tuple[np.ndarray, np.ndarray]:
    """``(times, |F|)`` for one joint, in N -- or in body weights if mass is given.

    JRA writes ``<joint>_on_<body>_in_<frame>_f{x,y,z}``; the joint name is
    matched loosely so ``hip_r`` finds ``hip_r_on_femur_r_in_femur_r_fx``.
    """
    df = read_storage(jra_path)
    comp = {}
    for axis in ("fx", "fy", "fz"):
        hit = [c for c in df.columns
               if c.lower().startswith(joint.lower()) and c.lower().endswith(axis)]
        if not hit:
            raise KeyError(
                f"no '{joint}' {axis} column in {os.path.basename(str(jra_path))}. "
                f"Available joints: {sorted({c.split('_on_')[0] for c in df.columns if '_on_' in c})}")
        comp[axis] = df[hit[0]].to_numpy(float)
    mag = np.sqrt(comp["fx"] ** 2 + comp["fy"] ** 2 + comp["fz"] ** 2)
    if body_mass:
        mag = mag / (float(body_mass) * 9.80665)
    return df["time"].to_numpy(float), mag


def sanity_check(jra_path, body_mass, joint="hip_r", max_bw=12.0) -> Dict[str, object]:
    """Is this JCF physiologically possible, or is it the unbalanced-JRA artefact?

    Peak hip contact force in running is ~5-8 body weights. Anything above
    ``max_bw`` is almost certainly a forces file that was missing its residual
    and reserve columns -- the ~100x failure this module is built to prevent.
    """
    t, bw = contact_force_magnitude(jra_path, joint, body_mass)
    peak = float(np.max(bw))
    return {
        "joint": joint, "peak_BW": peak, "mean_BW": float(np.mean(bw)),
        "plausible": peak <= max_bw,
        "verdict": ("plausible" if peak <= max_bw else
                    f"IMPLAUSIBLE ({peak:.0f} BW): the forces file was almost "
                    "certainly missing its residual/reserve columns -- rebuild "
                    "it with jcf.build_forces_file()"),
    }
