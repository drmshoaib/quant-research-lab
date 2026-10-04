# Nonlinear Cross-Sectional ETF Ranking: Development Evidence, Robustness, and Transaction-Cost Limits

**Author:** Muhammad Shoaib  
**Research programme:** Quant Research Lab v0.2  
**Status:** Development frozen after portfolio-accounting audit; final 252-date hold-out locked and unevaluated  
**Date:** 4 October 2026

## Executive Summary

This study asks whether information available at the close of a trading day can rank future relative returns across a fixed universe of 30 liquid ETFs. The design uses next-open execution, purged expanding-window validation, an immutable 252-date final hold-out, pre-registered experiment rules, HAC/Newey-West inference, explicit turnover costs, and a permanent record of negative results.

The strongest development specification is an eight-feature HistGradientBoosting model, **pruned8**, evaluated at a five-session horizon. Across 3,087 out-of-sample development dates it produces mean daily cross-sectional Spearman rank IC **0.02701**, HAC `t=3.922`, `p=8.78e-5`, median fold IC **0.02766**, and positive mean IC in **12 of 13** eligible development years. A 999-replicate global symbol-identity placebo gives empirical one-sided `p=0.001`. The signal is weak at one session but remains statistically significant at 10 and 20 sessions, which is more consistent with a medium-horizon ranking effect than a next-day anomaly.

The statistical signal is substantially stronger than the economic backtest. Under the frozen five-sleeve, dollar-neutral rank portfolio, corrected zero-cost annualised arithmetic return is **2.34%**, but annualised turnover is **41.91 times gross notional**. At the pre-specified 5 bps one-way cost, annualised arithmetic net return is only **0.25%** with Sharpe **0.065**, and performance is negative at 10 bps. Several turnover-reduction mechanisms improved cost efficiency, but none satisfied its complete pre-registered promotion rule. The evidence therefore supports a predictive-ranking claim, not a production-ready trading strategy.

Robustness is mixed. Horizon and chronological tests pass, and the symbol-identity placebo is decisively rejected. However, EXP-006 fails its overall rule because removing the 16-name US risk-asset block reduces aggregate IC to **0.01183**, only **43.8%** of the full-universe value, with HAC `p=0.179`. A subsequent group-neutral experiment shows that this weakness is not simply broad asset-class rotation: after removing each broad group's target mean and retraining the model, the equal-weight four-group composite retains **86.3%** of the control within-group IC and remains significant at `p=0.00981`. Nevertheless, its equal-weight non-US composite has `p=0.0501247`, narrowly failing the pre-registered `p<0.05` requirement.

> **Development conclusion:** A statistically significant nonlinear cross-sectional ETF ranking signal exists in the frozen development sample, is strongest at medium horizons, survives temporal and symbol-identity falsification, and retains substantial within-group information after broad asset-class neutralisation. Its economic value is fragile to realistic trading costs, and its cross-asset breadth is not strong enough to satisfy all pre-registered robustness criteria.

The final hold-out has not been inspected.

## 1. Research Question

The primary question is whether a compact set of end-of-day market features can rank five-session forward relative ETF returns out of sample. Predictive ranking is treated as the primary research object; portfolio returns are secondary evidence because portfolio engineering and transaction costs can obscure whether a forecasting signal exists at all.

Every material experiment after the initial baseline was registered in `docs/research_log.md` before its result was inspected. Promotion rules were not relaxed when experiments narrowly missed them.

## 2. Data and Frozen Research Sample

The universe contains 30 ETFs spanning US broad equity and sectors, developed and emerging international equity, country ETFs, Treasury duration, investment-grade and high-yield credit, precious metals, oil, agriculture, real estate, biotechnology and retail.

A fixed ETF universe was chosen for v0.2 to reduce the constituent-membership survivorship problem that would arise from backtesting today's equity constituents through history. It does **not** eliminate universe-selection bias: the ETF set itself was chosen ex post, ETFs have different inception dates, liquidity profiles and economic exposures, and the 30-name panel is not a point-in-time representation of the full investable market.

The research window is frozen from **1 January 2010 to 3 October 2026 exclusive**. Actual adjusted observations run from **4 January 2010 through 2 October 2026**. The frozen dataset contains **126,390 rows** across 30 symbols and has SHA-256 `ec782ac2cd812a6d81abcbf9cbcdecdd448ab8822b585fbd07c3a74968a3bbd3`.

