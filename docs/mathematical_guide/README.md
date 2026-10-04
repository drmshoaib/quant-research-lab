# Mathematics of the Quant Research Lab

**Audience:** undergraduate students in mathematics, statistics, data science, computer science, economics or engineering  
**Project:** Quant Research Lab v0.2  
**Purpose:** explain the mathematics, statistical reasoning and Python implementation well enough that a careful reader can reproduce the development study from first principles

This guide accompanies the main [research note](../research_note.md). The research note answers *what did we find?* This guide answers *what exactly did we calculate, why did we calculate it, and how is it implemented?*

The final 252-date hold-out remains locked. This guide explains the development workflow only.

## How to use this guide

Read the parts in order if you are new to quantitative finance.

1. [Part 1 — Data, returns, features and targets](01-data-returns-features-targets.md)
2. [Part 2 — Models and walk-forward learning](02-models-and-walk-forward.md)
3. [Part 3 — Rank IC, inference and robustness](03-inference-and-robustness.md)
4. [Part 4 — Portfolio mathematics and transaction costs](04-portfolio-and-costs.md)
5. [Part 5 — Reproducing the research in Python](05-reproduction-guide.md)
6. [Part 6 — Worked example and exercises](06-worked-example.md)

## Mathematical prerequisites

You do not need advanced stochastic calculus. The project mainly uses logarithms, percentages, means, standard deviations, correlations, matrices, least-squares regression, basic hypothesis testing and constrained optimisation.

## Core notation

| Symbol | Meaning |
|---|---|
| \(i\) | asset / ETF index |
| \(t\) | decision date |
| \(O_{i,t}\) | adjusted opening price of asset \(i\) on date \(t\) |
| \(C_{i,t}\) | adjusted closing price |
| \(H_{i,t},L_{i,t}\) | adjusted high and low |
| \(V_{i,t}\) | volume |
| \(h\) | forecast horizon; primary value is 5 sessions |
| \(x_{i,t}\) | feature vector known after the close on date \(t\) |
| \(y_{i,t}\) | modelling target attached to decision date \(t\) |
| \(\hat y_{i,t}\) | model prediction / score |
| \(w_{i,t}\) | portfolio weight |
| \(IC_t\) | cross-sectional rank information coefficient |
| \(c\) | one-way transaction cost rate |
| \(N_t\) | number of eligible assets on date \(t\) |

## The central timing idea

At the close of day \(t\), the model may use information up to that close. It may not pretend that it traded at the same close. The first assumed tradable price is the next opening price, \(O_{i,t+1}\).

For the five-session target, the position enters at \(t+1\) open and exits at \(t+6\) open:

\[
r^{(5)}_{i,t}
=
\log\left(\frac{O_{i,t+6}}{O_{i,t+1}}\right).
\]

Python implementation: [forward_open_return](../../src/quantlab/targets.py) in src/quantlab/targets.py.

## The research question in mathematical form

Given a feature vector \(x_{i,t}\), learn a function

\[
f:x_{i,t}\mapsto \hat y_{i,t}
\]

such that higher model scores tend to correspond to higher future **relative** returns.

The project is mainly a ranking problem. The primary statistical object is daily Spearman rank correlation:

\[
IC_t=\rho_S(\hat y_{\cdot,t},y_{\cdot,t}).
\]

## What the project found on development data

The frozen eight-feature HistGradientBoosting specification produced approximately:

- mean five-session rank IC **0.02701**;
- HAC t-statistic **3.922**;
- HAC two-sided p-value **8.78 × 10⁻⁵**;
- positive annual mean IC in **12 of 13** eligible development years;
- 999-permutation symbol-identity placebo p-value **0.001**.

Under corrected arithmetic-return accounting, the diagnostic portfolio earns about **2.34% annualised before costs** and about **0.25% at 5 bps one way**, with annualised turnover about **41.91**. This distinction between *predictability* and *tradability* is a central lesson.

## Code map

| Mathematical task | Python implementation |
|---|---|
| validate OHLCV panel | [validate_panel](../../src/quantlab/data.py) |
| download adjusted OHLCV | [download_yahoo](../../src/quantlab/data.py) |
| construct features | [build_features](../../src/quantlab/features.py) |
| forward log return | [forward_open_return](../../src/quantlab/targets.py) |
| cross-sectional target | [forward_relative_return](../../src/quantlab/targets.py) |
| simple portfolio return | [next_open_to_open_simple_return](../../src/quantlab/targets.py) |
| eligible dates | [eligible_decision_dates](../../src/quantlab/targets.py) |
| purged folds | [PurgedWalkForward](../../src/quantlab/splits.py) |
| modelling frame | [prepare_research_frame](../../src/quantlab/pipeline.py) |
| fold predictions | [walk_forward_predictions](../../src/quantlab/pipeline.py) |
| models | [make_model](../../src/quantlab/models.py) |
| daily rank IC | [rank_ic_by_date](../../src/quantlab/metrics.py) |
| HAC mean test | [hac_mean_test](../../src/quantlab/metrics.py) |
| rank portfolio | [rank_weights](../../src/quantlab/portfolio.py) |
| staggered sleeves | [staggered_weights](../../src/quantlab/backtest.py) |
| backtest | [run_backtest](../../src/quantlab/backtest.py) |
| turnover budget | [turnover_budget_projection](../../src/quantlab/portfolio.py) |
| no-trade band | [no_trade_band_projection](../../src/quantlab/portfolio.py) |
| chronological robustness | [chronological_ic_blocks](../../src/quantlab/robustness.py) |
| permutation placebo | [global_symbol_permutation_test](../../src/quantlab/robustness.py) |
| group diagnostics | [asset_group_diagnostics](../../src/quantlab/robustness.py) |
| group-neutral target | [forward_group_relative_return](../../src/quantlab/targets.py) |

## Reproducibility rule

A reproduction is only valid if it preserves the frozen data, universe, feature definitions, timing, hold-out manifest, purge/embargo rules, model hyperparameters and evaluation rules.

Do not use the final hold-out for experimentation.
