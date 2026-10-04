from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quantlab.backtest import run_backtest, weights_from_predictions
from quantlab.data import download_yahoo, load_panel_csv, load_universe, save_panel_csv
from quantlab.metrics import backtest_summary, hac_mean_test, rank_ic_by_date
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.targets import next_open_to_open_return


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run development-only quant research baseline.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", help="Long OHLCV CSV. If omitted, Yahoo is used.")
    p.add_argument("--universe", default="data/universe_etf.csv")
    p.add_argument("--cache-data", default="outputs/market_data.csv")
    p.add_argument("--output-dir", default="outputs/baseline")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.data:
        panel = load_panel_csv(args.data)
    else:
        symbols = load_universe(args.universe)
        panel = download_yahoo(symbols, start=cfg["start"], end=cfg.get("end"))
        save_panel_csv(panel, args.cache_data)

    research = prepare_research_frame(panel, horizon=cfg["horizon"], holdout_days=cfg["holdout_days"])
    realized = next_open_to_open_return(panel)

    summary: dict[str, object] = {
        "protocol": {
            "holdout_start": str(research.holdout_dates.min().date()),
            "holdout_end": str(research.holdout_dates.max().date()),
            "holdout_locked": True,
            "horizon_sessions": cfg["horizon"],
            "cost_bps": cfg["cost_bps"],
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
        ic = rank_ic_by_date(pred)
        ic_test = hac_mean_test(ic, maxlags=max(1, cfg["horizon"] - 1))
        weights = weights_from_predictions(
            pred,
            gross_limit=cfg["gross_limit"],
            max_abs_weight=cfg["max_abs_weight"],
        )
        bt = run_backtest(weights, realized, cost_bps=cfg["cost_bps"])
        model_dir = outdir / model_name
        model_dir.mkdir(parents=True, exist_ok=True)
        pred.reset_index().to_csv(model_dir / "predictions.csv", index=False)
        ic.to_csv(model_dir / "rank_ic.csv", header=True)
        bt.to_csv(model_dir / "backtest.csv", index=True)
        summary["models"][model_name] = {"rank_ic_hac": ic_test, "backtest": backtest_summary(bt)}

    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldout remains LOCKED. Do not evaluate it until the research protocol is frozen.")


if __name__ == "__main__":
    main()
