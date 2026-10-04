# EXP-002 Results — Nonlinear Attribution and Turnover Reduction

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Workflow run:** `37190136845`

## Research question

EXP-002 asked two development-only questions:

1. Which frozen v0.1 features materially support the HistGradientBoosting rank IC observed in EXP-001?
2. Can causal score smoothing preserve most of that IC while reducing turnover enough to improve 5 bps net performance?

The experiment used the same frozen 30-ETF data snapshot, purged walk-forward folds, five-session target, six-date pre-hold-out embargo, five-sleeve portfolio and transaction-cost model as EXP-001.

## Full HistGradientBoosting benchmark

The full model reproduced the EXP-001 result:

- mean rank IC: **0.02624**;
- HAC t-statistic: **3.849**;
- HAC p-value: **0.000119**;
- annualised turnover: **42.79** times gross notional;
- zero-cost annualised return: **2.21%**;
- 5 bps net annualised return: **0.07%**;
- 5 bps Sharpe: **0.017**.

This exact reproduction is an important internal check: EXP-002 starts from the same nonlinear signal documented in EXP-001.

## Feature ablation

The pre-registered materiality rule required both mean IC loss >= 0.003 and BH-FDR significance at q = 0.10.

| Removed feature | Mean IC loss | Paired HAC p | BH q | Material contributor |
|---|---:|---:|---:|:---:|
| vol_60 | 0.00945 | 0.0502 | 0.1506 | No |
| vol_20 | 0.00887 | 0.0205 | 0.0924 | **Yes** |
| drawdown_60 | 0.00750 | 0.00583 | 0.0524 | **Yes** |
| mom_60 | 0.00351 | 0.4327 | 0.4868 | No |
| mom_20 | 0.00349 | 0.2637 | 0.4747 | No |
| range_1 | 0.00330 | 0.2124 | 0.4747 | No |
| ret_1 | 0.00232 | 0.3497 | 0.4868 | No |
| volume_z_20 | 0.00187 | 0.4307 | 0.4868 | No |
| mom_5 | -0.00077 | 0.7791 | 0.7791 | No |

The clearest supported structure is therefore **recent volatility plus medium-horizon drawdown**.

The result for `vol_60` is also informative. Its point estimate is the largest of all ablations, but the paired variation is sufficiently large that it fails the nine-way FDR rule. This is consistent with possible redundancy between the two volatility horizons and should not be overstated.

Removing `mom_5` marginally improved IC, but the difference is small and statistically weak. It is therefore evidence for possible noise, not sufficient evidence on its own for deletion.

## Causal rank smoothing

Predictions were converted each day to centred cross-sectional percentile ranks and then smoothed causally by symbol with pre-declared EWMA spans of 3, 5 and 10 decision dates.

| Signal | Mean IC | IC retained | HAC p | Ann. turnover | Turnover reduction | 0 bp ann. return | 5 bp ann. return | 5 bp Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Unsmoothed | 0.02624 | 100.0% | 0.000119 | 42.79 | — | 2.21% | 0.07% | 0.017 |
| Span 3 | 0.02373 | 90.4% | 0.00128 | 37.03 | 13.5% | 1.41% | -0.44% | -0.102 |
| Span 5 | 0.02256 | 86.0% | 0.00269 | 32.37 | 24.4% | 1.00% | -0.62% | -0.136 |
| Span 10 | 0.02152 | 82.0% | 0.00539 | 25.38 | 40.7% | 0.63% | -0.64% | -0.136 |

Span 10 passed the IC-retention, significance and turnover-reduction gates, but failed the economic gate because its 5 bps net return was below the unsmoothed baseline. Spans 3 and 5 failed the turnover gate and also failed the economic gate.

No smoothing candidate therefore qualifies.

## Cost-efficiency interpretation

The approximate one-way break-even cost implied by zero-cost return divided by annualised turnover is:

- unsmoothed: **5.16 bps**;
- span 3: **3.80 bps**;
- span 5: **3.10 bps**;
- span 10: **2.49 bps**.

Smoothing lowers turnover, but it lowers gross return even faster. The nonlinear information therefore appears relatively fast-moving at the portfolio-expression stage. Simple temporal averaging is the wrong mechanism for extracting the economic value seen in the IC.

## Decision

Two attribution findings survive the registered rule: `vol_20` and `drawdown_60`.

No causal EWMA smoothing candidate is promoted.

The next justified development experiment is to test a **reduced nonlinear feature specification and explicit turnover-aware portfolio construction**, while keeping the model family, data, validation and hold-out unchanged. That experiment must be registered before its results are inspected.

The final 252-date hold-out remains locked.
