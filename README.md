# Quant Research Lab

A research-grade, reproducible project for testing cross-sectional predictive signals in financial time series.

The objective is not to maximise a backtest screenshot. It is to demonstrate the workflow expected in serious quantitative research: explicit timing assumptions, leakage controls, purged walk-forward validation, statistical inference, transaction costs, reproducible code, and an untouched final hold-out.

## Research question

Can a compact set of lagged market features rank future **relative** returns across a liquid fixed ETF universe out of sample?

At decision date `t`, features use information available by the close. The target enters at the next open and exits `h` sessions later. The final year is locked during normal development.

## What is implemented

- provider-agnostic long-form OHLCV data interface;
- optional Yahoo/yfinance downloader;
- lagged momentum, volatility, range, volume and drawdown features;
- next-open execution convention;
- 5-session forward cross-sectional relative-return target;
- expanding **purged walk-forward** validation;
- Ridge regression baseline;
- histogram gradient boosting nonlinear comparator;
- daily Spearman rank IC;
- HAC/Newey-West inference for overlapping horizons;
- dollar-neutral, gross-constrained rank portfolios;
- transaction-cost-aware backtesting;
- constrained alpha/risk/turnover optimiser using SLSQP;
- explicit 252-session locked hold-out;
- unit tests for leakage, split purging, portfolio constraints and costs.

## Why ETFs in v0.1?

Using today's equity constituents to backtest history creates a subtle survivorship problem. The first phase therefore uses a fixed universe of liquid ETFs spanning equities, sectors, rates, credit, commodities and real estate. A later equity phase will use point-in-time membership data.

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

## Run the development experiment

With Yahoo data:

```bash
python scripts/run_baseline.py
```

Or with a provider-exported long OHLCV CSV containing
`date,symbol,open,high,low,close,volume`:

```bash
python scripts/run_baseline.py --data path/to/ohlcv.csv
```

Outputs are written below `outputs/baseline/`. **The final 252-session hold-out is not scored by this script.**

## Research discipline

Before the hold-out is unlocked, freeze:

1. universe;
2. features;
3. prediction horizon;
4. model family and hyperparameters;
5. portfolio construction;
6. cost assumptions;
7. evaluation metrics.

See [`docs/research_protocol.md`](docs/research_protocol.md).

## Planned phases

- **v0.1 — methodology scaffold:** leakage-safe panel, walk-forward validation, baselines, inference, tests.
- **v0.2 — empirical baseline:** run the full history, diagnose IC stability and transaction-cost sensitivity.
- **v0.3 — optimisation:** covariance-aware portfolio construction and turnover/risk constraints.
- **v0.4 — point-in-time equities:** introduce a survivorship-safe equity universe.
- **v0.5 — research note:** publish a concise 4–6 page report including negative results and the one-time hold-out evaluation.

## Scope and disclaimer

This repository is a research/education project. It is not investment advice and is not presented as a production trading system.
