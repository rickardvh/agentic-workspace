from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release/support_bearing_promotion.py"
spec = importlib.util.spec_from_file_location("support_bearing_promotion_under_test", SCRIPT)
assert spec is not None and spec.loader is not None
PROMOTION = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = PROMOTION
spec.loader.exec_module(PROMOTION)


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_server_check_receipt_binds_required_check_to_exact_commit() -> None:
    receipt = PROMOTION.server_check_receipt(
        repository="owner/repo",
        commit="expected",
        required=["Support-bearing promotion"],
        check_runs={
            "check_runs": [
                {
                    "name": "Support-bearing promotion",
                    "conclusion": "success",
                    "head_sha": "expected",
                    "html_url": "https://example.test/check",
                }
            ]
        },
    )
    assert receipt["status"] == "passed"
    assert receipt["source_commit"] == "expected"

    mismatched = PROMOTION.server_check_receipt(
        repository="owner/repo",
        commit="expected",
        required=["Support-bearing promotion"],
        check_runs={"check_runs": [{"name": "Support-bearing promotion", "conclusion": "success", "head_sha": "other"}]},
    )
    assert mismatched["status"] == "blocked"


def test_checked_in_master_ruleset_requires_review_and_merge_sufficiency() -> None:
    policy = json.loads((ROOT / ".github/support-bearing-promotion.json").read_text(encoding="utf-8"))
    ruleset = json.loads((ROOT / ".github/rulesets/master-support-bearing.json").read_text(encoding="utf-8"))
    assert policy["live_ruleset_id"] == 20615912
    assert policy["required_check"] == "Merge sufficiency"
    assert policy["python_support"] == {
        "declared": ["3.11", "3.12", "3.13", "3.14"],
        "minimum": "3.11",
        "primary": "3.13",
        "newest": "3.14",
        "intermediate_disposition": {
            "3.12": "Declared compatible and bounded by the minimum and primary lanes; no independent promotion lane is required."
        },
    }
    assert {item["role"]: item["python"] for item in policy["runtime_matrix"]} == {
        "minimum": "3.11",
        "primary": "3.13",
        "newest": "3.14",
    }
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["refs/heads/master"]
    rules = {rule["type"]: rule for rule in ruleset["rules"]}
    assert "non_fast_forward" in rules
    assert rules["pull_request"]["parameters"]["required_review_thread_resolution"] is True
    assert rules["required_status_checks"]["parameters"]["required_status_checks"] == [
        {"context": "Merge sufficiency"},
        {"context": "Review approval"},
    ]


