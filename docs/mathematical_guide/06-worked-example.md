# Part 6 — Worked Example and Exercises

This part uses tiny numbers so the calculations can be checked by hand.

The real project has 30 ETFs, requires at least eight assets for the main IC, and uses 5-session horizons. The small example below uses four assets only to make the arithmetic visible.

## 1. Hypothetical decision date

Suppose that after today's close the model scores four ETFs:

| ETF | Model score |
|---|---:|
| A | 0.80 |
| B | 0.20 |
| C | 0.60 |
| D | 0.40 |

Their score ordering is

$$
A>C>D>B.
$$

## 2. A feature calculation

Suppose ETF A had adjusted close

$$
C_{A,t-20}=100,
\qquad
C_{A,t}=105.
$$

Its 20-session log momentum is

$$
mom20
=
\log(105)-\log(100)
=
\log(1.05)
\approx0.04879.
$$

That is approximately a 4.88% continuously compounded move.

Python analogue: [build_features](../../src/quantlab/features.py).

### Drawdown example

Suppose A's highest close in the last 60 sessions is 112.

Then

$$
drawdown60
=
\frac{105}{112}-1
\approx-0.0625.
$$

So A is 6.25% below its 60-session peak.

## 3. Five-session forward return

Suppose A enters next open at

$$
O_{A,t+1}=106
$$

and exits five sessions later at

$$
O_{A,t+6}=110.
$$

Then its raw target is

$$
r^{(5)}_{A,t}
=
\log\left(\frac{110}{106}\right)
\approx0.03704.
$$

The same calculation is done for every ETF.

Suppose raw forward log returns are:

| ETF | Raw forward log return |
|---|---:|
| A | 0.040 |
| B | -0.020 |
| C | 0.010 |
| D | -0.010 |

The cross-sectional mean is

$$
\bar r
=
\frac{0.040-0.020+0.010-0.010}{4}
=
0.005.
$$

Therefore relative targets are:

$$
y_A=0.040-0.005=0.035,
$$

$$
y_B=-0.020-0.005=-0.025,
$$

$$
y_C=0.010-0.005=0.005,
$$

$$
y_D=-0.010-0.005=-0.015.
$$

Table:

| ETF | Relative target |
|---|---:|
| A | 0.035 |
| B | -0.025 |
| C | 0.005 |
| D | -0.015 |

Their realised ordering is

$$
A>C>D>B.
$$

It exactly matches the model ordering.

## 4. Spearman IC by hand

Score ranks:

| ETF | Score rank |
|---|---:|
| A | 4 |
| B | 1 |
| C | 3 |
| D | 2 |

Target ranks are identical:

| ETF | Target rank |
|---|---:|
| A | 4 |
| B | 1 |
| C | 3 |
| D | 2 |

Therefore

$$
IC_t=1.
$$

### A less perfect example

Suppose realised ordering were

$$
A>D>C>B,
$$

with target ranks

$$
(4,1,2,3).
$$

Score ranks remain

$$
(4,1,3,2).
$$

Both rank vectors have mean

$$
\bar R=\bar S=2.5.
$$

Centred score ranks:

$$
(1.5,-1.5,0.5,-0.5).
$$

Centred target ranks:

$$
(1.5,-1.5,-0.5,0.5).
$$

Numerator:

$$
1.5(1.5)+(-1.5)(-1.5)+(0.5)(-0.5)+(-0.5)(0.5)
=4.
$$

Each sum of squared centred ranks is

$$
1.5^2+1.5^2+0.5^2+0.5^2=5.
$$

Thus

$$
IC_t
=
\frac{4}{\sqrt5\sqrt5}
=
0.8.
$$

So one local ranking mistake reduces IC from 1 to 0.8.

## 5. Rank portfolio by hand

For illustration, use a generous per-name cap of 0.5 rather than the project's real 0.08 cap.

Percentile ranks for the scores are

$$
q=(1.00,0.25,0.75,0.50).
$$

Subtract 0.5:

$$
q-0.5
=
(0.50,-0.25,0.25,0).
$$

Their mean is

$$
0.125.
$$

Re-centre:

$$
w^{raw}
=
(0.375,-0.375,0.125,-0.125).
$$

Check dollar neutrality:

$$
0.375-0.375+0.125-0.125=0.
$$

Check gross:

$$
|0.375|+|{-0.375}|+|0.125|+|{-0.125}|=1.
$$

So these are already unit-gross weights.

The real [rank_weights](../../src/quantlab/portfolio.py) additionally applies the 0.08 name cap.

