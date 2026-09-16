"""Selected composition preserves native proof/claim and method boundaries."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]


def install(root):
    for reference in [".agentic-workspace/skills/REGISTRY.json", ".agentic-workspace/skills/workspace-proof-selection/SKILL.md"]:
        path = root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / reference).read_bytes())


def procedure(binary, context, operation, **material):
    result = subprocess.run(
        [str(binary)],
        input=json.dumps({"proof-procedure": {**context, "request": {"operation": operation, **material}}}),
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_selected_check_to_receipt_and_remaining_claim(tmp_path, shared_core_binary, native_cli):
    install(tmp_path)
    (tmp_path / "a.txt").write_text("subject")
    context = {"target": str(tmp_path), "task": "Prove bounded behavior", "changed": ["a.txt"]}
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir()
    command = "Add-Content marker.txt executed" if os.name == "nt" else "echo executed >> marker.txt"
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[proof_routes]\n'
        '[protocols.test]\napplies_to_paths=["a.txt"]\ncommands=[' + json.dumps(command) + "]\n"
    )
    candidate = procedure(shared_core_binary, context, "execute")
    assert "effect" not in candidate  # One candidate is not a required action.
    first = procedure(shared_core_binary, context, "prepare")
    request = first["proof"]["execution_requests"][0]
    direct = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
    assert request == direct["verification"]["execution_requests"][0]
    result = procedure(shared_core_binary, context, "execute", request=request, expected_revision=first["procedure_revision"])
    assert result["effect"]["effect_outcome"]["status"] == "committed", result
    assert result["proof"]["evidence"][0]["checked_scope"]["claim"] == "selected-command-passed"
    assert result["proof"]["claim_review"]["status"] == "not-requested"
    assert result["completion_authority"] is False
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
    assert result["public_owner_calls"] == 3  # prepare, invoke (+native continuation), admit receipt
    print(
        {
            "prepare_bytes": len(json.dumps(first).encode()),
            "execute_result_bytes": len(json.dumps(result).encode()),
            "direct_full_start_bytes": len(json.dumps(direct).encode()),
            "composed_public_calls": 1 + result["public_owner_calls"],
        }
    )
    claim = result["proof"]["claim_review"]["request"]
    claim["arguments"] = {
        "disposition": "satisfied",
        "reason": "Fixture judgment on its exact bounded behavior.",
        "evidence_refs": [result["effect"]["value"]["publication"]["reference"]],
    }
    proposed = procedure(shared_core_binary, context, "prepare", request=claim)
    decision = next(
        d for d in proposed["operating"]["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review"
    )
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    resumed = procedure(shared_core_binary, context, "prepare", request=answer)
    assert resumed["proof"]["claim_review"]["status"] == "current"
    old_revision = first["procedure_revision"]
    (tmp_path / "unrelated.md").write_text("not method material")
    assert procedure(shared_core_binary, context, "prepare")["procedure_revision"] == old_revision
    skill = tmp_path / ".agentic-workspace/skills/workspace-proof-selection/SKILL.md"
    skill.write_text(skill.read_text() + "\nUpdated selected method.\n")
    stale = procedure(shared_core_binary, context, "execute", request=request, expected_revision=old_revision)
    assert stale["effect_outcome"] == "not-invoked"
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
    # Added source scope is material even with the original task/paths fixed.
    source.write_text(source.read_text() + '[protocols.added]\napplies_to_paths=["a.txt"]\ncommands=["echo new"]\n')
    expired = procedure(shared_core_binary, context, "execute", request=request)
    assert "effect" not in expired
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


def test_direct_missing_method_and_strict_closeout_without_protocol(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "An ordinary change"}
    direct = procedure(shared_core_binary, context, "direct")
    assert direct["public_owner_calls"] == 0 and list(tmp_path.iterdir()) == []
    missing = procedure(shared_core_binary, context, "prepare")
    assert missing["effect_outcome"] == "not-invoked"
    install(tmp_path)
    before = procedure(shared_core_binary, context, "prepare")
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text("[assurance]\nstrict_closeout=true\n")
    after = procedure(shared_core_binary, context, "prepare")
    assert after["proof"]["execution_requests"] == []
    assert after["proof"]["claim_review"]["request"] is not None
    assert "strict-closeout-judgment-required" in {b["code"] for b in after["operating"]["decision_packet"]["blockers"]}
    assert before["operating"]["decision_packet"]["blockers"] != after["operating"]["decision_packet"]["blockers"]
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_confirmed_check_survives_failed_continuation(tmp_path, shared_core_binary, native_cli):
    install(tmp_path)
    (tmp_path / "a.txt").write_text("subject")
    context = {"target": str(tmp_path), "task": "Exercise continuation failure", "changed": ["a.txt"]}
    command = (
        "Add-Content marker.txt executed; Set-Content .agentic-workspace/config.toml '[invalid'"
        if os.name == "nt"
        else "echo executed >> marker.txt; printf '[invalid' > .agentic-workspace/config.toml"
    )
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[proof_routes]\n'
        '[protocols.test]\napplies_to_paths=["a.txt"]\ncommands=[' + json.dumps(command) + "]\n"
    )
    first = procedure(shared_core_binary, context, "prepare")
    result = procedure(shared_core_binary, context, "execute", request=first["proof"]["execution_requests"][0])
    assert result["status"] == "reentry-required"
    assert result["effect"]["effect_outcome"]["status"] == "committed"
    assert result["effect"]["continuation_status"] == "unavailable"
    assert result["retry_effect"] is False
    assert result["exact_reentry"]["invocation"]["operation_id"] == "proof.report"
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


def test_optional_method_drift_preserves_current_frontier_and_effect(tmp_path, shared_core_binary, native_cli):
    install(tmp_path)
    (tmp_path / "a.txt").write_text("subject")
    context = {"target": str(tmp_path), "task": "Check method drift after effect", "changed": ["a.txt"]}
    skill = ".agentic-workspace/skills/workspace-proof-selection/SKILL.md"
    command = (
        f"Add-Content marker.txt executed; Add-Content {skill} changed"
        if os.name == "nt"
        else f"echo executed >> marker.txt; echo changed >> {skill}"
    )
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[proof_routes]\n'
        '[protocols.test]\napplies_to_paths=["a.txt"]\ncommands=[' + json.dumps(command) + "]\n"
    )
    first = procedure(shared_core_binary, context, "prepare")
    result = procedure(shared_core_binary, context, "execute", request=first["proof"]["execution_requests"][0])
    assert result["status"] == "reentry-required"
    assert result["effect"]["effect_outcome"]["status"] == "committed"
    assert result["effect"]["continuation_status"] == "current"
    assert "procedure changed" in result["diagnostic"]
    assert result["retry_effect"] is False
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


def test_owner_carries_sole_required_check_and_preserves_real_choices(tmp_path, shared_core_binary, native_cli):
    install(tmp_path)
    (tmp_path / "a.txt").write_text("subject")
    context = {"target": str(tmp_path), "task": "Satisfy the required check", "changed": ["a.txt"]}
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir()
    (tmp_path / ".agentic-workspace/config.toml").write_text("[assurance]\nstrict_closeout=true\n")
    command = "Add-Content marker.txt executed" if os.name == "nt" else "echo executed >> marker.txt"
    profile = (
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols]\n[proof_routes]\n'
        "[assurance.proof_profiles.required]\nrequired_commands=[" + json.dumps(command) + "]\n"
    )
    requirement = (
        '[assurance.requirements.current]\nlevel="high"\nforce="required-before-closeout"\n'
        'applies_to_paths=["a.txt"]\nproof_profile="required"\n'
    )
    for extra in (
        'optional_commands=["echo alternative"]\n',
        '[assurance.proof_profiles.unselected]\nrequired_commands=["echo lazy alternative"]\n',
    ):
        source.write_text(profile + extra + requirement)
        choice = procedure(shared_core_binary, context, "execute")
        assert "effect" not in choice
        assert choice["proof"]["required_execution"]["status"] == "not-settled"
        assert not (tmp_path / "marker.txt").exists()
    # Unresolved semantic applicability is still a judgment, never a task-word match.
    source.write_text(profile + requirement.replace('applies_to_paths=["a.txt"]\n', 'applies_to_task_markers=["required check"]\n'))
    unresolved = procedure(shared_core_binary, context, "execute")
    assert "effect" not in unresolved and unresolved["proof"]["assurance_request"] is not None
    source.write_text(profile + requirement)
    direct = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
    assert direct["verification"]["required_execution"]["status"] == "unique-required-action"
    # One caller interaction, with no execute-selected envelope copied by the model.
    result = procedure(shared_core_binary, context, "execute")
    assert result["effect"]["effect_outcome"]["status"] == "committed", result
    assert result["public_owner_calls"] == 4
    assert result["proof"]["evidence"][0]["checked_scope"]["claim"] == "selected-command-passed"
    assert result["proof"]["strategy_control"]["obligations"][0]["missing_commands"] == []
    assert result["proof"]["required_execution"]["status"] == "not-settled"
    assert result["proof"]["claim_review"]["status"] == "not-requested"
    assert "strict-closeout-judgment-required" in {b["code"] for b in result["operating"]["decision_packet"]["blockers"]}
    claim = direct["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["effect"]["value"]["publication"]["reference"]]
    settled = procedure(shared_core_binary, context, "execute", request=claim)
    assert "effect" not in settled
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