def _compose_fixture(tmp_path: Path, commit: str = "release-commit") -> list[str]:
    dist = tmp_path / "dist"
    runtime = tmp_path / "runtime"
    dist.mkdir()
    runtime.mkdir()
    wheel = dist / "agentic_workspace-1.0.0-py3-none-linux_x86_64.whl"
    binary = b"fixture native executable"
    digest = hashlib.sha256(binary).hexdigest()
    manifest = {"rust_host": "x86_64-unknown-linux-gnu", "sha256": digest, "cli_sha256": digest}
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("agentic_workspace/_native/artifact.json", json.dumps(manifest))
        for name in ("agentic-workspace", "agentic-workspace-core"):
            archive.writestr(f"agentic_workspace/_native/{name}", binary)
    with zipfile.ZipFile(dist / "agentic-workspace-native-1.0.0-x86_64-unknown-linux-gnu.zip", "w") as archive:
        archive.writestr("artifact.json", json.dumps(manifest))
        for name in ("agentic-workspace", "agentic-workspace-core"):
            archive.writestr(name, binary)
    with tarfile.open(dist / "root.tgz", "w:gz") as archive:
        for name, data in {
            "package/package.json": {"os": ["linux"], "cpu": ["x64"]},
            "package/src/native/bin/artifact.json": manifest,
        }.items():
            raw = json.dumps(data).encode()
            entry = tarfile.TarInfo(name)
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
        for name in ("agentic-workspace", "agentic-workspace-core"):
            entry = tarfile.TarInfo("package/src/native/bin/" + name)
            entry.size = len(binary)
            archive.addfile(entry, io.BytesIO(binary))
    wheel_digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    server = _write(
        tmp_path / "server.json",
        {
            "kind": "agentic-workspace/server-promotion-receipt/v1",
            "status": "passed",
            "source_commit": commit,
        },
    )
    for os_name, python, node in (
        ("ubuntu-latest", "3.11", "20"),
        ("ubuntu-latest", "3.13", "24"),
        ("ubuntu-latest", "3.14", "24"),
    ):
        _write(
            runtime / f"{os_name}-py{python}-node{node}.json",
            {
                "kind": "agentic-workspace/runtime-support-receipt/v1",
                "status": "passed",
                "source_commit": commit,
                "os": os_name,
                "python": python,
                "node": node,
            },
        )
    semantic = []
    for major in (20, 24, 25):
        semantic.append(
            _write(
                dist / f"generated-command-conformance-node{major}.json",
                {
                    "kind": "agentic-workspace/native-release-conformance/v1",
                    "status": "passed",
                    "subject": {"node_version": f"v{major}.0.0"},
                },
            )
        )
    _write(
        dist / "distribution-install-readiness.json",
        {
            "kind": "agentic-workspace/distribution-install-readiness/v1",
            "status": "passed",
            "artifact": {"name": wheel.name, "sha256": wheel_digest},
        },
    )
    _write(
        dist / "redistributable-package-readiness.json",
        {
            "kind": "agentic-workspace/redistributable-package-readiness/v1",
            "status": "passed",
            "license_spdx": "MIT",
            "artifact_count": 3,
            "artifacts": [
                {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in dist.iterdir()
                if path.suffix in {".whl", ".tgz", ".zip"}
            ],
        },
    )
    _write(
        dist / "security-supply-chain-readiness.json",
        {
            "kind": "agentic-workspace/security-supply-chain-readiness/v1",
            "status": "ready",
            "release_promotion_allowed": True,
            "subject": {"source_identity": commit},
        },
    )
    return [
        "compose",
        "--commit",
        commit,
        "--artifact-dir",
        str(dist),
        "--server-receipt",
        str(server),
        "--runtime-receipt-dir",
        str(runtime),
        *[argument for path in semantic for argument in ("--semantic-receipt", str(path))],
        "--output",
        str(dist / "support-bearing-promotion.json"),
    ]


def test_composed_promotion_passes_only_with_every_exact_receipt(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    assert PROMOTION.main(args) == 0
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert set(result["domains"].values()) == {"passed", "ready"}
    assert result["artifacts"]


def test_composed_promotion_fails_closed_on_stale_or_missing_evidence(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    (tmp_path / "runtime/ubuntu-latest-py3.14-node24.json").unlink()
    security = tmp_path / "dist/security-supply-chain-readiness.json"
    payload = json.loads(security.read_text(encoding="utf-8"))
    payload["subject"]["source_identity"] = "stale"
    _write(security, payload)
    assert PROMOTION.main(args) == 1
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert any("runtime support receipt" in failure for failure in result["failures"])
    assert any("exact source commit" in failure for failure in result["failures"])


def test_python_support_policy_rejects_package_minimum_below_policy(tmp_path: Path) -> None:
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    for relative in (
        "pyproject.toml",
        "packages/memory/pyproject.toml",
        "packages/planning/pyproject.toml",
        "packages/verification/pyproject.toml",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    root_pyproject = tmp_path / "pyproject.toml"
    root_pyproject.write_text(
        root_pyproject.read_text(encoding="utf-8").replace('requires-python = ">=3.11"', 'requires-python = ">=3.10"', 1), encoding="utf-8"
    )
    policy = json.loads((tmp_path / ".github/support-bearing-promotion.json").read_text(encoding="utf-8"))

    assert PROMOTION.python_support_policy_failures(policy, tmp_path) == [
        "pyproject.toml requires-python '>=3.10' does not match policy minimum 3.11"
    ]


def test_composed_promotion_rejects_missing_runtime_receipt(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    (tmp_path / "runtime/ubuntu-latest-py3.11-node20.json").unlink()
    assert PROMOTION.main(args) == 1
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert any("missing runtime support receipt" in failure for failure in result["failures"])


def test_composed_promotion_fails_closed_on_invalid_semantic_runtime(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    receipt = tmp_path / "dist/generated-command-conformance-node20.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["subject"]["node_version"] = "20.0.0"
    _write(receipt, payload)

    assert PROMOTION.main(args) == 1
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert "generated-command-conformance-node20.json has invalid semantic-conformance Node version '20.0.0'" in result["failures"]
    assert "missing semantic conformance for Node majors: [20]" in result["failures"]


def test_composed_promotion_rejects_redistribution_artifact_drift(tmp_path: Path) -> None:
    args = _compose_fixture(tmp_path)
    (tmp_path / "dist/agentic_workspace-1.0.0-py3-none-linux_x86_64.whl").write_bytes(b"tampered-wheel")
    assert PROMOTION.main(args) == 1
    result = json.loads((tmp_path / "dist/support-bearing-promotion.json").read_text(encoding="utf-8"))
    assert "redistribution receipt does not bind the exact distributable artifact names and sha256 digests" in result["failures"]


def test_supported_windows_receipt_cannot_replace_missing_published_artifacts(tmp_path):
    _compose_fixture(tmp_path)
    policy = json.loads((ROOT / ".github/support-bearing-promotion.json").read_text())
    policy["runtime_matrix"].append({"os": "windows-latest", "python": "3.14", "node": "24"})
    policy["published_platforms"]["windows-latest"] = {
        "rust_host": "x86_64-pc-windows-msvc",
        "wheel_platform": "win_amd64",
        "node_platform": "win32",
        "node_arch": "x64",
    }
    failures = PROMOTION.published_platform_failures(policy, tmp_path / "dist")
    assert any("windows-latest" in failure and "installable wheel" in failure for failure in failures)


def test_published_linux_set_requires_npm_and_standalone_pair(tmp_path):
    _compose_fixture(tmp_path)
    policy = json.loads((ROOT / ".github/support-bearing-promotion.json").read_text())
    assert PROMOTION.published_platform_failures(policy, tmp_path / "dist") == []
    (tmp_path / "dist/root.tgz").unlink()
    assert any("installable npm" in failure for failure in PROMOTION.published_platform_failures(policy, tmp_path / "dist"))
