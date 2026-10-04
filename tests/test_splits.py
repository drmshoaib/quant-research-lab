import pandas as pd

from quantlab.splits import PurgedWalkForward


def test_purged_walk_forward_gap():
    dates = pd.bdate_range("2010-01-01", periods=1000)
    splitter = PurgedWalkForward(min_train_days=300, test_days=50, step_days=50, purge_days=6)
    splits = list(splitter.split(dates))
    assert splits
    for s in splits:
        train_last = dates.get_loc(s.train_dates[-1])
        test_first = dates.get_loc(s.test_dates[0])
        assert test_first - train_last - 1 >= 6
