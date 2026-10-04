# EXP-007 Results — Group-Neutral Target and Within-Group Alpha

**Run date:** 4 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Successful workflow run:** `37195612927`

## Executive result

EXP-007 asked whether the pruned8 HistGradientBoosting signal survives when broad asset-class moves are removed from the training target and every broad asset group receives equal weight in evaluation.

Four of five pre-registered acceptance gates passed.

| Gate | Result |
|---|---|
| Four-group composite positive, HAC p < 0.05 | **PASS** |
| At least 3/4 broad groups positive | **PASS** |
| Non-US composite positive, HAC p < 0.05 | **FAIL** |
| At least 80% within-group IC retained | **PASS** |
| Chronological-thirds rule | **PASS** |
| **Overall EXP-007** | **FAIL** |

The only failing gate is extremely close numerically but remains a failure: the non-US composite HAC p-value is **0.0501247**, while the registered rule required **p < 0.05**.

## Control versus group-neutral model

Both models use identical pruned8 features, HistGradientBoosting hyperparameters, folds, dates, purge and embargo. Only the training target changes.

| Metric | Original-target control | Group-neutral target |
|---|---:|---:|
| Equal-weight four-group mean IC | 0.02092 | **0.01806** |
| Four-group HAC p | 0.00443 | **0.00981** |
| Equal-weight non-US mean IC | 0.01979 | **0.01725** |
| Non-US HAC p | 0.0294 | **0.05012** |
| Four-group IC retention | — | **86.32%** |

The group-neutral model therefore retains most of the within-group ranking information after between-group target means are removed.

A key technical point is that subtracting a same-date group mean does not change the ordering of realised returns inside that group. The change in within-group IC is therefore driven by **model retraining**, not a mechanical change in within-group target ranks.

## Group-level results

| Broad group | Mean IC | HAC p |
|---|---:|---:|
| US risk assets | **0.01700** | **0.0389** |
| International equity | 0.00421 | 0.769 |
| Fixed income | **0.03948** | **0.00903** |
| Commodities | 0.01334 | 0.393 |

All four group means are positive.

US risk assets remain significant, but fixed income is stronger in mean IC. International equity and commodities are directionally positive but noisy. This is more nuanced than a purely US-equity signal.

## Chronological stability of group-neutral composite

| Block | Dates | Mean IC | HAC p |
|---:|---|---:|---:|
| 1 | 2013-04-11 to 2017-05-10 | **0.01854** | 0.0871 |
| 2 | 2017-05-11 to 2021-06-11 | **0.01102** | 0.402 |
| 3 | 2021-06-14 to 2025-07-18 | **0.02462** | **0.0437** |

All three chronological blocks are positive and two satisfy the pre-registered p < 0.10 criterion.

Unlike the raw-target aggregate IC in EXP-006, the group-neutral composite does **not** show a monotonic decline. The latest third is the strongest of the latter two blocks and is significant at 5%.

## Interpretation

EXP-006 showed that removing the entire US-risk block reduced the aggregate 30-ETF IC below the registered robustness threshold.

EXP-007 demonstrates that this dependence is not adequately explained by broad asset-class rotation alone. Once each broad group's target mean is removed:

- the equal-weight four-group signal remains statistically significant;
- 86.3% of the original model's within-group composite IC is retained;
- all four broad groups remain positive;
- fixed income retains a strong significant IC;
- the latest chronological third remains positive and significant.

The unresolved weakness is the equal-weight **non-US** composite. Its mean IC is economically positive at 0.01725, but its HAC p-value of 0.0501247 narrowly misses the registered 5% gate.

That near miss is reported exactly as observed. It is not rounded to 0.05 and does not justify changing the threshold.

## Decision

EXP-007 does **not** receive a formal pass.

At the same time, the evidence now supports a narrower and defensible development conclusion:

> The pruned8 nonlinear model contains statistically significant within-broad-group relative-ranking information that survives removal of broad asset-class target means, but evidence for the equal-weight non-US component is borderline under the pre-registered 5% criterion.

The final 252-date hold-out remains locked.

Further experimentation on group definitions, p-value thresholds or nearby model specifications is not recommended. Seven sequential development experiments are already sufficient to document both the positive evidence and the limitations. The next defensible step is to freeze the development conclusion and prepare the final specification manifest/research note before deciding whether to perform the one-time hold-out evaluation.
