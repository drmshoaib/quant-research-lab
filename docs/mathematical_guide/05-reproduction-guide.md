# Part 5 — Reproducing the Research in Python

This part turns the mathematics into an executable workflow. A valid reproduction must preserve not only the code but also the timing convention, frozen data, universe, hold-out, model and statistical protocol.

## 1. Repository structure

| Path | Purpose |
|---|---|
| [src/quantlab](../../src/quantlab) | reusable research library |
| [scripts](../../scripts) | experiment entry points |
| [configs](../../configs) | frozen settings, hold-out and snapshot metadata |
| [data](../../data) | ETF universe |
| [docs](../../docs) | protocol, results and research notes |
| [tests](../../tests) | mathematical and software invariants |
| [.github/workflows](../../.github/workflows) | reproducible GitHub Actions runs |

## 2. Create a Python environment

From the repository root:

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,data]'
~~~

Run the test suite before any experiment:

~~~bash
pytest
~~~

Important test groups include:

- [test_features.py](../../tests/test_features.py): future values must not alter past features;
- [test_targets.py](../../tests/test_targets.py): next-open target timing and arithmetic portfolio returns;
- [test_splits.py](../../tests/test_splits.py): purging and date manifests;
- [test_pipeline.py](../../tests/test_pipeline.py): hold-out locking and embargo logic;
- [test_backtest.py](../../tests/test_backtest.py): staggered sleeves, costs, liquidation and compounding;
- [test_portfolio.py](../../tests/test_portfolio.py): neutrality, exposure limits and optimisation;
- [test_robustness.py](../../tests/test_robustness.py): permutation and robustness logic;
- [test_group_neutral.py](../../tests/test_group_neutral.py): group-neutral calculations.

The tests are part of the mathematical specification, not merely software housekeeping.

## 3. Frozen numerical configuration

The main settings are in [configs/baseline.json](../../configs/baseline.json).

Key values are

$$
h=5,\quad minAssets=8,\quad minTrain=756,
$$

$$
test=63,\quad step=63,\quad holdout=252,\quad purge=6,
$$

and

$$
cost=5\text{ bps},\quad gross=1,\quad \max_i|w_i|=0.08.
$$

The final specification is in [configs/final_specification_v0.2.json](../../configs/final_specification_v0.2.json).

## 4. Frozen universe

The exact 30-symbol universe and taxonomy are in [data/universe_etf.csv](../../data/universe_etf.csv).

Do not silently add or remove symbols if the aim is to reproduce v0.2.

The fixed ETF design reduces one constituent-membership survivorship problem, but the ETF set itself is still selected ex post. Reproduction means using the same universe, not claiming that the universe is unbiased.

## 5. Frozen data snapshot

The official market-data snapshot is described in [configs/data_snapshot.json](../../configs/data_snapshot.json).

Its SHA-256 checksum is

~~~
ec782ac2cd812a6d81abcbf9cbcdecdd448ab8822b585fbd07c3a74968a3bbd3
~~~

The large CSV was stored as a workflow artifact rather than committed as ordinary source.

To reproduce the **official** results, use the byte-identical frozen snapshot. A new Yahoo download at a later date may contain provider revisions.

### Why a checksum matters

A cryptographic hash is a deterministic fingerprint. If the checksum changes, the research input is not byte-identical.

Financial data vendors may revise adjusted historical series, so a frozen checksum makes the input auditable.

## 6. Hold-out manifest

The final 252 eligible decision dates are explicitly stored in [configs/holdout_dates.csv](../../configs/holdout_dates.csv).

The development code checks that the manifest is the final eligible block of the frozen target calendar.

Do not regenerate or replace it during ordinary reproduction.

The original freeze procedure is implemented in [scripts/freeze_holdout.py](../../scripts/freeze_holdout.py).

## 7. Reproducing the freeze procedure separately

If you want to understand how the hold-out was created, use a separate output path or copy of the repository.

Conceptually the script:

1. loads adjusted OHLCV;
2. computes eligible target dates;
3. takes the final 252 dates;
4. writes the ordered manifest.

Generic command:

~~~bash
python scripts/freeze_holdout.py --data path/to/adjusted_ohlcv.csv
~~~

Do not overwrite the committed v0.2 manifest when reproducing the existing study.

## 8. Main baseline flow

Runner: [scripts/run_baseline.py](../../scripts/run_baseline.py).

With the frozen data available:

~~~bash
python scripts/run_baseline.py \
  --data path/to/frozen_market_data.csv \
  --output-dir outputs/reproduction/exp001
~~~

The script performs:

~~~text
load config and hold-out manifest
load frozen adjusted OHLCV
prepare leakage-safe research frame
compute arithmetic realised portfolio returns

for each model:
    generate purged walk-forward predictions
    compute daily rank IC
    compute HAC and temporal diagnostics
    convert scores to rank weights
    construct five staggered sleeves
    append terminal liquidation
    backtest at several transaction costs
    save predictions, IC and summary files
~~~

## 9. Main function chain

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

Trace this chain while reading Parts 1–4.

## 10. EXP-001 — linear versus nonlinear baseline

Runner: [scripts/run_baseline.py](../../scripts/run_baseline.py).

Question:

> does a simple Ridge model produce a defensible cross-sectional ranking signal, and how does the fixed nonlinear comparator behave?

Ridge failed the pre-registered primary hypothesis. HistGradientBoosting became the development candidate.

Typical outputs include predictions, daily IC, cohort weights, live weights, backtest rows and a JSON summary.

## 11. EXP-002 — feature attribution and score smoothing

