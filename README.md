# wellrx-tcl

**Gas well critical-velocity (Turner / Coleman / Lea) calculator for Python.**

A small, dependency-free library for computing the minimum gas velocity (and
corresponding standard-condition rate) required to lift water or condensate
droplets out of a vertical gas well's tubing. Below the critical rate, the well
is at risk of liquid loading: droplets accumulate, hydrostatic head builds, and
gas inflow from the formation chokes off.

This is the Python companion to the free interactive calculator at
**[wellrx.app/tools/critical-velocity/](https://wellrx.app/tools/critical-velocity/)**.

For background and a 24-hour decision tree on what to do when these signals
fire, see **[7 Early-Warning Signs of Gas Well Liquid Loading](https://wellrx.app/learn/liquid-loading-early-warning-signs/)**.

## Install

```bash
pip install wellrx-tcl
```

## Quickstart

```python
from wellrx_tcl import compute, compute_all, recommended_correlation

# One correlation at a time
result = compute(
    tubing_id_in=2.441,           # 2-7/8" OD tubing
    flowing_pressure_psia=500,
    flowing_temperature_f=110,
    gas_specific_gravity=0.65,
    z_factor=0.90,
    fluid="water",                # or "condensate" or "mixed"
    correlation="turner",         # or "coleman" or "lea"
)
print(result)
#  Turner: v_c =   2.04 ft/s   q_c =     197 Mcfd

# All three correlations at once
results = compute_all(tubing_id_in=2.441, flowing_pressure_psia=500, flowing_temperature_f=110, fluid="water")
for r in results.values():
    print(r)
#  Turner: v_c =   2.04 ft/s   q_c =     197 Mcfd
# Coleman: v_c =   1.69 ft/s   q_c =     163 Mcfd
#     Lea: v_c =   1.49 ft/s   q_c =     144 Mcfd

# Heuristic for which correlation to trust
print(recommended_correlation(500))  # 'lea'
print(recommended_correlation(150))  # 'coleman' — Turner over-predicts low-pressure
```

## Why three correlations?

| Correlation | Year | Best for | Why |
|---|---|---|---|
| **Turner** | 1969 | Field default, high-pressure (>2000 psia) | Most conservative; 20% padding over the spherical-droplet drag derivation. Tends to over-predict on mature low-pressure wells. |
| **Coleman** | 1991 | Low-pressure mature wells (FTP < 500 psia) | Same form as Turner without the 20% padding. Better fit for unconventional / depleted gas wells. |
| **Lea / Nickens** | modern | Vertical / near-vertical wells with characterized PVT | k chosen at 1.4 for typical fluid load. The current engineering reference. |

Run `recommended_correlation(p_psia)` for a quick by-pressure-regime hint.

## Returned data

Each `compute()` call returns a `CriticalResult` dataclass:

```python
@dataclass
class CriticalResult:
    correlation: str         # "turner" | "coleman" | "lea"
    v_c_ft_s: float          # critical velocity, ft/s
    q_c_mcfd: float          # critical rate at standard conditions, Mcfd
    rho_g_lb_ft3: float      # computed gas density at flowing conditions
    tubing_id_in: float
    tubing_area_in2: float
    flowing_pressure_psia: float
    flowing_temperature_f: float
    gas_specific_gravity: float
    z_factor: float
    fluid: str
```

## Caveats

- Field-form coefficients use Lea-form `K × [σ(ρ_L−ρ_g)]^0.25 / ρ_g^0.5` with
  `K = {turner: 1.92, coleman: 1.59, lea: 1.40}`.
- Critical rate uses `Q_sc = 3056 × P × v × A_ft² / (T × Z)` (T in °R), which
  carries the conversion from actual to standard conditions and ft³/s → Mcfd.
- The library is a planning estimate. For production decisions, validate against
  the well's documented loading history and PVT.
- Deviated / horizontal wells past ~30° inclination need an inclination-corrected
  approach not provided by Turner / Coleman / Lea alone.

## Reference

- Turner, R. G., Hubbard, M. G., & Dukler, A. E. (1969). *Analysis and Prediction
  of Minimum Flow Rate for the Continuous Removal of Liquids from Gas Wells.*
  Journal of Petroleum Technology, 21(11), 1475–1482.
- Coleman, S. B. et al. (1991). *A New Look at Predicting Gas-Well Load-Up.*
  Journal of Petroleum Technology, 43(03), 329–333.
- Lea, J. F., Nickens, H. V., & Wells, M. (2008). *Gas Well Deliquification.*
  Gulf Professional Publishing.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Related

- **Free interactive calculator:** [wellrx.app/tools/critical-velocity/](https://wellrx.app/tools/critical-velocity/)
- **Field guide:** [7 Early-Warning Signs of Gas Well Liquid Loading](https://wellrx.app/learn/liquid-loading-early-warning-signs/)
- **Plunger lift checklist:** [21-point optimization checklist](https://wellrx.app/learn/plunger-lift-optimization-checklist/)

---

**About WellRX.** WellRX is an AI-powered daily decision-support system for
natural-gas operators with 20–200 active wells. Virtual petroleum, production,
and chemical engineering team reviews every active well every morning against
live SCADA / historian / FSR data and delivers a field-ready Rx by 6:30 AM CT.
Charter-partner cohort open: setup waived + 50% off three months at
[wellrx.app/beta/](https://wellrx.app/beta/).
