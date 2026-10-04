from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, minimize


def rank_weights(
    scores: pd.Series,
    *,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
) -> pd.Series:
    """Dollar-neutral monotone rank portfolio with gross and name caps.

    Steps: centred percentile ranks -> demean -> scale to the gross limit ->
    clip each name at the cap -> restore dollar neutrality by scaling down the
    heavier side (longs or shorts) to match the lighter one.

    The final step keeps every weight inside the cap. Re-demeaning after an
    asymmetric clip (the earlier implementation) could push a weight back
    above the cap when scores were tied. For distinct scores the two
    constructions give identical weights, because the clip is then symmetric.
    """
    s = scores.dropna().astype(float)
    if len(s) < 2:
        return pd.Series(0.0, index=scores.index)
    ranks = s.rank(method="average", pct=True) - 0.5
    w = ranks - ranks.mean()
    if float(np.abs(w).sum()) > 0:
        w = w * (gross_limit / float(np.abs(w).sum()))
    w = w.clip(-max_abs_weight, max_abs_weight)
    long_side = float(w[w > 0].sum())
    short_side = float(-w[w < 0].sum())
    if long_side > 0 and short_side > 0:
        side = min(long_side, short_side)
        w = w.where(w <= 0, w * (side / long_side))
        w = w.where(w >= 0, w * (side / short_side))
    else:
        w = w - w.mean()
    gross = float(np.abs(w).sum())
    if gross > gross_limit and gross > 0:
        w = w * (gross_limit / gross)
    out = pd.Series(0.0, index=scores.index, dtype=float)
    out.loc[w.index] = w
    return out