Runner: [scripts/run_exp002.py](../../scripts/run_exp002.py).

### Leave-one-feature-out ablation

For each feature $j$, compare

$$
IC_t^{full}
$$

with

$$
IC_t^{(-j)}.
$$

The paired loss is

$$
D_{j,t}=IC_t^{full}-IC_t^{(-j)}.
$$

HAC inference is applied to the loss series, and BH FDR correction is applied across the family of feature tests.

### EWMA score smoothing

Daily scores are first converted to centred cross-sectional ranks. Each symbol's rank path is then causally smoothed.

No smoothing span passed all registered signal, turnover and net-return gates.

## 12. EXP-003 — reduced features and partial adjustment

Runner: [scripts/run_exp003.py](../../scripts/run_exp003.py).

Compared feature sets include full9, core2, core3 and pruned8.

Pruned8 became the frozen feature specification because it was the only reduced model satisfying all registered statistical eligibility rules.

The same experiment tested partial-adjustment execution. No adjustment rate was promoted.

## 13. EXP-004 — turnover-budget projection

Runner: [scripts/run_exp004.py](../../scripts/run_exp004.py).

Budgets are

$$
B\in\{0.12,0.10,0.08\}.
$$

Each date solves the constrained projection described in Part 4.

The corrected 0.12 candidate retained

$$
79.9649\%
$$

of zero-cost return against an 80% requirement.

It therefore remained a failure rather than being rounded into a pass.

## 14. EXP-005 — no-trade bands

Runner: [scripts/run_exp005.py](../../scripts/run_exp005.py).

Bands are

$$
b\in\{0.005,0.010,0.020\}.
$$

Small desired weight changes are held unchanged; active names are moved toward target subject to portfolio constraints.

No candidate passed all registered gates.

## 15. EXP-006 — robustness and falsification

Runner: [scripts/run_exp006.py](../../scripts/run_exp006.py).

It contains four pre-specified robustness sections:

1. horizon checks;
2. chronological thirds;
3. broad asset-group dependence;
4. a 999-replicate symbol-identity permutation placebo.

Core functions:

- [prepare_horizon_research_frame](../../src/quantlab/robustness.py)
- [chronological_ic_blocks](../../src/quantlab/robustness.py)
- [asset_group_diagnostics](../../src/quantlab/robustness.py)
- [global_symbol_permutation_test](../../src/quantlab/robustness.py)

EXP-006 formally failed because removing the US-risk block did not satisfy the leave-one-group-out retention/significance rule.

A valid reproduction reproduces that negative result.

## 16. EXP-007 — group-neutral learning

Runner: [scripts/run_exp007.py](../../scripts/run_exp007.py).

The HistGradientBoosting model is retrained using the group-neutral target while keeping the same dates, folds, features and hyperparameters.

Four of five gates passed. The non-US composite produced

$$
p=0.0501247,
$$

which is not less than the pre-registered 0.05 threshold.

Again, faithful reproduction includes reproducing the failure.

## 17. Portfolio-accounting correction

Read [accounting_correction.md](../accounting_correction.md).

Before the final hold-out was touched, a technical audit corrected two secondary portfolio-accounting issues:

1. portfolio P&L now uses simple open-to-open returns;
2. terminal liquidation is explicitly costed.

The predictive targets, model scores, rank IC, model selection and EXP-006/007 robustness results were unchanged.

The correction workflow is [.github/workflows/economic-correction.yml](../../.github/workflows/economic-correction.yml).

## 18. GitHub Actions as experiment records

Workflow YAML files specify:

- Python version;
- dependencies;
- frozen-data artifact retrieval;
- checksum verification;
- exact experiment command;
- output artifact upload.

This provides a cleaner audit trail than a notebook whose execution order may be uncertain.

Read each workflow beside its matching script.

## 19. What should match?

A faithful reproduction should match, apart from negligible floating-point differences:

- scored date counts;
- mean rank IC;
- HAC statistics;
- fold and annual IC summaries;
- experiment gate decisions;
- portfolio turnover;
- transaction-cost sensitivity;
- selected/rejected execution rules;
- permutation seed and empirical p-value.

## 20. Floating-point tolerance

Numbers such as

$$
0.02700877388
$$

and

$$
0.02700877387
$$

are practically identical.

A difference that changes a registered gate is not.

For example, moving a retention result from 79.96% to 80.10% would require investigation because the research decision could change.

## 21. How to audit one prediction row

Choose one date and symbol from a predictions output.

Then:

1. inspect its prior adjusted OHLCV;
2. recompute its features using [features.py](../../src/quantlab/features.py);
3. verify its future target using [targets.py](../../src/quantlab/targets.py);
4. identify its walk-forward fold;
5. confirm that all training dates precede the purged test block;
6. compare its score with the other ETFs that day;
7. calculate its rank;
8. reproduce that day's Spearman IC.

Doing this once turns the whole pipeline from a black box into a transparent sequence of calculations.

## 22. Safe extension rules

Before a new research experiment, specify:

- the question;
- exact formula;
- expected direction;
- data window;
- acceptance rule;
- multiplicity treatment;
- whether it is exploratory or confirmatory.

The format is illustrated in [research_log.md](../research_log.md).

Do not search repeatedly until a pleasing result appears.

## 23. Never use the final hold-out as a debugging set

If the hold-out is opened and then the model, features or thresholds are changed because the result is disappointing, the hold-out becomes development data.

For software debugging, use unit tests, synthetic data or existing development outputs.

The value of the final 252 dates comes entirely from the fact that their outcomes have not guided the research.
