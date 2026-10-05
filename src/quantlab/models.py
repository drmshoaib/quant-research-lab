from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

V02_BOOSTING_PARAMS = dict(
    learning_rate=0.05,
    max_iter=250,
    max_leaf_nodes=15,
    min_samples_leaf=40,
    l2_regularization=1.0,
)

# v0.3 (EXP-008) Ridge: the penalty is fixed PER OBSERVATION. scikit-learn's Ridge
# minimises ||y - Xb||^2 + alpha ||b||^2 without dividing by n, so a fixed alpha=10 on
# 22,680-113,400 standardised rows shrinks by well under 1% (docs/errata.md, A3). With
# alpha = kappa * n, a direction of the standardised design with correlation-matrix
# eigenvalue lambda is shrunk by the factor lambda / (lambda + kappa), independent of n.
V03_RIDGE_KAPPA = 0.1


class TimeOrderedEarlyStoppingBoosting(BaseEstimator, RegressorMixin):
    """Histogram gradient boosting whose number of trees is chosen on a *chronological* split.

    scikit-learn's built-in early stopping holds out a random fraction of rows,
    which for a panel with overlapping targets is an optimistic validation set
    (rows adjacent in time to the fitted rows). This estimator instead:

    1. splits the training rows by *date*: the last ``validation_fraction`` of
       distinct dates form the validation block, with a purge of ``purge_days``
       dates removed between the two blocks so no validation label overlaps a
       fitted one;
    2. fits ``max_iter`` trees on the earlier block with early stopping off;
    3. walks ``staged_predict`` over the validation block and picks the number of
       trees with the lowest validation MSE, stopping ``patience`` rounds after
       the last improvement (never fewer than ``min_iter`` trees);
    4. refits that many trees on the *whole* training block.

    ``fit`` needs the dates of the rows, passed as ``dates`` (array-like aligned
    with ``X``) or taken from the first level of a MultiIndex on ``X``.
    """

    def __init__(
        self,
        *,
        validation_fraction: float = 0.1,
        purge_days: int = 6,
        patience: int = 10,
        min_iter: int = 10,
        random_state: int = 42,
        **boosting_params,
    ):
        self.validation_fraction = validation_fraction
        self.purge_days = purge_days
        self.patience = patience
        self.min_iter = min_iter
        self.random_state = random_state
        self.boosting_params = {**V02_BOOSTING_PARAMS, **boosting_params}

    def _base(self, max_iter: int) -> HistGradientBoostingRegressor:
        params = {**self.boosting_params, "max_iter": max_iter}
        return HistGradientBoostingRegressor(early_stopping=False, random_state=self.random_state, **params)

    def fit(self, X, y, dates=None):
        if dates is None:
            if not isinstance(X, pd.DataFrame) or not isinstance(X.index, pd.MultiIndex):
                raise ValueError("pass dates= or give X a (date, symbol) MultiIndex")
            dates = X.index.get_level_values(0)
        dates = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates)))
        Xv = np.asarray(X, dtype=float)
        yv = np.asarray(y, dtype=float)
        unique = dates.unique().sort_values()
        n_val = max(1, int(round(self.validation_fraction * len(unique))))
        if len(unique) <= n_val + self.purge_days + 1:
            raise ValueError("not enough distinct dates for a time-ordered validation split")
        val_dates = unique[-n_val:]
        fit_dates = unique[: len(unique) - n_val - self.purge_days]
        fit_mask = dates.isin(fit_dates)
        val_mask = dates.isin(val_dates)

        probe = self._base(self.boosting_params["max_iter"]).fit(Xv[fit_mask], yv[fit_mask])
        best_iter, best_mse, since_best = None, np.inf, 0
        for k, pred in enumerate(probe.staged_predict(Xv[val_mask]), start=1):
            mse = float(np.mean((pred - yv[val_mask]) ** 2))
            if mse < best_mse - 1e-12:
                best_mse, best_iter, since_best = mse, k, 0
            else:
                since_best += 1
            if k >= self.min_iter and since_best >= self.patience:
                break
        self.n_iter_ = int(max(self.min_iter, best_iter or self.min_iter))
        self.validation_mse_ = best_mse
        self.validation_dates_ = val_dates
        self.model_ = self._base(self.n_iter_).fit(Xv, yv)
        return self

    def predict(self, X):
        return self.model_.predict(np.asarray(X, dtype=float))


def make_model(name: str, *, ridge_alpha: float = 10.0, random_state: int = 42, n_train: int | None = None):
    """Model factory.

    Frozen v0.2 names (results in the research note depend on them):
      "ridge"    Pipeline(StandardScaler, Ridge(alpha=ridge_alpha)), alpha fixed at 10.
      "hist_gb"  HistGradientBoostingRegressor with the v0.2 parameters and scikit-learn's
                 default early_stopping="auto" (see the NOTE below).

    v0.3 / EXP-008 names (registered methods experiment; see docs/research_log.md):
      "ridge_v03"        Ridge with alpha = V03_RIDGE_KAPPA * n_train (needs n_train).
      "hist_gb_v03"      the v0.2 boosting parameters with early stopping OFF: exactly
                         max_iter trees, deterministic given the data.
      "hist_gb_v03_time" the v0.2 parameters with TIME-ORDERED early stopping
                         (TimeOrderedEarlyStoppingBoosting), exposing n_iter_.
    """
    if name == "ridge":
        return Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=ridge_alpha))])
    if name == "ridge_v03":
        if n_train is None or n_train < 1:
            raise ValueError("ridge_v03 needs n_train to set alpha = kappa * n_train")
        return Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=V03_RIDGE_KAPPA * n_train))])
    if name == "hist_gb":
        # NOTE (frozen v0.2 behaviour, recorded for transparency): scikit-learn's
        # default early_stopping="auto" switches early stopping ON whenever the
        # training set has more than 10,000 rows, which every development fold
        # does (>= 756 dates x 30 symbols). A random 10% of the training rows is
        # then held out and boosting stops after 10 rounds without improvement,
        # so max_iter=250 is only a ceiling and random_state affects the result.
        # The value is written out explicitly here so the behaviour is visible;
        # changing it would alter the frozen development results and therefore
        # requires a new registered experiment (EXP-008). See docs/errata.md.
        return HistGradientBoostingRegressor(early_stopping="auto", random_state=random_state, **V02_BOOSTING_PARAMS)
    if name == "hist_gb_v03":
        return HistGradientBoostingRegressor(early_stopping=False, random_state=random_state, **V02_BOOSTING_PARAMS)
    if name == "hist_gb_v03_time":
        return TimeOrderedEarlyStoppingBoosting(random_state=random_state)
    raise ValueError(f"unknown model: {name}")


def fitted_n_iter(model) -> int | None:
    """Number of boosting rounds actually fitted, or None for models without one."""
    if isinstance(model, Pipeline):
        model = model.steps[-1][1]
    n = getattr(model, "n_iter_", None)
    return int(n) if n is not None else None


__all__ = [
    "V02_BOOSTING_PARAMS",
    "V03_RIDGE_KAPPA",
    "TimeOrderedEarlyStoppingBoosting",
    "clone",
    "fitted_n_iter",
    "make_model",
]
