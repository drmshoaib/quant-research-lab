from __future__ import annotations

import numpy as np
import pandas as pd

from .data import validate_panel

FEATURE_COLUMNS = [
    "ret_1",
    "mom_5",
    "mom_20",
    "mom_60",
    "vol_20",
    "vol_60",
    "range_1",
    "volume_z_20",
    "drawdown_60",
]


def _zscore(s: pd.Series, window: int) -> pd.Series:
    mean = s.rolling(window, min_periods=window).mean()
    std = s.rolling(window, min_periods=window).std(ddof=0)
    return (s - mean) / std.replace(0.0, np.nan)


def build_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Construct end-of-day features using only information available at date t."""
    panel = validate_panel(panel)
    parts: list[pd.DataFrame] = []

    for symbol, g in panel.groupby(level="symbol", sort=False):
        g = g.droplevel("symbol").sort_index()
        log_close = np.log(g["close"].astype(float))
        r1 = log_close.diff()
        log_vol = np.log1p(g["volume"].astype(float))
        rolling_peak = g["close"].rolling(60, min_periods=60).max()

        f = pd.DataFrame(index=g.index)
        f["ret_1"] = r1
        f["mom_5"] = log_close.diff(5)
        f["mom_20"] = log_close.diff(20)
        f["mom_60"] = log_close.diff(60)
        f["vol_20"] = r1.rolling(20, min_periods=20).std(ddof=0) * np.sqrt(252.0)
        f["vol_60"] = r1.rolling(60, min_periods=60).std(ddof=0) * np.sqrt(252.0)
        f["range_1"] = (g["high"] - g["low"]) / g["close"].replace(0.0, np.nan)
        f["volume_z_20"] = _zscore(log_vol, 20)
        f["drawdown_60"] = g["close"] / rolling_peak - 1.0
        f["symbol"] = symbol
        f["date"] = f.index
        parts.append(f.reset_index(drop=True))

    out = pd.concat(parts, ignore_index=True).set_index(["date", "symbol"]).sort_index()
    return out[FEATURE_COLUMNS]
