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


def next_open_to_open_return(panel: pd.DataFrame) -> pd.Series:
    """One-session realised log return for a position chosen at decision date t."""
    return forward_open_return(panel, horizon=1).rename("realized_return")