def turnover_budget_projection(
    target: pd.Series,
    previous: pd.Series | None,
    *,
    turnover_budget: float,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
    tolerance: float = 1e-7,
) -> tuple[pd.Series, dict[str, object]]:
    """Project a target portfolio onto an exact L1 turnover budget.

    The convex programme minimises squared Euclidean distance to the target
    subject to dollar neutrality, gross exposure, per-name bounds and
    sum(abs(w - w_prev)) <= turnover_budget.

    Absolute-value constraints are represented with auxiliary variables, so the
    SLSQP problem has a smooth quadratic objective and linear constraints.
    """
    if turnover_budget <= 0:
        raise ValueError("turnover_budget must be positive")
    t = target.astype(float).copy()
    p = (
        pd.Series(0.0, index=t.index, dtype=float)
        if previous is None
        else previous.reindex(t.index).fillna(0.0).astype(float)
    )
    if len(t) < 2:
        raise ValueError("target must contain at least two assets")

    desired_turnover = float((t - p).abs().sum())
    if desired_turnover <= turnover_budget + tolerance:
        info = {
            "solver_success": True,
            "used_fallback": False,
            "message": "target_within_budget",
            "desired_turnover": desired_turnover,
            "actual_turnover": desired_turnover,
            "tracking_error": 0.0,
            "binding": bool(abs(desired_turnover - turnover_budget) <= 1e-6),
        }
        return t.rename(target.name or "weight"), info

    n = len(t)
    target_values = t.to_numpy(dtype=float)
    prev_values = p.to_numpy(dtype=float)

    # x = [w (n), turnover auxiliaries u (n), gross auxiliaries g (n)]
    x0 = np.concatenate(
        [
            prev_values,
            np.zeros(n, dtype=float),
            np.abs(prev_values),
        ]
    )

    lower = np.concatenate(
        [
            np.full(n, -max_abs_weight),
            np.zeros(n),
            np.zeros(n),
        ]
    )
    upper = np.concatenate(
        [
            np.full(n, max_abs_weight),
            np.full(n, turnover_budget),
            np.full(n, gross_limit),
        ]
    )

    rows: list[np.ndarray] = []
    lbs: list[float] = []
    ubs: list[float] = []

    # u_i >= |w_i - prev_i|
    for i in range(n):
        row = np.zeros(3 * n)
        row[i] = -1.0
        row[n + i] = 1.0
        rows.append(row)
        lbs.append(-prev_values[i])
        ubs.append(np.inf)

        row = np.zeros(3 * n)
        row[i] = 1.0
        row[n + i] = 1.0
        rows.append(row)
        lbs.append(prev_values[i])
        ubs.append(np.inf)

    # g_i >= |w_i|
    for i in range(n):
        row = np.zeros(3 * n)
        row[i] = -1.0
        row[2 * n + i] = 1.0
        rows.append(row)
        lbs.append(0.0)
        ubs.append(np.inf)

        row = np.zeros(3 * n)
        row[i] = 1.0
        row[2 * n + i] = 1.0
        rows.append(row)
        lbs.append(0.0)
        ubs.append(np.inf)

    row = np.zeros(3 * n)
    row[n : 2 * n] = 1.0
    rows.append(row)
    lbs.append(-np.inf)
    ubs.append(turnover_budget)

    row = np.zeros(3 * n)
    row[2 * n :] = 1.0
    rows.append(row)
    lbs.append(-np.inf)
    ubs.append(gross_limit)

    inequality = LinearConstraint(np.vstack(rows), np.asarray(lbs), np.asarray(ubs))
    neutrality_row = np.zeros((1, 3 * n))
    neutrality_row[0, :n] = 1.0
    neutrality = LinearConstraint(neutrality_row, np.array([0.0]), np.array([0.0]))

    tiny = 1e-10

    def objective(x: np.ndarray) -> float:
        w = x[:n]
        return float(np.square(w - target_values).sum() + tiny * x[n:].sum())

    def gradient(x: np.ndarray) -> np.ndarray:
        grad = np.full(3 * n, tiny, dtype=float)
        grad[:n] = 2.0 * (x[:n] - target_values)
        return grad

    result = minimize(
        objective,
        x0,
        jac=gradient,
        method="SLSQP",
        bounds=Bounds(lower, upper),
        constraints=[inequality, neutrality],
        options={"maxiter": 300, "ftol": 1e-12, "disp": False},
    )

    candidate = pd.Series(result.x[:n], index=t.index, dtype=float)
    actual_turnover = float((candidate - p).abs().sum())
    neutral_error = abs(float(candidate.sum()))
    gross = float(candidate.abs().sum())
    cap = float(candidate.abs().max())

    feasible = bool(
        result.success
        and actual_turnover <= turnover_budget + tolerance
        and neutral_error <= tolerance
        and gross <= gross_limit + tolerance
        and cap <= max_abs_weight + tolerance
    )

    used_fallback = False
    message = str(result.message)
    if not feasible:
        used_fallback = True
        alpha = min(1.0, turnover_budget / desired_turnover)
        candidate = p + alpha * (t - p)
        actual_turnover = float((candidate - p).abs().sum())
        message = f"fallback_proportional_after: {result.message}"

    tracking_error = float(np.sqrt(np.square(candidate.to_numpy() - target_values).sum()))
    info = {
        "solver_success": feasible,
        "used_fallback": used_fallback,
        "message": message,
        "desired_turnover": desired_turnover,
        "actual_turnover": actual_turnover,
        "tracking_error": tracking_error,
        "binding": bool(abs(actual_turnover - turnover_budget) <= 1e-6),
    }
    return candidate.rename(target.name or "weight"), info


def turnover_budget_path(
    target_weights: pd.Series,
    *,
    turnover_budget: float,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
    force_final_zero: bool = False,
) -> tuple[pd.Series, pd.DataFrame]:
    """Apply the turnover-budget projection causally through time."""
    if target_weights.empty:
        return target_weights.copy(), pd.DataFrame()
    if not isinstance(target_weights.index, pd.MultiIndex) or list(target_weights.index.names) != ["date", "symbol"]:
        raise ValueError("target_weights must use a MultiIndex named ['date', 'symbol']")

    target = target_weights.unstack("symbol").sort_index().fillna(0.0)
    if force_final_zero and not np.allclose(target.iloc[-1].to_numpy(dtype=float), 0.0):
        raise ValueError("force_final_zero requires an all-zero final target row")

    previous = pd.Series(0.0, index=target.columns, dtype=float)
    rows: list[pd.Series] = []
    diagnostics: list[dict[str, object]] = []

    for i, (date, desired) in enumerate(target.iterrows()):
        terminal = bool(force_final_zero and i == len(target) - 1)
        if terminal:
            current = pd.Series(0.0, index=target.columns, dtype=float)
            actual_turnover = float((current - previous).abs().sum())
            info = {
                "solver_success": True,
                "used_fallback": False,
                "message": "forced_terminal_liquidation",
                "desired_turnover": actual_turnover,
                "actual_turnover": actual_turnover,
                "tracking_error": 0.0,
                "binding": False,
            }
        else:
            current, info = turnover_budget_projection(
                desired,
                previous,
                turnover_budget=turnover_budget,
                gross_limit=gross_limit,
                max_abs_weight=max_abs_weight,
            )

        current.name = date
        rows.append(current)
        diagnostics.append(
            {
                "date": pd.Timestamp(date),
                **info,
                "terminal_liquidation": terminal,
            }
        )
        previous = current

    wide = pd.DataFrame(rows, index=target.index)
    out = wide.stack()
    out.index = out.index.set_names(["date", "symbol"])
    diag = pd.DataFrame(diagnostics).set_index("date")
    return out.sort_index().rename(target_weights.name or "weight"), diag


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


