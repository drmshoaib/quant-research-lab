"""One-shot evaluation of the locked v0.2 hold-out, under the pre-registered plan.

Plan: docs/holdout_analysis_plan.md (hash-pinned in configs/holdout_analysis_plan.json).

SAFETY MODEL
------------
* Default mode is a DRY RUN on development data: the last 252 development dates are treated as a
  pseudo-hold-out, with a six-date embargo before them. Dry runs never read hold-out outcomes
  and may be repeated freely. They exist to find bugs while finding them is harmless.
* The real run needs BOTH `--unlock` AND the environment variable
  QRL_HOLDOUT_UNLOCK=I_UNDERSTAND_THIS_RUNS_ONCE. Before any computation it verifies every hash
  listed in the plan, refuses if outputs/holdout/result.json already exists, and (when git is
  available) refuses on a dirty working tree.
* Nothing in this script changes the model, features or portfolio rule. The decision row is
  computed by `decide()` from the plan's table and written verbatim.

Usage:
    python scripts/evaluate_holdout.py --data frozen/outputs/market_data.csv --dry-run
    QRL_HOLDOUT_UNLOCK=I_UNDERSTAND_THIS_RUNS_ONCE python scripts/evaluate_holdout.py \
        --data frozen/outputs/market_data.csv --unlock
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import statsmodels
from scipy.stats import norm

from quantlab.backtest import append_liquidation_row, run_backtest, staggered_weights, weights_from_predictions
from quantlab.data import load_panel_csv
from quantlab.metrics import backtest_summary, hac_lag_sensitivity, hac_mean_test, rank_ic_by_date
from quantlab.models import fitted_n_iter, make_model
from quantlab.pipeline import prepare_research_frame
from quantlab.robustness import global_date_permutation_test, global_symbol_permutation_test
from quantlab.splits import load_date_manifest, select_dates
from quantlab.targets import next_open_to_open_simple_return

PLAN_PATH = Path("configs/holdout_analysis_plan.json")
UNLOCK_ENV = "QRL_HOLDOUT_UNLOCK"
UNLOCK_VALUE = "I_UNDERSTAND_THIS_RUNS_ONCE"


def sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one_sided_p(mean: float, two_sided_p: float) -> float:
    """One-sided p-value for H1: mean > 0 from a two-sided HAC p-value."""
    if not np.isfinite(two_sided_p):
        return math.nan
    return 0.5 * two_sided_p if mean > 0 else 1.0 - 0.5 * two_sided_p


def decide(ic_h: float, p_h: float, se_h: float, plan: dict) -> dict:
    """Apply the plan's binding decision table. Pure function; unit-tested."""
    ref = plan["development_reference"]
    z = (ic_h - ref["mean_ic"]) / math.sqrt(ref["se_corrected"] ** 2 + se_h ** 2)
    if ic_h > 0 and p_h < plan["primary"]["level"]:
        row = "confirmed"
    elif ic_h > 0:
        row = "consistent_inconclusive"
    elif z >= norm.ppf(0.05):
        row = "not_replicated"
    else:
        row = "contradicted"
    return {"row": row, "ic_h": ic_h, "p_h_one_sided": p_h, "se_h": se_h, "z_vs_development": z,
            "statement": plan["decision_table"][row]}


def verify_frozen_inputs(data_path: Path, plan: dict, *, require_clean_tree: bool) -> dict:
    checks = {}
    actual = sha256(data_path)
    checks["market_data"] = {"expected": plan["market_data_sha256"], "actual": actual, "ok": actual == plan["market_data_sha256"]}
    for rel, expected in plan["frozen_inputs_sha256"].items():
        a = sha256(rel)
        checks[rel] = {"expected": expected, "actual": a, "ok": a == expected}
    a = sha256(plan["document"])
    checks[plan["document"]] = {"expected": plan["document_sha256"], "actual": a, "ok": a == plan["document_sha256"]}
    if require_clean_tree:
        try:
            dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
            checks["git_clean"] = {"ok": dirty == "", "detail": dirty[:500]}
        except Exception as exc:  # git unavailable: record, do not block
            checks["git_clean"] = {"ok": True, "detail": f"git not checked: {exc}"}
    failed = [k for k, v in checks.items() if not v["ok"]]
    if failed:
        raise SystemExit(f"REFUSING TO RUN: frozen-input verification failed for {failed}")
    return checks


