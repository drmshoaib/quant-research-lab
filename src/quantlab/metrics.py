from __future__ import annotations

import math

import numpy as np
import pandas as pd
import statsmodels.api as sm


def rank_ic_by_date(predictions: pd.DataFrame, min_assets: int = 8) -> pd.Series:
    required = {"y_true", "y_pred"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"predictions missing columns: {sorted(missing)}")

    def _ic(g: pd.DataFrame) -> float:
        g = g[["y_true", "y_pred"]].dropna()
        if len(g) < min_assets or g["y_true"].nunique() < 2 or g["y_pred"].nunique() < 2:
            return np.nan
        return float(g["y_true"].corr(g["y_pred"], method="spearman"))

    return predictions.groupby(level="date", sort=True).apply(_ic).dropna().rename("rank_ic")


def hac_mean_test(series: pd.Series, maxlags: int = 4) -> dict[str, float]:
    s = pd.Series(series, dtype=float).dropna()
    if len(s) < max(10, maxlags + 3):
        return {"mean": float(s.mean()) if len(s) else math.nan, "t_stat": math.nan, "p_value": math.nan}
    X = np.ones((len(s), 1))
    fit = sm.OLS(s.to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return {"mean": float(fit.params[0]), "t_stat": float(fit.tvalues[0]), "p_value": float(fit.pvalues[0])}


def rank_ic_diagnostics(
    ic: pd.Series,
    predictions: pd.DataFrame,
    *,
    hac_lag: int = 4,
    min_year_days: int = 20,
) -> dict[str, object]:
    """Summarise development rank IC with pre-declared temporal diagnostics."""
    s = pd.Series(ic, dtype=float).dropna().sort_index()
    std = float(s.std(ddof=1)) if len(s) > 1 else math.nan
    mean = float(s.mean()) if len(s) else math.nan
    median = float(s.median()) if len(s) else math.nan
    ic_ir = mean / std if np.isfinite(std) and std > 0 else math.nan
    positive_fraction = float((s > 0).mean()) if len(s) else math.nan

    fold_by_date = predictions["fold"].groupby(level="date").first().rename("fold")
    fold_frame = pd.DataFrame({"rank_ic": s}).join(fold_by_date, how="inner").dropna()
    fold_means = fold_frame.groupby("fold")["rank_ic"].mean().sort_index()
    median_fold_ic = float(fold_means.median()) if len(fold_means) else math.nan

    annual = (
        pd.DataFrame({"rank_ic": s})
        .assign(year=lambda x: x.index.year)
        .groupby("year")["rank_ic"]
        .agg(["mean", "count"])
    )
    eligible_annual = annual.loc[annual["count"] >= min_year_days]
    positive_year_fraction = (
        float((eligible_annual["mean"] > 0).mean()) if len(eligible_annual) else math.nan
    )

    hac = hac_mean_test(s, maxlags=hac_lag)
    return {
        "n_dates": int(len(s)),
        "mean": mean,
        "median": median,
        "std": std,
        "ic_ir_daily": float(ic_ir),
        "positive_fraction": positive_fraction,
        "hac": hac,
        "fold_mean_ic": {str(int(k)): float(v) for k, v in fold_means.items()},
        "median_fold_ic": median_fold_ic,
        "annual_ic": {
            str(int(year)): {"mean": float(row["mean"]), "count": int(row["count"])}
            for year, row in annual.iterrows()
        },
        "min_year_days": int(min_year_days),
        "positive_year_fraction": positive_year_fraction,
    }


def backtest_summary(daily: pd.DataFrame) -> dict[str, float]:
    if daily.empty:
        return {
            "ann_return": math.nan,
            "ann_vol": math.nan,
            "sharpe": math.nan,
            "max_drawdown": math.nan,
            "avg_turnover": math.nan,
            "ann_turnover": math.nan,
        }
    r = daily["net_return"].fillna(0.0)
    ann_return = float(r.mean() * 252.0)
    ann_vol = float(r.std(ddof=1) * np.sqrt(252.0))
    sharpe = ann_return / ann_vol if ann_vol > 0 else math.nan
    equity = np.exp(r.cumsum())
    drawdown = equity / equity.cummax() - 1.0
    avg_turnover = float(daily["turnover"].mean())
    return {
        "ann_return": ann_return,
        "ann_vol": ann_vol,
        "sharpe": float(sharpe),
        "max_drawdown": float(drawdown.min()),
        "avg_turnover": avg_turnover,
        "ann_turnover": float(avg_turnover * 252.0),
    }
