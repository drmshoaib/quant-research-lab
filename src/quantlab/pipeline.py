from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .features import FEATURE_COLUMNS, build_features
from .models import make_model
from .splits import PurgedWalkForward, development_and_holdout_dates, select_dates
from .targets import eligible_decision_dates, forward_relative_return


@dataclass
class ResearchFrames:
    frame: pd.DataFrame
    development_dates: pd.DatetimeIndex
    holdout_dates: pd.DatetimeIndex
    embargo_dates: pd.DatetimeIndex


def prepare_research_frame(
    panel: pd.DataFrame,
    *,
    horizon: int,
    holdout_days: int | None = None,
    holdout_dates: pd.DatetimeIndex | None = None,
    holdout_purge_days: int | None = None,
    min_assets: int = 8,
) -> ResearchFrames:
    """Build the modelling frame while keeping the hold-out calendar feature-independent."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if holdout_purge_days is None:
        holdout_purge_days = horizon + 1
    if holdout_purge_days < horizon:
        raise ValueError("holdout_purge_days must be at least the prediction horizon")

    X = build_features(panel)
    y = forward_relative_return(panel, horizon=horizon)
    eligible = eligible_decision_dates(panel, horizon=horizon, min_assets=min_assets)

    if holdout_dates is None:
        if holdout_days is None:
            raise ValueError("provide holdout_days or an explicit holdout_dates manifest")
        _, holdout = development_and_holdout_dates(eligible, holdout_days=holdout_days)
    else:
        holdout = pd.DatetimeIndex(pd.to_datetime(holdout_dates).unique()).sort_values()
        if holdout.empty:
            raise ValueError("holdout_dates is empty")
        if holdout_days is not None and len(holdout) != holdout_days:
            raise ValueError("holdout manifest length does not match holdout_days")
        missing = holdout.difference(eligible)
        if len(missing):
            raise ValueError(f"holdout manifest contains ineligible dates: {list(missing[:3])}")
        expected_tail = eligible[-len(holdout) :]
        if not holdout.equals(expected_tail):
            raise ValueError("holdout manifest is not the final eligible block of the frozen data window")

    before_holdout = eligible[eligible < holdout[0]]
    if len(before_holdout) <= holdout_purge_days:
        raise ValueError("insufficient pre-holdout dates after applying the holdout embargo")
    embargo = before_holdout[-holdout_purge_days:]
    development_eligible = before_holdout[:-holdout_purge_days]

    frame = X.join(y).dropna().sort_index()
    frame_dates = pd.DatetimeIndex(frame.index.get_level_values("date").unique()).sort_values()
    development = development_eligible.intersection(frame_dates)

    return ResearchFrames(
        frame=frame,
        development_dates=development,
        holdout_dates=holdout,
        embargo_dates=embargo,
    )


def walk_forward_predictions(
    research: ResearchFrames,
    *,
    model_name: str,
    horizon: int,
    min_train_days: int,
    test_days: int,
    step_days: int,
    ridge_alpha: float = 10.0,
    random_state: int = 42,
) -> pd.DataFrame:
    dev_frame = select_dates(research.frame, research.development_dates)
    splitter = PurgedWalkForward(
        min_train_days=min_train_days,
        test_days=test_days,
        step_days=step_days,
        purge_days=horizon + 1,
    )
    pieces: list[pd.DataFrame] = []
    for fold, split in enumerate(splitter.split(research.development_dates), start=1):
        train = select_dates(dev_frame, split.train_dates)
        test = select_dates(dev_frame, split.test_dates)
        if train.empty or test.empty:
            continue
        model = make_model(model_name, ridge_alpha=ridge_alpha, random_state=random_state)
        model.fit(train[FEATURE_COLUMNS], train["target"])
        pred = model.predict(test[FEATURE_COLUMNS])
        p = pd.DataFrame({"y_true": test["target"], "y_pred": pred}, index=test.index)
        p["fold"] = fold
        pieces.append(p)
    if not pieces:
        return pd.DataFrame(columns=["y_true", "y_pred", "fold"], index=research.frame.index[:0])
    return pd.concat(pieces).sort_index()
