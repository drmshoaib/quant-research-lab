from __future__ import annotations

import numpy as np
import pandas as pd

from .data import validate_panel


def _opens_on_common_calendar(panel: pd.DataFrame) -> pd.DataFrame:
    """Opening prices as a dates x symbols table on the union session calendar.

    Every symbol is reindexed to the union of all dates in the panel, so a
    missing bar becomes NaN instead of being skipped. Shifting this table by k
    rows then always means "k sessions later", even for an unbalanced panel.
    (Until October 2026 the functions below shifted each symbol's own rows,
    which silently jumped over missing sessions; the frozen v0.2 panel is
    balanced, 126,390 = 30 x 4,213 rows, so no reported result was affected.)
    """
    return panel["open"].astype(float).unstack("symbol").sort_index()


def _long(wide: pd.DataFrame, name: str, like: pd.Index) -> pd.Series:
    out = wide.stack(future_stack=True)
    out.index = out.index.set_names(["date", "symbol"])
    # Return exactly the (date, symbol) rows of the input panel, in sorted order.
    return out.reindex(like).sort_index().rename(name)


def forward_open_return(panel: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """Forward log return aligned to decision date t.

    Information is assumed known after the close at t. Execution occurs at the
    next session's open (t+1); exit is at the open h sessions after entry, that
    is at the open of session t+h+1. The target never uses the current close as
    an executable price. If the entry or exit bar is missing the value is NaN.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    panel = validate_panel(panel)
    opens = _opens_on_common_calendar(panel)
    y = np.log(opens.shift(-(horizon + 1)) / opens.shift(-1))
    return _long(y, "forward_return", panel.index)


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
    """One-session realised log return aligned to decision date t.

    This remains useful for modelling diagnostics. Portfolio P&L should use
    next_open_to_open_simple_return so transaction costs and compounding are
    handled in arithmetic-return space.
    """
    return forward_open_return(panel, horizon=1).rename("realized_log_return")


def next_open_to_open_simple_return(panel: pd.DataFrame) -> pd.Series:
    """One-session realised simple return for portfolio P&L.

    A position selected after the close at t enters at open t+1 and earns the
    simple return to open t+2. This equals exp(r) - 1 for the one-session log
    return and is computed on the same common session calendar.
    """
    r = forward_open_return(panel, horizon=1)
    return np.expm1(r).rename("realized_return")


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
