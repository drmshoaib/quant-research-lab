# EXP-001 Results — Frozen v0.2 Baseline

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Workflow run:** `37189513253`

**Accounting note (4 October 2026):** The economic portfolio figures in this file are preserved as originally recorded. A subsequent pre-hold-out technical audit corrected portfolio P&L to arithmetic open-to-open returns and standardised terminal liquidation costs. Statistical signal results and all registered decisions were unchanged. Use [`docs/accounting_correction.md`](accounting_correction.md) for the corrected economic figures.


## Frozen inputs

- 30-ETF fixed universe.
- Adjusted market-data snapshot: 126,390 rows, 4 January 2010 to 2 October 2026.
- Snapshot SHA-256: `ec782ac2cd812a6d81abcbf9cbcdecdd448ab8822b585fbd07c3a74968a3bbd3`.
- Hold-out: 252 eligible decision dates, 24 September 2025 to 24 September 2026.
- Pre-hold-out embargo: 6 decision dates.
- Development evaluation dates: 3,087.
- Target horizon: 5 sessions.
- Portfolio translation: five staggered sleeves.
- Base cost: 5 bps one way.

## Primary statistical result

| Metric | Ridge | HistGradientBoosting |
|---|---:|---:|
| Mean rank IC | 0.00365 | 0.02624 |
| Median rank IC | 0.00156 | 0.02870 |
| IC standard deviation | 0.31025 | 0.24281 |
| Daily IC IR | 0.01176 | 0.10808 |
| Positive IC dates | 50.1% | 54.1% |
| HAC t-statistic | 0.435 | 3.849 |
| HAC p-value | 0.664 | 0.000119 |
| Median fold IC | 0.00324 | 0.02301 |
| Positive development years | 7/13 (53.8%) | 11/13 (84.6%) |
| Positive folds | 25/49 (51.0%) | 38/49 (77.6%) |

Ridge therefore fails the pre-registered EXP-001 acceptance rule. Its mean IC is positive but statistically indistinguishable from zero, and its positive-year fraction misses the 60% gate.

HistGradientBoosting has materially stronger rank information. Its mean IC exceeds Ridge by 0.02260. It beats Ridge on 28 of 49 folds (57.1%), so the relative advantage is not uniform even though the nonlinear model itself has positive mean IC in most folds.

## Economic diagnostic

| One-way cost | Ridge ann. return | Ridge Sharpe | HistGB ann. return | HistGB Sharpe |
|---:|---:|---:|---:|---:|
| 0 bps | 0.87% | 0.179 | 2.21% | 0.565 |
| 2 bps | -0.03% | -0.006 | 1.35% | 0.346 |
| 5 bps | -1.37% | -0.282 | 0.07% | 0.017 |
| 10 bps | -3.61% | -0.743 | -2.07% | -0.530 |
| 20 bps | -8.08% | -1.665 | -6.35% | -1.625 |

Annualised turnover is 44.73 times gross notional for Ridge and 42.79 for HistGradientBoosting. The nonlinear model's approximate break-even one-way cost is about 5.2 bps, consistent with the near-zero 5 bps result.

## Decision

The primary Ridge baseline is rejected.

The nonlinear comparator is retained for development work because the IC evidence is statistically significant and appears across most years and folds. It is not yet promoted to the final specification. The next research question is whether the nonlinear IC is concentrated in identifiable features/regimes and whether its information can be converted into a lower-turnover portfolio.

The locked hold-out remains untouched.
