"""End-to-end test through Mew, using files on disk.

Writes a minimal .osim and a bioscout-layout trial folder into a temp dir, then
runs every tier through the public API. Catches the wiring that the pure-solver
selftest cannot: XML parameter parsing, .sto round-trips, time alignment, tier
selection, EMG mapping, and the bioscout output path.

    python -m pytest bioscout/simulate/mew/tests/test_end_to_end.py -v
    python bioscout/simulate/mew/tests/test_end_to_end.py          # no pytest needed
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import pandas as pd

# repo root: <root>/bioscout/simulate/mew/tests/this_file.py
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), *[os.pardir] * 4)))

from bioscout.simulate.mew.io_ports import write_sto, read_storage           # noqa: E402
from bioscout.simulate.mew.tests.synthetic import ToyGeometry, make_trial    # noqa: E402
from bioscout.simulate.mew.types import Tier                                 # noqa: E402


OSIM_MUSCLE = """      <Thelen2003Muscle name="{name}">
        <max_isometric_force>{fmax}</max_isometric_force>
        <optimal_fiber_length>{lopt}</optimal_fiber_length>
        <tendon_slack_length>{lts}</tendon_slack_length>
        <pennation_angle_at_optimal>0.1</pennation_angle_at_optimal>
        <max_contraction_velocity>10</max_contraction_velocity>
      </Thelen2003Muscle>
"""


def write_toy_osim(path, params):
    body = "".join(
        OSIM_MUSCLE.format(name=n, fmax=f, lopt=lo, lts=lt)
        for n, f, lo, lt in zip(params.names, params.f_max, params.l_opt, params.l_ts))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<OpenSimDocument Version="40000">\n'
                 '  <Model name="toy">\n    <ForceSet>\n      <objects>\n'
                 + body + "      </objects>\n    </ForceSet>\n  </Model>\n"
                 "</OpenSimDocument>\n")
    return path


def build_trial(root):
    """A bioscout-layout trial with ik / id / emg, plus the .osim beside it."""
    g = ToyGeometry()
    params = g.parameters()
    t, q = make_trial()

    mtu_params = params
    from bioscout.simulate.mew.mtu import build_mtu
    mtu = build_mtu(mtu_params)
    l_mt, R = g.mtu_lengths(q), g.moment_arms(q)
    v_mt = np.gradient(l_mt, t, axis=0)

    phase = np.linspace(0, 2 * np.pi, len(t))
    a_true = np.clip(np.column_stack(
        [0.5 * np.sin(phase + k * 0.4) ** 2 for k in range(len(g.muscles))]) + 0.02,
        0, 1)
    f_true = np.array([mtu.force(a_true[i], mtu.state(l_mt[i], v_mt[i]))
                       for i in range(len(t))])
    M = np.einsum("tdm,tm->td", R, f_true)

    os.makedirs(os.path.join(root, "external_biomechanics"), exist_ok=True)
    os.makedirs(os.path.join(root, "inputs"), exist_ok=True)

    write_sto(os.path.join(root, "external_biomechanics", "joint_angles.mot"),
              t, g.dofs, q[g.dofs].to_numpy(float), name="Coordinates")
    write_sto(os.path.join(root, "external_biomechanics", "inverse_dynamics.sto"),
              t, [f"{d}_moment" for d in g.dofs], M, name="InverseDynamics")
    write_sto(os.path.join(root, "inputs", "emg_filtered_normalised.mot"),
              t, ["EXT", "FLEX"], np.column_stack([a_true[:, 0], a_true[:, 3]]),
              name="EMG")

    osim = write_toy_osim(os.path.join(root, "toy.osim"), params)
    emg_map = {"EXT": ["ext_a", "ext_b"], "FLEX": ["flex_a", "flex_b"]}
    return osim, emg_map, a_true, f_true


def test_end_to_end(verbose=True):
    from bioscout.simulate.mew import Mew
    from bioscout.simulate.mew.bioscout_adapter import discover_trial, forces_output_path

    tmp = tempfile.mkdtemp(prefix="ma_e2e_")
    trial = os.path.join(tmp, "Run_test")
    os.makedirs(trial, exist_ok=True)
    osim, emg_map, a_true, f_true = build_trial(trial)

    found = discover_trial(trial)
    assert found["kinematics"] and found["moments"] and found["emg"], found

    ma = Mew.from_trial_dir(
        trial, osim, height=1.81, mass=78.0, emg_map=emg_map,
        geometry=ToyGeometry())

    # ---- tier selection picks EMG_INFORMED without being told ------------
    res = ma.run()
    assert res.tier == Tier.EMG_INFORMED, res.tier
    assert res.forces.shape == (len(res.times), len(res.muscles))
    assert np.isfinite(res.forces).all()
    assert res.provenance.emg_channels == ["EXT", "FLEX"], res.provenance.emg_channels
    assert res.provenance.parameter_source.startswith("scaled:")
    if verbose:
        print("  auto tier:", res.summary())

    # ---- the ladder, and confidence ordering ----------------------------
    prev_conf = -1.0
    for tier in (Tier.KINEMATICS_ONLY, Tier.STATIC_OPT, Tier.EMG_INFORMED):
        r = ma.run(tier=tier)
        if verbose:
            print(f"  {tier.label:22s} confidence {r.confidence:.3f}  "
                  f"mean|residual| {np.mean(np.abs(r.moment_residual)):8.3f} Nm")
        assert r.confidence > prev_conf, f"{tier.label} did not improve confidence"
        prev_conf = r.confidence
    assert ma.run(tier=Tier.KINEMATICS_ONLY).provenance.moment_source == "scaled_template"

    # ---- pinning a tier the inputs cannot support must FAIL loudly -------
    try:
        ma.run(tier=Tier.CALIBRATED_HYBRID)
        raise AssertionError("pinning tier 3 without calibration should have raised")
    except ValueError:
        pass

    # ---- .sto round-trip in the CEINMS-compatible location ---------------
    out = res.write_sto(forces_output_path(trial), extra=True)
    assert out.endswith(os.path.join("ceinms", "Optimised", "MuscleForces.sto"))
    back = read_storage(out)
    assert list(back.columns) == ["time"] + res.muscles
    assert np.allclose(back[res.muscles].to_numpy(), res.forces, atol=1e-6)
    assert os.path.exists(os.path.join(os.path.dirname(out),
                                       "MuscleForces_provenance.json"))
    if verbose:
        print(f"  wrote and re-read {out}")
        print("\n  END-TO-END PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(test_end_to_end())
