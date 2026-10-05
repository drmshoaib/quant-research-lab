from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import pandas as pd

from .features import FEATURE_COLUMNS, build_features
from .models import fitted_n_iter, make_model
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
    feature_columns: Sequence[str] | None = None,
    purge_days: int | None = None,
) -> pd.DataFrame:
    """Fit one fresh model per purged walk-forward fold and return out-of-sample scores.

    ``purge_days`` defaults to ``horizon + 1``, the frozen v0.2 value. It is a
    parameter so that the configuration file, not this function, is the single
    source of truth when a caller wants to pass ``train_test_purge_days``.
    This is the frozen v0.2 entry point; its output is unchanged. Use
    :func:`walk_forward_predictions_with_diagnostics` to also obtain per-fold
    information such as the number of boosting rounds actually fitted.
    """
    predictions, _ = walk_forward_predictions_with_diagnostics(
        research,
        model_name=model_name,
        horizon=horizon,
        min_train_days=min_train_days,
        test_days=test_days,
        step_days=step_days,
        ridge_alpha=ridge_alpha,
        random_state=random_state,
        feature_columns=feature_columns,
        purge_days=purge_days,
    )
    return predictions


def walk_forward_predictions_with_diagnostics(
    research: ResearchFrames,
    *,
    model_name: str,
    horizon: int,
    min_train_days: int,
    test_days: int,
    step_days: int,
    ridge_alpha: float = 10.0,
    random_state: int = 42,
    feature_columns: Sequence[str] | None = None,
    purge_days: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Walk-forward predictions plus one diagnostics row per fold.

    The diagnostics frame (indexed by fold) records the training and test date
    ranges, the row counts, and ``n_iter`` (the number of boosting rounds the
    fitted model used; NaN for models without one). Recording ``n_iter`` is the
    EXP-008 remedy for the undocumented early stopping of v0.2 (docs/errata.md,
    A1): whatever the stopping rule, the number of trees becomes part of the
    record.
    """
    if purge_days is None:
        purge_days = horizon + 1
    if purge_days < horizon:
        raise ValueError("purge_days must be at least the prediction horizon")
    features = list(FEATURE_COLUMNS if feature_columns is None else feature_columns)
    if not features:
        raise ValueError("feature_columns must contain at least one feature")
    unknown = sorted(set(features).difference(research.frame.columns))
    if unknown:
        raise ValueError(f"unknown feature columns: {unknown}")

    dev_frame = select_dates(research.frame, research.development_dates)
    splitter = PurgedWalkForward(
        min_train_days=min_train_days,
        test_days=test_days,
        step_days=step_days,
        purge_days=purge_days,
    )
    pieces: list[pd.DataFrame] = []
    diagnostics: list[dict] = []
    for fold, split in enumerate(splitter.split(research.development_dates), start=1):
        train = select_dates(dev_frame, split.train_dates)
        test = select_dates(dev_frame, split.test_dates)
        if train.empty or test.empty:
            continue
        model = make_model(model_name, ridge_alpha=ridge_alpha, random_state=random_state, n_train=len(train))
        model.fit(train[features], train["target"])
        pred = model.predict(test[features])
        p = pd.DataFrame({"y_true": test["target"], "y_pred": pred}, index=test.index)
        p["fold"] = fold
        pieces.append(p)
        n_iter = fitted_n_iter(model)
        diagnostics.append(
            {
                "fold": fold,
                "train_start": split.train_dates[0],
                "train_end": split.train_dates[-1],
                "test_start": split.test_dates[0],
                "test_end": split.test_dates[-1],
                "n_train_rows": int(len(train)),
                "n_test_rows": int(len(test)),
                "n_iter": float(n_iter) if n_iter is not None else float("nan"),
            }
        )
    if not pieces:
        empty = pd.DataFrame(columns=["y_true", "y_pred", "fold"], index=research.frame.index[:0])
        return empty, pd.DataFrame(columns=["train_start", "train_end", "test_start", "test_end", "n_train_rows", "n_test_rows", "n_iter"])
    return pd.concat(pieces).sort_index(), pd.DataFrame(diagnostics).set_index("fold")
