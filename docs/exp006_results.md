# EXP-006 Results — Robustness and Falsification of pruned8

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Successful workflow run:** `37194799457`

## Executive result

EXP-006 subjected the frozen pruned8 HistGradientBoosting signal to four pre-registered robustness challenges.

| Section | Result |
|---|---|
| Horizon robustness | **PASS** |
| Chronological subperiod stability | **PASS** |
| Asset-group dependence | **FAIL** |
| Symbol-identity placebo | **PASS** |
| **Overall robustness** | **FAIL** |

The failure is specific rather than general: predictive information remains strong across medium horizons, time blocks and a symbol-identity placebo, but aggregate rank IC falls materially when the US risk-asset block is removed.

## A. Horizon robustness

| Horizon | Mean IC | HAC t | HAC p | BH q (alternate horizons) | Positive years |
|---:|---:|---:|---:|---:|---:|
| 1 session | 0.00413 | 0.831 | 0.406 | 0.406 | 53.8% |
| 5 sessions | **0.02701** | **3.922** | **0.0000878** | — | **92.3%** |
| 10 sessions | **0.02366** | **2.645** | **0.00816** | **0.0202** | **84.6%** |
| 20 sessions | **0.03166** | **2.471** | **0.0135** | **0.0202** | **76.9%** |

The pre-registered horizon rule passes: all three alternate horizons have positive mean IC and the adjacent 10-session horizon survives BH-FDR.

The economic interpretation is more specific than simple decay. The signal is weak at one session but remains strong over 5–20 sessions. It therefore appears to be a medium-horizon cross-sectional effect rather than an immediate next-day ranking effect.

Horizon-specific pre-hold-out embargoes were 2, 6, 11 and 21 eligible decision dates for horizons 1, 5, 10 and 20 respectively.

## B. Chronological stability

The five-session out-of-sample IC series was divided into three consecutive equal blocks of 1,029 dates.

| Block | Dates | Mean IC | HAC t | HAC p |
|---:|---|---:|---:|---:|
| 1 | 2013-04-11 to 2017-05-10 | **0.03279** | 2.810 | **0.00496** |
| 2 | 2017-05-11 to 2021-06-11 | **0.02688** | 2.140 | **0.0324** |
| 3 | 2021-06-14 to 2025-07-18 | **0.02136** | 1.860 | 0.0629 |

All three block means are positive and two are significant at 5%, so the pre-registered subperiod rule passes.

The decreasing point estimates should still be treated seriously. Mean IC falls from 0.0328 to 0.0269 to 0.0214. The latest block remains positive but is only borderline under HAC inference. This is compatible with a persistent but weakening effect.

## C. Asset-group dependence

### Within-group IC

| Group | Assets | Mean IC | HAC p |
|---|---:|---:|---:|
| US risk assets | 16 | **0.02457** | **0.00227** |
| International equity | 5 | 0.00675 | 0.648 |
| Fixed income | 5 | **0.04459** | **0.00413** |
| Commodities | 4 | 0.00943 | 0.534 |

All four broad groups have positive mean within-group IC, satisfying the first part of the breadth rule.

### Leave-one-group-out IC

| Excluded group | Remaining assets | Mean IC | Retention vs full | HAC p | Rule |
|---|---:|---:|---:|---:|---|
| **US risk assets** | 14 | **0.01183** | **43.8%** | **0.179** | **FAIL** |
| International equity | 25 | 0.02591 | 95.9% | 0.000647 | Pass |
| Fixed income | 25 | 0.02756 | 102.0% | 0.0000570 | Pass |
| Commodities | 26 | 0.03015 | 111.6% | 0.0000377 | Pass |

This is the sole formal failure in EXP-006.

The result should not be simplified to “the signal exists only in US equities”: fixed-income within-group IC is actually larger than US-risk within-group IC and statistically significant. The precise statement is that the **aggregate 30-ETF ranking result depends materially on having the US risk-asset block present**. Without those 16 ETFs, the remaining-universe aggregate IC falls below the pre-registered 50% retention threshold and is no longer statistically significant.

This could reflect several mechanisms: the larger US block may provide most of the cross-sectional breadth; the model may exploit relative dispersion within US risk assets; or part of the full-universe IC may arise from interactions between US risk assets and other asset classes. EXP-006 does not distinguish these explanations.

## D. Symbol-identity placebo

The placebo preserved complete prediction time series and serial dependence but globally permuted which symbol each prediction path belonged to.

- permutations: **999**;
- fixed seed: **20261004**;
- observed mean IC: **0.02701**;
- placebo mean: **0.00010**;
- placebo standard deviation: **0.00654**;
- placebo 95th percentile: **0.01141**;
- empirical one-sided p-value: **0.001**.

The observed signal is far into the upper tail of the placebo distribution. Random symbol identity does not plausibly explain the development result under this test.

## Decision

EXP-006 does **not** receive an overall robustness pass because the asset-group-dependence rule fails.

The final 252-date hold-out remains locked.

At the same time, the experiment strengthens several parts of the research case:

- the five-day result reproduces exactly;
- the effect extends to 10- and 20-session horizons;
- all three chronological blocks have positive IC;
- the symbol-identity placebo is decisively rejected;
- US risk assets and fixed income both show significant within-group IC.

The next experiment should therefore investigate the source of the US-risk dependence, not search for better execution or new features. The key distinction to test is whether the model is exploiting **within-group relative ranking** or **between-group asset-class structure**.

A group-neutral target/model is the natural next falsification.