Yahoo/yfinance data are requested with `auto_adjust=True`, so OHLC prices are adjusted for splits and distributions.

The final hold-out consists of **252 eligible decision dates from 24 September 2025 through 24 September 2026**. It is defined from the frozen market/target calendar rather than the feature-complete frame, so changing feature missingness cannot move the hold-out boundary. The hold-out remains unevaluated.

## 3. Timing, Target, and Leakage Controls

At decision date `t`, all features use information available by the close of `t`. The earliest executable price is the next session's open. For the primary five-session horizon:

```text
r_raw(i,t) = log( O(i,t+6) / O(i,t+1) )
y(i,t)     = r_raw(i,t) - cross_sectional_mean_t(r_raw)
```

Development validation uses an expanding purged walk-forward scheme with a **756-date minimum training history**, **63-date test blocks**, **63-date steps**, a **6-date train/test purge**, and a **6-date pre-hold-out embargo**. No hold-out observation enters fitting, feature selection, execution-rule selection or robustness work.

The pre-hold-out embargo prevents five-session development labels from using the outcome path belonging to the nominal hold-out.

## 4. Frozen Development Model

The final **pruned8** feature set is:

| Feature | Definition |
|---|---|
| `ret_1` | 1-session log close return |
| `mom_20` | 20-session log-price change |
| `mom_60` | 60-session log-price change |
| `vol_20` | 20-session realised volatility, annualised |
| `vol_60` | 60-session realised volatility, annualised |
| `range_1` | `(high-low)/close` |
| `volume_z_20` | 20-session z-score of `log1p(volume)` |
| `drawdown_60` | close / 60-session rolling peak - 1 |

`mom_5` was removed in EXP-003 because pruned8 was the only reduced specification satisfying all pre-registered statistical eligibility rules. This is not proof that five-day momentum is individually harmful; its leave-one-out improvement in EXP-002 was not statistically significant.

The final development model is `HistGradientBoostingRegressor` with learning rate **0.05**, **250** maximum iterations, **15** maximum leaf nodes, minimum leaf size **40**, L2 regularisation **1.0**, and random seed **42**. No hyperparameter search was performed.

## 5. From Linear Baseline to Nonlinear Signal

EXP-001 compared a Ridge baseline with the nonlinear model:

| Metric | Ridge | HistGradientBoosting |
|---|---:|---:|
| Mean rank IC | 0.00365 | **0.02624** |
| HAC p-value | 0.664 | **0.000119** |
| Median fold IC | 0.00324 | **0.02301** |
| Positive development years | 53.8% | **84.6%** |

The pre-registered Ridge hypothesis failed. The nonlinear comparator showed significant ranking information and became the focus of subsequent work.

EXP-002 used leave-one-feature-out ablation with Benjamini-Hochberg FDR control. `vol_20` and `drawdown_60` were the only individual features satisfying the registered material-contributor rule. `vol_60` had the largest raw IC loss when removed but did not survive the multiple-testing rule.

EXP-003 showed why ablation could not be read as a minimal feature recipe. The two-feature volatility/drawdown model retained only **45.8%** of full-model IC; adding `vol_60` raised retention to **67.9%**. By contrast, pruned8 produced mean IC **0.02701**, slightly above the full nine-feature model, with positive mean IC in **92.3%** of eligible years.

## 6. Statistical Evidence for pruned8

The frozen five-session development result is mean daily rank IC **0.02701**, median fold IC **0.02766**, HAC `t=3.922`, two-sided `p=0.0000878`, with positive mean IC in **12/13 development years**.

### Horizon structure

| Horizon | Mean IC | HAC p | BH q for alternate horizons |
|---:|---:|---:|---:|
| 1 session | 0.00413 | 0.406 | 0.406 |
| 5 sessions | **0.02701** | **0.0000878** | - |
| 10 sessions | **0.02366** | **0.00816** | **0.0202** |
| 20 sessions | **0.03166** | **0.0135** | **0.0202** |

The signal is weak at one day but persists over 5-20 sessions. This argues against interpreting it as a very short-lived next-day anomaly.

