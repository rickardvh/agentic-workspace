from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "release" / "promote_command_generation_release.py"
SEMANTIC_PROOF_SCRIPT = REPO_ROOT / "scripts" / "check" / "run_generated_command_package_proof.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("promote_command_generation_release", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_semantic_proof_module():
    spec = importlib.util.spec_from_file_location("run_generated_command_package_proof_promotion_test", SEMANTIC_PROOF_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_fixture_repo(repo: Path, *, dependency_url: str) -> None:
    (repo / "generated" / "python").mkdir(parents=True)
    (repo / "generated").mkdir(exist_ok=True)
    (repo / "pyproject.toml").write_text(
        f'[dependency-groups]\ndev = [\n  "command-generation @ {dependency_url}",\n]\n',
        encoding="utf-8",
    )
    for relative in (
        "generated/python/Dockerfile.conformance",
        "generated/python/Dockerfile.primitive-conformance",
        "generated/typescript.conformance.Dockerfile",
    ):
        (repo / relative).write_text(
            f'RUN python -m pip install "command-generation @ {dependency_url}"\n',
            encoding="utf-8",
        )


def _security_readiness_receipt(*, subject: str = "sha256:candidate") -> dict[str, object]:
    return {
        "kind": "agentic-workspace/security-supply-chain-readiness/v1",
        "status": "ready",
        "release_promotion_allowed": True,
        "subject_fingerprint": subject,
    }


def _current_strict_health_policy_fingerprint() -> str:
    from agentic_workspace import workspace_runtime_core

    return workspace_runtime_core._strict_health_policy_fingerprint()


def _strict_health_receipt(*, subject: str = "sha256:candidate") -> dict[str, object]:
    return {
        "kind": "agentic-workspace/health-policy-proof-receipt/v1",
        "outcome": "passed",
        "policy_fingerprint": _current_strict_health_policy_fingerprint(),
        "subject_fingerprint": subject,
        "blocking_count": 0,
    }


def test_typescript_conformance_dockerfile_exposes_verification_runtime_source() -> None:
    dockerfile = (REPO_ROOT / "generated/typescript.conformance.Dockerfile").read_text(encoding="utf-8")

    assert "COPY README.md ./README.md" in dockerfile
    assert "/work/packages/verification/src" in dockerfile
    assert "./packages/verification ." in dockerfile


def test_promote_command_generation_release_updates_pyproject_and_dockerfiles(tmp_path: Path) -> None:
    module = _load_module()
    old_url = (
        "https://github.com/rickardvh/command-generation/releases/download/v1.0.0/"
        "command_generation-1.0.0-py3-none-any.whl#sha256=" + "0" * 64
    )
    release = module.CommandGenerationRelease(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="a" * 64,
    )
    _write_fixture_repo(tmp_path, dependency_url=old_url)

    result = module.promote_command_generation_release(
        repo_root=tmp_path,
        release=release,
        refresh_lock=False,
        security_readiness_receipt=_security_readiness_receipt(),
        expected_security_subject_fingerprint="sha256:candidate",
        strict_health_receipt=_strict_health_receipt(),
        expected_strict_health_subject_fingerprint="sha256:candidate",
    )

    assert result.changed_paths == (
        "pyproject.toml",
        "generated/python/Dockerfile.conformance",
        "generated/python/Dockerfile.primitive-conformance",
        "generated/typescript.conformance.Dockerfile",
    )
    assert result.promotion_inputs[0]["status"] == "accepted"
    assert result.promotion_inputs[0]["input"] == "security-supply-chain-readiness"
    assert result.promotion_inputs[1]["status"] == "accepted"
    assert result.promotion_inputs[1]["input"] == "strict-current-health"
    assert release.dependency_spec in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    for relative in module.DOCKERFILE_REFS:
        assert release.dependency_spec in (tmp_path / relative).read_text(encoding="utf-8")


def test_promote_command_generation_release_check_reports_stale_refs(tmp_path: Path) -> None:
    module = _load_module()
    old_url = (
        "https://github.com/rickardvh/command-generation/releases/download/v1.0.0/"
        "command_generation-1.0.0-py3-none-any.whl#sha256=" + "0" * 64
    )
    release = module.CommandGenerationRelease(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="a" * 64,
    )
    _write_fixture_repo(tmp_path, dependency_url=old_url)

    result = module.promote_command_generation_release(
        repo_root=tmp_path,
        release=release,
        check=True,
        security_readiness_receipt=_security_readiness_receipt(),
        expected_security_subject_fingerprint="sha256:candidate",
        strict_health_receipt=_strict_health_receipt(),
        expected_strict_health_subject_fingerprint="sha256:candidate",
    )

    assert result.changed_paths == ()
    assert set(result.stale_paths) == {"pyproject.toml", *module.DOCKERFILE_REFS}
    assert old_url in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("receipt_mutation", "reason"),
    [
        (None, "missing-security-readiness"),
        ({"subject_fingerprint": "sha256:stale"}, "stale-or-mismatched-security-readiness"),
        ({"status": "blocked", "release_promotion_allowed": False}, "failed-security-readiness"),
    ],
)
def test_release_promotion_blocks_invalid_security_readiness_before_writes(
    tmp_path: Path, receipt_mutation: dict[str, object] | None, reason: str
) -> None:
    module = _load_module()
    old_url = (
        "https://github.com/rickardvh/command-generation/releases/download/v1.0.0/"
        "command_generation-1.0.0-py3-none-any.whl#sha256=" + "0" * 64
    )
    release = module.CommandGenerationRelease(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="a" * 64,
    )
    _write_fixture_repo(tmp_path, dependency_url=old_url)
    receipt = None if receipt_mutation is None else {**_security_readiness_receipt(), **receipt_mutation}

    with pytest.raises(module.ReleasePromotionBlocked) as exc_info:
        module.promote_command_generation_release(
            repo_root=tmp_path,
            release=release,
            refresh_lock=False,
            security_readiness_receipt=receipt,
            expected_security_subject_fingerprint="sha256:candidate",
        )

    assert exc_info.value.decision["reason"] == reason
    assert old_url in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("receipt_mutation", "reason"),
    [
        (None, "missing-strict-health-receipt"),
        ({"subject_fingerprint": "sha256:stale"}, "stale-strict-health-subject"),
        ({"policy_fingerprint": "sha256:stale"}, "stale-strict-health-policy"),
        ({"outcome": "failed", "blocking_count": 1}, "strict-health-failed"),
    ],
)
def test_release_promotion_blocks_invalid_strict_health_before_writes(
    tmp_path: Path, receipt_mutation: dict[str, object] | None, reason: str
) -> None:
    module = _load_module()
    old_url = (
        "https://github.com/rickardvh/command-generation/releases/download/v1.0.0/"
        "command_generation-1.0.0-py3-none-any.whl#sha256=" + "0" * 64
    )
    release = module.CommandGenerationRelease(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="a" * 64,
    )
    _write_fixture_repo(tmp_path, dependency_url=old_url)
    receipt = None if receipt_mutation is None else {**_strict_health_receipt(), **receipt_mutation}

    with pytest.raises(module.ReleasePromotionBlocked) as exc_info:
        module.promote_command_generation_release(
            repo_root=tmp_path,
            release=release,
            refresh_lock=False,
            security_readiness_receipt=_security_readiness_receipt(),
            expected_security_subject_fingerprint="sha256:candidate",
            strict_health_receipt=receipt,
            expected_strict_health_subject_fingerprint="sha256:candidate",
        )

    assert exc_info.value.decision["reason"] == reason
    assert old_url in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")


