# EXP-005 Results — No-Trade Band Execution

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Successful workflow run:** `37193646068`

**Accounting note (4 October 2026):** The economic portfolio figures in this file are preserved as originally recorded. A subsequent pre-hold-out technical audit corrected portfolio P&L to arithmetic open-to-open returns and standardised terminal liquidation costs. Statistical signal results and all registered decisions were unchanged. Use [`docs/accounting_correction.md`](accounting_correction.md) for the corrected economic figures.


## Research question

EXP-005 kept the frozen pruned8 HistGradientBoosting forecast unchanged and tested whether small desired per-name portfolio changes could simply be ignored while larger changes were executed immediately.

Three no-trade bands were registered before results were observed:

- 0.005 absolute portfolio weight;
- 0.010;
- 0.020.

Names inside the band remained at their previous actual weight. Names outside the band could move toward, but never past, their current target weight.

## Frozen signal reference

The pruned8 prediction signal again reproduced exactly:

- mean rank IC: **0.02701**;
- HAC t-statistic: **3.922**;
- HAC p-value: **8.78e-5**;
- median fold IC: **0.02766**;
- positive development years: **12/13 = 92.3%**.

## Execution result

| Execution | Ann. turnover | Reduction | 0 bp return | Gross retained | 5 bp return | 5 bp Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Instant pruned8 | 41.91 | — | 2.25% | 100% | 0.15% | 0.040 |
| Band 0.005 | 35.36 | 15.6% | 2.06% | **91.73%** | **0.30%** | **0.077** |
| Band 0.010 | 29.15 | **30.5%** | 1.70% | 75.70% | **0.25%** | **0.065** |
| Band 0.020 | 20.36 | **51.4%** | 1.04% | 46.36% | 0.02% | 0.007 |

No candidate passes all pre-registered acceptance gates.

The 0.005 band preserves gross alpha well and produces the strongest 5 bps net return in EXP-005, but it reduces turnover by only 15.6%, below the required 25%.

The 0.010 band achieves the required turnover reduction and improves 5 bps economics, but preserves only 75.7% of zero-cost return, below the required 80%.

The 0.020 band is too restrictive: more than half of turnover disappears, but so does more than half of gross return.

## Cost sensitivity

| Execution | 0 bps | 2 bps | 5 bps | 10 bps | 20 bps |
|---|---:|---:|---:|---:|---:|
| Instant | 2.25% | 1.41% | 0.15% | -1.94% | -6.13% |
| Band 0.005 | 2.06% | 1.36% | 0.30% | -1.47% | -5.01% |
| Band 0.010 | 1.70% | 1.12% | 0.25% | -1.21% | -4.13% |
| Band 0.020 | 1.04% | 0.64% | 0.02% | -0.99% | -3.03% |

Approximate one-way break-even costs are:

- instant pruned8: **5.37 bps**;
- band 0.005: **5.83 bps**;
- band 0.010: **5.84 bps**;
- band 0.020: **5.12 bps**.

Moderate no-trade filtering therefore improves cost efficiency, but the stronger filters sacrifice too much gross alpha.

## Trading diagnostics

| Band | Active names | Held names | Desired L1 change ignored | Dates with no discretionary trade | Solver fallbacks |
|---:|---:|---:|---:|---:|---:|
| 0.005 | 46.2% | 53.8% | 21.5% | 0.3% | 0 |
| 0.010 | 28.4% | 71.6% | 43.5% | 1.2% | 0 |
| 0.020 | 14.6% | 85.4% | 67.1% | 18.6% | 0 |

The optimisation was operationally stable at all three bands.

## Interpretation

The no-trade mechanism confirms the broad economic lesson from EXP-004: **selective trading is better than uniform slowing**.

However, EXP-005 also reveals a sharp trade-off. Small bands preserve the signal but do not reduce turnover enough; larger bands reduce turnover sufficiently but discard too much of the predictive portfolio movement.

It would be tempting to search between 0.005 and 0.010 after seeing these results. That search is deliberately not performed. The location of the apparent trade-off boundary is now development information, so tuning directly around it would weaken the research design.

## Decision

No EXP-005 candidate is promoted.

Instant pruned8 remains the formal development benchmark.

Rather than continue inventing or tuning execution mechanisms, the next phase should test the **robustness and falsifiability of the pruned8 predictive signal** across horizons, subperiods, asset groups and placebo procedures before the final specification is frozen.

The final 252-date hold-out remains locked.
