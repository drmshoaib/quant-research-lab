from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

from quantlab.backtest import run_backtest, staggered_weights, weights_from_predictions
from quantlab.data import load_panel_csv
from quantlab.features import FEATURE_COLUMNS
from quantlab.metrics import backtest_summary, hac_mean_test, rank_ic_by_date, rank_ic_diagnostics
from quantlab.pipeline import prepare_research_frame, walk_forward_predictions
from quantlab.signals import causal_rank_ewma
from quantlab.splits import load_date_manifest
from quantlab.targets import next_open_to_open_simple_return


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run EXP-002 development-only attribution and turnover study.")
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True, help="Frozen adjusted OHLCV CSV.")
    p.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    p.add_argument("--output-dir", default="outputs/exp002")
    return p.parse_args()


def portfolio_diagnostics(
    predictions: pd.DataFrame,
    *,
    realized: pd.Series,
    realized_dates: pd.DatetimeIndex,
    cfg: dict[str, object],
) -> dict[str, object]:
    ic = rank_ic_by_date(predictions, min_assets=int(cfg.get("min_assets", 8)))
    ic_diag = rank_ic_diagnostics(
        ic,
        predictions,
        hac_lag=max(1, int(cfg["horizon"]) - 1),
        min_year_days=int(cfg.get("min_year_ic_days", 20)),
    )
    cohort = weights_from_predictions(
        predictions,
        gross_limit=float(cfg["gross_limit"]),
        max_abs_weight=float(cfg["max_abs_weight"]),
    )
    live = staggered_weights(
        cohort,
        horizon=int(cfg["horizon"]),
        decision_dates=realized_dates,
    )
    cost_sensitivity: dict[str, dict[str, float]] = {}
    base_bt = None
    for cost in cfg.get("cost_sensitivity_bps", [0, 2, 5, 10, 20]):
        bt = run_backtest(live, realized, cost_bps=float(cost))
        cost_sensitivity[str(cost)] = backtest_summary(bt)
        if float(cost) == float(cfg["cost_bps"]):
            base_bt = bt
    if base_bt is None:
        base_bt = run_backtest(live, realized, cost_bps=float(cfg["cost_bps"]))

    return {
        "rank_ic": ic_diag,
        "backtest_base_cost": backtest_summary(base_bt),
        "cost_sensitivity": cost_sensitivity,
        "_rank_ic_series": ic,
    }


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
    realized = next_open_to_open_simple_return(panel)
    realized_dates = pd.DatetimeIndex(
        realized.dropna().index.get_level_values("date").unique()
    ).sort_values()

    full_pred = walk_forward_predictions(
        research,
        model_name="hist_gb",
        horizon=int(cfg["horizon"]),
        min_train_days=int(cfg["min_train_days"]),
        test_days=int(cfg["test_days"]),
        step_days=int(cfg["step_days"]),
        ridge_alpha=float(cfg["ridge_alpha"]),
        random_state=int(cfg["random_state"]),
        feature_columns=FEATURE_COLUMNS,
    )
    full_eval = portfolio_diagnostics(
        full_pred,
        realized=realized,
        realized_dates=realized_dates,
        cfg=cfg,
    )
    full_ic = full_eval.pop("_rank_ic_series")
    full_pred.reset_index().to_csv(outdir / "full_predictions.csv", index=False)
    full_ic.to_csv(outdir / "full_rank_ic.csv", header=True)

    ablations: dict[str, dict[str, object]] = {}
    p_values: list[float] = []
    features = list(FEATURE_COLUMNS)

    for feature in features:
        cols = [c for c in features if c != feature]
        pred = walk_forward_predictions(
            research,
            model_name="hist_gb",
            horizon=int(cfg["horizon"]),
            min_train_days=int(cfg["min_train_days"]),
            test_days=int(cfg["test_days"]),
            step_days=int(cfg["step_days"]),
            ridge_alpha=float(cfg["ridge_alpha"]),
            random_state=int(cfg["random_state"]),
            feature_columns=cols,
        )
        ic = rank_ic_by_date(pred, min_assets=int(cfg.get("min_assets", 8)))
        aligned = pd.concat(
            [full_ic.rename("full"), ic.rename("ablated")],
            axis=1,
            join="inner",
        ).dropna()
        loss = (aligned["full"] - aligned["ablated"]).rename("ic_loss")
        paired = hac_mean_test(loss, maxlags=max(1, int(cfg["horizon"]) - 1))
        diag = rank_ic_diagnostics(
            ic,
            pred,
            hac_lag=max(1, int(cfg["horizon"]) - 1),
            min_year_days=int(cfg.get("min_year_ic_days", 20)),
        )
        p_values.append(float(paired["p_value"]))
        ablations[feature] = {
            "remaining_features": cols,
            "rank_ic": diag,
            "mean_ic_loss": float(loss.mean()),
            "paired_hac": paired,
            "n_paired_dates": int(len(loss)),
        }
        ic.to_csv(outdir / f"ablation_{feature}_rank_ic.csv", header=True)

    reject, q_values, _, _ = multipletests(p_values, alpha=0.10, method="fdr_bh")
    for feature, is_reject, q_value in zip(features, reject, q_values):
        record = ablations[feature]
        record["bh_q_value"] = float(q_value)
        record["bh_reject_q_0_10"] = bool(is_reject)
        record["material_contributor"] = bool(
            float(record["mean_ic_loss"]) >= 0.003 and bool(is_reject)
        )

    ablation_table = pd.DataFrame(
        [
            {
                "feature": feature,
                "full_mean_ic": float(full_eval["rank_ic"]["mean"]),
                "ablated_mean_ic": float(ablations[feature]["rank_ic"]["mean"]),
                "mean_ic_loss": float(ablations[feature]["mean_ic_loss"]),
                "paired_hac_t": float(ablations[feature]["paired_hac"]["t_stat"]),
                "paired_p_value": float(ablations[feature]["paired_hac"]["p_value"]),
                "bh_q_value": float(ablations[feature]["bh_q_value"]),
                "material_contributor": bool(ablations[feature]["material_contributor"]),
            }
            for feature in features
        ]
    ).sort_values("mean_ic_loss", ascending=False)
    ablation_table.to_csv(outdir / "ablation_summary.csv", index=False)

    smoothing: dict[str, dict[str, object]] = {}
    baseline_mean_ic = float(full_eval["rank_ic"]["mean"])
    baseline_turnover = float(full_eval["backtest_base_cost"]["ann_turnover"])
    baseline_net_return = float(full_eval["backtest_base_cost"]["ann_return"])

    for span in [3, 5, 10]:
        smoothed = causal_rank_ewma(full_pred, span=span)
        eval_ = portfolio_diagnostics(
            smoothed,
            realized=realized,
            realized_dates=realized_dates,
            cfg=cfg,
        )
        ic_series = eval_.pop("_rank_ic_series")
        ic_retention = float(eval_["rank_ic"]["mean"]) / baseline_mean_ic
        turnover_reduction = 1.0 - float(eval_["backtest_base_cost"]["ann_turnover"]) / baseline_turnover
        qualifies = {
            "ic_retention_ge_0_80": bool(ic_retention >= 0.80),
            "hac_p_lt_0_05": bool(
                float(eval_["rank_ic"]["mean"]) > 0
                and float(eval_["rank_ic"]["hac"]["p_value"]) < 0.05
            ),
            "turnover_reduction_ge_0_30": bool(turnover_reduction >= 0.30),
            "net_return_5bps_gt_baseline": bool(
                float(eval_["backtest_base_cost"]["ann_return"]) > baseline_net_return
            ),
        }
        eval_["ic_retention"] = ic_retention
        eval_["turnover_reduction"] = turnover_reduction
        eval_["qualification_gates"] = qualifies
        eval_["qualifies"] = bool(all(qualifies.values()))
        smoothing[str(span)] = eval_
        ic_series.to_csv(outdir / f"smoothing_span_{span}_rank_ic.csv", header=True)

    qualifying = [
        (int(span), rec)
        for span, rec in smoothing.items()
        if bool(rec["qualifies"])
    ]
    if qualifying:
        selected_span, selected = min(
            qualifying,
            key=lambda x: float(x[1]["backtest_base_cost"]["ann_turnover"]),
        )
        selected_smoothing_span: int | None = selected_span
    else:
        selected_smoothing_span = None

    smoothing_table = pd.DataFrame(
        [
            {
                "span": int(span),
                "mean_ic": float(rec["rank_ic"]["mean"]),
                "hac_p_value": float(rec["rank_ic"]["hac"]["p_value"]),
                "ic_retention": float(rec["ic_retention"]),
                "ann_turnover": float(rec["backtest_base_cost"]["ann_turnover"]),
                "turnover_reduction": float(rec["turnover_reduction"]),
                "net_ann_return_5bps": float(rec["backtest_base_cost"]["ann_return"]),
                "sharpe_5bps": float(rec["backtest_base_cost"]["sharpe"]),
                "qualifies": bool(rec["qualifies"]),
            }
            for span, rec in smoothing.items()
        ]
    ).sort_values("span")
    smoothing_table.to_csv(outdir / "smoothing_summary.csv", index=False)

    summary = {
        "protocol": {
            "holdout_locked": True,
            "holdout_start": str(research.holdout_dates.min().date()),
            "holdout_end": str(research.holdout_dates.max().date()),
            "development_dates_scored": int(len(full_ic)),
            "model": "hist_gb",
            "features": features,
            "ablation_fdr_q": 0.10,
            "material_ic_loss_threshold": 0.003,
            "smoothing_spans": [3, 5, 10],
            "smoothing_ic_retention_threshold": 0.80,
            "smoothing_turnover_reduction_threshold": 0.30,
        },
        "full_model": full_eval,
        "ablations": ablations,
        "material_contributors": [
            feature for feature in features if bool(ablations[feature]["material_contributor"])
        ],
        "smoothing": smoothing,
        "selected_smoothing_span": selected_smoothing_span,
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nHoldout remains LOCKED. EXP-002 used development predictions only.")


if __name__ == "__main__":
    main()