### Chronological stability

| Period | Mean IC | HAC p |
|---|---:|---:|
| 2013-04-11 to 2017-05-10 | **0.03279** | **0.00496** |
| 2017-05-11 to 2021-06-11 | **0.02688** | **0.0324** |
| 2021-06-14 to 2025-07-18 | **0.02136** | 0.0629 |

All three means are positive, although the raw-target aggregate signal weakens over time.

### Symbol-identity placebo

EXP-006 globally permuted complete prediction-symbol paths **999** times while preserving each date's score distribution and the serial structure of each prediction path. The null distribution had mean **0.00010**, standard deviation **0.00654**, and 95th percentile **0.01141**. The observed IC of **0.02701** produced empirical one-sided `p=0.001`.

## 7. Asset-Group Dependence and Group-Neutral Falsification

Within-group mean IC in EXP-006 was positive in all four pre-declared broad groups:

| Group | Mean IC | HAC p |
|---|---:|---:|
| US risk assets | **0.02457** | **0.00227** |
| International equity | 0.00675 | 0.648 |
| Fixed income | **0.04459** | **0.00413** |
| Commodities | 0.00943 | 0.534 |

However, removing the US risk-asset block from the aggregate ranking reduced mean IC to **0.01183**, only **43.8%** of the full-universe value, with HAC `p=0.179`. This caused EXP-006 to fail its overall pre-registered robustness rule.

EXP-007 tested whether this dependence was simply broad asset-class rotation. The training target was redefined by subtracting each broad group's same-date mean forward return while keeping features, model, dates, folds and hyperparameters unchanged.

Under group-neutral training, the equal-weight four-group mean IC was **0.01806**, HAC `p=0.00981`, retaining **86.32%** of the original-target control's within-group IC. All four broad-group mean ICs remained positive.

The equal-weight non-US composite was positive at **0.01725**, but HAC `p=0.0501247`, narrowly above the pre-registered `p<0.05` threshold. EXP-007 therefore formally failed.

The interpretation is narrower than either 'US-only' or 'fully cross-asset'. Broad asset-class rotation does not explain the signal: substantial within-group information survives neutralisation, including a strong fixed-income result. But evidence for the equal-weight non-US component remains borderline under the registered rule.

## 8. Portfolio Translation and Transaction-Cost Limits

The primary forecast is translated into five staggered equal-capital sleeves. Each daily score produces a dollar-neutral rank cohort entering at the next open and remaining active for five one-session open-to-open periods. Gross exposure is capped at **1.0** and each cohort name at **0.08 absolute weight**.

For instant pruned8 execution:

| One-way cost | Annualised arithmetic return |
|---:|---:|
| 0 bps | **2.34%** |
| 2 bps | **1.51%** |
| 5 bps | **0.25%** |
| 10 bps | **-1.85%** |
| 20 bps | **-6.04%** |

Annualised turnover is **41.91 times gross notional**. Approximate one-way break-even cost is **5.59 bps**. At the registered 5 bps cost, Sharpe is only **0.065**.

This is the clearest distinction between statistical and economic evidence in the project: the model ranks returns better than chance, but the benchmark portfolio captures that information only at very thin net economics.

### Execution experiments

Score smoothing (EXP-002) and uniform portfolio inertia (EXP-003) reduced turnover but destroyed gross alpha faster than they saved costs. Selective turnover budgets and no-trade bands (EXP-004/005) improved 5 bps economics, but no candidate passed its complete pre-registered promotion gate.

The closest turnover-budget candidate raised corrected 5 bps annualised return from **0.25% to 0.38%** while reducing turnover **28.7%**, but retained only **79.965%** of zero-cost return against an 80% requirement, a miss of about **0.035 percentage points**. The strongest no-trade candidate raised 5 bps return to **0.39%** while retaining **92.1%** of gross return, but reduced turnover only **15.6%** against a 25% requirement. Neither threshold was relaxed after the result.

Instant pruned8 therefore remains the formal execution benchmark.

## 9. What Failed

