import numpy as np
import pandas as pd

from quantlab.portfolio import (
    optimise_weights,
    rank_weights,
    turnover_budget_path,
    turnover_budget_projection,
)


def test_rank_weights_constraints():
    scores = pd.Series(np.linspace(-1, 1, 20), index=[f"A{i}" for i in range(20)])
    w = rank_weights(scores, gross_limit=1.0, max_abs_weight=0.08)
    assert abs(w.sum()) < 1e-10
    assert w.abs().sum() <= 1.0 + 1e-10
    assert w.abs().max() <= 0.08 + 1e-10


def test_optimizer_constraints():
    names = [f"A{i}" for i in range(12)]
    alpha = pd.Series(np.linspace(-0.02, 0.02, len(names)), index=names)
    cov = pd.DataFrame(np.eye(len(names)) * 0.01, index=names, columns=names)
    w = optimise_weights(alpha, cov, gross_limit=1.0, max_abs_weight=0.15)
    assert abs(w.sum()) < 1e-5
    assert w.abs().sum() <= 1.001
    assert w.abs().max() <= 0.1501


def test_turnover_budget_projection_constraints_and_selectivity():
    names = [f"A{i}" for i in range(8)]
    previous = pd.Series(
        [0.08, 0.06, 0.02, -0.02, -0.08, -0.06, 0.0, 0.0],
        index=names,
    )
    target = pd.Series(
        [-0.08, 0.08, 0.06, 0.02, 0.08, -0.08, -0.04, -0.04],
        index=names,
    )
    w, info = turnover_budget_projection(
        target,
        previous,
        turnover_budget=0.12,
        gross_limit=1.0,
        max_abs_weight=0.08,
    )
    assert abs(w.sum()) <= 1e-7
    assert w.abs().sum() <= 1.0 + 1e-7
    assert w.abs().max() <= 0.08 + 1e-7
    assert (w - previous).abs().sum() <= 0.12 + 1e-7
    assert info["actual_turnover"] <= 0.12 + 1e-7

    # The projection should not collapse to a uniform proportional move.
    alpha = 0.12 / float((target - previous).abs().sum())
    proportional = previous + alpha * (target - previous)
    assert not np.allclose(w.to_numpy(), proportional.to_numpy(), atol=1e-5)


def test_turnover_budget_path_is_causal_and_terminal_liquidation_is_exact():
    dates = pd.bdate_range("2024-01-01", periods=5)
    symbols = ["A", "B", "C", "D"]
    idx = pd.MultiIndex.from_product([dates[:4], symbols], names=["date", "symbol"])
    target = pd.Series(
        [
            0.08, 0.04, -0.08, -0.04,
            -0.08, 0.08, -0.04, 0.04,
            0.04, 0.08, -0.08, -0.04,
            -0.04, 0.04, 0.08, -0.08,
        ],
        index=idx,
        name="weight",
    )
    liquidation = pd.MultiIndex.from_product([[dates[4]], symbols], names=["date", "symbol"])
    target = pd.concat([target, pd.Series(0.0, index=liquidation, name="weight")])

    actual, diag = turnover_budget_path(
        target,
        turnover_budget=0.10,
        gross_limit=1.0,
        max_abs_weight=0.08,
        force_final_zero=True,
    )
    wide = actual.unstack("symbol")
    assert np.allclose(wide.iloc[-1].to_numpy(), 0.0)
    assert (diag.loc[~diag["terminal_liquidation"], "actual_turnover"] <= 0.10 + 1e-7).all()

    changed = target.copy()
    changed.loc[(dates[3], "A")] = 0.08
    changed.loc[(dates[3], "B")] = -0.08
    changed.loc[(dates[3], "C")] = 0.04
    changed.loc[(dates[3], "D")] = -0.04
    changed_actual, _ = turnover_budget_path(
        changed,
        turnover_budget=0.10,
        gross_limit=1.0,
        max_abs_weight=0.08,
        force_final_zero=True,
    )
    past = actual.index.get_level_values("date") <= dates[2]
    assert np.allclose(actual.loc[past].to_numpy(), changed_actual.loc[past].to_numpy())


def test_no_trade_band_holds_small_changes_and_moves_only_toward_target():
    from quantlab.portfolio import no_trade_band_projection

    names = ["A", "B", "C", "D", "E", "F"]
    previous = pd.Series([0.06, 0.04, 0.00, -0.02, -0.04, -0.04], index=names)
    target = pd.Series([0.055, 0.07, 0.01, -0.05, -0.035, -0.05], index=names)

    w, info = no_trade_band_projection(
        target,
        previous,
        no_trade_band=0.01,
        gross_limit=1.0,
        max_abs_weight=0.08,
    )

    desired = target - previous
    inactive = desired.abs() <= 0.01
    assert np.allclose(w.loc[inactive].to_numpy(), previous.loc[inactive].to_numpy())
    assert abs(w.sum()) <= 1e-7
    assert w.abs().sum() <= 1.0 + 1e-7
    assert w.abs().max() <= 0.08 + 1e-7

    active = ~inactive
    lo = pd.concat([previous.loc[active], target.loc[active]], axis=1).min(axis=1)
    hi = pd.concat([previous.loc[active], target.loc[active]], axis=1).max(axis=1)
    assert (w.loc[active] >= lo - 1e-7).all()
    assert (w.loc[active] <= hi + 1e-7).all()
    assert info["held_fraction"] > 0


def test_no_trade_band_path_is_causal_and_terminal_liquidation_is_exact():
    from quantlab.portfolio import no_trade_band_path

    dates = pd.bdate_range("2024-01-01", periods=5)
    symbols = ["A", "B", "C", "D"]
    idx = pd.MultiIndex.from_product([dates[:4], symbols], names=["date", "symbol"])
    target = pd.Series(
        [
            0.04, 0.02, -0.04, -0.02,
            0.06, 0.02, -0.05, -0.03,
            0.08, 0.00, -0.04, -0.04,
            0.04, 0.04, -0.06, -0.02,
        ],
        index=idx,
        name="weight",
    )
    liquidation = pd.MultiIndex.from_product(
        [[dates[4]], symbols], names=["date", "symbol"]
    )
    target = pd.concat(
        [target, pd.Series(0.0, index=liquidation, name="weight")]
    )

    actual, diag = no_trade_band_path(
        target,
        no_trade_band=0.01,
        gross_limit=1.0,
        max_abs_weight=0.08,
        force_final_zero=True,
    )
    wide = actual.unstack("symbol")
    assert np.allclose(wide.iloc[-1].to_numpy(), 0.0)
    assert diag.iloc[-1]["terminal_liquidation"]

    changed = target.copy()
    changed.loc[(dates[3], "A")] = 0.08
    changed.loc[(dates[3], "B")] = 0.00
    changed.loc[(dates[3], "C")] = -0.04
    changed.loc[(dates[3], "D")] = -0.04
    changed_actual, _ = no_trade_band_path(
        changed,
        no_trade_band=0.01,
        gross_limit=1.0,
        max_abs_weight=0.08,
        force_final_zero=True,
    )
    past = actual.index.get_level_values("date") <= dates[2]
    assert np.allclose(
        actual.loc[past].to_numpy(),
        changed_actual.loc[past].to_numpy(),
    )

