from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_validation_runtime_plan.py"
    spec = importlib.util.spec_from_file_location("check_validation_runtime_plan", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_payloads(checker) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        json.loads(checker.PLAN_PATH.read_text(encoding="utf-8")),
        json.loads(checker.EVIDENCE_PATH.read_text(encoding="utf-8")),
        json.loads(checker.MANIFEST_PATH.read_text(encoding="utf-8")),
    )


def _runtime_record(evidence: dict[str, Any], *, phase: str, metric: str) -> dict[str, Any]:
    for record in evidence["runtime_records"]:
        if record.get("phase") == phase and record.get("metric") == metric:
            return record
    raise AssertionError(f"missing runtime record: {phase} {metric}")


def _critical_path_report(evidence: dict[str, Any], *, phase: str, command: str) -> dict[str, Any]:
    for report in evidence["critical_path_reports"]:
        if report.get("phase") == phase and report.get("command") == command:
            return report
    raise AssertionError(f"missing critical path report: {phase} {command}")


def _repo_identity(checker) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/validation-repository-identity/v1",
        "head": checker._git_value("rev-parse", "HEAD"),
        "tree": checker._git_value("rev-parse", "HEAD^{tree}"),
        "tracked_dirty": False,
    }


def _expected_top_contributors(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"constituent_id": result["constituent_id"], "duration_seconds": result["duration_seconds"]}
        for result in sorted(manifest["results"], key=lambda item: float(item.get("duration_seconds") or 0.0), reverse=True)[:3]
    ]


def _refresh_runtime_links(checker, evidence: dict[str, Any], manifest: dict[str, Any], plan_identity: dict[str, Any]) -> None:
    repository = manifest["repository"]
    broad_after = _runtime_record(evidence, phase="after", metric="broad_validation.full")
    broad_after["duration_seconds"] = manifest["critical_path_seconds"]
    broad_after["manifest"] = checker._repo_relative(checker.MANIFEST_PATH)
    broad_after["measured_head"] = repository["head"]
    broad_after["measured_tree"] = repository["tree"]
    broad_after["plan_graph_sha256"] = plan_identity["graph_sha256"]

    evidence.setdefault("pinned_revisions", {})["after_reference"] = {
        "label": "checked-in broad validation manifest",
        "measured_head": repository["head"],
        "measured_tree": repository["tree"],
        "plan_graph_sha256": plan_identity["graph_sha256"],
        "tree_identity": f"{repository['head']}^{{tree}}",
    }

    report = _critical_path_report(evidence, phase="after", command=checker.BROAD_TRACE_COMMAND)
    report["critical_path_seconds"] = manifest["critical_path_seconds"]
    report["summed_work_seconds"] = manifest["summed_work_seconds"]
    report["top_contributors"] = _expected_top_contributors(manifest)


def _write_fixture(
    checker,
    tmp_path: Path,
    monkeypatch,
    plan: dict[str, Any],
    evidence: dict[str, Any],
    manifest: dict[str, Any],
    *,
    refresh_identity: bool = True,
) -> None:
    plan_path = tmp_path / "validation-plan.json"
    evidence_path = tmp_path / "runtime-evidence.json"
    manifest_path = tmp_path / "check-bounded-parallel-manifest.json"
    monkeypatch.setattr(checker, "PLAN_PATH", plan_path)
    monkeypatch.setattr(checker, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(checker, "MANIFEST_PATH", manifest_path)

    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    if refresh_identity:
        plan_identity = checker._plan_identity(plan)
        repository = manifest.get("repository")
        if not isinstance(repository, dict):
            repository = _repo_identity(checker)
            manifest["repository"] = repository
        manifest["plan_identity"] = plan_identity
        for result in manifest.get("results", []):
            if isinstance(result, dict):
                result["plan_identity"] = plan_identity
                result["repository"] = repository
        _refresh_runtime_links(checker, evidence, manifest, plan_identity)

    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def test_validation_runtime_plan_matches_makefile_ci_and_evidence() -> None:
    checker = _load_checker()

    assert checker.validation_findings() == []


def test_validation_runtime_plan_rejects_duplicate_trace_execution(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    plan["trace_fixtures"][0]["events"].append({"constituent_id": "sync.all", "outcome": "passed"})
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("duplicate constituent execution: sync.all" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_missing_compact_label_map_entry(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    plan["compact_label_map"].pop("workspace lint")
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("compact label missing from validation plan: workspace lint" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_manifest_command_drift(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    manifest["results"][0]["command"] = ["uv", "run", "python", "-c", "print('stale')"]
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("command does not match validation plan" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_manifest_dependency_drift(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    manifest["results"][0]["dependencies"] = ["sync.memory"]
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("dependencies do not match validation plan" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_manifest_proof_purpose_drift(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    manifest["results"][0]["proof_purpose"] = "stale proof claim"
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("proof_purpose does not match validation plan" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_missing_broad_constituent(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    removed = manifest["results"].pop()["constituent_id"]
    manifest["result_count"] = len(manifest["results"])
    manifest["outcomes"] = {"passed": len(manifest["results"])}
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any(f"manifest missing broad constituents: {removed}" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_extra_broad_result(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    extra = dict(manifest["results"][0])
    manifest["results"].append(extra)
    manifest["result_count"] = len(manifest["results"])
    manifest["outcomes"] = {"passed": len(manifest["results"])}
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)

    findings = checker.validation_findings()

    assert any("manifest has extra broad constituents" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_stale_plan_identity(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)
    manifest = json.loads(checker.MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["plan_identity"]["graph_sha256"] = "stale"
    checker.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    findings = checker.validation_findings()

    assert any("manifest plan_identity graph_sha256 is stale" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_stale_head_identity(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)
    evidence = json.loads(checker.EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence["pinned_revisions"]["after_reference"]["measured_head"] = "stale"
    checker.EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    findings = checker.validation_findings()

    assert any("after_reference measured_head must match manifest repository head" in finding.message for finding in findings)


def test_validation_runtime_plan_rejects_stale_checked_in_manifest(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    plan["compact_label_map"]["workspace lint"]["command"] = ["uv", "run", "ruff", "check", "src"]
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest, refresh_identity=False)

    findings = checker.validation_findings()

    assert any("manifest plan_identity graph_sha256 is stale" in finding.message for finding in findings)
