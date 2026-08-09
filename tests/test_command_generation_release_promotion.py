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

    result = module.promote_command_generation_release(repo_root=tmp_path, release=release, refresh_lock=False)

    assert result.changed_paths == (
        "pyproject.toml",
        "generated/python/Dockerfile.conformance",
        "generated/python/Dockerfile.primitive-conformance",
        "generated/typescript.conformance.Dockerfile",
    )
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

    result = module.promote_command_generation_release(repo_root=tmp_path, release=release, check=True)

    assert result.changed_paths == ()
    assert set(result.stale_paths) == {"pyproject.toml", *module.DOCKERFILE_REFS}
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
        "registry_fingerprint": "sha256:stale",
        "node_version": "v24.0.0",
    }
    receipt = {
        "kind": "agentic-workspace/generated-command-semantic-conformance-receipt/v1",
        "status": "passed",
        "receipt_id": "sha256:" + hashlib.sha256(json.dumps(subject, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "subject": subject,
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 1

    receipt["subject"]["registry_fingerprint"] = "sha256:current"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 0

    receipt["subject"]["node_version"] = "v25.0.0"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=20) == 1

    receipt["subject"]["node_version"] = "24"
    receipt["receipt_id"] = (
        "sha256:" + hashlib.sha256(json.dumps(receipt["subject"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert module._verify_receipt(receipt_path, artifact_dir=tmp_path, expected_node_major=24) == 1

    receipt["subject"]["node_version"] = "v24.0.0"
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
    assert workflow.count("--packed-conformance --artifact-dir dist --receipt-out") == 3
    assert '--verify-receipt "$receipt" --artifact-dir dist --expected-node-major "$runtime_major"' in workflow
    assert 'runtime_match.group("major")' in workflow
    assert '"semantic_conformance": {' in workflow
    assert "dist/generated-command-conformance-node*.json" in workflow
