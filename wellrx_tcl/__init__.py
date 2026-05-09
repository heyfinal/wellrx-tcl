"""
WellRX TCL — gas well critical-velocity (Turner / Coleman / Lea) library.

Computes the minimum gas velocity (and the corresponding standard-condition rate)
required to lift water or condensate droplets out of a vertical gas well's tubing.

Below the critical rate, the well is at risk of liquid loading: droplets
accumulate, hydrostatic head builds, and gas inflow from the formation chokes off.

Reference: Lea, J. F., Nickens, H. V., & Wells, M. (2008). Gas Well Deliquification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

__version__ = "0.1.0"

# Field defaults — Lea & Nickens 2008
# σ in lbf/ft  (1 dyn/cm × 6.85e-5 = 1 lbf/ft)
# ρ in lb/ft³
_FLUIDS = {
    "water":      {"sigma_dyne_cm": 60.0, "rho_lb_ft3": 67.0},
    "condensate": {"sigma_dyne_cm": 20.0, "rho_lb_ft3": 45.0},
    "mixed":      {"sigma_dyne_cm": 40.0, "rho_lb_ft3": 56.0},
}

# Turner formula coefficients in Lea-form: v_c = K × [σ(ρ_L−ρ_g)]^0.25 / ρ_g^0.5
_K = {
    "turner": 1.92,   # 1969 — most conservative, with 20% padding
    "coleman": 1.59,  # 1991 — no padding, better for low-pressure wells
    "lea": 1.40,      # modern reference, fluid-dependent (1.4 typical)
}

# Conversion: σ in dyn/cm × this constant = σ in lbf/ft
# (1 dyn/cm × 6.85e-5 = lbf/ft, but field-form Turner expects σ in lbf/ft
#  with magnitudes ~0.06 for water — which corresponds to a slightly different
#  unit convention. We adopt 0.06 = water as the field default.)
_SIGMA_FIELD_FORM = 0.0682 / 72.0  # → σ_field for water (60 dyn/cm) = ~0.0568 lbf/ft

Fluid = Literal["water", "condensate", "mixed"]
Correlation = Literal["turner", "coleman", "lea"]


@dataclass
class CriticalResult:
    """Critical velocity and standard-condition rate for one correlation."""

    correlation: str
    v_c_ft_s: float        # critical velocity in ft/s
    q_c_mcfd: float        # critical rate at standard conditions in Mcfd
    rho_g_lb_ft3: float    # computed gas density at depth
    tubing_id_in: float
    tubing_area_in2: float
    flowing_pressure_psia: float
    flowing_temperature_f: float
    gas_specific_gravity: float
    z_factor: float
    fluid: str

    def __str__(self) -> str:
        return (
            f"{self.correlation.title():>7s}: "
            f"v_c = {self.v_c_ft_s:6.2f} ft/s   "
            f"q_c = {self.q_c_mcfd:7.0f} Mcfd"
        )


def gas_density(
    p_psia: float,
    t_f: float,
    gamma_g: float = 0.65,
    z: float = 0.90,
) -> float:
    """Gas density at flowing conditions (lb/ft³).

    ρ_g = P × M / (Z × R × T)
    with M = 28.96 × γ_g (lb/lbmol), R = 10.732 (psi·ft³/lbmol/°R),
    T in °R = °F + 459.67.
    """
    if p_psia <= 0:
        raise ValueError("p_psia must be positive")
    if z <= 0:
        raise ValueError("z must be positive")
    t_r = t_f + 459.67
    return (p_psia * 28.96 * gamma_g) / (z * 10.732 * t_r)


def critical_velocity(
    correlation: Correlation,
    rho_l_lb_ft3: float,
    rho_g_lb_ft3: float,
    sigma_lbf_ft: float,
) -> float:
    """Critical velocity (ft/s) by named correlation.

    v_c = K × [σ × (ρ_L − ρ_g)]^0.25 / ρ_g^0.5
    """
    if correlation not in _K:
        raise ValueError(
            f"unknown correlation {correlation!r}; expected one of {sorted(_K)}"
        )
    if rho_g_lb_ft3 <= 0:
        raise ValueError("rho_g_lb_ft3 must be positive")
    if rho_l_lb_ft3 <= rho_g_lb_ft3:
        raise ValueError(
            "liquid density must exceed gas density (you may have inverted them)"
        )
    k = _K[correlation]
    return k * (sigma_lbf_ft * (rho_l_lb_ft3 - rho_g_lb_ft3)) ** 0.25 / rho_g_lb_ft3 ** 0.5


def critical_rate_mcfd(
    v_c_ft_s: float,
    p_psia: float,
    t_f: float,
    tubing_id_in: float,
    z: float = 0.90,
) -> float:
    """Critical rate at standard conditions (Mcfd) for a given critical velocity.

    Q_sc (Mcfd) = 3056 × p × v_c × A / (T × Z), with A in ft² and T in °R.

    Derivation: Q_sc / Q_actual = (P × T_sc) / (P_sc × T × Z) at Z_sc = 1, then
    convert ft³/s → Mcfd by multiplying by 86,400 / 1000.
    P_sc = 14.7 psia, T_sc = 520°R; the resulting constant is 3056.
    """
    if tubing_id_in <= 0:
        raise ValueError("tubing_id_in must be positive")
    t_r = t_f + 459.67
    a_in2 = math.pi * tubing_id_in ** 2 / 4.0
    a_ft2 = a_in2 / 144.0
    return 3056.0 * p_psia * v_c_ft_s * a_ft2 / (t_r * z)


def compute(
    tubing_id_in: float,
    flowing_pressure_psia: float,
    flowing_temperature_f: float = 100.0,
    gas_specific_gravity: float = 0.65,
    z_factor: float = 0.90,
    fluid: Fluid = "water",
    correlation: Correlation = "turner",
) -> CriticalResult:
    """Compute critical velocity and rate for one correlation.

    >>> r = compute(tubing_id_in=2.441, flowing_pressure_psia=100,
    ...             flowing_temperature_f=100, fluid="water",
    ...             correlation="turner")
    >>> 80 < r.q_c_mcfd < 100  # ~89 Mcfd at these defaults
    True
    """
    if fluid not in _FLUIDS:
        raise ValueError(f"unknown fluid {fluid!r}; expected one of {sorted(_FLUIDS)}")

    rho_g = gas_density(
        p_psia=flowing_pressure_psia,
        t_f=flowing_temperature_f,
        gamma_g=gas_specific_gravity,
        z=z_factor,
    )

    fp = _FLUIDS[fluid]
    sigma_field = _SIGMA_FIELD_FORM * fp["sigma_dyne_cm"]  # lbf/ft

    v_c = critical_velocity(
        correlation=correlation,
        rho_l_lb_ft3=fp["rho_lb_ft3"],
        rho_g_lb_ft3=rho_g,
        sigma_lbf_ft=sigma_field,
    )

    q_c = critical_rate_mcfd(
        v_c_ft_s=v_c,
        p_psia=flowing_pressure_psia,
        t_f=flowing_temperature_f,
        tubing_id_in=tubing_id_in,
        z=z_factor,
    )

    a_in2 = math.pi * tubing_id_in ** 2 / 4.0

    return CriticalResult(
        correlation=correlation,
        v_c_ft_s=v_c,
        q_c_mcfd=q_c,
        rho_g_lb_ft3=rho_g,
        tubing_id_in=tubing_id_in,
        tubing_area_in2=a_in2,
        flowing_pressure_psia=flowing_pressure_psia,
        flowing_temperature_f=flowing_temperature_f,
        gas_specific_gravity=gas_specific_gravity,
        z_factor=z_factor,
        fluid=fluid,
    )


def compute_all(
    tubing_id_in: float,
    flowing_pressure_psia: float,
    flowing_temperature_f: float = 100.0,
    gas_specific_gravity: float = 0.65,
    z_factor: float = 0.90,
    fluid: Fluid = "water",
) -> dict[str, CriticalResult]:
    """Compute Turner, Coleman, and Lea results for the same well conditions."""
    return {
        c: compute(
            tubing_id_in=tubing_id_in,
            flowing_pressure_psia=flowing_pressure_psia,
            flowing_temperature_f=flowing_temperature_f,
            gas_specific_gravity=gas_specific_gravity,
            z_factor=z_factor,
            fluid=fluid,
            correlation=c,
        )
        for c in ("turner", "coleman", "lea")
    }


def recommended_correlation(flowing_pressure_psia: float) -> str:
    """Heuristic recommendation by flowing tubing pressure regime."""
    if flowing_pressure_psia < 500:
        return "coleman"
    if flowing_pressure_psia < 2000:
        return "lea"
    return "turner"


__all__ = [
    "__version__",
    "CriticalResult",
    "compute",
    "compute_all",
    "critical_rate_mcfd",
    "critical_velocity",
    "gas_density",
    "recommended_correlation",
]
