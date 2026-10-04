import numpy as np
import pandas as pd

from quantlab.backtest import (
    append_liquidation_row,
    partial_adjustment_weights,
    run_backtest,
    staggered_weights,
)


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
    expected.index.name = "date"
    pd.testing.assert_series_equal(got, expected, check_freq=False)

    ridx = pd.MultiIndex.from_product([dates[:4], ["A"]], names=["date", "symbol"])
    realized = pd.Series([0.01, 0.02, 0.03, 0.04], index=ridx)
    bt = run_backtest(live, realized, cost_bps=0)
    assert np.allclose(bt["gross_return"].to_numpy(), [0.005, 0.02, 0.03, 0.02])


def test_partial_adjustment_is_causal_and_forces_terminal_liquidation():
    dates = pd.bdate_range("2024-01-01", periods=4)
    idx = pd.MultiIndex.from_product([dates[:3], ["A", "B"]], names=["date", "symbol"])
    target = pd.Series(
        [0.5, -0.5, -0.5, 0.5, 0.5, -0.5],
        index=idx,
        name="weight",
    )
    target = append_liquidation_row(target, liquidation_date=dates[3])

    actual = partial_adjustment_weights(
        target,
        adjustment_rate=0.5,
        force_final_zero=True,
    )
    wide = actual.unstack("symbol")
    assert np.allclose(wide.iloc[0].to_numpy(), [0.25, -0.25])
    assert np.allclose(wide.iloc[-1].to_numpy(), [0.0, 0.0])
    assert np.allclose(wide.sum(axis=1).to_numpy(), 0.0)
    assert (wide.abs().sum(axis=1) <= 1.0 + 1e-12).all()

    changed = target.copy()
    changed.loc[(dates[2], "A")] = -0.5
    changed.loc[(dates[2], "B")] = 0.5
    changed_actual = partial_adjustment_weights(
        changed,
        adjustment_rate=0.5,
        force_final_zero=True,
    )
    first_two = actual.index.get_level_values("date") <= dates[1]
    assert np.allclose(
        actual.loc[first_two].to_numpy(),
        changed_actual.loc[first_two].to_numpy(),
    )


def test_partial_adjustment_reduces_turnover_for_alternating_targets():
    dates = pd.bdate_range("2024-01-01", periods=5)
    idx = pd.MultiIndex.from_product([dates[:4], ["A", "B"]], names=["date", "symbol"])
    target = pd.Series(
        [0.5, -0.5, -0.5, 0.5, 0.5, -0.5, -0.5, 0.5],
        index=idx,
        name="weight",
    )
    target = append_liquidation_row(target, liquidation_date=dates[4])
    actual = partial_adjustment_weights(target, adjustment_rate=0.5, force_final_zero=True)
    realized = pd.Series(0.0, index=target.index)
    instant_bt = run_backtest(target, realized, cost_bps=0)
    actual_bt = run_backtest(actual, realized, cost_bps=0)
    assert actual_bt["turnover"].sum() < instant_bt["turnover"].sum()