## 6. One-period portfolio return

Suppose next-open-to-next-open simple returns are:

| ETF | Simple return |
|---|---:|
| A | +1.0% |
| B | -0.5% |
| C | +0.2% |
| D | +0.1% |

In decimals:

$$
R=(0.010,-0.005,0.002,0.001).
$$

Gross portfolio return is

$$
R_p
=
0.375(0.010)
+
(-0.375)(-0.005)
+
0.125(0.002)
+
(-0.125)(0.001).
$$

Calculate each contribution:

$$
0.00375+0.001875+0.00025-0.000125
=
0.00575.
$$

Thus

$$
R_p=0.575\%.
$$

Notice that short B makes money because B's return is negative.

## 7. Transaction cost by hand

Suppose this is the first day, so previous weights are zero.

Turnover is

$$
TO
=
\sum_i|w_i-0|
=1.
$$

At 5 bps,

$$
c=5/10000=0.0005.
$$

Cost is

$$
Cost=0.0005(1)=0.0005=0.05\%.
$$

Net return:

$$
R^{net}
=
0.00575-0.0005
=
0.00525.
$$

So net return is

$$
0.525\%.
$$

Python analogue: [run_backtest](../../src/quantlab/backtest.py).

## 8. Why portfolio turnover can be large

Suppose tomorrow the desired weights reverse:

$$
w_{t+1}
=
(-0.375,0.375,-0.125,0.125).
$$

Then turnover is

$$
|{-0.375}-0.375|
+
|0.375-(-0.375)|
+
|{-0.125}-0.125|
+
|0.125-(-0.125)|.
$$

Therefore

$$
TO=0.75+0.75+0.25+0.25=2.
$$

A complete long-to-short reversal can generate turnover greater than gross exposure.

That is why apparently modest daily re-ranking can create very high annualised turnover.

## 9. Staggered sleeves by hand

Suppose, for illustration, the horizon is five sessions and each day's desired cohort is the same vector $c$.

Each cohort receives one-fifth capital.

After the first signal date:

$$
W_1=\frac15c.
$$

After the second:

$$
W_2=\frac15(c+c)=\frac25c.
$$

Then

$$
W_3=\frac35c,
\qquad
W_4=\frac45c,
\qquad
W_5=c.
$$

After steady state, the oldest sleeve expires when the newest enters.

If cohort weights differ through time,

$$
W_t
=
\frac15
(c_t+c_{t-1}+c_{t-2}+c_{t-3}+c_{t-4}).
$$

Python: [staggered_weights](../../src/quantlab/backtest.py).

## 10. HAC intuition with overlapping returns

Imagine daily ICs:

$$
0.10,0.08,0.09,0.07,0.11,\ldots
$$

If nearby observations are positively correlated, five consecutive positive values carry less independent information than five independent coin flips.

A naive standard error treats them as more independent than they really are.

Newey-West adjusts the variance estimate using lagged autocovariances.

You can think of it as saying:

> repeated nearby evidence should not be counted as if every observation were completely new information.

## 11. Benjamini-Hochberg worked example

Suppose five tests produce sorted p-values:

$$
0.005,\ 0.018,\ 0.040,\ 0.12,\ 0.40.
$$

Let

$$
q=0.10,\qquad m=5.
$$

BH thresholds are

$$
\frac15(0.10)=0.02,
$$

$$
\frac25(0.10)=0.04,
$$

$$
\frac35(0.10)=0.06,
$$

$$
\frac45(0.10)=0.08,
$$

$$
\frac55(0.10)=0.10.
$$

Compare:

- 0.005 ≤ 0.02: yes;
- 0.018 ≤ 0.04: yes;
- 0.040 ≤ 0.06: yes;
- 0.12 ≤ 0.08: no;
- 0.40 ≤ 0.10: no.

Largest passing rank is 3, so the first three hypotheses are rejected under BH FDR control.

## 12. Permutation p-value worked example

Suppose an observed mean IC is 0.03.

Run 999 valid symbol permutations.

Assume only two permuted mean ICs are at least 0.03.

Then

$$
p_{perm}
=
\frac{1+2}{999+1}
=
0.003.
$$

The plus-one correction prevents a reported p-value of zero.

## 13. Turnover-budget optimisation intuition

Suppose yesterday's portfolio is

$$
w^{-}=(0.3,-0.3,0,0)
$$

and today's desired target is

$$
w^*=(0,0,0.3,-0.3).
$$

