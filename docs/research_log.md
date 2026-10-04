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
4. positive mean annual rank IC in at least 60% of development calendar years with at least 20 daily IC observations.

Portfolio Sharpe is not an acceptance criterion for EXP-001. It is a secondary economic diagnostic.

HistGradientBoosting is compared with Ridge on the same dates and metrics. It is promoted only if its mean rank IC exceeds Ridge and its improvement is reasonably persistent across folds; aggregate Sharpe alone is insufficient.

**Result**  
Pending.

**Decision**  
Pending.

**Commit / output references**  
Protocol freeze: `04e57206fc4c7751dccc8e48cf799d707736af29`.  
Safeguarded implementation lineage begins at `e3d42f24546edd05c8fd3f8ed9bec8ec15fed9b7`.  
Frozen data/hold-out commit: `9dc3f66770e10159949df9c86d4743824fe94b76`.\nEXP-001 output references will be added after the run.

## EXP-002 — Nonlinear attribution and turnover reduction

**Date registered:** 4 October 2026  
**Status:** complete — attribution informative; smoothing rejected

**Question**  
Which of the nine frozen v0.1 features materially contribute to the development-sample HistGradientBoosting rank IC observed in EXP-001, and can that signal be expressed with substantially lower turnover without materially degrading predictive information?

**Part A — feature attribution**  
Use leave-one-feature-out HistGradientBoosting ablations. For each feature, refit the same purged walk-forward model after removing that feature and compare its daily rank IC with the full nine-feature HistGradientBoosting baseline on exactly the same development dates.

For feature (j), define the paired daily IC loss as

[
d_{j,t}=IC^{full}_t-IC^{-j}_t.
]

Report mean IC loss and a Newey-West/HAC test of (E[d_{j,t}]=0) with lag 4.

Because nine ablations are tested, apply Benjamini-Hochberg false-discovery-rate control at (q=0.10).

A feature is labelled a **material contributor** only if:

1. mean IC loss is at least 0.003; and
2. the paired ablation test survives BH FDR at (q=0.10).

Ablation evidence is interpreted conditionally: correlated features may substitute for one another, so a non-material ablation does not prove that a feature contains no information.

**Part B — turnover reduction**  
Do not refit or retune HistGradientBoosting. Start from the frozen full-model out-of-sample predictions from the EXP-002 run.

To make smoothing invariant to model-score scale across walk-forward folds:

1. convert each date's HistGradientBoosting predictions to centred cross-sectional percentile ranks;
2. apply a causal EWMA by symbol using only current and past ranked scores;
3. test exactly three pre-declared spans: 3, 5 and 10 decision dates;
4. pass the smoothed score through the same rank portfolio, five-sleeve horizon translation and cost model used in EXP-001.

The unsmoothed full HistGradientBoosting signal is the benchmark.

**Turnover-reduction acceptance rule**  
A smoothing candidate qualifies only if all of the following hold relative to the unsmoothed HistGradientBoosting benchmark from the same EXP-002 run:

1. mean rank IC retains at least 80% of baseline mean IC;
2. mean rank IC remains positive with HAC two-sided (p<0.05);
3. annualised turnover is reduced by at least 30%;
4. 5 bps net annualised return exceeds the unsmoothed baseline.

If more than one candidate qualifies, select the qualifying candidate with the lowest annualised turnover. No additional smoothing spans are tested in EXP-002.

**Development-only evaluation**  
Use the same frozen data snapshot, 252-date locked hold-out, six-date pre-hold-out embargo, purged walk-forward folds, five-session target, portfolio constraints and transaction-cost assumptions as EXP-001.

For the full model, every ablation and every smoothing candidate report mean/median rank IC, HAC inference, fold/year stability and portfolio performance. For smoothing candidates also report turnover reduction and cost sensitivity at 0, 2, 5, 10 and 20 bps.

**Result**  
The full HistGradientBoosting benchmark reproduced EXP-001 exactly: mean rank IC 0.02624, HAC t = 3.849, p = 1.19e-4, annualised turnover 42.79, and 5 bps net annualised return 0.07%.

Two features met the pre-registered material-contributor rule after nine-way BH-FDR control:

- `vol_20`: mean IC loss 0.00887; paired HAC p = 0.0205; BH q = 0.0924;
- `drawdown_60`: mean IC loss 0.00750; paired HAC p = 0.00583; BH q = 0.0524.

`vol_60` had the largest raw point-estimate IC loss (0.00945) but did not survive BH-FDR (q = 0.151), so it is not labelled a material contributor under the registered rule. Removing `mom_5` slightly increased mean IC by 0.00077, but this difference was not statistically meaningful.

All three causal smoothing candidates retained at least 80% of baseline IC and remained statistically positive. Span 10 reduced annualised turnover by 40.7%, exceeding the 30% turnover gate, but its 5 bps net annualised return fell to -0.64% versus +0.07% for the unsmoothed baseline. Spans 3 and 5 reduced turnover by only 13.5% and 24.4%, respectively, and also reduced 5 bps net return. No smoothing candidate passed all four pre-registered gates.

