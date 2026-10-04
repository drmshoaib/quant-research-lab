from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def rank_weights(
    scores: pd.Series,
    *,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
) -> pd.Series:
    """Dollar-neutral monotone rank portfolio with gross and name caps."""
    s = scores.dropna().astype(float)
    if len(s) < 2:
        return pd.Series(0.0, index=scores.index)
    ranks = s.rank(method="average", pct=True) - 0.5
    w = ranks - ranks.mean()
    if float(np.abs(w).sum()) > 0:
        w = w * (gross_limit / float(np.abs(w).sum()))
    w = w.clip(-max_abs_weight, max_abs_weight)
    w = w - w.mean()
    gross = float(np.abs(w).sum())
    if gross > gross_limit and gross > 0:
        w = w * (gross_limit / gross)
    out = pd.Series(0.0, index=scores.index, dtype=float)
    out.loc[w.index] = w
    return out


def optimise_weights(
    alpha: pd.Series,
    covariance: pd.DataFrame,
    previous: pd.Series | None = None,
    *,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
    risk_aversion: float = 5.0,
    turnover_penalty: float = 0.002,
) -> pd.Series:
    """Constrained alpha/risk/turnover optimisation using SLSQP.

    Objective: maximise alpha'w - lambda*w'Sigma*w - gamma*|w-w_prev|_1
    subject to dollar neutrality, gross exposure, and per-name bounds.
    """
    names = alpha.dropna().index.intersection(covariance.index).intersection(covariance.columns)
    if len(names) < 2:
        return pd.Series(0.0, index=alpha.index)
    a = alpha.loc[names].to_numpy(dtype=float)
    cov = covariance.loc[names, names].to_numpy(dtype=float)
    cov = 0.5 * (cov + cov.T) + np.eye(len(names)) * 1e-8
    prev = np.zeros(len(names)) if previous is None else previous.reindex(names).fillna(0.0).to_numpy(dtype=float)
    eps = 1e-8

    def smooth_abs(x: np.ndarray) -> np.ndarray:
        return np.sqrt(x * x + eps)

    def objective(w: np.ndarray) -> float:
        utility = a @ w - risk_aversion * (w @ cov @ w) - turnover_penalty * smooth_abs(w - prev).sum()
        return -float(utility)

    constraints = [
        {"type": "eq", "fun": lambda w: float(w.sum())},
        {"type": "ineq", "fun": lambda w: float(gross_limit - smooth_abs(w).sum())},
    ]
    x0 = rank_weights(pd.Series(a, index=names), gross_limit=min(gross_limit, 0.9 * gross_limit), max_abs_weight=max_abs_weight).to_numpy()
    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=[(-max_abs_weight, max_abs_weight)] * len(names),
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if not result.success:
        w = rank_weights(pd.Series(a, index=names), gross_limit=gross_limit, max_abs_weight=max_abs_weight)
    else:
        w = pd.Series(result.x, index=names)
    out = pd.Series(0.0, index=alpha.index, dtype=float)
    out.loc[names] = w
    return out
