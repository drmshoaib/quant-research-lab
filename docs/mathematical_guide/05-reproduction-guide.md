# Part 5 — Reproducing the Research in Python

This part turns the mathematics into an executable workflow.

The objective is not merely to obtain similar-looking numbers. A valid reproduction must preserve the timing, data snapshot, hold-out, model and statistical protocol.

## 1. Repository structure

The most important directories are:

| Path | Purpose |
|---|---|
| [src/quantlab](../../src/quantlab) | reusable research library |
| [scripts](../../scripts) | experiment entry points |
| [configs](../../configs) | frozen settings, hold-out and snapshot metadata |
| [data](../../data) | ETF universe definition |
| [docs](../../docs) | protocol, results and research notes |
| [tests](../../tests) | mathematical and implementation checks |
| [.github/workflows](../../.github/workflows) | reproducible GitHub Actions runs |

## 2. Create a Python environment

From the repository root:

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,data]'
~~~

On Windows PowerShell the activation command is different, but the package installation is the same.

The editable installation means changes in src/quantlab are immediately visible to the scripts.

## 3. Run the test suite first

~~~bash
pytest
~~~

A research result should not be reproduced from code whose invariants are failing.

Important test groups include:

- [test_features.py](../../tests/test_features.py): future data must not change past features;
- [test_targets.py](../../tests/test_targets.py): next-open timing and arithmetic portfolio returns;
- [test_splits.py](../../tests/test_splits.py): purging and date manifests;
- [test_pipeline.py](../../tests/test_pipeline.py): hold-out locking and embargo behaviour;
- [test_backtest.py](../../tests/test_backtest.py): staggered sleeves, costs, liquidation and compounding;
- [test_portfolio.py](../../tests/test_portfolio.py): neutrality, gross limits and optimisation;
- [test_robustness.py](../../tests/test_robustness.py): permutation and robustness machinery;
- [test_group_neutral.py](../../tests/test_group_neutral.py): group-neutral calculations.

These tests are part of the mathematical specification, not just software housekeeping.

## 4. Frozen configuration

The main numerical settings live in [configs/baseline.json](../../configs/baseline.json).

Key values are:

\[
h=5,
\quad
minAssets=8,
\quad
minTrain=756,
\quad
test=63,
\quad
step=63,
\]

\[
holdout=252,
\quad
purge=6,
\quad
cost=5\text{ bps},
\quad
gross=1,
\quad
max|w_i|=0.08.
\]

The final frozen specification is in [configs/final_specification_v0.2.json](../../configs/final_specification_v0.2.json).

## 5. Frozen universe

The ETF list and taxonomy are in [data/universe_etf.csv](../../data/universe_etf.csv).

The 30 symbols span:

- broad US equities;
- US sectors;
- international equity;
- government bonds;
- corporate credit;
- commodities;
- real estate;
- biotechnology;
- retail.

Do not silently add or remove symbols if you want to reproduce the official v0.2 experiment.

## 6. Frozen market data

The official data snapshot is described in [configs/data_snapshot.json](../../configs/data_snapshot.json).

The large market-data CSV is not committed as an ordinary repository file. It was frozen as a workflow artifact and verified with a SHA-256 checksum.

Official snapshot checksum:

\[
\text{ec782ac2cd812a6d81abcbf9cbcdecdd448ab8822b585fbd07c3a74968a3bbd3}.
\]

The original freeze workflow is [.github/workflows/freeze-holdout.yml](../../.github/workflows/freeze-holdout.yml).

To reproduce the **official** numbers, use the byte-identical frozen snapshot rather than redownloading Yahoo data later. A fresh Yahoo download may be revised by the provider.

## 7. Why checksums matter

A cryptographic hash is a deterministic fingerprint of a file.

If

\[
SHA256(file_A)=SHA256(file_B),
\]

then, for practical reproducibility purposes, the files can be treated as byte-identical.

If the checksum differs, the dataset is not the same research input.

This is important because financial vendors can revise historical data.

## 8. Hold-out manifest

The hold-out dates are stored explicitly in [configs/holdout_dates.csv](../../configs/holdout_dates.csv).

