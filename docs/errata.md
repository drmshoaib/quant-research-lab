# Errata and Known Issues — v0.2 development programme

**Date:** 4 October 2026  
**Status:** development specification remains frozen; hold-out remains locked

This file records defects, imprecisions and limitations found during an independent
review of the frozen v0.2 programme (October 2026). It separates issues that *would change reported numbers* from those that do
not. Nothing in the frozen manifest (`configs/final_specification_v0.2.json`) has been
altered; items in Section A can only be addressed by a new registered experiment.

## A. Issues that affect reported numbers (not corrected; disclosed)

### A1. Undocumented early stopping in the gradient-boosting model
`HistGradientBoostingRegressor` was constructed with scikit-learn's default
`early_stopping="auto"`, which turns early stopping **on** whenever the training set has
more than 10,000 rows. Every development fold does (≥ 756 dates × 30 symbols = 22,680
rows). A random 10% of the training rows is held out and boosting stops after 10 rounds
without validation improvement, so the frozen `max_iter=250` was a ceiling, not the number
of trees fitted; `random_state` affects the result; and the model was fitted on 90% of each
training block. None of this was stated in the protocol, the research note or the manifest.
*Fix for a future phase:* set `early_stopping` explicitly, record `n_iter_` per fold and pin
the scikit-learn version. The constructor now writes the value out explicitly, with a
comment, so the behaviour is visible without changing it.

### A2. Registered HAC lag understates the standard error
The protocol registers Newey–West lag `L = h − 1 = 4` for the five-session horizon. Under
the idealised overlap model (five-session outcome = sum of five independent daily pieces)
the IC series has autocorrelations `(h−k)/h`, the true long-run variance is `5γ₀`, and the
Bartlett estimator at `L = 4` recovers only `3.4γ₀`. The standard error is therefore
understated by about 21% in that model and a nominal 5% test rejects about 10% of the time.
Applied heuristically, the headline `t = 3.922` becomes about `3.2` (`p ≈ 0.001`); the
10- and 20-session horizon p-values (0.0082, 0.0135) would rise to roughly 0.03–0.04; and
the EXP-007 near miss (`p = 0.0501`) would be a clear miss. The registered results are
reported unchanged. *Fix:* a lag-sensitivity table (e.g. `L ∈ {4, 8, 10, 20}`) or a
data-driven lag in any future phase; see `docs/mathematical_guide/03` §7.

### A3. The Ridge "baseline" is effectively OLS
scikit-learn's Ridge objective is not divided by the sample size, so `alpha = 10` on
22,680–113,400 standardised rows shrinks coefficients by well under 1% unless the feature
correlation matrix has an eigenvalue of order 10⁻⁴. The EXP-001 comparison is therefore
"OLS versus boosting", which does not change its conclusion but should be described as such.

### A4. pruned8 was selected after its result had been seen
EXP-003's `pruned8` is identical to EXP-002's "drop `mom_5`" ablation (same data, folds and
seed), whose IC (0.02624 + 0.00077 = 0.02701) was therefore already known when EXP-003 was
registered. The selection step is mitigated by being a single, pre-declared rule and by the
locked hold-out, but it is a selection step and is now stated as one.

### A5. The hold-out analysis plan is incomplete
The manifest fixes the hold-out dates but not: whether the model is refitted once on all
development data or walk-forward continues; the test's sidedness and level; what counts as
confirmation or failure. A 252-date hold-out has only about 30% power to detect `IC = 0.027`
at the 5% level (one-sided). *Fix:* pre-register the hold-out analysis before unlocking.

### A6. Smaller statistical caveats
- The EXP-002 ablation tests share the full-model IC series; Benjamini–Hochberg relies on
  positive dependence there (not proved). Under the arbitrary-dependence correction neither
  retained contributor would survive.
- The 10- and 20-session horizon targets contain the 5-session target (correlations about
  0.71 and 0.50), so horizon robustness is not independent evidence.
- The symbol-identity permutation tests "no symbol-specific information in the scores"; a
  static asset-class tilt would also reject that null. It does not establish timing skill.
- The subperiod rule "two of three blocks with p < 0.05" is passed by a perfectly stable
  signal of the observed strength only about two thirds of the time; block 3's p = 0.063
  is consistent with no decay. Under the lag correction of A2 the block p-values become
  roughly 0.021, 0.078 and 0.125, so the registered block rule itself would not have passed.
- In a synthetic check (persistent features, overlapping targets) the random 10% early-
  stopping split of A1 stopped later than a time-ordered split in five of six seeds
  (10–158 trees against 11–34), consistent with the suspicion that the random split's
  optimistic validation loss lengthens training. Untested on the real panel.

## B. Code defects corrected (no effect on frozen results)

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

## C. Known fragilities left unchanged

- **`targets.py` shifts by rows, not sessions.** `forward_open_return` and
  `next_open_to_open_simple_return` use `shift` within each symbol, which silently jumps over
  a missing bar. The frozen panel is balanced (126,390 = 30 × 4,213 rows), so all results are
  correct. A calendar-robust version (reindex each symbol to the union of dates before
  shifting) was written and tested during the review; it was not merged into `src/` in
  this revision.
- `signals.causal_rank_ewma` "centred" ranks have mean `1/(2N_t)`, not 0; harmless because
  `rank_weights` re-ranks and demeans.
- `group_neutral.composite_ic_diagnostics` averages over whichever groups are present on a
  date (`skipna=True`), silently re-weighting on dates with a missing group; harmless on the
  balanced panel.
- `l2_regularization = 1.0` shrinks leaf values by at most about 2.4% with
  `min_samples_leaf = 40`.
- `global_symbol_permutation_test` raises on a date whose rank vector has zero norm (all
  scores tied) instead of skipping that date; impossible with boosted-tree scores on 30 ETFs.
- `metrics.backtest_summary` reports `ann_return` = 252 × mean daily net return (an
  arithmetic annualisation) without saying so in its key name; documents call it
  "annualised (arithmetic) return".
- `PurgedWalkForward.split` line 35 (`len(train) >= min_train_days`) can never be false;
  harmless dead code.
- `scripts/run_baseline.py` codes the EXP-001 gates only for the Ridge model; the comparator's
  "reasonably persistent across folds" rule was never quantified in code.
- `optimise_weights` (unused by any experiment) smooths `|x|` as `sqrt(x² + ε)`, making the
  gross constraint slightly conservative and removing exact sparsity; its failure fallback
  ignores the previous portfolio.

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
