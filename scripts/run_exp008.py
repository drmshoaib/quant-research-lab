"""EXP-008 — Methods re-run: early stopping, inference lag, Ridge scaling, timing placebo.

Pre-registered in docs/research_log.md (EXP-008). This is a *methods* experiment:
it does not promote or reject any signal. It re-runs the frozen pruned8 development
evaluation under corrected methods and reports whether each v0.2 conclusion survives.

Development data only. The hold-out manifest is loaded solely to exclude it.

Usage (CI runs it against the frozen data artefact, see .github/workflows/exp008.yml):

    python scripts/run_exp008.py --data frozen/outputs/market_data.csv --output-dir outputs/exp008
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import statsmodels

from quantlab.data import load_panel_csv
from quantlab.metrics import hac_lag_sensitivity, newey_west_automatic_lag, rank_ic_by_date, rank_ic_diagnostics
from quantlab.models import V03_RIDGE_KAPPA
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions_with_diagnostics
from quantlab.robustness import global_date_permutation_test, global_symbol_permutation_test
from quantlab.splits import load_date_manifest

PRUNED8 = ["ret_1", "mom_20", "mom_60", "vol_20", "vol_60", "range_1", "volume_z_20", "drawdown_60"]
LAGS = (0, 4, 8, 10, 20)
PRIMARY_LAG = 10  # 2h, pre-registered as the EXP-008 primary inference lag
FROZEN_V02_MEAN_IC = 0.02701  # configs/final_specification_v0.2.json
N_PERMUTATIONS = 999

# Pre-registered rows of the comparison table. The control must reproduce the frozen v0.2
# number (the acceptance condition for the whole run); the others are the corrected methods.
VARIANTS = {
    "control_v02_hist_gb": {"model_name": "hist_gb", "features": PRUNED8},
    "v03_no_early_stopping": {"model_name": "hist_gb_v03", "features": PRUNED8},
    "v03_time_ordered_early_stopping": {"model_name": "hist_gb_v03_time", "features": PRUNED8},
    "v02_ridge_alpha_10": {"model_name": "ridge", "features": PRUNED8},
    "v03_ridge_kappa_0_1": {"model_name": "ridge_v03", "features": PRUNED8},
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EXP-008 methods re-run (development data only).")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True, help="Frozen long adjusted OHLCV CSV.")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--output-dir", default="outputs/exp008")
    p.add_argument("--n-permutations", type=int, default=N_PERMUTATIONS)
    p.add_argument("--variants", nargs="*", default=list(VARIANTS), help="Subset of variants to run.")
    return p.parse_args()


def evaluate_variant(research, cfg, name: str, spec: dict, outdir: Path, n_perm: int) -> dict:
    pred, diag = walk_forward_predictions_with_diagnostics(
        research,
        model_name=spec["model_name"],
        horizon=int(cfg["horizon"]),
        min_train_days=int(cfg["min_train_days"]),
        test_days=int(cfg["test_days"]),
        step_days=int(cfg["step_days"]),
        ridge_alpha=float(cfg["ridge_alpha"]),
        random_state=int(cfg["random_state"]),
        feature_columns=spec["features"],
        purge_days=int(cfg.get("train_test_purge_days", cfg["horizon"] + 1)),
    )
    ic = rank_ic_by_date(pred, min_assets=int(cfg.get("min_assets", 8)))
    registered = rank_ic_diagnostics(ic, pred, hac_lag=4, min_year_days=int(cfg.get("min_year_ic_days", 20)))
    lag_table = hac_lag_sensitivity(ic, lags=LAGS, include_automatic=True)
    primary = lag_table.loc[PRIMARY_LAG]

    symbol_placebo = global_symbol_permutation_test(pred, n_permutations=n_perm)
    timing_placebo = global_date_permutation_test(pred, n_permutations=n_perm)

    pred.reset_index().to_csv(outdir / f"{name}_predictions.csv", index=False)
    ic.to_csv(outdir / f"{name}_rank_ic.csv", header=True)
    diag.to_csv(outdir / f"{name}_fold_diagnostics.csv")
    lag_table.to_csv(outdir / f"{name}_lag_sensitivity.csv")

    n_iter = diag["n_iter"].dropna()
    return {
        "model_name": spec["model_name"],
        "n_scored_dates": int(len(ic)),
        "mean_rank_ic": float(ic.mean()),
        "registered_lag4": {"t_stat": registered["hac"]["t_stat"], "p_value": registered["hac"]["p_value"]},
        "primary_lag10": {"se": float(primary["se"]), "t_stat": float(primary["t_stat"]), "p_value": float(primary["p_value"])},
        "lag_sensitivity": {str(int(k)): {"se": float(r["se"]), "t_stat": float(r["t_stat"]), "p_value": float(r["p_value"])} for k, r in lag_table.iterrows()},
        "automatic_lag": int(newey_west_automatic_lag(len(ic))),
        "positive_year_fraction": registered["positive_year_fraction"],
        "median_fold_ic": registered["median_fold_ic"],
        "n_iter": {
            "min": float(n_iter.min()) if len(n_iter) else None,
            "median": float(n_iter.median()) if len(n_iter) else None,
            "max": float(n_iter.max()) if len(n_iter) else None,
            "per_fold": [None if np.isnan(v) else int(v) for v in diag["n_iter"].tolist()],
        },
        "symbol_placebo_p": symbol_placebo.empirical_p_value,
        "timing_placebo_p": timing_placebo.empirical_p_value,
        "timing_placebo_null_sd": float(np.std(timing_placebo.null_mean_ics)),
        "significant_at_5pct_lag10": bool(primary["p_value"] < 0.05 and ic.mean() > 0),
    }


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    holdout_dates = load_date_manifest(args.holdout_manifest)
    panel = load_panel_csv(args.data)
    research = prepare_research_frame(
        panel,
        horizon=int(cfg["horizon"]),
        holdout_days=int(cfg["holdout_days"]),
        holdout_dates=holdout_dates,
        holdout_purge_days=int(cfg.get("holdout_purge_days", cfg["horizon"] + 1)),
        min_assets=int(cfg.get("min_assets", 8)),
    )

    results = {}
    for name in args.variants:
        results[name] = evaluate_variant(research, cfg, name, VARIANTS[name], outdir, args.n_permutations)
        print(f"{name}: mean IC {results[name]['mean_rank_ic']:.5f}, lag-10 p {results[name]['primary_lag10']['p_value']:.4g}, "
              f"n_iter median {results[name]['n_iter']['median']}, timing placebo p {results[name]['timing_placebo_p']:.3f}")

    control = results.get("control_v02_hist_gb")
    reproduced = bool(control and abs(control["mean_rank_ic"] - FROZEN_V02_MEAN_IC) < 5e-5)

    summary = {
        "experiment": "EXP-008",
        "type": "methods re-run; no promotion decision",
        "holdout": "locked; development data only",
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "statsmodels": statsmodels.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "pre_registered": {
            "control_must_reproduce_frozen_mean_ic": FROZEN_V02_MEAN_IC,
            "primary_inference_lag": PRIMARY_LAG,
            "lag_table": list(LAGS),
            "ridge_kappa": V03_RIDGE_KAPPA,
            "placebo_permutations": args.n_permutations,
            "gates": {
                "G1_reproduction": "|control mean IC - 0.02701| < 5e-5",
                "G2_inference": "pruned8 mean IC > 0 with lag-10 HAC p < 0.05 under v0.3 no-early-stopping",
                "G3_early_stopping": "v0.3 variants' mean IC within [0.5, 1.5] x control; n_iter recorded per fold",
                "G4_timing": "timing placebo p <= 0.05 for the control and for v0.3 no-early-stopping",
            },
        },
        "gate_results": {
            "G1_reproduction": reproduced,
            "G2_inference": bool(results.get("v03_no_early_stopping", {}).get("significant_at_5pct_lag10", False)),
            "G3_early_stopping": bool(
                control
                and all(
                    0.5 * control["mean_rank_ic"] <= results[v]["mean_rank_ic"] <= 1.5 * control["mean_rank_ic"]
                    for v in ("v03_no_early_stopping", "v03_time_ordered_early_stopping")
                    if v in results
                )
            ),
            "G4_timing": bool(
                control
                and control["timing_placebo_p"] <= 0.05
                and results.get("v03_no_early_stopping", {}).get("timing_placebo_p", 1.0) <= 0.05
            ),
        },
        "variants": results,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary["gate_results"], indent=2))
    print("\nHoldout remains LOCKED. EXP-008 used development data only.")
    if not reproduced:
        print("WARNING: control did not reproduce the frozen v0.2 mean IC; check library versions.", file=sys.stderr)


if __name__ == "__main__":
    main()
