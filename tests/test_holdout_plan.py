"""The pre-registered hold-out plan is hash-pinned, and its decision rule is a pure function."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location("evaluate_holdout", ROOT / "scripts" / "evaluate_holdout.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_plan_hashes_pin_the_document_and_frozen_inputs():
    plan = json.loads((ROOT / "configs" / "holdout_analysis_plan.json").read_text())
    assert plan["status"] == "registered_not_evaluated"
    doc = hashlib.sha256((ROOT / plan["document"]).read_bytes()).hexdigest()
    assert doc == plan["document_sha256"], "docs/holdout_analysis_plan.md was edited after registration"
    for rel, expected in plan["frozen_inputs_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected, rel
    snapshot = json.loads((ROOT / "configs" / "data_snapshot.json").read_text())
    assert plan["market_data_sha256"] == snapshot["sha256"]
    assert plan["primary"]["hac_lag"] == 10 and plan["primary"]["level"] == 0.05


def test_decision_table_rows():
    mod = _load_script()
    plan = json.loads((ROOT / "configs" / "holdout_analysis_plan.json").read_text())
    assert mod.decide(0.03, 0.02, 0.025, plan)["row"] == "confirmed"
    assert mod.decide(0.01, 0.30, 0.025, plan)["row"] == "consistent_inconclusive"
    assert mod.decide(-0.005, 0.60, 0.025, plan)["row"] == "not_replicated"
    d = mod.decide(-0.05, 0.95, 0.025, plan)
    assert d["row"] == "contradicted" and d["z_vs_development"] < -1.645
    # Boundary of the plan's orientation figure: se_h = 0.0292 puts the cut-off near -0.023.
    assert mod.decide(-0.020, 0.8, 0.0292, plan)["row"] == "not_replicated"
    assert mod.decide(-0.026, 0.8, 0.0292, plan)["row"] == "contradicted"
    assert mod.one_sided_p(0.01, 0.10) == pytest.approx(0.05)
    assert mod.one_sided_p(-0.01, 0.10) == pytest.approx(0.95)


def test_unlock_is_refused_without_the_environment_variable(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "QRL_HOLDOUT_UNLOCK"}
    proc = subprocess.run(
        [sys.executable, "scripts/evaluate_holdout.py", "--data", "does_not_matter.csv", "--unlock", "--output-dir", str(tmp_path)],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "REFUSING TO RUN" in proc.stdout + proc.stderr
    assert not (tmp_path / "result.json").exists()


def test_unlock_with_wrong_data_is_refused_by_hash_check(tmp_path, synthetic_panel):
    from quantlab.data import save_panel_csv

    data = tmp_path / "panel.csv"
    save_panel_csv(synthetic_panel, data)
    env = dict(os.environ, QRL_HOLDOUT_UNLOCK="I_UNDERSTAND_THIS_RUNS_ONCE")
    proc = subprocess.run(
        [sys.executable, "scripts/evaluate_holdout.py", "--data", str(data), "--unlock", "--output-dir", str(tmp_path / "out")],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "verification failed" in proc.stdout + proc.stderr
    assert not (tmp_path / "out").exists()
