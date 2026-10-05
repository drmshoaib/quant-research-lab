from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import build_features
from .metrics import hac_mean_test, rank_ic_by_date
from .pipeline import ResearchFrames
from .targets import eligible_decision_dates, forward_relative_return


@dataclass(frozen=True)
class PermutationResult:
    observed_mean_ic: float
    null_mean_ics: np.ndarray
    empirical_p_value: float
    dates_used: int
    symbols_used: int


def prepare_horizon_research_frame(
    panel: pd.DataFrame,
    *,
    horizon: int,
    holdout_dates: pd.DatetimeIndex,
    min_assets: int = 8,
) -> ResearchFrames:
    """Build a development frame for an alternate horizon without touching holdout outcomes."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    holdout = pd.DatetimeIndex(pd.to_datetime(holdout_dates).unique()).sort_values()
    if holdout.empty:
        raise ValueError("holdout_dates is empty")

    X = build_features(panel)
    y = forward_relative_return(panel, horizon=horizon)
    eligible = eligible_decision_dates(panel, horizon=horizon, min_assets=min_assets)

    holdout_start = pd.Timestamp(holdout[0])
    # The manifest was frozen on the primary (h=5) calendar, so it cannot be
    # required to equal the final eligible block of *this* horizon: a longer
    # horizon loses more trailing dates, a shorter one keeps extra ones after
    # the manifest's end. What must hold is that the manifest starts inside
    # this horizon's calendar, so that the embargo below is meaningful, and
    # that every eligible date from the hold-out start onwards is kept out of
    # development, which the slicing below guarantees.
    if holdout_start > eligible[-1]:
        raise ValueError("holdout manifest starts after the last eligible date for this horizon")
    before_holdout = eligible[eligible < holdout_start]
    embargo_days = horizon + 1
    if len(before_holdout) <= embargo_days:
        raise ValueError("insufficient pre-holdout dates for horizon-specific embargo")

    embargo = before_holdout[-embargo_days:]
    development_eligible = before_holdout[:-embargo_days]

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


def chronological_ic_blocks(
    ic: pd.Series,
    *,
    n_blocks: int = 3,
    hac_lag: int = 4,
) -> list[dict[str, object]]:
    """Split ordered IC dates into nearly equal consecutive blocks."""
    s = pd.Series(ic, dtype=float).dropna().sort_index()
    if n_blocks < 2:
        raise ValueError("n_blocks must be >= 2")
    if len(s) < n_blocks:
        raise ValueError("not enough IC observations for requested blocks")

    positions = np.array_split(np.arange(len(s)), n_blocks)
    out: list[dict[str, object]] = []
    for block_number, pos in enumerate(positions, start=1):
        block = s.iloc[pos]
        test = hac_mean_test(block, maxlags=hac_lag)
        out.append(
            {
                "block": block_number,
                "start": str(pd.Timestamp(block.index[0]).date()),
                "end": str(pd.Timestamp(block.index[-1]).date()),
                "n_dates": int(len(block)),
                "mean_ic": float(block.mean()),
                "median_ic": float(block.median()),
                "hac": test,
            }
        )
    return out


def global_symbol_permutation_test(
    predictions: pd.DataFrame,
    *,
    n_permutations: int = 999,
    seed: int = 20261004,
) -> PermutationResult:
    """Global symbol-identity permutation test for mean daily Spearman rank IC.

    A single symbol permutation is applied to every date in each replicate,
    preserving complete prediction paths and serial dependence.
    """
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    required = {"y_true", "y_pred"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"predictions missing columns: {sorted(missing)}")

    truth = predictions["y_true"].unstack("symbol").sort_index()
    score = predictions["y_pred"].unstack("symbol").reindex(
        index=truth.index,
        columns=truth.columns,
    )
    complete = truth.notna().all(axis=1) & score.notna().all(axis=1)
    truth = truth.loc[complete]
    score = score.loc[complete]
    if truth.empty:
        raise ValueError("no complete dates available for permutation test")
    if truth.shape[1] < 4:
        raise ValueError("permutation test requires at least four symbols")

    truth_rank = truth.rank(axis=1, method="average").to_numpy(dtype=float)
    score_rank = score.rank(axis=1, method="average").to_numpy(dtype=float)

    truth_centered = truth_rank - truth_rank.mean(axis=1, keepdims=True)
    score_centered = score_rank - score_rank.mean(axis=1, keepdims=True)

    truth_norm = np.sqrt(np.square(truth_centered).sum(axis=1))
    score_norm = np.sqrt(np.square(score_centered).sum(axis=1))
    denominator = truth_norm * score_norm
    if np.any(denominator <= 0):
        raise ValueError("degenerate rank vectors in permutation test")

    observed_daily = (
        truth_centered * score_centered
    ).sum(axis=1) / denominator
    observed_mean = float(observed_daily.mean())

    rng = np.random.default_rng(seed)
    n_symbols = truth.shape[1]
    null = np.empty(n_permutations, dtype=float)
    for i in range(n_permutations):
        perm = rng.permutation(n_symbols)
        daily = (
            truth_centered * score_centered[:, perm]
        ).sum(axis=1) / denominator
        null[i] = float(daily.mean())

    p = float((1 + np.sum(null >= observed_mean)) / (n_permutations + 1))
    return PermutationResult(
        observed_mean_ic=observed_mean,
        null_mean_ics=null,
        empirical_p_value=p,
        dates_used=int(truth.shape[0]),
        symbols_used=int(truth.shape[1]),
    )


def _centred_rank_matrices(predictions: pd.DataFrame):
    """Shared preparation for the two placebo tests: centred rank matrices and norms."""
    required = {"y_true", "y_pred"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"predictions missing columns: {sorted(missing)}")
    truth = predictions["y_true"].unstack("symbol").sort_index()
    score = predictions["y_pred"].unstack("symbol").reindex(index=truth.index, columns=truth.columns)
    complete = truth.notna().all(axis=1) & score.notna().all(axis=1)
    truth = truth.loc[complete]
    score = score.loc[complete]
    if truth.empty:
        raise ValueError("no complete dates available for permutation test")
    if truth.shape[1] < 4:
        raise ValueError("permutation test requires at least four symbols")
    tr = truth.rank(axis=1, method="average").to_numpy(dtype=float)
    sr = score.rank(axis=1, method="average").to_numpy(dtype=float)
    tc = tr - tr.mean(axis=1, keepdims=True)
    sc = sr - sr.mean(axis=1, keepdims=True)
    denominator = np.sqrt(np.square(tc).sum(axis=1)) * np.sqrt(np.square(sc).sum(axis=1))
    if np.any(denominator <= 0):
        raise ValueError("degenerate rank vectors in permutation test")
    return tc, sc, denominator, truth.shape


def global_date_permutation_test(
    predictions: pd.DataFrame,
    *,
    n_permutations: int = 999,
    seed: int = 20261005,
    method: str = "shift",
    min_shift: int = 21,
) -> PermutationResult:
    """Timing placebo: realign the whole cross-section of scores to the wrong dates.

    This is the complement of ``global_symbol_permutation_test``. That test
    keeps each symbol's score path intact and relabels *symbols*, so a static
    asset-class tilt (scores that never change) is rejected by it. This test
    keeps each date's cross-section of scores intact and relabels *dates*, so a
    static tilt is invariant under the null and cannot be rejected: whatever
    IC survives here is attributable to *when* the scores said what they said.

    Null hypothesis: the scores carry no date-specific information about the
    outcomes, i.e. the mean IC would be unchanged if the score cross-sections
    were attached to other dates.

    method="shift" (default): each replicate applies one circular shift of at
    least ``min_shift`` sessions to the score matrix. Shifting preserves the
    serial dependence of the score paths (their autocorrelation, and that of
    the overlapping targets), so the null distribution reflects the same
    dependence as the observed statistic. ``min_shift`` should exceed the
    memory of the scores and the target horizon (21 sessions is about a month,
    well beyond h+1 = 6 and the 60-session feature windows' typical
    autocorrelation of the ranks); with T dates there are T - 2*min_shift + 1
    admissible shifts, so for large n_permutations shifts repeat.

    method="permute": a single random permutation of dates per replicate. It
    destroys serial dependence and is therefore anti-conservative when scores
    are persistent; it is provided for comparison and teaching, not as the
    primary placebo.
    """
    if n_permutations < 1:
        raise ValueError("n_permutations must be >= 1")
    if method not in {"shift", "permute"}:
        raise ValueError("method must be 'shift' or 'permute'")
    tc, sc, denominator, (n_dates, n_symbols) = _centred_rank_matrices(predictions)
    if method == "shift" and n_dates < 2 * min_shift + 1:
        raise ValueError("not enough dates for the requested minimum shift")

    observed_mean = float(((tc * sc).sum(axis=1) / denominator).mean())
    rng = np.random.default_rng(seed)
    null = np.empty(n_permutations, dtype=float)
    for i in range(n_permutations):
        if method == "shift":
            k = int(rng.integers(min_shift, n_dates - min_shift + 1))
            moved = np.roll(sc, k, axis=0)
        else:
            moved = sc[rng.permutation(n_dates), :]
        # Each date's own norm is unchanged by moving whole rows, so the denominator
        # must pair the truth norm of date t with the score norm of the row now at t.
        score_norm = np.sqrt(np.square(moved).sum(axis=1))
        truth_norm = denominator / np.sqrt(np.square(sc).sum(axis=1))
        null[i] = float(((tc * moved).sum(axis=1) / (truth_norm * score_norm)).mean())

    p = float((1 + np.sum(null >= observed_mean)) / (n_permutations + 1))
    return PermutationResult(
        observed_mean_ic=observed_mean,
        null_mean_ics=null,
        empirical_p_value=p,
        dates_used=int(n_dates),
        symbols_used=int(n_symbols),
    )


def broad_asset_group_map(universe: pd.DataFrame) -> dict[str, list[str]]:
    """Map the repository's ETF taxonomy into the four EXP-006 broad groups."""
    if not {"symbol", "group"}.issubset(universe.columns):
        raise ValueError("universe must contain symbol and group columns")

    buckets = {
        "US_risk_assets": {
            "US_equity",
            "US_sector",
            "real_estate",
            "biotech",
            "retail",
        },
        "International_equity": {
            "developed_ex_US",
            "emerging_markets",
            "Japan",
            "United_Kingdom",
            "China",
        },
        "Fixed_income": {
            "long_treasury",
            "intermediate_treasury",
            "short_treasury",
            "investment_grade_credit",
            "high_yield_credit",
        },
        "Commodities": {
            "gold",
            "silver",
            "oil",
            "agriculture",
        },
    }
    groups: dict[str, list[str]] = {}
    assigned: set[str] = set()
    for broad, labels in buckets.items():
        symbols = (
            universe.loc[universe["group"].isin(labels), "symbol"]
            .astype(str)
            .tolist()
        )
        groups[broad] = symbols
        assigned.update(symbols)

    all_symbols = set(universe["symbol"].astype(str))
    if assigned != all_symbols:
        missing = sorted(all_symbols.difference(assigned))
        extra = sorted(assigned.difference(all_symbols))
        raise ValueError(
            f"broad group mapping mismatch; missing={missing}, extra={extra}"
        )
    return groups


