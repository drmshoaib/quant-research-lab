import numpy as np
import pandas as pd

from quantlab.features import FEATURE_COLUMNS, build_features

FIELDS = ["open", "high", "low", "close", "volume"]


def _perturb_future(panel: pd.DataFrame, cutoff, seed: int) -> pd.DataFrame:
    """Multiply every field of every future bar by an independent random factor.

    Independent factors per row and per field are needed so that leaks which a
    common factor would hide are also caught: a scale-invariant quantity such
    as (high - low) / close, a quantity built only from opens or volume, and a
    cross-sectionally demeaned quantity (a common factor cancels in all three).
    """
    rng = np.random.default_rng(seed)
    changed = panel.copy()
    changed[FIELDS] = changed[FIELDS].astype(float)
    future = changed.index.get_level_values("date") > cutoff
    n = int(future.sum())
    for field in FIELDS:
        changed.loc[future, field] = changed.loc[future, field] * rng.uniform(0.5, 2.0, n)
    # Keep the bars internally consistent so the perturbed panel is still valid data.
    body_hi = np.maximum(changed["open"], changed["close"])
    body_lo = np.minimum(changed["open"], changed["close"])
    changed["high"] = np.maximum(changed["high"], body_hi)
    changed["low"] = np.minimum(changed["low"], body_lo)
    return changed


def test_future_mutation_does_not_change_past_features(synthetic_panel):
    f1 = build_features(synthetic_panel)
    dates = synthetic_panel.index.get_level_values("date").unique()
    for k, cutoff in enumerate(dates[[150, 500, 900]]):
        changed = _perturb_future(synthetic_panel, cutoff, seed=k)
        f2 = build_features(changed)
        past1 = f1.loc[f1.index.get_level_values("date") <= cutoff]
        past2 = f2.loc[f2.index.get_level_values("date") <= cutoff]
        assert np.allclose(past1.to_numpy(), past2.to_numpy(), equal_nan=True)


def test_perturbation_check_catches_a_leaky_feature(synthetic_panel):
    """The causality check must have teeth: a feature that peeks one day ahead fails it."""

    def leaky_features(panel: pd.DataFrame) -> pd.DataFrame:
        f = build_features(panel).copy()
        rel = panel["high"] / panel["close"] - 1.0  # scale-invariant leak
        f["leak"] = rel.groupby(level="symbol").shift(-1)
        return f

    cutoff = synthetic_panel.index.get_level_values("date").unique()[500]
    f1 = leaky_features(synthetic_panel)
    f2 = leaky_features(_perturb_future(synthetic_panel, cutoff, seed=0))
    past1 = f1.loc[f1.index.get_level_values("date") <= cutoff]
    past2 = f2.loc[f2.index.get_level_values("date") <= cutoff]
    assert np.allclose(past1[FEATURE_COLUMNS].to_numpy(), past2[FEATURE_COLUMNS].to_numpy(), equal_nan=True)
    assert not np.allclose(past1["leak"].to_numpy(), past2["leak"].to_numpy(), equal_nan=True)
