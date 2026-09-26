from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src/tooling/check"))
from check_rust_dependencies import check as check_rust_dependencies  # noqa: E402
from check_security_supply_chain import evaluate_security_supply_chain  # noqa: E402


def _copy_security_surface(target: Path) -> None:
    paths = [
        "SECURITY.md",
        "docs/security/threat-model.md",
        "uv.lock",
        "pyproject.toml",
        "src/core/src/modules/verification/native_proof.rs",
        "src/tooling/contracts/security_supply_chain_policy.json",
        "src/tooling/check/check_security_supply_chain.py",
        "src/tooling/release/release_lifecycle.py",
        "src/tooling/release/stable_manifest.py",
        ".github/workflow-write-permissions.json",
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain.toml",
        "deny.toml",
        "src/tooling/check/check_rust_dependencies.py",
    ]
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)
    shutil.copytree(REPO_ROOT / ".github/workflows", target / ".github/workflows")
    for manifest in (REPO_ROOT / "src/core/Cargo.toml", REPO_ROOT / "src/cli/rust/Cargo.toml"):
        destination = target / manifest.relative_to(REPO_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest, destination)


def test_repository_security_supply_chain_readiness_is_exact_and_ready() -> None:
    receipt = evaluate_security_supply_chain(REPO_ROOT)

    assert receipt["status"] == "ready", receipt["failures"]
    assert receipt["release_promotion_allowed"] is True
    assert receipt["subject_fingerprint"].startswith("sha256:")
    assert {control["status"] for control in receipt["controls"]} == {"pass"}


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
    extra = tmp_path / "src/unsafe.py"
    extra.write_text("import subprocess\nsubprocess.run('echo unsafe', shell=True)\n", encoding="utf-8")

    receipt = evaluate_security_supply_chain(tmp_path)

    assert receipt["status"] == "blocked"
    shell = next(control for control in receipt["controls"] if control["id"] == "trusted-shell-admission")
    assert "src/unsafe.py" in shell["shell_true_paths"]


def test_exact_subject_changes_with_lock_workflow_checker_and_source(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    baseline = evaluate_security_supply_chain(tmp_path)["subject_fingerprint"]
    for relative in (
        "uv.lock",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        "src/tooling/check/check_security_supply_chain.py",
        "Cargo.lock",
        "deny.toml",
        "src/tooling/check/check_rust_dependencies.py",
        "src/core/Cargo.toml",
    ):
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


def test_rust_policy_runner_enforces_version_lock_and_propagates_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    policy = json.loads((REPO_ROOT / "src/tooling/contracts/security_supply_chain_policy.json").read_text(encoding="utf-8"))
    observed = f"cargo-deny {policy['rust_dependencies']['version']}"
    failed = False

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["check"] is True
        if "check" in command and failed:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, stdout=observed)

    monkeypatch.setattr(subprocess, "run", run)
    check_rust_dependencies()
    assert calls[-1] == ["cargo", "deny", "--locked", "--config", "deny.toml", "check", "advisories", "licenses", "sources"]
    failed = True
    with pytest.raises(subprocess.CalledProcessError):
        check_rust_dependencies()
    observed = "cargo-deny 0.0.0"
    calls.clear()
    with pytest.raises(ValueError, match="Expected cargo-deny"):
        check_rust_dependencies()
    assert len(calls) == 1  # A different tool must never evaluate the policy.


def test_rust_gate_missing_from_either_publisher_blocks_readiness(tmp_path: Path) -> None:
    _copy_security_surface(tmp_path)
    for relative in (".github/workflows/security.yml", ".github/workflows/release.yml"):
        path = tmp_path / relative
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("python src/tooling/check/check_rust_dependencies.py --install", "echo skipped"), encoding="utf-8")
        receipt = evaluate_security_supply_chain(tmp_path)
        assert receipt["release_promotion_allowed"] is False
        assert any(failure["control"] == "rust-dependency-policy-wiring" for failure in receipt["failures"])
        path.write_text(original, encoding="utf-8")
