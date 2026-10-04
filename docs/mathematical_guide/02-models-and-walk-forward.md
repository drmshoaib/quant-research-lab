# Part 2 — Models and Walk-Forward Learning

Main implementation:

- [src/quantlab/models.py](../../src/quantlab/models.py)
- [src/quantlab/pipeline.py](../../src/quantlab/pipeline.py)
- [src/quantlab/splits.py](../../src/quantlab/splits.py)

## 1. Supervised regression

Each observation is

$$
(x_{i,t},y_{i,t}),
$$

where $x_{i,t}\in\mathbb{R}^p$ is the feature vector and $y_{i,t}$ is the future relative-return target.

Collect training observations into

$$
X\in\mathbb{R}^{n\times p},
\qquad
y\in\mathbb{R}^{n}.
$$

We seek a function

$$
\hat y=f(x)
$$

that generalises to later dates.

## 2. Ridge regression

Python: [make_model](../../src/quantlab/models.py), Ridge branch.

Ordinary least squares minimises

$$
\|y-X\beta\|_2^2.
$$

Ridge adds an L2 penalty:

$$
\min_\beta
\left[
\|y-X\beta\|_2^2
+
\alpha\|\beta\|_2^2
\right].
$$

The project fixes

$$
\alpha=10.
$$

Ignoring intercept details, the closed-form solution is

$$
\hat\beta
=
(X^TX+\alpha I)^{-1}X^Ty.
$$

The term $\alpha I$ stabilises the inverse and shrinks coefficients toward zero.

## 3. Standardisation

Ridge is wrapped in StandardScaler.

For feature $j$,

$$
z_{ij}
=
\frac{x_{ij}-\mu_j}{s_j}.
$$

Scaling matters because the L2 penalty acts on coefficient magnitude. The scaler is fitted only on each training fold because it is inside the scikit-learn pipeline.

## 4. Regression trees

A regression tree repeatedly divides the feature space.

If a node contains observations $S$, its squared error is

$$
SSE(S)
=
\sum_{j\in S}(y_j-\bar y_S)^2.
$$

A split creates $S_L$ and $S_R$. Its improvement is

$$
\Delta
=
SSE(S)-SSE(S_L)-SSE(S_R).
$$

Each terminal leaf predicts its mean target.

Trees can express nonlinear rules and interactions such as:

> high volatility plus deep drawdown behaves differently from high volatility near a recent peak.

## 5. Gradient boosting

The project uses HistGradientBoostingRegressor.

Boosting builds

$$
F_M(x)
=
F_0(x)+\eta\sum_{m=1}^{M}f_m(x),
$$

where each $f_m$ is a small regression tree.

For squared-error loss

$$
L(y,F)=\frac12(y-F)^2,
$$

the negative gradient is

$$
-\frac{\partial L}{\partial F}
=
y-F.
$$

Thus each new tree approximately fits the current residuals.

The update is

$$
F_m(x)
=
F_{m-1}(x)+\eta f_m(x).
$$

Frozen parameters:

- learning rate $\eta=0.05$;
- maximum iterations $M=250$;
- maximum leaf nodes 15;
- minimum samples per leaf 40;
- L2 regularisation 1;
- random seed 42.

Python: [make_model](../../src/quantlab/models.py).

## 6. Histogram idea

Histogram boosting groups continuous feature values into bins, then searches split points between bins rather than every unique value.

This greatly reduces the computational cost of split search on large datasets.

The exact binning algorithm is supplied by scikit-learn; the research code freezes its model configuration.

## 7. Why compare linear and nonlinear models?

Ridge asks whether a stable linear combination of features is enough.

HistGradientBoosting can learn thresholds and interactions.

EXP-001 found Ridge weak and statistically insignificant while the nonlinear model produced materially positive rank IC. This suggests the predictive relation is not well represented by a simple fixed linear map.

## 8. Why avoid a giant model search?

Trying hundreds of algorithms and hyperparameter combinations creates a selection problem: the best development result may simply be the luckiest.

The project deliberately used a limited model comparison and fixed nonlinear hyperparameters. That reduces researcher degrees of freedom.

## 9. Why random train/test splitting is invalid here

A random split could train on 2024 and test on 2018. A trading system cannot learn from the future.

The project therefore uses expanding walk-forward validation.

Python:

- [PurgedWalkForward](../../src/quantlab/splits.py)
- [walk_forward_predictions](../../src/quantlab/pipeline.py)

## 10. Expanding walk-forward validation

Let ordered decision dates be

$$
d_1,d_2,\ldots,d_T.
$$

The first fold conceptually looks like

$$
\underbrace{d_1,\ldots,d_{756}}_{training}
\quad
\underbrace{d_{757},\ldots,d_{762}}_{purge}
\quad
\underbrace{d_{763},\ldots,d_{825}}_{test}.
$$

The test block has 63 dates. The next fold advances 63 dates while the training set expands.

Parameters:

$$
minTrain=756,\qquad test=63,\qquad step=63.
$$

## 11. Why purge $h+1$ dates?

For $h=5$,

$$
y_t=
\log\left(\frac{O_{t+6}}{O_{t+1}}\right).
$$

A training label close to the test boundary may use prices from the future test period.

The splitter therefore uses

$$
purge=h+1=6.
$$

Python: [walk_forward_predictions](../../src/quantlab/pipeline.py).

## 12. Pre-hold-out embargo

The same overlap problem occurs before the final hold-out.

The project uses

$$
development
\quad|\quad
6\text{-date embargo}
\quad|\quad
252\text{-date hold-out}.
$$

Python: [prepare_research_frame](../../src/quantlab/pipeline.py).

This protects not only the hold-out decision rows but also their future outcome path.

## 13. Feature-independent hold-out

The hold-out is frozen from the market-data/target calendar before feature missingness is considered.

The logic is:

1. create eligible target dates;
2. freeze the final 252;
3. create features;
4. drop missing feature rows;
5. intersect remaining rows with the already-fixed development calendar.

Therefore changing a feature cannot silently move the final hold-out.

## 14. Fold-by-fold fitting

For each fold:

1. select training dates;
2. select later test dates;
3. create a fresh model;
4. fit on training observations only;
5. predict test rows;
6. store truth, score and fold number.

Python: [walk_forward_predictions](../../src/quantlab/pipeline.py).

## 15. Scores rather than calibrated return forecasts

The final evaluation is based on ranks.

Predictions

$$
(0.001,0.002,0.003)
$$

and

$$
(1,2,3)
$$

produce the same ranking. For this project, that ordering is more important than exact return magnitude.

Part 3 explains how those rankings are evaluated statistically.
