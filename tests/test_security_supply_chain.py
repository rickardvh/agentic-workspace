from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts/check"))
from check_security_supply_chain import evaluate_security_supply_chain  # noqa: E402

from agentic_workspace import workspace_runtime_core  # noqa: E402


def _copy_security_surface(target: Path) -> None:
    paths = [
        "SECURITY.md",
        "docs/security/threat-model.md",
        "uv.lock",
        "src/agentic_workspace/trusted_execution.py",
        "src/agentic_workspace/contracts/security_supply_chain_policy.json",
        "scripts/check/check_security_supply_chain.py",
        ".github/workflow-write-permissions.json",
    ]
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)
    shutil.copytree(REPO_ROOT / ".github/workflows", target / ".github/workflows")


def test_repository_security_supply_chain_readiness_is_exact_and_ready() -> None:
    receipt = evaluate_security_supply_chain(REPO_ROOT)

    assert receipt["status"] == "ready", receipt["failures"]
    assert receipt["release_promotion_allowed"] is True
    assert receipt["subject_fingerprint"].startswith("sha256:")
    assert {control["status"] for control in receipt["controls"]} == {"pass"}


def test_workspace_report_projects_exact_security_readiness() -> None:
    receipt = workspace_runtime_core._security_supply_chain_readiness_payload(target_root=REPO_ROOT)

    assert receipt["kind"] == "agentic-workspace/security-supply-chain-readiness/v1"
    assert receipt["status"] == "ready"
    assert receipt["release_promotion_allowed"] is True


def test_unpinned_action_blocks_release_readiness(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "actions/checkout@v7"),
        encoding="utf-8",
    )

    receipt = evaluate_security_supply_chain(tmp_path)

    assert receipt["status"] == "blocked"
    assert receipt["release_promotion_allowed"] is False
    assert any(failure["control"] == "immutable-least-privilege-actions" for failure in receipt["failures"])


def test_new_unadmitted_shell_boundary_blocks_release_readiness(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    extra = tmp_path / "src/agentic_workspace/unsafe.py"
    extra.write_text("import subprocess\nsubprocess.run('echo unsafe', shell=True)\n", encoding="utf-8")

    receipt = evaluate_security_supply_chain(tmp_path)

    assert receipt["status"] == "blocked"
    shell = next(control for control in receipt["controls"] if control["id"] == "trusted-shell-admission")
    assert "src/agentic_workspace/unsafe.py" in shell["shell_true_paths"]


def test_exact_subject_changes_with_lock_workflow_checker_and_source(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    baseline = evaluate_security_supply_chain(tmp_path)["subject_fingerprint"]
    for relative in ("uv.lock", ".github/workflows/ci.yml", "scripts/check/check_security_supply_chain.py"):
        path = tmp_path / relative
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n# freshness change\n", encoding="utf-8")
        assert evaluate_security_supply_chain(tmp_path)["subject_fingerprint"] != baseline
        path.write_text(original, encoding="utf-8")
    artifacts = tmp_path / "dist"
    artifacts.mkdir()
    (artifacts / "candidate.whl").write_bytes(b"candidate-a")
    first = evaluate_security_supply_chain(tmp_path, source_identity="commit-a", artifact_dir=artifacts)
    (artifacts / "candidate.whl").write_bytes(b"candidate-b")
    second = evaluate_security_supply_chain(tmp_path, source_identity="commit-a", artifact_dir=artifacts)
    third = evaluate_security_supply_chain(tmp_path, source_identity="commit-b", artifact_dir=artifacts)
    assert first["subject_fingerprint"] != second["subject_fingerprint"]
    assert second["subject_fingerprint"] != third["subject_fingerprint"]


def test_semantic_permission_scanner_and_locked_sync_fail_closed(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    security = tmp_path / ".github/workflows/security.yml"
    original = security.read_text(encoding="utf-8")
    mutations = (
        ("contents: read", "contents: write", "immutable-least-privilege-actions"),
        ("gitleaks/gitleaks-action@", "example/no-op@", "blocking-security-scans"),
        ("runs-on: ubuntu-latest", "continue-on-error: true\n    runs-on: ubuntu-latest", "blocking-security-scans"),
        ("uv sync --locked", "uv sync", "locked-generator-and-runtime-dependencies"),
    )
    for old, new, control in mutations:
        security.write_text(original.replace(old, new, 1), encoding="utf-8")
        receipt = evaluate_security_supply_chain(tmp_path)
        assert receipt["status"] == "blocked"
        assert any(failure["control"] == control for failure in receipt["failures"])
    security.write_text(original, encoding="utf-8")


def test_repo_local_workflow_write_admission_is_required_and_fingerprinted(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    policy = tmp_path / ".github/workflow-write-permissions.json"
    baseline = evaluate_security_supply_chain(tmp_path)
    assert baseline["status"] == "ready"

    policy.unlink()
    blocked = evaluate_security_supply_chain(tmp_path)

    assert blocked["status"] == "blocked"
    assert blocked["subject_fingerprint"] != baseline["subject_fingerprint"]
    assert any(failure["control"] == "immutable-least-privilege-actions" for failure in blocked["failures"])


def test_release_promotion_requires_matching_current_security_receipt() -> None:
    receipt = evaluate_security_supply_chain(REPO_ROOT)
    accepted = workspace_runtime_core._security_readiness_promotion_input(
        receipt=receipt, expected_subject_fingerprint=receipt["subject_fingerprint"]
    )
    assert accepted["status"] == "accepted"
    for candidate, reason in (
        (None, "missing-security-readiness"),
        ({**receipt, "subject_fingerprint": "sha256:stale"}, "stale-or-mismatched-security-readiness"),
        ({**receipt, "status": "blocked", "release_promotion_allowed": False}, "failed-security-readiness"),
    ):
        blocked = workspace_runtime_core._security_readiness_promotion_input(
            receipt=candidate, expected_subject_fingerprint=receipt["subject_fingerprint"]
        )
        assert blocked["status"] == "blocked"
        assert blocked["reason"] == reason
