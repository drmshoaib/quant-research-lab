from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def make_model(name: str, *, ridge_alpha: float = 10.0, random_state: int = 42):
    if name == "ridge":
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=ridge_alpha)),
            ]
        )
    if name == "hist_gb":
        # NOTE (frozen v0.2 behaviour, recorded for transparency): scikit-learn's
        # default early_stopping="auto" switches early stopping ON whenever the
        # training set has more than 10,000 rows, which every development fold
        # does (>= 756 dates x 30 symbols). A random 10% of the training rows is
        # then held out and boosting stops after 10 rounds without improvement,
        # so max_iter=250 is only a ceiling and random_state affects the result.
        # The value is written out explicitly here so the behaviour is visible;
        # changing it would alter the frozen development results and therefore
        # requires a new registered experiment. See docs/errata.md.
        return HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=250,
            max_leaf_nodes=15,
            min_samples_leaf=40,
            l2_regularization=1.0,
            early_stopping="auto",
            random_state=random_state,
        )
    raise ValueError(f"unknown model: {name}")