def asset_group_diagnostics(
    predictions: pd.DataFrame,
    groups: dict[str, list[str]],
    *,
    baseline_mean_ic: float,
    hac_lag: int = 4,
) -> dict[str, object]:
    """Within-group and leave-one-group-out IC diagnostics."""
    symbols = predictions.index.get_level_values("symbol")

    within: dict[str, dict[str, object]] = {}
    leave_out: dict[str, dict[str, object]] = {}

    for name, group_symbols in groups.items():
        in_mask = symbols.isin(group_symbols)
        group_pred = predictions.loc[np.asarray(in_mask)]
        group_ic = rank_ic_by_date(group_pred, min_assets=4)
        group_hac = hac_mean_test(group_ic, maxlags=hac_lag)
        within[name] = {
            "n_symbols": int(len(group_symbols)),
            "n_dates": int(len(group_ic)),
            "mean_ic": float(group_ic.mean()),
            "median_ic": float(group_ic.median()),
            "hac": group_hac,
        }

        out_mask = ~symbols.isin(group_symbols)
        out_pred = predictions.loc[np.asarray(out_mask)]
        out_ic = rank_ic_by_date(out_pred, min_assets=8)
        out_hac = hac_mean_test(out_ic, maxlags=hac_lag)
        mean_ic = float(out_ic.mean())
        leave_out[name] = {
            "n_symbols_remaining": int(
                out_pred.index.get_level_values("symbol").nunique()
            ),
            "n_dates": int(len(out_ic)),
            "mean_ic": mean_ic,
            "median_ic": float(out_ic.median()),
            "retention_vs_full": (
                mean_ic / baseline_mean_ic
                if baseline_mean_ic != 0
                else float("nan")
            ),
            "hac": out_hac,
        }

    return {"within_group": within, "leave_one_group_out": leave_out}
