from quantlab.metrics import rank_ic_by_date
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions


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
