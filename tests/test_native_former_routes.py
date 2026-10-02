"""Former route intent requires explicit task-current adoption, with no writes."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(".agentic-workspace/local/current-task-routes.json")
REGISTRY = Path("tools/skills/REGISTRY.json")


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_declared_custom_registry_is_shared_and_unrelated_state_is_ignored(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    registry = tmp_path / REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"registry_sources": ["custom/routes.json"]}))
    custom = tmp_path / "custom/routes.json"
    custom.parent.mkdir()
    custom.write_text(json.dumps({"skills": [{"semantic_routes": ["custom/first"]}]}))
    context = {"target": str(tmp_path), "task": "Inspect custom routes"}
    first = consume(surface, shared_core_binary, native_cli, context)
    unrelated = tmp_path / ".agentic-workspace/local/scratch/nested/skills/REGISTRY.json"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("not a registry source")
    unchanged = consume(surface, shared_core_binary, native_cli, context)
    assert unchanged["semantic_routes"] == first["semantic_routes"]
    custom.write_text(json.dumps({"skills": [{"semantic_routes": ["custom/second"]}]}))
    changed = consume(surface, shared_core_binary, native_cli, context)
    assert (
        changed["decision_packet"]["semantic_task_routes"]["source_revision"]
        != first["decision_packet"]["semantic_task_routes"]["source_revision"]
    )
    custom.unlink()
    with pytest.raises(AssertionError, match="required route registry unavailable"):
        consume(surface, shared_core_binary, native_cli, context)


def fixture(root: Path) -> tuple[dict, bytes]:
    text = (ROOT / REGISTRY).read_text(encoding="utf-8")
    registry = root / REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(text, encoding="utf-8")
    declared = json.loads(text)
    route = next(
        route if isinstance(route, str) else route["id"] for skill in declared["skills"] for route in skill.get("semantic_routes", [])
    )

    def digest(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

    source = digest(f"{REGISTRY.as_posix()}\0{digest(text)}")
    fact = {
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "posture": "selected",
        "routes": [route],
        "task_identity": {"kind": "current-work", "id": "former-branch-planning-context"},
        "current_work_id": "former-branch-planning-context",
        "source_revision": source,
        "provenance": "agent-selected",
        "authority_effect": "applicability-only",
    }
    path = root / REFERENCE
    path.parent.mkdir(parents=True)
    raw = (json.dumps(fact, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return fact, raw


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_former_selection_requires_exact_current_agent_request(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    fact, raw = fixture(tmp_path)
    context = {"target": str(tmp_path), "task": "Inspect the current route contract", "changed": ["docs/routes.md"]}
    first = consume(surface, shared_core_binary, native_cli, context)
    candidate = first["semantic_routes"]["former_selection"]
    assert candidate["status"] == "candidate"
    assert candidate["current_task_relation"] == "unproven"
    assert candidate["routes"] == fact["routes"]
    assert first["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    assert "local_sources" not in first["configuration"]
    assert "local_source_selection" not in first["memory"]
    for capture in ("capture", "advisory_capture"):
        assert "contribution" not in first["memory"][capture]
        assert first["memory"][capture]["requests"]
    # Full detail includes every declared API schema, including passive skill
    # exposure. Bound that explicit introspection separately from current state
    # and the ordinary compact response; new APIs must not inflate the latter.
    # Resource integration adds seven independently addressable effects and one
    # proposal request (4,418 bytes of owner schemas; 84,489 total in this fixture).
    # Attribute its diagnostic-only allowance rather than relaxing all owners:
    # the pre-resource contract still has the existing 81 KB ceiling. Current
    # state, compact output and former-candidate budgets below remain unchanged.
    contract = first["capability_contract"]
    resource_owners = [owner for owner in contract["owners"] if owner["owner"] == "workspace-resources"]
    assert len(resource_owners) == 1
    assert len(json.dumps(resource_owners[0])) < 4_500
    non_resource_contract = {
        **contract,
        "owners": [owner for owner in contract["owners"] if owner["owner"] != "workspace-resources"],
        "restriction_authorities": [
            authority for authority in contract["restriction_authorities"] if authority["owner"] != "workspace-resources"
        ],
    }
    # Activation adds one introspection-only judgment schema, never an effect
    # or a quiet-work state contribution. Keep its allowance separate so other
    # owners cannot consume this budget and compact/current-state limits stand.
    activation = next(owner for owner in contract["owners"] if owner["owner"] == "activation")
    assert len(activation["requests"]) == 1
    assert not activation.get("operations") and not activation.get("effects")
    activation_bytes = len(json.dumps(activation))
    assert activation_bytes < 900
    assert "activation" not in first
    # Stronger-owner absorption adds only the explicit receiving-proof link.
    # Bound that named schema extension instead of widening unrelated APIs.
    memory = next(owner for owner in contract["owners"] if owner["owner"] == "memory")
    consequence = [
        row["input_schema"]["properties"]["receiving_consequence"]
        for row in memory["requests"]
        if "receiving_consequence" in row["input_schema"].get("properties", {})
    ]
    assert len(consequence) == 1
    assert set(consequence[0]["required"]) == {"claim", "evidence_reference", "proof_subject"}
    consequence_bytes = len(json.dumps({"receiving_consequence": consequence[0]}))
    assert consequence_bytes < 400
    # Local candidates add one bounded request and one effect schema to full
    # introspection. Attribute that exact named delta; candidate rows must not
    # enlarge unrelated ordinary state or compact responses below.
    candidate_requests = [row for row in memory["requests"] if row["kind"] == "memory/consider-observation/v1"]
    candidate_operations = [row for row in memory["operations"] if row["id"] == "memory.update-candidates"]
    assert len(candidate_requests) == 1 and len(candidate_operations) == 1
    candidate_bytes = sum(len(json.dumps(row)) for row in [*candidate_requests, *candidate_operations])
    assert 0 < candidate_bytes < 2_000, candidate_bytes
    # Future advice adds three optional authored properties to its existing
    # capture schema. Bound only that delta, not the whole preexisting publisher.
    advisory = next(row for row in memory["requests"] if row["kind"] == "memory/capture-advisory/v1")
    without_activity_cues = copy.deepcopy(advisory)
    advisory_properties = without_activity_cues["input_schema"]["properties"]["material"]["properties"]
    cues = {key: advisory_properties.pop(key) for key in ("routes_from", "semantic_routes", "origin")}
    assert all(cues[key]["type"] == "array" for key in ("routes_from", "semantic_routes"))
    assert cues["origin"]["type"] == "object"
    activity_cue_bytes = len(json.dumps(advisory)) - len(json.dumps(without_activity_cues))
    assert 0 < activity_cue_bytes < 700, activity_cue_bytes
    # Explicit Planning history discovery keeps unrelated entry quiet. It adds
    # one read-only introspection schema, not another retirement/recovery effect.
    # Bound that named delta separately; preserve the existing four-entry owner
    # allowances and the compact/remaining-state budgets below. Full detail's
    # offered requests are bounded separately from passive state metadata.
    planning = next(owner for owner in contract["owners"] if owner["owner"] == "planning")
    discovery_kind = "planning/discover-terminal-disposition/v1"
    discovery = [row for row in planning["requests"] if row["kind"] == discovery_kind]
    assert len(discovery) == 1
    discovery_bytes = len(json.dumps(discovery[0]))
    assert discovery_bytes < 300
    # Current-work selection/resume also has its own schema. Its optional exact
    # owner reference replaces implicit cursor binding; no new effect is added.
    selection = [row for row in planning["requests"] if row["kind"] == "planning/select-owner/v1"]
    assert len(selection) == 1
    selection_bytes = len(json.dumps(selection[0]))
    assert selection_bytes < 650
    retention_bytes = 0
    for owner_name in ("planning", "memory", "verification"):
        owner = next(row for row in contract["owners"] if row["owner"] == owner_name)
        retention = [
            row
            for row in owner["requests"]
            if ("terminal-disposition" in row["kind"] and row["kind"] != discovery_kind)
            or row["kind"] in {"verification/retire-receipts/v1", "verification/recover-retirement/v1"}
        ]
        retention += [
            row
            for row in owner["operations"]
            if row["id"].endswith((".retire-terminal", ".recover-terminal", ".retire-receipts", ".recover-retirement"))
        ]
        if not retention:
            continue
        size = sum(len(json.dumps(row)) for row in retention)
        assert len(retention) == 4 and size < 2_200, (owner_name, size)
        retention_bytes += size
    # Current-evidence adds three request schemas, two operations and one
    # Verification restriction effect (2,929 serialized bytes). Account for this
    # named introspection delta; keep all earlier and ordinary-response budgets.
    evidence_requests = {
        "verification/assess-current-evidence/v1",
        "verification/retire-current-evidence/v1",
        "verification/recover-current-evidence/v1",
    }
    evidence_operations = {"verification.record-current-evidence", "verification.recover-current-evidence"}
    verification = next(owner for owner in contract["owners"] if owner["owner"] == "verification")
    assert sum(row["kind"] in evidence_requests for row in verification["requests"]) == 3
    assert sum(row["id"] in evidence_operations for row in verification["operations"]) == 2
    without_current_evidence = {
        **non_resource_contract,
        "owners": [
            {
                **owner,
                "requests": [row for row in owner["requests"] if row["kind"] not in evidence_requests],
                "operations": [row for row in owner["operations"] if row["id"] not in evidence_operations],
            }
            if owner["owner"] == "verification"
            else owner
            for owner in non_resource_contract["owners"]
        ],
        "restriction_authorities": [
            {**owner, "affects": [effect for effect in owner["affects"] if effect != "effect:proof-execution"]}
            if owner["owner"] == "verification"
            else owner
            for owner in non_resource_contract["restriction_authorities"]
        ],
    }
    evidence_bytes = len(json.dumps(non_resource_contract)) - len(json.dumps(without_current_evidence))
    assert 0 < evidence_bytes < 3_000, evidence_bytes
    # Optional project plugins add two selected requests and one effect. This
    # allowance belongs only to their full introspection schemas; compact and
    # ordinary-state budgets below remain unchanged.
    configuration = next(owner for owner in contract["owners"] if owner["owner"] == "configuration")
    plugin_requests = [
        row
        for row in configuration["requests"]
        if row["kind"] in {"configuration/read-plugin-exposure/v1", "configuration/plugin-exposure/v1"}
    ]
    plugin_operations = [row for row in configuration["operations"] if row["id"] == "configuration.plugin-exposure"]
    assert len(plugin_requests) == 2 and len(plugin_operations) == 1
    plugin_bytes = sum(len(json.dumps(row)) for row in [*plugin_requests, *plugin_operations])
    assert 0 < plugin_bytes < 1_600, plugin_bytes
    # Source-defined bounded Planning work adds only these three optional
    # introspection properties. Attribute their exact serialized delta while
    # preserving the existing ordinary-state and compact-response ceilings.
    without_assignment_inputs = copy.deepcopy(planning)
    assignment_input_schemas = []

    def remove_assignment_input_schema(value):
        if isinstance(value, dict):
            properties = value.get("properties", {})
            if "assignment_inputs" in properties:
                assignment_input_schemas.append(properties.pop("assignment_inputs"))
            for item in value.values():
                remove_assignment_input_schema(item)
        elif isinstance(value, list):
            for item in value:
                remove_assignment_input_schema(item)

    remove_assignment_input_schema(without_assignment_inputs)
    assert len(assignment_input_schemas) == 3
    assert all(row["type"] == "object" for row in assignment_input_schemas)
    assignment_input_bytes = len(json.dumps(planning)) - len(json.dumps(without_assignment_inputs))
    assert 0 < assignment_input_bytes < 2_300, assignment_input_bytes
    # A Verification investigation reuses an exact native receipt; its one
    # optional request property is introspection only until explicitly supplied.
    analysis_request = next(row for row in verification["requests"] if row["kind"] == "verification/requirements/v1")
    without_analysis_receipt = copy.deepcopy(analysis_request)
    receipt_schema = without_analysis_receipt["input_schema"]["properties"].pop("analysis_receipt_ref")
    assert receipt_schema["type"] == "string" and receipt_schema["pattern"].startswith("^proof://local/")
    analysis_receipt_bytes = len(json.dumps(analysis_request)) - len(json.dumps(without_analysis_receipt))
    assert 0 < analysis_receipt_bytes < 250, analysis_receipt_bytes
    # Manual carriage is six explicit requests and two local effect operations,
    # not a quiet-work queue. Attribute only their full introspection schemas.
    delegation = next(owner for owner in contract["owners"] if owner["owner"] == "delegation")
    manual_kinds = {
        "delegation/retain-manual/v1",
        "delegation/report-manual/v1",
        "delegation/read-manual-result/v1",
        "delegation/settle-manual/v1",
        "delegation/dispose-manual/v1",
        "delegation/retire-manual/v1",
    }
    manual_requests = [row for row in delegation["requests"] if row["kind"] in manual_kinds]
    manual_operation_ids = {"delegation.record-manual", "delegation.retire-manual"}
    manual_operations = [row for row in delegation["operations"] if row["id"] in manual_operation_ids]
    assert len(manual_requests) == 6 and len(manual_operations) == 2
    without_manual_carriage = copy.deepcopy(non_resource_contract)
    without_manual_carriage["owners"] = [
        {
            **owner,
            "requests": [row for row in owner["requests"] if row["kind"] not in manual_kinds],
            "operations": [row for row in owner["operations"] if row["id"] not in manual_operation_ids],
            "effects": [row for row in owner["effects"] if row["id"] != "delegation-carriage"],
        }
        if owner["owner"] == "delegation"
        else owner
        for owner in without_manual_carriage["owners"]
    ]
    without_manual_carriage["restriction_authorities"] = [
        {**owner, "affects": [effect for effect in owner["affects"] if effect != "effect:delegation-carriage"]}
        if owner["owner"] == "delegation"
        else owner
        for owner in without_manual_carriage["restriction_authorities"]
    ]
    manual_bytes = len(json.dumps(non_resource_contract)) - len(json.dumps(without_manual_carriage))
    assert 0 < manual_bytes < 4_500, manual_bytes
    schema_extensions = (
        retention_bytes
        + discovery_bytes
        + selection_bytes
        + activation_bytes
        + consequence_bytes
        + evidence_bytes
        + plugin_bytes
        + assignment_input_bytes
        + analysis_receipt_bytes
        + manual_bytes
        + candidate_bytes
        + activity_cue_bytes
    )
    assert len(json.dumps(non_resource_contract)) - schema_extensions < 81_000
    assert len(json.dumps(contract)) - schema_extensions < 86_000
    assert not any(key.startswith("workspace.resources.") for key in first["decision_packet"]["operation_revisions"])
    terminal_retention = first["planning"]["terminal_retention"]
    offered_discovery = terminal_retention["discovery_request"]
    assert offered_discovery["request_kind"] == discovery_kind
    assert offered_discovery["arguments"] == {}
    assert len(json.dumps(offered_discovery)) < 650
    assert terminal_retention["status"] == "quiet" and terminal_retention["requests"] == []
    assert len(json.dumps({key: value for key, value in terminal_retention.items() if key != "discovery_request"})) < 500
    assert "current_evidence" not in first["verification"]
    assert "plugin_exposure_request" not in first["configuration_write"]
    assert "configuration.plugin-exposure" not in first["decision_packet"]["operation_revisions"]
    evidence_revisions = {
        key: value for key, value in first["decision_packet"]["operation_revisions"].items() if key in evidence_operations
    }
    assert set(evidence_revisions) == evidence_operations
    assert len(json.dumps(evidence_revisions)) < 250
    state = {key: value for key, value in first.items() if key != "capability_contract"}
    for owner_name, field in (("planning", "terminal_retention"), ("memory", "terminal_retention"), ("verification", "retention")):
        assert len(json.dumps(first[owner_name].get(field, {}))) < 1_600
        state[owner_name] = {key: value for key, value in first[owner_name].items() if key != field}
    # Full Planning detail offers one exact selection/resume request instead of
    # treating a remembered cursor as current work. Attribute only that envelope
    # here; keep the 28 KB ceiling for all remaining state and 6 KB for compact.
    selection_requests = state["planning"]["selection_requests"]
    assert len(selection_requests) == 1
    assert selection_requests[0]["request_kind"] == "planning/select-owner/v1"
    assert selection_requests[0]["arguments"] == {}
    assert len(json.dumps(selection_requests)) < 650
    state["planning"] = {key: value for key, value in state["planning"].items() if key != "selection_requests"}
    # Full Memory detail offers only the bounded candidate read envelope until
    # relevant material or a current scoped selection exists. No candidate rows
    # or candidate effect revision may leak into this unrelated entry.
    candidate_detail = state["memory"]["candidates"]
    assert candidate_detail["status"] == "available" and candidate_detail["selected"] == []
    assert len(candidate_detail["requests"]) == 1
    assert candidate_detail["requests"][0]["arguments"] == {"operation": "read"}
    assert len(json.dumps(candidate_detail)) < 900
    assert "memory.update-candidates" not in first["decision_packet"]["operation_revisions"]
    state["memory"] = {key: value for key, value in state["memory"].items() if key != "candidates"}
    # Retention/current-evidence and manual carriage contribute named bounded
    # effect revisions, never unsolicited task state or a manual queue.
    manual_revisions = {key: value for key, value in first["decision_packet"]["operation_revisions"].items() if key in manual_operation_ids}
    assert set(manual_revisions) == manual_operation_ids
    assert len(json.dumps(manual_revisions)) < 250
    state["decision_packet"] = {
        **first["decision_packet"],
        "operation_revisions": {
            key: value
            for key, value in first["decision_packet"]["operation_revisions"].items()
            if key
            not in {
                "planning.retire-terminal",
                "planning.recover-terminal",
                "memory.retire-terminal",
                "memory.recover-terminal",
                "verification.retire-receipts",
                "verification.recover-retirement",
                *evidence_operations,
                *manual_operation_ids,
            }
        },
    }
    assert len(json.dumps(state)) < 28_000, {key: len(json.dumps(value)) for key, value in state.items()}
    compact = consume(surface, shared_core_binary, native_cli, {**context, "projection": "compact"})
    assert len(json.dumps(compact)) < 6_000
    assert "planning_retention" not in compact
    assert len(json.dumps(candidate)) < 8_000
    request = candidate["selection_request"]
    assert request["task_identity"] != fact["task_identity"]
    selected = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert selected["decision_packet"]["semantic_task_routes"]["status"] == "current"
    assert selected["decision_packet"]["semantic_task_routes"]["routes"] == fact["routes"]
    assert (tmp_path / REFERENCE).read_bytes() == raw
    unrelated = consume(surface, shared_core_binary, native_cli, {**context, "task": "An unrelated direct task"})
    assert unrelated["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    stale_task = consume(surface, shared_core_binary, native_cli, {**context, "task": "An unrelated direct task", "request": request})
    assert stale_task["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    # A changed former record cannot keep an earlier current-task adoption valid.
    (tmp_path / REFERENCE).write_bytes(raw + b" ")
    stale_source = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert stale_source["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert (tmp_path / REFERENCE).read_bytes() == raw + b" "
    (tmp_path / REGISTRY).write_text((tmp_path / REGISTRY).read_text() + " ", encoding="utf-8")
    changed_catalogue = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert changed_catalogue["semantic_routes"]["former_selection"]["status"] == "stale"
    assert changed_catalogue["decision_packet"]["semantic_task_routes"]["status"] == "stale"


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
@pytest.mark.parametrize("failure", ["stale", "invalid", "oversized"])
def test_unadoptable_former_source_is_preserved_and_explicit(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, failure: str
) -> None:
    fact, raw = fixture(tmp_path)
    if failure == "stale":
        fact["source_revision"] = "old-vocabulary"
    elif failure == "invalid":
        fact["authority_effect"] = "grant-authority"
    else:
        fact["routes"] = fact["routes"] * 17
    raw = json.dumps(fact).encode()
    (tmp_path / REFERENCE).write_bytes(raw)
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Read an unrelated document"})
    diagnostic = result["semantic_routes"]["former_selection"]
    assert diagnostic["status"] == ("stale" if failure == "stale" else "unresolved")
    assert (
        diagnostic["reason"]
        == {
            "stale": "former-route-vocabulary-revision-changed",
            "invalid": "former-route-source-invalid-or-unsupported",
            "oversized": "former-route-selection-exceeds-candidate-bound",
        }[failure]
    )
    assert "selection_request" not in diagnostic
    assert result["decision_packet"]["semantic_task_routes"]["posture"] == "unresolved"
    assert result["decision_packet"]["status"] == "direct"
    assert (tmp_path / REFERENCE).read_bytes() == raw


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_no_former_source_direct_work_has_no_candidate_or_state(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Read the short document"})
    assert "former_selection" not in (result["semantic_routes"] or {})
    assert result["decision_packet"]["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_new_unreadable_former_source_stales_an_earlier_selection(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    fixture(tmp_path)
    (tmp_path / REFERENCE).unlink()
    context = {"target": str(tmp_path), "task": "Inspect the current route contract"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    request = next(r for r in initial["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "none", "routes": []}
    (tmp_path / REFERENCE).mkdir()
    result = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert result["semantic_routes"]["former_selection"]["reason"] == "former-route-source-unreadable-or-linked"
    assert result["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert (tmp_path / REFERENCE).is_dir()


def test_negative_route_conclusion_reuses_until_opaque_discovery_changes(tmp_path, shared_core_binary, native_cli):
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"semantic_routes": ["example/optional"]}]}))
    context = {"target": str(tmp_path), "task": "No specialized procedure is needed"}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    request = next(r for r in call()["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "none", "routes": []}
    first = call(request=request)
    fact = first["decision_packet"]["semantic_task_routes"]
    assert fact["status"] == "current" and fact["posture"] == "none"
    assert call(request=request)["decision_packet"]["semantic_task_routes"] == fact
    (tmp_path / "unrelated.txt").write_text("This does not change the eligible route set")
    assert call(request=request)["decision_packet"]["semantic_task_routes"] == fact
    added = tmp_path / ".agentic-workspace/skills/REGISTRY.json"
    added.parent.mkdir(parents=True)
    added.write_text(json.dumps({"skills": [{"semantic_routes": ["new/eligible"]}]}))
    stale = call(request=request)
    assert stale["decision_packet"]["semantic_task_routes"]["status"] == "stale"
    assert stale["decision_packet"]["semantic_task_routes"]["source_revision"] != fact["source_revision"]
    assert not (tmp_path / ".agentic-workspace/local").exists()
