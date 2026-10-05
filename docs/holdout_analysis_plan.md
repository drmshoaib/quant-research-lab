# Pre-registered Hold-out Analysis Plan — v0.2 `pruned8`

**Date registered:** 5 October 2026  
**Status:** registered; hold-out **not yet evaluated**  
**Hold-out:** `configs/holdout_dates.csv`, 252 eligible decision dates, 24 September 2025 to
24 September 2026, defined before any feature existed (`docs/research_protocol.md` §3).  
**Machine-readable copy:** `configs/holdout_analysis_plan.json` (the evaluation script checks
that this document's SHA-256 matches the hash recorded there, so the plan cannot be edited
silently after registration).

This plan closes the open item recorded in `docs/errata.md` (A5): the manifest fixed *which*
dates are held out but not *how* they would be analysed. Everything below is decided here,
before `scripts/evaluate_holdout.py` is allowed to run on the hold-out dates.

## 1. What is evaluated

The frozen development specification and nothing else (`configs/final_specification_v0.2.json`):
`pruned8` features; five-session full-universe-relative target; `HistGradientBoostingRegressor`
with the frozen hyperparameters **as frozen**, including scikit-learn's default early stopping
(`early_stopping="auto"`, `random_state=42`), because that is the model the development
evidence describes. The corrected `hist_gb_v03` variant of EXP-008 is reported as a secondary
row, never as the decision model.

## 2. Fitting scheme

**Fit once, score all.** One model is fitted on **all development data**: every eligible
decision date strictly before the six-date pre-hold-out embargo, with complete features and
targets (3,889 dates by the inference in the research note; the script records the actual
count). The fitted model scores all 252 hold-out dates. The walk-forward is **not** continued
into the hold-out, because later hold-out folds would then be trained on realised hold-out
outcomes and the 252 dates would stop being a single unseen block.

## 3. Primary statistic and test

- Primary statistic: the hold-out mean daily Spearman rank IC, $\overline{IC}_H$, over the
  252 dates (`metrics.rank_ic_by_date`, `min_assets = 8`).
- Primary test: **one-sided**, $\mathcal H_0\colon \mathbb E[IC_t] \le 0$ against
  $\mathbb E[IC_t] > 0$, at level **5%**, using the Newey–West standard error with
  **lag $L = 10 = 2h$** (`metrics.hac_mean_test`, normal reference distribution as in the
  development runs). The one-sided p-value is half the two-sided value when
  $\overline{IC}_H>0$ and $1 - \tfrac12 p_{\text{two-sided}}$ otherwise.
- Why lag 10 and not the registered development lag 4: `docs/errata.md` A2 and
  `docs/mathematical_guide/03-inference-and-robustness.md` §7 show that lag $h-1$ recovers only about two thirds of the long-run variance under
  overlapping targets. The development lag is kept **for comparison** in the sensitivity table
  (§5) but does not decide the outcome.

## 4. Decision table (binding)

Let $p_H$ be the one-sided lag-10 p-value. Let $\overline{IC}_D = 0.02701$ and
$se_D = 0.00689 \times 1.213 = 0.00836$ be the development mean and its lag-corrected
standard error, and $se_H$ the **realised** lag-10 hold-out standard error.

| Outcome | Condition | Statement that will be made |
|---|---|---|
| **Confirmed** | $\overline{IC}_H > 0$ and $p_H < 0.05$ | the ranking skill replicates on unseen data |
| **Consistent, inconclusive** | $\overline{IC}_H > 0$ and $p_H \ge 0.05$ | the hold-out agrees in sign but one year is too short to confirm; no claim of replication |
| **Not replicated** | $\overline{IC}_H \le 0$ and $Z \ge -1.645$ | no evidence of skill out of sample; the development claim is weakened |
| **Contradicted** | $Z < -1.645$, where $Z = (\overline{IC}_H - \overline{IC}_D)/\sqrt{se_D^2 + se_H^2}$ | the hold-out is significantly worse than the development estimate (one-sided 5%); the development result is to be treated as an artefact |

For orientation only (the rule uses the realised $se_H$): if the hold-out IC series is as
dispersed as the development one, $se_H \approx 0.00836\sqrt{3087/252} = 0.0292$ and the
"Contradicted" boundary is $\overline{IC}_H \approx 0.027 - 1.645 \times 0.0304 = -0.023$.
No row permits any change to the model, the features or the portfolio rule.

## 5. Secondary analyses (reported, no gates)

1. Lag-sensitivity table of $\overline{IC}_H$: $t$ and one-sided $p$ at $L \in \{0, 4, 8, 10, 20\}$
   (`metrics.hac_lag_sensitivity`).
2. The same primary statistic for `hist_gb_v03` (early stopping off), fitted once on the same
   development data.
3. Symbol-identity placebo and timing placebo on the hold-out predictions, 999 replicates each
   (`robustness.global_symbol_permutation_test`, `robustness.global_date_permutation_test`).
   With only 252 dates these are low-powered; they are reported, not gated.
4. Five-sleeve instant-execution portfolio on the hold-out dates (gross 1, cap 0.08, terminal
   liquidation costed) at 0 and 5 bps one way: annualised arithmetic return, Sharpe, turnover
   (`backtest.run_backtest`, `metrics.backtest_summary`). Secondary evidence, as in development.
5. Positive-IC fraction of hold-out dates and the hold-out IC standard deviation, for comparison
   with development (0.541 and 0.243 for the full-feature model in EXP-001).

## 6. Power statement (made in advance)

With $se_H \approx 0.0292$ the expected $t$ is $0.027/0.0292 = 0.92$ if the true IC equals the
development estimate, giving one-sided 5% power of about **24%** (30% with the uncorrected
$se_H = 0.0241$). "Consistent, inconclusive" is therefore the single most likely outcome
**even if the signal is real**, and will be reported as exactly that. The development estimate
is also the survivor of a (small, disclosed) selection process and is probably biased upwards.
To reach 80% power the true IC would need to be about $2.49 \times 0.0292 = 0.073$.

## 7. Procedure for the single evaluation

1. This document and `configs/holdout_analysis_plan.json` are committed; the JSON records the
   SHA-256 of this document.
2. `scripts/evaluate_holdout.py --dry-run` is run on development data (the last 252
   development dates as a pseudo-hold-out, with a six-date embargo before them) to check the
   code. Dry runs may be repeated; they never touch hold-out dates.
3. The real run requires **both** the flag `--unlock` **and** the environment variable
   `QRL_HOLDOUT_UNLOCK=I_UNDERSTAND_THIS_RUNS_ONCE`. Before computing anything it verifies:
   the data file's SHA-256 against `configs/data_snapshot.json`; the SHA-256 of
   `configs/holdout_dates.csv`, `data/universe_etf.csv`, `configs/final_specification_v0.2.json`
   and this document against the JSON; that `outputs/holdout/result.json` does not already
   exist; and, when `git` is available, that the working tree is clean.
4. The script writes `outputs/holdout/result.json` (decision row, all statistics, environment
   versions, hashes) and the prediction and IC files. The output is saved unedited.
5. The research note gains a hold-out section quoting the result verbatim, and
   `configs/final_specification_v0.2.json` is updated to `"evaluated": true` with the result
   file's hash. There is no second run.

## 8. What this plan does not do

It does not re-open any development choice, tune anything on the hold-out, or run EXP-006/007
style robustness on the hold-out beyond the two placebos listed above. If the result is
"Contradicted" or "Not replicated", the next research phase starts from a new protocol, not
from this hold-out.
