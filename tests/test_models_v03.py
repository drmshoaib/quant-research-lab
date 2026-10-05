"""Tests for the EXP-008 (v0.3) model variants and fold diagnostics."""
import numpy as np
import pandas as pd
import pytest

from quantlab.metrics import hac_lag_sensitivity, newey_west_automatic_lag
from quantlab.models import V02_BOOSTING_PARAMS, V03_RIDGE_KAPPA, fitted_n_iter, make_model
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions, walk_forward_predictions_with_diagnostics


def test_frozen_names_are_unchanged():
    m = make_model("hist_gb")
    assert m.early_stopping == "auto" and m.max_iter == 250
    r = make_model("ridge")
    assert r.steps[-1][1].alpha == 10.0


def test_v03_boosting_has_no_early_stopping_and_fits_all_trees():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(12_000, 4))
    y = X[:, 0] + rng.normal(size=12_000)
    m = make_model("hist_gb_v03").fit(X, y)
    assert m.early_stopping is False
    assert fitted_n_iter(m) == V02_BOOSTING_PARAMS["max_iter"]
    legacy = make_model("hist_gb").fit(X, y)  # > 10,000 rows: default early stopping kicks in
    assert fitted_n_iter(legacy) < V02_BOOSTING_PARAMS["max_iter"]


def test_ridge_v03_penalty_scales_with_n():
    a = make_model("ridge_v03", n_train=1000).steps[-1][1].alpha
    b = make_model("ridge_v03", n_train=4000).steps[-1][1].alpha
    assert a == pytest.approx(V03_RIDGE_KAPPA * 1000) and b == pytest.approx(4 * a)
    with pytest.raises(ValueError):
        make_model("ridge_v03")
    # Shrinkage of a unit-eigenvalue direction is lambda/(lambda+kappa), independent of n.
    rng = np.random.default_rng(1)
    for n in (2000, 8000):
        X = rng.normal(size=(n, 1))
        X = (X - X.mean()) / X.std()
        y = 2.0 * X[:, 0]
        coef = make_model("ridge_v03", n_train=n).fit(X, y).steps[-1][1].coef_[0]
        assert coef == pytest.approx(2.0 / (1.0 + V03_RIDGE_KAPPA), rel=1e-3)


def test_time_ordered_early_stopping_uses_dates_and_exposes_n_iter(synthetic_panel):
    research = prepare_research_frame(synthetic_panel, horizon=5, holdout_days=60, min_assets=8)
    frame = research.frame.loc[research.frame.index.get_level_values("date").isin(research.development_dates)]
    X = frame[["ret_1", "mom_20", "vol_20"]]
    y = frame["target"]
    m = make_model("hist_gb_v03_time").fit(X, y)
    n = fitted_n_iter(m)
    assert 10 <= n <= 250
    # The validation block is the LAST 10% of distinct dates, purged from the fit block.
    dates = X.index.get_level_values("date").unique().sort_values()
    assert m.validation_dates_[0] > dates[int(len(dates) * 0.9) - 7]
    assert m.predict(X.iloc[:5]).shape == (5,)
    with pytest.raises(ValueError):
        make_model("hist_gb_v03_time").fit(X.to_numpy(), y.to_numpy())  # no dates available


def test_walk_forward_diagnostics_record_n_iter_and_match_frozen_output(synthetic_panel):
    research = prepare_research_frame(synthetic_panel, horizon=5, holdout_days=60, min_assets=8)
    kw = dict(horizon=5, min_train_days=300, test_days=63, step_days=63, feature_columns=["ret_1", "mom_20"])
    frozen = walk_forward_predictions(research, model_name="ridge", **kw)
    preds, diag = walk_forward_predictions_with_diagnostics(research, model_name="ridge", **kw)
    pd.testing.assert_frame_equal(frozen, preds)
    assert list(diag.index) == sorted(preds["fold"].unique())
    assert diag["n_iter"].isna().all()  # Ridge has no boosting rounds
    assert (diag["test_end"] > diag["train_end"]).all()
    preds_gb, diag_gb = walk_forward_predictions_with_diagnostics(research, model_name="hist_gb_v03", **kw)
    assert (diag_gb["n_iter"] == 250).all()


def test_lag_sensitivity_table():
    assert newey_west_automatic_lag(3087) == 8
    rng = np.random.default_rng(0)
    e = rng.normal(size=2000)
    x = pd.Series(np.convolve(e, np.ones(5), mode="valid") / 5 + 0.02)  # 5-session overlap
    tab = hac_lag_sensitivity(x, lags=(0, 4, 10))
    assert set(tab.index) == {0, 4, 10, newey_west_automatic_lag(len(x))}
    # Standard errors must grow with the lag for an overlapping series.
    assert tab.loc[0, "se"] < tab.loc[4, "se"] < tab.loc[10, "se"]
    assert tab["automatic"].sum() == 1