The manifest contains 252 ordered dates.

The development scripts verify that the manifest is the final eligible block of the frozen calendar.

The hold-out should not be regenerated during reproduction unless you are reproducing the **freeze procedure itself**.

## 9. Reproducing the freeze procedure separately

The script is [scripts/freeze_holdout.py](../../scripts/freeze_holdout.py).

Conceptually it performs:

1. load/download adjusted panel;
2. compute eligible target dates;
3. split off the last 252;
4. save them as a manifest.

A generic command is:

~~~bash
python scripts/freeze_holdout.py --data path/to/adjusted_ohlcv.csv
~~~

Do not overwrite the committed v0.2 manifest when reproducing the existing research.

## 10. Baseline experiment flow

The baseline runner is [scripts/run_baseline.py](../../scripts/run_baseline.py).

With the frozen CSV available locally:

~~~bash
python scripts/run_baseline.py \
  --data path/to/frozen_market_data.csv \
  --output-dir outputs/reproduction/exp001
~~~

The script performs roughly:

~~~text
load config
load hold-out manifest
load frozen OHLCV panel
prepare research frame
compute simple realised portfolio returns

for each model:
    create walk-forward predictions
    calculate daily rank IC
    calculate HAC diagnostics
    convert scores to cohort weights
    combine five staggered sleeves
    append terminal liquidation
    backtest at several transaction costs
    save predictions, IC and summaries
~~~

## 11. Library call chain

For the main five-session experiment, the important function chain is:

~~~text
load_panel_csv
    |
prepare_research_frame
    |-- build_features
    |-- forward_relative_return
    |-- eligible_decision_dates
    |
walk_forward_predictions
    |-- PurgedWalkForward
    |-- make_model
    |
rank_ic_by_date
rank_ic_diagnostics
    |-- hac_mean_test
    |
weights_from_predictions
    |-- rank_weights
    |
staggered_weights
append_liquidation_row
run_backtest
backtest_summary
~~~

Following this chain is one of the best ways to understand the codebase.

## 12. EXP-001: baseline linear versus nonlinear model

Runner: [scripts/run_baseline.py](../../scripts/run_baseline.py).

Research question:

> does a simple Ridge model produce a defensible cross-sectional signal, and how does a fixed nonlinear comparator behave?

The Ridge hypothesis failed. HistGradientBoosting became the development candidate.

Outputs include:

- prediction CSV;
- daily rank IC CSV;
- cohort weights;
- live weights;
- backtest;
- JSON summary.

## 13. EXP-002: feature attribution and score smoothing

Runner: [scripts/run_exp002.py](../../scripts/run_exp002.py).

Two main mathematical operations:

### Leave-one-feature-out ablation

Fit the full model and nine ablated models, each omitting one feature.

Compare paired IC series and apply BH FDR control.

### EWMA smoothing

Transform scores to daily ranks and causally smooth each symbol's ranked score path.

The experiment asks whether turnover can fall without destroying signal and net return.

No smoothing span passed every registered gate.

## 14. EXP-003: reduced feature sets and partial adjustment

Runner: [scripts/run_exp003.py](../../scripts/run_exp003.py).

Feature specifications include:

- full9;
- core2;
- core3;
- pruned8.

The experiment established pruned8 as the only reduced specification passing all registered statistical eligibility conditions.

It also tests partial adjustment rates for portfolio inertia.

No partial-adjustment rule was promoted.

## 15. EXP-004: explicit turnover budgets

Runner: [scripts/run_exp004.py](../../scripts/run_exp004.py).

Budgets:

\[
B\in\{0.12,0.10,0.08\}.
\]

Each day, solve the constrained projection explained in Part 4.

The corrected 0.12 budget came extremely close to the gross-return retention requirement:

\[
79.9649\%
\]

versus an 80% threshold.

It still failed.

This is a useful reproducibility check because a different implementation should reach the same gate decision rather than rounding it into a pass.

## 16. EXP-005: no-trade bands

Runner: [scripts/run_exp005.py](../../scripts/run_exp005.py).

Bands:

