# Errata and Known Issues — v0.2 development programme

**Date:** 4 October 2026  
**Status:** remediation complete for fixable items; historical v0.2 numbers remain frozen; hold-out remains locked

This file records defects, imprecisions and limitations found during an independent
review of the frozen v0.2 programme (October 2026). It separates issues that *would change reported numbers* from those that do
not. Nothing in the frozen manifest (`configs/final_specification_v0.2.json`) has been
altered; items in Section A can only be addressed by a new registered experiment.

## Resolution summary

| Item | Resolution |
|---|---|
| A1 early stopping | **Tested/resolved prospectively.** EXP-008 shows the signal remains positive and lag-10 significant with early stopping off and with time-ordered early stopping; model complexity is sensitive to the stopping rule. |
| A2 HAC lag | **Resolved for the primary five-session claim.** Control lag-10 p = 0.000254 and lag-20 p = 0.000349; no-early-stopping lag-10 p = 0.000984. Alternate-horizon dependence remains a disclosed limitation. |
| A3 Ridge scaling | **Resolved.** Ridge with alpha = 0.1 x n_train remains null (mean IC 0.00143, lag-10 p = 0.863). |
| A4 pruned8 selection reuse | **Historical limitation; cannot be undone.** Explicitly disclosed and protected by the untouched hold-out. |
| A5 hold-out analysis plan | **Closed.** Pre-registered, hash-pinned plan and locked evaluation script exist. |
| A6 statistical caveats / timing placebo | **Partly resolved, partly retained as limitations.** Timing placebo implemented; EXP-008 G4 fails for corrected variants, so timing-skill language is downgraded. |
| Section B code defects | **Corrected with tests; frozen balanced-panel results unchanged.** |
| Section C safe code fragilities | **Fixable items corrected.** Remaining entries are historical/protocol limitations or intentionally out-of-scope design notes. |

EXP-008 results: `docs/exp008_results.md`, workflow run `38923117741`.

## A. Issues that affect reported numbers (not corrected; disclosed)

### A1. Undocumented early stopping in the gradient-boosting model
`HistGradientBoostingRegressor` was constructed with scikit-learn's default
`early_stopping="auto"`, which turns early stopping **on** whenever the training set has
more than 10,000 rows. Every development fold does (≥ 756 dates × 30 symbols = 22,680
rows). A random 10% of the training rows is held out and boosting stops after 10 rounds
without validation improvement, so the frozen `max_iter=250` was a ceiling, not the number
of trees fitted; `random_state` affects the result; and the model was fitted on 90% of each
training block. None of this was stated in the protocol, the research note or the manifest.
**Resolution:** the frozen constructor now states `early_stopping="auto"` explicitly.
EXP-008 re-ran development with early stopping off and with a purged time-ordered validation
block under a pinned environment. Mean IC is 0.02322 (lag-10 p = 0.000984) with early
stopping off and 0.01830 (p = 0.0231) with time-ordered stopping, versus 0.02701 for the
frozen control. Random-row stopping used a median 110 trees; time-ordered stopping selected
a median 12. Early stopping therefore affects model complexity and magnitude, but does not
explain the existence or sign of the development IC.

### A2. Registered HAC lag understates the standard error
The protocol registers Newey–West lag `L = h − 1 = 4` for the five-session horizon. Under
the idealised overlap model (five-session outcome = sum of five independent daily pieces)
the IC series has autocorrelations `(h−k)/h`, the true long-run variance is `5γ₀`, and the
Bartlett estimator at `L = 4` recovers only `3.4γ₀`. The standard error is therefore
understated by about 21% in that model and a nominal 5% test rejects about 10% of the time.
Applied heuristically, the headline `t = 3.922` becomes about `3.2` (`p ≈ 0.001`); the
10- and 20-session horizon p-values (0.0082, 0.0135) would rise to roughly 0.03–0.04; and
the EXP-007 near miss (`p = 0.0501`) would be a clear miss. The registered results are
reported unchanged. **Resolution:** EXP-008 reports lags 0, 4, 8, 10 and 20 (plus automatic lag 8). For the
frozen five-session control, lag-10 p = 0.000254 and lag-20 p = 0.000349. For the
no-early-stopping model, lag-10 p = 0.000984 and lag-20 p = 0.00140. The primary
five-session development inference is therefore robust to the safer lag choice. The
hold-out plan uses lag 10 as its primary inference lag. The earlier 10- and 20-session
horizon checks remain correlated sensitivity analyses rather than independent evidence.

