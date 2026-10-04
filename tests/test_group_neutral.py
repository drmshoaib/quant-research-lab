import numpy as np
import pandas as pd

from quantlab.group_neutral import (
    composite_ic_diagnostics,
    inverse_group_map,
    prepare_group_neutral_research_frame,
    within_group_ic_matrix,
)
from quantlab.robustness import broad_asset_group_map
from quantlab.targets import forward_group_relative_return


def test_group_relative_target_has_zero_group_mean(synthetic_panel):
    symbols = synthetic_panel.index.get_level_values("symbol").unique().tolist()
    split = len(symbols) // 2
    mapping = {
        symbol: ("G1" if i < split else "G2")
        for i, symbol in enumerate(symbols)
    }
    target = forward_group_relative_return(
        synthetic_panel,
        mapping,
        horizon=5,
    ).dropna()
    frame = target.rename("target").reset_index()
    frame["group"] = frame["symbol"].map(mapping)
    means = frame.groupby(["date", "group"])["target"].mean()
    assert np.allclose(means.to_numpy(), 0.0, atol=1e-12)


def test_group_neutral_frame_respects_same_holdout_boundary(synthetic_panel):
    from quantlab.targets import eligible_decision_dates

    symbols = synthetic_panel.index.get_level_values("symbol").unique().tolist()
    mapping = {
        symbol: ("G1" if i < len(symbols) // 2 else "G2")
        for i, symbol in enumerate(symbols)
    }
    eligible = eligible_decision_dates(
        synthetic_panel,
        horizon=5,
        min_assets=8,
    )
    holdout = eligible[-100:]
    research = prepare_group_neutral_research_frame(
        synthetic_panel,
        symbol_groups=mapping,
        horizon=5,
        holdout_dates=holdout,
        holdout_purge_days=6,
        min_assets=8,
    )
    assert research.holdout_dates.equals(holdout)
    assert len(research.embargo_dates) == 6
    assert research.development_dates.max() < research.embargo_dates.min()


def test_equal_weight_group_composite_does_not_weight_by_group_size():
    dates = pd.bdate_range("2024-01-01", periods=30)
    groups = {
        "Big": [f"B{i}" for i in range(8)],
        "Small1": [f"S1_{i}" for i in range(4)],
        "Small2": [f"S2_{i}" for i in range(4)],
        "Small3": [f"S3_{i}" for i in range(4)],
    }
    rows = []
    for date in dates:
        for group, symbols in groups.items():
            for rank, symbol in enumerate(symbols):
                truth = float(rank)
                pred = truth if group == "Big" else -truth
                rows.append((date, symbol, truth, pred, 1))
    pred = pd.DataFrame(
        rows,
        columns=["date", "symbol", "y_true", "y_pred", "fold"],
    ).set_index(["date", "symbol"])

    matrix = within_group_ic_matrix(
        pred,
        groups,
        min_assets=4,
    )
    diag = composite_ic_diagnostics(
        matrix,
        non_us_groups=["Small1", "Small2", "Small3"],
        hac_lag=4,
    )
    assert np.isclose(
        diag["equal_weight_four_group"]["mean_ic"],
        -0.5,
    )
    assert np.isclose(
        diag["equal_weight_non_us"]["mean_ic"],
        -1.0,
    )
