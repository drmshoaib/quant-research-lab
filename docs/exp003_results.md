# EXP-003 Results — Reduced Nonlinear Specification and Turnover-Aware Execution

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Successful workflow run:** `37191103896`

**Accounting note (4 October 2026):** The economic portfolio figures in this file are preserved as originally recorded. A subsequent pre-hold-out technical audit corrected portfolio P&L to arithmetic open-to-open returns and standardised terminal liquidation costs. Statistical signal results and all registered decisions were unchanged. Use [`docs/accounting_correction.md`](accounting_correction.md) for the corrected economic figures.


## Research question

EXP-003 tested whether the nonlinear signal from EXP-001/002 could be represented with fewer features and whether portfolio-level partial adjustment could reduce turnover without smoothing model scores.

Four feature specifications and exactly two partial-adjustment rates were registered before results were inspected.

## Feature specification result

| Specification | Features | Mean IC | HAC p | Median fold IC | Positive years | Ann. turnover | 0 bp ann. return | 5 bp ann. return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full9 | 9 | 0.02624 | 0.000119 | 0.02301 | 84.6% | 42.79 | 2.21% | 0.07% |
| core2 | 2 | 0.01203 | 0.0616 | 0.01353 | 76.9% | 40.68 | -0.27% | -2.30% |
| core3 | 3 | 0.01781 | 0.00576 | 0.01774 | 84.6% | 37.76 | 1.36% | -0.52% |
| pruned8 | 8 | **0.02701** | **0.0000878** | **0.02766** | **92.3%** | 41.91 | **2.25%** | **0.15%** |

The pre-registered reduced-model gate required at least 80% of full9 mean IC, significant positive HAC inference, positive median fold IC, and positive mean IC in at least 70% of eligible years.

Only **pruned8**, which removes `mom_5`, passed every gate. It retains 102.9% of full9 mean IC and is therefore selected under the pre-declared rule.

The result also corrects a tempting over-interpretation of EXP-002. `vol_20` and `drawdown_60` were the only individual ablations satisfying the FDR/materiality rule, but the two-feature model retains only 45.8% of full9 IC. Adding `vol_60` raises retention to 67.9%, still below the 80% gate. The broader feature set therefore contains nonlinear interaction or substitutable information that individual leave-one-out tests cannot fully reveal.

## Economic comparison

At instant execution, pruned8 improves slightly on full9:

- annualised turnover: 41.91 versus 42.79;
- zero-cost annualised return: 2.25% versus 2.21%;
- 5 bps net annualised return: 0.15% versus 0.07%;
- 5 bps Sharpe: 0.040 versus 0.017;
- approximate one-way break-even cost: 5.37 bps versus 5.16 bps.

These are incremental improvements. The 5 bps net result remains economically thin and turns negative at 10 bps, so this is not yet a robust trading specification.

## Turnover-aware partial adjustment

Part B applied portfolio-level inertia to the selected pruned8 target without smoothing model scores.

| Adjustment rate | Ann. turnover | Turnover reduction | 0 bp ann. return | Gross-return retention | 5 bp ann. return | 5 bp Sharpe |
|---:|---:|---:|---:|---:|---:|---:|
| 1.00 instant | 41.91 | — | 2.25% | 100% | 0.15% | 0.040 |
| 0.50 | 30.25 | 27.8% | 1.58% | 70.2% | 0.07% | 0.018 |
| 0.25 | 21.07 | 49.7% | 1.00% | 44.6% | -0.05% | -0.014 |

Neither partial-adjustment rule qualifies.

The 0.50 rule misses the 30% turnover threshold and the 80% gross-return retention threshold. The 0.25 rule achieves a large turnover reduction but gives up more than half of gross return. Neither improves 5 bps net annualised return relative to instant pruned8 execution.

## Interpretation

Two consecutive experiments now give the same qualitative answer. Uniform temporal smoothing, whether applied to scores (EXP-002) or portfolio weights (EXP-003), reduces turnover but destroys alpha too quickly.

The predictive information appears to require timely re-ranking. A better turnover mechanism should therefore **choose which trades to spend turnover on** rather than slowing every desired position change.

This motivates a turnover-budgeted projection or no-trade mechanism: retain the fast pruned8 forecast, but allocate limited turnover to the largest economically relevant target changes.

## Decision

Promote **pruned8 HistGradientBoosting with instant rank execution** as the current development benchmark.

Reject the two partial-adjustment rules.

The final 252-date hold-out remains locked.
