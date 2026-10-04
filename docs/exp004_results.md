# EXP-004 Results — Turnover-Budgeted Portfolio Projection

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Successful workflow run:** `37191844160`

**Accounting note (4 October 2026):** The economic portfolio figures in this file are preserved as originally recorded. A subsequent pre-hold-out technical audit corrected portfolio P&L to arithmetic open-to-open returns and standardised terminal liquidation costs. Statistical signal results and all registered decisions were unchanged. Use [`docs/accounting_correction.md`](accounting_correction.md) for the corrected economic figures.


## Research question

EXP-004 kept the pruned8 HistGradientBoosting forecast fixed and changed only execution.

At each development date, the actual portfolio was the feasible portfolio closest in squared Euclidean distance to the instantaneous five-sleeve rank target, subject to dollar neutrality, gross exposure, per-name limits and one of three pre-registered daily L1 turnover budgets: 0.12, 0.10 and 0.08.

## Frozen signal reference

The pruned8 forecast reproduced EXP-003:

- mean rank IC: **0.02701**;
- HAC t-statistic: **3.922**;
- HAC p-value: **8.78e-5**;
- median fold IC: **0.02766**;
- positive development years: **12/13 = 92.3%**.

Portfolio projection does not change these prediction statistics.

## Execution result

| Execution | Ann. turnover | Reduction | 0 bp return | Gross return retained | 5 bp return | 5 bp Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Instant pruned8 | 41.91 | — | 2.25% | 100% | 0.15% | 0.040 |
| Budget 0.12 | 29.89 | 28.7% | 1.79% | **79.46%** | **0.29%** | **0.080** |
| Budget 0.10 | 25.12 | 40.1% | 1.54% | 68.48% | 0.28% | 0.079 |
| Budget 0.08 | 20.15 | 51.9% | 1.24% | 55.10% | 0.23% | 0.067 |

All three constrained portfolios improve 5 bps net return and Sharpe relative to instant execution. None passes the pre-registered 80% gross-return-retention gate.

The 0.12 candidate is a particularly close miss: it retains 79.46% rather than 80%. The rule is therefore **not** relaxed after observing the result.

## Cost sensitivity

| Execution | 0 bps | 2 bps | 5 bps | 10 bps | 20 bps |
|---|---:|---:|---:|---:|---:|
| Instant | 2.25% | 1.41% | 0.15% | -1.94% | -6.13% |
| Budget 0.12 | 1.79% | 1.19% | 0.29% | -1.20% | -4.19% |
| Budget 0.10 | 1.54% | 1.04% | 0.28% | -0.97% | -3.48% |
| Budget 0.08 | 1.24% | 0.84% | 0.23% | -0.78% | -2.79% |

Approximate one-way break-even costs are:

- instant pruned8: **5.37 bps**;
- budget 0.12: **5.98 bps**;
- budget 0.10: **6.13 bps**;
- budget 0.08: **6.15 bps**.

The tighter budgets sacrifice more gross alpha but improve cost efficiency because turnover falls faster than gross return.

## Projection diagnostics

| Budget | Mean tracking error | 95th pct tracking error | Constraint binding | Solver fallbacks |
|---:|---:|---:|---:|---:|
| 0.12 | 0.0221 | 0.0563 | 93.1% | 0 |
| 0.10 | 0.0337 | 0.0720 | 98.1% | 0 |
| 0.08 | 0.0484 | 0.0904 | 99.5% | 0 |

The optimisation was operationally stable. No deterministic fallback was used for any tested budget.

## Interpretation

EXP-004 differs materially from the failed smoothing experiments.

EXP-002 smoothed model scores and EXP-003 partially adjusted all portfolio weights. Both destroyed gross alpha faster than they saved costs.

The turnover-budget projection instead decides **which target changes receive scarce turnover**. That preserves enough economically useful movement for every tested budget to improve net performance at 5 bps.

However, the pre-registered experiment asked for at least 80% retention of zero-cost return. None meets that standard. The closest candidate, 0.12, misses by only 0.54 percentage points, but admitting it after seeing the result would move the goalposts.

## Decision

No EXP-004 candidate is promoted.

Instant pruned8 remains the formal development benchmark.

Turnover-budget projection is retained as a promising execution mechanism because it improves 5 bps net return, Sharpe and break-even cost without altering the predictive model. Any follow-up must be separately pre-registered and must not simply search around the observed 0.12 near miss.

The final 252-date hold-out remains locked.
