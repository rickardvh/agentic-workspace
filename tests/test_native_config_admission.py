"""Native configuration preserves real source force without a Python oracle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def former_repository(target: Path) -> tuple[Path, Path]:
    manifest = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())
    refs = [*manifest["payload_files"], ".agentic-workspace/payload-provenance.json", ".agentic-workspace/config.toml", "AGENTS.md"]
    plan_ref = ".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json"
    for ref in [*refs, plan_ref]:
        path = target / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / ref).read_bytes())
    selector = target / ".agentic-workspace/local/planning/owner-selection.json"
    selector.parent.mkdir(parents=True)
    selector.write_text(
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "v1-contraction-2983-2990", "ref": plan_ref},
                "reason": "Retain the established former owner",
            }
        )
    )
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version=1\n[runtime]\nsupports_internal_delegation=true\nstrong_planner_available=false\n"
        "[safety]\nsafe_to_auto_run_commands=false\nrequires_human_verification_on_pr=true\n"
    )
    return selector, target / plan_ref


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_configuration_admits_only_the_exact_planning_effect(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    selector, plan = former_repository(tmp_path)
    context = {"target": str(tmp_path), "task": "Continue the real owner through its explicitly authorized selector transfer"}

    def call(**kwargs):
        return consume(surface, shared_core_binary, native_cli, {**context, **kwargs})

    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    first = call()
    assert first["configuration"]["payload"]["status"] == "satisfied"
    assert not any("task" in b["affects"] for b in first["decision_packet"]["blockers"])
    restrictions = first["decision_packet"]["blockers"]
    assert any(b["code"] == "local-command-safety-ceiling" for b in restrictions)
    assert any(b["code"] == "local-human-review-required" for b in restrictions)
    closeout = next(r for r in first["configuration"]["residuals"] if r["field"] == "workflow_obligations.dogfooding_lane_closeout")
    assert "claim:complete" in closeout["affects"] and "task" not in closeout["affects"]
    initiative = next(r for r in first["configuration"]["residuals"] if r["field"] == "workspace.improvement_latitude")
    assert initiative["value"] == "proactive" and initiative["affects"] == ["effect:initiative"]
    assert {p: p.read_bytes() for p in before} == before, "discovery never transfers source custody"
    transfer = first["planning"]["selector_transfer"]["request"]
    transfer["arguments"]["answer"] = "authorize-selector-transfer"
    selected = call(request=[first["startup_adapter"]["requests"][0], transfer])
    action = selected["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    payload = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    payload.write_bytes(before[payload] + b"\nchanged after admission\n")
    stale = call()
    assert stale["configuration"]["payload"]["status"] == "unresolved"
    assert any(b["code"] == "native-payload-target-unproven" and b["affects"] == ["task"] for b in stale["decision_packet"]["blockers"])
    assert stale["configuration"]["revision"] != first["configuration"]["revision"]
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert selector.read_bytes() == before[selector]
    assert plan.read_bytes() == before[plan]
    payload.write_bytes(before[payload])
    result = call(invocation=action)
    assert result["custody"]["committed"]
    assert plan.read_bytes() == before[plan]
    current = call()
    assert current["planning"]["current_owner"]["current"] is True
    assert current["decision_packet"]["status"] != "terminal"
    assert {p: p.read_bytes() for p in before if p != selector} == {p: b for p, b in before.items() if p != selector}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_config_force_and_payload_labels_cannot_waive_requirements(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    former_repository(tmp_path)
    context = {"target": str(tmp_path), "task": "Inspect current configuration"}

    def call():
        return consume(surface, shared_core_binary, native_cli, context)

    config = tmp_path / ".agentic-workspace/config.toml"
    original = config.read_text()
    config.write_text(original.replace('enforcement = "advisory"', 'enforcement = "blocking"'))
    blocking = call()
    assert any(
        b["code"].startswith("native-config-owner:") and "cli_compatibility" in b["code"] and "task" in b["affects"]
        for b in blocking["decision_packet"]["blockers"]
    )
    config.write_text(original)
    provenance = tmp_path / ".agentic-workspace/payload-provenance.json"
    recorded = provenance.read_bytes()
    forged = json.loads(recorded)
    forged["release_identity"]["version"] = "99.0.0"
    provenance.write_text(json.dumps(forged))
    assert call()["configuration"]["payload"]["status"] == "unresolved"
    provenance.write_bytes(recorded)
    missing = tmp_path / ".agentic-workspace/WORKFLOW.md"
    missing.unlink()
    assert call()["configuration"]["payload"]["status"] == "unresolved", "matching provenance labels cannot prove absent payload"
    config.write_text(original.replace('policy = "required-before-work"', 'policy = "required-before-claim"'))
    claim = call()
    blocker = next(b for b in claim["decision_packet"]["blockers"] if b["code"] == "native-payload-target-unproven")
    assert "task" not in blocker["affects"] and "claim:complete" in blocker["affects"]
    config.write_text(original.replace('policy = "required-before-work"', 'policy = "advisory"'))
    advisory = call()
    assert advisory["configuration"]["payload"]["status"] == "unresolved"
    assert not any(b["code"] == "native-payload-target-unproven" for b in advisory["decision_packet"]["blockers"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unconfigured_native_payload_has_no_read_or_artifact_tax(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    before = list(tmp_path.iterdir())
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect a direct task"})
    assert result["configuration"]["payload"] == {"status": "not-configured", "blockers": []}
    assert result["decision_packet"]["status"] == "direct"
    assert list(tmp_path.iterdir()) == before
