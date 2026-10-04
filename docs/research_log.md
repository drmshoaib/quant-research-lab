# Research Log — v0.2

Use one entry per hypothesis **before** inspecting its empirical result.

## Entry template

### EXP-XXX — Short name

**Date registered:**  
**Status:** proposed / running / accepted / rejected / superseded

**Question**  
State one testable question.

**Signal definition**  
Give the exact formula, lookback, lag and any cross-sectional transformation.

**Rationale**  
State the market mechanism or statistical reason being tested.

**Expected direction**  
Positive / negative / unsigned, with a short justification.

**Development-only evaluation**  
Specify rank IC, HAC lag, folds, horizons, ablations or placebo checks to be used.

**Acceptance rule**  
State the rule before results are inspected.

**Result**  
Complete only after the experiment runs.

**Decision**  
Promote, reject, revise or retain as diagnostic.

**Commit / output references**  
Record the code commit and output paths.

## EXP-001 — Frozen v0.2 baseline

**Date registered:** 4 October 2026  
**Status:** proposed

**Question**  
Does the pre-declared v0.1 feature set contain stable cross-sectional information about 5-session relative ETF returns under the frozen v0.2 protocol?

**Signal definition**  
Use the nine existing end-of-day features without modification:

- ret_1;
- mom_5;
- mom_20;
- mom_60;
- vol_20;
- vol_60;
- range_1;
- volume_z_20;
- drawdown_60.

Primary model: Ridge regression with alpha = 10.  
Secondary comparator: HistGradientBoostingRegressor with the fixed repository hyperparameters.

The target is 5-session next-open-to-open relative log return. No hold-out dates enter model fitting, feature selection or evaluation.

**Rationale**  
The baseline tests whether simple trend, short-horizon reversal, volatility, range, volume and drawdown information jointly contain persistent cross-sectional ranking information before any feature search is undertaken. Ridge is the primary statistical benchmark because it constrains model complexity; histogram gradient boosting tests whether the same frozen feature set contains useful nonlinear structure.

**Expected direction**  
Positive mean rank IC for the primary Ridge model. No directional superiority is pre-declared for HistGradientBoosting relative to Ridge.

**Development-only evaluation**  
Use the frozen expanding purged walk-forward design:

- minimum training history: 756 decision dates;
- test block: 63 decision dates;
- step: 63 decision dates;
- train/test purge: 6 decision dates;
- pre-hold-out embargo: 6 decision dates.

Report mean and median daily Spearman rank IC, IC standard deviation, IC information ratio, positive-IC fraction, fold-level IC, annual IC and Newey-West/HAC inference with lag 4.

Translate forecasts into the five-sleeve horizon-consistent portfolio. Report gross and net performance at 5 bps one-way costs, plus cost sensitivity at 0, 2, 5, 10 and 20 bps.

**Acceptance rule**  
The frozen feature set is considered to have passed the primary development test if Ridge satisfies all of the following:

1. mean daily rank IC > 0;
2. HAC two-sided p-value < 0.05;
3. median fold-level rank IC > 0;
4. positive mean annual rank IC in at least 60% of development calendar years with sufficient observations.

Portfolio Sharpe is not an acceptance criterion for EXP-001. It is a secondary economic diagnostic.

HistGradientBoosting is compared with Ridge on the same dates and metrics. It is promoted only if its mean rank IC exceeds Ridge and its improvement is reasonably persistent across folds; aggregate Sharpe alone is insufficient.

**Result**  
Pending.

**Decision**  
Pending.

**Commit / output references**  
Protocol freeze: `04e57206fc4c7751dccc8e48cf799d707736af29`.  
Safeguarded implementation lineage begins at `e3d42f24546edd05c8fd3f8ed9bec8ec15fed9b7`.  
Frozen hold-out manifest and EXP-001 output references will be added after generation.