### A3. The Ridge "baseline" is effectively OLS
scikit-learn's Ridge objective is not divided by the sample size, so `alpha = 10` on
22,680–113,400 standardised rows shrinks coefficients by well under 1% unless the feature
correlation matrix has an eigenvalue of order 10⁻⁴. The EXP-001 comparison is therefore
"OLS versus boosting", which does not change its conclusion but should be described as such.
**Resolution:** EXP-008 adds `ridge_v03` with `alpha = 0.1 · n_train`. It produces
mean IC 0.001434 with lag-10 p = 0.863, so stronger regularisation does not reveal a
linear signal and the substantive linear-versus-nonlinear conclusion is unchanged.

### A4. pruned8 was selected after its result had been seen
EXP-003's `pruned8` is identical to EXP-002's "drop `mom_5`" ablation (same data, folds and
seed), whose IC (0.02624 + 0.00077 = 0.02701) was therefore already known when EXP-003 was
registered. The selection step is mitigated by being a single, pre-declared rule and by the
locked hold-out, but it is a selection step and is now stated as one.

### A5. The hold-out analysis plan was incomplete (closed 5 October 2026)
The manifest fixed the hold-out dates but not: whether the model is refitted once on all
development data or walk-forward continues; the test's sidedness and level; what counts as
confirmation or failure. A 252-date hold-out has only about 24–30% power to detect
`IC = 0.027` at the 5% level (one-sided). **Closed:** `docs/holdout_analysis_plan.md`
(hash-pinned in `configs/holdout_analysis_plan.json`) now fixes all of these, and
`scripts/evaluate_holdout.py` enforces them, is locked by default, dry-runs on development
data and refuses a second run. The hold-out itself remains unevaluated.

### A6. Smaller statistical caveats
- The EXP-002 ablation tests share the full-model IC series; Benjamini–Hochberg relies on
  positive dependence there (not proved). Under the arbitrary-dependence correction neither
  retained contributor would survive.
- The 10- and 20-session horizon targets contain the 5-session target (correlations about
  0.71 and 0.50), so horizon robustness is not independent evidence.
- The symbol-identity permutation tests "no symbol-specific information in the scores"; a
  static asset-class tilt would also reject that null. It does not establish timing skill.
  **Addressed with an informative failure:** `robustness.global_date_permutation_test`
  was run in EXP-008. Timing-placebo p = 0.034 for the frozen control but 0.082 for
  no-early-stopping and 0.109 for time-ordered stopping. The pre-registered timing gate
  therefore fails, so robust date-specific timing skill is **not** claimed; a persistent
  cross-sectional tilt remains a viable explanation for part of the signal.
- The subperiod rule "two of three blocks with p < 0.05" is passed by a perfectly stable
  signal of the observed strength only about two thirds of the time; block 3's p = 0.063
  is consistent with no decay. Under the lag correction of A2 the block p-values become
  roughly 0.021, 0.078 and 0.125, so the registered block rule itself would not have passed.
- In a synthetic check (persistent features, overlapping targets) the random 10% early-
  stopping split of A1 stopped later than a time-ordered split in five of six seeds
  (10–158 trees against 11–34), consistent with the suspicion that the random split's
  optimistic validation loss lengthens training. Untested on the real panel.

## B. Code defects corrected (no effect on frozen results)