Full turnover would be

$$
|0-0.3|
+
|0-(-0.3)|
+
|0.3-0|
+
|-0.3-0|
=
1.2.
$$

If the budget is

$$
B=0.4,
$$

the optimiser cannot reach the target.

It instead chooses the feasible $w$ closest to $w^*$ while requiring

$$
\|w-w^{-}\|_1\le0.4.
$$

This is the mathematical meaning of “trade toward the target subject to a turnover budget.”

## 14. No-trade band intuition

Suppose current weights are

$$
w^{-}=(0.10,-0.10,0.05,-0.05)
$$

and target is

$$
w^*=(0.103,-0.106,0.070,-0.067).
$$

Changes are

$$
\Delta=(0.003,-0.006,0.020,-0.017).
$$

With band

$$
b=0.005,
$$

the first change is ignored because

$$
0.003\le0.005.
$$

The other three become active.

This prevents very small trades from being executed merely to track the target exactly.

## 15. Ridge regression exercise

Consider

$$
X=
\begin{bmatrix}
1\\
2\\
3
\end{bmatrix},
\qquad
y=
\begin{bmatrix}
1\\
2\\
2
\end{bmatrix}.
$$

Ignoring the intercept and using $\alpha=1$,

$$
\hat\beta
=
(X^TX+\alpha)^{-1}X^Ty.
$$

Compute:

$$
X^TX=1^2+2^2+3^2=14,
$$

$$
X^Ty=1(1)+2(2)+3(2)=11.
$$

Therefore

$$
\hat\beta
=
\frac{11}{15}
\approx0.7333.
$$

Without Ridge penalty,

$$
\hat\beta_{OLS}
=
\frac{11}{14}
\approx0.7857.
$$

The Ridge coefficient is smaller: this is shrinkage.

## 16. Exercises

### Exercise 1 — log versus simple returns

A price moves 50 → 52 → 51.

1. Calculate both simple one-period returns.
2. Calculate both log returns.
3. Verify that the two log returns add to $\log(51/50)$.
4. Verify that the simple returns do not simply add to the two-period simple return.

### Exercise 2 — relative target

Four forward log returns are

$$
0.03,\ 0.01,\ -0.02,\ 0.00.
$$

Calculate the cross-sectional mean and all four relative targets. Verify that their mean is zero.

### Exercise 3 — drawdown

An ETF's 60-session maximum close is 240 and current close is 210.

Compute drawdown.

### Exercise 4 — annualised volatility

Suppose daily volatility is 1.2%.

Compute the conventional annualised volatility using 252 trading days.

### Exercise 5 — Spearman IC

Model ranks are

$$
(1,2,3,4,5)
$$

and realised ranks are

$$
(2,1,3,5,4).
$$

Calculate Spearman correlation as Pearson correlation of these rank vectors.

### Exercise 6 — costs

A portfolio has annualised zero-cost arithmetic return 3% and annualised turnover 50.

What one-way cost in basis points approximately makes expected annualised net return zero?

Use

$$
b^*
=
10000\frac{0.03}{50}.
$$

### Exercise 7 — purge reasoning

Draw the price dates used by a five-session target attached to decision date $t$.

Then explain why training observations immediately before a test block can overlap the test outcome path.

### Exercise 8 — research discipline

A pre-registered rule says a candidate passes if retention is at least 80%.

You observe 79.97%.

Should you:

A. round to 80% and pass it;  
B. change the threshold to 79%;  
C. record a failure and discuss that it was a near miss?

The project chooses C.

## 17. Final conceptual checklist

An undergraduate who understands this project should be able to explain:

1. why next-open timing is used;
2. the difference between simple and log returns;
3. every frozen feature formula;
4. why the target is cross-sectionally centred;
5. Ridge regression and L2 shrinkage;
6. the intuition of gradient-boosted trees;
7. why random cross-validation is invalid;
8. why purging and embargoes are needed;
9. Spearman rank IC;
10. why HAC inference is used;
11. how BH controls multiple testing;
12. how the permutation placebo works;
13. dollar neutrality and gross exposure;
14. staggered sleeves;
15. turnover and transaction costs;
16. Sharpe ratio and drawdown;
17. turnover-budget and no-trade-band optimisation;
18. why a statistically significant signal may still be economically unattractive;
19. why negative experiments must remain in the record;
20. why the untouched hold-out should be opened only once.

If you can derive the equations, trace the linked functions and reproduce the development outputs, you understand the mathematical core of the Quant Research Lab.
