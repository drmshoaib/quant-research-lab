# Part 4 — Portfolio Mathematics, Costs and Execution Controls

Main implementation:

- [src/quantlab/portfolio.py](../../src/quantlab/portfolio.py)
- [src/quantlab/backtest.py](../../src/quantlab/backtest.py)
- [src/quantlab/signals.py](../../src/quantlab/signals.py)
- [src/quantlab/metrics.py](../../src/quantlab/metrics.py)
- [scripts/run_exp004.py](../../scripts/run_exp004.py)
- [scripts/run_exp005.py](../../scripts/run_exp005.py)

The portfolio is deliberately a **secondary diagnostic**. The primary research question concerns predictive ranking.

## 1. From scores to percentile ranks

Python: [rank_weights](../../src/quantlab/portfolio.py).

Suppose the model predicts scores

$$
s_1,\ldots,s_N.
$$

Convert them to percentile ranks $q_i\in(0,1]$.

The code centres those ranks:

$$
r_i=q_i-0.5.
$$

It then removes any residual mean:

$$
\tilde r_i
=
r_i-\bar r.
$$

Assets with high scores receive positive values, low scores negative values.

## 2. Dollar neutrality

A portfolio is dollar neutral if

$$
\sum_i w_i=0.
$$

Positive weights are longs and negative weights are shorts.

Example:

$$
w=(0.25,0.25,-0.20,-0.30)
$$

has

$$
\sum_i w_i=0.
$$

Dollar neutrality removes net capital direction, but it does **not** guarantee market-beta neutrality, duration neutrality or equal risk.

## 3. Gross exposure

Gross exposure is

$$
G=\sum_i|w_i|.
$$

The benchmark limit is

$$
G\le1.
$$

If longs total +0.5 and shorts total -0.5, gross exposure is

$$
0.5+0.5=1.
$$

The rank weights are scaled so their L1 norm reaches the gross limit when possible.

## 4. Per-name weight cap

Each asset satisfies

$$
|w_i|\le0.08.
$$

This prevents one ETF from dominating a cohort.

The code clips weights, recentres them and, if required, rescales gross exposure again.

## 5. A five-session forecast cannot be backtested as a one-day strategy

The target predicts return from

$$
O_{t+1}
\quad\text{to}\quad
O_{t+6}.
$$

If the portfolio were discarded after one day, its holding period would not match the target.

The solution is a **staggered sleeve portfolio**.

Python: [staggered_weights](../../src/quantlab/backtest.py).

## 6. Cohorts and staggered sleeves

Let $c_t$ be the cohort portfolio produced from the signal at decision date $t$.

For horizon $h=5$, each cohort contributes one-fifth of portfolio capital for five one-session periods.

The live portfolio is approximately

$$
W_t
=
\frac{1}{5}
(
c_t+c_{t-1}+c_{t-2}+c_{t-3}+c_{t-4}
).
$$

More generally,

$$
W_t
=
\frac{1}{h}
\sum_{k=0}^{h-1}c_{t-k}.
$$

This is exactly what the rolling-sum logic in [staggered_weights](../../src/quantlab/backtest.py) implements.

At the beginning, fewer than five cohorts exist, so unused sleeves are effectively cash. After five signal dates, the portfolio reaches steady state.

## 7. Realised one-session arithmetic return

For an asset held from the next open to the following open,

$$
R_{i,t}
=
\frac{O_{i,t+2}}{O_{i,t+1}}-1.
$$

Python: [next_open_to_open_simple_return](../../src/quantlab/targets.py).

The portfolio gross return is

$$
R^{gross}_{p,t}
=
\sum_i w_{i,t}R_{i,t}.
$$

This is why the backtest must use **simple**, not log, returns.

## 8. Why log returns cannot simply be weighted as portfolio returns

For one asset,

$$
r_i=\log(1+R_i).
$$

But in general,

$$
\sum_i w_i\log(1+R_i)
\neq
\log\left(1+\sum_i w_iR_i\right).
$$

The weighted sum of asset log returns is therefore not the exact log return of a rebalanced portfolio.

The repository corrected this issue before any hold-out evaluation. See [accounting_correction.md](../accounting_correction.md).

## 9. Turnover

One-way traded notional is measured by the L1 change in weights:

$$
TO_t
=
\sum_i
|w_{i,t}-w_{i,t-1}|.
$$

If a weight changes from +0.05 to -0.05, traded notional is

$$
|-0.05-0.05|=0.10.
$$

That correctly counts selling the existing 0.05 long and establishing a 0.05 short.

Python: [run_backtest](../../src/quantlab/backtest.py).

