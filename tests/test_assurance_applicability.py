"""Source-current assurance applicability has one owner across public consumers."""

# ruff: noqa: F811
import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume, native_cli  # noqa: F401


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_assurance_scope_requires_bound_judgment(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    quiet = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Read a document", "changed": []})
    assert quiet["verification"]["assurance_request"] is None
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version=1\n[assurance.requirements.review]\nlevel="high"\nforce="blocking"\napplies_to_paths=["src/**"]\napplies_to_task_markers=["proof"]\nblocking_claims=["claim-work-complete"]\nrequired_evidence=["domain-review"]\n',
        encoding="utf-8",
    )
    context = {"target": str(tmp_path), "task": "Read a description of proof terminology", "changed": ["docs/terms.md"]}
    result = consume(surface, shared_core_binary, native_cli, context)
    row = result["verification"]["assurance_applicability"]["requirements"][0]
    assert row["status"] == "unresolved"
    # Final projection exposes one composed authority and one requirement body;
    # the ordinary current request below still round-trips across all consumers.
    assert all("contribution" not in owner for owner in result.values() if isinstance(owner, dict))
    assert row["source_requirement"]["required_evidence"] == ["domain-review"]
    gap = result["verification"]["assurance_owner_gaps"][0]
    assert gap["requirement_id"] == row["id"]
    assert gap["status"] == "owner-evidence-not-admitted"
    assert "source_requirement" not in gap
    assert result["decision_packet"]["blockers"] == result["decision_packet"]["pending_consequences"]["blockers"]
    owner = next(owner for owner in result["capability_contract"]["owners"] if owner["owner"] == "verification")
    assert any(request["kind"] == "verification/assurance-applicability/v1" and request["input_schema"] for request in owner["requests"])
    assert not row["applies_because"]
    assert not any(r["field"] == "assurance.requirements" for r in result["configuration"]["residuals"])
    assert any(b["affects"] == ["claim:claim-work-complete"] for b in result["decision_packet"]["blockers"])
    request = result["verification"]["assurance_request"]
    request["arguments"]["decisions"] = {"review": "not-applicable"}
    resolved = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert resolved["verification"]["assurance_applicability"]["requirements"][0]["status"] == "not-applicable"
    assert not any(b["code"].startswith("assurance:") for b in resolved["decision_packet"]["blockers"])
    claim = result["verification"]["requests"][0]
    composed = consume(surface, shared_core_binary, native_cli, {**context, "request": [claim, request]})
    assert composed["verification"]["assurance_applicability"]["requirements"][0]["status"] == "not-applicable"
    assert "current-task-claim-judgment-not-admitted" in composed["verification"]["evidence_gaps"]
    assert not any(b["code"].startswith("assurance:") for b in composed["decision_packet"]["blockers"])
    authentication = result["verification"]["authentication_request"]
    authentication["arguments"]["host_result_ref"] = "independent-review-host-result:missing-fixture"
    all_requests = consume(surface, shared_core_binary, native_cli, {**context, "request": [authentication, claim, request]})
    assert all_requests["verification"]["host_authentication"] is not None
    assert "current-task-claim-judgment-not-admitted" in all_requests["verification"]["evidence_gaps"]
    assert all_requests["verification"]["assurance_applicability"]["requirements"][0]["status"] == "not-applicable"
    changed = consume(surface, shared_core_binary, native_cli, {**context, "task": "Different work", "request": [claim, request]})
    assert changed["verification"]["assurance_applicability"]["requirements"][0]["status"] == "unresolved"
    assert "verification-request-stale" in changed["verification"]["evidence_gaps"]
    with pytest.raises(AssertionError, match="at most one"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": [request, request]})
    stale = consume(surface, shared_core_binary, native_cli, {**context, "task": "Different work", "request": request})
    assert stale["verification"]["assurance_applicability"]["requirements"][0]["status"] == "unresolved"
    exact = consume(surface, shared_core_binary, native_cli, {**context, "changed": ["src/a.rs"], "request": request})
    assert exact["verification"]["assurance_applicability"]["requirements"][0]["status"] == "applicable"
    assert any(b["code"] == "assurance:review:applicable" for b in exact["decision_packet"]["blockers"])
    forged = json.loads(json.dumps(request))
    forged["arguments"]["decisions"]["unknown"] = "not-applicable"
    with pytest.raises(AssertionError, match="unknown requirement"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": forged})
    source.write_text(source.read_text() + "# current source changes\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="stale for the current capability contract revision"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    fresh = consume(surface, shared_core_binary, native_cli, context)
    assert fresh["verification"]["assurance_applicability"]["requirements"][0]["status"] == "unresolved"
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_python_consumers_share_exact_applicability_without_marker_match() -> None:
    from agentic_workspace import workspace_runtime_core as runtime

    requirement = {"id": "review", "applies_to_task_markers": ["proof"], "applies_to_paths": ["src/**"]}
    for task in ("proof", "unrelated words"):
        assert (
            runtime._assurance_requirement_match(requirement=requirement, changed_paths=[], task_text=task, planning_facts={})[0] is False
        )
    assert (
        runtime._assurance_requirement_match(requirement=requirement, changed_paths=["src/a.rs"], task_text="", planning_facts={})[0]
        is True
    )


def test_real_source_requirement_keeps_claim_boundary_when_scope_is_unknown(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    from agentic_workspace import decision
    from agentic_workspace import workspace_runtime_core as runtime
    from agentic_workspace.config import load_workspace_config

    root = Path(__file__).resolve().parents[1]
    text = (root / ".agentic-workspace/verification/manifest.toml").read_text(encoding="utf-8")
    section = text.split("[assurance.requirements.test_evidence_change_decision]", 1)[1].split(
        "[assurance.requirements.closeout_intent_satisfaction]", 1
    )[0]
    path = tmp_path / ".agentic-workspace/verification/manifest.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[assurance.requirements.test_evidence_change_decision]' + section,
        encoding="utf-8",
    )
    report = runtime._assurance_requirements_report_payload(
        config=load_workspace_config(target_root=tmp_path),
        target_root=tmp_path,
        task_text="Mention an ordinary test in prose",
        changed_paths=["docs/intro.md"],
    )
    assert report["active"] == []
    status = report["evidence_status"][0]
    assert status["state"] == "unknown"
    assert status["blocking_claims"] == ["claim-work-complete", "close-parent-lane"]
    query = status["next_action"]["public_query"]
    current = decision.start({**query["input"], "projection": "full"})
    request = current["verification"]["assurance_request"]
    request["arguments"]["decisions"] = {"test_evidence_change_decision": "not-applicable"}
    assert (
        decision.start({**query["input"], "request": request, "projection": "full"})["verification"]["assurance_applicability"][
            "requirements"
        ][0]["status"]
        == "not-applicable"
    )
    actual = consume(
        "native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Small change", "changed": ["tests/example.py"]}
    )
    assert actual["verification"]["assurance_applicability"]["requirements"][0]["status"] == "applicable"
    assert actual["verification"]["assurance_owner_gaps"][0]["status"] == "owner-evidence-not-admitted"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unreconciled_planning_owner_is_not_known_absence(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    root = Path(__file__).resolve().parents[1]
    plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / plan_ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((root / plan_ref).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[todo]\nactive_items = [{{id="delegation-lane-sweep",status="in-progress",surface="{plan_ref.as_posix()}"}}]\nqueued_items=[]\n',
        encoding="utf-8",
    )
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version=1\n[assurance.requirements.risk_review]\nlevel="high"\nforce="blocking"\napplies_to_risk_refs=["risk:material"]\n',
        encoding="utf-8",
    )
    context = {"target": str(tmp_path), "task": "Continue the selected work", "changed": []}
    result = consume(surface, shared_core_binary, native_cli, context)
    assert result["planning"]["status"] == "unresolved"
    assert result["verification"]["assurance_applicability"]["requirements"][0]["status"] == "unresolved"
    request = result["verification"]["assurance_request"]
    request["arguments"]["decisions"] = {"risk_review": "not-applicable"}
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    row = result["verification"]["assurance_applicability"]["requirements"][0]
    assert row["status"] == "unresolved"
    assert "current agent applicability judgment" not in row["applies_because"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_planning_frontier_preserves_verification_request_lifetime(tmp_path, shared_core_binary, native_cli, surface):
    from tests.test_native_planning_create import material

    context = {"target": str(tmp_path), "task": "Continue one exact bounded outcome"}

    def call(extra=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **(extra or {})})

    request = call()["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    created = call({"invocation": call({"request": request})["decision_packet"]["primary_action"]})
    context = created["value"]["selection_context"]
    call({"invocation": call({"request": created["value"]["selection_request"]})["decision_packet"]["primary_action"]})
    before = call()
    claim = before["verification"]["requests"][0]
    update = before["planning"]["update_requests"][0]
    update["arguments"]["material"] = {**material(), "lifecycle": "live", "phase": "validation"}
    call({"invocation": call({"request": update})["decision_packet"]["primary_action"]})
    fresh = call()
    call({"invocation": call({"request": fresh["planning"]["requests"][0]})["decision_packet"]["primary_action"]})
    current = call({"request": claim})
    assert current["verification"]["source"] == before["verification"]["source"]
    assert "verification-request-stale" not in current["verification"]["evidence_gaps"]
    assert "current-task-claim-judgment-not-admitted" in current["verification"]["evidence_gaps"]
    assert current["decision_packet"]["status"] != "terminal"
    update = call()["planning"]["update_requests"][0]
    update["arguments"]["material"] = {
        **material(),
        "lifecycle": "live",
        "phase": "validation",
        "scope": {"allowed": "Materially different work"},
    }
    call({"invocation": call({"request": update})["decision_packet"]["primary_action"]})
    fresh = call()
    call({"invocation": call({"request": fresh["planning"]["requests"][0]})["decision_packet"]["primary_action"]})
    changed = call({"request": claim})
    assert "verification-request-stale" in changed["verification"]["evidence_gaps"]
