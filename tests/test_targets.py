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


def _old_row_shift_forward_return(panel, horizon):
    """The pre-October-2026 implementation, kept here only to pin equivalence on balanced panels."""
    values = []
    for symbol, g in panel.groupby(level="symbol", sort=False):
        g = g.droplevel("symbol").sort_index()
        y = np.log(g["open"].shift(-(horizon + 1)) / g["open"].shift(-1)).rename("forward_return")
        y = y.to_frame()
        y["symbol"] = symbol
        y["date"] = y.index
        values.append(y.reset_index(drop=True).set_index(["date", "symbol"])["forward_return"])
    return pd.concat(values).sort_index()


def test_forward_return_matches_row_shift_on_balanced_panel(synthetic_panel):
    new = forward_open_return(synthetic_panel, horizon=5)
    old = _old_row_shift_forward_return(synthetic_panel, 5)
    assert new.index.equals(old.index)
    assert np.allclose(new.to_numpy(), old.to_numpy(), equal_nan=True)


def test_forward_return_counts_sessions_not_rows_when_a_bar_is_missing(synthetic_panel):
    dates = synthetic_panel.index.get_level_values("date").unique()
    gap_date = dates[100]
    panel = synthetic_panel.drop(index=(gap_date, "A00"))
    y = forward_open_return(panel, horizon=5)
    opens = synthetic_panel["open"].unstack("symbol")
    # Decision dates whose entry (t+1) or exit (t+6) open for A00 is the missing bar give NaN...
    for k in (1, 6):
        assert np.isnan(y.loc[(dates[100 - k], "A00")])
    # ...and every other A00 target still spans exactly six sessions of the common calendar.
    d = dates[90]
    expected = np.log(opens.loc[dates[96], "A00"] / opens.loc[dates[91], "A00"])
    assert np.isclose(y.loc[(d, "A00")], expected)
    # The old row-shift version would have jumped over the gap for dates just before it.
    old = _old_row_shift_forward_return(panel, 5)
    assert not np.isclose(old.loc[(dates[97], "A00")], y.loc[(dates[97], "A00")])
    # Other symbols are untouched.
    assert np.allclose(
        y.xs("A01", level="symbol").to_numpy(),
        forward_open_return(synthetic_panel, horizon=5).xs("A01", level="symbol").to_numpy(),
        equal_nan=True,
    )
