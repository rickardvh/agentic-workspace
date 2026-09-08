"""Accepted override policies preserve exact source authority and provenance."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_external_operation_clients import _run_typescript_assignment

from agentic_workspace.assignment_source import current_replacement, execution_configuration, revision
from agentic_workspace.client import AWClientError
from agentic_workspace.generated_operations import assignment_export, assignment_reassign


@pytest.mark.parametrize("language", ["python", "typescript"])
@pytest.mark.parametrize("policy", [None, "explicit-only", "allowed-with-recorded-reason", "disallowed"])
def test_public_override_policy_requires_source_and_records_reason(tmp_path: Path, language: str, policy: str | None) -> None:
    _exercise_override(tmp_path, language, policy)


@pytest.mark.parametrize("language", ["python", "typescript"])
@pytest.mark.parametrize("failure", ["missing-source", "stale-answer", "missing-reason", "tampered-packet"])
def test_recorded_reason_cannot_authorize_or_refresh_override(tmp_path: Path, language: str, failure: str) -> None:
    _exercise_override(tmp_path, language, "allowed-with-recorded-reason", failure)


def _exercise_override(tmp_path: Path, language: str, policy: str | None, failure: str = "") -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/feature.py").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "src/feature.py"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=AW Tests", "-c", "user.email=tests@example.com", "commit", "-qm", "baseline"],
        check=True,
    )
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    (source.parent / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    config = 'schema_version = 1\n[delegation]\nassignment_policy = "required-best-fit"\ntransport_authority = "manual"\n'
    if policy is not None:
        config += f'human_override_policy = "{policy}"\n'
    config += 'current_target = "orchestrator"\n'
    config += """[delegation_targets.orchestrator]
strength = "strong"
location = "local"
transports = [{kind="internal"}]
[delegation_targets.worker]
strength = "strong"
location = "external"
execution_methods = ["manual"]
transports = [{kind="manual"}]
"""
    replacement_config = """[delegation_targets.next_worker]
target_id = "next-worker"
target_revision = "1"
strength = "strong"
location = "external"
execution_methods = ["manual"]
transports = [{kind="manual"}]
"""
    source.write_text(config, encoding="utf-8")
    invocation = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/run_agentic_workspace.py")]

    def export(values):
        try:
            return (
                _run_typescript_assignment(tmp_path, "export", values)
                if language == "typescript"
                else assignment_export(values, target=tmp_path, invocation=invocation)
            )
        except AWClientError as error:
            pytest.fail(json.dumps(error.details))

    values = {"task": "Implement the bounded feature change.", "changed": ["src/feature.py"], "dry_run": True}
    missing = export(values)
    assert missing["status"] == "requirements-required", missing
    assert not missing["mutation_applied"]
    judgment = missing["preview"]["task_requirements"]["judgment_request"]["arguments"]
    judgment["required_result_classes"] = ["unapplied-patch"]
    values["task_judgment_json"] = json.dumps(judgment)
    preview = export(values)
    assert preview["preview"]["task_requirements"]["status"] == "resolved", preview
    offers = preview["preview"]["execution_configurations"]
    chosen = next(
        row["configuration"]
        for row in offers["candidates"]
        if row["eligible"] and row["configuration"]["target"] == "worker" and row["configuration"]["transport"] == "manual"
    )
    exported = export(
        {**values, "dry_run": False, "transport": "manual", "configuration_revision": offers["revision"], "configuration_id": chosen["id"]}
    )
    assert exported["status"] == "handoff-prepared", json.dumps(exported)
    old_packet = json.loads(
        (tmp_path / next(ref for ref in exported["artifact_refs"] if ref.endswith("packet.json"))).read_text(encoding="utf-8")
    )
    identity = old_packet["assignment_identity"]
    assert identity["task_judgment"] == judgment
    assert old_packet["return_contract"]["required_identity"]["packet_integrity"] == old_packet["packet_integrity"]
    manifest = json.loads(
        (tmp_path / next(ref for ref in exported["artifact_refs"] if ref.endswith("manifest.json"))).read_text(encoding="utf-8")
    )
    assert manifest["integrity"] == old_packet["packet_integrity"]
    config += replacement_config
    source.write_text(config, encoding="utf-8")
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
    if failure == "tampered-packet":
        damaged = json.loads(json.dumps(old_packet))
        damaged["assignment_identity"]["human_intent"] = "Different work after sealing"
        (tmp_path / next(ref for ref in exported["artifact_refs"] if ref.endswith("packet.json"))).write_text(
            json.dumps(damaged), encoding="utf-8"
        )
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
    result = (
        _run_typescript_assignment(tmp_path, "reassign", args)
        if language == "typescript"
        else assignment_reassign(args, target=tmp_path, invocation=invocation)
    )
    if failure or policy == "disallowed":
        assert result["status"] == "blocked", json.dumps(result)
        expected_reason = {
            "missing-source": "assignment-override-authority-unavailable",
            "stale-answer": "assignment-override-stale-work",
            "missing-reason": "missing-required-input",
            "tampered-packet": "assignment-override-stale-work",
            "": "assignment-override-authority-unavailable",
        }[failure]
        assert expected_reason in {item["reason"] for item in result["failures"]}, json.dumps(result)
        assert not result["mutation_applied"]
        assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
        return
    assert result["status"] == "replaced", json.dumps(result)
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
    assert exported["status"] == "handoff-prepared", json.dumps(exported)
    if policy == "allowed-with-recorded-reason":
        assert current_replacement(tmp_path, packet, packet["replacement"]["work"])["status"] == "current"
        tampered = json.loads(json.dumps(packet))
        tampered["replacement"]["source"]["recorded_reason"] = "Changed after sealing"
        with pytest.raises(ValueError):
            current_replacement(tmp_path, tampered, tampered["replacement"]["work"])
