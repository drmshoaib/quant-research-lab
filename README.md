# Quant Research Lab

A reproducible cross-sectional quant research project built around a simple question:

> Can end-of-day market information rank medium-horizon **relative** ETF returns out of sample?

## Current development result

The frozen development model is an eight-feature `HistGradientBoostingRegressor` (`pruned8`) evaluated with next-open execution and purged expanding-window validation.

- mean 5-session daily rank IC: **0.02701**;
- HAC t-statistic: **3.922**, two-sided **p = 8.78e-5**;
- positive mean IC in **12/13** eligible development years;
- 999-path symbol-identity placebo: empirical **p = 0.001**;
- 10- and 20-session horizon checks remain significant after BH correction;
- group-neutral retraining retains **86.3%** of the control within-group IC.

The evidence is statistically interesting but **not a production trading result**. Under corrected arithmetic-return portfolio accounting, the instant five-sleeve benchmark earns about **2.34% annualised before costs** and **0.25% at 5 bps one way**, with annualised turnover **41.91** and Sharpe **0.065**. Cross-asset robustness is also incomplete: EXP-006 and EXP-007 each fail one pre-registered robustness condition.

**The final 252-date hold-out remains locked and unevaluated.**

Learn or review the full mathematics in the **[undergraduate mathematical guide](docs/mathematical_guide/README.md)**. It derives the returns, features, Ridge and gradient boosting models, purged walk-forward validation, HAC/Newey-West inference, Spearman IC, multiple-testing control, portfolio construction, transaction costs, constrained optimisation and robustness tests, with direct links to the Python implementation and a worked example.

Read the evidence in:

- [Mathematical guide](docs/mathematical_guide/README.md)
- [Research note](docs/research_note.md)
- [Final frozen specification](configs/final_specification_v0.2.json)
- [Research log](docs/research_log.md)
- [Portfolio-accounting correction](docs/accounting_correction.md)
- [Research protocol](docs/research_protocol.md)
- [Errata and known issues](docs/errata.md) (independent review, October 2026)

## Research discipline

The project is designed to demonstrate research process rather than optimise a headline backtest:

- fixed data window and checksum;
- immutable hold-out date manifest;
- next-open execution convention;
- horizon-aware purging and pre-hold-out embargo;
- pre-registered experiment rules;
- daily Spearman rank IC with HAC/Newey-West inference;
- multiple-testing control where relevant;
- negative-result retention;
- explicit transaction costs and turnover;
- robustness and placebo testing;
- unit tests for leakage, timing, price adjustment, portfolio alignment and constraints.

## Frozen v0.2 specification

Primary horizon: **5 sessions**.

Features:

`ret_1`, `mom_20`, `mom_60`, `vol_20`, `vol_60`, `range_1`, `volume_z_20`, `drawdown_60`.

Model:

`HistGradientBoostingRegressor(learning_rate=0.05, max_iter=250, max_leaf_nodes=15, min_samples_leaf=40, l2_regularization=1.0, random_state=42)`.

Validation:

- minimum training history: 756 decision dates;
- test block / step: 63 / 63 dates;
- train/test purge: 6 dates;
- pre-hold-out embargo: 6 dates;
- final hold-out: 252 eligible dates, 24 September 2025 to 24 September 2026.

## Why ETFs?

Using current equity constituents throughout history creates a severe constituent-membership survivorship problem. This first empirical phase instead uses a fixed 30-ETF universe spanning equities, rates, credit, commodities and real estate.

That choice **reduces one source of membership bias; it does not make the universe point-in-time or unbiased**. The ETF set itself is selected ex post and cross-sectional breadth is uneven. A later equity phase should use point-in-time membership data.

## Repository structure

- `src/quantlab/` — data, features, targets, models, splits, portfolio and robustness code;
- `scripts/` — reproducible experiment runners;
- `configs/` — frozen baseline, data snapshot, hold-out and final specification;
- `docs/` — protocol, audit trail, experiment results and research note;
- `tests/` — leakage, timing, accounting and constraint tests.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,data]'
pytest
```

## Development history

- **v0.1:** methodology scaffold and leakage-safe validation.
- **v0.2:** frozen ETF development programme, EXP-001 through EXP-007, robustness work and research note.
- **Current state:** development specification frozen; hold-out not yet evaluated.
- **Future:** one-time hold-out decision, then point-in-time equity research and risk-aware portfolio construction as separate phases.

## Scope

This repository is a research and education project. The portfolio is a diagnostic translation of the signal, not an investment recommendation or production trading system.
