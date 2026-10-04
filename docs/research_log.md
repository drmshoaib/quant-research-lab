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
**Status:** complete — economically encouraging; no candidate promoted

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

## EXP-005 — No-trade band execution

**Date registered:** 4 October 2026  
**Status:** complete — no candidate promoted

**Question**  
Can the fast \`pruned8\` HistGradientBoosting signal be traded more efficiently by ignoring small desired per-name weight changes while executing larger changes immediately, rather than imposing a portfolio-wide turnover budget or temporal smoothing?

**Forecast specification**  
Use the frozen \`pruned8\` HistGradientBoosting model selected in EXP-003 without changing features, hyperparameters, target, walk-forward folds, rank construction or five-sleeve horizon translation.

The instantaneous five-sleeve rank portfolio \(w_t^*\) is the desired target.

**No-trade rule**  
Let \(w_{t-1}\) be the previous actual portfolio and define the desired per-name change

\[
d_{i,t}=w_{i,t}^*-w_{i,t-1}.
\]

For a fixed no-trade band \(b\), names satisfying

\[
|d_{i,t}| \le b
\]

are held exactly at their previous actual weight.

Names with \(|d_{i,t}|>b\) are eligible to trade immediately. Among eligible names, solve the minimum-distance portfolio

\[
\min_w \sum_i (w_i-w_{i,t}^*)^2
\]

subject to dollar neutrality, gross exposure at most 1.0, per-name absolute weight at most 0.08, and the additional monotonicity constraint that every traded name must remain between its previous actual weight and its current target weight. This prevents overshooting the signal target merely to satisfy another constraint.

The previous actual portfolio is always feasible, so the policy can choose not to trade when the active set cannot improve the target while preserving constraints.

Test exactly three pre-declared absolute weight bands:

- \(b=0.005\) (0.5 percentage points of portfolio weight);
- \(b=0.010\) (1.0 percentage point);
- \(b=0.020\) (2.0 percentage points).

These thresholds are defined in per-name portfolio-weight units and are unrelated to the EXP-004 turnover-budget values.

The final development portfolio is forcibly liquidated to zero on the next available pre-hold-out embargo date after the last active sleeve. Terminal liquidation is exempt from the no-trade band but its full transaction cost is charged.

**Solver rule**  
The constrained projection is initialised at the previous feasible portfolio. If SLSQP fails or any constraint is violated beyond \(10^{-7}\), the deterministic fallback is the previous actual portfolio for that date, implying no discretionary trade. Every fallback is counted. EXP-005 is operationally invalid if fallbacks exceed 0.5% of regular projected development dates for any tested band.

**Acceptance rule**  
A no-trade candidate qualifies only if all of the following hold relative to instant pruned8 execution:

1. annualised turnover is reduced by at least 25%;
2. zero-cost annualised return retains at least 80% of the instant portfolio's zero-cost annualised return;
3. 5 bps net annualised return exceeds the instant portfolio's 5 bps net annualised return;
4. 5 bps Sharpe exceeds the instant portfolio's 5 bps Sharpe.

If more than one candidate qualifies, select the qualifying band with the highest 5 bps net annualised return. If two candidates are within 1 basis point of annualised return, select the one with lower annualised turnover.

No other no-trade bands or execution rules are tested in EXP-005.

**Diagnostics**  
For each band report:

- zero-cost and 2/5/10/20 bps annualised return;
- Sharpe and maximum drawdown;
- average and annualised turnover;
- turnover reduction versus instant execution;
- zero-cost return retention;
- average and 95th-percentile tracking error \(\|w_t-w_t^*\|_2\);
- mean active-name fraction and mean held-name fraction;
- mean fraction of desired L1 target change ignored by the band;
- fraction of dates with no discretionary trade;
- solver fallback count and rate.

The model's rank IC is reported only as a frozen reference because the no-trade rule does not change predictions.

**Development-only evaluation**  
Use the exact frozen market-data artifact, 252-date locked hold-out, six-date pre-hold-out embargo, 49-fold purged walk-forward design, five-session target, five-sleeve portfolio translation and transaction-cost assumptions from EXP-001–004.

**Result**  
Pending.

**Decision**  
Pending.

**Commit / output references**  
Frozen data/hold-out: \`9dc3f66770e10159949df9c86d4743824fe94b76\`.  
Current formal development benchmark: instant \`pruned8\`, recorded in EXP-003 at \`ac88f152510bd04f4eb774a4746f3c1aacf2338c\`.  
EXP-004 turnover-budget result: \`c343b89adfb5a02faadddb34339f3a0b52a7e793\`.  
EXP-005 implementation and outputs will be added after execution.

## EXP-006 — Robustness and falsification of pruned8

**Date registered:** 4 October 2026  
**Status:** complete — overall robustness rule failed on asset-group dependence

**Question**  
Does the predictive rank IC of the frozen \`pruned8\` HistGradientBoosting specification survive independent challenges to horizon, time period, asset-group composition and symbol identity, or is the EXP-001–005 result plausibly an artefact of one sample/specification?

**Frozen model**  
Use the \`pruned8\` HistGradientBoosting specification selected in EXP-003:

- \`ret_1\`;
- \`mom_20\`;
- \`mom_60\`;
- \`vol_20\`;
- \`vol_60\`;
- \`range_1\`;
- \`volume_z_20\`;
- \`drawdown_60\`.

No feature, hyperparameter or portfolio rule is selected in EXP-006. Predictive rank IC is the primary object of study. The locked 252-date hold-out remains untouched.

### A. Horizon decay

Refit the same frozen model and validation design at exactly four forward-return horizons:

- 1 session;
- 5 sessions (reference);
- 10 sessions;
- 20 sessions.

For each horizon \(h\), features remain end-of-day at \(t\), execution starts at the next open, the target exits \(h\) sessions later, the train/test purge is \(h+1\) decision dates, and the pre-hold-out embargo is also \(h+1\) eligible decision dates before the fixed hold-out start of 24 September 2025.

The fixed hold-out start is a boundary, not a horizon-specific tuning sample. No target used in development may overlap that boundary.

Report mean/median rank IC, HAC inference using lag \(h-1\) (lag 1 for \(h=1\)), fold stability and annual stability.

For the three alternate horizons \(\{1,10,20\}\), apply Benjamini-Hochberg FDR at \(q=0.10\) to their HAC p-values.

**Horizon-robustness rule:** at least two of the three alternate horizons must have positive mean IC, and at least one of the adjacent horizons \(h=1\) or \(h=10\) must have positive mean IC and survive BH-FDR at \(q=0.10\). The 20-session horizon is allowed to decay.

### B. Chronological subperiod stability

Using only the frozen five-session out-of-sample development predictions, split the ordered scored decision dates into three consecutive blocks of as nearly equal size as possible. The split is based only on date order/count, not results.

For each block report its exact date range, number of IC dates, mean rank IC and HAC test with lag 4.

**Subperiod rule:** all three block mean ICs must be positive, and at least two of the three blocks must have two-sided HAC \(p<0.05\).

### C. Asset-group dependence

Map the existing universe taxonomy into four pre-declared broad groups:

- **US risk assets:** \`US_equity\`, \`US_sector\`, \`real_estate\`, \`biotech\`, \`retail\`;
- **International equity:** \`developed_ex_US\`, \`emerging_markets\`, \`Japan\`, \`United_Kingdom\`, \`China\`;
- **Fixed income:** \`long_treasury\`, \`intermediate_treasury\`, \`short_treasury\`, \`investment_grade_credit\`, \`high_yield_credit\`;
- **Commodities:** \`gold\`, \`silver\`, \`oil\`, \`agriculture\`.

On the frozen five-session predictions:

1. compute daily within-group rank IC for each broad group, using at least four assets;
2. recompute aggregate daily rank IC four times, each time excluding one broad group.

No model is retrained for this diagnostic.

**Asset-group breadth rule:** at least three of the four broad groups must have positive mean within-group IC. In addition, every leave-one-group-out aggregate must retain at least 50% of the full-universe mean IC and remain positive with HAC \(p<0.05\), lag 4.

### D. Symbol-identity placebo

Use the frozen five-session predictions and targets. Preserve every symbol's complete prediction time series, each date's cross-sectional score distribution and all serial dependence, but randomly permute the mapping from prediction-symbol paths to target-symbol paths.

Generate exactly 999 independent global symbol permutations with NumPy seed \`20261004\`. For each permutation compute mean daily cross-sectional Spearman rank IC over the same development dates.

The one-sided empirical placebo p-value is

\[
p_{\mathrm{perm}}=
\frac{1+\#\{\bar{IC}^{perm}\ge \bar{IC}^{obs}\}}
{1000}.
\]

**Placebo rule:** \(p_{\mathrm{perm}}\le0.01\).

### EXP-006 robustness decision

The frozen pruned8 signal receives an overall **robustness pass** only if all four sections A–D pass their pre-registered rules.

If EXP-006 passes, the next step is to prepare the final specification manifest and a concise research note before any hold-out evaluation. Passing EXP-006 does **not** itself authorise opening the hold-out.

If any section fails, record the failure and do not alter these rules after observing the result.

**Commit / output references**  
Frozen data/hold-out: \`9dc3f66770e10159949df9c86d4743824fe94b76\`.  
Current formal development benchmark: instant \`pruned8\`, recorded at \`ac88f152510bd04f4eb774a4746f3c1aacf2338c\`.  
EXP-005 result: \`6593bd4ed72eb6be769f9c3fc55d5f2c667d40b5\`.  
EXP-006 implementation and outputs will be added after execution.

## EXP-007 — Group-neutral target and within-group alpha

**Date registered:** 4 October 2026  
**Status:** proposed

**Question**  
Does the frozen \`pruned8\` HistGradientBoosting specification contain genuine within-asset-group relative-return information after broad asset-class moves are removed from the target, or is the development signal mainly a consequence of between-group structure and the breadth of the US risk-asset block?

**Broad groups**  
Reuse exactly the four pre-declared groups from EXP-006:

- **US risk assets:** \`US_equity\`, \`US_sector\`, \`real_estate\`, \`biotech\`, \`retail\`;
- **International equity:** \`developed_ex_US\`, \`emerging_markets\`, \`Japan\`, \`United_Kingdom\`, \`China\`;
- **Fixed income:** \`long_treasury\`, \`intermediate_treasury\`, \`short_treasury\`, \`investment_grade_credit\`, \`high_yield_credit\`;
- **Commodities:** \`gold\`, \`silver\`, \`oil\`, \`agriculture\`.

No group definition may change after results are observed.

**Group-neutral target**  
Keep the five-session next-open-to-open raw return timing from the frozen protocol. For symbol \(i\) in broad group \(g(i)\), define

\[
y^{GN}_{i,t}
=
r^{(5)}_{i,t}
-
\frac{1}{N_{g(i),t}}
\sum_{j\in g(i)} r^{(5)}_{j,t}.
\]

Thus each broad group's same-date target mean is zero by construction. The model receives no group label or group dummy as a feature.

Use the frozen \`pruned8\` features and the fixed HistGradientBoosting hyperparameters from EXP-003. Use the same 756-date minimum training window, 63-date test blocks, 63-date step, six-date train/test purge and six-date pre-hold-out embargo as the five-session reference experiment.

The 252-date hold-out remains locked and is not scored.

**Control model**  
On the exact same folds and dates, refit the same \`pruned8\` HistGradientBoosting model using the original full-universe-relative five-session target. This control is not a new model-selection candidate; it provides a same-run reference for within-group IC retention.

**Primary evaluation**  
For both the group-neutral model and control model:

1. compute daily Spearman rank IC separately inside each of the four broad groups, requiring at least four assets;
2. form an **equal-weight four-group composite IC** each date by averaging the available group ICs, so the 16-name US risk block receives the same group weight as each smaller block;
3. form an **equal-weight non-US composite IC** each date by averaging International equity, Fixed income and Commodities.

Use Newey-West/HAC inference with lag 4 for the composite series and each group series.

Also report chronological thirds for the group-neutral equal-weight four-group composite, using the same deterministic date-count split rule as EXP-006.

**EXP-007 acceptance rule**  
The group-neutral specification passes only if all of the following hold:

1. equal-weight four-group composite mean IC is positive with HAC two-sided \(p<0.05\);
2. at least three of the four broad groups have positive mean within-group IC;
3. equal-weight non-US composite mean IC is positive with HAC two-sided \(p<0.05\);
4. group-neutral equal-weight four-group composite mean IC retains at least 80% of the control model's equal-weight four-group composite mean IC on the same scored dates;
5. all three chronological thirds of the group-neutral four-group composite have positive mean IC, with at least two of the three having HAC \(p<0.10\).

The 80% retention threshold is carried forward from earlier development experiments rather than chosen from EXP-007 outcomes.

No alternative target centring, group weighting, feature set, model family, horizon or acceptance threshold is tested in EXP-007.

**Interpretation rule**  
Passing EXP-007 would support the claim that the predictive structure is not merely broad asset-class rotation and that meaningful within-group alpha survives outside the US-risk block.

Failing EXP-007 would be recorded as evidence that the current signal depends materially on between-group structure or on US-risk cross-sectional breadth. The failure would not be repaired by redefining groups after the fact.

Passing EXP-007 does not itself authorise opening the final hold-out. A final specification manifest and research note must still be prepared before any hold-out evaluation.

**Commit / output references**  
Frozen data/hold-out: \`9dc3f66770e10159949df9c86d4743824fe94b76\`.  
Current formal development benchmark: instant \`pruned8\`, recorded at \`ac88f152510bd04f4eb774a4746f3c1aacf2338c\`.  
EXP-006 robustness result: \`03213bb4f3997271177dd4373e1d2edadddbb0ab\`.  
EXP-007 implementation and outputs will be added after execution.

