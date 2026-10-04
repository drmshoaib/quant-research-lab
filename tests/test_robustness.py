import numpy as np
import pandas as pd

from quantlab.robustness import (
    chronological_ic_blocks,
    global_symbol_permutation_test,
    prepare_horizon_research_frame,
)


def test_horizon_frame_applies_hplus1_embargo(synthetic_panel):
    holdout = pd.bdate_range("2024-01-01", periods=40)
    # Use an actual tail block from the synthetic panel's eligible calendar by
    # deriving a reference frame first.
    from quantlab.targets import eligible_decision_dates

    eligible = eligible_decision_dates(synthetic_panel, horizon=5, min_assets=8)
    fixed_holdout = eligible[-100:]

    research = prepare_horizon_research_frame(
        synthetic_panel,
        horizon=10,
        holdout_dates=fixed_holdout,
        min_assets=8,
    )
    assert len(research.embargo_dates) == 11
    assert research.development_dates.max() < research.embargo_dates.min()
    assert research.embargo_dates.max() < fixed_holdout[0]


def test_chronological_blocks_cover_series_once():
    dates = pd.bdate_range("2020-01-01", periods=101)
    ic = pd.Series(np.linspace(-0.1, 0.2, len(dates)), index=dates)
    blocks = chronological_ic_blocks(ic, n_blocks=3, hac_lag=4)
    assert sum(b["n_dates"] for b in blocks) == len(ic)
    assert blocks[0]["start"] == str(dates[0].date())
    assert blocks[-1]["end"] == str(dates[-1].date())


def test_global_symbol_permutation_is_reproducible():
    dates = pd.bdate_range("2020-01-01", periods=50)
    symbols = [f"S{i}" for i in range(6)]
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    base = np.tile(np.arange(len(symbols), dtype=float), len(dates))
    pred = pd.DataFrame(
        {
            "y_true": base,
            "y_pred": base,
            "fold": 1,
        },
        index=idx,
    )
    a = global_symbol_permutation_test(pred, n_permutations=99, seed=123)
    b = global_symbol_permutation_test(pred, n_permutations=99, seed=123)
    assert a.observed_mean_ic > 0.99
    assert np.allclose(a.null_mean_ics, b.null_mean_ics)
    assert a.empirical_p_value == b.empirical_p_value
