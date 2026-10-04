import numpy as np
import pandas as pd

from quantlab.backtest import run_backtest, staggered_weights


def test_transaction_costs_reduce_return():
    dates = pd.bdate_range("2024-01-01", periods=4)
    idx = pd.MultiIndex.from_product([dates, ["A", "B"]], names=["date", "symbol"])
    weights = pd.Series([0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5], index=idx)
    realized = pd.Series(0.001, index=idx)
    zero = run_backtest(weights, realized, cost_bps=0)
    cost = run_backtest(weights, realized, cost_bps=10)
    assert (cost["net_return"] <= zero["net_return"] + 1e-15).all()
    assert cost["cost"].sum() > 0


def test_staggered_sleeves_match_horizon_and_run_off():
    dates = pd.bdate_range("2024-01-01", periods=6)
    signal_dates = dates[:3]
    idx = pd.MultiIndex.from_product([signal_dates, ["A"]], names=["date", "symbol"])
    cohort = pd.Series(1.0, index=idx, name="weight")

    live = staggered_weights(cohort, horizon=2, decision_dates=dates)
    got = live.xs("A", level="symbol")
    expected = pd.Series([0.5, 1.0, 1.0, 0.5], index=dates[:4], name="weight")
    pd.testing.assert_series_equal(got, expected, check_freq=False)

    ridx = pd.MultiIndex.from_product([dates[:4], ["A"]], names=["date", "symbol"])
    realized = pd.Series([0.01, 0.02, 0.03, 0.04], index=ridx)
    bt = run_backtest(live, realized, cost_bps=0)
    assert np.allclose(bt["gross_return"].to_numpy(), [0.005, 0.02, 0.03, 0.02])
