from __future__ import annotations

import pandas as pd


def causal_rank_ewma(predictions: pd.DataFrame, *, span: int) -> pd.DataFrame:
    """Causally smooth daily cross-sectional prediction ranks by symbol.

    Each date's model scores are first converted to centred percentile ranks,
    making the transformation invariant to score scale across walk-forward
    folds. EWMA uses only current and past ranked scores. The returned frame
    preserves exactly the original prediction rows.
    """
    if span < 2:
        raise ValueError("span must be >= 2")
    required = {"y_true", "y_pred", "fold"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"predictions missing columns: {sorted(missing)}")
    if predictions.empty:
        return predictions.copy()

    out = predictions.copy().sort_index()
    ranked = (
        out["y_pred"]
        .groupby(level="date", sort=True)
        .rank(method="average", pct=True)
        .sub(0.5)
    )
    wide = ranked.unstack("symbol").sort_index()
    smooth = wide.ewm(span=span, adjust=False, min_periods=1, ignore_na=True).mean()
    smooth_long = smooth.stack().rename("y_pred")
    smooth_long.index = smooth_long.index.set_names(["date", "symbol"])
    out["y_pred"] = smooth_long.reindex(out.index)
    return out.dropna(subset=["y_pred"])
