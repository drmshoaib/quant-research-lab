from __future__ import annotations

from dataclasses import dataclass
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


def select_dates(frame: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    mask = frame.index.get_level_values("date").isin(dates)
    return frame.loc[np.asarray(mask)]
