from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quantlab.backtest import (
    append_liquidation_row,
    run_backtest,
    staggered_weights,
    weights_from_predictions,
)
from quantlab.data import load_panel_csv
from quantlab.metrics import backtest_summary, rank_ic_by_date, rank_ic_diagnostics
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.portfolio import no_trade_band_path
from quantlab.splits import load_date_manifest
from quantlab.targets import next_open_to_open_simple_return


PRUNED8 = [
    "ret_1",
    "mom_20",
    "mom_60",
    "vol_20",
    "vol_60",
    "range_1",
    "volume_z_20",
    "drawdown_60",
]
NO_TRADE_BANDS = [0.005, 0.010, 0.020]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EXP-005 no-trade-band study.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True, help="Frozen adjusted OHLCV CSV.")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--output-dir", default="outputs/exp005")
    return p.parse_args()


def cost_key(cost: float) -> str:
    value = float(cost)
    return str(int(value)) if value.is_integer() else str(value)


def evaluate_weights(
    weights: pd.Series,
    realized: pd.Series,
    costs: list[float],
    base_cost: float,
) -> dict[str, object]:
    sensitivity: dict[str, dict[str, float]] = {}
    base = None
    for cost in costs:
        summary = backtest_summary(
            run_backtest(weights, realized, cost_bps=float(cost))
        )
        sensitivity[cost_key(cost)] = summary
        if float(cost) == float(base_cost):
            base = summary
    if base is None:
        base = backtest_summary(
            run_backtest(weights, realized, cost_bps=base_cost)
        )
    return {"base_cost": base, "cost_sensitivity": sensitivity}