\[
b\in\{0.005,0.010,0.020\}.
\]

Small target changes are ignored and the remaining active positions are projected subject to portfolio constraints.

No candidate passed all turnover, retention and net-return gates.

## 17. EXP-006: robustness and falsification

Runner: [scripts/run_exp006.py](../../scripts/run_exp006.py).

This experiment contains four sections:

1. horizon robustness;
2. chronological thirds;
3. asset-group dependence;
4. symbol-identity permutation placebo.

Important code:

- [prepare_horizon_research_frame](../../src/quantlab/robustness.py)
- [chronological_ic_blocks](../../src/quantlab/robustness.py)
- [asset_group_diagnostics](../../src/quantlab/robustness.py)
- [global_symbol_permutation_test](../../src/quantlab/robustness.py)

The experiment formally failed because the leave-US-risk-out aggregate did not meet the registered retention/significance rule.

The failure is part of the result.

## 18. EXP-007: group-neutral learning

Runner: [scripts/run_exp007.py](../../scripts/run_exp007.py).

The model is retrained using the group-neutral target while keeping:

- the same dates;
- the same folds;
- the same features;
- the same model hyperparameters.

It computes within-group ICs and equal-weight group composites.

Four of five gates passed. The non-US composite produced

\[
p=0.0501247,
\]

which is not less than 0.05.

Again, exact reproduction includes reproducing the **failure**.

## 19. Portfolio accounting correction

Read [docs/accounting_correction.md](../accounting_correction.md).

The correction changed only the economic accounting:

- portfolio P&L now uses simple returns;
- equity uses cumulative products of \(1+R\);
- terminal liquidation is explicitly costed.

Prediction targets, scores, rank IC, model selection and robustness conclusions did not change.

The correction workflow is [.github/workflows/economic-correction.yml](../../.github/workflows/economic-correction.yml).

## 20. GitHub Actions as reproducible experiments

The workflow files under [.github/workflows](../../.github/workflows) specify:

- Python version;
- package installation;
- data artifact retrieval;
- checksum verification;
- experiment command;
- output upload.

This makes an experiment more reproducible than a notebook whose cells may have been run in an unknown order.

For a student, the workflow YAML is worth reading alongside each experiment script.

## 21. What outputs should match?

A faithful reproduction should match, up to harmless floating-point differences:

- number of scored dates;
- mean IC;
- HAC statistics;
- fold and annual IC summaries;
- experiment gate decisions;
- portfolio turnover;
- cost-sensitive returns;
- selected or rejected candidate rules;
- permutation seed and empirical p-value.

If these disagree materially, investigate before interpreting the result.

## 22. Floating-point differences

Numerical libraries can sometimes differ slightly across operating systems or package versions.

Differences such as

\[
0.02700877388
\quad\text{versus}\quad
0.02700877387
\]

are usually immaterial.

A result switching from 79.96% to 80.10%, however, would be material because it could change a registered decision.

This is why environment and dependency control matter.

## 23. How to trace one prediction

To understand one row:

1. locate a date/symbol in a predictions CSV;
2. inspect its OHLCV history;
3. recompute its features from [features.py](../../src/quantlab/features.py);
4. verify the forward target from [targets.py](../../src/quantlab/targets.py);
5. identify its walk-forward fold;
6. confirm the fold's training dates precede it;
7. compare its model score with scores of other ETFs that date;
8. compute its rank;
9. compute the day's Spearman IC.

This transforms the pipeline from a black box into auditable mathematics.

## 24. Safe extension rules

If you create a new experiment, do not immediately run dozens of variations.

A defensible extension should first specify:

- question;
- exact formula;
- expected direction;
- dates used;
- acceptance rule;
- multiplicity treatment;
- whether it is exploratory or confirmatory.

The repository's [research_log.md](../research_log.md) shows this discipline.

## 25. Do not use the final hold-out as a debugging set

If the hold-out is opened and then the code, features or model are changed because the result was disappointing, the hold-out becomes development data.

The final test has value only because its outcomes have not guided the research process.

For learning purposes, use synthetic data or the existing development outputs to debug new code.