- **`targets.py` shifted by rows, not sessions** (fixed 5 October 2026). `forward_open_return`
  and `next_open_to_open_simple_return` shifted each symbol's own rows, so a missing bar would
  have been skipped silently. Both now reindex every symbol to the union session calendar
  before shifting (a missing entry or exit bar gives NaN); the simple return is `expm1` of the
  one-session log return. The frozen panel is balanced (126,390 = 30 × 4,213 rows), so the
  old and new functions agree on it (pinned by a test) and no reported number changes.
- **`portfolio.rank_weights` could exceed the per-name cap when scores tied** (re-demeaning
  after an asymmetric clip). Fixed by scaling the heavier side down to the lighter one after
  clipping; identical output for distinct scores (verified numerically). Ties among
  boosted-tree scores across 30 ETFs are essentially impossible, so no result changes.
- **`tests/test_features.py` was too weak**: it multiplied future close/high/low by one
  common factor and never touched open or volume, so scale-invariant leaks, open/volume
  leaks and cross-sectionally demeaned leaks passed. Replaced by independent random factors
  on all five fields at three cut-offs, plus a test that the check catches a planted leak.
  `build_features` passes the stronger test.
- **`pipeline.walk_forward_predictions` hard-coded `purge = horizon + 1`**; it now takes
  `purge_days` (default unchanged) so a configuration file can be the single source of truth.
- **`robustness.prepare_horizon_research_frame`** now rejects a manifest that starts after
  the horizon's last eligible date, and documents why the h=5 manifest cannot be required to
  equal the final eligible block of another horizon.
- Literal `"\n"` printed by `run_exp006.py`/`run_exp007.py`; unused imports/variables in
  `tests/test_group_neutral.py`, `tests/test_robustness.py`, `scripts/run_exp004.py`.

## C. Former fragilities and remaining historical limitations

- **Fixed:** `signals.causal_rank_ewma` now subtracts each date's actual rank mean, so
  smoothed rank inputs are exactly cross-sectionally centred. A regression test verifies zero mean.
- **Fixed:** `group_neutral.composite_ic_diagnostics` now requires all intended groups
  on a date before forming an equal-weight composite, preventing silent time-varying reweighting.
  The frozen balanced panel is unchanged.
- `l2_regularization = 1.0` shrinks leaf values by at most about 2.4% with
  `min_samples_leaf = 40`.
- **Fixed:** symbol/date permutation preparation now skips dates with degenerate all-tied
  rank vectors and raises only if every complete date is degenerate. Covered by a regression test.
- **Fixed:** `metrics.backtest_summary` now exposes the explicit
  `ann_arithmetic_return` key while retaining `ann_return` as a backward-compatible alias.
- **Fixed:** the unreachable `len(train) >= min_train_days` guard was removed from
  `PurgedWalkForward.split`.
- **Historical protocol limitation:** `scripts/run_baseline.py` encoded the primary Ridge
  gates but the original comparator phrase "reasonably persistent across folds" was not
  numerically defined before results. It cannot be retroactively repaired without inventing
  a rule after seeing data. EXP-008 uses explicit quantitative gates instead.
- **Fixed:** the unused `optimise_weights` helper now represents gross exposure and
  turnover with exact L1 auxiliary variables. Its numerical-failure fallback keeps the
  previous portfolio when that portfolio is feasible. This helper remains outside all frozen
  v0.2 experiments.

## D. Documentation corrected in this revision

- `docs/research_log.md`: EXP-001, EXP-004 and EXP-005 entries had been left at
  "Result: Pending / Decision: Pending" although their results files existed; back-filled
  and marked as such.
- `docs/mathematical_guide/02` §11: exact purge derivation (`p ≥ h`; the project's `h+1`
  is one session of margin).
- `docs/mathematical_guide/03`: Spearman is invariant to strictly *increasing* (not
  "monotone") transforms; BH rejects the *k smallest* p-values; dependence caveat for BH;
  the `+1` permutation p-value is exactly valid, not cosmetic; HAC-lag caveat (A2).
- `docs/mathematical_guide/04` §18: the break-even cost is exact under arithmetic
  annualisation.
