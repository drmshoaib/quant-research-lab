from __future__ import annotations

import numpy as np
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
    out = live.stack()
    out.index = out.index.set_names(["date", "symbol"])
    return out.sort_index().rename("weight")


def append_liquidation_row(weights: pd.Series, *, liquidation_date: pd.Timestamp) -> pd.Series:
    """Append a zero-weight row after the final portfolio date."""
    if weights.empty:
        return weights.copy()
    if not isinstance(weights.index, pd.MultiIndex) or list(weights.index.names) != ["date", "symbol"]:
        raise ValueError("weights must use a MultiIndex named ['date', 'symbol']")
    date = pd.Timestamp(liquidation_date)
    wide = weights.unstack("symbol").sort_index().fillna(0.0)
    if date <= pd.Timestamp(wide.index[-1]):
        raise ValueError("liquidation_date must be after the final weight date")
    wide.loc[date] = 0.0
    out = wide.sort_index().stack()
    out.index = out.index.set_names(["date", "symbol"])
    return out.sort_index().rename(weights.name or "weight")


def partial_adjustment_weights(
    target_weights: pd.Series,
    *,
    adjustment_rate: float,
    force_final_zero: bool = False,
) -> pd.Series:
    """Move a fixed fraction toward each live target portfolio.

    The recursion is causal:
        w_t = (1-lambda) w_{t-1} + lambda w*_t.

    If force_final_zero=True, the final target row must be all zeros and the
    actual portfolio is liquidated fully on that row. This is used only for the
    pre-declared terminal liquidation inside the development embargo.
    """
    if not 0.0 < adjustment_rate <= 1.0:
        raise ValueError("adjustment_rate must lie in (0, 1]")
    if target_weights.empty:
        return target_weights.copy()
    if not isinstance(target_weights.index, pd.MultiIndex) or list(target_weights.index.names) != ["date", "symbol"]:
        raise ValueError("target_weights must use a MultiIndex named ['date', 'symbol']")

    target = target_weights.unstack("symbol").sort_index().fillna(0.0)
    if force_final_zero and not np.allclose(target.iloc[-1].to_numpy(dtype=float), 0.0):
        raise ValueError("force_final_zero requires an all-zero final target row")

    actual = pd.DataFrame(0.0, index=target.index, columns=target.columns)
    previous = np.zeros(target.shape[1], dtype=float)
    for i, (_, row) in enumerate(target.iterrows()):
        desired = row.to_numpy(dtype=float)
        if force_final_zero and i == len(target) - 1:
            current = np.zeros_like(previous)
        else:
            current = (1.0 - adjustment_rate) * previous + adjustment_rate * desired
        actual.iloc[i] = current
        previous = current

    out = actual.stack()
    out.index = out.index.set_names(["date", "symbol"])
    return out.sort_index().rename(target_weights.name or "weight")


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
