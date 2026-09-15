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
    for ref in [*refs, plan_ref, ".agentic-workspace/verification/manifest.toml"]:
        path = target / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / ref).read_bytes())
    # Stage a current installation fixture from the actual shipped manifest.
    # The repository's historical v0.51 installation roster is not a current
    # source-checkout installation receipt; preserve that negative separately.
    provenance_path = target / ".agentic-workspace/payload-provenance.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["payload_files"] = manifest["payload_files"]
    provenance_path.write_text(json.dumps(provenance))
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
    assert not any(r["field"].startswith("workflow_obligations.") for r in first["configuration"]["residuals"])
    assert first["configuration"]["improvement_latitude"] == "proactive"
    assert not any(r["field"] == "assurance.strict_closeout" for r in first["configuration"]["residuals"])
    closeout = next(b for b in restrictions if b["code"] == "strict-closeout-judgment-required")
    assert "claim:complete" in closeout["affects"]
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
    config.write_text(original + '\n[cli_compatibility]\nenforcement="blocking"\n', encoding="utf-8")
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


def test_historical_installation_roster_cannot_claim_new_payload(tmp_path, shared_core_binary, native_cli):
    former_repository(tmp_path)
    provenance = tmp_path / ".agentic-workspace/payload-provenance.json"
    historical = json.loads(provenance.read_text())
    historical["payload_files"].remove(".agentic-workspace/skills/workspace-instruction-correction/SKILL.md")
    provenance.write_text(json.dumps(historical))
    current = consume("json", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect historical payload"})
    assert current["configuration"]["payload"]["status"] == "unresolved"
    assert any(gap["path"].endswith("workspace-instruction-correction/SKILL.md") for gap in current["configuration"]["payload"]["gaps"])


def test_former_local_sources_are_distinguished_without_default_fallback(tmp_path, shared_core_binary, native_cli):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        'schema_version=1\n[local_memory]\nenabled=false\ntarget_guidance_enabled=false\npath="private-notes"\nuser_guidance_root="missing-guidance"\ntarget_guidance_overlay_path="empty-overlay"\ncorrection_events_path="private-notes/note/child"\n'
    )
    private = tmp_path / "private-notes/note"
    private.parent.mkdir()
    private.write_text("PRIVATE-SENTINEL-KEEP")
    (tmp_path / "empty-overlay").write_text("")
    before = source.read_bytes(), private.read_bytes()
    context = {"target": str(tmp_path), "task": "Inspect local source availability", "changed": []}
    result = consume("json", shared_core_binary, native_cli, context)
    selection = result["configuration"]["local_sources"]
    states = {row["field"]: row["status"] for row in selection["observations"]}
    assert states["local_memory.path"] == "present-material-unclassified"
    assert states["local_memory.user_guidance_root"] == "explicit-source-missing"
    assert states["local_memory.target_guidance_overlay_path"] == "present-empty-file"
    assert states["local_memory.correction_events_path"] == "source-inaccessible-or-unconfined"
    assert states["local_memory.enabled"] == "unsupported-explicit-choice"
    assert selection["status"] == "unsupported-preserved" and not selection["fallback_used"]
    assert result["memory"]["local_source_selection"] == selection
    assert "PRIVATE-SENTINEL-KEEP" not in str(result)
    assert (source.read_bytes(), private.read_bytes()) == before
    assert not (tmp_path / ".agentic-workspace/memory").exists()
    assert result["decision_packet"]["claim_boundary"]["allowed"] == []
    # An explicit source-owner retirement changes no data and creates no default.
    source.write_text("schema_version=2\n")
    for _ in range(2):
        fresh = consume("json", shared_core_binary, native_cli, context)
        assert "local_sources" not in fresh["configuration"]
        assert "local_source_selection" not in fresh["memory"]
        assert private.read_bytes() == before[1]
        assert not (tmp_path / ".agentic-workspace/memory").exists()