The zero-cost annualised return declined monotonically from 2.21% unsmoothed to 1.41%, 1.00% and 0.63% for spans 3, 5 and 10. Approximate break-even one-way cost therefore fell from 5.16 bps unsmoothed to 3.80, 3.10 and 2.49 bps. In this experiment, causal smoothing destroyed gross alpha faster than it saved turnover.

**Decision**  
Retain `vol_20` and `drawdown_60` as supported nonlinear contributors. Treat `vol_60` as suggestive but not confirmed because it failed the registered FDR rule.

Reject EWMA score smoothing with spans 3, 5 and 10 as the turnover solution. No smoothing candidate is promoted.

Do not unlock the hold-out. A justified next experiment is a pre-registered reduced-feature / turnover-control study that tests whether the supported volatility-drawdown structure can be expressed more efficiently, without adding new features or inspecting hold-out outcomes.

**Commit / output references**  
Frozen data/hold-out: `9dc3f66770e10159949df9c86d4743824fe94b76`.  
EXP-001 recorded result: `35f5268e52c4a2a66d29047fb53073dc2184e521`.  
EXP-002 registration: `ca72cfda628e106dfbc62af05cf63558b606837a`.  
EXP-002 implementation: `78d3a53ebde435132eb031422a3d01231188eabc`.  
EXP-002 workflow commit: `25bf422d55b3f2f1451222b58a9563dff8611121`.  
Workflow run: `37190136845`.  
Development-results artifact: `11299225073` (digest `sha256:0156f1f6b0ed1d9b0f1f38011717f9c50fe40afcf979a79826853ce7a03b9640`).

## EXP-003 — Reduced nonlinear specification and turnover-aware execution

**Date registered:** 4 October 2026  
**Status:** proposed

**Question**  
Can the nonlinear ETF signal identified in EXP-001/002 be represented with a smaller feature set, and can portfolio-level partial adjustment reduce trading costs without smoothing away the predictive signal?

**Part A — reduced HistGradientBoosting specifications**  
Use the same frozen HistGradientBoosting hyperparameters and walk-forward folds. Test exactly four pre-declared feature sets:

1. **full9** — all nine frozen v0.1 features;
2. **core2** — `vol_20`, `drawdown_60`;
3. **core3** — `vol_20`, `vol_60`, `drawdown_60`;
4. **pruned8** — full9 excluding `mom_5`.

No additional feature combinations are tested in EXP-003.

A reduced specification is **statistically eligible** only if all of the following hold:

1. mean daily rank IC is at least 80% of the full9 mean IC;
2. mean rank IC is positive with Newey-West/HAC two-sided (p<0.05), lag 4;
3. median fold-level rank IC is positive;
4. at least 70% of eligible development years have positive mean rank IC.

If more than one reduced specification is eligible, select the one with the fewest features. If two eligible specifications have the same feature count, select the one with the higher mean rank IC.

If no reduced specification is eligible, retain full9 and proceed to Part B with full9.

**Part B — turnover-aware portfolio adjustment**  
For the selected Part-A specification, form the same daily rank cohort portfolios and five-sleeve live target portfolio (w_t^*) as in EXP-001/002.

Do not smooth model scores. Instead test exactly two recursive portfolio-level adjustment rules in addition to instant rebalancing:

[
w_t^{(lambda)}=(1-lambda)w_{t-1}^{(lambda)}+lambda w_t^*,
]

with (lambdain{0.50,0.25}), starting from zero weights.

Because the rule is a convex combination of feasible dollar-neutral portfolios, it preserves neutrality, gross exposure and per-name bounds. Transaction costs are charged on the actual adjusted weights.

The unsmoothed, instant target portfolio ((lambda=1)) is the execution benchmark.

A turnover-aware rule qualifies only if:

1. annualised turnover is reduced by at least 30% relative to instant execution for the same selected feature specification;
2. zero-cost annualised return retains at least 80% of the instant portfolio's zero-cost annualised return;
3. 5 bps net annualised return exceeds the instant portfolio's 5 bps net annualised return.

If both partial-adjustment rules qualify, select (lambda=0.50) because it is the less interventionist rule. No other adjustment rates are tested in EXP-003.

**Secondary control**  
Report the same instant-execution portfolio metrics for all four Part-A feature specifications so that any turnover effect from feature reduction itself is visible. Do not select a model based on Sharpe alone.

**Development-only evaluation**  
Use the exact frozen market-data artifact, 252-date locked hold-out, six-date pre-hold-out embargo, purged 49-fold walk-forward design, five-session target, five-sleeve translation, gross/name constraints and 0/2/5/10/20 bps cost grid from EXP-001/002.

**Result**  
Pending.

**Decision**  
Pending.

**Commit / output references**  
Frozen data/hold-out: `9dc3f66770e10159949df9c86d4743824fe94b76`.  
EXP-002 recorded result: `7c0d1af4ca3e861712b1894e24067ade6faa78ce`.  
EXP-003 implementation and outputs will be added after execution.

