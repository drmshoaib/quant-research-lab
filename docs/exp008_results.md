# EXP-008 Results — Methods Re-run

**Run date:** 16 October 2026  
**Status:** Complete  
**Hold-out:** Locked and untouched  
**Workflow run:** `38923117741`  
**Artifact:** `12055513405`  
**Artifact digest:** `sha256:9a57d77dd6313cf713a738dba8135af879d15d3a284c569600629d71f7c05452`

## Purpose

EXP-008 was registered to address four methodological issues identified after the v0.2 development programme:

1. undocumented random-row early stopping in `HistGradientBoostingRegressor`;
2. an overly short primary HAC lag for overlapping five-session targets;
3. an effectively unregularised Ridge baseline;
4. a symbol-identity placebo that could not distinguish timing skill from a static cross-sectional tilt.

This is a methods sensitivity experiment, not a new model-selection exercise. The final 252-date hold-out was not used.

## Registered gates

| Gate | Rule | Result |
|---|---|---|
| G1 — reproduction | frozen control mean IC within 5e-5 of 0.02701 | **PASS** |
| G2 — inference | no-early-stopping pruned8 mean IC > 0 and lag-10 HAC p < 0.05 | **PASS** |
| G3 — early stopping | both corrected boosting variants retain 50–150% of control IC and record n_iter | **PASS** |
| G4 — timing | timing-placebo p <= 0.05 for control and no-early-stopping model | **FAIL** |

Overall: **three of four gates pass**. The unresolved issue is timing evidence.

## Environment

- Python: **3.11.17**
- NumPy: **2.4.6**
- pandas: **3.0.5**
- scikit-learn: **1.9.1**
- statsmodels: **0.15.0**

The original invalid Python-3.11 pins were corrected before this successful run. The frozen market-data CSV was retrieved from the preserved 90-day copy and verified against the original SHA-256.

## Boosting variants

| Variant | Mean IC | Lag-4 p | Lag-10 p | Median fold IC | Positive years | Median trees | Timing placebo p |
|---|---:|---:|---:|---:|---:|---:|---:|
| v0.2 control, random-row early stopping | **0.02701** | 8.78e-5 | **0.000254** | 0.02766 | 92.3% | 110 | **0.034** |
| v0.3, early stopping off | **0.02322** | 0.000372 | **0.000984** | 0.02795 | 92.3% | 250 | 0.082 |
| v0.3, time-ordered early stopping | **0.01830** | 0.0121 | **0.0231** | 0.00998 | 69.2% | 12 | 0.109 |

### Interpretation

The original result is not an artefact of the registered lag-4 standard error. The control remains strongly significant at lag 10 and even lag 20.

The nonlinear signal also survives removing early stopping entirely: mean IC falls from 0.02701 to 0.02322 but remains statistically significant at lag 10 with p = 0.000984.

The time-ordered early-stopping variant is weaker, but still positive and significant at lag 10. Its much smaller median tree count (12 versus 110 for random-row early stopping) confirms that the frozen random validation split materially affected model complexity.

Therefore early stopping affects **signal magnitude and tree count**, but it does not explain the existence of the development IC.

## HAC lag sensitivity

For the frozen control:

| Lag | SE | t | p |
|---:|---:|---:|---:|
| 0 | 0.00437 | 6.178 | 6.49e-10 |
| 4 | 0.00689 | 3.922 | 8.78e-5 |
| 8 | 0.00732 | 3.692 | 0.000222 |
| 10 | 0.00738 | 3.659 | **0.000254** |
| 20 | 0.00755 | 3.576 | **0.000349** |

The headline five-session result is therefore robust to a substantially longer HAC lag, even though lag 4 was too optimistic as a generic default.

For the no-early-stopping model, lag-10 p = **0.000984** and lag-20 p = **0.00140**.

## Ridge scaling

| Ridge variant | Mean IC | Lag-10 p |
|---|---:|---:|
| v0.2 alpha = 10 | 0.00371 | 0.681 |
| v0.3 alpha = 0.1 x n_train | 0.00143 | 0.863 |

The stronger, sample-size-scaled Ridge penalty does not reveal a hidden linear signal. If anything, the Ridge result becomes weaker. The practical interpretation of EXP-001 is therefore unchanged: the useful development signal is nonlinear.

## Placebo results

### Symbol-identity placebo

- v0.2 control: **p = 0.001**
- no early stopping: **p = 0.001**
- time-ordered early stopping: **p = 0.003**

These continue to reject arbitrary reassignment of score paths to symbols.

### Timing placebo

- v0.2 control: **p = 0.034**
- no early stopping: **p = 0.082**
- time-ordered early stopping: **p = 0.109**

The pre-registered G4 timing gate therefore fails.

This matters. The symbol placebo establishes symbol-specific cross-sectional information, but a static or slowly varying cross-sectional tilt can also pass that test. The new timing placebo is designed so that a static tilt is invariant under the null. Only the frozen control rejects the timing placebo at 5%; the two corrected early-stopping variants do not.

The appropriate conclusion is therefore:

> The development sample contains statistically significant nonlinear cross-sectional ranking structure, robust to safer HAC inference and explicit early-stopping choices, but evidence that this structure represents genuine date-specific timing skill rather than a persistent cross-sectional tilt is model-dependent and not robust across corrected variants.

## Decision

EXP-008 does not alter the frozen v0.2 numbers or model choice.

However, the research note should be more cautious about **timing skill**. It may state that cross-sectional predictive structure is statistically supported, while recording that the corrected no-early-stopping and time-ordered variants fail the pre-registered timing placebo.

The hold-out remains locked. The pre-registered hold-out plan remains the binding procedure for any eventual one-time evaluation.