def no_trade_band_projection(
    target: pd.Series,
    previous: pd.Series | None,
    *,
    no_trade_band: float,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
    tolerance: float = 1e-7,
) -> tuple[pd.Series, dict[str, object]]:
    """Project toward target while freezing small desired position changes.

    Names with abs(target - previous) <= no_trade_band remain unchanged.
    Active names may move only between their previous and target weights, so
    the solver cannot overshoot the desired signal direction.
    """
    if no_trade_band < 0:
        raise ValueError("no_trade_band must be non-negative")
    t = target.astype(float).copy()
    p = (
        pd.Series(0.0, index=t.index, dtype=float)
        if previous is None
        else previous.reindex(t.index).fillna(0.0).astype(float)
    )
    if len(t) < 2:
        raise ValueError("target must contain at least two assets")

    delta = t - p
    active = delta.abs() > no_trade_band
    desired_l1 = float(delta.abs().sum())
    ignored_l1 = float(delta.loc[~active].abs().sum())
    ignored_fraction = ignored_l1 / desired_l1 if desired_l1 > 0 else 0.0

    if not bool(active.any()):
        info = {
            "solver_success": True,
            "used_fallback": False,
            "message": "no_active_names",
            "desired_turnover": desired_l1,
            "actual_turnover": 0.0,
            "tracking_error": float(np.sqrt(np.square((p - t).to_numpy()).sum())),
            "active_fraction": 0.0,
            "held_fraction": 1.0,
            "ignored_l1_fraction": ignored_fraction,
            "no_discretionary_trade": True,
        }
        return p.rename(target.name or "weight"), info

    n = len(t)
    target_values = t.to_numpy(dtype=float)
    prev_values = p.to_numpy(dtype=float)
    active_values = active.to_numpy(dtype=bool)

    w_lower = np.empty(n, dtype=float)
    w_upper = np.empty(n, dtype=float)
    for i in range(n):
        if active_values[i]:
            w_lower[i] = max(-max_abs_weight, min(prev_values[i], target_values[i]))
            w_upper[i] = min(max_abs_weight, max(prev_values[i], target_values[i]))
        else:
            w_lower[i] = prev_values[i]
            w_upper[i] = prev_values[i]

    # x = [w (n), gross auxiliaries g (n)]
    x0 = np.concatenate([prev_values, np.abs(prev_values)])
    lower = np.concatenate([w_lower, np.zeros(n)])
    upper = np.concatenate([w_upper, np.full(n, gross_limit)])

    rows: list[np.ndarray] = []
    lbs: list[float] = []
    ubs: list[float] = []

    # g_i >= |w_i|
    for i in range(n):
        row = np.zeros(2 * n)
        row[i] = -1.0
        row[n + i] = 1.0
        rows.append(row)
        lbs.append(0.0)
        ubs.append(np.inf)

        row = np.zeros(2 * n)
        row[i] = 1.0
        row[n + i] = 1.0
        rows.append(row)
        lbs.append(0.0)
        ubs.append(np.inf)

    row = np.zeros(2 * n)
    row[n:] = 1.0
    rows.append(row)
    lbs.append(-np.inf)
    ubs.append(gross_limit)

    gross_constraint = LinearConstraint(
        np.vstack(rows),
        np.asarray(lbs),
        np.asarray(ubs),
    )
    neutrality_row = np.zeros((1, 2 * n))
    neutrality_row[0, :n] = 1.0
    neutrality = LinearConstraint(
        neutrality_row,
        np.array([0.0]),
        np.array([0.0]),
    )

    tiny = 1e-10

    def objective(x: np.ndarray) -> float:
        w = x[:n]
        return float(np.square(w - target_values).sum() + tiny * x[n:].sum())

    def gradient(x: np.ndarray) -> np.ndarray:
        grad = np.full(2 * n, tiny, dtype=float)
        grad[:n] = 2.0 * (x[:n] - target_values)
        return grad

    result = minimize(
        objective,
        x0,
        jac=gradient,
        method="SLSQP",
        bounds=Bounds(lower, upper),
        constraints=[gross_constraint, neutrality],
        options={"maxiter": 300, "ftol": 1e-12, "disp": False},
    )

    candidate = pd.Series(result.x[:n], index=t.index, dtype=float)
    actual_turnover = float((candidate - p).abs().sum())
    neutral_error = abs(float(candidate.sum()))
    gross = float(candidate.abs().sum())
    cap = float(candidate.abs().max())
    bounds_ok = bool(
        np.all(candidate.to_numpy() >= w_lower - tolerance)
        and np.all(candidate.to_numpy() <= w_upper + tolerance)
    )

    feasible = bool(
        result.success
        and neutral_error <= tolerance
        and gross <= gross_limit + tolerance
        and cap <= max_abs_weight + tolerance
        and bounds_ok
    )

    used_fallback = False
    message = str(result.message)
    if not feasible:
        used_fallback = True
        candidate = p.copy()
        actual_turnover = 0.0
        message = f"fallback_previous_after: {result.message}"

    tracking_error = float(
        np.sqrt(np.square(candidate.to_numpy() - target_values).sum())
    )
    info = {
        "solver_success": feasible,
        "used_fallback": used_fallback,
        "message": message,
        "desired_turnover": desired_l1,
        "actual_turnover": actual_turnover,
        "tracking_error": tracking_error,
        "active_fraction": float(active.mean()),
        "held_fraction": float((~active).mean()),
        "ignored_l1_fraction": ignored_fraction,
        "no_discretionary_trade": bool(actual_turnover <= tolerance),
    }
    return candidate.rename(target.name or "weight"), info


