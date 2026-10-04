# Research Protocol — Cross-Sectional Predictive Signals

## Research question

Can a compact set of lagged price, volatility, range and volume features produce a stable out-of-sample ranking of **future relative returns** across a liquid, fixed ETF universe after realistic turnover costs?

This is a signal-research exercise, not a claim of a profitable trading strategy.

## Why a fixed ETF universe first?

The first version deliberately uses a fixed set of liquid ETFs rather than today's equity-index constituents. That avoids silently introducing constituent survivorship bias while keeping the data freely reproducible. A later phase may use point-in-time equity membership from a suitable data source.

## Timing convention

At decision date **t**:

- all features use data available by the close of t;
- the hypothetical trade enters at the next session's open, t+1;
- the h-session prediction target is log(Open[t+h+1] / Open[t+1]);
- the modelling target subtracts the same-date cross-sectional mean, making the task relative rather than directional.

This timing convention prevents use of the current close as an executable price and makes look-ahead assumptions explicit.

## Primary hypothesis

A fixed, pre-declared feature set has non-zero cross-sectional predictive information for 5-session relative returns.

### Primary statistic

Daily Spearman rank information coefficient (IC), summarised by:

- mean IC;
- HAC/Newey-West t-statistic with lag h-1 to account for overlapping forward-return horizons.

### Secondary evidence

A dollar-neutral rank portfolio evaluated on next-open-to-open returns with explicit one-way transaction costs. Report:

- annualised return and volatility;
- Sharpe ratio;
- maximum drawdown;
- turnover;
- sensitivity to transaction costs.

Portfolio performance is secondary to signal validity.

## Pre-declared models

1. **Ridge regression** — deliberately simple statistical baseline.
2. **Histogram gradient boosting** — nonlinear comparator.

The aim is to test whether nonlinear structure improves genuinely out-of-sample ranking, not to run a large model search.

## Validation design

- expanding-window training;
- purged walk-forward test blocks;
- purge gap of h+1 decision dates between training and testing;
- final 252-session hold-out is excluded from normal development runs.

The final hold-out should be evaluated once, after freezing:

- universe;
- feature definitions;
- target horizon;
- model family/hyperparameters;
- portfolio construction;
- cost assumptions;
- reporting metrics.

## Multiple testing

The baseline intentionally limits the feature set and model count. If the project expands to many hypotheses, false-discovery control and/or a formal research registry should be added. Negative results must be retained in the research log rather than discarded.

## Known limitations of v0.1

- free Yahoo data is convenient but is not institutional-grade market data;
- ETF universe is broad and heterogeneous rather than a pure equity cross-section;
- no bid/ask spread or market-impact model beyond bps transaction costs;
- no corporate-event or intraday modelling;
- no point-in-time equity constituent database;
- no capacity analysis.

These are documented limitations, not hidden assumptions.
