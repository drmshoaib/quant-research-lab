from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quantlab.backtest import append_liquidation_row, run_backtest, staggered_weights, weights_from_predictions
from quantlab.data import download_yahoo, load_panel_csv, load_universe, save_panel_csv
from quantlab.metrics import backtest_summary, rank_ic_by_date, rank_ic_diagnostics
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.splits import load_date_manifest
from quantlab.targets import next_open_to_open_simple_return


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run development-only quant research baseline.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", help="Long adjusted OHLCV CSV. If omitted, Yahoo is used.")
    p.add_argument("--universe", default="data/universe_etf.csv")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--cache-data", default="outputs/market_data.csv")
    p.add_argument("--output-dir", default="outputs/baseline")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if not cfg.get("end"):
        raise ValueError("config end date must be fixed; rolling data are forbidden in v0.2")

    manifest_path = Path(args.holdout_manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"{manifest_path} does not exist. Run scripts/freeze_holdout.py and commit the manifest first."
        )
    holdout_dates = load_date_manifest(manifest_path)

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.data:
        panel = load_panel_csv(args.data)
    else:
        symbols = load_universe(args.universe)
        panel = download_yahoo(symbols, start=cfg["start"], end=cfg["end"])
        save_panel_csv(panel, args.cache_data)

    research = prepare_research_frame(
        panel,
        horizon=cfg["horizon"],
        holdout_days=cfg["holdout_days"],
        holdout_dates=holdout_dates,
        holdout_purge_days=cfg.get("holdout_purge_days", cfg["horizon"] + 1),
        min_assets=cfg.get("min_assets", 8),
    )
    realized = next_open_to_open_simple_return(panel)
    realized_dates = pd.DatetimeIndex(
        realized.dropna().index.get_level_values("date").unique()
    ).sort_values()

    summary: dict[str, object] = {
        "protocol": {
            "data_start": cfg["start"],
            "data_end_exclusive": cfg["end"],
            "holdout_start": str(research.holdout_dates.min().date()),
            "holdout_end": str(research.holdout_dates.max().date()),
            "holdout_locked": True,
            "holdout_manifest": str(manifest_path),
            "holdout_purge_days": len(research.embargo_dates),
            "horizon_sessions": cfg["horizon"],
            "portfolio_sleeves": cfg["horizon"],
            "cost_bps": cfg["cost_bps"],
            "cost_sensitivity_bps": cfg.get("cost_sensitivity_bps", [0, 2, 5, 10, 20]),
        },
        "models": {},
    }

    for model_name in cfg["models"]:
        pred = walk_forward_predictions(
            research,
            model_name=model_name,
            horizon=cfg["horizon"],
            min_train_days=cfg["min_train_days"],
            test_days=cfg["test_days"],
            step_days=cfg["step_days"],
            ridge_alpha=cfg["ridge_alpha"],
            random_state=cfg["random_state"],
        )
        if pred.empty:
            continue

        ic = rank_ic_by_date(pred, min_assets=cfg.get("min_assets", 8))
        ic_diag = rank_ic_diagnostics(
            ic,
            pred,
            hac_lag=max(1, cfg["horizon"] - 1),
            min_year_days=cfg.get("min_year_ic_days", 20),
        )

        cohort = weights_from_predictions(
            pred,
            gross_limit=cfg["gross_limit"],
            max_abs_weight=cfg["max_abs_weight"],
        )
        live_weights = staggered_weights(
            cohort,
            horizon=cfg["horizon"],
            decision_dates=realized_dates,
        )
        last_live = pd.Timestamp(live_weights.index.get_level_values("date").max())
        liquidation_candidates = realized_dates[realized_dates > last_live]
        if not len(liquidation_candidates):
            raise ValueError("no realised-return date available for terminal liquidation")
        liquidation_date = pd.Timestamp(liquidation_candidates[0])
        if liquidation_date >= research.holdout_dates[0]:
            raise ValueError("terminal liquidation would enter the locked holdout")
        live_weights = append_liquidation_row(
            live_weights,
            liquidation_date=liquidation_date,
        )

        base_bt = run_backtest(live_weights, realized, cost_bps=cfg["cost_bps"])
        cost_sensitivity: dict[str, dict[str, float]] = {}
        for cost in cfg.get("cost_sensitivity_bps", [0, 2, 5, 10, 20]):
            bt_cost = run_backtest(live_weights, realized, cost_bps=float(cost))
            cost_sensitivity[str(cost)] = backtest_summary(bt_cost)

        model_dir = outdir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        pred.reset_index().to_csv(model_dir / "predictions.csv", index=False)
        ic.to_csv(model_dir / "rank_ic.csv", header=True)
        cohort.rename("cohort_weight").reset_index().to_csv(model_dir / "cohort_weights.csv", index=False)
        live_weights.reset_index().to_csv(model_dir / "live_weights.csv", index=False)
        base_bt.to_csv(model_dir / "backtest.csv", index=True)

        model_summary: dict[str, object] = {
            "rank_ic": ic_diag,
            "backtest_base_cost": backtest_summary(base_bt),
            "cost_sensitivity": cost_sensitivity,
        }

        if model_name == "ridge":
            hac = ic_diag["hac"]
            model_summary["exp001_primary_acceptance"] = {
                "mean_ic_positive": bool(ic_diag["mean"] > 0),
                "hac_two_sided_p_lt_0_05": bool(hac["p_value"] < 0.05),
                "median_fold_ic_positive": bool(ic_diag["median_fold_ic"] > 0),
                "positive_year_fraction_ge_0_60": bool(
                    ic_diag["positive_year_fraction"] >= 0.60
                ),
            }
            gates = model_summary["exp001_primary_acceptance"]
            model_summary["exp001_primary_pass"] = bool(all(gates.values()))

        summary["models"][model_name] = model_summary

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldout remains LOCKED. No hold-out predictions or scores were produced.")


if __name__ == "__main__":
    main()
