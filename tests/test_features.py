import numpy as np

from quantlab.features import build_features


def test_future_mutation_does_not_change_past_features(synthetic_panel):
    f1 = build_features(synthetic_panel)
    cutoff = synthetic_panel.index.get_level_values("date").unique()[500]
    changed = synthetic_panel.copy()
    future = changed.index.get_level_values("date") > cutoff
    changed.loc[future, "close"] *= 4.0
    changed.loc[future, "high"] *= 4.0
    changed.loc[future, "low"] *= 4.0
    f2 = build_features(changed)
    past1 = f1.loc[f1.index.get_level_values("date") <= cutoff]
    past2 = f2.loc[f2.index.get_level_values("date") <= cutoff]
    assert np.allclose(past1.to_numpy(), past2.to_numpy(), equal_nan=True)