def fit_once_and_score(frame_dev: pd.DataFrame, frame_eval: pd.DataFrame, features: list[str], model_name: str, random_state: int):
    model = make_model(model_name, random_state=random_state, n_train=len(frame_dev))
    model.fit(frame_dev[features], frame_dev["target"])
    pred = pd.DataFrame({"y_true": frame_eval["target"], "y_pred": model.predict(frame_eval[features])}, index=frame_eval.index)
    pred["fold"] = 1
    return pred, fitted_n_iter(model)


def portfolio_block(pred: pd.DataFrame, realized: pd.Series, eval_dates: pd.DatetimeIndex, plan: dict, horizon: int) -> dict:
    realized_dates = pd.DatetimeIndex(realized.dropna().index.get_level_values("date").unique()).sort_values()
    cohort = weights_from_predictions(pred, gross_limit=plan["secondary"]["gross_limit"], max_abs_weight=plan["secondary"]["max_abs_weight"])
    live = staggered_weights(cohort, horizon=horizon, decision_dates=realized_dates)
    last_live = pd.Timestamp(live.index.get_level_values("date").max())
    candidates = realized_dates[realized_dates > last_live]
    out = {}
    if len(candidates):
        live = append_liquidation_row(live, liquidation_date=pd.Timestamp(candidates[0]))
    for bps in plan["secondary"]["portfolio_cost_bps"]:
        daily = run_backtest(live, realized, cost_bps=float(bps))
        out[f"{bps}bps"] = backtest_summary(daily)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Pre-registered hold-out evaluation (locked by default).")
    ap.add_argument("--data", required=True)
    ap.add_argument("--config", default="configs/baseline.json")
    ap.add_argument("--holdout-manifest", default="configs/holdout_dates.csv")
    ap.add_argument("--plan", default=str(PLAN_PATH))
    ap.add_argument("--dry-run", action="store_true", help="Pseudo-hold-out on development data (default if --unlock absent).")
    ap.add_argument("--unlock", action="store_true", help="Evaluate the REAL hold-out. Also needs the environment variable.")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--n-permutations", type=int, default=None)
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text())
    cfg = json.loads(Path(args.config).read_text())
    horizon = int(plan["horizon"])
    features = list(plan["features"])
    n_perm = args.n_permutations or int(plan["secondary"]["placebo_permutations"])

    real_run = bool(args.unlock) and os.environ.get(UNLOCK_ENV) == UNLOCK_VALUE
    if args.unlock and not real_run:
        raise SystemExit(f"REFUSING TO RUN: --unlock also requires {UNLOCK_ENV}={UNLOCK_VALUE} in the environment.")
    if not real_run:
        args.dry_run = True
    outdir = Path(args.output_dir or ("outputs/holdout" if real_run else "outputs/holdout_dry_run"))
    result_path = outdir / "result.json"
    if real_run and result_path.exists():
        raise SystemExit(f"REFUSING TO RUN: {result_path} already exists. The hold-out is evaluated once.")

    checks = verify_frozen_inputs(Path(args.data), plan, require_clean_tree=real_run) if real_run else {"dry_run": True}

    holdout_dates = load_date_manifest(args.holdout_manifest)
    panel = load_panel_csv(args.data)
    research = prepare_research_frame(
        panel, horizon=horizon, holdout_days=int(cfg["holdout_days"]), holdout_dates=holdout_dates,
        holdout_purge_days=int(plan["embargo_days"]), min_assets=int(plan["min_assets"]),
    )
    dev_dates = research.development_dates
    if real_run:
        fit_dates, eval_dates = dev_dates, research.holdout_dates
    else:
        # Pseudo-hold-out: last 252 development dates, with the embargo carved out before them.
        n_eval = len(research.holdout_dates)
        eval_dates = dev_dates[-n_eval:]
        fit_dates = dev_dates[: len(dev_dates) - n_eval - int(plan["embargo_days"])]

    frame_fit = select_dates(research.frame, fit_dates)
    frame_eval = select_dates(research.frame, eval_dates)
    if not real_run:
        assert frame_eval.index.get_level_values("date").max() < research.holdout_dates[0], "dry run touched the hold-out"

    realized = next_open_to_open_simple_return(panel)
    outdir.mkdir(parents=True, exist_ok=True)
    results = {}
    for role, model_name in (("decision_model", plan["decision_model"]), ("secondary_model", plan["secondary_model"])):
        pred, n_iter = fit_once_and_score(frame_fit, frame_eval, features, model_name, int(cfg["random_state"]))
        ic = rank_ic_by_date(pred, min_assets=int(plan["min_assets"]))
        primary = hac_mean_test(ic, maxlags=int(plan["primary"]["hac_lag"]))
        p_one = one_sided_p(primary["mean"], primary["p_value"])
        se_h = primary["mean"] / primary["t_stat"] if primary["t_stat"] not in (0, math.nan) and np.isfinite(primary["t_stat"]) else math.nan
        lag_table = hac_lag_sensitivity(ic, lags=plan["lag_sensitivity"])
        lag_table["p_one_sided"] = [one_sided_p(m, p) for m, p in zip(lag_table["mean"], lag_table["p_value"])]
        block = {
            "model_name": model_name,
            "n_fit_rows": int(len(frame_fit)),
            "n_fit_dates": int(len(fit_dates)),
            "n_eval_dates_scored": int(len(ic)),
            "n_iter": n_iter,
            "mean_ic": float(ic.mean()),
            "ic_std": float(ic.std(ddof=1)),
            "positive_fraction": float((ic > 0).mean()),
            "primary_lag10": {"t_stat": primary["t_stat"], "p_two_sided": primary["p_value"], "p_one_sided": p_one, "se": float(se_h)},
            "lag_sensitivity": {str(int(k)): {"t_stat": float(r["t_stat"]), "p_one_sided": float(r["p_one_sided"])} for k, r in lag_table.iterrows()},
            "symbol_placebo_p": global_symbol_permutation_test(pred, n_permutations=n_perm).empirical_p_value,
            "timing_placebo_p": global_date_permutation_test(pred, n_permutations=n_perm).empirical_p_value,
            "portfolio": portfolio_block(pred, realized, eval_dates, plan, horizon),
        }
        if role == "decision_model":
            block["decision"] = decide(block["mean_ic"], p_one, float(se_h), plan)
        results[role] = block
        pred.reset_index().to_csv(outdir / f"{role}_predictions.csv", index=False)
        ic.to_csv(outdir / f"{role}_rank_ic.csv", header=True)
        lag_table.to_csv(outdir / f"{role}_lag_sensitivity.csv")

    out = {
        "mode": "REAL_HOLDOUT_EVALUATION" if real_run else "DRY_RUN_ON_DEVELOPMENT_DATA",
        "plan_version": plan["plan_version"],
        "plan_document_sha256": plan["document_sha256"],
        "evaluation_dates": {"start": str(eval_dates[0].date()), "end": str(eval_dates[-1].date()), "n": int(len(eval_dates))},
        "fit_dates": {"start": str(fit_dates[0].date()), "end": str(fit_dates[-1].date()), "n": int(len(fit_dates))},
        "verification": checks,
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "statsmodels": statsmodels.__version__,
                        "numpy": np.__version__, "pandas": pd.__version__},
        "results": results,
    }
    result_path.write_text(json.dumps(out, indent=2, default=str))
    d = results["decision_model"]["decision"]
    print(f"[{out['mode']}] mean IC {d['ic_h']:.5f}  one-sided lag-10 p {d['p_h_one_sided']:.4f}  z vs development {d['z_vs_development']:.2f}")
    print(f"Decision row: {d['row'].upper()} — {d['statement']}")
    if not real_run:
        print("Dry run on development data only. The hold-out remains LOCKED.")


if __name__ == "__main__":
    main()
