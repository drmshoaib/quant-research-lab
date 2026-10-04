from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .features import FEATURE_COLUMNS, build_features
from .models import make_model
from .splits import PurgedWalkForward, development_and_holdout_dates, select_dates
from .targets import forward_relative_return


@dataclass
class ResearchFrames:
    frame: pd.DataFrame
    development_dates: pd.DatetimeIndex
    holdout_dates: pd.DatetimeIndex


def prepare_research_frame(panel: pd.DataFrame, *, horizon: int, holdout_days: int) -> ResearchFrames:
    X = build_features(panel)
    y = forward_relative_return(panel, horizon=horizon)
    frame = X.join(y).dropna().sort_index()
    dates = pd.DatetimeIndex(frame.index.get_level_values("date").unique()).sort_values()
    dev, holdout = development_and_holdout_dates(dates, holdout_days=holdout_days)
    return ResearchFrames(frame=frame, development_dates=dev, holdout_dates=holdout)


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