def test_release_from_payload_uses_release_asset_digest() -> None:
    module = _load_module()
    payload = {
        "tag_name": "v1.2.3",
        "assets": [
            {
                "name": "command_generation-1.2.3-py3-none-any.whl",
                "browser_download_url": (
                    "https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl"
                ),
                "digest": "sha256:" + "b" * 64,
            }
        ],
    }

    release = module._release_from_payload(payload)

    assert release.version == "1.2.3"
    assert release.sha256 == "b" * 64
    assert release.dependency_spec.endswith("#sha256=" + "b" * 64)


def test_release_from_payload_rejects_missing_wheel_asset() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="has no command_generation-1.2.3-py3-none-any.whl asset"):
        module._release_from_payload({"tag_name": "v1.2.3", "assets": []})


def test_explicit_wheel_url_rejects_sha_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_sha256_url", lambda _url: "b" * 64)
    args = SimpleNamespace(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="a" * 64,
        trust_supplied_sha256=False,
    )

    with pytest.raises(SystemExit, match="SHA-256 mismatch"):
        module._release_from_args(args)


def test_explicit_wheel_url_can_trust_supplied_sha_for_offline_use(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()

    def fail_if_called(_url: str) -> str:
        raise AssertionError("offline trust mode must not download the wheel")

    monkeypatch.setattr(module, "_sha256_url", fail_if_called)
    args = SimpleNamespace(
        version="1.2.3",
        wheel_url="https://github.com/rickardvh/command-generation/releases/download/v1.2.3/command_generation-1.2.3-py3-none-any.whl",
        sha256="A" * 64,
        trust_supplied_sha256=True,
    )

    release = module._release_from_args(args)

    assert release.sha256 == "a" * 64


def test_semantic_receipt_verification_fails_closed_for_stale_or_mismatched_subject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_semantic_proof_module()
    artifact = tmp_path / "workspace-cli.tgz"
    artifact.write_bytes(b"exact-packed-artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    packages = [
        {
            "id": "root-workspace",
            "name": "@agentic-workspace/workspace-cli",
            "generated_root": "generated/workspace/typescript",
            "runnable": True,
        }
    ]
    monkeypatch.setattr(module, "_typescript_packages", lambda: packages)
    monkeypatch.setattr(module, "_registry_fingerprint", lambda: "sha256:current")
    subject = {
        "artifacts": [
            {
                "package_id": "root-workspace",
                "package_name": "@agentic-workspace/workspace-cli",
                "asset": artifact.name,
                "sha256": digest,
                "runnable": True,
                "conformance_status": "passed",
            }
        ],
        "runtime_identity": {"kind": "node", "version": "v24.0.0"},
        "validation_identity": {
            "runner": "scripts/check/run_generated_command_package_proof.py",
            "mode": "exact-packed-typescript-semantic-conformance",
            "registry_fingerprint": "sha256:stale",
        },
        "registry_fingerprint": "sha256:stale",
        "node_version": "v24.0.0",
        "execution_context": "hosted-ci",
    }
    receipt = {
        "kind": "agentic-workspace/generated-command-semantic-conformance-receipt/v1",
        "status": "passed",
        "receipt_id": "sha256:" + hashlib.sha256(json.dumps(subject, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "subject": subject,
        "environment_boundary": {
            "claim": "hosted semantic-lane evidence; the complete hosted workflow remains authoritative",
            "host_only_not_reproduced": ["hosted runner provisioning and image"],
        },
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 1

    receipt["subject"]["registry_fingerprint"] = "sha256:current"
    receipt["subject"]["validation_identity"]["registry_fingerprint"] = "sha256:current"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24, expected_execution_context="hosted-ci") == 0
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24, expected_execution_context="local") == 1

    receipt["subject"]["node_version"] = "v25.0.0"
    receipt["subject"]["runtime_identity"]["version"] = "v25.0.0"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=20) == 1

    receipt["subject"]["node_version"] = "24"
    receipt["subject"]["runtime_identity"]["version"] = "24"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 1

    receipt["subject"]["node_version"] = "v24.0.0"
    receipt["subject"]["runtime_identity"]["version"] = "v24.0.0"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    artifact.write_bytes(b"drifted-artifact")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 1


def test_release_workflow_requires_exact_artifact_semantic_receipts() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    ownership = json.loads((REPO_ROOT / ".github" / "release-ownership.json").read_text(encoding="utf-8"))

    assert ownership["semantic_conformance"]["required_for_support_bearing_typescript_release"] is True
    assert ownership["semantic_conformance"]["runtime_majors"] == [20, 24, 25]
    assert workflow.count("make packed-artifact-conformance PACKED_ARTIFACT_DIR=dist") == 3
    assert workflow.count("PACKED_ARTIFACT_CONTEXT=hosted-ci") == 3
    assert (
        '--verify-receipt "$receipt" --artifact-dir dist --expected-node-major "$runtime_major" --expected-execution-context hosted-ci'
    ) in workflow
    assert 'runtime_match.group("major")' in workflow
    assert '"semantic_conformance": {' in workflow
    assert "dist/generated-command-conformance-node*.json" in workflow