def no_trade_band_path(
    target_weights: pd.Series,
    *,
    no_trade_band: float,
    gross_limit: float = 1.0,
    max_abs_weight: float = 0.08,
    force_final_zero: bool = False,
) -> tuple[pd.Series, pd.DataFrame]:
    """Apply a no-trade-band projection causally through time."""
    if target_weights.empty:
        return target_weights.copy(), pd.DataFrame()
    if (
        not isinstance(target_weights.index, pd.MultiIndex)
        or list(target_weights.index.names) != ["date", "symbol"]
    ):
        raise ValueError(
            "target_weights must use a MultiIndex named ['date', 'symbol']"
        )

    target = target_weights.unstack("symbol").sort_index().fillna(0.0)
    if force_final_zero and not np.allclose(
        target.iloc[-1].to_numpy(dtype=float), 0.0
    ):
        raise ValueError(
            "force_final_zero requires an all-zero final target row"
        )

    previous = pd.Series(0.0, index=target.columns, dtype=float)
    rows: list[pd.Series] = []
    diagnostics: list[dict[str, object]] = []

    for i, (date, desired) in enumerate(target.iterrows()):
        terminal = bool(force_final_zero and i == len(target) - 1)
        if terminal:
            current = pd.Series(0.0, index=target.columns, dtype=float)
            actual_turnover = float((current - previous).abs().sum())
            info = {
                "solver_success": True,
                "used_fallback": False,
                "message": "forced_terminal_liquidation",
                "desired_turnover": actual_turnover,
                "actual_turnover": actual_turnover,
                "tracking_error": 0.0,
                "active_fraction": 1.0 if actual_turnover > 0 else 0.0,
                "held_fraction": 0.0 if actual_turnover > 0 else 1.0,
                "ignored_l1_fraction": 0.0,
                "no_discretionary_trade": False,
            }
        else:
            current, info = no_trade_band_projection(
                desired,
                previous,
                no_trade_band=no_trade_band,
                gross_limit=gross_limit,
                max_abs_weight=max_abs_weight,
            )

        current.name = date
        rows.append(current)
        diagnostics.append(
            {
                "date": pd.Timestamp(date),
                **info,
                "terminal_liquidation": terminal,
            }
        )
        previous = current

    wide = pd.DataFrame(rows, index=target.index)
    out = wide.stack()
    out.index = out.index.set_names(["date", "symbol"])
    diag = pd.DataFrame(diagnostics).set_index("date")
    return out.sort_index().rename(target_weights.name or "weight"), diag
