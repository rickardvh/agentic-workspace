from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import cast

ROOT = Path(__file__).parents[1]


def _evaluation_module() -> ModuleType:
    path = ROOT / "tools/model-evaluation/run.py"
    spec = importlib.util.spec_from_file_location("aw_model_evaluation", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeAdapter:
    def __init__(self, status: str = "available") -> None:
        self.status = status
        self.probes: list[str] = []
        self.requests: list[dict[str, object]] = []

    def probe(self, provider: str) -> Mapping[str, object]:
        self.probes.append(provider)
        return {"status": self.status, "provenance": f"fake:{provider}"}

    def execute(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.requests.append(dict(request))
        return {
            "effective_provider_input": {"condition": request["condition"], "scenario_id": request["scenario_id"]},
            "tool_calls": [{"name": "workspace"}] if request["condition"] == "assisted" else [],
            "retries": 1,
            "repairs": 0,
            "correct": True,
            "authority_outcome": "preserved",
            "unknowns": [],
        }


def test_required_maintainer_skills_are_current_and_outside_packages() -> None:
    names = {path.parent.name for path in (ROOT / "tools/skills").glob("*/SKILL.md")}
    assert names == {
        "pr-review-recheck",
        "github-issue-shaping",
        "github-issue-creation",
        "self-improvement-dogfooding",
    }
    text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "tools/skills").glob("*/SKILL.md"))
    for removed in (
        "agentic-workspace report",
        "agentic-workspace reconcile",
        "agentic-workspace proof",
        "external-intent refresh",
    ):
        assert removed not in text


def test_minimal_model_evaluation_runs_and_reports_provider_availability() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/model-evaluation/run.py"), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert all(item["passed"] for item in report["results"])
    assert report["provider_availability"] == {
        "provider": None,
        "configured": False,
        "status": "unknown",
        "available": None,
        "provenance": "provider-not-configured",
    }
    assert report["live_results"] == []


def test_configured_provider_without_adapter_is_unknown() -> None:
    report = _evaluation_module().run(ROOT, "example")
    assert report["provider_availability"] == {
        "provider": "example",
        "configured": True,
        "status": "unknown",
        "available": None,
        "provenance": "adapter-not-configured",
    }
    assert report["live_results"] == []


def test_no_provider_makes_zero_adapter_calls() -> None:
    adapter = FakeAdapter()
    report = _evaluation_module().run(ROOT, None, adapter)
    assert report["provider_availability"]["status"] == "unknown"
    assert adapter.probes == []
    assert adapter.requests == []


def test_unavailable_provider_does_not_execute_live_conditions() -> None:
    adapter = FakeAdapter("unavailable")
    report = _evaluation_module().run(ROOT, "example", adapter)
    assert report["provider_availability"]["status"] == "unavailable"
    assert report["provider_availability"]["provenance"] == "fake:example"
    assert report["live_results"] == []
    assert adapter.probes == ["example"]
    assert adapter.requests == []


def test_available_provider_runs_matched_conditions_with_bounded_evidence() -> None:
    adapter = FakeAdapter()
    report = _evaluation_module().run(ROOT, "example", adapter)
    assert [item["id"] for item in report["live_results"]] == ["direct", "typed-operation"]
    assert len(adapter.requests) == 4
    for result in report["live_results"]:
        assert set(result) == {"id", "direct", "assisted"}
        for condition in (result["direct"], result["assisted"]):
            assert set(condition) == {
                "condition",
                "elapsed_ms",
                "effective_provider_input",
                "tool_calls",
                "retries",
                "repairs",
                "correct",
                "authority_outcome",
                "unknowns",
            }
    assisted = [request for request in adapter.requests if request["condition"] == "assisted"]
    typed = next(request for request in assisted if request["scenario_id"] == "typed-operation")
    evidence = typed["workspace_evidence"]
    assert isinstance(evidence, dict)
    evidence = cast(dict[str, object], evidence)
    assert evidence["decision_status"] == "actionable"
    assert "operation_result" in evidence
    assert "next_decision" in evidence


def test_model_evaluation_tools_are_excluded_from_built_wheel(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    wheel = next(tmp_path.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    assert not any(name.startswith("tools/") or "model-evaluation" in name for name in names)
