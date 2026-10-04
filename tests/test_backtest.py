import pandas as pd

from quantlab.backtest import run_backtest


def test_transaction_costs_reduce_return():
    dates = pd.bdate_range("2024-01-01", periods=4)
    idx = pd.MultiIndex.from_product([dates, ["A", "B"]], names=["date", "symbol"])
    weights = pd.Series([0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5], index=idx)
    realized = pd.Series(0.001, index=idx)
    zero = run_backtest(weights, realized, cost_bps=0)
    cost = run_backtest(weights, realized, cost_bps=10)
    assert (cost["net_return"] <= zero["net_return"] + 1e-15).all()
    assert cost["cost"].sum() > 0
