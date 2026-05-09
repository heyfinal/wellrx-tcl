"""Sanity tests for wellrx_tcl."""

import math

import pytest

from wellrx_tcl import (
    compute,
    compute_all,
    critical_rate_mcfd,
    critical_velocity,
    gas_density,
    recommended_correlation,
)


def test_gas_density_typical():
    rho_g = gas_density(p_psia=500, t_f=100, gamma_g=0.65, z=0.90)
    assert 1.5 < rho_g < 2.0


def test_gas_density_low_pressure():
    rho_g = gas_density(p_psia=50, t_f=100, gamma_g=0.65, z=0.95)
    assert 0.1 < rho_g < 0.3


def test_critical_velocity_turner_above_coleman():
    # Same conditions; Turner has 20% padding so v_T > v_C > v_L (in Lea-form coefficients).
    cond = dict(
        rho_l_lb_ft3=67.0, rho_g_lb_ft3=1.74, sigma_lbf_ft=0.0568,
    )
    v_T = critical_velocity(correlation="turner", **cond)
    v_C = critical_velocity(correlation="coleman", **cond)
    v_L = critical_velocity(correlation="lea", **cond)
    assert v_T > v_C > v_L > 0


def test_compute_water_low_pressure_default():
    """2-7/8" tubing at 100 psia, 100°F, water — sanity check around 89 Mcfd."""
    r = compute(
        tubing_id_in=2.441,
        flowing_pressure_psia=100,
        flowing_temperature_f=100,
        fluid="water",
        correlation="turner",
    )
    assert 80 < r.q_c_mcfd < 100
    assert 4.0 < r.v_c_ft_s < 5.5


def test_compute_water_high_pressure():
    """Higher pressure → much higher critical rate (more gas mass moving)."""
    r = compute(
        tubing_id_in=2.441,
        flowing_pressure_psia=1500,
        flowing_temperature_f=120,
        fluid="water",
        correlation="turner",
    )
    # Hand-derived: at FTP=1500 psia, T=120°F, γ_g=0.65, Z=0.9 →
    # ρ_g ≈ 5.04 lb/ft³, v_T ≈ 1.17 ft/s, q_T ≈ 334 Mcfd
    assert 250 < r.q_c_mcfd < 450


def test_compute_condensate_lower_than_water():
    """Condensate has lower σ and ρ_L — critical rate should be lower than water at same conditions."""
    cond_w = compute(tubing_id_in=2.441, flowing_pressure_psia=500, fluid="water", correlation="turner")
    cond_c = compute(tubing_id_in=2.441, flowing_pressure_psia=500, fluid="condensate", correlation="turner")
    assert cond_c.q_c_mcfd < cond_w.q_c_mcfd


def test_compute_all_returns_three_correlations():
    out = compute_all(tubing_id_in=2.441, flowing_pressure_psia=200, fluid="water")
    assert set(out.keys()) == {"turner", "coleman", "lea"}
    # Same well conditions; Turner conservative bound, Lea lowest.
    assert out["turner"].q_c_mcfd > out["coleman"].q_c_mcfd > out["lea"].q_c_mcfd


def test_recommended_correlation_by_pressure():
    assert recommended_correlation(100) == "coleman"
    assert recommended_correlation(800) == "lea"
    assert recommended_correlation(2500) == "turner"


def test_compute_rejects_invalid_fluid():
    with pytest.raises(ValueError):
        compute(tubing_id_in=2.441, flowing_pressure_psia=100, fluid="brine")


def test_compute_rejects_invalid_correlation():
    with pytest.raises(ValueError):
        compute(tubing_id_in=2.441, flowing_pressure_psia=100, correlation="nodal")


def test_critical_rate_scales_linearly_with_pressure_for_fixed_velocity():
    """At fixed v_c, Q_sc scales linearly with P (gas density compresses)."""
    q1 = critical_rate_mcfd(v_c_ft_s=5.0, p_psia=100, t_f=100, tubing_id_in=2.441)
    q2 = critical_rate_mcfd(v_c_ft_s=5.0, p_psia=1000, t_f=100, tubing_id_in=2.441)
    assert math.isclose(q2 / q1, 10.0, rel_tol=1e-3)
