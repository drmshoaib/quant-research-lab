# Part 1 — Data, Returns, Features and Targets

Main implementation:

- [src/quantlab/data.py](../../src/quantlab/data.py)
- [src/quantlab/features.py](../../src/quantlab/features.py)
- [src/quantlab/targets.py](../../src/quantlab/targets.py)
- [scripts/freeze_holdout.py](../../scripts/freeze_holdout.py)

## 1. Panel data

One row represents one asset on one date:

$$
(t,i,O,H,L,C,V).
$$

The Pandas index is the pair $(date,symbol)$. The function [validate_panel](../../src/quantlab/data.py) checks the index, required OHLCV columns, sorting and duplicates.

This matters mathematically because rolling windows and shifts depend on a unique chronological sequence for every symbol.

## 2. Adjusted prices

Splits and distributions can create mechanical price jumps. A 2-for-1 split may change a quoted price from 100 to 50 without a 50% economic loss.

The Yahoo adapter [download_yahoo](../../src/quantlab/data.py) therefore requests adjusted OHLC with auto adjustment enabled.

The research principle is:

> price movements used by features and targets should represent economic return movements, not mechanical corporate-action jumps.

## 3. Simple and log returns

### Simple return

$$
R=\frac{P_1}{P_0}-1.
$$

For 100 to 103:

$$
R=0.03=3\%.
$$

Simple returns are the correct one-period portfolio object:

$$
R_{p,t}=\sum_i w_{i,t}R_{i,t}.
$$

Portfolio P&L therefore uses [next_open_to_open_simple_return](../../src/quantlab/targets.py).

### Log return

$$
r=\log\left(\frac{P_1}{P_0}\right).
$$

For 100 to 103:

$$
r=\log(1.03)\approx0.02956.
$$

For small returns,

$$
\log(1+R)\approx R.
$$

Log returns are time additive:

$$
\log\left(\frac{P_2}{P_0}\right)
=
\log\left(\frac{P_1}{P_0}\right)
+
\log\left(\frac{P_2}{P_1}\right).
$$

The model target and momentum features use log returns; portfolio P&L uses simple returns.

## 4. Decision time and execution time

At decision date $t$, all features use data available by the close of $t$. The earliest assumed execution is the next open $O_{i,t+1}$.

For horizon $h$,

$$
r^{(h)}_{i,t}
=
\log\left(
\frac{O_{i,t+h+1}}{O_{i,t+1}}
\right).
$$

For $h=5$,

$$
r^{(5)}_{i,t}
=
\log\left(
\frac{O_{i,t+6}}{O_{i,t+1}}
\right).
$$

Python: [forward_open_return](../../src/quantlab/targets.py).

This avoids same-close look-ahead.

## 5. Cross-sectional relative-return target

Define the same-date cross-sectional mean

$$
\bar r_t
=
\frac{1}{N_t}
\sum_{j=1}^{N_t}r^{(5)}_{j,t}.
$$

Then

$$
y_{i,t}=r^{(5)}_{i,t}-\bar r_t.
$$

Python: [forward_relative_return](../../src/quantlab/targets.py).

By construction,

$$
\frac{1}{N_t}\sum_i y_{i,t}=0.
$$

Thus the model is asked to predict relative winners and losers, not the overall market direction.

## 6. Group-neutral target

For broad group $g(i)$,

$$
\bar r_{g,t}
=
\frac{1}{N_{g,t}}
\sum_{j\in g}r^{(5)}_{j,t},
$$

and

$$
y^{GN}_{i,t}=r^{(5)}_{i,t}-\bar r_{g(i),t}.
$$

Python:

- [forward_group_relative_return](../../src/quantlab/targets.py)
- [prepare_group_neutral_research_frame](../../src/quantlab/group_neutral.py)

This tests whether predictive ranking survives **within** asset groups after group-level moves are removed.

## 7. Feature mathematics

Features are created in [build_features](../../src/quantlab/features.py).

### 7.1 One-session return

Let $p_{i,t}=\log C_{i,t}$. Then

$$
ret1_{i,t}
=
p_{i,t}-p_{i,t-1}
=
\log\left(\frac{C_{i,t}}{C_{i,t-1}}\right).
$$

### 7.2 Momentum

For window $k$,

$$
mom^{(k)}_{i,t}
=
\log C_{i,t}-\log C_{i,t-k}
=
\log\left(\frac{C_{i,t}}{C_{i,t-k}}\right).
$$

The initial model used $k=5,20,60$. The final pruned8 specification keeps 20 and 60.

### 7.3 Realised volatility

For daily log returns $r$ over a $k$-day window,

$$
\sigma_{k,t}
=
\sqrt{
\frac{1}{k}
\sum_{j=0}^{k-1}(r_{t-j}-\bar r)^2
}.
$$

The code uses population standard deviation inside each rolling window, then annualises:

$$
vol_{k,t}=\sigma_{k,t}\sqrt{252}.
$$

The factor $\sqrt{252}$ follows from variance additivity under the simplifying independent-return approximation.

### 7.4 High-low range

$$
range_{i,t}
=
\frac{H_{i,t}-L_{i,t}}{C_{i,t}}.
$$

Dividing by close makes the feature scale-free.

### 7.5 Volume z-score

First transform volume:

$$
u_{i,t}=\log(1+V_{i,t}).
$$

Then over 20 sessions:

$$
z_{i,t}
=
\frac{u_{i,t}-\mu_{i,t}^{(20)}}
{\sigma_{i,t}^{(20)}}.
$$

A value of 2 means current log-volume is about two recent standard deviations above its rolling mean.

### 7.6 Drawdown

Let

$$
M_{i,t}^{(60)}
=
\max(C_{i,t-59},\ldots,C_{i,t}).
$$

Then

$$
DD_{i,t}
=
\frac{C_{i,t}}{M_{i,t}^{(60)}}-1.
$$

The quantity is non-positive. A value of -0.10 means price is 10% below its 60-session peak.

## 8. Rolling windows and missing values

A 60-session feature cannot exist at the start of a series. The code requires the full rolling window before a feature becomes available.

This creates missing rows, but the hold-out boundary is **not** allowed to depend on those missing feature rows.

## 9. Eligible decision dates

A date is eligible when at least eight assets have observable forward returns.

Let

$$
I_{i,t}
=
\begin{cases}
1,&r^{(h)}_{i,t}\text{ exists},\\
0,&\text{otherwise}.
\end{cases}
$$

Eligibility requires

$$
\sum_i I_{i,t}\ge8.
$$

Python: [eligible_decision_dates](../../src/quantlab/targets.py).

The final 252 eligible dates are frozen by [scripts/freeze_holdout.py](../../scripts/freeze_holdout.py).

## 10. Leakage

Leakage means future information influences training or evaluation.

Examples include using tomorrow's price as a feature, fitting scalers on future test data, allowing overlapping forward labels across train/test boundaries, or moving the hold-out after changing features.

The project addresses leakage through backward-looking features, next-open targets, purging, a pre-hold-out embargo, fold-specific fitting and an immutable hold-out calendar.