## 10. Initial entry and terminal liquidation

On the first portfolio date, previous weight is zero, so initial turnover is

$$
TO_1=\sum_i|w_{i,1}|.
$$

At the end, a realistic accounting must also liquidate the portfolio to zero:

$$
TO_{exit}
=
\sum_i|0-w_{i,T}|.
$$

Python: [append_liquidation_row](../../src/quantlab/backtest.py).

The accounting audit standardised this exit cost across experiments.

## 11. Transaction costs

If one-way cost is $b$ basis points, then

$$
c=\frac{b}{10000}.
$$

At 5 bps,

$$
c=0.0005.
$$

Daily cost is

$$
Cost_t
=
c\,TO_t.
$$

Net return is

$$
R^{net}_{p,t}
=
R^{gross}_{p,t}-Cost_t.
$$

This cost model is intentionally simple. It does not model instrument-specific spreads, market impact or borrow.

## 12. Annualised turnover

Average daily turnover is

$$
\overline{TO}
=
\frac1T\sum_t TO_t.
$$

The code annualises by

$$
TO_{ann}=252\,\overline{TO}.
$$

A value of 41.91 means annual traded notional is about 41.91 times one unit of gross portfolio capital under this convention.

## 13. Annualised arithmetic return

The summary reports

$$
\mu_{ann}
=
252\,\bar R,
$$

where

$$
\bar R
=
\frac1T\sum_tR_t.
$$

This is an annualised **arithmetic mean return**, not a compounded CAGR.

That distinction should be stated whenever the number is presented.

## 14. Annualised volatility

Let daily return standard deviation be $s_R$. Then

$$
\sigma_{ann}
=
s_R\sqrt{252}.
$$

Again, this square-root scaling is a standard convention based on weak dependence / constant-variance approximations.

## 15. Sharpe ratio

With no risk-free adjustment in this research diagnostic,

$$
Sharpe
=
\frac{\mu_{ann}}{\sigma_{ann}}.
$$

Python: [backtest_summary](../../src/quantlab/metrics.py).

At 5 bps, corrected pruned8 Sharpe is only about 0.065. This is economically weak even though IC is statistically significant.

## 16. Equity curve

Because daily portfolio returns are simple returns,

$$
Equity_t
=
\prod_{s\le t}(1+R^{net}_{p,s}).
$$

Python uses cumulative product in [backtest_summary](../../src/quantlab/metrics.py).

## 17. Drawdown

Running peak equity is

$$
M_t=\max_{s\le t}Equity_s.
$$

Drawdown is

$$
DD_t
=
\frac{Equity_t}{M_t}-1.
$$

Maximum drawdown is

$$
MDD=\min_t DD_t.
$$

If equity falls from 1.20 to 0.96,

$$
DD=0.96/1.20-1=-0.20.
$$

That is a 20% drawdown.

## 18. Break-even transaction cost

Because the cost model is linear in turnover and the project annualises the arithmetic mean of daily returns, the relation is exact rather than approximate:

$$
R^{net}_{ann}
=
R^{gross}_{ann}
-
c\,TO_{ann}.
$$

(It would be approximate only for a compound-growth measure of return.)

Set net return to zero:

$$
0=
R^{gross}_{ann}
-
c^*TO_{ann}.
$$

Then

$$
c^*
=
\frac{R^{gross}_{ann}}{TO_{ann}}.
$$

Convert to basis points:

$$
b^*
=
10000
\frac{R^{gross}_{ann}}{TO_{ann}}.
$$

Using corrected pruned8 values,

$$
R^{gross}_{ann}\approx0.023444,
\qquad
TO_{ann}\approx41.912,
$$

so

$$
b^*
\approx
10000\frac{0.023444}{41.912}
\approx5.59\text{ bps}.
$$

This shows how narrow the economic margin is.

## 19. EWMA score smoothing

Python: [causal_rank_ewma](../../src/quantlab/signals.py).

First convert daily scores to centred percentile ranks. Then for each symbol apply an exponentially weighted moving average.

A standard EWMA recursion is

$$
z_t
=
\alpha x_t+(1-\alpha)z_{t-1},
$$

with

$$
\alpha
=
\frac{2}{span+1}.
$$

Longer span means smaller $\alpha$, therefore slower score changes.

The hope is to reduce portfolio turnover.

The risk is signal delay: if the forecast changes genuinely, smoothing can keep yesterday's view for too long.

EXP-002 found that turnover reduction came with too much loss of gross return.

## 20. Partial adjustment of portfolio weights

Python: [partial_adjustment_weights](../../src/quantlab/backtest.py).

