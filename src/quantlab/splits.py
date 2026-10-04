from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DateSplit:
    train_dates: pd.DatetimeIndex
    test_dates: pd.DatetimeIndex


@dataclass(frozen=True)
class PurgedWalkForward:
    min_train_days: int = 756
    test_days: int = 63
    step_days: int = 63
    purge_days: int = 6

    def split(self, dates: pd.DatetimeIndex) -> Iterator[DateSplit]:
        dates = pd.DatetimeIndex(pd.to_datetime(dates).unique()).sort_values()
        n = len(dates)
        if n < self.min_train_days + self.purge_days + self.test_days:
            return

        test_start = self.min_train_days + self.purge_days
        while test_start + self.test_days <= n:
            train_end = test_start - self.purge_days
            train = dates[:train_end]
            test = dates[test_start : test_start + self.test_days]
            if len(train) >= self.min_train_days:
                yield DateSplit(train_dates=train, test_dates=test)
            test_start += self.step_days


def development_and_holdout_dates(
    dates: pd.DatetimeIndex,
    holdout_days: int,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    dates = pd.DatetimeIndex(pd.to_datetime(dates).unique()).sort_values()
    if holdout_days < 1 or len(dates) <= holdout_days:
        raise ValueError("holdout_days must leave at least one development date")
    return dates[:-holdout_days], dates[-holdout_days:]


def save_date_manifest(dates: pd.DatetimeIndex, path: str | Path) -> None:
    """Persist an immutable ordered date manifest as YYYY-MM-DD."""
    dates = pd.DatetimeIndex(pd.to_datetime(dates).unique()).sort_values()
    if dates.empty:
        raise ValueError("cannot save an empty date manifest")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d")}).to_csv(path, index=False)


def load_date_manifest(path: str | Path) -> pd.DatetimeIndex:
    """Load and validate a date manifest."""
    df = pd.read_csv(path)
    if list(df.columns) != ["date"]:
        raise ValueError("date manifest must contain exactly one column named 'date'")
    dates = pd.DatetimeIndex(pd.to_datetime(df["date"], errors="raise"))
    if dates.has_duplicates:
        raise ValueError("date manifest contains duplicates")
    if not dates.is_monotonic_increasing:
        raise ValueError("date manifest must be sorted")
    if dates.empty:
        raise ValueError("date manifest is empty")
    return dates


def select_dates(frame: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    mask = frame.index.get_level_values("date").isin(dates)
    return frame.loc[np.asarray(mask)]