- **Ridge baseline:** no statistically convincing rank signal.
- **Two/three-feature volatility-drawdown cores:** insufficient IC retention.
- **EWMA score smoothing:** lower turnover but worse net economics.
- **Uniform weight inertia:** lower turnover but excessive gross-alpha loss.
- **Turnover-budget projection:** economically promising, but no candidate passed all promotion gates.
- **No-trade bands:** moderate filtering improved cost efficiency, but the turnover/alpha trade-off prevented promotion.
- **EXP-006 overall robustness:** failed because aggregate IC depended materially on inclusion of the US risk-asset block.
- **EXP-007 overall group-neutral test:** failed because the equal-weight non-US HAC p-value was **0.0501247**, not below the registered 0.05 threshold.

These failures prevent a stronger claim such as robust cross-asset alpha or a profitable production strategy at realistic costs.

## 10. Limitations

The universe is only 30 ETFs and is fixed rather than a point-in-time equity universe. Cross-sectional breadth is uneven: the US risk block contains 16 names while commodities contain four.

Yahoo adjusted OHLC is suitable for this research stage but is not an institutional execution dataset. The cost model does not model instrument/date-specific bid-ask spreads, market impact, borrow, financing, taxes, queue position or intraday execution uncertainty. The diagnostic portfolio is dollar neutral but **not** beta-, duration-, volatility- or factor-neutral; equal weight is therefore not equal risk across heterogeneous ETFs.

The model was developed through seven sequential pre-registered experiments on one development sample. Pre-registration constrains but does not eliminate researcher degrees of freedom. The untouched final hold-out is therefore essential if a stronger out-of-sample claim is desired.

Statistical significance also does not imply economic materiality. The IC evidence is meaningful, but the portfolio has a narrow transaction-cost margin.

## 11. Frozen Development Conclusion

> **Using a frozen 30-ETF panel, next-open execution and purged expanding-window validation, a fixed HistGradientBoosting model using eight end-of-day price/volume features produces statistically significant medium-horizon cross-sectional ranking information. The signal survives chronological segmentation, 10- and 20-session horizon tests and a 999-replicate symbol-identity placebo. Much of the within-group signal survives broad asset-class target neutralisation. However, the evidence does not satisfy every pre-registered cross-asset robustness test, and high turnover leaves little net return at a 5 bps one-way cost assumption.**

The study does **not** establish a production-ready trading strategy, robustness to materially higher transaction costs, universe-independent alpha, strong non-US evidence at the registered 5% threshold, or future performance.

## 12. Final Hold-Out

**Status: LOCKED - no result has been inspected.**

The immutable hold-out contains 252 eligible decision dates from **24 September 2025 to 24 September 2026**.

If final evaluation is authorised, it must use `configs/final_specification_v0.2.json` without further development changes:

- primary target: five-session full-universe-relative next-open-to-open return;
- model: frozen pruned8 HistGradientBoosting;
- primary metric: daily cross-sectional Spearman rank IC;
- inference: HAC/Newey-West, lag 4;
- secondary portfolio: instant five-sleeve rank portfolio;
- base transaction cost: 5 bps one way.

The hold-out is to be evaluated **once**. The result must be reported unchanged even if weak, insignificant or negative. No post-holdout feature, model, threshold or execution retuning is permitted within v0.2.

## 13. Conclusion

The most important outcome is not a high Sharpe ratio. It is a reproducible chain of evidence separating a statistically detectable nonlinear ranking signal from the much harder problem of converting that signal into robust net returns.

The development data provide statistically supported evidence that the model is learning non-random medium-horizon cross-sectional structure. They also show that the effect is not uniformly broad across asset groups and that turnover costs consume most of the apparent portfolio edge.

That combination of positive and negative evidence is the appropriate basis for deciding whether the one remaining untouched sample should be spent on a final test.

---

### Reproducibility record

The full record is in `docs/research_protocol.md`, `docs/research_log.md`, `docs/exp001_results.md` through `docs/exp007_results.md`, `docs/accounting_correction.md`, `configs/data_snapshot.json`, `configs/holdout_dates.csv`, and `configs/final_specification_v0.2.json`.

The final statistical development evidence was produced under workflow commit `56b22b231d3e3e6c485b680cba34ed2627713c74`. Portfolio economics were subsequently recomputed under corrected simple-return accounting in workflow run `37199738636` at code commit `0eb8aacaa1b7dbee555a7d2bcba6b6fe44c0955b`, before any hold-out evaluation.
