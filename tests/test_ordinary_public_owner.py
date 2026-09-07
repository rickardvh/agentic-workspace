"""Ordinary generated clients preserve current source-owner decisions."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(target: Path, runtime: str, *arguments: str, expected_exit: int = 0) -> dict:
    prefix = (
        [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]
        if runtime == "python"
        else ["node", str(ROOT / "generated/workspace/typescript/src/cli.mjs")]
    )
    result = subprocess.run(
        [*prefix, *arguments, "--target", str(target), "--format", "json"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == expected_exit, (result.stdout, result.stderr)
    return json.loads(result.stdout) if result.stdout else {"diagnostic": result.stderr}


@pytest.mark.parametrize("runtime", ["python", "typescript"])
@pytest.mark.parametrize("operation", ["start", "implement"])
def test_ordinary_public_owner_uses_current_local_policy(tmp_path: Path, runtime: str, operation: str) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/introduction.md").write_text("# A small project\n")
    arguments = [operation, "--task", "Correct the spelling in the introduction", "--changed", "docs/introduction.md"]
    quiet = _run(tmp_path, runtime, *arguments)
    assert quiet["decision_packet"]["surface"] == operation
    assert "effective_orchestration" not in quiet
    local = tmp_path / ".agentic-workspace/config.local.toml"
    local.write_text("""schema_version = 1
[runtime]
supports_internal_delegation = true
[safety]
safe_to_auto_run_commands = true
[delegation]
assignment_policy = "required-best-fit"
transport_authority = "manual"
current_target = "current"
[delegation_targets.current]
strength = "strong"
execution_methods = ["internal"]
capability_classes = ["boundary-shaping", "reasoning-heavy", "mechanical-follow-through"]
[delegation_targets.bounded]
strength = "weak"
execution_methods = ["manual"]
capability_classes = ["mechanical-follow-through"]
""")
    configured = _run(tmp_path, runtime, *arguments)
    if operation == "start":
        assert configured["effective_orchestration"]["assignment"]["authority"] == "binding"
    child = configured["task_assignment_disposition"]["bounded_child_assignment"]
    assert child["selected_target"] == "bounded"
    assert child["implementation_allowed"] is False
    assert child["required_next_action"] == "materialize-canonical-assignment"
    assert configured["task_assignment_disposition"]["next_action"]["operation_invocation"]["operation_id"] == "assignment.export"
    assert configured["decision_packet"]["effects"]["implementation_allowed"] is False, configured
    # Source drift is consumed on each call; a current local winner stays local.
    local.write_text(local.read_text().replace('current_target = "current"', 'current_target = "bounded"'))
    retained = _run(tmp_path, runtime, *arguments)
    assert retained["task_assignment_disposition"]["outcome"] == "execute-here"
    assert retained["task_assignment_disposition"]["bounded_child_assignment"]["status"] == "selected-current"
    assert not (tmp_path / ".agentic-workspace/planning/assignments").exists()


@pytest.mark.parametrize("runtime", ["python", "typescript"])
def test_ordinary_semantic_request_retains_exact_source_currentness(tmp_path: Path, runtime: str) -> None:
    from tests.test_shared_core import _commit_native, _native_archive, _write_native

    _, record = _native_archive(tmp_path)
    record["semantic_routes"] = ["architecture/authority"]
    _write_native(tmp_path / "design/choice.md", record)
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "architecture", "semantic_routes": ["architecture/authority"]}]}))
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        "schema_version = 1\n[modules]\nenabled = []\n[assurance]\n"
        'decision_record_target = "design"\ndecision_record_revision = "' + revision + '"\n'
    )
    arguments = ["start", "--task", "Consider the design"]
    quiet = _run(tmp_path, runtime, *arguments)
    assert "decision_context" not in quiet["decision_packet"]
    discovered = _run(tmp_path, runtime, *arguments, "--select", "semantic_route_result")["values"]["semantic_route_result"]
    request = discovered["requests"][1]
    request["arguments"] = {"posture": "selected", "routes": ["architecture/authority"]}
    current = _run(tmp_path, runtime, *arguments, "--request", json.dumps(request))["decision_packet"]
    assert current["semantic_route_result"]["status"] == "current"
    assert current["decision_context"]["consequences"][0]["id"] == record["id"]
    stale = _run(tmp_path, runtime, "start", "--task", "A different bounded task", "--request", json.dumps(request))["decision_packet"]
    assert stale["semantic_route_result"]["status"] == "stale"
    assert "decision_context" not in stale
    registry.write_text(registry.read_text() + "\n")
    drift = _run(tmp_path, runtime, *arguments, "--request", json.dumps(request))["decision_packet"]
    assert drift["semantic_route_result"]["status"] == "stale"
    assert "decision_context" not in drift
    assert not (tmp_path / ".agentic-workspace/local/current-task-routes.json").exists()


@pytest.mark.parametrize("runtime", ["python", "typescript"])
def test_ordinary_invalid_local_policy_exposes_owner_error(tmp_path: Path, runtime: str) -> None:
    config = tmp_path / ".agentic-workspace/config.local.toml"
    config.parent.mkdir()
    config.write_text('schema_version = 1\n[delegation]\nassignment_policy = "required-best-fitt"\n')
    result = _run(tmp_path, runtime, "start", "--task", "Correct the spelling", expected_exit=2)
    if runtime == "typescript":
        assert result["status"] == "rejected"
        assert result["reason_code"] == "ordinary-owner-operation-rejected"
    assert ".agentic-workspace/config.local.toml assignment_policy must be one of:" in result["diagnostic"]
    assert "local-preferred, best-fit-advisory, required-best-fit" in result["diagnostic"]
    assert "decision_packet" not in result
