from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_validation_runtime_plan.py"
    spec = importlib.util.spec_from_file_location("check_validation_runtime_plan", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_validation_runtime_plan_matches_makefile_ci_and_evidence() -> None:
    checker = _load_checker()

    assert checker.validation_findings() == []


def test_validation_runtime_plan_rejects_duplicate_trace_execution(tmp_path: Path) -> None:
    checker = _load_checker()
    plan = json.loads(checker.PLAN_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(checker.EVIDENCE_PATH.read_text(encoding="utf-8"))
    plan["trace_fixtures"][0]["events"].append({"constituent_id": "sync.all", "outcome": "passed"})
    plan_path = tmp_path / "validation-plan.json"
    evidence_path = tmp_path / "runtime-evidence.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    checker.PLAN_PATH = plan_path
    checker.EVIDENCE_PATH = evidence_path

    findings = checker.validation_findings()

    assert any("duplicate constituent execution: sync.all" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_missing_compact_label_map_entry(tmp_path: Path) -> None:
    checker = _load_checker()
    plan = json.loads(checker.PLAN_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(checker.EVIDENCE_PATH.read_text(encoding="utf-8"))
    plan["compact_label_map"].pop("workspace lint")
    plan_path = tmp_path / "validation-plan.json"
    evidence_path = tmp_path / "runtime-evidence.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    checker.PLAN_PATH = plan_path
    checker.EVIDENCE_PATH = evidence_path

    findings = checker.validation_findings()

    assert any("compact label missing from validation plan: workspace lint" in finding.message for finding in findings)
