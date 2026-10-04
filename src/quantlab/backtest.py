from __future__ import annotations

import pandas as pd

from .portfolio import rank_weights


def weights_from_predictions(
    predictions: pd.DataFrame,
    *,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
) -> pd.Series:
    pieces: list[pd.Series] = []
    for date, g in predictions.groupby(level="date", sort=True):
        scores = g["y_pred"].droplevel("date")
        w = rank_weights(scores, gross_limit=gross_limit, max_abs_weight=max_abs_weight)
        w.index = pd.MultiIndex.from_product([[date], w.index], names=["date", "symbol"])
        pieces.append(w)
    return pd.concat(pieces).sort_index().rename("weight") if pieces else pd.Series(dtype=float, name="weight")


def run_backtest(
    weights: pd.Series,
    realized_returns: pd.Series,
    *,
    cost_bps: float = 5.0,
) -> pd.DataFrame:
    """Backtest next-open-to-open returns with one-way transaction costs."""
    w = weights.unstack("symbol").sort_index().fillna(0.0)
    r = realized_returns.unstack("symbol").reindex(w.index).reindex(columns=w.columns).fillna(0.0)
    gross_ret = (w * r).sum(axis=1)
    turnover = w.diff().abs().sum(axis=1)
    if len(turnover):
        turnover.iloc[0] = w.iloc[0].abs().sum()
    costs = turnover * (cost_bps / 10_000.0)
    out = pd.DataFrame({"gross_return": gross_ret, "turnover": turnover, "cost": costs})
    out["net_return"] = out["gross_return"] - out["cost"]
    return out
