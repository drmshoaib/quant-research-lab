# Methodological Correction — Portfolio Return Accounting

**Date:** 4 October 2026  
**Status:** Completed before final hold-out evaluation  
**Hold-out:** Locked and untouched

## Why this correction was made

A hiring-manager-style technical review of the frozen research note identified two accounting issues in the **secondary portfolio diagnostics**.

First, the modelling target intentionally uses log returns, but early portfolio backtests also used weighted one-session log returns as portfolio P&L. For a rebalanced portfolio with transaction costs, the economically correct accounting is in arithmetic-return space:

```text
R_i,t       = O_i,t+2 / O_i,t+1 - 1
R_gross,t   = sum_i w_i,t * R_i,t
cost_t      = c * sum_i |w_i,t - w_i,t-1|
R_net,t     = R_gross,t - cost_t
equity_t    = product_s<=t (1 + R_net,s)
```

Second, EXP-001 and EXP-002 allowed their final staggered sleeves to run through the final return period but did not book the terminal liquidation turnover/cost. EXP-003 onward already included explicit terminal liquidation. The baseline and EXP-002 scripts were brought into the same convention.

## Scope

This is a **methodological correction, not a new research experiment**.

It does not change:

- the frozen market-data snapshot;
- the universe;
- the hold-out manifest or boundary;
- features;
- targets used for model fitting;
- model hyperparameters;
- walk-forward folds;
- predictions;
- rank IC or HAC inference;
- feature attribution;
- the pruned8 model-selection decision;
- EXP-006/007 robustness results.

Only portfolio P&L, Sharpe, drawdown, break-even cost and economic promotion gates in EXP-001 through EXP-005 were recomputed.

## Corrected headline economics

For the formal pruned8 instant-execution benchmark:

| One-way cost | Annualised arithmetic return |
|---:|---:|
| 0 bps | **2.3444%** |
| 2 bps | **1.5062%** |
| 5 bps | **0.2488%** |
| 10 bps | **-1.8468%** |
| 20 bps | **-6.0381%** |

Annualised turnover is **41.9124**, 5 bps Sharpe is **0.0647**, and approximate one-way break-even cost is **5.59 bps**.

The corrected full-nine-feature HistGradientBoosting benchmark is 2.2808% at zero cost and 0.1412% at 5 bps.

## Did any registered decision change?

**No.**

- EXP-001: Ridge still fails; HistGradientBoosting remains the nonlinear development candidate.
- EXP-002: all EWMA smoothing variants remain rejected.
- EXP-003: pruned8 remains the only eligible reduced specification; partial adjustment remains rejected.
- EXP-004: all turnover-budget candidates remain rejected. The 0.12 budget now retains **79.9649%** of zero-cost return against the pre-registered **80%** requirement. It remains a failure; the threshold is not rounded or relaxed.
- EXP-005: all no-trade candidates remain rejected. Band 0.005 preserves 92.06% of gross return but reduces turnover only 15.63%; band 0.010 reduces turnover 30.45% but retains only 76.75% of gross return.

The formal execution benchmark therefore remains **instant pruned8**.

## Reproducibility

Correction code commit: `0eb8aacaa1b7dbee555a7d2bcba6b6fe44c0955b`  
Correction workflow run: `37199738636`

Corrected artifacts:

- EXP-001: artifact `11302617689`, digest `sha256:318b77477de5f221acb770a873d4f4c8a1be2776cdd1ed7ab19f48e5cd13b671`;
- EXP-002: artifact `11301787895`, digest `sha256:350f5d530bf3910509ff7ecfb5b4ac4b808067b6eef5829dd636f03bf9ec6908`;
- EXP-003: artifact `11302093735`, digest `sha256:18b4e861b6b4ad74d50ca56bae05363101d5d799eaa13ea5e9ebaefd9d040162`;
- EXP-004: artifact `11302358647`, digest `sha256:0a047f14bd2f502d9739164e908f0a2adde077863eb378111cc2776701948bbd`;
- EXP-005: artifact `11302388415`, digest `sha256:b73e7cccd3edab16be9a10f351a7c0146ffa5730f86536b7ad3d058db7f7c0c7`.

The hold-out was not accessed during this correction.
