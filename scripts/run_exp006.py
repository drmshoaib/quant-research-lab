from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

from quantlab.data import load_panel_csv
from quantlab.metrics import rank_ic_by_date, rank_ic_diagnostics
from quantlab.pipeline import walk_forward_predictions
from quantlab.robustness import (
    asset_group_diagnostics,
    broad_asset_group_map,
    chronological_ic_blocks,
    global_symbol_permutation_test,
    prepare_horizon_research_frame,
)
from quantlab.splits import load_date_manifest


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
HORIZONS = [1, 5, 10, 20]
ALTERNATE_HORIZONS = [1, 10, 20]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EXP-006 robustness and falsification study.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True, help="Frozen adjusted OHLCV CSV.")
    p.add_argument("--universe", default="data/universe_etf.csv")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--output-dir", default="outputs/exp006")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    panel = load_panel_csv(args.data)
    holdout_dates = load_date_manifest(args.holdout_manifest)

    horizon_results: dict[str, dict[str, object]] = {}
    horizon_predictions: dict[int, pd.DataFrame] = {}
    horizon_ics: dict[int, pd.Series] = {}

    for horizon in HORIZONS:
        research = prepare_horizon_research_frame(
            panel,
            horizon=horizon,
            holdout_dates=holdout_dates,
            min_assets=int(cfg.get("min_assets", 8)),
        )
        pred = walk_forward_predictions(
            research,
            model_name="hist_gb",
            horizon=horizon,
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
        hac_lag = 1 if horizon == 1 else horizon - 1
        diag = rank_ic_diagnostics(
            ic,
            pred,
            hac_lag=hac_lag,
            min_year_days=int(cfg.get("min_year_ic_days", 20)),
        )
        diag["embargo_days"] = int(len(research.embargo_dates))
        diag["development_start"] = str(research.development_dates.min().date())
        diag["development_end"] = str(research.development_dates.max().date())
        diag["scored_start"] = str(ic.index.min().date())
        diag["scored_end"] = str(ic.index.max().date())
        horizon_results[str(horizon)] = diag
        horizon_predictions[horizon] = pred
        horizon_ics[horizon] = ic

        pred.reset_index().to_csv(
            outdir / f"horizon_{horizon}_predictions.csv",
            index=False,
        )
        ic.to_csv(
            outdir / f"horizon_{horizon}_rank_ic.csv",
            header=True,
        )

    alt_p = [
        float(horizon_results[str(h)]["hac"]["p_value"])
        for h in ALTERNATE_HORIZONS
    ]
    reject, qvals, _, _ = multipletests(
        alt_p,
        alpha=0.10,
        method="fdr_bh",
    )
    for h, rejected, qval in zip(ALTERNATE_HORIZONS, reject, qvals):
        horizon_results[str(h)]["bh_q_value"] = float(qval)
        horizon_results[str(h)]["bh_reject_q_0_10"] = bool(rejected)

    alt_positive = sum(
        float(horizon_results[str(h)]["mean"]) > 0
        for h in ALTERNATE_HORIZONS
    )
    adjacent_significant = any(
        float(horizon_results[str(h)]["mean"]) > 0
        and bool(horizon_results[str(h)]["bh_reject_q_0_10"])
        for h in [1, 10]
    )
    horizon_pass = bool(
        alt_positive >= 2
        and adjacent_significant
    )

    baseline_pred = horizon_predictions[5]
    baseline_ic = horizon_ics[5]
    baseline_mean = float(baseline_ic.mean())

    subperiods = chronological_ic_blocks(
        baseline_ic,
        n_blocks=3,
        hac_lag=4,
    )
    subperiod_pass = bool(
        all(float(b["mean_ic"]) > 0 for b in subperiods)
        and sum(
            float(b["hac"]["p_value"]) < 0.05
            for b in subperiods
        ) >= 2
    )

    universe = pd.read_csv(args.universe)
    groups = broad_asset_group_map(universe)
    group_diag = asset_group_diagnostics(
        baseline_pred,
        groups,
        baseline_mean_ic=baseline_mean,
        hac_lag=4,
    )
    within_positive = sum(
        float(v["mean_ic"]) > 0
        for v in group_diag["within_group"].values()
    )
    leave_out_passes = [
        bool(
            float(v["retention_vs_full"]) >= 0.50
            and float(v["mean_ic"]) > 0
            and float(v["hac"]["p_value"]) < 0.05
        )
        for v in group_diag["leave_one_group_out"].values()
    ]
    asset_group_pass = bool(
        within_positive >= 3
        and all(leave_out_passes)
    )

    placebo = global_symbol_permutation_test(
        baseline_pred,
        n_permutations=999,
        seed=20261004,
    )
    placebo_pass = bool(
        placebo.empirical_p_value <= 0.01
    )
    pd.Series(
        placebo.null_mean_ics,
        name="permuted_mean_rank_ic",
    ).to_csv(
        outdir / "symbol_permutation_null.csv",
        index=False,
    )

    section_pass = {
        "horizon_decay": horizon_pass,
        "subperiod_stability": subperiod_pass,
        "asset_group_dependence": asset_group_pass,
        "symbol_identity_placebo": placebo_pass,
    }
    overall_pass = bool(all(section_pass.values()))

    summary = {
        "protocol": {
            "holdout_locked": True,
            "holdout_start": str(holdout_dates.min().date()),
            "holdout_end": str(holdout_dates.max().date()),
            "features": PRUNED8,
            "horizons": HORIZONS,
            "alternate_horizon_fdr_q": 0.10,
            "subperiod_blocks": 3,
            "broad_asset_groups": groups,
            "permutations": 999,
            "permutation_seed": 20261004,
        },
        "horizon_results": horizon_results,
        "horizon_rule": {
            "alternate_positive_count": int(alt_positive),
            "adjacent_bh_significant": bool(adjacent_significant),
            "pass": horizon_pass,
        },
        "subperiods": subperiods,
        "subperiod_pass": subperiod_pass,
        "asset_groups": group_diag,
        "asset_group_rule": {
            "within_group_positive_count": int(within_positive),
            "leave_one_group_out_passes": leave_out_passes,
            "pass": asset_group_pass,
        },
        "symbol_identity_placebo": {
            "observed_mean_ic": placebo.observed_mean_ic,
            "empirical_p_value": placebo.empirical_p_value,
            "dates_used": placebo.dates_used,
            "symbols_used": placebo.symbols_used,
            "null_mean": float(placebo.null_mean_ics.mean()),
            "null_std": float(placebo.null_mean_ics.std(ddof=1)),
            "null_p95": float(
                pd.Series(placebo.null_mean_ics).quantile(0.95)
            ),
            "pass": placebo_pass,
        },
        "section_pass": section_pass,
        "overall_robustness_pass": overall_pass,
    }

    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    pd.DataFrame(subperiods).to_json(
        outdir / "subperiod_summary.json",
        orient="records",
        indent=2,
    )
    pd.DataFrame(
        [
            {
                "group": name,
                **record,
            }
            for name, record in group_diag["within_group"].items()
        ]
    ).to_json(
        outdir / "within_group_summary.json",
        orient="records",
        indent=2,
    )
    pd.DataFrame(
        [
            {
                "excluded_group": name,
                **record,
            }
            for name, record in group_diag["leave_one_group_out"].items()
        ]
    ).to_json(
        outdir / "leave_group_out_summary.json",
        orient="records",
        indent=2,
    )

    print(json.dumps(summary, indent=2))
    print(
        "\\nHoldout remains LOCKED. "
        "EXP-006 used development data only."
    )


if __name__ == "__main__":
    main()
