"""Direct owner journeys preserve proof/claim boundaries after wrapper removal."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]


def test_removed_wrappers_do_not_execute(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Reject retired procedure"}
    for command, request in [
        ("proof-procedure", {"operation": "execute"}),
        ("resources", {"operation": "scratch-create", "compose": True}),
    ]:
        result = subprocess.run(
            [str(shared_core_binary)], input=json.dumps({command: {**context, "request": request}}), text=True, capture_output=True
        )
        assert result.returncode != 0
    assert list(tmp_path.iterdir()) == []


def install(root):
    for reference in [".agentic-workspace/skills/REGISTRY.json", ".agentic-workspace/skills/workspace-proof-selection/SKILL.md"]:
        path = root / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / reference).read_bytes())


def procedure(binary, context, operation, **material):
    """Test caller following the shared fragments through direct owners.

    This is fixture choreography, never a shipped facade or authority source.
    """
    native = binary.with_name("agentic-workspace" + binary.suffix)

    def call(**fields):
        return consume("native", binary, native, {**context, **fields}, host_path=os.environ["PATH"])

    def present(full):
        return {
            "proof": full["verification"],
            "operating": {"decision_packet": full["decision_packet"], "advisory_context": full["memory"].get("advisory_context", [])},
            "completion_authority": False,
        }

    carried = material.get("request", [])
    carried = carried if isinstance(carried, list) else [carried]
    full = call(**({"request": carried} if carried else {}))
    if operation == "prepare":
        return present(full)
    assert operation == "execute"
    if not any(r["request_kind"] == "verification/execute-selected/v1" for r in carried):
        required = full["verification"]["required_execution"]
        if required["status"] != "unique-required-action":
            return present(full)
        request = required["request"]
        carried += request if isinstance(request, list) else [request]
        full = call(request=carried)
    actions = [a for a in full["decision_packet"]["ready_actions"] if a["operation_id"] == "proof.report"]
    if len(actions) != 1:
        return present(full)
    action = actions[0]
    effect = call(invocation=action)
    if effect["continuation_status"] != "current":
        return {"status": "reentry-required", "effect": effect, "retry_effect": False, "exact_reentry": {**context, "invocation": action}}
    prerequisites = [r for r in carried if r["request_kind"] not in ["verification/execute-selected/v1", "verification/claim/v1"]]
    current = call(request=prerequisites) if prerequisites else effect["continuation"]["result"]
    evidence = current["verification"]["requests"][0]
    evidence["arguments"]["evidence_refs"] = [*material.get("evidence_refs", []), effect["value"]["publication"]["reference"]]
    result = present(call(request=[*prerequisites, evidence]))
    result["effect"] = effect
    return result


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
    fragment = (ROOT / ".agentic-workspace/skills/workspace-proof-selection/references/select.md").read_text()
    identity = json.loads(fragment.split("```agentic-owner-reference\n", 1)[1].split("```", 1)[0])
    selected = consume("json", shared_core_binary, native_cli, {**context, "reference": identity})
    assert selected["status"] == "current" and selected["value"] == request
    assert not (tmp_path / "marker.txt").exists()
    result = procedure(shared_core_binary, context, "execute", request=request)
    assert result["effect"]["effect_outcome"]["status"] == "committed", result
    assert result["proof"]["evidence"][0]["checked_scope"]["claim"] == "selected-command-passed"
    assert result["proof"]["claim_review"]["status"] == "not-requested"
    assert result["completion_authority"] is False
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
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
    # Optional method drift does not change native owner authority or rerun proof.
    skill = tmp_path / ".agentic-workspace/skills/workspace-proof-selection/SKILL.md"
    skill.write_text(skill.read_text() + "\nUpdated selected method.\n")
    # Added source scope is material even with the original task/paths fixed.
    source.write_text(source.read_text() + '[protocols.added]\napplies_to_paths=["a.txt"]\ncommands=["echo new"]\n')
    expired = procedure(shared_core_binary, context, "execute", request=request)
    assert "effect" not in expired
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


def test_direct_owner_retains_strict_closeout_without_optional_skill(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "An ordinary change"}
    # No optional method is required to access current native owner constraints.
    before = procedure(shared_core_binary, context, "prepare")
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
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
    assert result["effect"]["effect_outcome"]["status"] == "committed"
    assert result["effect"]["continuation_status"] == "current"
    assert result["proof"]["evidence"][0]["checked_scope"]["claim"] == "selected-command-passed"
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
    # Follow the owner-established requirement, retaining independent claim judgment.
    result = procedure(shared_core_binary, context, "execute")
    assert result["effect"]["effect_outcome"]["status"] == "committed", result
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
