import pandas as pd

from quantlab.splits import PurgedWalkForward, load_date_manifest, save_date_manifest


def test_purged_walk_forward_gap():
    dates = pd.bdate_range("2010-01-01", periods=1000)
    splitter = PurgedWalkForward(min_train_days=300, test_days=50, step_days=50, purge_days=6)
    splits = list(splitter.split(dates))
    assert splits
    for s in splits:
        train_last = dates.get_loc(s.train_dates[-1])
        test_first = dates.get_loc(s.test_dates[0])
        assert test_first - train_last - 1 >= 6


def test_date_manifest_round_trip(tmp_path):
    dates = pd.bdate_range("2024-01-01", periods=10)
    path = tmp_path / "holdout_dates.csv"
    save_date_manifest(dates, path)
    loaded = load_date_manifest(path)
    assert loaded.equals(dates)
