"""bioscout.model.scale_muscle_forces - allometric and athlete-specific Fmax scaling (session.yaml `fmax_scaling`).

Maximum isometric force is proportional to PCSA = V / Lopt. OpenSim's ScaleTool
changes segment lengths (and so Lopt/Lts) and segment masses, but it never
touches max_isometric_force. A generic 75 kg model scaled to a 91 kg athlete
therefore keeps 75 kg muscles. This module restores the missing strength from
MRI-based volume data:

Handsfield et al. (2014) J Biomech 47:631-638, n = 24 healthy adults (Fig. 5)
    V_tot = 47 * m * h + 1285        R2 = 0.92   (cm3; m in kg, h in m)  [default]
    V_tot = 91 * m + 588             R2 = 0.85
    V_tot = 119 * h - 13361          R2 = 0.64   (h in cm)
    V_tot is the total unilateral lower-limb muscle volume. Individual muscle
    volumes are a near-constant fraction of V_tot (Fig. 2A), so every muscle
    scales with the same volume ratio.

Handsfield et al. (2017) Scand J Med Sci Sports 27:1050-1060, elite sprinters
    Muscle volume per height-mass was 22 % larger in total than in the 2014
    non-sprinters, and the increase was not uniform (Table 1). SPRINTER_PCT_DIFF
    holds the per-muscle % differences, available as an optional "trained athlete"
    profile (sprinters, not powerlifters: use it as a documented proxy).

Scaling rule applied to each muscle i:

    V_ratio   = V_tot(subject) / V_tot(reference)
    F_i'      = F_i * V_ratio / L_ratio * A_i * extra

    L_ratio   = length scale of the muscle (Lopt' / Lopt, taken from the model
                pair when given; 1.0 otherwise, i.e. volume ratio only)
    A_i       = 1 + SPRINTER_PCT_DIFF[muscle] / 100 when athlete="sprinter", else 1
    extra     = free multiplier (e.g. the old mvic factor), default 1

Reference: the Rajagopal-family generics (Rajagopal, Lernagopal, GPK) were built
from the Handsfield 2014 volumes for a 1.70 m, 75.337 kg subject, which are the
defaults below.
"""
from __future__ import annotations

import re

REF_MASS_KG = 75.337
REF_HEIGHT_M = 1.70

# Handsfield 2014, Fig. 5 (cm3)
def total_muscle_volume(mass_kg: float, height_m: float | None = None,
                        method: str = "height_mass") -> float:
    """Total unilateral lower-limb muscle volume (cm3), Handsfield et al. 2014."""
    if method == "height_mass":
        return 47.0 * mass_kg * height_m + 1285.0
    if method == "mass":
        return 91.0 * mass_kg + 588.0
    if method == "height":
        return 119.0 * (height_m * 100.0) - 13361.0
    raise ValueError("method must be 'height_mass', 'mass' or 'height'")


def volume_ratio(mass_kg, height_m, ref_mass_kg=REF_MASS_KG,
                 ref_height_m=REF_HEIGHT_M, method="height_mass") -> float:
    return (total_muscle_volume(mass_kg, height_m, method)
            / total_muscle_volume(ref_mass_kg, ref_height_m, method))


# Handsfield 2017, Table 1: non-sprinter normalised volume (cm3 / kg-m, from the
# 2014 cohort) and % difference sprinter vs non-sprinter.
NONSPRINT_NORM_VOL = {
    "semitendinosus": 1.5, "gracilis": 0.9, "tensor_fasciae_latae": 0.5,
    "rectus_femoris": 2.2, "sartorius": 1.3, "obturator_externus": 0.4,
    "gluteus_maximus": 6.9, "vastus_medialis": 3.5, "vastus_intermedius": 2.2,
    "piriformis": 0.4, "tibialis_posterior": 0.9, "adductor_magnus": 4.6,
    "vastus_lateralis": 6.8, "biceps_femoris_lh": 1.7, "biceps_femoris_sh": 0.8,
    "adductor_longus": 1.3, "pectineus": 0.5, "quadratus_femoris": 0.3,
    "adductor_brevis": 0.8, "semimembranosus": 2.0, "psoas": 2.2, "gemelli": 0.1,
    "peroneals": 1.1, "gluteus_medius": 2.6, "gastrocnemius_lateral": 1.2,
    "obturator_internus": 0.2, "soleus": 3.6, "iliacus": 1.4,
    "gastrocnemius_medial": 2.1, "popliteus": 0.2, "tibialis_anterior": 1.1,
    "flexor_hallucis_longus": 0.6, "digital_extensors": 0.8,
    "gluteus_minimus": 0.9, "flexor_digitorum_longus": 0.2,
}
SPRINTER_PCT_DIFF = {
    "semitendinosus": 54, "gracilis": 42, "tensor_fasciae_latae": 41,
    "rectus_femoris": 40, "sartorius": 37, "obturator_externus": 32,
    "gluteus_maximus": 31, "vastus_medialis": 30, "vastus_intermedius": 29,
    "piriformis": 28, "tibialis_posterior": 28, "adductor_magnus": 26,
    "vastus_lateralis": 26, "biceps_femoris_lh": 26, "biceps_femoris_sh": 26,
    "adductor_longus": 25, "pectineus": 24, "quadratus_femoris": 22,
    "adductor_brevis": 21, "semimembranosus": 20, "psoas": 19, "gemelli": 18,
    "peroneals": 11, "gluteus_medius": 8, "gastrocnemius_lateral": 7,
    "obturator_internus": 7, "soleus": 6, "iliacus": 6,
    "gastrocnemius_medial": 4, "popliteus": 4, "tibialis_anterior": 2,
    "flexor_hallucis_longus": 1, "digital_extensors": 1,
    "gluteus_minimus": -3, "flexor_digitorum_longus": -8,
}
SPRINTER_TOTAL_PCT_DIFF = 22   # total lower-limb volume per height-mass

