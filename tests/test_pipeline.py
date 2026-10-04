from quantlab.metrics import rank_ic_by_date
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.splits import development_and_holdout_dates
from quantlab.targets import eligible_decision_dates


def test_walk_forward_pipeline_runs(synthetic_panel):
    research = prepare_research_frame(synthetic_panel, horizon=5, holdout_days=100)
    pred = walk_forward_predictions(
        research,
        model_name="ridge",
        horizon=5,
        min_train_days=400,
        test_days=50,
        step_days=50,
    )
    assert not pred.empty
    assert set(pred.columns) == {"y_true", "y_pred", "fold"}
    ic = rank_ic_by_date(pred, min_assets=5)
    assert len(ic) > 0


def test_holdout_manifest_is_feature_independent_and_embargoed(synthetic_panel):
    eligible = eligible_decision_dates(synthetic_panel, horizon=5, min_assets=8)
    _, holdout = development_and_holdout_dates(eligible, holdout_days=100)

    research = prepare_research_frame(
        synthetic_panel,
        horizon=5,
        holdout_days=100,
        holdout_dates=holdout,
        holdout_purge_days=6,
        min_assets=8,
    )

    assert research.holdout_dates.equals(holdout)
    before = eligible[eligible < holdout[0]]
    assert research.embargo_dates.equals(before[-6:])
    assert research.development_dates.max() < research.embargo_dates.min()

    changed = synthetic_panel.copy()
    affected = changed.index.get_level_values("date").isin(holdout[:10])
    changed.loc[affected, "volume"] = float("nan")
    changed_research = prepare_research_frame(
        changed,
        horizon=5,
        holdout_days=100,
        holdout_dates=holdout,
        holdout_purge_days=6,
        min_assets=8,
    )
    assert changed_research.holdout_dates.equals(holdout)
