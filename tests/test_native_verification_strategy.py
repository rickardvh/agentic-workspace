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
    source = root / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    (root / ".agentic-workspace/config.toml").write_text(
        '[assurance]\ndefault_level="medium"\nagent_may_escalate=true\nagent_may_deescalate=false\n'
    )
    command = "Add-Content -Path marker.txt -Value executed" if os.name == "nt" else "echo executed >> marker.txt"
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[assurance.proof_profiles.required]\nrequired_commands=['
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
def test_exact_native_command_evidence_discharges_only_its_profile_obligation(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = setup(tmp_path, binding=True)
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    command = "Add-Content -Path marker.txt -Value executed" if os.name == "nt" else "echo executed >> marker.txt"
    text = source.read_text().replace(
        f"required_commands=[{json.dumps(command)}]", f'required_commands=[{json.dumps(command)},"echo second"]'
    )
    source.write_text(
        text
        + '[assurance.domain_proof_lanes.foreign]\npurpose="Different exact route"\napplies_to_paths=["a.txt"]\ncommands=['
        + json.dumps(command)
        + "]\n"
    )

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    def run(route, command, *, manual=False):
        current = call(context)
        requests = current["verification"]["record_requests" if manual else "execution_requests"]
        request = next(r for r in requests if r["arguments"]["route_id"] == route and r["arguments"]["command"] == command)
        if manual:
            request["arguments"]["result"] = "passed"
        action = call({**context, "request": request})["decision_packet"]["primary_action"]
        return call({**context, "invocation": action})["value"]["publication"]["reference"]

    def claim(refs, task=None):
        current = {**context, "task": task or context["task"]}
        request = call(current)["verification"]["requests"][0]
        request["arguments"]["evidence_refs"] = refs
        return call({**current, "request": request})

    foreign = run("domain:foreign", command)
    foreign_view = claim([foreign])
    obligation = foreign_view["verification"]["strategy_control"]["obligations"][0]
    assert obligation["missing_commands"] == [command, "echo second"]
    first = run("profile:required", command)
    manual = run("profile:required", "echo second", manual=True)
    partial = claim([foreign, first, manual])
    assert partial["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == ["echo second"]
    second = run("profile:required", "echo second")
    refs = [first, second]
    satisfied = claim(refs)
    obligation = satisfied["verification"]["strategy_control"]["obligations"][0]
    assert obligation["status"] == "current-command-evidence-satisfied"
    assert obligation["missing_commands"] == [] and set(obligation["evidence_refs"]) == set(refs)
    blockers = {b["code"] for b in satisfied["decision_packet"]["blockers"]}
    assert "profile-proof-required:required" not in blockers
    assert "assurance:current:applicable" in blockers and "verification-evidence-unresolved" in blockers
    assert satisfied["decision_packet"]["claim_boundary"]["allowed"] == []
    assert satisfied["decision_packet"]["status"] != "terminal"
    changed_task = claim(refs, "A different requested outcome")
    assert changed_task["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == []
    assert changed_task["decision_packet"]["claim_boundary"]["allowed"] == []
    assert all(item["task_judgment"]["current_judgment_count"] == 0 for item in changed_task["verification"]["evidence"])
    (tmp_path / "a.txt").write_text("material source changed")
    assert claim(refs)["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == [command, "echo second"]
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed", "executed"]


def test_failed_native_command_cannot_discharge_profile(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    context = setup(tmp_path, binding=True)
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    text = source.read_text()
    begin = text.index("required_commands=")
    end = text.index("\n", begin)
    source.write_text(text[:begin] + 'required_commands=["exit 7"]' + text[end:])

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "failed"
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    assert call({**context, "request": claim})["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == ["exit 7"]


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
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    with source.open("a") as stream:
        stream.write(
            '[assurance.domain_proof_lanes.denied]\npurpose="Declared candidate"\napplies_to_paths=["a.txt"]\ncommands=["echo forbidden"]\n'
        )
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        manifest.read_text()
        + '[protocols.denied]\napplies_to_paths=["a.txt"]\n[proof_routes.manifest_denied]\nprotocol_refs=["denied"]\ncommands=["echo forbidden"]\n'
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
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    with source.open("a") as stream:
        stream.write(
            '[assurance.requirements.semantic]\nlevel="high"\nforce="required-before-closeout"\napplies_to_task_markers=["semantic scope"]\nproof_profile="required"\n'
        )

    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text() + '[workspace]\nagent_instructions_file="AGENTS.md"\n')
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
    delivered = call({**context, "request": execution})
    assert delivered["startup_adapter"]["status"] == "source-context-delivered"
    assert delivered["startup_adapter"]["response"]["text"] == startup.read_text(encoding="utf-8")
    action = delivered["decision_packet"]["primary_action"]
    assert call({**context, "request": [startup_read, *execution]})["decision_packet"]["primary_action"] == action
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
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(
        config.read_text()
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
    with pytest.raises(AssertionError, match="contradictory command roles"):
        call({**context, "request": request})
    with pytest.raises(AssertionError, match="contradictory command roles"):
        call(context)


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


def test_reader_loads_current_verification_manifest_without_shared_config(tmp_path):
    from agentic_workspace.config import load_workspace_config

    setup(tmp_path, binding=True)
    (tmp_path / ".agentic-workspace/config.toml").unlink()
    result = load_workspace_config(target_root=tmp_path)
    assert not result.exists
    assert "required" in {profile.id for profile in result.assurance.proof_profiles}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_subsystem_profile_uses_current_ownership_without_granting_review(tmp_path, shared_core_binary, native_cli, surface):
    context = setup(tmp_path)
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(exist_ok=True)
    declaration = (
        manifest.read_text() + '[assurance.subsystem_profiles.runtime]\nassurance_level="high"\nforce="required-before-closeout"\n'
        'scope_refs=["ownership.subsystems.runtime"]\nproof_profile="required"\n'
        'required_evidence=["runtime-check","independent-review"]\nreview_owner="maintainer"\n'
        'blocked_without_evidence=["claim-work-complete"]\n'
    )
    manifest.write_text(declaration)
    ownership = tmp_path / ".agentic-workspace/OWNERSHIP.toml"
    scope = '[[subsystems]]\nid="runtime"\npaths=["a.txt"]\n'

    def call(**updates):
        return consume(surface, shared_core_binary, native_cli, {**context, **updates}, host_path=os.environ["PATH"])

    with pytest.raises(AssertionError, match="Ownership"):
        call()
    ownership.write_text(scope)
    current = call()["verification"]
    assert current["strategy_control"]["effective_level"] == "high"
    assert current["strategy_request"]["arguments"]["level"] == "high"
    row = current["assurance_applicability"]["requirements"][0]
    assert row["id"] == "subsystem:runtime" and row["status"] == "applicable"
    assert row["source_requirement"]["review_owner"] == "maintainer"
    assert row["source_requirement"]["required_evidence"] == ["runtime-check", "independent-review"]
    assert current["assurance_owner_gaps"], "scope and profile selection cannot admit review"
    request = current["execution_requests"][0]
    action = call(request=request)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "proof.report"
    unrelated = call(changed=["unrelated.txt"])["verification"]
    assert unrelated["assurance_applicability"]["requirements"][0]["status"] == "not-applicable"
    assert unrelated["strategy_control"]["effective_level"] == "medium"
    assert unrelated["strategy_control"]["selected_profiles"] == []
    published = call(invocation=action)["value"]["publication"]["reference"]
    claim = call()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [published]
    checked = call(request=claim)
    assert checked["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
    assert checked["decision_packet"]["claim_boundary"]["allowed"] == []
    ownership.write_text(scope + "\n")
    with pytest.raises(AssertionError, match="stale|changed"):
        call(invocation=action)
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]
    claim = call()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [published]
    rechecked = call(request=claim)
    assert rechecked["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
    assert rechecked["decision_packet"]["claim_boundary"]["allowed"] == []
    ownership.write_text(scope + scope)
    with pytest.raises(AssertionError, match="one current Ownership"):
        call()
    ownership.write_text(scope)
    manifest.write_text(declaration.replace("ownership.subsystems.runtime", "unknown-scope"))
    with pytest.raises(AssertionError, match="scope requires owner"):
        call()
    manifest.write_text(declaration + 'level="low"\n')
    with pytest.raises(AssertionError, match="invalid Verification declaration|unsupported"):
        call()
    manifest.write_text('schema_version="agentic-workspace/verification-manifest/v1"\n')
    ownership.write_text("Malformed unrelated ownership source")
    assert call()["verification"]["strategy_control"]["effective_level"] == "medium"
    assert (tmp_path / "marker.txt").read_text().splitlines() == ["executed"]


# These owner semantics have no adapter-specific encoding. Exercise the core JSON
# ingress once; existing cross-surface conformance/transfer cases own adapter parity.
def test_strict_closeout_requires_current_judgment_without_matching_protocol(tmp_path, shared_core_binary, native_cli):
    setup(tmp_path)
    (tmp_path / ".agentic-workspace/verification/manifest.toml").unlink()
    source = tmp_path / ".agentic-workspace/config.toml"
    context = {"target": str(tmp_path), "task": "Check resulting work", "changed": ["a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    source.write_text("[assurance]\nstrict_closeout=false\n")
    assert call()["verification"]["judgment_request"] is None
    source.write_text("[assurance]\nstrict_closeout=true\n")
    before = source.read_bytes()
    current = call()
    assert current["verification"]["judgment_request"] is not None
    assert any(b["code"] == "strict-closeout-judgment-required" for b in current["decision_packet"]["blockers"])
    request = current["verification"]["claim_review"]["request"]
    request["arguments"] = {"disposition": "satisfied", "reason": "Checked this exact fixture outcome.", "evidence_refs": []}
    proposed = call(request=request)
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    assert any(b["code"] == "strict-closeout-judgment-required" for b in proposed["decision_packet"]["blockers"])
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "current"
    assert not any(b["code"] == "strict-closeout-judgment-required" for b in reviewed["decision_packet"]["blockers"])
    assert source.read_bytes() == before
    (tmp_path / "a.txt").write_text("Different work")
    with pytest.raises(AssertionError, match="stale"):
        call(request=answer)
