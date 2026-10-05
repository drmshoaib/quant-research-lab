import numpy as np
import pandas as pd
import pytest

from quantlab.robustness import (
    chronological_ic_blocks,
    global_symbol_permutation_test,
    prepare_horizon_research_frame,
)


def test_horizon_frame_applies_hplus1_embargo(synthetic_panel):
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


def _prediction_panel(scores, outcomes):
    T, N = outcomes.shape
    dates = pd.bdate_range("2020-01-01", periods=T)
    symbols = [f"S{i:02d}" for i in range(N)]
    idx = pd.MultiIndex.from_product([dates, symbols], names=["date", "symbol"])
    return pd.DataFrame({"y_true": outcomes.ravel(), "y_pred": scores.ravel()}, index=idx)


def test_date_permutation_test_is_blind_to_a_static_tilt_but_the_symbol_test_is_not():
    from quantlab.robustness import global_date_permutation_test, global_symbol_permutation_test

    rng = np.random.default_rng(0)
    T, N = 300, 12
    tilt = rng.normal(size=N)
    outcomes = 0.5 * tilt[None, :] + rng.normal(size=(T, N))
    scores = np.repeat(tilt[None, :], T, axis=0) + 1e-9 * rng.normal(size=(T, N))
    pred = _prediction_panel(scores, outcomes)
    symbol = global_symbol_permutation_test(pred, n_permutations=199)
    timing = global_date_permutation_test(pred, n_permutations=199)
    assert symbol.empirical_p_value < 0.05
    # Moving whole cross-sections to other dates changes nothing for a static tilt.
    assert np.allclose(timing.null_mean_ics, timing.observed_mean_ic, atol=1e-6)
    assert timing.empirical_p_value == 1.0


def test_date_permutation_test_detects_timing_skill_and_is_valid_under_the_null():
    from quantlab.robustness import global_date_permutation_test

    rng = np.random.default_rng(1)
    T, N = 300, 12
    outcomes = rng.normal(size=(T, N))
    skilled = _prediction_panel(outcomes + 2.0 * rng.normal(size=(T, N)), outcomes)
    assert global_date_permutation_test(skilled, n_permutations=199).empirical_p_value < 0.05
    noise = _prediction_panel(rng.normal(size=(T, N)), outcomes)
    res = global_date_permutation_test(noise, n_permutations=199, seed=3)
    assert res.empirical_p_value > 0.05
    assert res.dates_used == T and res.symbols_used == N
    # The "permute" variant runs and agrees on the observed statistic.
    res2 = global_date_permutation_test(noise, n_permutations=50, method="permute")
    assert np.isclose(res2.observed_mean_ic, res.observed_mean_ic)
    with pytest.raises(ValueError):
        global_date_permutation_test(noise, min_shift=200)
