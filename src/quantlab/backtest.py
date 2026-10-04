from __future__ import annotations

import pandas as pd

from .portfolio import rank_weights


def weights_from_predictions(
    predictions: pd.DataFrame,
    *,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
) -> pd.Series:
    """Convert each decision date's scores into one cohort portfolio."""
    pieces: list[pd.Series] = []
    for date, g in predictions.groupby(level="date", sort=True):
        scores = g["y_pred"].droplevel("date")
        w = rank_weights(scores, gross_limit=gross_limit, max_abs_weight=max_abs_weight)
        w.index = pd.MultiIndex.from_product([[date], w.index], names=["date", "symbol"])
        pieces.append(w)
    return pd.concat(pieces).sort_index().rename("weight") if pieces else pd.Series(dtype=float, name="weight")


def staggered_weights(
    cohort_weights: pd.Series,
    *,
    horizon: int,
    decision_dates: pd.DatetimeIndex,
) -> pd.Series:
    """Translate h-session cohort forecasts into h staggered equal-capital sleeves.

    A cohort formed on decision date t contributes 1/h of its target weight to
    the live portfolio for the h one-session open-to-open return periods
    beginning at the next open. After the final signal, the calendar is extended
    for h-1 sessions so existing sleeves run off naturally.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if cohort_weights.empty:
        return pd.Series(dtype=float, name="weight")
    if not isinstance(cohort_weights.index, pd.MultiIndex) or list(cohort_weights.index.names) != ["date", "symbol"]:
        raise ValueError("cohort_weights must use a MultiIndex named ['date', 'symbol']")

    calendar = pd.DatetimeIndex(pd.to_datetime(decision_dates).unique()).sort_values()
    if calendar.empty:
        raise ValueError("decision_dates is empty")

    w = cohort_weights.unstack("symbol").sort_index().fillna(0.0)
    signal_dates = pd.DatetimeIndex(w.index)
    missing = signal_dates.difference(calendar)
    if len(missing):
        raise ValueError(f"signal dates missing from decision calendar: {list(missing[:3])}")

    start_pos = int(calendar.get_indexer([signal_dates[0]])[0])
    last_pos = int(calendar.get_indexer([signal_dates[-1]])[0])
    end_pos = min(last_pos + horizon - 1, len(calendar) - 1)
    eval_dates = calendar[start_pos : end_pos + 1]

    cohorts = w.reindex(eval_dates, fill_value=0.0)
    live = cohorts.rolling(window=horizon, min_periods=1).sum() / float(horizon)
    out = live.stack(dropna=False)
    out.index = out.index.set_names(["date", "symbol"])
    return out.sort_index().rename("weight")


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
