from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def validate_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Validate and canonicalise a long OHLCV panel indexed by date and symbol."""
    if not isinstance(panel.index, pd.MultiIndex) or list(panel.index.names) != ["date", "symbol"]:
        raise ValueError("panel must use a MultiIndex named ['date', 'symbol']")
    missing = [c for c in REQUIRED_COLUMNS if c not in panel.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    out = panel.copy()
    out.index = pd.MultiIndex.from_arrays(
        [pd.to_datetime(out.index.get_level_values("date")), out.index.get_level_values("symbol").astype(str)],
        names=["date", "symbol"],
    )
    out = out.sort_index()
    if out.index.has_duplicates:
        raise ValueError("panel contains duplicate (date, symbol) rows")
    return out


def load_panel_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    needed = {"date", "symbol", *REQUIRED_COLUMNS}
    missing = needed.difference(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")
    return validate_panel(df.set_index(["date", "symbol"]))


def save_panel_csv(panel: pd.DataFrame, path: str | Path) -> None:
    validate_panel(panel).reset_index().to_csv(path, index=False)


def load_universe(path: str | Path) -> list[str]:
    df = pd.read_csv(path)
    if "symbol" not in df.columns:
        raise ValueError("universe file must contain a 'symbol' column")
    return df["symbol"].dropna().astype(str).tolist()


def download_yahoo(
    symbols: Iterable[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Download OHLCV from Yahoo through yfinance, imported lazily.

    This is a convenience adapter for the public research project. The core
    research code is provider-agnostic and can consume any long OHLCV CSV.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Install the data extra: pip install -e '.[data]'") from exc

    tickers = list(symbols)
    if not tickers:
        raise ValueError("at least one symbol is required")

    raw = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("Yahoo download returned no data")

    frames: list[pd.DataFrame] = []
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance may place ticker at either level depending on version/options.
        lvl0 = set(map(str, raw.columns.get_level_values(0)))
        ticker_first = bool(set(tickers).intersection(lvl0))
        for symbol in tickers:
            if ticker_first:
                if symbol not in raw.columns.get_level_values(0):
                    continue
                sub = raw[symbol].copy()
            else:
                if symbol not in raw.columns.get_level_values(1):
                    continue
                sub = raw.xs(symbol, axis=1, level=1).copy()
            sub.columns = [str(c).lower().replace(" ", "_") for c in sub.columns]
            sub["symbol"] = symbol
            sub["date"] = sub.index
            frames.append(sub.reset_index(drop=True))
    else:
        if len(tickers) != 1:
            raise RuntimeError("unexpected single-level columns for multiple tickers")
        sub = raw.copy()
        sub.columns = [str(c).lower().replace(" ", "_") for c in sub.columns]
        sub["symbol"] = tickers[0]
        sub["date"] = sub.index
        frames.append(sub.reset_index(drop=True))

    panel = pd.concat(frames, ignore_index=True)
    keep = ["date", "symbol", "open", "high", "low", "close", "volume"]
    panel = panel[keep].dropna(subset=["open", "high", "low", "close"])
    return validate_panel(panel.set_index(["date", "symbol"]))
