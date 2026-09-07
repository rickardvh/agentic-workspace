"""Accepted override policies preserve exact source authority and provenance."""

import json
from pathlib import Path

import pytest
from tests.test_external_operation_clients import _prepare_shared_worktree_assignment, _run_typescript_assignment

from agentic_workspace.assignment_source import current_replacement, execution_configuration, revision
from agentic_workspace.generated_operations import assignment_export, assignment_reassign


@pytest.mark.parametrize("language", ["python", "typescript"])
@pytest.mark.parametrize("policy", [None, "explicit-only", "allowed-with-recorded-reason", "disallowed"])
def test_public_override_policy_requires_source_and_records_reason(tmp_path: Path, language: str, policy: str | None) -> None:
    _exercise_override(tmp_path, language, policy)


@pytest.mark.parametrize("language", ["python", "typescript"])
@pytest.mark.parametrize("failure", ["missing-source", "stale-answer", "missing-reason"])
def test_recorded_reason_cannot_authorize_or_refresh_override(tmp_path: Path, language: str, failure: str) -> None:
    _exercise_override(tmp_path, language, "allowed-with-recorded-reason", failure)


def _exercise_override(tmp_path: Path, language: str, policy: str | None, failure: str = "") -> None:
    identity, invocation, _ = _prepare_shared_worktree_assignment(tmp_path, run_id="override-policy")
    plan_path = tmp_path / identity["plan_ref"]
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text(json.dumps({"revision": identity["plan_revision"]}))
    old_packet = json.loads((tmp_path / ".agentic-workspace/local/assignment-runs/override-policy/export/packet.json").read_text())
    source = tmp_path / ".agentic-workspace/config.local.toml"
    config = "schema_version = 1\n[delegation]\n"
    if policy is not None:
        config += f'human_override_policy = "{policy}"\n'
    config += """[delegation_targets.next_worker]
target_id = "next-worker"
target_revision = "1"
strength = "strong"
location = "external"
transports = [{kind="manual"}]
"""
    source.write_text(config)
    execution = execution_configuration(tmp_path, "next_worker", "manual")
    answer = {
        "assignment_id": old_packet["assignment_id"],
        "assignment_revision": "stale" if failure == "stale-answer" else old_packet["assignment_revision"],
        "work_id": identity["slice_id"],
        "work_revision": identity["plan_revision"],
        "target": "next_worker",
        "transport": "manual",
        "execution_revision": revision(execution),
        "packet_integrity": old_packet["packet_integrity"],
    }
    if failure != "missing-source":
        source.write_text(
            config + "\n[delegation.replacement]\n" + "\n".join(f"{key} = {json.dumps(value)}" for key, value in answer.items())
        )
    args = {
        "assignment_id": old_packet["assignment_id"],
        "assignment_revision": old_packet["assignment_revision"],
        "run_id": old_packet["run_id"],
        "target_name": "next_worker",
        "transport": "manual",
        "reason": "  Prefer this current permitted configuration for the bounded work.  ",
    }
    if failure == "missing-reason":
        args.pop("reason")
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
    result = (
        _run_typescript_assignment(tmp_path, "reassign", args)
        if language == "typescript"
        else assignment_reassign(args, target=tmp_path, invocation=invocation)
    )
    if failure or policy == "disallowed":
        assert result["status"] == "blocked", result
        expected_reason = {
            "missing-source": "assignment-override-authority-unavailable",
            "stale-answer": "assignment-override-stale-work",
            "missing-reason": "missing-required-input",
            "": "assignment-override-authority-unavailable",
        }[failure]
        assert expected_reason in {item["reason"] for item in result["failures"]}, result
        assert not result["mutation_applied"]
        assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
        return
    assert result["status"] == "replaced", result
    packet = result["replacement_packet"]
    provenance = packet["replacement"]["source"]
    assert provenance["human_override_policy"] == (policy or "explicit-only")
    assert provenance.get("recorded_reason") == (args["reason"].strip() if policy == "allowed-with-recorded-reason" else None)
    export_args = {key: packet[key] for key in ("assignment_id", "assignment_revision", "run_id", "transport")}
    exported = (
        _run_typescript_assignment(tmp_path, "export", export_args)
        if language == "typescript"
        else assignment_export(export_args, target=tmp_path, invocation=invocation)
    )
    assert exported["status"] == "handoff-prepared", exported
    if policy == "allowed-with-recorded-reason":
        assert current_replacement(tmp_path, packet, packet["replacement"]["work"])["status"] == "current"
        tampered = json.loads(json.dumps(packet))
        tampered["replacement"]["source"]["recorded_reason"] = "Changed after sealing"
        with pytest.raises(ValueError):
            current_replacement(tmp_path, tampered, tampered["replacement"]["work"])
