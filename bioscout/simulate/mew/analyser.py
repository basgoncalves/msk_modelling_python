"""Mew -- the public facade.

    ma = Mew(model="Rajagopal2015.osim", height=1.81, mass=78,
             kinematics="joint_angles.mot")
    res = ma.run()
    print(res.summary())

Everything optional is optional. The class figures out which tier the inputs
support, runs it, and hands back a result that says what it did.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from . import excitation, geometry as geo, tiers
from .io_ports import as_frame, common_time, derivative, resample
from .mtu import MuscleParameters, build_mtu, scale_parameters
from dataclasses import replace

from .solver import FrameSolver, SolverWeights
from .types import MuscleForceResult, Provenance, SubjectSpec, Tier, TrialInputs


class Mew:
    """Muscle forces from whatever inputs exist, with a tier and a confidence."""

    def __init__(self, model=None, *, height=None, mass=None, name="subject",
                 kinematics=None, moments=None, grf=None, emg=None,
                 moment_arms=None, emg_map=None, time_range=None, side="both",
                 trial_type=None, trial_name="trial", theta_file=None,
                 subject: Optional[SubjectSpec] = None,
                 inputs: Optional[TrialInputs] = None,
                 muscles: Optional[Sequence[str]] = None,
                 dofs: Optional[Sequence[str]] = None,
                 tendon="auto", geometry=None):
        self.subject = subject or SubjectSpec(
            model=model, height=height, mass=mass, name=name, theta_file=theta_file)
        self.inputs = inputs or TrialInputs(
            kinematics=kinematics, moments=moments, grf=grf, emg=emg,
            moment_arms=moment_arms, emg_map=emg_map or {}, time_range=time_range,
            side=side, trial_type=trial_type, name=trial_name)
        self._muscles = list(muscles) if muscles else None
        self._dofs = list(dofs) if dofs else None
        self.tendon = tendon
        self._geometry = geometry
        self._params: Optional[MuscleParameters] = None
        self.ml_prior = None            # set to an ml.SurrogateSolver to use eps

    # ------------------------------------------------------------------ #
    #  Constructors
    # ------------------------------------------------------------------ #
    @classmethod
    def from_bioscout(cls, iteration, trial, **kw) -> "Mew":
        """Build from a bioscout ``Iteration`` and trial name. See bioscout_adapter."""
        from .bioscout_adapter import analyser_from_iteration
        return analyser_from_iteration(iteration, trial, **kw)

    @classmethod
    def from_trial_dir(cls, trial_dir, model, **kw) -> "Mew":
        """Build from a bioscout-layout trial folder, without importing bioscout."""
        from .bioscout_adapter import analyser_from_trial_dir
        return analyser_from_trial_dir(trial_dir, model, **kw)

    # ------------------------------------------------------------------ #
    #  Parameters and geometry
    # ------------------------------------------------------------------ #
    def parameters(self) -> MuscleParameters:
        """Calibrated theta if available, else generic scaled by height/mass."""
        if self._params is not None:
            return self._params

        base = geo.read_model_parameters(self.subject.model, self._muscles)
        theta = self.subject.theta_file
        if theta and os.path.exists(str(theta)):
            with open(theta, "r", encoding="utf-8") as fh:
                loaded = MuscleParameters.from_dict(json.load(fh))
            common = [m for m in base.names if m in loaded.names]
            if not common:
                raise ValueError(f"{theta} shares no muscles with {self.subject.model}")
            self._params = loaded.subset(common)
            self._params.source = f"calibrated:{os.path.basename(str(theta))}"
        else:
            self._params = scale_parameters(
                base, height=self.subject.height, mass=self.subject.mass)
        return self._params

    def geometry(self) -> geo.GeometryProvider:
        if self._geometry is None:
            self._geometry = geo.build_geometry(
                osim=self.subject.model, ma_dir=self.inputs.moment_arms,
                muscles=self._muscles, dofs=self._dofs)
        return self._geometry

    # ------------------------------------------------------------------ #
    #  Run
    # ------------------------------------------------------------------ #
    def run(self, *, tier: Optional[Tier] = None,
            weights: Optional[SolverWeights] = None,
            smoothing: Optional[float] = None, filter_hz: Optional[float] = None,
            emg_delay=0.045, emg_gains=None) -> MuscleForceResult:
        """Solve the trial at the highest supported tier (or a pinned one).

        Two independent smoothing controls, because they are genuinely different
        things and conflating them would hide which one produced a result:

        ``smoothing``
            The solver's temporal-coupling weight (``SolverWeights.delta``).
            This is smoothing done DURING the solve: each frame is penalised for
            departing from the previous frame's activations, so the solution
            picked is a smooth one that still satisfies the moment constraint.
            ``0`` turns it off and gives frame-independent solving -- the same
            regime OpenSim SO runs in, chatter included. Physiologically it is
            the defensible kind: activation cannot jump discontinuously.

        ``filter_hz``
            A zero-lag low-pass applied to the OUTPUTS after solving. Cosmetic
            by comparison: it makes the traces look smooth but the filtered
            forces no longer exactly reproduce the tracked moments. Off by
            default. Use it for figures, not for anything you then integrate,
            differentiate, or feed to JointReaction.

        Prefer ``smoothing``; reach for ``filter_hz`` only when you know why.
        """
        sub, inp = self.subject, self.inputs

        chosen_tier, moment_source, preset, warnings = tiers.select_tier(
            inp, sub, pin=tier)
        w = weights or preset
        if smoothing is not None:
            w = replace(w, delta=float(smoothing))
            if float(smoothing) == 0.0:
                warnings.append(
                    "solver smoothing is OFF (smoothing=0): frames are solved "
                    "independently, so expect frame-to-frame chatter like SO's")

        # -- align every signal onto the kinematics clock ------------------
        q = as_frame(inp.kinematics, "kinematics")
        emg_df = as_frame(inp.emg, "emg") if inp.emg is not None else None
        others = [as_frame(inp.moments, "moments") if inp.moments is not None else None]
        # EMG constrains the window ONLY when it is actually used. Otherwise a
        # short EMG file would silently shorten a tier-1 solve that never reads it.
        if w.gamma > 0 and emg_df is not None:
            others.append(emg_df)
        times = common_time([f for f in others if f is not None], q, inp.time_range)
        q = resample(q, times)

        # -- geometry ------------------------------------------------------
        g = self.geometry()
        muscles = list(g.muscles)
        dofs = list(g.dofs)
        l_mt = g.mtu_lengths(q)                       # (nt, nm)
        R = g.moment_arms(q)                          # (nt, ndof, nm)
        v_mt = derivative(l_mt, times)

        params = self.parameters().subset(
            [m for m in muscles if m in self.parameters().names])
        if params.n != len(muscles):
            missing = [m for m in muscles if m not in params.names]
            warnings.append(f"{len(missing)} muscle(s) in the geometry have no "
                            f"parameters and were dropped, e.g. {missing[:3]}")
            keep = [i for i, m in enumerate(muscles) if m in params.names]
            muscles = [muscles[i] for i in keep]
            l_mt, v_mt, R = l_mt[:, keep], v_mt[:, keep], R[:, :, keep]

        # -- moments to track ---------------------------------------------
        M = moment_source.moments(times, dofs, inp, sub)

        # Drop DOFs no muscle can actuate (pelvis translations, and any
        # coordinate whose moment arms are all ~0 for this muscle set). Left in,
        # they contribute their FULL moment to the residual every frame -- the
        # solve is unaffected but the confidence score is permanently poisoned
        # by moments that were never the muscles' job. Found on FAIS 009/RunL1,
        # 2026-09-02: 7.25 Nm "unexplained" was almost entirely pelvis DOFs.
        actuated = np.max(np.abs(R), axis=(0, 2)) > 1e-4     # (ndof,)
        if not actuated.all():
            dropped = [d for d, ok in zip(dofs, actuated) if not ok]
            warnings.append(
                f"{len(dropped)} DOF(s) have no muscle moment arm and were "
                f"excluded from moment tracking: {dropped[:6]}"
                + (" ..." if len(dropped) > 6 else ""))
            keep_d = np.flatnonzero(actuated)
            dofs = [dofs[i] for i in keep_d]
            R = R[:, keep_d, :]
            M = M[:, keep_d]
        if not dofs:
            raise ValueError(
                "no coordinate in the geometry has a non-zero moment arm -- "
                "check that the moment-arm tables and the model muscles match")

        # -- EMG -----------------------------------------------------------
        a_emg, emg_mask, channels = excitation.emg_targets(
            emg_df if w.gamma > 0 else None,
            inp.emg_map, muscles, params, times,
            gains=emg_gains, delay_s=emg_delay)
        if w.gamma > 0 and not emg_mask.any():
            warnings.append("EMG tracking weight is non-zero but no channel maps "
                            "onto a model muscle -- check emg_map")

        # -- ML prior ------------------------------------------------------
        a_prior = None
        if self.ml_prior is not None and w.eps > 0:
            a_prior = self.ml_prior.activations(q, muscles, times)

        # -- solve ---------------------------------------------------------
        mtu = build_mtu(params, tendon=self.tendon)
        dt = float(np.median(np.diff(times))) if len(times) > 1 else None
        sol = FrameSolver(mtu, w).solve(l_mt, v_mt, R, M,
                                        a_emg=a_emg, emg_mask=emg_mask,
                                        a_prior=a_prior, dt=dt)
        if sol.n_failed:
            warnings.append(f"{sol.n_failed}/{len(times)} frames fell back to the "
                            "previous frame's activations (solver did not converge)")

        # The single most useful diagnostic: a muscle parked far down the
        # ascending limb cannot make force whatever the solver does, and the
        # moment silently goes to the reserves instead.
        op = mtu.operating_range(l_mt)
        weak = [(m, float(f), float(r)) for m, f, r in
                zip(op["muscles"], op["mean_f_L"], op["tendon_ratio"]) if f < 0.6]
        if weak:
            weak.sort(key=lambda x: x[1])
            warnings.append(
                f"{len(weak)} muscle(s) operate below 0.6 of peak force-length "
                f"and cannot reach their rated force -- worst: "
                + ", ".join(f"{m} (f_L={f:.2f}, tendon/fibre={r:.1f})"
                            for m, f, _r in weak[:4] for r in [_r])
                + ". This is generic tendon slack length, not a solver failure: "
                  "calibrate l_ts (tier 3) before trusting these muscles.")

        prov = Provenance(
            model=str(sub.model), model_hash=sub.model_hash, subject=sub.name,
            trial=inp.name, tier=chosen_tier.label, moment_source=moment_source.name,
            parameter_source=params.source, geometry_source=g.source,
            emg_channels=channels, weights=w.as_dict(), solver=sol.method,
            warnings=warnings)

        res = MuscleForceResult(
            times=times, muscles=muscles, forces=sol.forces,
            activations=sol.activations, tier=chosen_tier, dofs=dofs,
            moment_residual=sol.residual, moment_target=M,
            series=sol.series, provenance=prov)

        if filter_hz:
            _apply_output_filter(res, float(filter_hz))
            prov.warnings.append(
                f"outputs low-pass filtered at {filter_hz} Hz AFTER solving -- "
                "the filtered forces no longer exactly reproduce the tracked "
                "moments, so do not feed them to JointReaction")
            prov.weights = dict(prov.weights, filter_hz=float(filter_hz))
        res.confidence = tiers.score_confidence(
            chosen_tier, moment_source, sol.residual, M,
            n_failed=sol.n_failed, n_frames=len(times))
        return res

    # ------------------------------------------------------------------ #
    def run_all_tiers(self) -> Dict[str, MuscleForceResult]:
        """Solve at every tier the inputs support -- the degradation-curve figure."""
        out = {}
        top, *_ = tiers.select_tier(self.inputs, self.subject)
        for t in Tier:
            if t > top:
                continue
            try:
                out[t.label] = self.run(tier=t)
            except Exception as exc:                       # keep going, report
                out[t.label] = exc
        return out

    def __repr__(self):
        have = ", ".join(k for k, v in self.inputs.available().items() if v)
        return (f"<Mew {self.subject.name}/{self.inputs.name} "
                f"model={os.path.basename(str(self.subject.model))} have=[{have}]>")


def _apply_output_filter(res: MuscleForceResult, cutoff_hz: float) -> None:
    """Zero-lag low-pass every muscle-indexed output of a result, in place.

    Deliberately does NOT touch ``moment_residual`` / ``moment_target``: the
    reserves are the record of what the UNFILTERED solve could not explain, and
    smoothing them would quietly improve the confidence score without improving
    anything real.
    """
    try:
        from scipy.signal import butter, filtfilt
    except ImportError:
        res.provenance.warnings.append("filter_hz ignored: scipy not available")
        return
    t = res.times
    if len(t) < 20:
        res.provenance.warnings.append(
            f"filter_hz ignored: only {len(t)} frames, too few to filter cleanly")
        return
    fs = 1.0 / float(np.median(np.diff(t)))
    wn = float(cutoff_hz) / (0.5 * fs)
    if not 0 < wn < 1:
        res.provenance.warnings.append(
            f"filter_hz={cutoff_hz} ignored: not below Nyquist ({0.5 * fs:.0f} Hz)")
        return
    b, a = butter(4, wn, btype="low")
    res.forces = filtfilt(b, a, res.forces, axis=0)
    res.activations = np.clip(filtfilt(b, a, res.activations, axis=0), 0.0, 1.0)
    for k, v in res.series.items():
        res.series[k] = filtfilt(b, a, v, axis=0)
