from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_panel() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2018-01-01", periods=1100)
    symbols = [f"A{i:02d}" for i in range(12)]
    parts = []
    for j, symbol in enumerate(symbols):
        shocks = rng.normal(0.0002 + j * 0.00001, 0.01, len(dates))
        close = 100.0 * np.exp(np.cumsum(shocks))
        overnight = rng.normal(0.0, 0.002, len(dates))
        open_ = close * np.exp(overnight)
        high = np.maximum(open_, close) * (1.0 + rng.uniform(0.0, 0.01, len(dates)))
        low = np.minimum(open_, close) * (1.0 - rng.uniform(0.0, 0.01, len(dates)))
        volume = rng.integers(100_000, 2_000_000, len(dates))
        parts.append(pd.DataFrame({"date": dates, "symbol": symbol, "open": open_, "high": high, "low": low, "close": close, "volume": volume}))
    return pd.concat(parts, ignore_index=True).set_index(["date", "symbol"]).sort_index()
