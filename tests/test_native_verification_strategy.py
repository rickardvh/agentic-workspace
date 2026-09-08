"""Source-bound strategy judgment without proof or reviewer authority."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def setup(root: Path, *, binding: bool = False) -> dict:
    (root / "a.txt").write_text("current")
    source = root / ".agentic-workspace/config.toml"
    source.parent.mkdir(parents=True)
    command = "Add-Content -Path marker.txt -Value executed" if os.name == "nt" else "echo executed >> marker.txt"
    source.write_text(
        'schema_version=1\n[assurance]\ndefault_level="medium"\nagent_may_escalate=true\nagent_may_deescalate=false\n[assurance.proof_profiles.required]\nrequired_commands=['
        + json.dumps(command)
        + ']\noptional_commands=["echo optional"]\ndisallowed_commands=["echo forbidden"]\n[assurance.proof_profiles.unrelated]\nrequired_commands=["echo unrelated"]\n'
    )
    if binding:
        with source.open("a") as stream:
            stream.write(
                '[assurance.requirements.current]\nlevel="high"\nforce="required-before-closeout"\napplies_to_paths=["a.txt"]\nproof_profile="required"\n'
            )
    return {"target": str(root), "task": "Check bounded source", "changed": ["a.txt"]}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_level_permissions_and_profiles_require_current_judgment(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = setup(tmp_path)

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    first = call(context)
    policy = first["verification"]["strategy_control"]
    assert policy["effective_level"] == "medium"
    assert policy["selected_profiles"] == []
    assert first["verification"]["execution_requests"] == []
    assert not any(
        row["field"]
        in ["assurance.default_level", "assurance.agent_may_escalate", "assurance.agent_may_deescalate", "assurance.proof_profiles"]
        for row in first["configuration"]["residuals"]
    )
    request = first["verification"]["strategy_request"]
    request["arguments"] = {"level": "low", "profile_ids": ["required"], "reason": "A bounded assessment"}
    denied = call({**context, "request": request})["verification"]
    assert denied["strategy_control"]["level_status"] == "rejected"
    assert "assurance-deescalation-not-authorized" in denied["strategy_control"]["gaps"]
    request["arguments"]["level"] = "high"
    selected = call({**context, "request": request})["verification"]
    assert selected["strategy_control"]["effective_level"] == "high"
    assert [row["id"] for row in selected["strategy_control"]["selected_profiles"]] == ["required"]
    assert all("unrelated" not in json.dumps(item) for item in selected["execution_requests"])
    complete = selected["execution_requests"][0]
    assert len(complete) == 2
    ready = call({**context, "request": complete})
    invocation = ready["decision_packet"]["primary_action"]
    assert invocation["operation_id"] == "proof.report"
    result = call({**context, "invocation": invocation})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["claim_boundary"]["completion_claim_allowed"] is False
    assert call({**context, "invocation": invocation})["value"] == result["value"]
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
    stale = call({**context, "task": "Unrelated outcome", "request": complete})
    assert "verification-request-stale" in stale["verification"]["evidence_gaps"]
    assert not any(action["source_owner"] == "verification" for action in stale["decision_packet"]["pending_consequences"]["actions"])
    assert not any(action["source_owner"] == "verification" for action in stale["decision_packet"]["ready_actions"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_binding_profiles_and_cross_route_disallowed_commands(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = setup(tmp_path, binding=True)
    source = tmp_path / ".agentic-workspace/config.toml"
    with source.open("a") as stream:
        stream.write(
            '[assurance.domain_proof_lanes.denied]\npurpose="Declared candidate"\napplies_to_paths=["a.txt"]\ncommands=["echo forbidden"]\n'
        )
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.denied]\napplies_to_paths=["a.txt"]\n[proof_routes.manifest_denied]\nprotocol_refs=["denied"]\ncommands=["echo forbidden"]\n'
    )

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    first = call(context)["verification"]
    assert first["strategy_control"]["selected_profiles"][0]["selected_by"] == "binding-requirement"
    request = first["strategy_request"]
    request["arguments"]["profile_ids"] = []
    selected = call({**context, "request": request})["verification"]
    assert [row["id"] for row in selected["strategy_control"]["selected_profiles"]] == ["required"]
    for route_id in ["domain:denied", "manifest_denied"]:
        denied = next(item for item in first["execution_requests"] if item["arguments"]["route_id"] == route_id)
        blocked = call({**context, "request": denied})
        assert blocked["verification"]["execution"]["reason"] == "selected-proof-profile-disallows-command"
        assert not any(action["source_owner"] == "verification" for action in blocked["decision_packet"]["pending_consequences"]["actions"])
        assert not any(action["source_owner"] == "verification" for action in blocked["decision_packet"]["ready_actions"])
    assert not (tmp_path / "marker.txt").exists()
    source.write_text(source.read_text().replace('force="required-before-closeout"', 'force="recommended"'))
    optional = call(context)["verification"]["strategy_control"]
    assert optional["selected_profiles"] == []
    assert optional["recommended_profiles"] == ["required"]


def test_current_scope_judgment_travels_with_profile_execution(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    context = setup(tmp_path)
    source = tmp_path / ".agentic-workspace/config.toml"
    with source.open("a") as stream:
        stream.write(
            '[workspace]\nagent_instructions_file="AGENTS.md"\n'
            '[assurance.requirements.semantic]\nlevel="high"\nforce="required-before-closeout"\napplies_to_task_markers=["semantic scope"]\nproof_profile="required"\n'
        )

    startup = tmp_path / "AGENTS.md"
    startup.write_text("Keep current profile scope and evidence separate.", encoding="utf-8")

    def call(value):
        return consume("json", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    packet = call(context)
    startup_read = packet["startup_adapter"]["requests"][0]
    first = packet["verification"]
    assert first["strategy_control"]["selected_profiles"] == []
    scope = first["assurance_request"]
    scope["arguments"]["decisions"]["semantic"] = "applicable"
    chosen = call({**context, "request": scope})["verification"]
    execution = chosen["execution_requests"][0]
    assert len(execution) == 2
    assert not call({**context, "request": execution})["decision_packet"]["ready_actions"]
    action = call({**context, "request": [startup_read, *execution]})["decision_packet"]["primary_action"]
    assert action["source_requests"] == [startup_read]
    original = startup.read_bytes()
    startup.write_bytes(original + b"\nChanged startup source")
    with pytest.raises(AssertionError):
        call({**context, "invocation": action})
    assert not (tmp_path / "marker.txt").exists()
    startup.write_bytes(original)
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "passed"
    assert call({**context, "invocation": action})["value"] == result["value"]
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


def test_current_level_permission_change_and_profile_conflict(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    context = setup(tmp_path)
    source = tmp_path / ".agentic-workspace/config.toml"
    source.write_text(
        source.read_text()
        .replace("agent_may_escalate=true", "agent_may_escalate=false")
        .replace("agent_may_deescalate=false", "agent_may_deescalate=true")
    )

    def call(value):
        return consume("json", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["strategy_request"]
    request["arguments"]["level"] = "high"
    assert "assurance-escalation-not-authorized" in call({**context, "request": request})["verification"]["strategy_control"]["gaps"]
    request["arguments"]["level"] = "low"
    assert call({**context, "request": request})["verification"]["strategy_control"]["effective_level"] == "low"
    request["arguments"]["profile_ids"] = ["missing"]
    invalid = call({**context, "request": request})["verification"]["strategy_control"]
    assert "selected-proof-profile-unavailable:missing" in invalid["gaps"]
    assert invalid["execution_blocked"] is True
    source.write_text(source.read_text().replace('optional_commands=["echo optional"]', 'optional_commands=["echo forbidden"]'))
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "request": request})
    current = call(context)["verification"]["strategy_request"]
    current["arguments"]["profile_ids"] = ["required"]
    invalid = call({**context, "request": current})["verification"]["strategy_control"]
    assert "proof-profile-command-role-conflict:required" in invalid["gaps"]
    assert invalid["execution_blocked"] is True


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_planning_profile_source_gap_and_subject_reentry_are_explicit(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = setup(tmp_path)

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    previous = call(context)["verification"]["strategy_request"]
    ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((Path(__file__).resolve().parents[1] / ref).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{ref.as_posix()}"\nstatus="active"\n'
    )
    initial = call(context)
    request = initial["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    selected = call({**context, "request": request})
    action = selected["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    call({**context, "invocation": action})
    stale = call({**context, "request": previous})["verification"]
    assert "verification-request-stale" in stale["evidence_gaps"]
    current = call(context)["verification"]["strategy_request"]
    result = call({**context, "request": current})["verification"]
    assert "planning-assurance-profile-projection-unavailable" in result["strategy_control"]["gaps"]
    assert result["strategy_control"]["selected_profiles"] == []
