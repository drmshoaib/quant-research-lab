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
        return HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_iter=250,
            max_leaf_nodes=15,
            min_samples_leaf=40,
            l2_regularization=1.0,
            random_state=random_state,
        )
    raise ValueError(f"unknown model: {name}")
