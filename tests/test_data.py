import sys
import types

import pandas as pd

from quantlab.data import download_yahoo


def test_yahoo_adapter_requests_adjusted_ohlc(monkeypatch):
    captured = {}
    fake = types.ModuleType("yfinance")

    def download(**kwargs):
        captured.update(kwargs)
        dates = pd.bdate_range("2024-01-01", periods=4)
        return pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0, 103.0],
                "High": [101.0, 102.0, 103.0, 104.0],
                "Low": [99.0, 100.0, 101.0, 102.0],
                "Close": [100.5, 101.5, 102.5, 103.5],
                "Volume": [1000, 1100, 1200, 1300],
            },
            index=dates,
        )

    fake.download = download
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    panel = download_yahoo(["TEST"], start="2024-01-01", end="2024-01-10")

    assert captured["auto_adjust"] is True
    assert captured["actions"] is False
    assert not panel.empty
