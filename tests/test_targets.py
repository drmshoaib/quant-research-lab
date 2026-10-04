import numpy as np
import pandas as pd

from quantlab.targets import forward_open_return


def test_forward_target_uses_next_open():
    dates = pd.bdate_range("2024-01-01", periods=8)
    df = pd.DataFrame({
        "date": dates,
        "symbol": "A",
        "open": [10, 11, 12, 13, 14, 15, 16, 17],
        "high": [11, 12, 13, 14, 15, 16, 17, 18],
        "low": [9, 10, 11, 12, 13, 14, 15, 16],
        "close": [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000],
        "volume": 1_000,
    }).set_index(["date", "symbol"])
    y = forward_open_return(df, horizon=2)
    expected = np.log(13 / 11)  # entry t+1, exit t+3
    assert np.isclose(y.iloc[0], expected)
