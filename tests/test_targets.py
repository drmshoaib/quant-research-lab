import numpy as np
import pandas as pd

from quantlab.targets import forward_open_return, next_open_to_open_simple_return


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


def test_next_open_to_open_simple_return_uses_arithmetic_return():
    dates = pd.bdate_range("2024-01-01", periods=5)
    df = pd.DataFrame({
        "date": dates,
        "symbol": "A",
        "open": [10.0, 11.0, 12.0, 15.0, 18.0],
        "high": [10.5, 11.5, 12.5, 15.5, 18.5],
        "low": [9.5, 10.5, 11.5, 14.5, 17.5],
        "close": [10.0, 11.0, 12.0, 15.0, 18.0],
        "volume": 1_000,
    }).set_index(["date", "symbol"])
    r = next_open_to_open_simple_return(df)
    assert np.isclose(r.iloc[0], 12.0 / 11.0 - 1.0)
