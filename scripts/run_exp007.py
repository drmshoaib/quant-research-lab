from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quantlab.data import load_panel_csv
from quantlab.group_neutral import (
    composite_ic_diagnostics,
    inverse_group_map,
    prepare_group_neutral_research_frame,
    within_group_ic_matrix,
)
from quantlab.pipeline import (
    prepare_research_frame,
    walk_forward_predictions,
)
from quantlab.robustness import (
    broad_asset_group_map,
    chronological_ic_blocks,
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
NON_US_GROUPS = [
    "International_equity",
    "Fixed_income",
    "Commodities",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run EXP-007 group-neutral target study."
    )
    p.add_argument("--config", default="configs/baseline.json")
    p.add_argument("--data", required=True)
    p.add_argument("--universe", default="data/universe_etf.csv")
    p.add_argument(
        "--holdout-manifest",
        default="configs/holdout_dates.csv",
    )
    p.add_argument("--output-dir", default="outputs/exp007")
    return p.parse_args()


def clean_diag(diag: dict[str, object]) -> dict[str, object]:
    out = dict(diag)
    out.pop("_full_series", None)
    out.pop("_non_us_series", None)
    return out


def main() -> None:
    args = parse_args()
    cfg = json.loads(Path(args.config).read_text())
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    panel = load_panel_csv(args.data)
    universe = pd.read_csv(args.universe)
    groups = broad_asset_group_map(universe)
    symbol_groups = inverse_group_map(groups)
    holdout_dates = load_date_manifest(args.holdout_manifest)

    control_research = prepare_research_frame(
        panel,
        horizon=5,
        holdout_days=int(cfg["holdout_days"]),
        holdout_dates=holdout_dates,
        holdout_purge_days=6,
        min_assets=int(cfg.get("min_assets", 8)),
    )
    gn_research = prepare_group_neutral_research_frame(
        panel,
        symbol_groups=symbol_groups,
        horizon=5,
        holdout_dates=holdout_dates,
        holdout_purge_days=6,
        min_assets=int(cfg.get("min_assets", 8)),
    )

    if not control_research.development_dates.equals(
        gn_research.development_dates
    ):
        raise RuntimeError(
            "control and group-neutral development calendars differ"
        )
    if not control_research.holdout_dates.equals(
        gn_research.holdout_dates
    ):
        raise RuntimeError(
            "control and group-neutral holdout calendars differ"
        )

    common_args = dict(
        model_name="hist_gb",
        horizon=5,
        min_train_days=int(cfg["min_train_days"]),
        test_days=int(cfg["test_days"]),
        step_days=int(cfg["step_days"]),
        ridge_alpha=float(cfg["ridge_alpha"]),
        random_state=int(cfg["random_state"]),
        feature_columns=PRUNED8,
    )

    control_pred = walk_forward_predictions(
        control_research,
        **common_args,
    )
    gn_pred = walk_forward_predictions(
        gn_research,
        **common_args,
    )

    if not control_pred.index.equals(gn_pred.index):
        raise RuntimeError(
            "control and group-neutral scored prediction rows differ"
        )

    control_group_ic = within_group_ic_matrix(
        control_pred,
        groups,
        min_assets=4,
    )
    gn_group_ic = within_group_ic_matrix(
        gn_pred,
        groups,
        min_assets=4,
    )

    control_diag_raw = composite_ic_diagnostics(
        control_group_ic,
        non_us_groups=NON_US_GROUPS,
        hac_lag=4,
    )
    gn_diag_raw = composite_ic_diagnostics(
        gn_group_ic,
        non_us_groups=NON_US_GROUPS,
        hac_lag=4,
    )

    control_full = control_diag_raw["_full_series"]
    gn_full = gn_diag_raw["_full_series"]
    control_non_us = control_diag_raw["_non_us_series"]
    gn_non_us = gn_diag_raw["_non_us_series"]

    common_dates = control_full.index.intersection(gn_full.index)
    control_full_common = control_full.loc[common_dates]
    gn_full_common = gn_full.loc[common_dates]
    retention = (
        float(gn_full_common.mean()) / float(control_full_common.mean())
        if float(control_full_common.mean()) != 0
        else float("nan")
    )

    thirds = chronological_ic_blocks(
        gn_full,
        n_blocks=3,
        hac_lag=4,
    )

    group_positive_count = sum(
        float(record["mean_ic"]) > 0
        for record in gn_diag_raw["groups"].values()
    )
    third_positive = all(
        float(block["mean_ic"]) > 0
        for block in thirds
    )
    third_p_lt_010 = sum(
        float(block["hac"]["p_value"]) < 0.10
        for block in thirds
    )

    gates = {
        "four_group_composite_positive_hac_p_lt_0_05": bool(
            float(gn_diag_raw["equal_weight_four_group"]["mean_ic"]) > 0
            and float(
                gn_diag_raw["equal_weight_four_group"]["hac"]["p_value"]
            ) < 0.05
        ),
        "at_least_three_groups_positive": bool(
            group_positive_count >= 3
        ),
        "non_us_composite_positive_hac_p_lt_0_05": bool(
            float(gn_diag_raw["equal_weight_non_us"]["mean_ic"]) > 0
            and float(
                gn_diag_raw["equal_weight_non_us"]["hac"]["p_value"]
            ) < 0.05
        ),
        "within_group_composite_retention_ge_0_80": bool(
            retention >= 0.80
        ),
        "chronological_thirds_rule": bool(
            third_positive
            and third_p_lt_010 >= 2
        ),
    }

    summary = {
        "protocol": {
            "holdout_locked": True,
            "holdout_start": str(
                holdout_dates.min().date()
            ),
            "holdout_end": str(
                holdout_dates.max().date()
            ),
            "features": PRUNED8,
            "groups": groups,
            "non_us_groups": NON_US_GROUPS,
            "horizon": 5,
            "purge_days": 6,
            "holdout_embargo_days": 6,
            "control_and_group_neutral_same_dates": True,
        },
        "control": clean_diag(control_diag_raw),
        "group_neutral": clean_diag(gn_diag_raw),
        "control_four_group_mean_common_dates": float(
            control_full_common.mean()
        ),
        "group_neutral_four_group_mean_common_dates": float(
            gn_full_common.mean()
        ),
        "four_group_ic_retention_vs_control": retention,
        "group_positive_count": int(group_positive_count),
        "group_neutral_chronological_thirds": thirds,
        "acceptance_gates": gates,
        "overall_pass": bool(all(gates.values())),
    }

    (outdir / "summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    control_pred.reset_index().to_csv(
        outdir / "control_predictions.csv",
        index=False,
    )
    gn_pred.reset_index().to_csv(
        outdir / "group_neutral_predictions.csv",
        index=False,
    )
    control_group_ic.to_csv(
        outdir / "control_within_group_ic.csv",
    )
    gn_group_ic.to_csv(
        outdir / "group_neutral_within_group_ic.csv",
    )
    pd.DataFrame(thirds).to_json(
        outdir / "group_neutral_chronological_thirds.json",
        orient="records",
        indent=2,
    )
    pd.DataFrame(
        {
            "control_four_group": control_full,
            "group_neutral_four_group": gn_full,
            "control_non_us": control_non_us,
            "group_neutral_non_us": gn_non_us,
        }
    ).to_csv(outdir / "composite_ic_series.csv")

    print(json.dumps(summary, indent=2))
    print(
        "\\nHoldout remains LOCKED. "
        "EXP-007 used development data only."
    )


if __name__ == "__main__":
    main()
