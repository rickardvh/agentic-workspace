from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
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


def _load_run_id_allocator():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "allocate_validation_run_id.py"
    spec = importlib.util.spec_from_file_location("allocate_validation_run_id", path)
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


def test_measurement_phase_defers_only_checked_in_manifest_freshness(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)
    manifest["plan_identity"]["graph_sha256"] = "stale"
    for result in manifest["results"]:
        result["plan_identity"]["graph_sha256"] = "stale"
    checker.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    assert checker.validation_findings(measurement_phase=True) == []
    assert any("stale" in finding.message for finding in checker.validation_findings())


def test_measurement_phase_retains_plan_make_ci_and_evidence_budget_checks(tmp_path: Path, monkeypatch) -> None:
    checker = _load_checker()
    plan, evidence, manifest = _load_payloads(checker)
    plan["constituents"][0].pop("proof_purpose")
    _runtime_record(evidence, phase="after", metric="structured_file_inventory.full")["duration_seconds"] = 31.0
    _write_fixture(checker, tmp_path, monkeypatch, plan, evidence, manifest)
    makefile_path = tmp_path / "Makefile"
    makefile_path.write_text("check-bounded-parallel:\n\t@echo incomplete\n", encoding="utf-8")
    ci_path = tmp_path / "ci.yml"
    ci_path.write_text("name: incomplete\n", encoding="utf-8")
    monkeypatch.setattr(checker, "MAKEFILE_PATH", makefile_path)
    monkeypatch.setattr(checker, "CI_PATH", ci_path)

    messages = [finding.message for finding in checker.validation_findings(measurement_phase=True)]
    assert any("proof_purpose" in message for message in messages)
    assert any("Makefile" in finding.path for finding in checker.validation_findings(measurement_phase=True))
    assert any("ci.yml" in finding.path for finding in checker.validation_findings(measurement_phase=True))
    assert "full structured inventory must complete within 30 seconds" in messages


def test_bounded_trace_records_distinct_measurement_constituents_and_posture() -> None:
    checker = _load_checker()
    plan = json.loads(checker.PLAN_PATH.read_text(encoding="utf-8"))
    constituents = {item["id"]: item for item in plan["constituents"]}
    expected_ids = {"test.workspace-contracts-measurement", "validation-runtime.plan-measurement"}
    broad_trace = next(item for item in plan["trace_fixtures"] if item["command"] == checker.BROAD_TRACE_COMMAND)
    trace_ids = {item["constituent_id"] for item in broad_trace["events"]}

    assert expected_ids.issubset(trace_ids)
    assert {"test.workspace-contracts", "validation-runtime.plan"}.isdisjoint(trace_ids)
    for constituent_id in expected_ids:
        constituent = constituents[constituent_id]
        assert "checked-in manifest freshness" in constituent["proof_purpose"]
        assert constituent["execution_posture"] == "bounded measurement with explicit checked-in-manifest freshness deferral"
        assert "measurement" in constituent["owner_boundary"]


def test_validation_runtime_plan_declares_run_attempt_and_proof_receipt_contracts() -> None:
    checker = _load_checker()
    plan = json.loads(checker.PLAN_PATH.read_text(encoding="utf-8"))

    identity = plan["execution_identity_contract"]
    assert identity["run_provenance"] == ["allocated-here", "explicitly-joined", "transported-child"]
    assert "cannot" not in identity["transport_rule"].lower()
    assert "matching explicit join token" in identity["transport_rule"]
    assert "monotonically ordered attempt" in identity["retry_rule"]
    receipt = plan["proof_receipt_contract"]
    assert receipt["execution_classes"] == ["focused-local", "exhaustive-local", "exhaustive-ci-owned"]
    assert {"timeout", "cancelled", "failed"}.issubset(receipt["outcomes"])


def test_automatic_validation_run_ids_do_not_collide_within_one_second_or_concurrently() -> None:
    allocator = _load_run_id_allocator()

    with ThreadPoolExecutor(max_workers=16) as pool:
        run_ids = list(pool.map(lambda _: allocator.allocate_validation_run_id(), range(128)))

    assert len(run_ids) == len(set(run_ids))
    assert all(run_id.startswith("local-") for run_id in run_ids)


def test_make_materializes_one_automatic_run_id_per_process(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    probe = tmp_path / "validation-id-probe.mk"
    probe.write_text(
        ".PHONY: validation-id-probe\nvalidation-id-probe:\n\t@echo $(VALIDATION_RUN_ID)\n\t@echo $(VALIDATION_RUN_ID)\n",
        encoding="utf-8",
    )

    def invoke() -> list[str]:
        fresh_environment = os.environ.copy()
        for key in ("VALIDATION_RUN_ID", "VALIDATION_JOIN_TOKEN", "VALIDATION_RUN_PROVENANCE"):
            fresh_environment.pop(key, None)
        result = subprocess.run(
            ["make", "--no-print-directory", "-f", str(root / "Makefile"), "-f", str(probe), "validation-id-probe"],
            cwd=root,
            env=fresh_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    first = invoke()
    second = invoke()

    assert len(first) == 2 and first[0] == first[1]
    assert len(second) == 2 and second[0] == second[1]
    assert first[0] != second[0]


def test_stock_pre_commit_routes_through_the_repo_owned_composition() -> None:
    root = Path(__file__).resolve().parents[1]
    config = (root / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "entry: uv run python scripts/git_hooks/pre_commit.py" in config
    assert "entry: make format\n" not in config
    assert "entry: make lint\n" not in config
    assert "entry: make typecheck\n" not in config


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