Let $w_t^*$ be the target portfolio and $w_{t-1}$ the current portfolio.

The actual portfolio moves only a fraction $\lambda$ toward target:

$$
w_t
=
(1-\lambda)w_{t-1}
+
\lambda w_t^*.
$$

If $\lambda=1$, execution is instant.

If $\lambda=0.5$, only half the desired move is taken each date.

This is a simple low-pass filter on portfolio weights.

EXP-003 showed that reduced turnover did not preserve enough gross alpha.

## 21. Turnover-budget projection

Python:

- [turnover_budget_projection](../../src/quantlab/portfolio.py)
- [turnover_budget_path](../../src/quantlab/portfolio.py)
- [scripts/run_exp004.py](../../scripts/run_exp004.py)

Let $w^*$ be today's desired target and $w^{-}$ yesterday's actual portfolio.

The optimisation solves approximately

$$
\min_w
\|w-w^*\|_2^2
$$

subject to

$$
\sum_i w_i=0,
$$

$$
\sum_i|w_i|\le G,
$$

$$
|w_i|\le m,
$$

and

$$
\sum_i|w_i-w_i^{-}|
\le B,
$$

where

- $G=1$ gross limit;
- $m=0.08$ name cap;
- $B$ is the daily turnover budget.

Interpretation:

> find the feasible portfolio closest in Euclidean distance to the desired target, without trading more than the allowed budget.

### 21.1 Why auxiliary variables are introduced

Absolute values are awkward for smooth optimisation.

For turnover, introduce $u_i$ such that

$$
u_i\ge w_i-w_i^{-},
$$

$$
u_i\ge-(w_i-w_i^{-}),
$$

$$
u_i\ge0.
$$

Then

$$
u_i\ge|w_i-w_i^{-}|.
$$

Impose

$$
\sum_i u_i\le B.
$$

Similarly introduce gross auxiliaries $g_i$ satisfying

$$
g_i\ge|w_i|
$$

and

$$
\sum_i g_i\le G.
$$

This converts the absolute-value constraints into linear inequalities.

The code solves the smooth quadratic problem with SLSQP.

## 22. SLSQP in plain language

SLSQP stands for Sequential Least Squares Programming.

It repeatedly approximates a constrained nonlinear problem by easier quadratic subproblems and moves toward a solution satisfying:

- the objective;
- equality constraints;
- inequality constraints;
- bounds.

The repository checks feasibility after optimisation and has a proportional fallback if the numerical solver fails.

This is important engineering: optimisation code must verify the answer rather than trust a success flag blindly.

## 23. No-trade band

Python:

- [no_trade_band_projection](../../src/quantlab/portfolio.py)
- [no_trade_band_path](../../src/quantlab/portfolio.py)
- [scripts/run_exp005.py](../../scripts/run_exp005.py)

Let

$$
\Delta_i
=
w_i^*-w_i^{-}.
$$

If

$$
|\Delta_i|\le b,
$$

where $b$ is the no-trade band, leave the asset unchanged.

Only sufficiently large desired changes become active.

The idea is that tiny position changes may not justify trading costs.

The active weights are optimised subject to neutrality, gross and name constraints, without overshooting the desired direction.

## 24. General alpha-risk-turnover optimisation

The repository also implements [optimise_weights](../../src/quantlab/portfolio.py), although it was deliberately not used as the primary v0.2 benchmark.

The conceptual objective is

$$
\max_w
\left[
\alpha^Tw
-
\lambda w^T\Sigma w
-
\gamma\|w-w^{-}\|_1
\right].
$$

Terms:

### Expected alpha

$$
\alpha^Tw
$$

rewards exposure to predicted returns.

### Risk penalty

$$
w^T\Sigma w
$$

is portfolio variance if $\Sigma$ is the return covariance matrix.

### Turnover penalty

$$
\|w-w^{-}\|_1
=
\sum_i|w_i-w_i^{-}|
$$

discourages expensive trading.

The coefficients $\lambda$ and $\gamma$ control the trade-off.

This is closer to an institutional portfolio-construction problem, but introducing it during signal discovery would mix forecasting research with optimisation tuning. The project therefore deferred it.

## 25. Why the portfolio is not called a final strategy

The benchmark portfolio is:

- dollar neutral;
- gross constrained;
- name capped.

It is **not** explicitly:

- beta neutral;
- duration neutral;
- volatility scaled;
- factor neutral;
- spread aware;
- market-impact aware;
- borrow constrained.

Therefore the portfolio is best interpreted as a diagnostic translation of ranking skill into economic returns, not a production-ready trading strategy.
