# Research Protocol — v0.2 Cross-Sectional Predictive Signals

**Status:** Development protocol frozen; final hold-out locked  
**Protocol date:** 4 October 2026  
**Primary horizon:** 5 trading sessions

## 1. Research question

Can a compact set of information available at the close of decision date (t) rank future **relative** returns across a fixed liquid ETF universe out of sample, and does that information survive realistic turnover costs?

The primary object of inference is predictive ranking quality. Portfolio performance is secondary evidence.

## 2. Data universe and frozen data window

The v0.2 universe is the 30-symbol ETF universe in `data/universe_etf.csv`. It is fixed for the whole v0.2 programme.

The research data window is frozen as:

- start: 1 January 2010;
- end: 3 October 2026, exclusive in the Yahoo adapter, so the last intended US session is 2 October 2026.

The data end date must not roll forward during v0.2.

Price fields used for returns and price-derived features must be consistently adjusted for splits and distributions. For Yahoo/yfinance this means adjusted OHLC data. A provider-exported dataset may be used instead, but its adjustment convention must be documented and internally consistent.

No empirical result may be compared across data snapshots unless the snapshot change is explicitly registered as a new experiment.

## 3. Hold-out definition

The final hold-out consists of the last 252 eligible decision dates from the frozen market-data/target calendar.

The hold-out calendar is generated once from the frozen data snapshot, persisted in `configs/holdout_dates.csv`, and then treated as immutable. It is defined before feature engineering, so feature-specific missingness cannot move the boundary.

A six-decision-date ((h+1)) embargo immediately before the hold-out is excluded from development. This prevents development labels and portfolio sleeves from overlapping the hold-out outcome path.

No model fitting, feature selection, threshold choice, hyperparameter choice, cost calibration or portfolio rule may use hold-out outcomes.

The hold-out is evaluated once after the final development specification has been committed. There is no second tuning cycle after seeing it.

## 4. Timing convention

At decision date (t):

- features use information available by the close of (t);
- the earliest executable price is the open of (t+1);
- for horizon (h=5), the raw target is

[
y_{i,t}^{raw}=\log\left(\frac{O_{i,t+h+1}}{O_{i,t+1}}\right);
]

- the modelling target is the same-date cross-sectional relative return

[
y_{i,t}=y_{i,t}^{raw}-\frac{1}{N_t}\sum_{j=1}^{N_t}y_{j,t}^{raw}.
]

All target calculations remain outside the feature pipeline.

## 5. Development validation

Development evaluation uses expanding purged walk-forward validation with:

- minimum training history: 756 decision dates;
- test block: 63 decision dates;
- step: 63 decision dates;
- train/test purge: (h+1=6) decision dates;
- pre-hold-out embargo: (h+1=6) decision dates;
- no hold-out observations in any development fold.

The primary baseline models remain:

1. Ridge regression with (alpha=10);
2. `HistGradientBoostingRegressor` with the fixed v0.1 hyperparameters.

A hyperparameter search is a separate registered experiment. If introduced, tuning must occur inside the development sample using a nested time-ordered procedure.

## 6. Baseline feature set

The v0.1 feature set is the starting benchmark:

- 1-session return;
- 5-, 20- and 60-session momentum;
- 20- and 60-session realised volatility;
- daily high-low range;
- 20-session log-volume z-score;
- 60-session drawdown.

These features are the benchmark, not the final frozen feature set.

v0.2 may investigate additional signals using development data only. Every candidate must be entered in `docs/research_log.md` before its result is inspected, including the hypothesis, formula, expected direction where meaningful, and acceptance criterion.

## 7. Signal inference

The primary statistic is daily cross-sectional Spearman rank IC.

For each signal or model report:

- mean rank IC;
- median rank IC;
- IC standard deviation and IC information ratio;
- fraction of dates with the expected IC sign;
- fold-level IC;
- annual IC;
- HAC/Newey-West t-statistic and two-sided p-value with lag (h-1=4);
- IC decay across nearby horizons where relevant.

When a research batch contains several candidate signals, multiple-testing control must be reported. Benjamini-Hochberg false-discovery-rate control at (q=0.10) is the default for exploratory signal batches.

A signal is not promoted on aggregate IC alone. It must also have reasonable temporal stability and must not depend on a single short subperiod.

## 8. Portfolio translation

A 5-session forecast is evaluated with a horizon-consistent portfolio.

The v0.2 implementation uses five staggered sleeves:

- each decision date creates one cohort from that day's scores;
- the cohort enters at the next open;
- it remains active for five one-session open-to-open return periods;
- each cohort receives (1/5) of portfolio capital;
- five overlapping cohorts are active in steady state;
- after the final development signal, existing sleeves run off during the pre-hold-out embargo.

The baseline portfolio remains:

- dollar neutral;
- gross exposure limit: 1.0;
- per-name absolute weight cap: 0.08 at the cohort level;
- rank-based construction;
- no covariance optimiser in the primary v0.2 result.

The existing optimiser is reserved for the later optimisation phase so signal discovery is not confounded with portfolio engineering.

## 9. Transaction costs

The base assumption is 5 basis points one way, charged on actual traded notional:

[
C_t = c\sum_i |w_{i,t}-w_{i,t-1}|.
]

Cost sensitivity must be reported at 0, 2, 5, 10 and 20 bps.

Turnover is computed from the horizon-consistent composite portfolio.

## 10. Performance reporting

Signal evidence is primary. Portfolio statistics are secondary.

The development report must include:

- annualised arithmetic return;
- annualised volatility;
- Sharpe ratio;
- maximum drawdown;
- average and annualised turnover;
- gross and net performance;
- cost sensitivity;
- year-by-year results;
- fold-by-fold results.

Because overlapping sleeves induce serial dependence, uncertainty for mean portfolio return should use a HAC or block-bootstrap estimate rather than an IID standard error.

## 11. Robustness and falsification

Pre-hold-out robustness work may include:

- 1-, 5-, 10- and 20-session prediction horizons;
- feature ablations;
- alternative cost assumptions;
- subperiod analysis;
- broad asset-group neutrality as a robustness check;
- volatility-regime analysis;
- permutation or sign-randomisation placebo tests;
- block-bootstrap confidence intervals.

Exploratory and pre-specified checks must be labelled separately in the research log.

## 12. Freeze before hold-out

Before unlocking the 252-session hold-out, commit a final experiment manifest containing:

- data snapshot identifier/checksum and data end date;
- immutable hold-out date manifest;
- universe file checksum;
- final feature list and formulas;
- target horizon;
- model classes and hyperparameters;
- walk-forward parameters;
- portfolio-construction rule;
- cost assumptions;
- evaluation metrics;
- code commit SHA.

The final hold-out result is then run once and reported without modification. A weak or negative hold-out result remains part of the research record.
