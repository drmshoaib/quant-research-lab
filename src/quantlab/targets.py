from __future__ import annotations

import numpy as np
import pandas as pd

from .data import validate_panel


def forward_open_return(panel: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """Forward log return aligned to decision date t.

    Information is assumed known after the close at t. Execution occurs at the
    next session's open (t+1); exit is at the open h sessions later. Thus the
    target never uses the current close as an executable price.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    panel = validate_panel(panel)
    values: list[pd.Series] = []
    for symbol, g in panel.groupby(level="symbol", sort=False):
        g = g.droplevel("symbol").sort_index()
        entry = g["open"].shift(-1)
        exit_ = g["open"].shift(-(horizon + 1))
        y = np.log(exit_ / entry)
        y.name = "forward_return"
        y = y.to_frame()
        y["symbol"] = symbol
        y["date"] = y.index
        values.append(y.reset_index(drop=True).set_index(["date", "symbol"])["forward_return"])
    return pd.concat(values).sort_index()


def forward_relative_return(panel: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """Forward return minus same-date cross-sectional mean return."""
    raw = forward_open_return(panel, horizon=horizon)
    mean_by_date = raw.groupby(level="date").transform("mean")
    out = raw - mean_by_date
    out.name = "target"
    return out


def eligible_decision_dates(
    panel: pd.DataFrame,
    *,
    horizon: int,
    min_assets: int = 8,
) -> pd.DatetimeIndex:
    """Decision dates with enough observable forward returns for inference.

    This calendar depends only on market data and target timing. It is therefore
    suitable for freezing the hold-out independently of feature missingness.
    """
    if min_assets < 2:
        raise ValueError("min_assets must be >= 2")
    raw = forward_open_return(panel, horizon=horizon)
    counts = raw.notna().groupby(level="date").sum()
    dates = counts.index[counts >= min_assets]
    return pd.DatetimeIndex(pd.to_datetime(dates)).sort_values()


def next_open_to_open_return(panel: pd.DataFrame) -> pd.Series:
    """One-session realised log return for a position chosen at decision date t."""
    return forward_open_return(panel, horizon=1).rename("realized_return")


def forward_group_relative_return(
    panel: pd.DataFrame,
    symbol_groups: dict[str, str] | pd.Series,
    horizon: int = 5,
) -> pd.Series:
    """Forward return minus same-date mean within each pre-declared group."""
    raw = forward_open_return(panel, horizon=horizon)
    group_map = (
        symbol_groups.astype(str)
        if isinstance(symbol_groups, pd.Series)
        else pd.Series(symbol_groups, dtype=str)
    )
    group_map.index = group_map.index.astype(str)

    frame = raw.rename("forward_return").reset_index()
    frame["broad_group"] = frame["symbol"].astype(str).map(group_map)
    if frame["broad_group"].isna().any():
        missing = sorted(
            frame.loc[frame["broad_group"].isna(), "symbol"]
            .astype(str)
            .unique()
            .tolist()
        )
        raise ValueError(f"missing broad-group mapping for symbols: {missing}")

    group_mean = frame.groupby(
        ["date", "broad_group"],
        sort=False,
    )["forward_return"].transform("mean")
    frame["target"] = frame["forward_return"] - group_mean
    out = frame.set_index(["date", "symbol"])["target"].sort_index()
    out.name = "target"
    return out
