# Quant Research Lab

A research-grade, reproducible project for testing cross-sectional predictive signals in financial time series.

The objective is to demonstrate the workflow expected in serious quantitative research: explicit timing assumptions, leakage controls, purged walk-forward validation, statistical inference, transaction costs, reproducible code, and an untouched final hold-out.

## Research question

Can a compact set of lagged market features rank future **relative** returns across a liquid fixed ETF universe out of sample?

At decision date `t`, features use information available by the close. The target enters at the next open and exits five sessions later. The final 252 eligible decision dates in the frozen v0.2 data window are locked during normal development.

## What is implemented

- provider-agnostic long-form OHLCV data interface;
- split/dividend-adjusted Yahoo OHLC adapter;
- fixed v0.2 data end date;
- immutable hold-out date manifest workflow;
- pre-hold-out embargo to stop development labels overlapping hold-out outcomes;
- lagged momentum, volatility, range, volume and drawdown features;
- next-open execution convention;
- 5-session forward cross-sectional relative-return target;
- expanding **purged walk-forward** validation;
- Ridge regression baseline;
- histogram gradient boosting nonlinear comparator;
- daily Spearman rank IC;
- HAC/Newey-West inference for overlapping horizons;
- dollar-neutral, gross-constrained rank portfolios;
- five staggered portfolio sleeves aligned with the 5-session forecast;
- transaction-cost-aware backtesting on actual composite turnover;
- constrained alpha/risk/turnover optimiser using SLSQP for the later optimisation phase;
- explicit 252-session locked hold-out;
- unit tests for leakage, split purging, price adjustment, hold-out locking, portfolio alignment, constraints and costs.

## Why ETFs in v0.1/v0.2?

Using today's equity constituents to backtest history creates a survivorship problem. The first empirical phase therefore uses a fixed universe of liquid ETFs spanning equities, sectors, rates, credit, commodities and real estate. A later equity phase will use point-in-time membership data.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,data]'
```

## Run tests

```bash
pytest
```

## Freeze the v0.2 hold-out

The data window is fixed in `configs/baseline.json`. Before running empirical experiments, generate the 252-date hold-out manifest once:

```bash
python scripts/freeze_holdout.py
```

Then review and commit `configs/holdout_dates.csv`. The development script refuses to run without this manifest.

With a provider-exported **adjusted** OHLCV CSV:

```bash
python scripts/freeze_holdout.py --data path/to/ohlcv.csv
```

## Run the development experiment

With Yahoo data:

```bash
python scripts/run_baseline.py
```

Or with the same provider-exported adjusted OHLCV CSV:

```bash
python scripts/run_baseline.py --data path/to/ohlcv.csv
```

Outputs are written below `outputs/baseline/`. **The final 252-session hold-out is not scored by this script.**

## Research discipline

Before the hold-out is unlocked, freeze:

1. data snapshot and hold-out manifest;
2. universe;
3. features;
4. prediction horizon;
5. model family and hyperparameters;
6. portfolio construction;
7. cost assumptions;
8. evaluation metrics.

See [`docs/research_protocol.md`](docs/research_protocol.md), [`docs/v0.2_audit.md`](docs/v0.2_audit.md) and [`docs/research_log.md`](docs/research_log.md).

## Planned phases

- **v0.1 — methodology scaffold:** leakage-safe panel, walk-forward validation, baselines, inference, tests.
- **v0.2 — empirical baseline:** fixed data/hold-out protocol, full-history development experiments, IC stability and transaction-cost sensitivity.
- **v0.3 — optimisation:** covariance-aware portfolio construction and turnover/risk constraints.
- **v0.4 — point-in-time equities:** introduce a survivorship-safe equity universe.
- **v0.5 — research note:** publish a concise 4–6 page report including negative results and the one-time hold-out evaluation.

## Scope and disclaimer

This repository is a research/education project. It is not investment advice and is not presented as a production trading system.