# OpenSim muscle-name prefix (side suffix and compartment digit stripped) -> Handsfield muscle
MUSCLE_MAP = {
    "addbrev": "adductor_brevis", "addlong": "adductor_longus",
    "addmag": "adductor_magnus", "bflh": "biceps_femoris_lh",
    "bfsh": "biceps_femoris_sh", "edl": "digital_extensors",
    "ehl": "digital_extensors", "fdl": "flexor_digitorum_longus",
    "fhl": "flexor_hallucis_longus", "gaslat": "gastrocnemius_lateral",
    "gasmed": "gastrocnemius_medial", "glmax": "gluteus_maximus",
    "glmed": "gluteus_medius", "glmin": "gluteus_minimus", "grac": "gracilis",
    "iliacus": "iliacus", "perbrev": "peroneals", "perlong": "peroneals",
    "piri": "piriformis", "psoas": "psoas", "recfem": "rectus_femoris",
    "sart": "sartorius", "semimem": "semimembranosus",
    "semiten": "semitendinosus", "soleus": "soleus",
    "tfl": "tensor_fasciae_latae", "tibant": "tibialis_anterior",
    "tibpost": "tibialis_posterior", "vasint": "vastus_intermedius",
    "vaslat": "vastus_lateralis", "vasmed": "vastus_medialis",
    "quad_fem": "quadratus_femoris", "obt_internus": "obturator_internus",
    "obt_externus": "obturator_externus", "gemelli": "gemelli",
    "pect": "pectineus",
}


def handsfield_name(osim_muscle: str) -> str | None:
    """'glmax2_r' -> 'gluteus_maximus'; 'addmagDist_l' -> 'adductor_magnus'."""
    base = re.sub(r"_[lr]$", "", osim_muscle)
    for key in sorted(MUSCLE_MAP, key=len, reverse=True):
        if base.startswith(key):
            return MUSCLE_MAP[key]
    return None


def athlete_factor(osim_muscle: str, athlete: str | None = None) -> float:
    """1 + % difference / 100 for the muscle, or 1 (no profile / unmapped muscle)."""
    if athlete is None:
        return 1.0
    if athlete != "sprinter":
        raise ValueError("only athlete='sprinter' (Handsfield 2017) is available")
    name = handsfield_name(osim_muscle)
    if name is None:
        return 1.0 + SPRINTER_TOTAL_PCT_DIFF / 100.0
    return 1.0 + SPRINTER_PCT_DIFF[name] / 100.0


_MUSCLE = re.compile(r'(<(\w*Muscle\w*) name="([^"]+)">)(.*?)(</\2>)', re.S)


def _lopt(block):
    m = re.search(r"<optimal_fiber_length>([^<]+)<", block)
    return float(m.group(1)) if m else None


def scale_max_isometric_force(model_in: str, model_out: str, mass_kg: float,
                              height_m: float | None, *,
                              ref_mass_kg: float = REF_MASS_KG,
                              ref_height_m: float = REF_HEIGHT_M,
                              method: str = "height_mass",
                              generic_model: str | None = None,
                              athlete: str | None = None,
                              extra: float = 1.0) -> dict:
    """Write model_out with scaled max_isometric_force; return {muscle: factor}.

    generic_model: the unscaled generic .osim. If given, each muscle's Lopt ratio
    (scaled / generic) is used as L_ratio, so F scales with PCSA = V / L.
    Without it, F scales with the volume ratio only.
    Text edit only; no OpenSim needed. Only max_isometric_force is changed.
    """
    vr = volume_ratio(mass_kg, height_m, ref_mass_kg, ref_height_m, method)
    txt = open(model_in, encoding="utf-8", newline="").read()
    ref_lopt = {}
    if generic_model:
        g = open(generic_model, encoding="utf-8").read()
        ref_lopt = {m.group(3): _lopt(m.group(4)) for m in _MUSCLE.finditer(g)}
    factors = {}

    def fix(m):
        name, body = m.group(3), m.group(4)
        if name == "default" or "<max_isometric_force>" not in body:
            return m.group(0)
        l_ratio = 1.0
        if ref_lopt.get(name) and _lopt(body):
            l_ratio = _lopt(body) / ref_lopt[name]
        f = vr / l_ratio * athlete_factor(name, athlete) * extra
        factors[name] = f
        body = re.sub(r"<max_isometric_force>([^<]+)<",
                      lambda k: "<max_isometric_force>%.6f<" % (float(k.group(1)) * f), body)
        return m.group(1) + body + m.group(5)

    out = _MUSCLE.sub(fix, txt)
    open(model_out, "w", encoding="utf-8", newline="").write(out)
    return factors


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("model_in"); p.add_argument("model_out")
    p.add_argument("--mass", type=float, required=True)
    p.add_argument("--height", type=float, help="m (required unless --method mass)")
    p.add_argument("--method", default="height_mass", choices=["height_mass", "mass", "height"])
    p.add_argument("--generic", help="unscaled generic .osim for the Lopt ratio")
    p.add_argument("--athlete", choices=["sprinter"])
    p.add_argument("--extra", type=float, default=1.0)
    a = p.parse_args()
    fac = scale_max_isometric_force(a.model_in, a.model_out, a.mass, a.height,
                                    method=a.method, generic_model=a.generic,
                                    athlete=a.athlete, extra=a.extra)
    vals = sorted(fac.values())
    print("V_ratio %.3f | %d muscles scaled, factor %.3f..%.3f (median %.3f) -> %s"
          % (volume_ratio(a.mass, a.height, method=a.method), len(vals),
             vals[0], vals[-1], vals[len(vals) // 2], a.model_out))