def terminal_liquidation_date(
    target: pd.Series,
    realized_dates: pd.DatetimeIndex,
    holdout_start: pd.Timestamp,
) -> pd.Timestamp:
    last = pd.Timestamp(target.index.get_level_values("date").max())
    candidates = realized_dates[realized_dates > last]
    if not len(candidates):
        raise ValueError("no realised-return date available for terminal liquidation")
    liquidation = pd.Timestamp(candidates[0])
    if liquidation >= pd.Timestamp(holdout_start):
        raise ValueError("terminal liquidation would enter the locked holdout")
    return liquidation


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    panel = load_panel_csv(args.data)
    holdout_dates = load_date_manifest(args.holdout_manifest)
    research = prepare_research_frame(
        panel,
        horizon=int(cfg["horizon"]),
        holdout_days=int(cfg["holdout_days"]),
        holdout_dates=holdout_dates,
        holdout_purge_days=int(
            cfg.get("holdout_purge_days", int(cfg["horizon"]) + 1)
        ),
        min_assets=int(cfg.get("min_assets", 8)),
    )
    realized = next_open_to_open_simple_return(panel)
    realized_dates = pd.DatetimeIndex(
        realized.dropna().index.get_level_values("date").unique()
    ).sort_values()

    pred = walk_forward_predictions(
        research,
        model_name="hist_gb",
        horizon=int(cfg["horizon"]),
        min_train_days=int(cfg["min_train_days"]),
        test_days=int(cfg["test_days"]),
        step_days=int(cfg["step_days"]),
        ridge_alpha=float(cfg["ridge_alpha"]),
        random_state=int(cfg["random_state"]),
        feature_columns=PRUNED8,
    )
    ic = rank_ic_by_date(
        pred,
        min_assets=int(cfg.get("min_assets", 8)),
    )
    ic_diag = rank_ic_diagnostics(
        ic,
        pred,
        hac_lag=max(1, int(cfg["horizon"]) - 1),
        min_year_days=int(cfg.get("min_year_ic_days", 20)),
    )

    cohort = weights_from_predictions(
        pred,
        gross_limit=float(cfg["gross_limit"]),
        max_abs_weight=float(cfg["max_abs_weight"]),
    )
    live_target = staggered_weights(
        cohort,
        horizon=int(cfg["horizon"]),
        decision_dates=realized_dates,
    )
    liquidation_date = terminal_liquidation_date(
        live_target,
        realized_dates,
        research.holdout_dates[0],
    )
    live_target = append_liquidation_row(
        live_target,
        liquidation_date=liquidation_date,
    )

    costs = [
        float(x)
        for x in cfg.get(
            "cost_sensitivity_bps",
            [0, 2, 5, 10, 20],
        )
    ]
    base_cost = float(cfg["cost_bps"])
    instant = evaluate_weights(
        live_target,
        realized,
        costs,
        base_cost,
    )
    instant_turnover = float(
        instant["base_cost"]["ann_turnover"]
    )
    instant_zero_return = float(
        instant["cost_sensitivity"]["0"]["ann_return"]
    )
    instant_base_return = float(
        instant["base_cost"]["ann_return"]
    )
    instant_base_sharpe = float(
        instant["base_cost"]["sharpe"]
    )

    candidates: dict[str, dict[str, object]] = {}
    qualifying: list[tuple[float, dict[str, object]]] = []

    for band in NO_TRADE_BANDS:
        actual, diag = no_trade_band_path(
            live_target,
            no_trade_band=band,
            gross_limit=float(cfg["gross_limit"]),
            max_abs_weight=float(cfg["max_abs_weight"]),
            force_final_zero=True,
        )
        portfolio = evaluate_weights(
            actual,
            realized,
            costs,
            base_cost,
        )

        regular = diag.loc[
            ~diag["terminal_liquidation"]
        ].copy()
        fallback_count = int(
            regular["used_fallback"].sum()
        )
        projected_dates = int(len(regular))
        fallback_rate = (
            fallback_count / projected_dates
            if projected_dates
            else float("nan")
        )
        operationally_valid = bool(
            fallback_rate <= 0.005
        )

        turnover = float(
            portfolio["base_cost"]["ann_turnover"]
        )
        zero_return = float(
            portfolio["cost_sensitivity"]["0"]["ann_return"]
        )
        base_return = float(
            portfolio["base_cost"]["ann_return"]
        )
        base_sharpe = float(
            portfolio["base_cost"]["sharpe"]
        )
        turnover_reduction = (
            1.0 - turnover / instant_turnover
        )
        zero_retention = (
            zero_return / instant_zero_return
            if instant_zero_return > 0
            else float("nan")
        )

        gates = {
            "operationally_valid": operationally_valid,
            "turnover_reduction_ge_0_25": bool(
                turnover_reduction >= 0.25
            ),
            "zero_cost_return_retention_ge_0_80": bool(
                instant_zero_return > 0
                and zero_retention >= 0.80
            ),
            "net_return_5bps_gt_instant": bool(
                base_return > instant_base_return
            ),
            "sharpe_5bps_gt_instant": bool(
                base_sharpe > instant_base_sharpe
            ),
        }

        record = {
            "no_trade_band": band,
            "portfolio": portfolio,
            "turnover_reduction": turnover_reduction,
            "zero_cost_return_retention": zero_retention,
            "tracking_error_mean": float(
                regular["tracking_error"].mean()
            ),
            "tracking_error_p95": float(
                regular["tracking_error"].quantile(0.95)
            ),
            "active_name_fraction_mean": float(
                regular["active_fraction"].mean()
            ),
            "held_name_fraction_mean": float(
                regular["held_fraction"].mean()
            ),
            "ignored_l1_fraction_mean": float(
                regular["ignored_l1_fraction"].mean()
            ),
            "no_discretionary_trade_fraction": float(
                regular["no_discretionary_trade"].mean()
            ),
            "fallback_count": fallback_count,
            "projected_dates": projected_dates,
            "fallback_rate": fallback_rate,
            "qualification_gates": gates,
            "qualifies": bool(all(gates.values())),
        }
        candidates[str(band)] = record
        if record["qualifies"]:
            qualifying.append((band, record))

        diag.to_csv(
            outdir
            / f"no_trade_band_{band:.3f}_diagnostics.csv"
        )

    if qualifying:
        max_return = max(
            float(
                rec["portfolio"]["base_cost"]["ann_return"]
            )
            for _, rec in qualifying
        )
        near_best = [
            (band, rec)
            for band, rec in qualifying
            if (
                max_return
                - float(
                    rec["portfolio"]["base_cost"]["ann_return"]
                )
                <= 0.0001
            )
        ]
        selected_band, _ = min(
            near_best,
            key=lambda x: float(
                x[1]["portfolio"]["base_cost"]["ann_turnover"]
            ),
        )
    else:
        selected_band = None

    summary = {
        "protocol": {
            "holdout_locked": True,
            "holdout_start": str(
                research.holdout_dates.min().date()
            ),
            "holdout_end": str(
                research.holdout_dates.max().date()
            ),
            "features": PRUNED8,
            "no_trade_bands": NO_TRADE_BANDS,
            "turnover_reduction_threshold": 0.25,
            "zero_cost_return_retention_threshold": 0.80,
            "fallback_invalid_threshold": 0.005,
            "terminal_liquidation": True,
            "liquidation_date": str(
                liquidation_date.date()
            ),
        },
        "rank_ic_reference": ic_diag,
        "instant_benchmark": instant,
        "candidates": candidates,
        "selected_no_trade_band": selected_band,
    }

    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    pred.reset_index().to_csv(
        outdir / "pruned8_predictions.csv",
        index=False,
    )
    ic.to_csv(
        outdir / "pruned8_rank_ic.csv",
        header=True,
    )

    table = pd.DataFrame(
        [
            {
                "no_trade_band": float(band),
                "ann_turnover": float(
                    rec["portfolio"]["base_cost"]["ann_turnover"]
                ),
                "turnover_reduction": float(
                    rec["turnover_reduction"]
                ),
                "ann_return_0bps": float(
                    rec["portfolio"]["cost_sensitivity"]["0"]["ann_return"]
                ),
                "zero_cost_return_retention": float(
                    rec["zero_cost_return_retention"]
                ),
                "ann_return_5bps": float(
                    rec["portfolio"]["base_cost"]["ann_return"]
                ),
                "sharpe_5bps": float(
                    rec["portfolio"]["base_cost"]["sharpe"]
                ),
                "tracking_error_mean": float(
                    rec["tracking_error_mean"]
                ),
                "tracking_error_p95": float(
                    rec["tracking_error_p95"]
                ),
                "active_name_fraction_mean": float(
                    rec["active_name_fraction_mean"]
                ),
                "held_name_fraction_mean": float(
                    rec["held_name_fraction_mean"]
                ),
                "ignored_l1_fraction_mean": float(
                    rec["ignored_l1_fraction_mean"]
                ),
                "no_discretionary_trade_fraction": float(
                    rec["no_discretionary_trade_fraction"]
                ),
                "fallback_count": int(
                    rec["fallback_count"]
                ),
                "qualifies": bool(
                    rec["qualifies"]
                ),
            }
            for band, rec in candidates.items()
        ]
    ).sort_values("no_trade_band")
    table.to_csv(
        outdir / "no_trade_band_summary.csv",
        index=False,
    )

    print(json.dumps(summary, indent=2))
    print(
        "\\nHoldout remains LOCKED. "
        "EXP-005 used development data only."
    )


if __name__ == "__main__":
    main()
