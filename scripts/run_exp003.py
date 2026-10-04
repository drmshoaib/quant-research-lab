from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quantlab.backtest import (
    append_liquidation_row,
    partial_adjustment_weights,
    run_backtest,
    staggered_weights,
    weights_from_predictions,
)
from quantlab.data import load_panel_csv
from quantlab.metrics import backtest_summary, rank_ic_by_date, rank_ic_diagnostics
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.splits import load_date_manifest
from quantlab.targets import next_open_to_open_return


FEATURE_SETS = {
    "full9": [
        "ret_1",
        "mom_5",
        "mom_20",
        "mom_60",
        "vol_20",
        "vol_60",
        "range_1",
        "volume_z_20",
        "drawdown_60",
    ],
    "core2": ["vol_20", "drawdown_60"],
    "core3": ["vol_20", "vol_60", "drawdown_60"],
    "pruned8": [
        "ret_1",
        "mom_20",
        "mom_60",
        "vol_20",
        "vol_60",
        "range_1",
        "volume_z_20",
        "drawdown_60",
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EXP-003 reduced-feature and turnover-aware study.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True, help="Frozen adjusted OHLCV CSV.")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--output-dir", default="outputs/exp003")
    return p.parse_args()


def evaluate_weights(
    weights: pd.Series,
    realized: pd.Series,
    costs: list[float],
    base_cost: float,
) -> dict[str, object]:
    cost_sensitivity: dict[str, dict[str, float]] = {}
    base = None
    for cost in costs:
        bt = run_backtest(weights, realized, cost_bps=float(cost))
        cost_sensitivity[str(cost)] = backtest_summary(bt)
        if float(cost) == float(base_cost):
            base = cost_sensitivity[str(cost)]
    if base is None:
        base = backtest_summary(run_backtest(weights, realized, cost_bps=float(base_cost)))
    return {"base_cost": base, "cost_sensitivity": cost_sensitivity}


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
        holdout_purge_days=int(cfg.get("holdout_purge_days", int(cfg["horizon"]) + 1)),
        min_assets=int(cfg.get("min_assets", 8)),
    )
    realized = next_open_to_open_return(panel)
    realized_dates = pd.DatetimeIndex(
        realized.dropna().index.get_level_values("date").unique()
    ).sort_values()

    costs = [float(x) for x in cfg.get("cost_sensitivity_bps", [0, 2, 5, 10, 20])]
    base_cost = float(cfg["cost_bps"])

    specs: dict[str, dict[str, object]] = {}
    targets: dict[str, pd.Series] = {}

    for name, features in FEATURE_SETS.items():
        pred = walk_forward_predictions(
            research,
            model_name="hist_gb",
            horizon=int(cfg["horizon"]),
            min_train_days=int(cfg["min_train_days"]),
            test_days=int(cfg["test_days"]),
            step_days=int(cfg["step_days"]),
            ridge_alpha=float(cfg["ridge_alpha"]),
            random_state=int(cfg["random_state"]),
            feature_columns=features,
        )
        ic = rank_ic_by_date(pred, min_assets=int(cfg.get("min_assets", 8)))
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
        liq_date = terminal_liquidation_date(
            live_target,
            realized_dates,
            research.holdout_dates[0],
        )
        live_target = append_liquidation_row(live_target, liquidation_date=liq_date)
        targets[name] = live_target

        portfolio = evaluate_weights(live_target, realized, costs, base_cost)
        specs[name] = {
            "features": features,
            "n_features": len(features),
            "rank_ic": ic_diag,
            "instant_execution": portfolio,
            "liquidation_date": str(liq_date.date()),
        }
        pred.reset_index().to_csv(outdir / f"{name}_predictions.csv", index=False)
        ic.to_csv(outdir / f"{name}_rank_ic.csv", header=True)

    full_mean_ic = float(specs["full9"]["rank_ic"]["mean"])
    eligibility: dict[str, dict[str, bool]] = {}
    eligible_names: list[str] = []
    for name in ["core2", "core3", "pruned8"]:
        diag = specs[name]["rank_ic"]
        gates = {
            "mean_ic_retention_ge_0_80": bool(float(diag["mean"]) >= 0.80 * full_mean_ic),
            "positive_hac_p_lt_0_05": bool(
                float(diag["mean"]) > 0 and float(diag["hac"]["p_value"]) < 0.05
            ),
            "median_fold_ic_positive": bool(float(diag["median_fold_ic"]) > 0),
            "positive_year_fraction_ge_0_70": bool(float(diag["positive_year_fraction"]) >= 0.70),
        }
        eligibility[name] = gates
        specs[name]["statistical_eligibility"] = gates
        specs[name]["statistically_eligible"] = bool(all(gates.values()))
        if bool(all(gates.values())):
            eligible_names.append(name)

    if eligible_names:
        selected_spec = sorted(
            eligible_names,
            key=lambda name: (
                int(specs[name]["n_features"]),
                -float(specs[name]["rank_ic"]["mean"]),
            ),
        )[0]
    else:
        selected_spec = "full9"

    selected_target = targets[selected_spec]
    instant = specs[selected_spec]["instant_execution"]
    instant_zero = float(instant["cost_sensitivity"]["0"]["ann_return"])
    instant_base_return = float(instant["base_cost"]["ann_return"])
    instant_turnover = float(instant["base_cost"]["ann_turnover"])

    execution: dict[str, dict[str, object]] = {
        "1.0": {
            "adjustment_rate": 1.0,
            "portfolio": instant,
            "turnover_reduction": 0.0,
            "zero_cost_return_retention": 1.0,
            "qualification_gates": {
                "benchmark": True,
            },
            "qualifies": False,
        }
    }

    qualifying_rates: list[float] = []
    for rate in [0.50, 0.25]:
        actual = partial_adjustment_weights(
            selected_target,
            adjustment_rate=rate,
            force_final_zero=True,
        )
        portfolio = evaluate_weights(actual, realized, costs, base_cost)
        turnover = float(portfolio["base_cost"]["ann_turnover"])
        zero_return = float(portfolio["cost_sensitivity"]["0"]["ann_return"])
        base_return = float(portfolio["base_cost"]["ann_return"])
        turnover_reduction = 1.0 - turnover / instant_turnover
        zero_retention = zero_return / instant_zero if instant_zero > 0 else float("nan")
        gates = {
            "turnover_reduction_ge_0_30": bool(turnover_reduction >= 0.30),
            "zero_cost_return_retention_ge_0_80": bool(
                instant_zero > 0 and zero_retention >= 0.80
            ),
            "net_return_5bps_gt_instant": bool(base_return > instant_base_return),
        }
        execution[str(rate)] = {
            "adjustment_rate": rate,
            "portfolio": portfolio,
            "turnover_reduction": turnover_reduction,
            "zero_cost_return_retention": zero_retention,
            "qualification_gates": gates,
            "qualifies": bool(all(gates.values())),
        }
        if bool(all(gates.values())):
            qualifying_rates.append(rate)

    if 0.50 in qualifying_rates:
        selected_rate: float | None = 0.50
    elif 0.25 in qualifying_rates:
        selected_rate = 0.25
    else:
        selected_rate = None

    feature_table = pd.DataFrame(
        [
            {
                "specification": name,
                "n_features": int(rec["n_features"]),
                "mean_ic": float(rec["rank_ic"]["mean"]),
                "hac_p_value": float(rec["rank_ic"]["hac"]["p_value"]),
                "median_fold_ic": float(rec["rank_ic"]["median_fold_ic"]),
                "positive_year_fraction": float(rec["rank_ic"]["positive_year_fraction"]),
                "ann_turnover": float(rec["instant_execution"]["base_cost"]["ann_turnover"]),
                "ann_return_0bps": float(rec["instant_execution"]["cost_sensitivity"]["0"]["ann_return"]),
                "ann_return_5bps": float(rec["instant_execution"]["base_cost"]["ann_return"]),
                "sharpe_5bps": float(rec["instant_execution"]["base_cost"]["sharpe"]),
                "statistically_eligible": bool(rec.get("statistically_eligible", name == "full9")),
            }
            for name, rec in specs.items()
        ]
    )
    feature_table.to_csv(outdir / "feature_specification_summary.csv", index=False)

    execution_table = pd.DataFrame(
        [
            {
                "adjustment_rate": float(rate),
                "ann_turnover": float(rec["portfolio"]["base_cost"]["ann_turnover"]),
                "turnover_reduction": float(rec["turnover_reduction"]),
                "ann_return_0bps": float(rec["portfolio"]["cost_sensitivity"]["0"]["ann_return"]),
                "zero_cost_return_retention": float(rec["zero_cost_return_retention"]),
                "ann_return_5bps": float(rec["portfolio"]["base_cost"]["ann_return"]),
                "sharpe_5bps": float(rec["portfolio"]["base_cost"]["sharpe"]),
                "qualifies": bool(rec["qualifies"]),
            }
            for rate, rec in execution.items()
        ]
    ).sort_values("adjustment_rate", ascending=False)
    execution_table.to_csv(outdir / "execution_summary.csv", index=False)

    summary = {
        "protocol": {
            "holdout_locked": True,
            "holdout_start": str(research.holdout_dates.min().date()),
            "holdout_end": str(research.holdout_dates.max().date()),
            "feature_sets": FEATURE_SETS,
            "feature_ic_retention_threshold": 0.80,
            "feature_positive_year_threshold": 0.70,
            "adjustment_rates": [1.0, 0.50, 0.25],
            "turnover_reduction_threshold": 0.30,
            "zero_cost_return_retention_threshold": 0.80,
            "terminal_liquidation": True,
        },
        "specifications": specs,
        "statistically_eligible_reduced_specs": eligible_names,
        "selected_feature_specification": selected_spec,
        "execution": execution,
        "selected_adjustment_rate": selected_rate,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldout remains LOCKED. EXP-003 used development data only.")


if __name__ == "__main__":
    main()
