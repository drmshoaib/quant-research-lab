from __future__ import annotations

import argparse
import json
from pathlib import Path

from quantlab.data import download_yahoo, load_panel_csv, load_universe, save_panel_csv
from quantlab.splits import development_and_holdout_dates, save_date_manifest
from quantlab.targets import eligible_decision_dates


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze the v0.2 hold-out date manifest.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", help="Long adjusted OHLCV CSV. If omitted, Yahoo is used.")
    p.add_argument("--universe", default="data/universe_etf.csv")
    p.add_argument("--cache-data", default="outputs/market_data.csv")
    p.add_argument("--output", default="configs/holdout_dates.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if not cfg.get("end"):
        raise ValueError("config end date must be fixed before freezing the hold-out")

    if args.data:
        panel = load_panel_csv(args.data)
    else:
        symbols = load_universe(args.universe)
        panel = download_yahoo(symbols, start=cfg["start"], end=cfg["end"])
        save_panel_csv(panel, args.cache_data)

    eligible = eligible_decision_dates(
        panel,
        horizon=cfg["horizon"],
        min_assets=cfg.get("min_assets", 8),
    )
    _, holdout = development_and_holdout_dates(eligible, holdout_days=cfg["holdout_days"])
    save_date_manifest(holdout, args.output)

    print(f"Frozen {len(holdout)} hold-out decision dates.")
    print(f"First hold-out date: {holdout[0].date()}")
    print(f"Last hold-out date:  {holdout[-1].date()}")
    print(f"Manifest: {args.output}")
    print("Commit this manifest before running or tuning v0.2 experiments.")


if __name__ == "__main__":
    main()
