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
**Status:** complete — pruned8 selected; partial adjustment rejected

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

Because the rule is a convex combination of feasible dollar-neutral portfolios, it preserves neutrality, gross exposure and per-name bounds. Transaction costs are charged on the actual adjusted weights. For all execution variants, one additional zero-weight liquidation row is appended on the next available pre-hold-out embargo decision date after the final active sleeve; partial-adjustment variants are forced exactly to zero on that row. This counts terminal trading costs and prevents residual development exposure from entering the hold-out.

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
The full9 HistGradientBoosting benchmark reproduced the prior signal: mean rank IC 0.02624, HAC p = 1.19e-4, positive-year fraction 84.6%, and 5 bps net annualised return 0.07%.

Of the three pre-registered reduced specifications, only `pruned8` (full9 excluding `mom_5`) passed every statistical eligibility gate. Its mean rank IC was 0.02701 (102.9% of full9), HAC p = 8.78e-5, median fold IC 0.02766, and 12 of 13 eligible years were positive (92.3%). Its instant portfolio had annualised turnover 41.91, zero-cost annualised return 2.25%, and 5 bps net annualised return 0.15%.

The `core3` volatility/drawdown specification remained statistically significant (mean IC 0.01781, HAC p = 0.00576, 84.6% positive years) but retained only 67.9% of full9 mean IC and therefore failed the pre-registered 80% retention gate. `core2` retained only 45.8% of full9 IC and its HAC p-value was 0.0616. Thus the material ablations identified in EXP-002 are important conditional contributors, but they are not sufficient to reproduce the full nonlinear signal.

For the selected `pruned8` specification, portfolio partial adjustment did not solve the turnover problem. (lambda=0.50) reduced turnover by 27.8% but retained only 70.2% of zero-cost return and did not improve 5 bps net return. (lambda=0.25) reduced turnover by 49.7% but retained only 44.6% of zero-cost return and produced a negative 5 bps net return. Neither rule qualified.

The pruned8 instant portfolio's approximate one-way break-even cost improved slightly to about 5.37 bps, from about 5.16 bps for full9. This is an incremental improvement, not evidence of a robust high-cost strategy.

**Decision**  
Promote `pruned8` as the current development model specification because it is the only reduced model satisfying all pre-registered statistical gates and it is more parsimonious than full9. Do not interpret this as proof that `mom_5` is individually harmful; EXP-002 did not show a statistically significant ablation benefit from removing it.

Reject portfolio-level partial adjustment at (lambda=0.50) and (lambda=0.25). The results reinforce the conclusion from EXP-002 that uniform temporal inertia destroys useful gross alpha faster than it saves trading cost.

Do not unlock the hold-out. The next justified experiment should preserve the fast pruned8 signal and allocate a fixed turnover budget selectively to the largest portfolio changes, rather than slowing every position uniformly.

**Commit / output references**  
Frozen data/hold-out: `9dc3f66770e10159949df9c86d4743824fe94b76`.  
EXP-002 recorded result: `7c0d1af4ca3e861712b1894e24067ade6faa78ce`.  
EXP-003 registration: `46f69d890cc58293b2c426ca91067d223ed018ee`.  
Terminal-liquidation clarification: `55e5b447f35d217010b6749536c54077d9cd54e8`.  
EXP-003 implementation: `7751eb820dcf7f25ac25967e380bcfddad29c6c7`.  
Cost-key compatibility fix: `9f99678631eb64418e79637678817280c8b6a8c0`.  
Successful workflow commit: `dc359949e26188d99f0b0f69bc8ca1f23409c730`.  
Workflow run: `37191103896`.  
Development-results artifact: `11299500822` (digest `sha256:561697fcce6519bae1f1cfad72d3f1153250a11f6994125f8a4fa9107eb339c2`).

## EXP-004 — Turnover-budgeted portfolio projection

**Date registered:** 4 October 2026  
**Status:** proposed

**Question**  
Can the fast \`pruned8\` HistGradientBoosting signal selected in EXP-003 be expressed more efficiently by allocating a fixed daily turnover budget to the most important portfolio changes, rather than slowing every position uniformly?

**Forecast specification**  
Use the frozen \`pruned8\` HistGradientBoosting model from EXP-003 without changing features, hyperparameters, target, walk-forward folds, rank construction or five-sleeve horizon translation.

The instantaneous five-sleeve rank portfolio \(w_t^*\) is the desired target.

**Turnover-budgeted projection**  
At each development date, choose the actual portfolio \(w_t\) by solving

\[
\min_w \sum_i (w_i-w_{i,t}^*)^2
\]

subject to

\[
\sum_i w_i = 0,
\]

\[
\sum_i |w_i| \le 1,
\]

\[
|w_i| \le 0.08,
\]

and

\[
\sum_i |w_i-w_{i,t-1}| \le \tau.
\]

The previous actual portfolio \(w_{t-1}\), not the previous target, defines turnover. The optimisation is causal and uses no realised returns.

SLSQP is initialised at the previous feasible portfolio. If the numerical solver fails or violates a constraint beyond \(10^{-7}\), the deterministic fallback is the largest feasible proportional move from the previous portfolio toward the current target; every fallback is counted. EXP-004 is considered operationally invalid if fallbacks exceed 0.5% of projected development dates for any tested budget.

Test exactly three pre-declared daily L1 turnover budgets:

- \(\tau=0.12\);
- \(\tau=0.10\);
- \(\tau=0.08\).

The instant pruned8 portfolio is the benchmark.

The final development portfolio is forcibly liquidated to zero on the next available pre-hold-out embargo date after the last active sleeve. This terminal liquidation is exempt from the daily turnover budget, but its transaction cost is fully charged. This ensures no development exposure enters the locked hold-out.

**Acceptance rule**  
A turnover-budgeted candidate qualifies only if all of the following hold relative to instant pruned8 execution:

1. annualised turnover is reduced by at least 25%;
2. zero-cost annualised return retains at least 80% of the instant portfolio's zero-cost annualised return;
3. 5 bps net annualised return exceeds the instant portfolio's 5 bps net annualised return;
4. 5 bps Sharpe exceeds the instant portfolio's 5 bps Sharpe.

If more than one candidate qualifies, select the qualifying budget with the highest 5 bps net annualised return. If two candidates are effectively tied to within 1 basis point of annualised return, select the one with lower annualised turnover.

No other turnover budgets or objective functions are tested in EXP-004.

**Diagnostics**  
For each budget report:

- zero-cost and 2/5/10/20 bps annualised return;
- Sharpe and maximum drawdown;
- average and annualised turnover;
- turnover reduction versus instant execution;
- zero-cost return retention;
- average and 95th-percentile tracking error \(\|w_t-w_t^*\|_2\);
- fraction of dates on which the turnover constraint is binding to within \(10^{-6}\);
- optimisation failure count.

The model's rank IC is reported only as a frozen reference because portfolio projection does not alter predictions.

**Development-only evaluation**  
Use the exact frozen market-data artifact, 252-date locked hold-out, six-date pre-hold-out embargo, 49-fold purged walk-forward design, five-session target, five-sleeve portfolio translation and transaction-cost assumptions from EXP-001–003.

**Result**  
Pending.

**Decision**  
Pending.

**Commit / output references**  
Frozen data/hold-out: \`9dc3f66770e10159949df9c86d4743824fe94b76\`.  
Current development benchmark: \`pruned8\` from EXP-003, recorded at \`ac88f152510bd04f4eb774a4746f3c1aacf2338c\`.  
EXP-004 implementation and outputs will be added after execution.

