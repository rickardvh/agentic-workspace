from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

from agentic_workspace.workspace_runtime_core import _load_test_strategy_dispositions

LAUNCHER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_agentic_workspace.py"


def _launcher():
    spec = importlib.util.spec_from_file_location("merge_safe_launcher", LAUNCHER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {LAUNCHER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, check=check, capture_output=True, text=True)


def _record(record_id: str, test_path: str, *, reason: str = "lane-owned proof") -> str:
    return (
        json.dumps(
            {
                "kind": "agentic-workspace/test-strategy-disposition/v1",
                "id": record_id,
                "disposition": "standalone-durable-contract-proof",
                "changed_test_paths": [test_path],
                "reason": reason,
                "proof_owner": record_id,
                "replacement_or_follow_up_evidence": [],
                "reviewer_requested_coverage": False,
            },
            indent=2,
        )
        + "\n"
    )


def _base_repo(root: Path) -> object:
    launcher = _launcher()
    _write(root / "pyproject.toml", '[project]\nname = "fixture"\n')
    _write(root / "uv.lock", "# lock\n")
    _write(root / "LICENSE", "MIT\n")
    _write(root / "scripts/generate/generate_command_packages.py", "# generator\n")
    _write(root / "scripts/generate/workspace_command_generation.py", "# generation adapter\n")
    packages = []
    for owner in ("planning", "memory"):
        operation = f"operations/{owner}.report.json"
        packages.append(
            {
                "id": f"{owner}-package",
                "operation_contract_root": f"packages/{owner}/contracts",
                "commands": [{"operation_ref": {"path": operation}}],
                "targets": [{"generated_root": f"generated/{owner}/python"}],
            }
        )
        _write(root / f"packages/{owner}/contracts/{operation}", '{"value": "base"}\n')
        _write(root / f"generated/{owner}/python/operation.json", '{"value": "base"}\n')
    _write(root / "src/agentic_workspace/contracts/command_package_ir.json", json.dumps({"packages": packages}) + "\n")
    for owner, manifest in launcher.source_cli_fingerprint_manifests(repo_root=root).items():
        _write(root / f"generated/{owner}/.agentic-workspace-cli-fingerprint.json", json.dumps(manifest, indent=2) + "\n")
    _git(root, "init", "-b", "base")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "base")
    return launcher


def test_disjoint_package_state_merges_in_either_order_with_same_derived_state(tmp_path: Path) -> None:
    launcher = _base_repo(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    for lane in ("a", "b"):
        _git(tmp_path, "switch", "-c", f"lane-{lane}", base)
        owner = "planning" if lane == "a" else "memory"
        _write(
            tmp_path / f".agentic-workspace/verification/test-strategy-dispositions/lane-{lane}.json",
            _record(f"lane-{lane}", f"tests/test_{lane}.py"),
        )
        _write(tmp_path / f"packages/{owner}/contracts/operations/{owner}.report.json", json.dumps({"value": lane}) + "\n")
        _write(tmp_path / f"generated/{owner}/python/operation.json", json.dumps({"value": lane}) + "\n")
        manifest = launcher.source_cli_fingerprint_manifest(repo_root=tmp_path, owner=owner)
        _write(tmp_path / f"generated/{owner}/.agentic-workspace-cli-fingerprint.json", json.dumps(manifest, indent=2) + "\n")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"lane {lane}")

    observed: list[tuple[list[str], str]] = []
    for branch, order in (("order-ab", ("lane-a", "lane-b")), ("order-ba", ("lane-b", "lane-a"))):
        _git(tmp_path, "switch", "-c", branch, base)
        for lane in order:
            _git(tmp_path, "merge", "--no-edit", lane)
        dispositions = _load_test_strategy_dispositions(tmp_path)
        status = launcher.source_cli_fingerprint_manifest_status(repo_root=tmp_path)
        observed.append(([item["id"] for item in dispositions["items"]], str(status["status"])))

    assert observed == [(["lane-a", "lane-b"], "current"), (["lane-a", "lane-b"], "current")]


def test_same_generated_owner_changes_conflict_explicitly(tmp_path: Path) -> None:
    launcher = _base_repo(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    for lane in ("a", "b"):
        _git(tmp_path, "switch", "-c", f"generated-{lane}", base)
        _write(tmp_path / "packages/planning/contracts/operations/planning.report.json", json.dumps({"value": lane}) + "\n")
        _write(tmp_path / "generated/planning/python/operation.json", json.dumps({"value": lane}) + "\n")
        manifest = launcher.source_cli_fingerprint_manifest(repo_root=tmp_path, owner="planning")
        _write(tmp_path / "generated/planning/.agentic-workspace-cli-fingerprint.json", json.dumps(manifest, indent=2) + "\n")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"generated owner {lane}")

    _git(tmp_path, "switch", "generated-a")
    conflict = _git(tmp_path, "merge", "--no-edit", "generated-b", check=False)
    assert conflict.returncode != 0
    conflicts = _git(tmp_path, "diff", "--name-only", "--diff-filter=U").stdout.replace("\\", "/").splitlines()
    assert "generated/planning/.agentic-workspace-cli-fingerprint.json" in conflicts
    assert "packages/planning/contracts/operations/planning.report.json" in conflicts


def test_same_owner_record_remains_a_real_git_conflict(tmp_path: Path) -> None:
    _base_repo(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    record_path = tmp_path / ".agentic-workspace/verification/test-strategy-dispositions/shared-owner.json"
    for lane in ("a", "b"):
        _git(tmp_path, "switch", "-c", f"same-{lane}", base)
        _write(record_path, _record("shared-owner", "tests/test_shared.py", reason=f"lane {lane}"))
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"same owner {lane}")

    _git(tmp_path, "switch", "same-a")
    conflict = _git(tmp_path, "merge", "--no-edit", "same-b", check=False)
    assert conflict.returncode != 0
    assert _git(tmp_path, "diff", "--name-only", "--diff-filter=U").stdout.strip().replace("\\", "/") == (
        ".agentic-workspace/verification/test-strategy-dispositions/shared-owner.json"
    )
