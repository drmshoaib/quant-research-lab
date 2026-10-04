import numpy as np
import pandas as pd

from quantlab.signals import causal_rank_ewma


def test_causal_rank_ewma_does_not_use_future_predictions():
    dates = pd.bdate_range("2024-01-01", periods=5)
    symbols = ["A", "B", "C"]
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    base = pd.DataFrame(
        {
            "y_true": np.linspace(-0.1, 0.1, len(idx)),
            "y_pred": np.arange(len(idx), dtype=float),
            "fold": 1,
        },
        index=idx,
    )
    first = causal_rank_ewma(base, span=3)

    changed = base.copy()
    future = changed.index.get_level_values("date") > dates[2]
    changed.loc[future, "y_pred"] *= -100.0
    second = causal_rank_ewma(changed, span=3)

    past = first.index.get_level_values("date") <= dates[2]
    assert np.allclose(
        first.loc[past, "y_pred"].to_numpy(),
        second.loc[past, "y_pred"].to_numpy(),
    )


def test_causal_rank_ewma_preserves_rows():
    dates = pd.bdate_range("2024-01-01", periods=4)
    idx = pd.MultiIndex.from_product([dates, ["A", "B"]], names=["date", "symbol"])
    pred = pd.DataFrame(
        {
            "y_true": np.arange(len(idx), dtype=float),
            "y_pred": [1, 2, 2, 1, 3, 0, 4, -1],
            "fold": 1,
        },
        index=idx,
    )
    out = causal_rank_ewma(pred, span=3)
    assert out.index.equals(pred.index)
    assert list(out.columns) == list(pred.columns)
