from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_completion_cost_schema_analysis.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_completion_cost_schema_analysis", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_completion_cost_schema_analysis_covers_representative_ordinary_surfaces() -> None:
    checker = _load_checker()

    payload = checker.analyze_operations(max_findings_per_surface=4)

    assert payload["kind"] == "agentic-workspace/completion-cost-schema-analysis/v1"
    assert payload["ordinary_loop_surface"] is False
    assert payload["analyzed_surface_count"] >= 3
    analyzed = {surface["surface"] for surface in payload["analyzed_surfaces"]}
    assert {"start.context", "implement.context", "report.combined"}.issubset(analyzed)
    assert payload["finding_count"] > 0
    finding = payload["findings"][0]
    assert {
        "surface",
        "field_path",
        "suspected_cost_type",
        "owner_surface",
        "reason",
        "candidate_measurement",
        "candidate_reduction",
    }.issubset(finding)


def test_completion_cost_schema_analysis_reports_skipped_schema_refs_without_failure() -> None:
    checker = _load_checker()

    payload = checker.analyze_operations(operation_ids=("summary.report",), max_findings_per_surface=4)

    assert payload["analyzed_surface_count"] == 0
    assert payload["skipped_surface_count"] == 1
    assert payload["skipped_surfaces"][0]["surface"] == "summary.report"
    assert "schema" in payload["skipped_surfaces"][0]["reason"]


def test_completion_cost_schema_analysis_detects_unbounded_diagnostic_pattern() -> None:
    checker = _load_checker()
    surface = checker.Surface(
        operation_id="fixture.context",
        command="fixture",
        operation_path=Path("fixture.operation.json"),
        schema_path=Path("fixture.schema.json"),
        selector_available=False,
        detail_available=False,
    )
    schema = {
        "type": "object",
        "properties": {
            "diagnostics": {
                "type": "object",
                "additionalProperties": True,
                "description": "Diagnostic detail emitted in ordinary output.",
            }
        },
    }

    original_load_json = checker._load_json

    def fake_load_json(path: Path):
        if path == surface.schema_path:
            return schema
        return original_load_json(path)

    checker._load_json = fake_load_json
    try:
        findings = checker.analyze_surface(surface)
    finally:
        checker._load_json = original_load_json

    assert findings
    assert findings[0]["field_path"] == "diagnostics"
    assert findings[0]["suspected_cost_type"] == "review/repair churn"
    assert findings[0]["owner_surface"] == "workspace ordinary outputs"


def test_completion_cost_schema_analysis_main_does_not_fail_on_findings(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--format", "json", "--max-findings-per-surface", "1"])

    assert status == 0
    assert "completion-cost" in capsys.readouterr().out
