from __future__ import annotations

import numpy as np
import pandas as pd

from .features import build_features
from .metrics import hac_mean_test, rank_ic_by_date
from .pipeline import ResearchFrames
from .targets import (
    eligible_decision_dates,
    forward_group_relative_return,
)


def inverse_group_map(groups: dict[str, list[str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for group, symbols in groups.items():
        for symbol in symbols:
            if symbol in out:
                raise ValueError(f"symbol appears in multiple groups: {symbol}")
            out[symbol] = group
    return out


def prepare_group_neutral_research_frame(
    panel: pd.DataFrame,
    *,
    symbol_groups: dict[str, str],
    horizon: int,
    holdout_dates: pd.DatetimeIndex,
    holdout_purge_days: int | None = None,
    min_assets: int = 8,
) -> ResearchFrames:
    """Build the group-neutral modelling frame using the frozen holdout boundary."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if holdout_purge_days is None:
        holdout_purge_days = horizon + 1
    if holdout_purge_days < horizon:
        raise ValueError("holdout_purge_days must be at least the prediction horizon")

    holdout = pd.DatetimeIndex(
        pd.to_datetime(holdout_dates).unique()
    ).sort_values()
    if holdout.empty:
        raise ValueError("holdout_dates is empty")

    X = build_features(panel)
    y = forward_group_relative_return(
        panel,
        symbol_groups=symbol_groups,
        horizon=horizon,
    )
    eligible = eligible_decision_dates(
        panel,
        horizon=horizon,
        min_assets=min_assets,
    )

    missing = holdout.difference(eligible)
    if len(missing):
        raise ValueError(
            f"holdout manifest contains ineligible dates: {list(missing[:3])}"
        )
    expected_tail = eligible[-len(holdout):]
    if not holdout.equals(expected_tail):
        raise ValueError(
            "holdout manifest is not the final eligible block of the frozen data window"
        )

    before_holdout = eligible[eligible < holdout[0]]
    if len(before_holdout) <= holdout_purge_days:
        raise ValueError(
            "insufficient pre-holdout dates after applying the holdout embargo"
        )
    embargo = before_holdout[-holdout_purge_days:]
    development_eligible = before_holdout[:-holdout_purge_days]

    frame = X.join(y).dropna().sort_index()
    frame_dates = pd.DatetimeIndex(
        frame.index.get_level_values("date").unique()
    ).sort_values()
    development = development_eligible.intersection(frame_dates)

    return ResearchFrames(
        frame=frame,
        development_dates=development,
        holdout_dates=holdout,
        embargo_dates=embargo,
    )


def within_group_ic_matrix(
    predictions: pd.DataFrame,
    groups: dict[str, list[str]],
    *,
    min_assets: int = 4,
) -> pd.DataFrame:
    """Daily rank IC inside each broad group."""
    symbols = predictions.index.get_level_values("symbol")
    series: list[pd.Series] = []
    for group, group_symbols in groups.items():
        mask = symbols.isin(group_symbols)
        pred = predictions.loc[np.asarray(mask)]
        ic = rank_ic_by_date(pred, min_assets=min_assets).rename(group)
        series.append(ic)
    if not series:
        return pd.DataFrame()
    return pd.concat(series, axis=1).sort_index()


def composite_ic_diagnostics(
    group_ic: pd.DataFrame,
    *,
    non_us_groups: list[str],
    hac_lag: int = 4,
) -> dict[str, object]:
    """Equal-weight group composites and group-specific HAC diagnostics."""
    if group_ic.empty:
        raise ValueError("group_ic is empty")

    full = group_ic.mean(axis=1, skipna=True).dropna().rename("equal_weight_group_ic")
    non_us = (
        group_ic[non_us_groups]
        .mean(axis=1, skipna=True)
        .dropna()
        .rename("equal_weight_non_us_ic")
    )

    group_diag: dict[str, dict[str, object]] = {}
    for group in group_ic.columns:
        s = group_ic[group].dropna()
        group_diag[group] = {
            "n_dates": int(len(s)),
            "mean_ic": float(s.mean()),
            "median_ic": float(s.median()),
            "hac": hac_mean_test(s, maxlags=hac_lag),
        }

    return {
        "equal_weight_four_group": {
            "n_dates": int(len(full)),
            "mean_ic": float(full.mean()),
            "median_ic": float(full.median()),
            "hac": hac_mean_test(full, maxlags=hac_lag),
        },
        "equal_weight_non_us": {
            "n_dates": int(len(non_us)),
            "mean_ic": float(non_us.mean()),
            "median_ic": float(non_us.median()),
            "hac": hac_mean_test(non_us, maxlags=hac_lag),
        },
        "groups": group_diag,
        "_full_series": full,
        "_non_us_series": non_us,
    }
