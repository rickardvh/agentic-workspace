from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.contract_tooling import authority_markers_manifest, cli_commands_manifest
from agentic_workspace.result_adapter import adapt_action, adapt_module_result

_ORIGINAL_PATH_WRITE_TEXT = Path.write_text


def _path_write_text_with_parents(self: Path, data: str, *args, **kwargs):
    self.parent.mkdir(parents=True, exist_ok=True)
    return _ORIGINAL_PATH_WRITE_TEXT(self, data, *args, **kwargs)


Path.write_text = _path_write_text_with_parents


@dataclass
class FakeAction:
    kind: str
    path: Path
    detail: str


@dataclass
class FakeResult:
    target_root: Path
    message: str
    dry_run: bool
    actions: list[FakeAction] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class SlottedAction:
    kind: str
    path: Path
    detail: str


class DictAction:
    def __init__(self, path: Path) -> None:
        self.path = path

    def to_dict(self, target_root: Path) -> dict[str, object]:
        return {
            "kind": "converted",
            "path": self.path.relative_to(target_root),
            "detail": "used to_dict",
        }


def _assert_invoked_cli_identity(payload: dict[str, object], *, target_relation: str) -> dict[str, object]:
    identity = payload["invoked_cli_identity"]
    assert isinstance(identity, dict)
    assert identity["kind"] == "agentic-workspace/invoked-cli-identity/v1"
    assert identity["package"] == "agentic-workspace"
    assert identity["version"] == cli.__version__
    assert identity["source_class"] in {"source-checkout", "installed-package", "unknown"}
    if "confidence" in identity:
        assert identity["confidence"] in {"high", "medium", "low"}
    assert str(identity["module_path"]).endswith("src/agentic_workspace/cli.py")
    if "python_executable" in identity:
        assert identity["python_executable"]
    assert identity["target_relation"] == target_relation
    assert identity["compatibility"] == "not-evaluated"
    return identity


def _assert_cli_compatibility(payload: dict[str, object], *, status: str) -> dict[str, object]:
    compatibility = payload["cli_compatibility"]
    assert isinstance(compatibility, dict)
    assert compatibility["kind"] == "agentic-workspace/cli-compatibility/v1"
    assert compatibility["status"] == status
    assert compatibility["enforcement"] in {"off", "advisory", "blocking"}
    assert "failed_checks" in compatibility
    return compatibility


def _assert_cli_compatibility_schema(payload: dict[str, object], *, schema_name: str) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.evolve(schema=schema["$defs"]["cli_compatibility"]).iter_errors(payload["cli_compatibility"]),
        key=lambda error: list(error.path),
    )
    assert [error.message for error in errors] == []


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    repo_root = Path("./repo")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(repo_root, []))

    assert cli.main(["modules", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload["module_profiles"]] == [
        "routing-only",
        "planning",
        "memory",
        "full",
    ]
    full_profile = next(entry for entry in payload["module_profiles"] if entry["id"] == "full")
    assert full_profile["profile_kind"] == "installer-preset"
    assert full_profile["selected_modules"] == ["planning", "memory"]
    assert full_profile["selection_rule"] == "expands to every bundled module marked include_in_full_preset"
    assert payload["feature_tiers_compatibility"]["canonical_field"] == "module_profiles"
    assert [entry["id"] for entry in payload["feature_tiers"]] == [
        "routing-only",
        "planning",
        "memory",
        "full",
    ]
    footprint = payload["package_footprint"]
    assert footprint["decision"] == "bundle-first-party-modules-for-now"
    assert "unconditionally" in footprint["python_package_dependency_model"]
    assert "not Python package dependencies" in footprint["repo_footprint_rule"]
    assert footprint["bounded_by"] == ["#490", "#510"]
    component_model = payload["component_model"]
    assert component_model["schema_version"] == "agentic-workspace/module-components/v1"
    assert component_model["runtime_dependency"] == "none"
    assert {entry["id"] for entry in component_model["component_classes"]} == {
        "resource",
        "tool",
        "prompt",
        "schema",
        "root",
    }
    assert "FastMCP or MCP runtime dependencies" in " ".join(component_model["adapter_boundary"]["adapter_must_not"])
    workspace_components = payload["workspace_components"]
    assert workspace_components["scope"]["audience"] == "shipped-host-repo"
    assert "source-checkout maintainer tooling" in workspace_components["scope"]["excludes"]
    root_components = workspace_components["components"]
    assert {resource["uri"] for resource in root_components["resources"]} >= {
        "workspace://config",
        "workspace://summary",
        "workspace://report",
        "workspace://proof",
    }
    workspace_install = next(tool for tool in root_components["tools"] if tool["name"] == "workspace.install")
    assert workspace_install["read_only"] is False
    assert workspace_install["requires_dry_run"] is True
    assert workspace_install["result_schema"] == "workspace-lifecycle-plan/v1"
    workspace_uninstall = next(tool for tool in root_components["tools"] if tool["name"] == "workspace.uninstall")
    assert workspace_uninstall["destructive"] is True
    assert "destructive" in workspace_uninstall["safety"]["requires_approval_when"]
    assert {prompt["name"] for prompt in root_components["prompts"]} == {
        "workspace.startup",
        "workspace.external_handoff",
    }
    assert {root["id"] for root in root_components["roots"]} >= {
        "workspace-root",
        "workspace-local-root",
    }
    full_tier = next(entry for entry in payload["feature_tiers"] if entry["id"] == "full")
    assert full_tier["modules"] == ["planning", "memory"]
    assert "does not imply source-checkout maintainer tooling" in full_tier["cost_model"]
    assert "maintainer-dogfooding" not in {entry["id"] for entry in payload["feature_tiers"]}
    assert {entry["id"] for entry in payload["advanced_features"]} == {
        "review_artifacts",
        "external_adapters",
    }
    assert {entry["tier"] for entry in payload["advanced_features"]} == {"reusable-diagnostics"}
    assert all(entry["default_enabled"] is False for entry in payload["advanced_features"])
    shipped_catalog = json.dumps(
        {
            "feature_tiers": payload["feature_tiers"],
            "advanced_features": payload["advanced_features"],
        },
        sort_keys=True,
    )
    for source_checkout_only in (
        "maintainer-dogfooding",
        "command_generation",
        "autopilot_loops",
        "self-improvement",
        "codegen",
    ):
        assert source_checkout_only not in shipped_catalog
    assert [entry["name"] for entry in payload["modules"]] == ["planning", "memory"]
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    assert planning_module["install_signals"] == ["TODO.md", ".agentic-workspace/planning/execplans", ".agentic-workspace/planning"]
    assert planning_module["workflow_surfaces"] == [
        "AGENTS.md",
        "TODO.md",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans",
        "docs/maintainer/contributor-playbook.md",
        ".agentic-workspace/planning",
    ]
    assert planning_module["generated_artifacts"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert planning_module["autodetects_installation"] is True
    assert planning_module["installed"] is None
    assert planning_module["dry_run_commands"] == ["adopt", "install", "uninstall", "upgrade"]
    assert planning_module["force_commands"] == ["install"]
    assert planning_module["capabilities"] == [
        "active-execution-state",
        "execplan-routing",
    ]
    assert planning_module["dependencies"] == []
    assert planning_module["conflicts"] == []
    planning_components = planning_module["components"]
    assert {resource["uri"] for resource in planning_components["resources"]} >= {
        "planning://state",
        "planning://summary",
    }
    planning_install = next(tool for tool in planning_components["tools"] if tool["name"] == "planning.install")
    assert planning_install["read_only"] is False
    assert planning_install["requires_dry_run"] is True
    assert planning_install["result_schema"] == "workspace-module-report/v1"
    assert "ambiguous_ownership" in planning_install["safety"]["requires_approval_when"]
    assert {prompt["name"] for prompt in planning_components["prompts"]} >= {
        "planning.autopilot",
        "planning.reporting",
    }
    assert {root["id"] for root in planning_components["roots"]} >= {"planning-root"}
    assert planning_module["result_contract"]["schema_version"] == "workspace-module-report/v1"
    assert planning_module["lifecycle_hook_expectations"] == [
        "adopt",
        "doctor",
        "install",
        "status",
        "uninstall",
        "upgrade",
    ]
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    memory_components = memory_module["components"]
    assert {resource["uri"] for resource in memory_components["resources"]} >= {
        "memory://index",
        "memory://manifest",
    }
    memory_upgrade = next(tool for tool in memory_components["tools"] if tool["name"] == "memory.upgrade")
    assert memory_upgrade["read_only"] is False
    assert memory_upgrade["requires_dry_run"] is True
    assert memory_upgrade["safety"]["dry_run_command"].startswith("agentic-workspace upgrade --modules memory")
    assert {prompt["name"] for prompt in memory_components["prompts"]} >= {
        "memory.router",
        "memory.capture",
    }
    assert planning_module["command_args"]["install"] == ["target", "dry_run", "force"]
    assert planning_module["command_args"]["doctor"] == ["target"]


def test_root_command_manifest_classifies_host_repo_command_surface() -> None:
    manifest = cli_commands_manifest()
    commands = manifest["commands"]
    command_roles = {command["name"]: command["role"] for command in commands}
    command_audiences = {command["name"]: command["audience"] for command in commands}

    assert set(command_roles) == {
        "modules",
        "planning",
        "summary",
        "start",
        "implement",
        "defaults",
        "proof",
        "setup",
        "ownership",
        "config",
        "system-intent",
        "note-delegation-outcome",
        "skills",
        "report",
        "reconcile",
        "external-intent",
        "preflight",
        "install",
        "init",
        "prompt",
        "status",
        "doctor",
        "upgrade",
        "uninstall",
    }
    assert command_roles["install"] == "core_lifecycle"
    assert command_roles["upgrade"] == "core_lifecycle"
    assert command_roles["start"] == "core_context_router"
    assert command_roles["planning"] == "core_context_router"
    assert command_roles["report"] == "core_context_router"
    assert command_roles["modules"] == "module_delegation_front_door"
    assert command_roles["setup"] == "reusable_host_repo_diagnostics"
    assert command_roles["external-intent"] == "reusable_host_repo_diagnostics"
    assert command_audiences["note-delegation-outcome"] == "local_only"
    assert command_audiences["setup"] == "advanced_host_repo"
    assert all(command["classification_note"] for command in commands)
    assert "source_checkout_only_maintainer_development" not in set(command_roles.values())
    assert "remove_or_hide" not in set(command_roles.values())

    prompt = next(command for command in commands if command["name"] == "prompt")
    assert {subcommand["name"] for subcommand in prompt["subcommands"]} == {"init", "upgrade", "uninstall"}
    assert {subcommand["role"] for subcommand in prompt["subcommands"]} == {"core_lifecycle"}

    external_intent = next(command for command in commands if command["name"] == "external-intent")
    assert external_intent["subcommands"][0]["audience"] == "advanced_host_repo"


def test_modules_command_does_not_advertise_current_memory_as_ordinary_surface(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["modules", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    ordinary_surfaces = memory_module["install_signals"] + memory_module["workflow_surfaces"]
    assert ".agentic-workspace/memory/repo/current" not in ordinary_surfaces
    assert ".agentic-workspace/memory/repo/current/" not in ordinary_surfaces


def test_defaults_command_reports_machine_readable_default_routes_as_json(capsys) -> None:
    assert cli.main(["defaults", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["startup"]["canonical_doc"] == ".agentic-workspace/docs/minimum-operating-model.md"
    assert payload["startup"]["context_router"]["kind"] == "workspace-context-router-family/v1"
    assert [view["view"] for view in payload["startup"]["context_router"]["views"]] == [
        "start",
        "summary",
        "report",
        "defaults",
        "preflight",
    ]
    assert payload["startup"]["default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert payload["startup"]["supported_agent_instructions_files"] == ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules"]
    assert payload["startup"]["tiny_safe_model"]["entrypoint"] == "AGENTS.md"
    assert payload["startup"]["tiny_safe_model"]["entry_query"] == 'agentic-workspace start --profile tiny --task "<task>" --format json'
    assert (
        payload["startup"]["tiny_safe_model"]["first_compact_queries"][0]
        == 'agentic-workspace start --target ./repo --profile tiny --task "<task>" --format json'
    )
    assert payload["startup"]["tiny_safe_model"]["deeper_reads_become_valid_when"][0].startswith("the active summary points")
    vague_route = payload["startup"]["vague_outcome_route"]
    assert vague_route["status"] == "available"
    assert vague_route["compact_commands"][0] == 'agentic-workspace preflight --target . --task "<task>" --format json'
    assert "satisfaction evidence" in " ".join(vague_route["answer_contract"])
    assert vague_route["raw_read_rule"].startswith("Open raw .agentic-workspace files only after compact output")
    work_gate = payload["startup"]["work_intent_gate"]
    assert work_gate["rule"].startswith("Choose the smallest workflow shape before implementation")
    assert [level["id"] for level in work_gate["levels"]] == ["direct", "bounded", "lane", "epic"]
    assert "optional intake evidence" in work_gate["external_tracker_rule"]
    assert "adaptive_assurance" in work_gate["assurance_rule"]
    assert ".agentic-workspace/planning/state.toml" not in payload["startup"]["primary"][2]
    assert payload["startup"]["first_queries"][0]["command"] == 'agentic-workspace start --profile tiny --task "<task>" --format json'
    assert payload["startup"]["first_queries"][0]["field"] == "immediate_next_allowed_action"
    assert payload["startup"]["first_queries"][1]["command"] == "agentic-workspace defaults --section startup --format json"
    assert payload["startup"]["first_queries"][2]["field"] == "workspace.agent_instructions_file"
    assert payload["startup"]["first_queries"][3]["field"] == "planning_record"
    assert payload["startup"]["surface_roles"][0]["surface"] == "AGENTS.md"
    assert any(
        role.get("surface") == "llms.txt" and role.get("role") == "external install/adopt handoff only"
        for role in payload["startup"]["surface_roles"]
    )
    state_role = next(role for role in payload["startup"]["surface_roles"] if role["surface"] == ".agentic-workspace/planning/state.toml")
    assert state_role["role"] == "planning source behind compact summary, not ordinary first-contact reading"
    assert "only when" in state_role["edit_rule"]
    assert payload["startup"]["surface_roles"][3]["kind"] == "managed"
    assert payload["startup"]["escalation_cues"][0]["boundary"] == "workspace"
    assert payload["startup"]["escalation_cues"][1]["boundary"] == "planning"
    planning_load_next = payload["startup"]["escalation_cues"][1]["load_next"]
    assert planning_load_next[0] == "agentic-workspace summary --format json"
    assert planning_load_next[1] == "agentic-workspace summary --format json --profile full"
    assert "only when" in planning_load_next[2]
    assert payload["startup"]["top_level_capabilities"][2]["module"] == "memory"
    assert any("current agent does not natively look for `AGENTS.md`" in step for step in payload["startup"]["fallbacks"])
    skill_routing = payload["startup"]["skill_routing"]
    assert skill_routing["status"] == "advisory"
    assert skill_routing["query"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert "planning-autopilot" not in {route["skill"] for route in skill_routing["preferred_routes"]}
    assert "planning-intake-upstream-task" not in {route["skill"] for route in skill_routing["preferred_routes"]}
    assert "planning-review-pass" not in {route["skill"] for route in skill_routing["preferred_routes"]}
    assert skill_routing["available_advanced_route_command"] == "agentic-workspace modules --target ./repo --format json"
    assert any("WORKFLOW.md" in fallback for fallback in skill_routing["fallback_when_skills_unavailable"])
    assert payload["compact_contract_profile"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["compact_contract_profile"]["rule"] == (
        "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump."
    )
    assert payload["compact_contract_profile"]["selectors"]["defaults"] == ("agentic-workspace defaults --section <section> --format json")
    assert payload["operating_questions"]["canonical_doc"] == "docs/which-package.md"
    assert payload["operating_questions"]["command"] == "agentic-workspace defaults --section operating_questions --format json"
    assert payload["operating_questions"]["questions"][0]["id"] == "startup_or_lifecycle_path"
    assert payload["operating_questions"]["questions"][1]["ask_first"] == "agentic-workspace summary --format json"
    assert payload["operating_questions"]["questions"][2]["ask_first"] == "agentic-workspace preflight --target ./repo --format json"
    assert payload["operating_questions"]["questions"][2]["then_if_needed"][0] == "agentic-workspace report --target ./repo --format json"
    assert payload["install_profiles"]["canonical_doc"] == "docs/which-package.md"
    assert payload["install_profiles"]["command"] == "agentic-workspace defaults --section install_profiles --format json"
    assert payload["install_profiles"]["rule"].startswith("Use the public workspace entrypoint and choose the smallest preset")
    assert payload["install_profiles"]["recommendation_order"] == ["memory", "planning", "full"]
    assert payload["install_profiles"]["profiles"][0]["preset"] == "memory"
    assert payload["install_profiles"]["profiles"][1]["preset"] == "planning"
    assert payload["install_profiles"]["lightweight_profile"]["preset"] == "memory"
    assert payload["lifecycle"]["primary_entrypoint"] == "agentic-workspace"
    assert "agentic-workspace install --target ./repo --preset <memory|planning|full>" == payload["lifecycle"]["default_install_command"]
    assert payload["lifecycle"]["default_setup_posture"] == "smallest-viable-preset-first"
    assert payload["lifecycle"]["canonical_external_agent_handoff"] == "llms.txt"
    assert payload["lifecycle"]["canonical_bootstrap_next_action"] == ".agentic-workspace/bootstrap-handoff.md"
    assert payload["lifecycle"]["canonical_bootstrap_handoff_record"] == ".agentic-workspace/bootstrap-handoff.json"
    assert payload["setup"]["canonical_doc"] == "docs/jumpstart-contract.md"
    assert Path(payload["setup"]["canonical_doc"]).exists()
    assert payload["setup"]["command"] == "agentic-workspace setup --target ./repo --format json"
    assert payload["setup"]["rule"] == "Setup is a bounded post-bootstrap phase that stays separate from init."
    assert payload["setup"]["phase"] == "post-bootstrap"
    assert payload["setup"]["scope"] == [
        "orient from a compact report first",
        "keep follow-through bounded and reviewable",
    ]
    assert payload["setup_findings_promotion"]["canonical_doc"] == "docs/setup-findings-contract.md"
    assert Path(payload["setup_findings_promotion"]["canonical_doc"]).exists()
    assert payload["setup_findings_promotion"]["command"] == "agentic-workspace setup --target ./repo --format json"
    assert payload["setup_findings_promotion"]["artifact_path"] == "tools/setup-findings.json"
    assert payload["setup_findings_promotion"]["schema_path"] == "src/agentic_workspace/contracts/schemas/setup_findings.schema.json"
    assert payload["setup_findings_promotion"]["accepted_kind"] == "workspace-setup-findings/v1"
    assert payload["setup_findings_promotion"]["accepted_classes"][0]["class"] == "repo_friction_evidence"
    assert payload["setup_findings_promotion"]["accepted_classes"][1]["class"] == "planning_candidate"
    assert payload["setup_findings_promotion"]["secondary"] == [
        "Do not build a workspace-owned analyzer.",
        "Do not auto-write planning or memory state from setup input.",
        "Do not preserve findings that have no durable owner or bounded next action.",
    ]
    assert payload["intent"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["intent"]["command"] == "agentic-workspace defaults --section intent --format json"
    assert payload["intent"]["rule"] == "Confirmed intent stays human-owned; interpreted intent must remain visibly inferred."
    assert payload["intent"]["confirmed_intent"]["summary"] == "the human-owned request before workspace normalization"
    assert payload["intent"]["interpreted_intent"]["summary"] == "the workspace-normalized request carried forward by lifecycle commands"
    assert payload["system_intent"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"
    assert payload["system_intent"]["command"] == "agentic-workspace defaults --section system_intent --format json"
    assert payload["system_intent"]["authority_ladder"][0]["layer"] == "confirmed request or live issue cluster"
    assert "larger outcome is actually closed" in payload["system_intent"]["recoverability"]["must_answer"][1]
    assert payload["surface_value_guardrail"]["command"] == "agentic-workspace defaults --section surface_value_guardrail --format json"
    assert payload["surface_value_guardrail"]["preference_order"][0] == "remove an unnecessary surface"
    assert "replace, compress, merge" in payload["surface_value_guardrail"]["value_questions"][1]
    assert payload["effective_authority"]["defaults_command"] == "agentic-workspace defaults --section effective_authority --format json"
    assert payload["effective_authority"]["authority_map"][1]["surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert payload["effective_authority"]["system_intent_embodiment"]["must_answer_before_closure"][0].startswith("Did the slice")
    assert payload["clarification"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["clarification"]["command"] == "agentic-workspace defaults --section clarification --format json"
    assert payload["clarification"]["rule"] == "When a prompt is vague, ask the smallest repo-context question that removes the ambiguity."
    assert payload["clarification"]["mode"] == "minimal-interruption"
    assert payload["clarification"]["first_questions"] == [
        "Which surface should change?",
        "What proof would make the change safe?",
        "Does the work belong in planning, memory, or workspace-level docs?",
    ]
    assert payload["prompt_routing"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["prompt_routing"]["command"] == "agentic-workspace defaults --section prompt_routing --format json"
    assert payload["prompt_routing"]["rule"] == "Map vague prompt classes to a proof lane and an owner before widening the task."
    assert payload["prompt_routing"]["route_by_class"][0]["class"] == "workspace lifecycle change"
    assert payload["prompt_routing"]["route_by_class"][0]["proof_lane"] == "workspace_cli"
    assert payload["prompt_routing"]["route_by_class"][0]["owner_surface"] == "src/agentic_workspace/cli.py"
    assert payload["prompt_routing"]["route_by_class"][2]["proof_lane"] == "memory_payload"
    assert payload["prompt_routing"]["route_by_class"][3]["proof_lane"] == "workspace_cli"
    assert payload["prompt_routing"]["route_by_class"][3]["broaden_with"] == ["planning_surfaces"]
    assert payload["relay"]["canonical_doc"] == ".agentic-workspace/docs/delegation-posture-contract.md"
    assert payload["relay"]["command"] == "agentic-workspace defaults --section relay --format json"
    assert payload["relay"]["rule"] == (
        "Use a strong planner to normalize the vague prompt, then hand the compact contract to a bounded executor without prescribing the execution method."
    )
    assert payload["relay"]["handoff_command"] == "agentic-planning handoff --format json"
    assert payload["relay"]["execution_methods"][1]["id"] == "external cli or api"
    assert payload["relay"]["planner_role"]["summary"] == (
        "shape confirmed and interpreted intent, choose the proof lane, and freeze the smallest safe contract."
    )
    assert payload["relay"]["memory_bridge"]["summary"] == (
        "when routed Memory is installed, borrow durable repo understanding before freezing the compact contract."
    )
    assert payload["setup"]["secondary"] == [
        "Do not widen init.",
        "Do not collapse setup into the proof backlog.",
        "Do not turn setup into generic analysis.",
    ]
    assert payload["validation"]["default_routes"]["planning_package"] == "cd packages/planning && uv run pytest tests/test_installer.py"
    workspace_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "workspace_cli")
    assert "root workspace CLI changes" in workspace_lane["when"]
    assert workspace_lane["enough_proof"] == [
        "uv run pytest tests -q",
        "uv run ruff check src tests",
    ]
    assert "the change also touches generated maintainer docs" in workspace_lane["broaden_when"]
    assert "the narrow lane cannot prove the change on its own" in workspace_lane["escalate_when"]
    planning_surface_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "planning_surfaces")
    assert planning_surface_lane["enough_proof"] == ["agentic-workspace doctor --target ./repo --modules planning --format json"]
    assert payload["validation"]["escalation_rule"] == (
        "Broaden validation only when the narrower lane stops proving the touched contract or the change crosses boundaries."
    )
    assert payload["proof_surfaces"]["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["proof_surfaces"]["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_surfaces"]["default_routes"]["workspace_proof"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_selection"]["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["proof_selection"]["command"] == "agentic-workspace defaults --section proof_selection --format json"
    assert payload["proof_selection"]["rule"] == (
        "Make proof choice cheap by naming the narrowest lane that still answers the trust question."
    )
    assert payload["proof_selection"]["recommended_lanes"][0]["id"] == "workspace_proof"
    assert payload["proof_selection"]["recommended_lanes"][0]["enough_proof"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_selection"]["recommended_lanes"][2]["id"] == "validation_lane"
    assert "Prefer the smallest queryable proof answer first." in payload["proof_selection"]["rule_of_thumb"]
    assert payload["assurance_onboarding"]["status"] == "absent"
    assert payload["assurance_onboarding"]["command"] == "agentic-workspace defaults --section assurance_onboarding --format json"
    assert payload["assurance_onboarding"]["states"]["usable"].startswith("at least one proof profile")
    assert payload["ownership_mapping"]["canonical_doc"] == ".agentic-workspace/docs/ownership-authority-contract.md"
    assert payload["ownership_mapping"]["command"] == "agentic-workspace ownership --target ./repo --format json"
    assert payload["ownership_mapping"]["ledger"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["combined_install"]["primary"] == "agentic-workspace install --target ./repo --preset <memory|planning|full>"
    assert payload["combined_install"]["full_when"].startswith("Use --preset full only when both")
    assert payload["recovery"]["canonical_doc"] == "docs/environment-recovery-contract.md"
    assert payload["recovery"]["rule"] == "Inspect state first, refresh contract second, re-run the narrowest proving lane third."
    assert payload["recovery"]["ordered_path"][:2] == [
        "agentic-workspace status --target ./repo",
        "agentic-workspace doctor --target ./repo",
    ]
    assert ".agentic-workspace/bootstrap-handoff.md" in payload["recovery"]["handoff_surfaces"]
    assert ".agentic-workspace/bootstrap-handoff.json" in payload["recovery"]["handoff_surfaces"]
    assert (
        payload["recovery"]["effective_output_posture"]["command"]
        == "agentic-workspace config --target ./repo --profile compact --format json"
    )
    assert payload["recovery"]["effective_output_posture"]["field"] == "workspace.optimization_bias"
    assert payload["completion"]["rule"] == (
        "When a completed slice came from state.toml, clear the matched queue residue in the same pass."
    )
    assert payload["completion"]["prefer_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/README.md",
    ]
    assert payload["delegated_judgment"]["canonical_doc"] == "docs/delegated-judgment-contract.md"
    assert payload["delegated_judgment"]["rule"] == "Improve means locally; do not silently rewrite ends locally."
    assert "requested outcome" in payload["delegated_judgment"]["human_sets"]
    assert "bounded decomposition" in payload["delegated_judgment"]["agent_may_decide"]
    assert "the better-looking solution changes the requested outcome" in payload["delegated_judgment"]["escalate_when"]
    assert payload["delegated_judgment"]["operational_follow_through"] == [
        "use a checked-in execplan when the requested outcome must survive across sessions",
        "preserve escalation boundaries in the machine-readable defaults when the task is broad enough to need them",
        "route durable residue into the correct checked-in surface instead of leaving it in chat",
    ]
    assert payload["mixed_agent"]["rule"] == "Prefer runtime/task inference first, then stable policy, then explicit prompting."
    assert payload["mixed_agent"]["decision_order"] == [
        "runtime/task inference",
        "repo-owned policy",
        "optional local machine/runtime override",
        "explicit prompting when still unsafe",
    ]
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["supported_fields"] == [
        "workspace.cli_invoke",
        "runtime.supports_internal_delegation",
        "runtime.strong_planner_available",
        "runtime.cheap_bounded_executor_available",
        "handoff.prefer_internal_delegation_when_available",
        "safety.safe_to_auto_run_commands",
        "safety.requires_human_verification_on_pr",
        "delegation.mode",
        "clarification.mode",
        "local_memory.enabled",
        "local_memory.path",
        "delegation_targets.<target>.strength",
        "delegation_targets.<target>.location",
        "delegation_targets.<target>.confidence",
        "delegation_targets.<target>.task_fit",
        "delegation_targets.<target>.capability_classes",
        "delegation_targets.<target>.execution_methods",
        "delegation_targets.<target>.model_family",
        "delegation_targets.<target>.provider",
        "delegation_targets.<target>.context_capacity",
        "delegation_targets.<target>.reasoning_profile",
        "delegation_targets.<target>.cost_class",
        "delegation_targets.<target>.latency_class",
        "delegation_targets.<target>.safe_task_classes",
        "delegation_targets.<target>.forbidden_task_classes",
        "delegation_targets.<target>.escalation_target",
        "delegation_targets.<target>.confidence_source",
        "delegation_targets.<target>.last_evaluation",
        "delegation_targets.<target>.human_control_modes",
    ]
    assert payload["mixed_agent"]["local_override"]["supported_target_strengths"] == ["strong", "medium", "weak"]
    assert payload["mixed_agent"]["local_override"]["supported_target_locations"] == ["local", "external", "either"]
    assert payload["mixed_agent"]["local_override"]["supported_capability_classes"] == [
        "boundary-shaping",
        "reasoning-heavy",
        "mixed",
        "mechanical-follow-through",
    ]
    assert payload["mixed_agent"]["local_override"]["supported_target_execution_methods"] == [
        "internal",
        "cli",
        "api",
        "manual",
    ]
    assert payload["mixed_agent"]["local_override"]["supported_target_context_capacities"] == ["small", "medium", "large", "unknown"]
    assert payload["mixed_agent"]["local_override"]["supported_target_reasoning_profiles"] == [
        "weak",
        "balanced",
        "strong",
        "unknown",
    ]
    assert payload["mixed_agent"]["local_override"]["supported_target_cost_classes"] == ["cheap", "standard", "premium", "unknown"]
    assert payload["mixed_agent"]["local_override"]["supported_target_latency_classes"] == ["fast", "standard", "slow", "unknown"]
    assert payload["mixed_agent"]["local_override"]["supported_delegation_modes"] == ["off", "manual", "suggest", "auto"]
    assert payload["mixed_agent"]["local_override"]["supported_clarification_modes"] == ["ask-first", "suggest", "auto-continue"]
    delegation_control = payload["mixed_agent"]["delegation_control"]
    assert delegation_control["field"] == "delegation.mode"
    assert delegation_control["default"] == "suggest"
    assert "quality" in delegation_control["quality_first_rule"]
    assert delegation_control["mode_semantics"]["auto"].startswith("permit automatic delegation")
    clarification_control = payload["mixed_agent"]["clarification_control"]
    assert clarification_control["field"] == "clarification.mode"
    assert clarification_control["default"] == "suggest"
    assert clarification_control["mode_semantics"]["ask-first"].startswith("stop and ask")
    assert payload["mixed_agent"]["local_outcome_artifact"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "kind": "agentic-workspace/delegation-outcomes/v1",
        "rule": "local-only delegation outcome evidence used to derive advisory tuning suggestions over time",
    }
    assert payload["mixed_agent"]["local_integration_area"]["root"] == ".agentic-workspace/local/integrations"
    assert payload["mixed_agent"]["local_integration_area"]["subfolder_convention"] == "<vendor-or-runtime>/"
    assert payload["mixed_agent"]["local_integration_area"]["authoritative"] is False
    assert payload["mixed_agent"]["local_integration_area"]["git_ignored"] is True
    assert payload["mixed_agent"]["local_integration_area"]["scratch"]["root"] == ".agentic-workspace/local/scratch"
    assert payload["mixed_agent"]["local_integration_area"]["scratch"]["safe_to_delete"] is True
    assert payload["mixed_agent"]["local_integration_area"]["canonical_doc"] == ".agentic-workspace/docs/local-integration-area.md"
    shim_pattern = payload["mixed_agent"]["local_integration_area"]["runtime_artifact_shim_pattern"]
    assert shim_pattern["kind"] == "agentic-workspace/local-runtime-artifact-shim/v1"
    assert shim_pattern["artifact_classes"] == ["internal-plan", "check-bundle", "handoff-state", "runtime-export"]
    assert shim_pattern["authoritative"] is False
    assert "proof_command" in shim_pattern["metadata_required"]
    assert "local shims never become shared authority by existing locally" in shim_pattern["promotion_boundary"]
    assert "not a plugin registry or shared compatibility framework" in payload["mixed_agent"]["local_integration_area"]["boundary_rules"]
    assert payload["mixed_agent"]["local_scratch"]["sign"].startswith("Go ahead and use this")
    agent_aids = payload["mixed_agent"]["agent_aid_storage"]
    assert agent_aids["command"] == "agentic-workspace defaults --section agent_aid_storage --format json"
    assert agent_aids["candidate_root"] == ".agentic-workspace/agent-aids"
    assert agent_aids["candidate_root_exists"] is False
    assert agent_aids["ordinary_startup"] is False
    assert agent_aids["manifest_name"] == "manifest.json"
    assert agent_aids["manifest_kind"] == "agentic-workspace/agent-aid/v1"
    assert agent_aids["manifest_schema"] == "src/agentic_workspace/contracts/schemas/agent_aid_manifest.schema.json"
    assert agent_aids["creation_affordance"]["agent_may_create"] is True
    assert "handoff cost" in agent_aids["creation_affordance"]["summary"]
    assert agent_aids["creation_affordance"]["first_pattern"]["makefile_variable"] == "COMPACT_RUN"
    assert agent_aids["creation_affordance"]["first_pattern"]["timeout_option"] == "--timeout-seconds <seconds>"
    assert agent_aids["creation_affordance"]["first_pattern"]["full_log_root"] == "scratch/command-logs"
    assert agent_aids["executable_safety"]["hidden_required_workflow"] == "forbidden"
    assert agent_aids["executable_safety"]["canonical_proof_role_requires_status"] == "promoted"
    assert {entry["class"] for entry in agent_aids["storage_classes"]} == {
        "local-only",
        "checked-in-candidate",
        "promoted-repo-native",
        "package-owned",
        "source-checkout-only",
    }
    assert "the model is repo-, agent-, tool-, and language-agnostic" in agent_aids["boundary_rules"]
    assert payload["mixed_agent"]["local_memory"]["path"] == ".agentic-workspace/local/memory.toml"
    assert payload["mixed_agent"]["local_memory"]["authoritative"] is False
    assert payload["mixed_agent"]["local_memory"]["advisory_only"] is True
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["handoff_quality"]["must_recover"] == [
        "current intent",
        "hard constraints",
        "relevant durable context",
        "proof expectations",
        "immediate next action",
    ]
    assert payload["mixed_agent"]["delegated_run_guardrail"]["rule"].startswith("Before delegating bounded implementation")
    assert payload["mixed_agent"]["delegated_run_guardrail"]["required_preflight_checks"][0] == (
        "recover handoff-quality must_recover fields from checked-in state"
    )
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["default_trust"] == "normal"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_when"][0] == (
        "target advisory review burden is high"
    )
    assert payload["mixed_agent"]["delegated_run_guardrail"]["weak_target_escalation"]["quality_over_cost"].startswith(
        "Cost saving is valid"
    )
    assert payload["mixed_agent"]["delegated_run_guardrail"]["strong_target_downrouting"]["quality_over_cost"].startswith(
        "Down-routing is valid"
    )
    assert payload["delegation_posture"]["canonical_doc"] == ".agentic-workspace/docs/delegation-posture-contract.md"
    assert payload["delegation_posture"]["command"] == "agentic-workspace defaults --section delegation_posture --format json"
    assert payload["delegation_posture"]["rule"] == (
        "Use the effective mixed-agent posture to decide whether to keep work direct, "
        "split it into planner/implementer/validator subtasks, or escalate to a stronger planner."
    )
    assert payload["delegation_posture"]["preferred_split"] == ["planner", "implementer", "validator"]
    assert payload["delegation_posture"]["config_controls"] == [
        ".agentic-workspace/config.local.toml runtime.supports_internal_delegation",
        ".agentic-workspace/config.local.toml runtime.strong_planner_available",
        ".agentic-workspace/config.local.toml runtime.cheap_bounded_executor_available",
        ".agentic-workspace/config.local.toml handoff.prefer_internal_delegation_when_available",
        ".agentic-workspace/config.local.toml delegation_targets.<target>.*",
        ".agentic-workspace/delegation-outcomes.json",
    ]
    assert payload["delegation_posture"]["secondary"] == [
        "Do not treat config as a scheduler.",
        "Do not delegate when the task stays cheap and direct.",
        "Do not use weak targets for high-judgment work just to save tokens; escalate first.",
        "Do not spend strong-agent budget on mechanical work when a safe cheaper route is configured.",
        "Do not silently rewrite ends.",
    ]
    assert payload["delegation_posture"]["capability_posture_fields"] == [
        "execution class",
        "recommended strength",
        "preferred location",
        "delegation friendly",
        "strong external reasoning",
        "work shape",
        "proof burden",
        "risk flags",
        "inspection evidence required",
        "classification authority",
        "self-assessment authority",
        "why",
    ]
    assert payload["config"]["path"] == ".agentic-workspace/config.toml"
    assert payload["config"]["command"] == "agentic-workspace config --target ./repo --profile compact --format json"
    assert "workspace.default_preset" in payload["config"]["supported_fields"]
    assert "workspace.improvement_latitude" in payload["config"]["supported_fields"]
    assert "workspace.optimization_bias" in payload["config"]["supported_fields"]
    assert "workspace.workflow_artifact_profile" in payload["config"]["supported_fields"]
    assert "system_intent.sources" in payload["config"]["supported_fields"]
    assert "workflow_obligations.<name>.summary" in payload["config"]["supported_fields"]
    assert payload["agent_configuration_system"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert (
        payload["agent_configuration_system"]["command"] == "agentic-workspace defaults --section agent_configuration_system --format json"
    )
    assert payload["agent_configuration_system"]["configuration_classes"][0]["id"] == "startup_and_adapter_policy"
    assert payload["agent_configuration_system"]["authority_map"][0]["surface"] == ".agentic-workspace/config.toml"
    assert payload["agent_configuration_system"]["adapter_surfaces"][0]["surface"] == "AGENTS.md"
    assert payload["agent_configuration_queries"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_queries"]["query_classes"][0]["id"] == "startup_path"
    assert payload["agent_configuration_queries"]["query_classes"][3]["ask_first"] == "agentic-workspace summary --format json"
    assert payload["improvement_latitude"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["improvement_latitude"]["command"] == "agentic-workspace defaults --section improvement_latitude --format json"
    assert payload["improvement_latitude"]["owner_surface"] == "workspace"
    assert payload["improvement_latitude"]["policy_target"] == "repo-directed-improvement"
    assert payload["improvement_latitude"]["workspace_self_adaptation"]["status"] == "allowed-with-bounds"
    assert "proof" in payload["improvement_latitude"]["workspace_self_adaptation"]["bounded_by"]
    assert payload["improvement_latitude"]["friction_response_order"][0]["action"] == "adapt-inside-workspace-first"
    assert "validation friction" in payload["improvement_latitude"]["guardrail_test"]["surface_repo_friction_when"][0]
    assert payload["improvement_latitude"]["guardrail_test"]["prefer"] == "one clear adaptation over accumulating many narrow special cases"
    threshold = payload["improvement_latitude"]["repo_directed_improvement_threshold"]
    assert threshold["status"] == "explicit-contract"
    assert "two independent friction confirmations" in threshold["minimum_threshold"][0]
    assert threshold["not_enough"][0] == "one-off agent discomfort"
    assert "shared repeated evidence" in threshold["collaboration_bias"]
    assert "workspace self-adaptation remains allowed" in payload["improvement_latitude"]["mode_interpretation"]["none"]
    assert payload["improvement_latitude"]["incidental_finding_policy"]["status"] == "required-reporting"
    assert "future agent efficiency" in payload["improvement_latitude"]["incidental_finding_policy"]["report_when"][0]
    assert "repo seams" in payload["improvement_latitude"]["examples"]["repo_directed_improvement_next"][0]
    assert payload["improvement_latitude"]["default_mode"] == "conservative"
    assert payload["improvement_latitude"]["supported_modes"][0]["mode"] == "none"
    assert payload["improvement_latitude"]["supported_modes"][1]["mode"] == "reporting"
    assert payload["improvement_latitude"]["supported_modes"][1]["initiative_posture"] == "reporting-only"
    assert "review outputs" in payload["improvement_latitude"]["supported_modes"][1]["reporting_destinations"]
    assert payload["improvement_latitude"]["supported_modes"][3]["mode"] == "balanced"
    assert "repeated shared evidence" in payload["improvement_latitude"]["supported_modes"][3]["allows"][1]
    assert payload["improvement_latitude"]["evidence_source"] == "agentic-workspace report --target ./repo --format json"
    assert payload["improvement_latitude"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
    ]
    assert payload["improvement_latitude"]["validation_friction"]["status"] == "explicit-contract"
    assert "weak_seam" in payload["improvement_latitude"]["validation_friction"]["subtypes"]
    assert (
        "the requested outcome still means the same thing after the improvement"
        in payload["improvement_latitude"]["decision_test"]["stays_local_when"]
    )
    assert (
        "the improvement changes what counts as success instead of only changing the means"
        in payload["improvement_latitude"]["decision_test"]["changed_task_when"]
    )
    assert payload["optimization_bias"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["optimization_bias"]["command"] == "agentic-workspace defaults --section optimization_bias --format json"
    assert payload["optimization_bias"]["owner_surface"] == "workspace"
    assert payload["optimization_bias"]["default_mode"] == "balanced"
    assert payload["optimization_bias"]["supported_modes"][0]["mode"] == "agent-efficiency"
    assert payload["optimization_bias"]["supported_modes"][2]["mode"] == "human-legibility"
    assert "execution method" in payload["optimization_bias"]["must_not_change"]
    assert payload["optimization_bias"]["surface_boundary"]["honors_bias"][0] == "derived report rendering density"
    assert "machine-readable report truth" in payload["optimization_bias"]["surface_boundary"]["stays_invariant"]
    assert payload["workflow_artifact_adapters"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert (
        payload["workflow_artifact_adapters"]["command"] == "agentic-workspace defaults --section workflow_artifact_adapters --format json"
    )
    assert payload["workflow_artifact_adapters"]["default_profile"] == "repo-owned"
    gemini_profile = next(
        profile for profile in payload["workflow_artifact_adapters"]["supported_profiles"] if profile["profile"] == "gemini"
    )
    assert gemini_profile["native_artifacts"] == ["implementation_plan.md", "task.md", "walkthrough.md"]
    assert gemini_profile["canonical_surfaces"] == [".agentic-workspace/planning/state.toml", ".agentic-workspace/planning/execplans/"]
    assert any("summary --format json" in step and "raw planning state" in step for step in payload["startup"]["secondary"])
    assert payload["startup"]["workflow_recovery"] == [
        (
            "When takeover or recovery is unclear, prefer "
            '`agentic-workspace start --profile tiny --task "<task>" --format json`, then '
            "`agentic-workspace preflight --format json`, "
            "`agentic-workspace defaults --section startup --format json`, "
            "`agentic-workspace config --target ./repo --profile compact --format json`, and "
            "`agentic-workspace summary --format json` before broader "
            "prose or repo-local workaround guidance."
        ),
    ]
    assert any("skills --target ./repo --task" in step for step in payload["skill_discovery"]["primary"])


def test_defaults_command_routes_through_generated_adapter(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def fake_defaults_handler(args) -> int:
        calls.append((args.command, args.format, getattr(args, "section", None)))
        print('{"ok": true}')
        return 0

    monkeypatch.setitem(cli._GENERATED_RUNTIME_HANDLERS, "defaults.report", fake_defaults_handler)

    assert cli.main(["defaults", "--section", "startup", "--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert calls == [("defaults", "json", "startup")]


def test_defaults_command_text_emphasises_primary_and_secondary_routes(capsys) -> None:
    assert cli.main(["defaults"]) == 0

    text = capsys.readouterr().out
    assert "Startup:" in text
    assert "agentic-workspace defaults --section startup --format json" in text
    assert "Lifecycle:" in text
    assert "primary entrypoint: agentic-workspace" in text
    assert "bootstrap handoff record: .agentic-workspace/bootstrap-handoff.json" in text
    assert "Setup:" in text
    assert "docs/jumpstart-contract.md" in text
    assert "Intent:" in text
    assert "Confirmed intent stays human-owned" in text
    assert "confirmed:" in text
    assert "interpreted:" in text
    assert "Clarification:" in text
    assert "mode: minimal-interruption" in text
    assert "Prompt routing:" in text
    assert "Relay:" in text
    assert "strong planner" in text
    assert "Agent configuration system:" in text
    assert "Agent configuration queries:" in text
    assert "Agent configuration workflow extensions:" in text
    assert "Improvement latitude:" in text
    assert "owner: workspace" in text
    assert "default mode: conservative" in text
    assert "none: Do not perform opportunistic repo-friction reduction" in text
    assert "reporting: Notice and surface notable repo friction" in text
    assert "Optimization bias:" in text
    assert "default mode: balanced" in text
    assert "agent-efficiency: Prefer terse durable outputs" in text
    assert "Delegation posture:" in text
    assert ".agentic-workspace/docs/delegation-posture-contract.md" in text
    assert "Compact contract profile:" in text
    assert ".agentic-workspace/docs/compact-contract-profile.md" in text
    assert "Proof surfaces:" in text
    assert ".agentic-workspace/docs/proof-surfaces-contract.md" in text
    assert "Proof selection:" in text
    assert "defaults --section proof_selection" in text
    assert "Ownership mapping:" in text
    assert ".agentic-workspace/docs/ownership-authority-contract.md" in text
    assert "Combined install:" in text
    assert "Recovery:" in text
    assert "docs/environment-recovery-contract.md" in text
    assert (
        "effective output posture: agentic-workspace config --target ./repo --profile compact --format json -> workspace.optimization_bias"
    ) in text
    assert "Completion:" in text
    assert "Config:" in text
    assert "Workflow artifact adapters:" in text
    assert ".agentic-workspace/docs/workspace-config-contract.md" in text
    assert "Delegated judgment:" in text
    assert "Delegated judgment follow-through:" in text
    assert "Mixed-agent:" in text
    assert "docs/delegated-judgment-contract.md" in text
    assert "make maintainer-surfaces" in text


def test_external_agent_handoff_text_names_target_repository_and_no_install_assumption() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    assert "Authority marker:" in text
    assert "- authority: generated-adapter" in text
    assert "- safe_to_edit: false" in text
    assert "Generated compatibility adapter" in text
    assert "Ordinary path:" in text
    assert 'agentic-workspace start --profile tiny --task "<task>" --format json' in text
    assert "agentic-workspace preflight --format json" in text
    assert "agentic-workspace config --target ./repo --profile compact --format json" in text
    assert "agentic-workspace summary --format json" in text
    assert "agentic-workspace proof --profile tiny --changed <paths> --format json" in text
    assert "agentic-workspace defaults --section install_profiles --format json" in text
    assert "Use `full` only when both Memory and Planning are explicitly desired." not in text
    assert "`AGENTS.md` remains the repo startup entrypoint" in text
    assert "Compact routing docs when present" not in text
    assert text.count("Read `AGENTS.md` first.") == 1
    assert text.count("`AGENTS.md` remains the repo startup entrypoint") == 1


def test_external_agent_handoff_text_demotes_broad_routing_until_compact_startup_fails() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    start_index = text.index('agentic-workspace start --profile tiny --task "<task>" --format json')
    preflight_index = text.index("agentic-workspace preflight --format json")
    config_index = text.index("agentic-workspace config --target ./repo --profile compact --format json")
    summary_index = text.index("agentic-workspace summary --format json")

    assert start_index < preflight_index
    assert start_index < config_index
    assert start_index < summary_index
    assert "When needed:" in text
    assert "Open raw planning or contract files only when compact commands point there." in text


def test_external_agent_handoff_text_does_not_default_combined_install_to_full() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning", "memory"])

    selector_index = text.index("agentic-workspace defaults --section install_profiles --format json")
    memory_index = text.index("agentic-workspace install --target ./repo --preset memory")
    planning_index = text.index("agentic-workspace install --target ./repo --preset planning")
    full_index = text.index("agentic-workspace install --target ./repo --preset full")

    assert selector_index < memory_index < planning_index < full_index
    assert "Use `full` only when both Memory and Planning are explicitly desired." in text


def test_external_agent_handoff_text_uses_configured_agent_instructions_filename() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"], agent_instructions_file="GEMINI.md")

    assert "Read `GEMINI.md` first." in text
    assert "`GEMINI.md` remains the repo startup entrypoint" in text


def test_external_agent_handoff_text_reports_workflow_artifact_profile() -> None:
    text = cli._external_agent_handoff_text(
        selected_modules=["planning"],
        agent_instructions_file="GEMINI.md",
        workflow_artifact_profile="gemini",
    )

    assert "Workflow artifact profile: gemini." in text
    assert "Generated compatibility adapter" in text
    assert 'agentic-workspace start --profile tiny --task "<task>" --format json' in text
    assert "Keep canonical authority in contracts, config, planning, Memory, and checks, not this adapter." in text


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    assert payload["exists"] is False
    assert payload["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["edit_reference"]["generated_reference_doc"] == "docs/reference/workspace-config.md"
    assert payload["edit_reference"]["source_schema"] == "src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
    assert "# Agentic Workspace managed config." in payload["edit_reference"]["managed_header"]
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --profile compact --format json"
    assert payload["workspace"]["default_preset"] == "full"
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "product-default"
    assert payload["workspace"]["improvement_latitude"] == "conservative"
    assert payload["workspace"]["improvement_latitude_source"] == "product-default"
    assert payload["workspace"]["optimization_bias"] == "balanced"
    assert payload["workspace"]["optimization_bias_source"] == "product-default"
    assert payload["workspace"]["advanced_features"] == []
    assert payload["workspace"]["advanced_features_source"] == "product-default"
    assert payload["workspace"]["supported_advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["workflow_artifact_adapter"]["canonical_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/",
    ]
    assert payload["workspace"]["agent_configuration_substrate"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["workspace"]["agent_configuration_substrate"]["owner_surface"] == ".agentic-workspace/config.toml"
    assert payload["workspace"]["workflow_obligations"] == []
    assert payload["config_enforcement"]["field_count_by_class"]["hard"] >= 1
    assert any(field["field"] == "workspace.improvement_latitude" for field in payload["config_enforcement"]["fields"])
    assert payload["update"]["wrapper_rule"] == "normal update execution stays behind agentic-workspace"
    assert {item["module"] for item in payload["update"]["modules"]} == {"planning", "memory"}
    assert {item["freshness"]["status"] for item in payload["update"]["modules"]} == {"unknown"}
    assert payload["assurance"]["default_level"] == "low"
    assert payload["assurance"]["default_level_source"] == "product-default"
    assert payload["assurance"]["onboarding"]["status"] == "absent"
    assert payload["assurance"]["onboarding"]["configured_profile_count"] == 0
    assert payload["mixed_agent"]["status"] == "reporting-only"
    assert payload["mixed_agent"]["repo_policy"]["source"] == "product-defaults"
    assert payload["mixed_agent"]["repo_policy"]["path"] == ".agentic-workspace/config.toml"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is False
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["exists"] is False
    assert payload["mixed_agent"]["local_override"]["applied"] is False
    assert payload["mixed_agent"]["local_integration_area"] == {
        "root": ".agentic-workspace/local/integrations",
        "subfolder_convention": "<vendor-or-runtime>/",
        "example_subfolder": ".agentic-workspace/local/integrations/codex",
        "scratch": {
            "root": ".agentic-workspace/local/scratch",
            "status": "ready-local-only",
            "exists": False,
            "git_ignored": True,
            "authoritative": False,
            "safe_to_delete": True,
            "sign": "Go ahead and use this for whatever temporary working files you need.",
        },
        "status": "available-local-only",
        "exists": False,
        "authoritative": False,
        "git_ignored": True,
        "canonical_doc": ".agentic-workspace/docs/local-integration-area.md",
        "runtime_artifact_shim_pattern": {
            "kind": "agentic-workspace/local-runtime-artifact-shim/v1",
            "root": ".agentic-workspace/local/integrations",
            "status": "local-only-pattern",
            "authoritative": False,
            "git_ignored": True,
            "use_for": [
                "internal agent plans that need compact checked-in planning updates",
                "runtime check bundles that need compact pass/fail plus inspectable logs",
                "handoff or resume state that needs a bounded workspace continuation record",
                "runtime-native planning systems that the agent is already optimized or hardwired to use",
            ],
            "bridge_rule": (
                "Use runtime-native plans as private working memory when they help, but bridge decisions, scope, proof, "
                "and continuation into checked-in Agentic Workspace Planning before implementation handoff or closeout."
            ),
            "preferred_bridge_steps": [
                "capture the runtime-native plan or todo list under the local integration area when it is useful evidence",
                "summarize only durable intent, scope, proof, and next action into checked-in planning state",
                "run agentic-workspace summary --format json after the bridge and resolve warnings before implementation",
            ],
            "artifact_classes": ["internal-plan", "check-bundle", "handoff-state", "runtime-export"],
            "metadata_required": [
                "kind",
                "source_runtime",
                "artifact_class",
                "input_owner",
                "output_target",
                "authority",
                "promotion_target",
                "proof_command",
                "created_at",
            ],
            "compact_output": "short agent-facing status, next action, and proof pointer",
            "full_evidence": "inspectable local artifact, manifest, command log, or exported source file",
            "promotion_boundary": [
                "local shims never become shared authority by existing locally",
                "promote only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces",
                "record proof before treating shim output as repo-shared state",
                "a runtime-native plan or todo list does not satisfy required Agentic Workspace Planning until bridged",
            ],
            "discovery": [
                "agentic-workspace defaults --section agent_aid_storage --format json",
                "agentic-workspace config --target ./repo --profile compact --format json",
                "agentic-workspace report --target ./repo --section agent_aids --format json",
            ],
        },
        "allowed_aid_kinds": [
            "prompt helpers",
            "export/import shims",
            "local wrappers",
            "native-workflow adapters",
            "resumable handoff helpers",
            "runtime scratch files",
        ],
        "boundary_rules": [
            "local-only and ignored by git",
            "optional for ordinary workspace commands",
            "non-authoritative for planning, memory, startup, review, and workflow state",
            "safe to delete without changing repo-owned shared behavior",
            "not a plugin registry or shared compatibility framework",
        ],
        "rule": "local-only vendor/runtime aids; may reduce local operating cost, but must not become shared workflow authority",
    }
    assert payload["mixed_agent"]["local_scratch"] == {
        "root": ".agentic-workspace/local/scratch",
        "status": "ready-local-only",
        "exists": False,
        "git_ignored": True,
        "authoritative": False,
        "safe_to_delete": True,
        "sign": "Go ahead and use this for whatever temporary working files you need.",
    }
    agent_aids = payload["mixed_agent"]["agent_aid_storage"]
    assert agent_aids["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    assert agent_aids["candidate_root"] == ".agentic-workspace/agent-aids"
    assert agent_aids["candidate_subdirs"] == [
        "scripts",
        "skills",
        "runbooks",
        "prompts",
        "checks",
        "templates",
        "module-components",
    ]
    assert [entry["class"] for entry in agent_aids["storage_classes"][:3]] == [
        "local-only",
        "checked-in-candidate",
        "promoted-repo-native",
    ]
    assert payload["mixed_agent"]["local_memory"]["status"] == "disabled"
    assert payload["mixed_agent"]["local_memory"]["path"] == ".agentic-workspace/local/memory.toml"
    assert payload["mixed_agent"]["local_memory"]["authoritative"] is False
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["runtime_inference"]["reported_here"] is False
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["delegated_run_guardrail"]["status"] == "present"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == []
    assert payload["mixed_agent"]["success_measures"] == [
        "lower long-run token cost",
        "lower restart and handoff cost",
        "cheap switching across agents and subscriptions",
        "persisted shared knowledge beats rediscovery",
    ]


def test_config_command_reports_compact_profile_for_agent_startup(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workspace]
improvement_latitude = "proactive"
optimization_bias = "agent-efficiency"

[workflow_obligations.closeout_proof]
summary = "Run closeout proof before reporting done."
stage = "closeout"
scope_tags = ["closeout"]
commands = ["make check"]
""".strip(),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace/config.local.toml",
        """
schema_version = 1

[delegation]
mode = "suggest"

[clarification]
mode = "ask-first"

[safety]
safe_to_auto_run_commands = false
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--profile", "compact", "--format", "json"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["kind"] == "agentic-workspace/config-compact/v1"
    assert payload["profile"] == "compact"
    assert "mixed_agent" not in payload
    assert payload["workspace"]["improvement_latitude"] == "proactive"
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["workflow_obligations"][0]["id"] == "closeout_proof"
    assert payload["local_runtime"]["delegation_mode"] == {"value": "suggest", "source": "local-override"}
    assert payload["local_runtime"]["clarification_mode"] == {"value": "ask-first", "source": "local-override"}
    assert payload["local_runtime"]["safe_to_auto_run_commands"] == {"value": False, "source": "local-override"}
    assert payload["edit_reference"]["check_command"] == "agentic-workspace config --target . --profile compact --format json"
    assert payload["full_profile_command"] == "agentic-workspace config --target . --profile full --format json"
    assert len(output) < 10000


def test_config_command_accepts_reporting_improvement_latitude_mode(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["improvement_latitude"] == "reporting"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_accepts_agent_efficiency_optimization_bias(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["optimization_bias"] == "agent-efficiency"
    assert payload["workspace"]["optimization_bias_source"] == "repo-config"


def test_config_command_reports_assurance_onboarding_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
""",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    partial = json.loads(capsys.readouterr().out)
    assert partial["assurance"]["onboarding"]["status"] == "partial"
    assert partial["assurance"]["onboarding"]["configured_profile_count"] == 0

    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
decision_record_target = "docs/decisions/"

[assurance.proof_profiles.security]
required_commands = ["uv run pytest tests/security -q"]
optional_commands = []
review_aids = []
""",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    usable = json.loads(capsys.readouterr().out)
    assert usable["assurance"]["onboarding"]["status"] == "usable"
    assert usable["assurance"]["onboarding"]["configured_profile_count"] == 1
    assert usable["assurance"]["onboarding"]["host_ref_count"] == 1


def test_config_command_reports_enabled_advanced_features(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nadvanced_features = ["review_artifacts", "external_adapters"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["advanced_features"] == ["review_artifacts", "external_adapters"]
    assert payload["workspace"]["advanced_features_source"] == "repo-config"


def test_config_command_reports_workflow_obligations_from_repo_config(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workflow_obligations.adapter_surface_refresh]\n"
        'summary = "Refresh adapter surfaces."\n'
        'stage = "before-claiming-completion"\n'
        'scope_tags = ["workspace", "adapter-surfaces"]\n'
        'commands = ["make maintainer-surfaces"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["workflow_obligations"][0]["id"] == "adapter_surface_refresh"
    assert payload["workspace"]["workflow_obligations"][0]["stage"] == "before-claiming-completion"
    assert payload["workspace"]["workflow_obligations"][0]["commands"] == ["make maintainer-surfaces"]


def test_config_command_reports_system_intent_source_declaration(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[system_intent]\n"
        'sources = ["SYSTEM_INTENT.md", "docs/product-direction.md"]\n'
        'preferred_source = "docs/product-direction.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["SYSTEM_INTENT.md", "docs/product-direction.md"]
    assert payload["workspace"]["system_intent"]["preferred_source"] == "docs/product-direction.md"
    assert payload["workspace"]["system_intent"]["mirror_path"] == ".agentic-workspace/system-intent/intent.toml"


def test_config_command_warns_about_unsupported_top_level_repo_config_fields(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\nunsupported_top_level = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["warnings"] == [".agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level."]


def test_config_command_autodetects_conservative_system_intent_sources_when_no_explicit_source_declared(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# README\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Repo Instructions\n", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("Repo direction hint\n", encoding="utf-8")

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["system_intent"]["sources"] == ["README.md", "AGENTS.md", "llms.txt"]
    assert payload["workspace"]["system_intent"]["sources_source"] == "autodetected-existing"
    assert payload["workspace"]["system_intent"]["preferred_source"] == "README.md"


def test_config_command_autodetects_existing_supported_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Gemini\n")

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["GEMINI.md"]


def test_config_command_autodetects_claude_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "CLAUDE.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["CLAUDE.md"]


def test_config_command_autodetects_legacy_cursor_rules_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".cursorrules").write_text("Use repo conventions.\n", encoding="utf-8")

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == ".cursorrules"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == [".cursorrules"]


def test_config_command_accepts_custom_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "docs/agent-instructions.md"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "docs/agent-instructions.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"


def test_config_command_discovers_workspace_root_from_subdirectory(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "balanced"\n',
        encoding="utf-8",
    )
    nested = tmp_path / "src" / "agentic_workspace"
    nested.mkdir(parents=True)
    previous_cwd = Path.cwd()
    monkeypatch.chdir(nested)
    try:
        assert cli.main(["config", "--format", "json"]) == 0
    finally:
        monkeypatch.chdir(previous_cwd)

    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == tmp_path.as_posix()
    assert payload["config_path"] == (tmp_path / ".agentic-workspace/config.toml").as_posix()
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"


def test_config_command_surfaces_unknown_local_override_fields_as_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            (
                "schema_version = 1",
                "",
                "[runtime]",
                "supports_internal_delegation = true",
                "mystery_flag = true",
                "",
                "[delegation_targets.gpt_5_4_mini]",
                'strength = "weak"',
                'location = "either"',
                'execution_methods = ["internal"]',
                'unexpected = "note"',
            )
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["warnings"] == [
        ".agentic-workspace/config.local.toml [runtime] contains unsupported field(s): mystery_flag.",
        ".agentic-workspace/config.local.toml delegation_targets.gpt_5_4_mini contains unsupported field(s): unexpected.",
    ]


def test_defaults_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "validation", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "validation"}
    assert payload["matched"] is True
    assert payload["answer"]["rule"] == "Run the narrowest proving lane that matches the touched surface."
    assert payload["answer"]["construction_boundary"]["route_repeated_repair_to"][:3] == [
        "scaffold",
        "writer_helper",
        "alias",
    ]
    assert "confirm correct construction" in payload["answer"]["construction_boundary"]["rule"]
    assert ".agentic-workspace/docs/compact-contract-profile.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_intent_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "intent"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["answer"]["command"] == "agentic-workspace defaults --section intent --format json"
    assert payload["answer"]["rule"] == "Confirmed intent stays human-owned; interpreted intent must remain visibly inferred."
    assert payload["answer"]["confirmed_intent"]["summary"] == "the human-owned request before workspace normalization"
    assert payload["answer"]["interpreted_intent"]["summary"] == "the workspace-normalized request carried forward by lifecycle commands"
    assert ".agentic-workspace/docs/compact-contract-profile.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_agent_aid_storage_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "agent_aid_storage", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "agent_aid_storage"}
    assert payload["matched"] is True
    assert payload["answer"]["command"] == "agentic-workspace defaults --section agent_aid_storage --format json"
    assert payload["answer"]["discovery_command"] == "agentic-workspace report --target ./repo --section agent_aids --format json"
    assert payload["answer"]["task_recommendation_command"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    assert payload["answer"]["candidate_root"] == ".agentic-workspace/agent-aids"
    assert payload["answer"]["ordinary_startup"] is False
    assert payload["answer"]["manifest_check"] == "python scripts/check/check_agent_aids.py"
    affordance = payload["answer"]["creation_affordance"]
    assert affordance["kind"] == "agentic-workspace/agent-created-aid-affordance/v1"
    assert affordance["agent_may_create"] is True
    assert "parsing cost" in affordance["summary"]
    assert "compact-command-runner" in affordance["aid_types"]
    assert affordance["storage_decision"]["checked_in_candidate"] == ".agentic-workspace/agent-aids"
    assert "any agent working in this repo" in affordance["storage_decision"]["prefer_checked_in_when"][0]
    assert "credential" in affordance["storage_decision"]["prefer_local_only_when"][0]
    assert affordance["storage_decision"]["runtime_artifact_shims"]["compact_output"].startswith("short agent-facing")
    assert "silently become required workflow" in affordance["authority_boundary"][0]
    assert affordance["evidence_shape"]["full_evidence"] == "inspectable command log, artifact, manifest, or source file"
    assert affordance["first_pattern"]["command"] == "uv run python scripts/check/run_compact_command.py"
    assert "outer tool timeout" in affordance["first_pattern"]["timeout_rule"]
    assert affordance["first_pattern"]["success_output"] == "[ok] <label> (<duration>)"
    assert payload["answer"]["executable_safety"]["executable_types"] == ["script", "check"]
    assert payload["answer"]["executable_safety"]["candidate_aid_check"] == "python scripts/check/check_agent_aids.py"
    assert payload["answer"]["executable_safety"]["candidate_aids_are_not"] == [
        "canonical proof routes",
        "required workflow entrypoints",
    ]
    assert payload["answer"]["executable_safety"]["platform_specific_checked_in_requires"] == "checked_in_scope_justification"
    assert payload["answer"]["promotion_model"]["target_kinds"] == [
        "command",
        "check",
        "skill",
        "runbook",
        "prompt",
        "template",
        "module-component",
        "docs-contract",
    ]
    assert payload["answer"]["promotion_model"]["portable_repo_general_rule"].endswith("must be cross-platform.")
    assert [entry["class"] for entry in payload["answer"]["storage_classes"]] == [
        "local-only",
        "checked-in-candidate",
        "promoted-repo-native",
        "package-owned",
        "source-checkout-only",
    ]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_clarification_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "clarification", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "clarification"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["answer"]["command"] == "agentic-workspace defaults --section clarification --format json"
    assert payload["answer"]["mode"] == "minimal-interruption"
    assert payload["answer"]["first_questions"] == [
        "Which surface should change?",
        "What proof would make the change safe?",
        "Does the work belong in planning, memory, or workspace-level docs?",
    ]
    assert ".agentic-workspace/docs/compact-contract-profile.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_prompt_routing_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "prompt_routing", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "prompt_routing"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["answer"]["command"] == "agentic-workspace defaults --section prompt_routing --format json"
    assert payload["answer"]["route_by_class"][0]["class"] == "workspace lifecycle change"
    assert payload["answer"]["route_by_class"][0]["proof_lane"] == "workspace_cli"
    assert payload["answer"]["route_by_class"][0]["owner_surface"] == "src/agentic_workspace/cli.py"
    assert payload["answer"]["route_by_class"][2]["proof_lane"] == "memory_payload"
    assert payload["answer"]["route_by_class"][3]["proof_lane"] == "workspace_cli"
    assert payload["answer"]["route_by_class"][3]["broaden_with"] == ["planning_surfaces"]
    assert ".agentic-workspace/docs/compact-contract-profile.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_relay_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "relay", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "relay"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/delegation-posture-contract.md"
    assert payload["answer"]["command"] == "agentic-workspace defaults --section relay --format json"
    assert payload["answer"]["planner_role"]["summary"] == (
        "shape confirmed and interpreted intent, choose the proof lane, and freeze the smallest safe contract."
    )
    assert payload["answer"]["implementer_role"]["summary"] == (
        "execute the narrow contract without widening the requested end state, whether the executor is internal or external."
    )
    assert payload["answer"]["memory_bridge"]["summary"] == (
        "when routed Memory is installed, borrow durable repo understanding before freezing the compact contract."
    )
    assert ".agentic-workspace/docs/delegation-posture-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_improvement_latitude_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "improvement_latitude", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "improvement_latitude"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["answer"]["default_mode"] == "conservative"
    assert payload["answer"]["owner_surface"] == "workspace"
    assert payload["answer"]["policy_target"] == "repo-directed-improvement"
    assert payload["answer"]["workspace_self_adaptation"]["status"] == "allowed-with-bounds"
    assert payload["answer"]["friction_response_order"][1]["action"] == "promote-repo-directed-improvement-when-external"
    assert "workspace fit" in payload["answer"]["guardrail_test"]["adapt_when"][0]
    assert "reporting-only" in payload["answer"]["mode_interpretation"]["reporting"]
    assert payload["answer"]["supported_modes"][0]["mode"] == "none"
    assert payload["answer"]["supported_modes"][1]["mode"] == "reporting"
    assert payload["answer"]["supported_modes"][1]["initiative_posture"] == "reporting-only"
    assert payload["answer"]["supported_modes"][4]["mode"] == "proactive"
    assert payload["answer"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
    ]
    assert payload["answer"]["validation_friction"]["status"] == "explicit-contract"
    assert "validation_bounce_reentry" in payload["answer"]["validation_friction"]["subtypes"]
    assert (
        "the improvement changes what counts as success instead of only changing the means"
        in payload["answer"]["decision_test"]["changed_task_when"]
    )
    assert ".agentic-workspace/docs/workspace-config-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_surface_value_guardrail(capsys) -> None:
    assert cli.main(["defaults", "--section", "surface_value_guardrail", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "surface_value_guardrail"}
    assert payload["matched"] is True
    answer = payload["answer"]
    assert answer["owner_surface"] == "workspace"
    assert answer["applies_to"][0] == "checked-in contract or schema surfaces"
    assert answer["preference_order"][:3] == [
        "remove an unnecessary surface",
        "replace or merge with an existing compact surface",
        "compress or background an existing surface",
    ]
    assert answer["authority_classes"][0]["class"] == "authoritative"
    assert "first-line thing to remember" in answer["review_result"]["reject_when"][1]
    assert answer["review_gate"]["answer_field"] == "surface_value_review"
    assert (
        answer["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json"
    )


def test_defaults_section_selector_returns_effective_authority_view(capsys) -> None:
    assert cli.main(["defaults", "--section", "effective_authority", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "effective_authority"}
    assert payload["matched"] is True
    answer = payload["answer"]
    concerns = {entry["concern"]: entry for entry in answer["authority_map"]}
    assert concerns["compiled system intent"]["authority_class"] == "authoritative"
    assert concerns["runtime implementation"]["authority_class"] == "procedural-owned"
    owner_choice = answer["owner_choice_review"]
    concern_classes = {entry["id"]: entry for entry in owner_choice["concern_classes"]}
    assert concern_classes["config_policy"]["owner_surface"] == ".agentic-workspace/config.toml"
    assert concern_classes["generated_adapter_output"]["owner_surface"] == "generated/"
    assert concern_classes["runtime_primitive_implementation"]["authority_class"] == "procedural-owned"
    assert answer["system_intent_embodiment"]["status"] == "needs-review"
    assert answer["provenance"]["contract_inventory"] == "src/agentic_workspace/contracts/contract_inventory.json"
    assert answer["unresolved_gaps"][0]["id"] == "memory-not-installed"
    assert answer["idle_context"][0]["id"] == "no-active-planning-record"


def test_defaults_section_selector_returns_root_cli_authority_audit(capsys) -> None:
    assert cli.main(["defaults", "--section", "root_cli_authority", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "root_cli_authority"}
    answer = payload["answer"]
    assert answer["command"] == "agentic-workspace defaults --section root_cli_authority --format json"
    classes = {item["id"]: item for item in answer["responsibility_classes"]}
    assert classes["runtime-primitives"]["authority_class"] == "allowed-root-runtime"
    assert classes["remaining-interface-authority"]["authority_class"] == "remaining-interface-authority"
    candidates = answer["next_extraction_or_guard_candidates"]
    assert any(candidate["candidate_type"] == "extract-interface-authority" for candidate in candidates)
    assert any(candidate["candidate_type"] == "add-guard-check" for candidate in candidates)
    assert all(candidate["tracking_role"] in {"historical-provenance", "live-owner"} for candidate in candidates)
    assert all(candidate["tracking_role"] != "live-owner" or candidate["tracking_status"] != "closed" for candidate in candidates)
    assert not any(candidate.get("tracking_issue") == "#410" for candidate in candidates)
    assert any(
        candidate["provenance_issue"] == "#410" and candidate["tracking_role"] == "historical-provenance" for candidate in candidates
    )
    assert answer["direct_cli_edit_routing"]["route_to_contract_when"]
    assert answer["direct_cli_edit_routing"]["review_requires"]


def test_defaults_section_selector_returns_optimization_bias_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "optimization_bias", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "optimization_bias"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["answer"]["default_mode"] == "balanced"
    assert payload["answer"]["supported_modes"][0]["mode"] == "agent-efficiency"
    assert payload["answer"]["supported_modes"][1]["mode"] == "balanced"
    assert payload["answer"]["supported_modes"][2]["mode"] == "human-legibility"
    assert "canonical state semantics" in payload["answer"]["must_not_change"]
    assert ".agentic-workspace/docs/workspace-config-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_setup_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "setup", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "setup"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/jumpstart-contract.md"
    assert payload["answer"]["phase"] == "post-bootstrap"
    assert "docs/jumpstart-contract.md" in payload["refs"]
    assert "agentic-workspace setup --target ./repo --format json" in payload["refs"]


def test_defaults_section_selector_returns_agent_configuration_system_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "agent_configuration_system", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "agent_configuration_system"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["answer"]["configuration_classes"][1]["id"] == "workspace_policy"
    assert payload["answer"]["module_attachment_points"][0] == "descriptor lifecycle commands and install detection"
    assert payload["answer"]["adapter_surfaces"][1]["surface"] == "llms.txt"
    assert (
        payload["answer"]["selective_loading"]["first_queries"][0]
        == "agentic-workspace defaults --section agent_configuration_system --format json"
    )
    assert ".agentic-workspace/docs/workspace-config-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_agent_configuration_queries_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "agent_configuration_queries", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "agent_configuration_queries"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["answer"]["query_classes"][1]["id"] == "active_behavior_modules"
    assert payload["answer"]["query_classes"][2]["then_if_needed"][0] == "agentic-workspace defaults --section validation --format json"
    assert payload["answer"]["stop_rule"].startswith("Stop after the first compact answer")
    assert ".agentic-workspace/docs/workspace-config-contract.md" in payload["refs"]


def test_defaults_section_selector_returns_agent_configuration_workflow_extensions_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "agent_configuration_workflow_extensions", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "agent_configuration_workflow_extensions"}
    assert payload["matched"] is True
    assert payload["answer"]["owner_surface"] == ".agentic-workspace/config.toml [workflow_obligations]"
    assert payload["answer"]["definition_format"]["schema_version"] == "agentic-workspace/workflow-definition-format/v1"
    assert payload["answer"]["definition_format"]["primary_component_family"]["id"] == "workflow_obligation"
    assert (
        payload["answer"]["definition_format"]["flexibility_boundary"]["leave_flexible"][0]
        == "local implementation steps inside the bounded component"
    )
    assert payload["answer"]["supported_stages"][0] == "pre-work"
    assert payload["answer"]["consumption_rule"][0].startswith("workspace owns declaration")


def test_defaults_setup_findings_promotion_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "setup_findings_promotion", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "setup_findings_promotion"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/setup-findings-contract.md"
    assert payload["answer"]["primary_router"] == "agentic-workspace defaults --section improvement_intake --format json"
    assert payload["answer"]["artifact_path"] == "tools/setup-findings.json"
    assert payload["answer"]["schema_path"] == "src/agentic_workspace/contracts/schemas/setup_findings.schema.json"
    assert payload["answer"]["accepted_classes"][0]["class"] == "repo_friction_evidence"
    assert "docs/setup-findings-contract.md" in payload["refs"]
    assert "agentic-workspace setup --target ./repo --format json" in payload["refs"]


def test_defaults_improvement_intake_section_selector_returns_unified_router(capsys) -> None:
    assert cli.main(["defaults", "--section", "improvement_intake", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "improvement_intake"}
    assert payload["matched"] is True
    answer = payload["answer"]
    assert answer["canonical_doc"] == "src/agentic_workspace/contracts/improvement_signal_contract.json"
    assert answer["payload"]["kind"] == "workspace-improvement-intake/v1"
    assert answer["payload"]["role"] == "router-not-backlog"
    subtype_ids = {item["id"] for item in answer["payload"]["subtypes"]}
    assert subtype_ids == {
        "setup_finding",
        "review_finding",
        "validation_friction",
        "memory_improvement_signal",
        "repair_recurrence",
    }
    assert answer["payload"]["audience_boundary"]["status"] == "target-repo"
    assert answer["payload"]["source_checkout_only"]["hidden_subtype_count"] == 1
    assert "dogfooding_friction" not in json.dumps(answer["payload"], sort_keys=True)
    review_route = next(item for item in answer["payload"]["subtypes"] if item["id"] == "review_finding")
    assert review_route["advanced_feature"] == "review_artifacts"
    validation_route = next(item for item in answer["payload"]["subtypes"] if item["id"] == "validation_friction")
    assert validation_route["classification"] == (
        "user_or_content_error | environment_or_dependency_error | interface_design_error | unclear_proof_contract"
    )
    assert validation_route["correct_by_design_remedies"][:3] == ["scaffold", "writer_helper", "alias"]
    assert answer["payload"]["signal_contract"]["candidate_kind"] == "workspace-improvement-signal-candidate/v1"
    assert "found" in answer["payload"]["signal_contract"]["closeout_statuses"]
    assert "interface_design_error" in answer["payload"]["signal_contract"]["validation_failure_classes"]
    assert answer["payload"]["signal_contract"]["correct_by_design_review"]["status"] == "required-when-relevant"
    assert "confirm correct construction" in answer["payload"]["signal_contract"]["correct_by_design_review"]["rule"]
    assert "issue follow-up" in answer["payload"]["allowed_destinations"]
    assert answer["payload"]["setup_findings"]["status"] == "not-evaluated"


def test_defaults_improvement_signal_section_selector_returns_signal_contract(capsys) -> None:
    assert cli.main(["defaults", "--section", "improvement_signal", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "improvement_signal"}
    assert payload["matched"] is True
    answer = payload["answer"]
    assert answer["payload"]["candidate_kind"] == "workspace-improvement-signal-candidate/v1"
    assert "workflow_cost" in answer["payload"]["kinds"]
    assert "scaffold" in answer["payload"]["likely_remediations"]
    failure_classes = {item["class"]: item for item in answer["payload"]["validation_failure_classes"]}
    assert failure_classes["interface_design_error"]["preferred_remediations"][:2] == ["scaffold", "writer_helper"]
    assert "proof selection" in failure_classes["unclear_proof_contract"]["route"]
    review = answer["payload"]["correct_by_design_review"]
    assert review["closeout_field"] == "correct_by_design_assessment"
    assert "Validation should confirm correct construction" in review["rule"]
    assert review["preferred_remediation_order"][:3] == ["scaffold", "writer_helper", "alias"]
    assert answer["payload"]["closeout_statuses"] == ["found", "fixed", "routed", "dismissed", "none"]
    assert "A signal is not a work item until an owner and proof path are chosen." in answer["payload"]["guardrails"]


def test_defaults_operating_questions_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "operating_questions", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "operating_questions"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/which-package.md"
    assert payload["answer"]["questions"][0]["id"] == "startup_or_lifecycle_path"
    assert payload["answer"]["questions"][3]["id"] == "proof_or_ownership_answer"
    assert payload["answer"]["questions"][4]["then_if_needed"][0] == "llms.txt"
    assert payload["answer"]["stop_rule"] == ("Do not reopen broader docs once one compact surface has answered the routine question.")
    assert "docs/which-package.md" in payload["refs"]


def test_defaults_install_profiles_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "install_profiles", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "install_profiles"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/which-package.md"
    assert payload["answer"]["default_entrypoint"] == "agentic-workspace"
    assert payload["answer"]["default_answer"].startswith("Start with `memory`")
    assert payload["answer"]["recommendation_order"] == ["memory", "planning", "full"]
    assert payload["answer"]["profiles"][0]["preset"] == "memory"
    assert payload["answer"]["profiles"][2]["preset"] == "full"
    assert payload["answer"]["partial_adoption"][1]["combination"] == "planning only"
    assert payload["answer"]["lightweight_profile"]["preset"] == "memory"
    assert "docs/which-package.md" in payload["refs"]


def test_defaults_system_intent_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "system_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "system_intent"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/system-intent-contract.md"
    assert payload["answer"]["source_declaration_surface"] == ".agentic-workspace/config.toml [system_intent]"
    assert payload["answer"]["mirror_surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert payload["answer"]["sync_behavior"].startswith("Refresh source hints and source-record metadata only")
    assert payload["answer"]["authority_ladder"][1]["layer"] == "delegated judgment and intent continuity"
    assert "agentic-workspace summary --format json" in payload["answer"]["recoverability"]["ask_first"]
    assert ".agentic-workspace/docs/system-intent-contract.md" in payload["refs"]


def test_defaults_durable_intent_section_selector_explains_lifecycle(capsys) -> None:
    assert cli.main(["defaults", "--section", "durable_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "durable_intent"}
    answer = payload["answer"]
    assert answer["intent_scopes"][0]["id"] == "task"
    assert answer["intent_scopes"][1]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert "subsystem-intent" in answer["promotion_choices"]
    assert answer["promotion_rule"].startswith("Promotion from task evidence creates reviewable")


def test_system_intent_command_sync_refreshes_source_metadata_without_mechanical_extraction(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[system_intent]\nsources = ["README.md"]\npreferred_source = "README.md"\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Product Direction\n\nKeep the system quiet.\n", encoding="utf-8")

    assert cli.main(["system-intent", "--target", str(tmp_path), "--sync", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-system-intent/v1"
    assert payload["mirror"]["status"] == "present"
    assert (tmp_path / ".agentic-workspace/system-intent/intent.toml").exists()
    mirror_text = (tmp_path / ".agentic-workspace/system-intent/intent.toml").read_text(encoding="utf-8")
    assert 'preferred_source = "README.md"' in mirror_text
    assert 'summary = ""' in mirror_text
    assert "needs_review = true" in mirror_text
    assert "[[source_records]]" in mirror_text
    assert 'path = "README.md"' in mirror_text
    subsystem_text = (tmp_path / ".agentic-workspace/system-intent/subsystems.toml").read_text(encoding="utf-8")
    assert 'kind = "agentic-workspace/subsystem-intent-set/v1"' in subsystem_text
    assert 'id = "planning"' in subsystem_text
    assert payload["subsystem_intent"]["subsystem_count"] == 2
    assert payload["decision_projection"]["task_intent"]["role"] == "bounded and closable"


def test_system_intent_rejects_invalid_subsystem_intent_lifecycle(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/system-intent").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/system-intent/subsystems.toml").write_text(
        'schema_version = 1\nkind = "agentic-workspace/subsystem-intent-set/v1"\n\n'
        '[[subsystems]]\nid = "ux"\nscope = "frontend"\nstatus = "done"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["system-intent", "--target", str(tmp_path), "--format", "json"])
    assert exc_info.value.code == 2
    assert "status must be one of" in capsys.readouterr().err


def test_system_intent_rejects_subsystem_intent_ids_missing_from_ownership(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
schema_version = 1

[[subsystems]]
id = "planning"
paths = [".agentic-workspace/planning/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "subsystems.toml",
        """
schema_version = 1
kind = "agentic-workspace/subsystem-intent-set/v1"

[[subsystems]]
id = "invented"
scope = "not in ownership"
status = "active"
summary = "This should not create a second subsystem taxonomy."
decision_tests = ["Is this valid?"]
confidence = "low"
needs_review = true
source_records = [{ source_type = "test", ref = "test", summary = "unknown id" }]
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["system-intent", "--target", str(tmp_path), "--format", "json"])
    assert exc_info.value.code == 2
    error = capsys.readouterr().err
    assert "is not declared in .agentic-workspace/OWNERSHIP.toml [[subsystems]]" in error
    assert "planning" in error


def test_start_surfaces_compact_durable_intent_for_task(capsys) -> None:
    assert cli.main(["start", "--target", ".", "--task", "planning closeout should preserve durable intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert payload["durable_intent"]["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert payload["durable_intent"]["subsystem_intent"]["ownership_registry"]["status"] == "present"
    assert any(match["id"] == "planning" for match in payload["durable_intent"]["subsystem_intent"]["matches"])


def test_start_matches_subsystem_intent_through_ownership_paths(capsys) -> None:
    assert (
        cli.main(["start", "--target", ".", "--changed", "packages/planning/src/repo_planning_bootstrap/installer.py", "--format", "json"])
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    matches = payload["durable_intent"]["subsystem_intent"]["matches"]
    planning_match = next(match for match in matches if match["id"] == "planning")
    assert planning_match["match_source"] == "ownership-path"


def test_preflight_surfaces_compact_durable_intent_for_task(capsys) -> None:
    assert cli.main(["preflight", "--target", ".", "--task", "memory routing should preserve durable context", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert any(match["id"] == "memory" for match in payload["durable_intent"]["subsystem_intent"]["matches"])


def test_start_matches_durable_intent_across_decision_pressure_types(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "subsystems.toml",
        """
schema_version = 1
kind = "agentic-workspace/subsystem-intent-set/v1"
rule = "Subsystem intent is durable scoped decision pressure, not active task state by default."

[[subsystems]]
id = "performance"
scope = "runtime memory usage"
status = "active"
summary = "Keep runtime memory usage bounded."
decision_tests = ["Does this preserve memory ceilings?"]
confidence = "high"
needs_review = false

[[subsystems]]
id = "accessibility"
scope = "UX accessibility"
status = "active"
summary = "Interfaces should stay accessible to elderly users."
decision_tests = ["Can low-vision and elderly users complete the flow?"]
confidence = "medium"
needs_review = true

[[subsystems]]
id = "docs"
scope = "documentation philosophy"
status = "active"
summary = "Prefer self-documenting code over external-facing wikis."
decision_tests = ["Is the durable explanation closest to the code?"]
confidence = "medium"
needs_review = false

[[subsystems]]
id = "audit"
scope = "compliance auditability"
status = "active"
summary = "Access logs must remain auditable."
decision_tests = ["Can a reviewer reconstruct access-log decisions?"]
confidence = "high"
needs_review = false
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "improve memory usage, elderly user accessibility, self-documenting code, and audit logs",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    matches = {match["id"] for match in payload["durable_intent"]["subsystem_intent"]["matches"]}
    assert {"performance", "accessibility"} <= matches
    assert payload["durable_intent"]["subsystem_intent"]["matched_count"] == 4


def test_report_durable_intent_section_returns_compact_projection(capsys) -> None:
    assert cli.main(["report", "--target", ".", "--section", "durable_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["selector"] == {"section": "durable_intent"}
    answer = payload["answer"]
    assert answer["rule"].startswith("Use durable intent as decision pressure")
    assert answer["system_intent"]["surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert answer["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"


def test_setup_command_reports_no_new_seed_surfaces_for_mature_repo(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    (target / "memory").mkdir(exist_ok=True)
    (target / "memory" / "index.md").write_text("# Memory index\n")

    assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-setup/v1"
    assert payload["command"] == "setup"
    assert payload["orientation"]["mode"] == "bounded-orientation-needed"
    assert payload["orientation"]["summary"].lower().startswith("review the strongest current surface candidates")
    assert payload["findings_promotion"]["artifact_path"] == "tools/setup-findings.json"
    assert payload["findings_promotion"]["schema_path"] == "src/agentic_workspace/contracts/schemas/setup_findings.schema.json"
    assert payload["analysis_input"]["status"] == "not-found"
    assert payload["next_action"]["summary"] == "Review the compact report surfaces"
    assert "agentic-workspace report --target ./repo --format json" in payload["next_action"]["commands"]


def test_setup_command_loads_promotable_findings_artifact(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    (target / "memory").mkdir(exist_ok=True)
    _write((target / "memory" / "index.md"), "# Memory index\n")
    (target / "tools").mkdir(exist_ok=True)
    _write(
        (target / "tools" / "setup-findings.json"),
        json.dumps(
            {
                "kind": "workspace-setup-findings/v1",
                "findings": [
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Workspace CLI remains a large shared hotspot.",
                        "confidence": 0.91,
                        "path": "src/agentic_workspace/cli.py",
                        "refs": [".agentic-workspace/docs/reporting-contract.md"],
                    },
                    {
                        "class": "planning_candidate",
                        "summary": "Promote one bounded module-reporting follow-on.",
                        "confidence": 0.83,
                        "next_action": "Promote the next module-reporting slice into .agentic-workspace/planning/state.toml after setup review.",
                    },
                    {
                        "class": "planning_candidate",
                        "summary": "Generic thought with no bounded action.",
                        "confidence": 0.82,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8-sig",
    )

    assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["analysis_input"]["status"] == "loaded"
    assert payload["analysis_input"]["loaded_count"] == 3
    assert payload["analysis_input"]["promotable"]["repo_friction_evidence"][0]["path"] == "src/agentic_workspace/cli.py"
    assert payload["analysis_input"]["promotable"]["planning_candidate"][0]["next_action"].startswith("Promote the next")
    assert payload["analysis_input"]["transient"][0]["promotion_reason"] == "planning candidate needs a bounded next_action"
    assert payload["next_action"]["summary"] == "Review promotable setup findings before seeding or promoting anything durable"
    assert payload["next_action"]["commands"] == [
        "agentic-workspace setup --target ./repo --format json",
        "agentic-workspace report --target ./repo --format json",
    ]


def test_defaults_delegation_posture_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "delegation_posture", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "delegation_posture"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/delegation-posture-contract.md"
    assert payload["answer"]["preferred_split"] == ["planner", "implementer", "validator"]
    assert ".agentic-workspace/docs/delegation-posture-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_proof_command_reports_routes_and_current_health(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["default_routes"]["planning_surfaces"] == "agentic-workspace doctor --target ./repo --modules planning --format json"
    assert payload["current"]["installed_modules"] == ["planning"]
    assert payload["current"]["status_health"] == "healthy"
    assert payload["current"]["doctor_health"] == "healthy"
    assert payload["current"]["warnings"] == []
    assert payload["current"]["needs_review"] == []
    assert calls == []


def test_proof_route_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["matched"] is True
    assert payload["answer"] == {
        "id": "workspace_proof",
        "command": "agentic-workspace proof --target ./repo --format json",
    }
    assert payload["target"] == tmp_path.as_posix()


def test_proof_current_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"current": True}
    assert payload["answer"]["installed_modules"] == ["planning"]
    assert payload["answer"]["status_health"] == "healthy"


def test_proof_route_selector_smoke_works_without_mocked_lifecycle(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
    capsys.readouterr()

    assert cli.main(["proof", "--target", str(target), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["answer"]["id"] == "workspace_proof"
    assert payload["answer"]["command"] == "agentic-workspace proof --target ./repo --format json"


def test_ownership_command_reports_authority_map(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[ownership_classes.repo_owned]\n"
        'summary = "repo-owned"\n\n'
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n\n'
        "[[managed_surfaces]]\n"
        'module = "workspace"\n'
        'path = ".agentic-workspace/OWNERSHIP.toml"\n'
        'kind = "ownership-ledger"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-if-owned"\n\n'
        "[[fences]]\n"
        'name = "workspace-workflow-pointer"\n'
        'module = "workspace"\n'
        'file = "AGENTS.md"\n'
        'start = "<!-- agentic-workspace:workflow:start -->"\n'
        'end = "<!-- agentic-workspace:workflow:end -->"\n'
        'ownership = "managed_fence"\n'
        'uninstall_policy = "remove-fence-only"\n\n'
        "[[authority_surfaces]]\n"
        'concern = "active-execution-state"\n'
        'surface = ".agentic-workspace/planning/state.toml"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "current work"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/ownership-authority-contract.md"
    assert payload["ledger_path"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["authority_surfaces"][0]["concern"] == "active-execution-state"
    assert payload["authority_surfaces"][0]["surface"] == ".agentic-workspace/planning/state.toml"
    assert any(entry["surface"] == ".agentic-workspace/planning/" for entry in payload["boundary_review"]["package_owned"]["module_roots"])
    assert any(
        entry["surface"] == ".agentic-workspace/OWNERSHIP.toml" for entry in payload["boundary_review"]["package_owned"]["managed_surfaces"]
    )
    assert len(payload["boundary_review"]["repo_owned"]["authority_surfaces"]) == 1
    assert payload["boundary_review"]["middle_ground"]["managed_fences"][0]["surface"] == "AGENTS.md#agentic-workspace:workflow"
    assert payload["boundary_review"]["smallest_explicit_repo_hook"]["surface"] == "AGENTS.md#agentic-workspace:workflow"
    assert payload["warnings"] == []


def test_ownership_real_init_does_not_settle_repo_root_memory_as_repo_owned_contract(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["ownership", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any(
        entry["surface"] == ".agentic-workspace/memory/" and entry["owner"] == "memory" and entry["ownership"] == "module_managed"
        for entry in payload["authority_surfaces"]
    )
    assert not any(entry["surface"] == "memory/" for entry in payload["authority_surfaces"])
    assert not any(entry["surface"] == "memory/" for entry in payload["boundary_review"]["repo_owned"]["authority_surfaces"])
    assert payload["boundary_review"]["smallest_explicit_repo_hook"]["surface"] == "AGENTS.md#agentic-workspace:workflow"


def test_ownership_diagnostics_report_startup_adapter_drift_and_ambiguity(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
    capsys.readouterr()
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8")
        + "\n\nAuthoritative source of truth for this sprint.\nCurrent task handoff: continue the checkout redesign.\n",
        encoding="utf-8",
    )
    _write(target / "llms.txt", "Authoritative source of truth for external agents.\n", encoding="utf-8")

    assert cli.main(["ownership", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    diagnostics = payload["diagnostics"]
    assert diagnostics["status"] == "attention-needed"
    findings = {finding["id"]: finding for finding in diagnostics["findings"]}
    assert findings["startup-adapter-active-state"]["concern"] == "active execution state"
    assert findings["startup-adapter-active-state"]["suspected_drift_surface"] == "AGENTS.md"
    assert findings["startup-authority-ambiguous"]["status"] == "ambiguous-owner"
    assert set(findings["startup-authority-ambiguous"]["claimed_by"]) >= {"AGENTS.md", "llms.txt"}


def test_report_surfaces_config_ownership_drift_diagnostic(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ndefault_preset = "planning"\ncurrent_task = "handoff detail"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "ownership_diagnostics", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    findings = {finding["id"]: finding for finding in payload["answer"]["findings"]}
    assert findings["config-active-state"]["concern"] == "active execution state"
    assert findings["config-active-state"]["suspected_drift_surface"] == ".agentic-workspace/config.toml"


def test_ownership_diagnostics_report_missing_config_owner(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n", encoding="utf-8")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    findings = {finding["id"]: finding for finding in payload["diagnostics"]["findings"]}
    assert findings["workspace-policy-missing-owner"]["status"] == "missing-owner"
    assert findings["workspace-policy-missing-owner"]["expected_primary_owner"] == ".agentic-workspace/config.toml"


def test_ownership_concern_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "active-execution-state"\n'
        'surface = ".agentic-workspace/planning/state.toml"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "current work"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--concern", "active-execution-state", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "ownership"
    assert payload["selector"] == {"concern": "active-execution-state"}
    assert payload["matched"] is True
    assert payload["answer"]["surface"] == ".agentic-workspace/planning/state.toml"
    assert payload["answer"]["owner"] == "repo"


def test_ownership_path_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert (
        cli.main(
            [
                "ownership",
                "--target",
                str(tmp_path),
                "--path",
                ".agentic-workspace/planning/agent-manifest.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"path": ".agentic-workspace/planning/agent-manifest.json"}
    assert payload["matched"] is True
    assert payload["answer"]["owner"] == "planning"
    assert payload["answer"]["matched_by"] == "module_root"


def test_ownership_path_selector_includes_host_repo_subsystems(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[subsystems]]\n"
        'id = "payments"\n'
        'paths = ["src/payments/**"]\n'
        'owns = ["payment orchestration"]\n'
        'does_not_own = ["catalog pricing"]\n'
        'proof = ["npm test -- payments"]\n'
        'escalate_when = ["payment provider contract changes"]\n\n'
        "[[subsystems]]\n"
        'id = "payments-api"\n'
        'paths = ["src/payments/api/**"]\n'
        'owns = ["payment API handlers"]\n'
        'proof = ["npm test -- payments-api"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--path", "src/payments/api/refund.ts", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["matched"] is True
    answer = payload["answer"]
    assert answer["matched_by"] == "subsystem"
    assert answer["primary_subsystem"]["id"] == "payments-api"
    assert answer["subsystem_overlap_count"] == 2
    assert answer["subsystems"][1]["id"] == "payments"
    assert answer["subsystems"][1]["does_not_own"] == ["catalog pricing"]


def test_proof_changed_paths_include_subsystem_proof_hints(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[subsystems]]\n"
        'id = "workspace-cli"\n'
        'paths = ["src/agentic_workspace/cli.py"]\n'
        'owns = ["workspace command routing"]\n'
        'does_not_own = ["planning state semantics"]\n'
        'proof = ["uv run pytest tests/test_workspace_cli.py -q"]\n'
        'escalate_when = ["public command contract changes"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["selector"] == {"changed": ["src/agentic_workspace/cli.py"]}
    answer = payload["answer"]
    assert "uv run pytest tests/test_workspace_cli.py -q" in answer["required_commands"]
    subsystem_lanes = [lane for lane in answer["selected_lanes"] if lane["id"] == "subsystem:workspace-cli"]
    assert subsystem_lanes
    assert subsystem_lanes[0]["subsystem"]["does_not_own"] == ["planning state semantics"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["matched_paths"] == ["src/agentic_workspace/cli.py"]


def test_config_command_reports_repo_owned_overrides(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n'
        'agent_instructions_file = "GEMINI.md"\n'
        'workflow_artifact_profile = "gemini"\n'
        'improvement_latitude = "balanced"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is True
    assert payload["workspace"]["default_preset"] == "planning"
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_profile"] == "gemini"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "repo-config"
    assert payload["workspace"]["improvement_latitude"] == "balanced"
    assert payload["workspace"]["improvement_latitude_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_adapter"]["native_artifacts"] == [
        "implementation_plan.md",
        "task.md",
        "walkthrough.md",
    ]
    planning_policy = next(item for item in payload["update"]["modules"] if item["module"] == "planning")
    assert planning_policy["source"] == "repo-config"
    assert planning_policy["source_ref"] == "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"
    assert planning_policy["source_label"] == "planning feature ref"
    assert planning_policy["recommended_upgrade_after_days"] == 14
    assert payload["mixed_agent"]["repo_policy"]["source"] == "repo-config"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is True


def test_config_command_reports_reserved_local_override_presence_without_applying_it(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n[runtime]\nsupports_internal_delegation = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["local_override"]["applied"] is True
    assert payload["mixed_agent"]["local_override"]["status"] == "applied"
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_reports_local_only_memory_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["mixed_agent"]["local_memory"]
    assert local_memory["status"] == "enabled"
    assert local_memory["enabled"] is True
    assert local_memory["configured"] is True
    assert local_memory["path"] == ".agentic-workspace/local/memory.toml"
    assert local_memory["controlled_by"] == ".agentic-workspace/config.local.toml"
    assert local_memory["authoritative"] is False
    assert local_memory["advisory_only"] is True
    assert "not a secret store" in local_memory["boundary_rules"]


def test_config_command_reports_narrow_local_override_fields_with_source_attribution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[runtime]\n"
        "supports_internal_delegation = true\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = true\n\n"
        "[handoff]\n"
        "prefer_internal_delegation_when_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["prefer_internal_delegation_when_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["derived_mode"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert payload["mixed_agent"]["derived_mode"]["handoff_preference"] == "prefer-internal-when-safe"


def test_config_command_reports_local_delegation_target_profiles(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.fast_docs]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.58\n"
        'task_fit = ["bounded-docs", "narrow-tests"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n\n'
        "[delegation_targets.primary_planner]\n"
        'strength = "strong"\n'
        'location = "local"\n'
        "confidence = 0.92\n"
        'model_family = "gpt-5.5"\n'
        'provider = "openai"\n'
        'context_capacity = "large"\n'
        'reasoning_profile = "strong"\n'
        'cost_class = "premium"\n'
        'latency_class = "slow"\n'
        'capability_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'safe_task_classes = ["boundary-shaping", "reasoning-heavy"]\n'
        'forbidden_task_classes = ["mechanical-follow-through"]\n'
        'escalation_target = "human"\n'
        'confidence_source = "local-evaluation"\n'
        'last_evaluation = "2026-05-04"\n'
        'human_control_modes = ["manual", "suggest"]\n'
        'execution_methods = ["internal", "api"]\n',
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["status"] == "configured"
    fast_docs = next(item for item in targets["profiles"] if item["name"] == "fast_docs")
    assert fast_docs["strength"] == "weak"
    assert fast_docs["location"] == "external"
    assert fast_docs["confidence"] == 0.58
    assert fast_docs["task_fit"] == ["bounded-docs", "narrow-tests"]
    assert fast_docs["capability_classes"] == ["mechanical-follow-through"]
    assert fast_docs["execution_methods"] == ["cli"]
    assert fast_docs["advisory"] == {
        "handoff_detail": "high",
        "review_burden": "high",
    }
    assert fast_docs["closeout_gate"]["trust"] == "lower-trust"
    assert "target strength is weak" in fast_docs["closeout_gate"]["reasons"]
    planner = next(item for item in targets["profiles"] if item["name"] == "primary_planner")
    assert planner["location"] == "local"
    assert planner["model_family"] == "gpt-5.5"
    assert planner["provider"] == "openai"
    assert planner["context_capacity"] == "large"
    assert planner["reasoning_profile"] == "strong"
    assert planner["cost_class"] == "premium"
    assert planner["latency_class"] == "slow"
    assert planner["capability_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["safe_task_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["forbidden_task_classes"] == ["mechanical-follow-through"]
    assert planner["escalation_target"] == "human"
    assert planner["confidence_source"] == "local-evaluation"
    assert planner["last_evaluation"] == "2026-05-04"
    assert planner["human_control_modes"] == ["manual", "suggest"]
    assert planner["execution_methods"] == ["internal", "api"]
    assert planner["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }
    assert planner["closeout_gate"]["trust"] == "normal"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == ["fast_docs"]
    posture_effect = payload["mixed_agent"]["delegated_run_guardrail"]["local_posture_effect"]
    assert posture_effect["status"] == "configured"
    assert posture_effect["configured_profiles"] == ["fast_docs", "primary_planner"]
    assert posture_effect["proof_burden"].startswith("lower-trust profiles require")


def test_config_command_rejects_invalid_local_target_reasoning_profile(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.worker]",
                'strength = "weak"',
                'execution_methods = ["cli"]',
                'reasoning_profile = "omniscient"',
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--target", str(target), "--format", "json"])
    assert "reasoning_profile must be one of" in capsys.readouterr().err


def test_config_command_reports_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[delegation_targets.local_worker]",
                'strength = "medium"',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    control = payload["mixed_agent"]["delegation_control"]
    assert control["configured_mode"] == "auto"
    assert control["effective_mode"] == "suggest"
    assert control["execution_permitted"] is False
    assert control["disabled_reason"] == "delegation.mode is auto, but safety.safe_to_auto_run_commands is not true"
    assert payload["mixed_agent"]["effective_posture"]["delegation_mode"] == {
        "value": "auto",
        "source": "local-override",
    }


def test_config_command_rejects_invalid_local_delegation_control_mode(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation]\nmode = "delegate-everything"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--target", str(target), "--format", "json"])
    assert "delegation.mode must be one of" in capsys.readouterr().err


def test_defaults_command_reports_runtime_resolution_policy(capsys) -> None:
    assert cli.main(["defaults", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["rule"].startswith("Query runtime_resolution before delegating")
    assert rr["resolution_categories"] == [
        "stay-local",
        "stronger-reasoning",
        "external-delegation",
        "manual-handoff",
    ]
    assert "execution class" in rr["posture_source_fields"]
    assert "recommended strength" in rr["posture_source_fields"]
    assert "strong external reasoning" in rr["posture_source_fields"]
    assert len(rr["resolution_algorithm"]) >= 4
    assert any("weak target below recommended_strength" in item for item in rr["resolution_algorithm"])
    assert any("strong target above recommended_strength" in item for item in rr["resolution_algorithm"])
    assert rr["confidence_levels"] == ["high", "medium", "low"]
    assert rr["self_assessment"]["authority"] == "advisory-only"
    assert "required_action=escalate-before-execution" in rr["self_assessment"]["cannot_override"]
    packets = payload["mixed_agent"]["capability_handoff_packets"]
    assert "weak_target_escalation" in packets["packet_types"]
    assert "strong_target_downrouting" in packets["packet_types"]
    assert "no_safe_route" in packets["packet_types"]


def test_defaults_command_reports_strong_handoff_packet_template(capsys) -> None:
    assert cli.main(["defaults", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    shp = payload["mixed_agent"]["strong_handoff_packet"]
    assert "manual-handoff" in shp["rule"]
    assert any("context:" in f for f in shp["required_fields"])
    assert any("question:" in f for f in shp["required_fields"])
    assert any("constraints:" in f for f in shp["required_fields"])
    assert any("expected_output:" in f for f in shp["required_fields"])
    assert any("return_to:" in f for f in shp["required_fields"])
    assert "500 tokens" in shp["size_guidance"]
    assert any("manual-handoff" in w for w in shp["when_to_use"])


def test_config_command_reports_runtime_resolution_for_no_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["posture_source"] == "none"
    assert rr["confidence"] in ("high", "medium", "low")
    assert "guidance" in rr
    assert rr["resolution_categories"] == [
        "stay-local",
        "stronger-reasoning",
        "external-delegation",
        "manual-handoff",
    ]


def test_config_command_runtime_resolution_recommends_external_delegation_when_strong_external_preferred(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.9",
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    # Without posture the default resolution is generated; just confirm structure is valid
    rr = payload["mixed_agent"]["runtime_resolution"]
    assert rr["recommendation"] in ("stay-local", "stronger-reasoning", "external-delegation", "manual-handoff")
    assert rr["profile_recommendations"][0]["name"] == "chatgpt"
    assert rr["profile_recommendations"][0]["recommendation"] in ("recommended", "acceptable", "poor-fit")
    assert "strong_handoff_packet" in payload["mixed_agent"]


def test_config_command_runtime_resolution_recommends_stronger_reasoning_for_boundary_shaping_with_strong_planner(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )
    assert rr["recommendation"] == "stronger-reasoning"
    assert rr["confidence"] == "high"
    assert any("boundary-shaping" in r for r in rr["reasons"])
    assert rr["posture_source"] == "provided"


def test_config_command_runtime_resolution_recommends_stay_local_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )
    assert rr["recommendation"] == "stay-local"
    assert rr["confidence"] == "high"
    assert any("mechanical-follow-through" in r for r in rr["reasons"])
    assert rr["weak_target_guardrail"]["status"] == "inactive"
    assert rr["downrouting_guardrail"]["status"] == "inactive"


def test_runtime_resolution_marks_weak_target_escalation_for_boundary_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "boundary-shaping", "recommended strength": "strong"},
    )

    haiku = rr["profile_recommendations"][0]
    assert haiku["name"] == "haiku"
    assert haiku["recommendation"] == "poor-fit"
    assert haiku["capability_mismatch"] is True
    assert haiku["required_action"] == "escalate-before-execution"
    assert rr["weak_target_guardrail"]["status"] == "active"
    assert rr["weak_target_guardrail"]["effective_mode"] == "suggest"
    assert "do not execute the weak target automatically" in rr["weak_target_guardrail"]["mode_action"]
    assert rr["weak_target_guardrail"]["mismatched_targets"][0]["name"] == "haiku"
    assert rr["self_assessment"]["authority"] == "advisory-only"
    assert "capability_mismatch" in rr["self_assessment"]["cannot_override"]


def test_runtime_resolution_marks_strong_target_downrouting_for_mechanical_work(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "suggest"',
                "",
                "[delegation_targets.haiku]",
                'strength = "weak"',
                'location = "external"',
                "confidence = 0.7",
                'task_fit = ["bounded docs edits"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
                "",
                "[delegation_targets.strong_planner]",
                'strength = "strong"',
                'location = "local"',
                "confidence = 0.9",
                'task_fit = ["architecture", "review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mechanical-follow-through"]',
                'execution_methods = ["internal"]',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    strong = next(item for item in rr["profile_recommendations"] if item["name"] == "strong_planner")
    assert strong["required_action"] == "delegate-down-when-safe"
    assert strong["overqualified_for_task"] is True
    assert rr["downrouting_guardrail"]["status"] == "active"
    assert rr["downrouting_guardrail"]["cheaper_fit_targets"][0]["name"] == "haiku"
    assert "cheaper bounded executor" in rr["downrouting_guardrail"]["mode_action"]


def test_runtime_resolution_respects_forbidden_task_classes(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.fast_worker]",
                'strength = "strong"',
                'execution_methods = ["cli"]',
                'capability_classes = ["mechanical-follow-through"]',
                'forbidden_task_classes = ["mechanical-follow-through"]',
                'reasoning_profile = "strong"',
            ]
        ),
        encoding="utf-8",
    )

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"execution class": "mechanical-follow-through", "recommended strength": "weak"},
    )

    worker = rr["profile_recommendations"][0]
    assert worker["recommendation"] == "poor-fit"
    assert worker["capability_mismatch"] is True
    assert worker["required_action"] == "escalate-before-execution"
    assert "target forbids this execution class" in worker["reasons"]


def test_config_command_runtime_resolution_recommends_manual_handoff_when_strong_external_preferred_and_no_external_targets(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    config = cli._load_workspace_config(target_root=target)
    rr = cli._runtime_resolution_payload(
        config=config,
        capability_posture={"strong external reasoning": "preferred"},
    )
    assert rr["recommendation"] == "manual-handoff"
    assert rr["confidence"] == "high"
    assert any("no automated external path" in r for r in rr["reasons"])


def test_config_command_accepts_manual_external_delegation_target(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "AGENTS.md").write_text("repo instructions\n", encoding="utf-8")
    (target / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (target / ".agentic-workspace/config.local.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                "confidence = 0.88",
                'task_fit = ["general-purpose-planning", "cross-cutting-review"]',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]["profiles"]
    chatgpt = next(profile for profile in targets if profile["name"] == "chatgpt")
    assert chatgpt["strength"] == "strong"
    assert chatgpt["location"] == "external"
    assert chatgpt["capability_classes"] == ["boundary-shaping", "reasoning-heavy", "mixed"]
    assert chatgpt["execution_methods"] == ["manual"]
    assert chatgpt["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }


def test_config_command_rejects_invalid_local_delegation_target_strength(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.bad_target]\nstrength = "expert"\nexecution_methods = ["cli"]\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        cli.main(["config", "--target", str(target), "--format", "json"])
    assert "strength must be one of" in capsys.readouterr().err


def test_config_command_accepts_utf8_bom_local_override(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[delegation_targets.fast_docs]\nstrength = "weak"\nexecution_methods = ["cli"]\n',
        encoding="utf-8-sig",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["delegation_targets"]["profiles"][0]["name"] == "fast_docs"


def test_note_delegation_outcome_command_writes_local_artifact(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "note-delegation-outcome",
                "--target",
                str(target),
                "--delegation-target",
                "gpt_5_4_mini",
                "--task-class",
                "bounded-docs",
                "--outcome",
                "success",
                "--handoff-sufficiency",
                "sufficient",
                "--review-burden",
                "light",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["path"] == ".agentic-workspace/delegation-outcomes.json"
    assert payload["record_count"] == 1
    artifact = json.loads((target / ".agentic-workspace/delegation-outcomes.json").read_text(encoding="utf-8"))
    assert artifact["kind"] == "agentic-workspace/delegation-outcomes/v1"
    assert artifact["records"][0]["delegation_target"] == "gpt_5_4_mini"


def test_config_command_reports_delegation_outcome_suggestions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[delegation_targets.gpt_5_4_mini]\n"
        'strength = "weak"\n'
        'location = "external"\n'
        "confidence = 0.62\n"
        'task_fit = ["bounded-docs"]\n'
        'capability_classes = ["mechanical-follow-through"]\n'
        'execution_methods = ["cli"]\n',
        encoding="utf-8",
    )
    (target / ".agentic-workspace/delegation-outcomes.json").write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/delegation-outcomes/v1",
                "records": [
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "bounded-docs",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "normal",
                        "escalation_required": False,
                    },
                    {
                        "recorded_at": "2026-04-17",
                        "delegation_target": "gpt_5_4_mini",
                        "task_class": "narrow-tests",
                        "outcome": "success",
                        "handoff_sufficiency": "sufficient",
                        "review_burden": "light",
                        "escalation_required": False,
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    targets = payload["mixed_agent"]["delegation_targets"]
    assert targets["outcome_artifact"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "status": "configured",
        "record_count": 3,
    }
    mini = targets["profiles"][0]
    assert mini["location"] == "external"
    assert mini["capability_classes"] == ["mechanical-follow-through"]
    assert mini["outcome_evidence"]["record_count"] == 3
    assert mini["outcome_evidence"]["confidence"]["action"] == "raise"
    assert mini["outcome_evidence"]["task_fit"]["suggest_add"] == ["narrow-tests"]


def test_modules_command_reports_installation_state_for_target(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"), "{}\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["modules", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    assert planning_module["installed"] is True
    assert memory_module["installed"] is False


def test_skills_command_lists_registered_workspace_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    skill_ids = {entry["id"] for entry in payload["skills"]}
    assert "workspace-startup" in skill_ids
    assert "workspace-setup-jumpstart" in skill_ids
    assert "planning-autopilot" in skill_ids
    assert "memory-router" in skill_ids
    assert "planning-reporting" in skill_ids
    assert all(entry["registration"] == "explicit" for entry in payload["skills"])
    workspace_startup = next(entry for entry in payload["skills"] if entry["id"] == "workspace-startup")
    assert workspace_startup["source_kind"] == "installed-workspace-skills"
    assert "workspace startup" in workspace_startup["activation_hints"]["phrases"]
    setup_jumpstart = next(entry for entry in payload["skills"] if entry["id"] == "workspace-setup-jumpstart")
    assert setup_jumpstart["source_kind"] == "installed-workspace-skills"
    assert "lived-in repo" in setup_jumpstart["activation_hints"]["phrases"]
    assert "mature repo" in setup_jumpstart["activation_hints"]["nouns"]
    autopilot = next(entry for entry in payload["skills"] if entry["id"] == "planning-autopilot")
    assert "run autopilot" in autopilot["activation_hints"]["phrases"]


def test_skills_command_recommends_matching_agent_aids_without_retired_aids(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    aid_root = target / ".agentic-workspace" / "agent-aids" / "scripts"
    manifest = {
        "kind": "agentic-workspace/agent-aid/v1",
        "id": "workspace-validation-wrapper",
        "type": "script",
        "status": "candidate",
        "scope": "repo-shared",
        "portability": "cross-platform",
        "proof_role": "candidate-aid",
        "owner": "workspace",
        "created_because": "Agents repeatedly need a bounded validation wrapper.",
        "use_when": ["validating workspace CLI and contract changes"],
        "entrypoint": ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
        "safety": {
            "read_only": True,
            "writes_repo": False,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        },
        "validation": {"commands": ["uv run python .agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"]},
        "promotion": {
            "target_kind": "check",
            "target": "scripts/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts",
            "retention_after_promotion": "delete",
        },
        "retirement": {"trigger": "obsolete", "retention_after_retirement": "delete"},
    }
    (aid_root / "workspace-validation" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (aid_root / "old-helper" / "manifest.json").write_text(
        json.dumps({**manifest, "id": "old-helper", "status": "retired"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "validate workspace CLI contracts",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload["agent_aids"]] == ["workspace-validation-wrapper"]
    assert payload["agent_aids"][0]["canonical_proof_route"] is False
    assert payload["agent_aids"][0]["safety_summary"]["read_only"] is True
    assert payload["agent_aid_recommendations"][0]["id"] == "workspace-validation-wrapper"
    assert payload["agent_aid_source"]["section_command"] == ("agentic-workspace report --target ./repo --section agent_aids --format json")


def test_skills_command_recommends_planning_autopilot_for_active_milestone_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "run autopilot and implement the current active milestone from the execplan",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-autopilot"
    assert payload["recommendations"][0]["score"] > 0
    assert any("phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_recommends_planning_reporting_for_setup_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "setup the repo after bootstrap without widening init",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "workspace-setup-jumpstart"
    assert payload["recommendations"][0]["score"] > 10
    assert "workspace setup jumpstart route" in payload["recommendations"][0]["reasons"][0]


def test_skills_command_recommends_setup_jumpstart_for_mature_repo_seeding(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "populate surfaces after newly installed workspace in a lived-in repo",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "workspace-setup-jumpstart"
    assert payload["recommendations"][0]["source_kind"] == "installed-workspace-skills"
    assert "pre-write and pre-seed discovery" in Path("docs/jumpstart-contract.md").read_text(encoding="utf-8")


def test_skills_command_recommends_memory_router_for_note_selection_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "find the smallest memory note set and route memory for this task",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "memory-router"
    assert payload["recommendations"][0]["source_kind"] == "installed-core-skills"


def test_skills_command_recommends_review_skill_for_natural_review_request(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "perform a review of the planning package",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-review-pass"
    assert any("verb match" in reason or "phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_discovers_temporary_memory_bootstrap_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--preset", "memory", "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "finish bootstrap installation review for memory",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    install_skill = next(entry for entry in payload["skills"] if entry["id"] == "install")

    assert install_skill["source_kind"] == "temporary-memory-bootstrap-skills"
    assert install_skill["scope"] == "temporary-bootstrap"
    assert install_skill["path"] == ".agentic-workspace/memory/bootstrap/skills/install/SKILL.md"
    assert payload["recommendations"][0]["id"] == "install"
    assert not payload["warnings"]
    assert any(source["name"] == "memory-bootstrap-temporary" and source["state"] == "registry" for source in payload["sources"])


def test_skills_command_recommends_high_risk_workflow_decision_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    cases = [
        ("large vague feature request classify shape before implementation", "workspace-work-shape"),
        ("decompose an epic into lanes before execplans", "planning-decompose"),
        ("tighten a new execplan before coding", "planning-new-plan-tighten"),
        ("assurance classification and delegation posture before implementation", "planning-assurance-delegation"),
        ("closeout trust and residue distillation after implementation", "planning-closeout-trust"),
    ]
    for task, expected in cases:
        assert cli.main(["skills", "--target", str(target), "--task", task, "--format", "json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["recommendations"], task
        assert payload["recommendations"][0]["id"] == expected


def test_skills_command_recommends_repo_dogfooding_for_skill_optimisation_loop(capsys) -> None:
    assert (
        cli.main(
            [
                "skills",
                "--target",
                ".",
                "--task",
                "run skill optimisation evaluation loops",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"]
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"


def test_skills_command_recommends_self_improvement_for_hyphenated_dogfooding_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "self-improvement-dogfooding",
                    "path": "self-improvement-dogfooding/SKILL.md",
                    "summary": "run bounded repo-local improvement cycles that dogfood package surfaces",
                    "activation_hints": {
                        "verbs": ["continue", "repeat", "improve", "dogfood", "autopilot"],
                        "nouns": ["self-improvement", "dogfooding", "improvement lane", "system intent"],
                        "phrases": ["run self-improvement", "repeat improvement work", "dogfood the package"],
                        "when": ["repo-local improvement loop", "system-intent follow-through"],
                    },
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md", "# Self-improvement\n")

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "create a system-intent review and use it to run self-improvement until findings are addressed",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"
    assert any("phrase match: run self-improvement" in reason for reason in payload["recommendations"][0]["reasons"])
    assert any("noun match" in reason and "self-improvement" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_prioritizes_self_improvement_for_system_wide_improvement_review(
    tmp_path: Path,
    capsys,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "self-improvement-dogfooding",
                    "path": "self-improvement-dogfooding/SKILL.md",
                    "summary": "run bounded repo-local improvement cycles that dogfood package surfaces",
                    "activation_hints": {
                        "nouns": ["self-improvement", "dogfooding", "system intent"],
                    },
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md", "# Self-improvement\n")

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "make a full review of the system as a whole to drive self-improvement",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"
    assert any("id match: self improvement" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_keeps_repo_owned_memory_and_general_skill_sources_distinct(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_json(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-memory-skills",
            "source_kind": "repo-owned-memory-skills",
            "skills": [
                {
                    "id": "package-context-inspection",
                    "path": "package-context-inspection/SKILL.md",
                    "summary": "inspect package context notes",
                },
                {
                    "id": "memory-reporting",
                    "path": "memory-reporting/SKILL.md",
                    "summary": "report memory freshness and cleanup signals",
                },
            ],
        },
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "README.md",
        "# Memory skills\n",
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "package-context-inspection" / "SKILL.md",
        "# Skill\n",
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "memory-reporting" / "SKILL.md",
        "# Skill\n",
    )
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "foundation-stability-check",
                    "path": "foundation-stability-check/SKILL.md",
                    "summary": "recheck operational authority",
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "README.md", "# Tool skills\n")
    _write(target / "tools" / "skills" / "foundation-stability-check" / "SKILL.md", "# Skill\n")

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_skill = next(entry for entry in payload["skills"] if entry["id"] == "package-context-inspection")
    memory_reporting_skill = next(entry for entry in payload["skills"] if entry["id"] == "memory-reporting")
    tool_skill = next(entry for entry in payload["skills"] if entry["id"] == "foundation-stability-check")

    assert memory_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_skill["path"] == ".agentic-workspace/memory/repo/skills/package-context-inspection/SKILL.md"
    assert memory_reporting_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_reporting_skill["path"] == ".agentic-workspace/memory/repo/skills/memory-reporting/SKILL.md"
    assert tool_skill["source_kind"] == "repo-owned-tool-skills"
    assert tool_skill["path"] == "tools/skills/foundation-stability-check/SKILL.md"


def test_init_dispatches_to_full_preset_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "full"
    assert payload["modules"] == ["planning", "memory"]
    assert payload["mode"] == "install"
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_seeds_schema_valid_workspace_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    config_text = config_path.read_text(encoding="utf-8")
    assert config_text.startswith("# Agentic Workspace managed config.\n")
    assert "# Edit this file directly only when changing repo-owned policy." in config_text
    assert "# Reference: .agentic-workspace/docs/workspace-config-contract.md" in config_text
    assert "# Check resolved config: agentic-workspace config --target . --profile compact --format json" in config_text
    assert 'default_preset = "planning"' in config_text
    assert payload["config"]["exists"] is True
    assert payload["config"]["edit_reference"]["reference_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert ".agentic-workspace/config.toml" in payload["created"]


def test_init_dry_run_reports_workspace_config_seed_without_writing(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert not (tmp_path / ".agentic-workspace" / "config.toml").exists()
    assert payload["config"]["exists"] is False
    assert ".agentic-workspace/config.toml" in payload["created"]


def test_init_preserves_existing_workspace_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    config_path = tmp_path / ".agentic-workspace" / "config.toml"
    existing_config = 'schema_version = 1\n\n[workspace]\noptimization_bias = "human-legibility"\n'
    _write(config_path, existing_config, encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert config_path.read_text(encoding="utf-8") == existing_config
    workspace_report = next(report for report in payload["module_reports"] if report["module"] == "workspace")
    config_action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/config.toml")
    assert config_action["kind"] == "current"
    assert "preserved repo-owned policy" in config_action["detail"]


def test_init_uses_default_preset_from_repo_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write(
        (tmp_path / ".agentic-workspace/config.toml"),
        'schema_version = 1\n\n[workspace]\ndefault_preset = "planning"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "planning"
    assert payload["modules"] == ["planning"]
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_uses_explicit_modules_csv(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--modules", "memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["memory"]
    assert calls == [("memory", "install", {"target": str(tmp_path), "dry_run": False, "force": False})]


def test_install_local_only_uses_agentic_workspace_local_only_root_and_updates_git_exclude(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".agentic-workspace" / "local-only"
    assert payload["command"] == "install"
    assert payload["target"] == install_root.as_posix()
    assert (install_root / "AGENTS.md").exists()
    assert (install_root / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (install_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (install_root / ".agentic-workspace" / "local" / "scratch").is_dir()
    assert (install_root / "LOCAL-ONLY.toml").read_text(encoding="utf-8").startswith('schema_version = 1\nmode = "local-only"')
    git_exclude_text = (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".agentic-workspace/" in git_exclude_text
    assert not (repo_root / ".gitignore").exists()
    lifecycle_plan = payload["lifecycle_plan"]
    assert "--local-only" in lifecycle_plan["next_safe_command"]["command"]
    assert lifecycle_plan["mutation_safety"]["local_only_preservation"]["status"] == "explicit-local-only-target"


def test_install_local_only_migrates_legacy_gitignore_residue(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)
    (repo_root / ".gitignore").write_text("# Agentic Workspace local-only storage\n.agentic-workspace/\n")

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".agentic-workspace" / "local-only"
    assert payload["command"] == "install"
    assert payload["target"] == install_root.as_posix()
    assert not (repo_root / ".gitignore").exists()
    assert (install_root / "LOCAL-ONLY.toml").exists()
    assert ".agentic-workspace/" in (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")


def test_uninstall_local_only_removes_agentic_workspace_local_only_root_and_git_exclude(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".agentic-workspace" / "local-only"
    assert payload["command"] == "uninstall"
    assert payload["target"] == install_root.as_posix()
    assert not install_root.exists()
    assert not (install_root / "LOCAL-ONLY.toml").exists()
    assert ".agentic-workspace/" not in (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    lifecycle_plan = payload["lifecycle_plan"]
    assert "--local-only" in lifecycle_plan["next_safe_command"]["command"]
    assert lifecycle_plan["mutation_safety"]["classification"] == "destructive-mutation"


def test_init_reports_required_prompt_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Memory\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        ".agentic-workspace/memory",
        ".agentic-workspace/memory/repo/index.md",
        ".agentic-workspace/planning",
        ".agentic-workspace/planning/execplans",
        "AGENTS.md",
        "TODO.md",
    ]
    assert payload["agent_instructions_file"] == "AGENTS.md"
    assert payload["handoff_prompt_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert "handoff_prompt" in payload
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["confirmed_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["interpreted_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert "must_not_change" in payload["handoff_record"]
    assert "escalate_when" in payload["handoff_record"]
    assert "Intent:" in payload["handoff_prompt"]
    assert "confirmed:" in payload["handoff_prompt"]
    assert "interpreted:" in payload["handoff_prompt"]
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert (tmp_path / "llms.txt").exists()
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_can_write_prompt_file(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    prompt_path = tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--write-prompt", str(prompt_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["handoff_prompt_path"] == prompt_path.as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert prompt_path.exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert "Finish the Agentic Workspace bootstrap" in prompt_path.read_text(encoding="utf-8")


def test_selection_commands_accept_non_interactive_flag() -> None:
    parser = cli.build_parser()

    install_args = parser.parse_args(["install", "--target", ".", "--local-only", "--non-interactive"])
    init_args = parser.parse_args(["init", "--target", ".", "--non-interactive"])
    uninstall_args = parser.parse_args(["uninstall", "--target", ".", "--local-only", "--non-interactive"])
    status_args = parser.parse_args(["status", "--target", ".", "--non-interactive"])
    prompt_args = parser.parse_args(["prompt", "upgrade", "--modules", "planning", "--target", ".", "--non-interactive"])

    assert install_args.local_only is True
    assert init_args.non_interactive is True
    assert uninstall_args.local_only is True
    assert status_args.non_interactive is True
    assert prompt_args.non_interactive is True


def test_prompt_init_uses_dry_run_workspace_bootstrap(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "init"
    assert payload["dry_run"] is True
    assert "handoff_prompt" in payload
    assert "Finish the Agentic Workspace bootstrap" in payload["handoff_prompt"]
    assert "handoff_record" not in payload
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_prompt_init_non_interactive_marks_prompt_free_handoff(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "do not assume a human can answer prompts or unblock a PTY" in payload["handoff_prompt"]


def test_prompt_init_returns_structured_handoff_record_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["prompt_requirement"] != "none"
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["next"]["immediate_brief"] == ".agentic-workspace/bootstrap-handoff.md"


def test_prompt_upgrade_builds_workspace_handoff_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "upgrade"
    assert payload["dry_run"] is True
    assert "Use the workspace CLI as the lifecycle entrypoint" in payload["handoff_prompt"]
    assert "README.md: inspect manually" in payload["handoff_prompt"]


def test_prompt_upgrade_non_interactive_mentions_prompt_free_execution(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "Run this flow with `--non-interactive`" in payload["handoff_prompt"]


def test_init_uses_recommended_prompt_for_single_existing_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["AGENTS.md"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_autodetects_existing_gemini_file_as_startup_entrypoint(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "GEMINI.md"), "# Existing Gemini\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["detected_surfaces"] == ["GEMINI.md"]
    assert "Read `GEMINI.md` first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


def test_init_treats_multiple_supported_startup_files_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "GEMINI.md"), "# Existing Gemini\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "GEMINI.md"]


def test_init_can_create_gemini_startup_file_for_blank_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert (tmp_path / "GEMINI.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert "Read `GEMINI.md` first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


def test_init_dry_run_rewrites_module_startup_actions_for_custom_agent_file(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert (
        cli.main(
            [
                "init",
                "--modules",
                "planning",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "GEMINI.md" in payload["preserved_existing"]
    assert "AGENTS.md" not in payload["preserved_existing"]


def test_init_treats_existing_llms_file_as_existing_workspace_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "llms.txt"), "# External agent handoff\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["llms.txt"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_docs_heavy_repo_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "state.toml"), "# Existing Roadmap\n")
    (tmp_path / "docs" / "maintainer" / "contributor-playbook.md").parent.mkdir(parents=True)
    _write((tmp_path / "docs" / "maintainer" / "contributor-playbook.md"), "# Contributor Playbook\n")
    _write((tmp_path / "docs" / "maintainer" / "maintainer-commands.md"), "# Maintainer Commands\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        ".agentic-workspace/planning",
        ".agentic-workspace/planning/state.toml",
        "AGENTS.md",
        "TODO.md",
        "docs/maintainer/contributor-playbook.md",
    ]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "docs/maintainer/contributor-playbook.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_existing_handoff_plus_workflow_surface_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "AGENTS.md"), "# Existing\n")
    _write((tmp_path / "llms.txt"), "# External agent handoff\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "docs_heavy_existing_repo"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "llms.txt"]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "llms.txt: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_partial_module_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Memory\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        ".agentic-workspace/memory/repo/index.md: partial module state detected",
        ".agentic-workspace/memory: partial module state detected",
        ".agentic-workspace/memory/repo/index.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory: reconcile existing workflow surface ownership",
    ]


def test_init_marks_partial_planning_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        ".agentic-workspace/planning/execplans: partial module state detected",
        ".agentic-workspace/planning: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning/execplans: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_mixed_module_partial_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    _write((tmp_path / "TODO.md"), "# Existing TODO\n")
    (tmp_path / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md"), "# Existing memory index\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        ".agentic-workspace/planning/execplans: partial module state detected",
        ".agentic-workspace/planning: partial module state detected",
        ".agentic-workspace/memory/repo/index.md: partial module state detected",
        ".agentic-workspace/memory: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning/execplans: reconcile existing workflow surface ownership",
        ".agentic-workspace/planning: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory/repo/index.md: reconcile existing workflow surface ownership",
        ".agentic-workspace/memory: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_status_detects_installed_modules_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, calls)
    (tmp_path / "planning").mkdir()
    _write((tmp_path / "TODO.md"), "# TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"), "{}\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: descriptors)

    assert cli.main(["status", "--target", str(tmp_path)]) == 0

    assert calls == [("planning", "status", {"target": str(tmp_path)})]


def test_init_requires_git_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_preset_conflicts_with_modules(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--preset", "planning", "--modules", "planning", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_real_init_creates_combined_memory_and_planning_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()
    assert (target / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
    assert (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    workflow_text = (target / ".agentic-workspace" / "WORKFLOW.md").read_text(encoding="utf-8")
    assert "not task state" in workflow_text
    assert "Do not edit this file to record task-specific" in workflow_text
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in agents_text
    assert 'start --profile tiny --task "<task>"' in agents_text
    assert "agentic-workspace start --format json" not in agents_text
    assert "agentic-workspace preflight --format json" not in agents_text
    assert (
        "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself." not in agents_text
    )
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in agents_text
    assert "## Module Notes" not in agents_text
    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert "<PROJECT_NAME>" not in agents_text


def test_install_real_init_can_use_gemini_as_root_startup_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--agent-instructions-file", "GEMINI.md"]) == 0

    assert (target / "GEMINI.md").exists()
    assert not (target / "AGENTS.md").exists()
    gemini_text = (target / "GEMINI.md").read_text(encoding="utf-8")
    assert 'start --profile tiny --task "<task>"' in gemini_text
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in gemini_text
    assert "Read `GEMINI.md` first." in (target / "llms.txt").read_text(encoding="utf-8")


def test_install_real_init_generates_llms_with_compact_startup_path_first(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    llms_text = (target / "llms.txt").read_text(encoding="utf-8")
    start_index = llms_text.index('agentic-workspace start --profile tiny --task "<task>" --format json')
    preflight_index = llms_text.index("agentic-workspace preflight --format json")
    config_index = llms_text.index("agentic-workspace config --target ./repo --profile compact --format json")
    summary_index = llms_text.index("agentic-workspace summary --format json")
    proof_index = llms_text.index("agentic-workspace proof --profile tiny --changed <paths> --format json")
    raw_index = llms_text.index("Open raw planning or contract files only when compact commands point there.")

    assert "Ordinary path:" in llms_text
    assert "agentic-workspace defaults --section install_profiles --format json" in llms_text
    assert "agentic-workspace install --target ./repo --preset memory" in llms_text
    assert "agentic-workspace install --target ./repo --preset planning" in llms_text
    assert "Use `full` only when both Memory and Planning are explicitly desired." in llms_text
    assert start_index < summary_index < proof_index
    assert proof_index < preflight_index
    assert config_index < raw_index


def test_status_real_init_reports_workspace_shared_layer_surfaces(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(action["path"] == ".agentic-workspace/WORKFLOW.md" and action["kind"] == "current" for action in workspace_report["actions"])
    assert any(
        action["path"] == ".agentic-workspace/OWNERSHIP.toml" and action["kind"] == "current" for action in workspace_report["actions"]
    )


def test_report_real_init_summarizes_combined_workspace_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    _assert_cli_compatibility(payload, status="no-expectation")
    _assert_cli_compatibility_schema(payload, schema_name="workspace_report.schema.json")
    assert payload["kind"] == "workspace-report/v1"
    assert payload["command"] == "report"
    assert payload["schema"]["schema_version"] == "workspace-reporting-schema/v1"
    assert payload["schema"]["command"] == "agentic-workspace report --target ./repo --format json"
    assert "discovery" in payload["schema"]["shared_fields"]
    assert "standing_intent" in payload["schema"]["shared_fields"]
    assert "repo_friction" in payload["schema"]["shared_fields"]
    assert "output_contract" in payload["schema"]["shared_fields"]
    assert "operating_posture" in payload["schema"]["shared_fields"]
    assert "config_enforcement" in payload["schema"]["shared_fields"]
    assert "agent_configuration_queries" in payload["schema"]["shared_fields"]
    assert "system_intent_mirror" in payload["schema"]["shared_fields"]
    assert "workflow_obligations" in payload["schema"]["shared_fields"]
    assert "execution_shape" in payload["schema"]["shared_fields"]
    assert "external_work_delta" in payload["schema"]["shared_fields"]
    assert "module_reports" in payload["schema"]["shared_fields"]
    assert payload["selected_modules"] == ["planning", "memory"]
    assert payload["installed_modules"] == ["planning", "memory"]
    assert payload["feature_tier"]["active"]["id"] == "full"
    assert payload["feature_tier"]["active"]["modules"] == ["planning", "memory"]
    assert payload["feature_tier"]["active"]["source"] == "installed_modules"
    assert payload["feature_tier"]["default_rule"].startswith("Use the smallest module profile")
    assert payload["feature_tier"]["compatibility_status"] == "deprecated-alias-for-module-profiles"
    assert "maintainer-dogfooding" not in {tier["id"] for tier in payload["feature_tier"]["available_tiers"]}
    assert payload["health"] == "healthy"
    assert payload["output_contract"]["optimization_bias"] == "balanced"
    assert payload["output_contract"]["optimization_bias_source"] == "product-default"
    assert payload["output_contract"]["surface"] == "report"
    assert payload["output_contract"]["rendered_view_style"] == "brief-explanatory"
    assert payload["output_contract"]["verbosity_budget"]["default_detail"] == "router-with-brief-context"
    assert payload["output_contract"]["surface_boundary"]["honors_bias"][1] == "rendered human-facing views"
    assert "ownership semantics" in payload["output_contract"]["surface_boundary"]["stays_invariant"]
    operating_posture = payload["operating_posture"]
    assert operating_posture["kind"] == "agentic-workspace/operating-posture/v1"
    assert operating_posture["improvement_latitude"]["mode"] == "conservative"
    assert operating_posture["optimization_bias"]["mode"] == "balanced"
    assert "report useful incidental findings compactly even when not acting" in operating_posture["required_behaviors"]
    assert operating_posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert payload["config_enforcement"]["status"] == "present"
    assert any(route["field"] == "workspace.optimization_bias" for route in payload["config_enforcement"]["weak_field_routes"])
    assert payload["agent_configuration_system"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_system"]["startup_entrypoint"] == "AGENTS.md"
    assert payload["agent_configuration_system"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["agent_configuration_system"]["module_attachment_status"][0]["module"] == "planning"
    assert payload["agent_configuration_queries"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_queries"]["current_work_status"] == "no-active-direction"
    assert payload["agent_configuration_queries"]["current_queries"][0]["id"] == "startup_path"
    assert payload["system_intent_mirror"]["mirror_surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert payload["system_intent_mirror"]["mirror"]["status"] in {"missing", "present"}
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert "durable_intent" in payload["schema"]["shared_fields"]
    assert payload["workflow_obligations"]["configured_count"] == 0
    assert payload["workflow_obligations"]["match_evidence"]["match_count"] == 0
    assert payload["workflow_obligations"]["relevant_to_current_work"] == []
    assert "product_managed_enclave" in payload["schema"]["shared_fields"]
    enclave = payload["product_managed_enclave"]
    assert enclave["managed_root"] == ".agentic-workspace/"
    assert enclave["startup_quietness"]["status"] == "compact"
    assert enclave["local_only_state"]["status"] == "non-authoritative"
    assert enclave["boundary_leaks"] == []
    assert "AGENTS.md managed workflow pointer fence only" in enclave["removability"]["would_affect"]
    assert payload["execution_shape"]["status"] == "present"
    assert payload["execution_shape"]["task_shape"]["id"] == "direct-or-no-active-plan"
    assert payload["execution_shape"]["narrow_work_fast_path"]["status"] == "blessed"
    assert payload["execution_shape"]["recommendation"]["id"] == "stay-direct"
    assert payload["execution_shape"]["recommendation"]["consult"] == [
        "agentic-workspace config --target ./repo --profile compact --format json"
    ]
    assert payload["next_action"]["summary"] == "No immediate action"
    assert not any(
        item["surface"] == ".agentic-workspace/docs/capability-aware-execution.md" for item in payload["discovery"]["memory_candidates"]
    )
    assert any(item["surface"] == ".agentic-workspace/planning/state.toml" for item in payload["discovery"]["planning_candidates"])
    assert payload["discovery"]["ambiguous"] == []
    assert payload["standing_intent"]["canonical_doc"] == ".agentic-workspace/docs/standing-intent-contract.md"
    assert payload["standing_intent"]["precedence_order"][0]["source"] == "explicit_current_human_instruction"
    assert payload["standing_intent"]["precedence_order"][1]["source"] == "active_directional_intent"
    assert payload["standing_intent"]["precedence_order"][2]["source"] == "config_policy"
    assert payload["standing_intent"]["supersession_rules"][0]["rule"] == "newer_same_owner_replaces_older"
    stronger_home = payload["standing_intent"]["stronger_home_model"]
    assert stronger_home["candidate_classes"][0]["class"] == "repo_doctrine"
    assert stronger_home["decision_test"]["promote_to_config_when"][0].startswith("the standing guidance should be machine-readable")
    assert all("current_owner" in example for example in stronger_home["examples"])
    assert "checked-in policy" in payload["standing_intent"]["effective_view"]["conflict_rule"]
    assert payload["standing_intent"]["effective_view"]["in_force_count"] == 3
    standing_classes = {item["class"]: item for item in payload["standing_intent"]["effective_view"]["items"]}
    assert standing_classes["config_policy"]["status"] == "present"
    assert standing_classes["repo_doctrine"]["status"] == "present"
    assert standing_classes["durable_understanding"]["status"] == "present"
    assert standing_classes["active_directional_intent"]["status"] == "absent"
    assert standing_classes["enforceable_workflow"]["status"] == "absent"
    assert payload["repo_friction"]["policy_mode"] == "conservative"
    assert payload["repo_friction"]["owner_surface"] == "workspace"
    assert payload["repo_friction"]["policy_target"] == "repo-directed-improvement"
    assert payload["repo_friction"]["workspace_self_adaptation"]["status"] == "allowed-with-bounds"
    assert payload["repo_friction"]["friction_response_order"][0]["action"] == "adapt-inside-workspace-first"
    assert "validation friction" in payload["repo_friction"]["guardrail_test"]["surface_repo_friction_when"][0]
    threshold = payload["repo_friction"]["repo_directed_improvement_threshold"]
    assert threshold["status"] == "explicit-contract"
    assert "two independent friction confirmations" in threshold["minimum_threshold"][0]
    assert threshold["not_enough"][1] == "one contributor or one model preferring a different repo shape"
    assert payload["repo_friction"]["initiative_posture"] == "local-touched-scope-only"
    assert payload["repo_friction"]["reporting_destinations"] == [
        "agentic-workspace report --target ./repo --format json",
        ".agentic-workspace/planning/state.toml or the active execplan when repeated friction deserves promotion",
    ]
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
    ]
    assert payload["repo_friction"]["large_file_hotspots"]["threshold_lines"] == 400
    assert payload["repo_friction"]["concept_surface_hotspots"]["threshold_lines"] == 200
    assert payload["repo_friction"]["planning_friction"]["status"] == "explicit-contract"
    assert "unclear_seam" in payload["repo_friction"]["planning_friction"]["subtypes"]
    assert payload["repo_friction"]["validation_friction"]["status"] == "explicit-contract"
    assert "weak_seam" in payload["repo_friction"]["validation_friction"]["subtypes"]
    assert "ordinary bug-fixing" in payload["repo_friction"]["validation_friction"]["distinguish_from"][0]
    failure_classes = {item["class"]: item for item in payload["repo_friction"]["validation_friction"]["failure_classification"]}
    assert failure_classes["user_or_content_error"]["interface_design_signal"] is False
    assert failure_classes["interface_design_error"]["interface_design_signal"] is True
    assert payload["repo_friction"]["validation_friction"]["correct_by_design_remedy_order"][:3] == [
        "scaffold",
        "writer_helper",
        "alias",
    ]
    assert payload["repo_friction"]["external_evidence"] == []
    assert payload["repo_friction"]["capture_shortcut"]["status"] == "available"
    assert "observed friction" in payload["repo_friction"]["capture_shortcut"]["minimum_record"]
    assert "surface_value_guardrail" in payload["schema"]["shared_fields"]
    assert payload["surface_value_guardrail"]["preference_order"][0] == "remove an unnecessary surface"
    assert payload["surface_value_guardrail"]["first_contact_budget"]["status"] == "active"
    assert payload["surface_value_guardrail"]["review_result"]["accept_when"][1] == "ownership and authority class are explicit"
    assert "effective_authority" in payload["schema"]["shared_fields"]
    assert "operational_compression" in payload["schema"]["shared_fields"]
    effective_authority = payload["effective_authority"]
    assert effective_authority["status"] == "ready"
    authority_by_concern = {entry["concern"]: entry for entry in effective_authority["authority_map"]}
    assert authority_by_concern["active plan and continuation"]["status"] == "absent"
    assert authority_by_concern["durable repo knowledge"]["status"] == "present"
    assert effective_authority["unresolved_gaps"] == []
    assert effective_authority["idle_context"][0]["id"] == "no-active-planning-record"
    assert effective_authority["system_intent_embodiment"]["anti_framework_pressure"][0] == "remove an unnecessary surface"
    assert payload["reports"][0]["module"] == "planning"
    assert {report["module"] for report in payload["module_reports"]} == {"planning", "memory"}
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["module_reports"] if report["module"] == "memory")
    assert planning_report["schema"]["command"] == "agentic-planning report --format json"
    assert memory_report["schema"]["command"] == "agentic-memory report --target ./repo --format json"
    assert payload["config"]["mixed_agent"]["status"] == "reporting-only"
    operational_compression = payload["operational_compression"]
    assert operational_compression["kind"] == "workspace-operational-compression/v1"
    assert operational_compression["advisory_only"] is True
    measures = operational_compression["measures"]
    assert measures["default_report_size_or_warning_count"]["warning_count"] == len(payload["findings"])
    assert measures["routed_memory_pull_size"]["sources"] == [
        "memory.habitual_pull.evidence",
        "memory.durable_facts.routing_measure",
    ]
    assert measures["unresolved_external_work_routing"]["provider_rule"].startswith(
        "Core planning only consumes provider-agnostic external work evidence"
    )


def test_report_default_profile_returns_router_before_deep_detail(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-report-router/v1"
    assert payload["schema"]["full_profile_command"] == "agentic-workspace report --target ./repo --profile full --format json"
    assert payload["schema"]["section_command"] == "agentic-workspace report --target ./repo --section <section> --format json"
    assert payload["report_profile"]["default_profile"] == "router"
    assert payload["report_profile"]["full_profile"] == "full"
    assert payload["report_profile"]["context_router"]["first_view"] == "start"
    assert payload["report_profile"]["config_enforcement"]["detail_section"] == "config_enforcement"
    assert payload["report_profile"]["decision_grade_fields"][0] == "health"
    ordinary_path = payload["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["entry_command"] == "agentic-workspace start --target ./repo --profile tiny --format json"
    assert ordinary_path["current_work_command"] == "agentic-workspace summary --format json"
    assert ordinary_path["proof_command"] == "agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json"
    recovery = ordinary_path["off_happy_path_recovery"]
    assert recovery["kind"] == "workspace-off-happy-path-recovery/v1"
    assert set(recovery["scenario_ids"]) >= {
        "opened-report-before-start",
        "opened-deep-review-artifact",
        "invalid-near-miss-command",
        "direct-generated-adapter-edit",
        "hand-authored-durable-artifact",
    }
    assert recovery["recover_by_default"] == "agentic-workspace start --target ./repo --profile tiny --format json"
    assert "report_profile.ordinary_agent_path" in payload["report_profile"]["decision_grade_fields"]
    guard = payload["report_profile"]["router_shape_guard"]
    assert guard["status"] == "active"
    assert len(payload) <= guard["max_top_level_fields"]
    assert payload["report_profile"]["feature_tier"]["active"]["id"] == "full"
    assert "available_tiers" not in payload["report_profile"]["feature_tier"]
    assert "report_profile.feature_tier" in payload["report_profile"]["decision_grade_fields"]
    assert len(payload["warning_summary"]["sample"]) <= guard["warning_sample_limit"]
    for section in guard["high_volume_sections_excluded"]:
        assert section not in payload
    assert payload["health"] == "healthy"
    assert "module_reports" not in payload
    assert "reports" not in payload
    assert "maintenance_pressure" not in payload
    assert payload["report_profile"]["feature_tier"]["advanced_policy"]["enabled_features"] == []
    assert "operational_compression" not in payload
    assert "closeout_trust" not in payload
    assert "external_work_delta" not in payload
    assert payload["operating_posture"]["surface"] == "report"
    assert payload["operating_posture"]["closeout_nudge"]["field"] == "improvement_signal_review"
    assert payload["execution_shape"]["task_shape_recommender"]["status"] == "available"
    assert payload["execution_shape"]["narrow_work_fast_path"]["status"] == "blessed"
    intake = payload["improvement_intake"]
    assert intake["kind"] == "workspace-improvement-intake/v1"
    assert intake["role"] == "router-not-backlog"
    assert intake["detail_section"] == "improvement_intake"
    assert isinstance(intake["candidate_count"], int)
    assert len(intake["candidate_sample"]) <= 3
    assert intake["subtypes"] == [
        "setup_finding",
        "review_finding",
        "validation_friction",
        "memory_improvement_signal",
        "repair_recurrence",
    ]
    assert "dogfooding_friction" not in json.dumps(intake, sort_keys=True)
    assert "improvement_intake" in payload["report_profile"]["decision_grade_fields"]
    reconciliation = payload["external_work_reconciliation"]
    assert reconciliation["kind"] == "planning-external-work-reconciliation/v1"
    assert "external_work_reconciliation" in payload["report_profile"]["decision_grade_fields"]
    assert payload["surface_value_guardrail"]["first_contact_budget"]["status"] == "active"
    assert payload["deeper_detail"]["high_volume_sections"][0]["section"] == "module_reports"
    section_hints = {item["section"]: item for item in payload["section_hints"]}
    assert section_hints["module_reports"]["volume"] == "high"
    assert "compact router field" in section_hints["module_reports"]["why_now"]
    assert "maintenance_pressure" not in section_hints
    assert section_hints["improvement_intake"]["volume"] == "normal"
    assert "improvement signal" in section_hints["improvement_intake"]["why_now"]
    assert section_hints["external_work_reconciliation"]["volume"] == "normal"
    assert "external-work" in section_hints["external_work_reconciliation"]["purpose_summary"]
    assert "operational_compression" not in section_hints
    assert "external_work_delta" not in section_hints
    assert section_hints["operating_posture"]["volume"] == "normal"
    assert "improvement posture" in section_hints["operating_posture"]["why_now"]
    assert "idle context" in section_hints["effective_authority"]["purpose_summary"]
    assert "idle state" in section_hints["effective_authority"]["why_now"]
    assert section_hints["effective_authority"]["command"] == (
        "agentic-workspace report --target ./repo --section effective_authority --format json"
    )
    assert len(json.dumps(payload, sort_keys=True)) < 30000

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0
    closeout_payload = json.loads(capsys.readouterr().out)
    closeout_answer = closeout_payload["answer"]
    assert "historical_review_artifacts" not in closeout_answer
    assert closeout_answer["terminal_action"]["blocking"] is False
    assert "what changes closure" not in json.dumps(closeout_answer).lower()
    assert closeout_answer["checks"]["package_workflow_evidence"]["status"] == "not-applicable"
    assert closeout_answer["checks"]["intent_satisfaction"]["reason"] == "no active planning record"
    historical_reviews = closeout_answer["evidence_summary"]["historical_review_artifacts"]
    assert historical_reviews["status"] == "evidence-only"
    assert "not ordinary operating input" in historical_reviews["role"]
    assert "retention_policy_status" in historical_reviews
    assert historical_reviews["detail"].endswith("report --target ./repo --profile full --format json")

    assert cli.main(["report", "--target", str(target), "--section", "operating_posture", "--format", "json"]) == 0
    posture_payload = json.loads(capsys.readouterr().out)
    posture = posture_payload["answer"]
    assert posture["kind"] == "agentic-workspace/operating-posture/v1"
    assert posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert posture["boundaries"]["not_blanket_refactor_permission"] is True


def test_report_router_uses_resolved_cli_invoke_for_copyable_commands(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"]["full_profile_command"] == "uv run agentic-workspace report --target ./repo --profile full --format json"
    assert payload["report_profile"]["default_command"] == "uv run agentic-workspace report --target ./repo --format json"
    ordinary_path = payload["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["entry_command"] == "uv run agentic-workspace start --target ./repo --profile tiny --format json"
    assert ordinary_path["state_command"] == "uv run agentic-workspace report --target ./repo --format json"
    assert ordinary_path["current_work_command"] == "uv run agentic-workspace summary --format json"
    assert ordinary_path["proof_command"] == "uv run agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json"
    recovery = ordinary_path["off_happy_path_recovery"]
    assert recovery["recover_by_default"] == "uv run agentic-workspace start --target ./repo --profile tiny --format json"
    assert payload["section_hints"][0]["command"].startswith("uv run agentic-workspace report ")
    if "maintenance_pressure" in payload:
        assert payload["maintenance_pressure"]["subcategories"][0]["section_command"].startswith("uv run agentic-workspace report ")


def test_defaults_repair_recovery_section_reports_fault_taxonomy(capsys) -> None:
    assert cli.main(["defaults", "--section", "repair_recovery", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    fault_classes = {item["id"] for item in answer["fault_classes"]}
    invariants = {item["id"] for item in answer["invariants"]}
    assert "package_command_bug" in fault_classes
    assert "workspace.required_surface_present" in invariants
    assert "planning.active_execplan_exists" in invariants
    assert "external_evidence.aggregates_match_items" in invariants
    assert answer["package_command_bug_signal"]["required_fields"] == [
        "command_run",
        "expected_invariant",
        "actual_broken_state",
        "affected_surfaces",
        "safe_repair_available",
        "reproduction_command",
        "suggested_regression_test",
    ]
    assert "repeated" in answer["recurrence_to_improvement"]
    assert "proof_after" in answer["repair_action_shape"]["required_fields"]


def test_improvement_intake_includes_repair_recurrence_subtype(capsys) -> None:
    assert cli.main(["defaults", "--section", "improvement_intake", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    subtypes = {item["id"]: item for item in payload["answer"]["payload"]["subtypes"]}
    repair = subtypes["repair_recurrence"]
    assert repair["source"] == "doctor.repair_actions or doctor.manual_review_actions"
    assert repair["selector"] == "agentic-workspace defaults --section repair_recovery --format json"
    assert "affordance" in repair["correct_by_design_remedies"]


def test_doctor_emits_affordance_shaped_repair_and_manual_review_actions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    agents_path = target / "AGENTS.md"
    agents_path.write_text(agents_path.read_text(encoding="utf-8").replace(cli.WORKSPACE_POINTER_BLOCK, ""), encoding="utf-8")

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    safe_action = workspace_report["repair_actions"][0]
    assert safe_action["id"] == "restore-missing-workspace-surface"
    assert safe_action["invariant"] == "workspace.required_surface_present"
    assert safe_action["safe_to_apply"] is True
    assert safe_action["command"].startswith("agentic-workspace upgrade --target ")
    assert "--dry-run" in safe_action["dry_run"]
    assert safe_action["proof_after"][0].startswith("agentic-workspace doctor --target ")
    assert safe_action["do_not"]
    assert safe_action["improvement_signal_candidate"]["kind"] == "repair_recurrence"

    manual_action = workspace_report["manual_review_actions"][0]
    assert manual_action["id"] == "restore-workspace-pointer-manually"
    assert manual_action["invariant"] == "workspace.startup_pointer_present"
    assert manual_action["safe_to_apply"] is False
    assert manual_action["command"] is None
    assert manual_action["proof_after"][0].startswith("agentic-workspace doctor --target ")

    repair_plan = workspace_report["repair_plan"]
    assert repair_plan["status"] == "safe-action-available"
    assert repair_plan["primary_next_action"]["id"] == "restore-missing-workspace-surface"
    assert repair_plan["repair_action_count"] == 1
    assert repair_plan["manual_review_action_count"] == 1
    assert payload["repair_plan"]["primary_next_action"]["id"] == "restore-missing-workspace-surface"
    assert payload["repair_actions"][0]["id"] == "restore-missing-workspace-surface"
    assert payload["manual_review_actions"][0]["id"] == "restore-workspace-pointer-manually"


def test_doctor_repair_actions_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    (target / "llms.txt").unlink()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    action = workspace_report["repair_actions"][0]
    assert action["id"] == "refresh-generated-agent-handoff"
    assert action["command"].startswith("uv run agentic-workspace upgrade ")
    assert action["dry_run"].startswith("uv run agentic-workspace upgrade ")
    assert action["proof_after"][0].startswith("uv run agentic-workspace doctor ")


def test_report_section_agent_aids_discovers_checked_in_and_local_aids(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    aid_root = target / ".agentic-workspace" / "agent-aids" / "scripts"
    candidate_manifest = {
        "kind": "agentic-workspace/agent-aid/v1",
        "id": "workspace-validation-wrapper",
        "type": "script",
        "status": "candidate",
        "scope": "repo-shared",
        "portability": "cross-platform",
        "proof_role": "candidate-aid",
        "owner": "workspace",
        "created_because": "Agents repeatedly need a bounded validation wrapper.",
        "use_when": ["validating workspace CLI and contract changes"],
        "entrypoint": ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
        "safety": {
            "read_only": True,
            "writes_repo": False,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        },
        "validation": {"commands": ["uv run python .agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"]},
        "promotion": {
            "target_kind": "check",
            "target": "scripts/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts",
            "retention_after_promotion": "delete",
        },
        "retirement": {"trigger": "obsolete", "retention_after_retirement": "delete"},
    }
    retired_manifest = {**candidate_manifest, "id": "old-helper", "status": "retired"}
    (aid_root / "workspace-validation" / "manifest.json").write_text(json.dumps(candidate_manifest), encoding="utf-8")
    (aid_root / "old-helper" / "manifest.json").write_text(json.dumps(retired_manifest), encoding="utf-8")
    (target / ".agentic-workspace" / "local" / "integrations" / "codex" / "README.md").write_text(
        "# Local aids\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--section", "agent_aids", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["kind"] == "workspace-agent-aids-discovery/v1"
    assert "storage" not in answer
    assert answer["storage_summary"]["candidate_root"] == ".agentic-workspace/agent-aids"
    assert answer["storage_summary"]["manifest_check"] == "python scripts/check/check_agent_aids.py"
    assert answer["summary"]["checked_in_count"] == 2
    assert answer["summary"]["visible_checked_in_count"] == 1
    assert answer["summary"]["retired_count"] == 1
    assert answer["summary"]["local_only_container_count"] == 1
    assert answer["creation_affordance"]["agent_may_create"] is True
    assert answer["creation_affordance"]["first_pattern"]["makefile_variable"] == "COMPACT_RUN"
    assert answer["creation_affordance"]["first_pattern"]["timeout_option"] == "--timeout-seconds <seconds>"
    candidate = next(entry for entry in answer["checked_in_aids"] if entry["id"] == "workspace-validation-wrapper")
    assert candidate["type"] == "script"
    assert candidate["status"] == "candidate"
    assert candidate["scope"] == "repo-shared"
    assert candidate["portability"] == "cross-platform"
    assert candidate["entrypoint"].endswith("workspace_validation.py")
    assert candidate["safety_summary"]["read_only"] is True
    assert candidate["canonical_proof_route"] is False
    assert candidate["promotion_summary"]["target_kind"] == "check"
    assert candidate["promotion_summary"]["discovery_route"] == "repo-check"
    assert candidate["promotion_summary"]["retention_after_promotion"] == "delete"
    assert [entry["id"] for entry in answer["recommended_actions"]] == ["workspace-validation-wrapper"]
    recommended = answer["recommended_actions"][0]
    assert recommended["risk"] == "candidate or advisory aid; inspect safety and portability before use"
    assert recommended["command"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert recommended["run"] == recommended["command"]
    assert recommended["required_inputs"] == ["current task", "aid safety summary", "proof role"]
    assert "declared validation" in recommended["next_proof"]
    assert answer["recommended_action_omitted_count"] == 0
    primary_action = answer["primary_next_action"]
    assert primary_action["action"] == "use-agent-aid"
    assert primary_action["id"] == "workspace-validation-wrapper"
    assert primary_action["command"] == recommended["command"]
    assert primary_action["required_inputs"] == ["current task", "aid safety summary", "proof role"]
    assert answer["local_only"]["entries"][0]["id"] == "codex"
    assert answer["local_only"]["entries"][0]["authority"] == "none"


def test_report_section_agent_aids_routes_empty_discovery_to_repeat_friction_review(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "agent_aids", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "storage" not in payload["answer"]
    assert payload["answer"]["storage_summary"]["canonical_doc"] == ".agentic-workspace/docs/agent-aids-storage.md"
    action = payload["answer"]["primary_next_action"]
    assert action["action"] == "create-bounded-aid-when-it-reduces-friction"
    assert action["command"] == 'agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert action["run"] == action["command"]
    assert action["required_inputs"] == ["current task", "friction evidence", "authority boundary"]
    assert "ordinary compact routes" in action["summary"]
    assert "handoff cost" in action["summary"]
    assert "checked in" in action["next_proof"]


def test_report_improvement_intake_keeps_dogfooding_source_checkout_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / "pyproject.toml", '[project]\nname = "agentic-workspace"\n')
    (target / "src" / "agentic_workspace").mkdir(parents=True)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    intake = payload["improvement_intake"]
    assert intake["audience_boundary"]["status"] == "source-checkout"
    assert intake["subtypes"] == [
        "setup_finding",
        "dogfooding_friction",
        "review_finding",
        "validation_friction",
        "memory_improvement_signal",
        "repair_recurrence",
    ]


def test_report_surfaces_review_retention_cleanup_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    review_dir = target / ".agentic-workspace" / "planning" / "reviews"
    docs_review_dir = target / "docs" / "reviews"
    docs_review_dir.mkdir(parents=True)
    _write_json(review_dir / "missing.review.json", {"kind": "planning-review/v1", "title": "Missing Retention"})
    _write_json(
        review_dir / "resolved.review.json",
        {
            "kind": "planning-review/v1",
            "title": "Resolved Review",
            "issue_classifications": [
                {
                    "id": "#1",
                    "classification": "evidence-present",
                    "live_state": "closed",
                    "resolution": "implemented",
                }
            ],
            "retention": {
                "closeout shape": "shrink after findings are routed",
                "trigger": "after issue closeout",
                "proof surface": "report closeout_trust",
            },
            "padding": [f"line {index}" for index in range(90)],
        },
    )
    _write(docs_review_dir / "historical.md", "# Historical Review\n\nImplemented and superseded.\n")

    assert cli.main(["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]) == 0

    closeout_payload = json.loads(capsys.readouterr().out)
    historical_summary = closeout_payload["answer"]["evidence_summary"]["historical_review_artifacts"]
    assert historical_summary["retention_policy_status"] == "attention"
    assert historical_summary["retention_candidate_count"] >= 2
    assert "historical_review_artifacts" not in closeout_payload["answer"]

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    full_payload = json.loads(capsys.readouterr().out)
    retention = full_payload["closeout_trust"]["historical_review_artifacts"]["retention_policy"]
    assert retention["status"] == "attention"
    assert retention["artifact_count"] >= 3
    assert retention["missing_retention_metadata_count"] >= 2
    signals = {candidate["signal"]: candidate for candidate in retention["candidates"]}
    assert signals["missing-retention-metadata"]["recommended_outcome"] == "add-retention-metadata"
    assert signals["retention-shape-shrink"]["recommended_outcome"] == "shrink"
    assert retention["default_outcome"] == "retain"
    assert "never deletes" in retention["rule"]

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0
    operational_payload = json.loads(capsys.readouterr().out)
    measures = operational_payload["answer"]["measures"]
    assert measures["review_retention_policy"]["candidate_count"] >= 2
    assert any(signal["measure"] == "review_retention_policy" for signal in operational_payload["answer"]["signals"])

    assert cli.main(["report", "--target", str(target), "--section", "maintenance_pressure", "--format", "json"]) == 0
    maintenance_payload = json.loads(capsys.readouterr().out)
    categories = {entry["id"]: entry for entry in maintenance_payload["answer"]["subcategories"]}
    assert categories["review_retention"]["status"] == "attention"
    assert "cleanup candidates" in categories["review_retention"]["summary"]


def test_report_section_selector_returns_compact_section_answer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "effective_authority", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "effective_authority"}
    assert payload["matched"] is True
    assert payload["answer"]["defaults_command"] == "agentic-workspace defaults --section effective_authority --format json"
    assert payload["answer"]["status"] == "ready"
    assert payload["answer"]["idle_context"][0]["id"] == "no-active-planning-record"
    assert payload["refs"][0] == ".agentic-workspace/docs/reporting-contract.md"


def test_report_section_selector_returns_operational_compression_measures(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "execplans" / "archive" / "compressed-lane.plan.json",
        {
            "kind": "planning-execplan/v1",
            "active_milestone": {"status": "completed"},
            "closeout_distillation": {
                "buckets": {
                    "continuation": [{"summary": "Parent remains open.", "owner": "planning", "source": "test"}],
                    "discard": [],
                    "memory": [],
                    "config_check": [],
                    "docs": [],
                    "issue_follow_up": [],
                }
            },
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "operational_compression"}
    assert payload["matched"] is True
    assert captured.err == ""
    answer = payload["answer"]
    assert answer["kind"] == "workspace-operational-compression/v1"
    assert answer["advisory_only"] is True
    assert answer["hard_failures"] == []
    assert "dashboard" in answer["rule"]
    measures = answer["measures"]
    assert measures["first_line_startup_read_surface_count"]["count"] >= 1
    assert measures["default_report_size_or_warning_count"]["decision_grade_field_count"] >= 1
    assert measures["additive_surface_replacement_pressure"]["status"] == "available-advisory-gate"
    assert measures["additive_surface_replacement_pressure"]["review_gate"]["rule"].startswith("Durable-surface changes")
    assert measures["durable_surface_metadata"]["required_metadata"] == ["owner", "authority", "summary"]
    assert measures["archived_plan_distillation"]["archived_plan_count"] == 1
    assert measures["archived_plan_distillation"]["with_distillation_count"] == 1
    assert measures["archived_plan_distillation"]["missing_distillation_count"] == 0
    assert measures["archived_plan_distillation"]["post_contract_missing_distillation_count"] == 0
    archive_retention = measures["archive_retention_policy"]
    assert archive_retention["kind"] == "workspace-archive-retention-policy/v1"
    assert archive_retention["advisory_only"] is True
    assert archive_retention["outcomes"] == [
        "retain",
        "shrink",
        "stub",
        "delete",
        "promote-summary-elsewhere",
    ]
    assert archive_retention["default_outcome"] == "retain"
    assert archive_retention["candidate_count"] == 0
    assert "never deletes" in archive_retention["rule"]
    review_retention = measures["review_retention_policy"]
    assert review_retention["kind"] == "workspace-review-retention-policy/v1"
    assert review_retention["advisory_only"] is True
    assert review_retention["default_outcome"] == "retain"
    generated_footprint = measures["generated_output_footprint"]
    assert generated_footprint["kind"] == "workspace-generated-output-footprint/v1"
    assert generated_footprint["advisory_only"] is True
    assert generated_footprint["freshness"]["ordinary_report_runs_checks"] is False
    assert "Generated outputs are reproducible derived artifacts" in generated_footprint["guardrails"][0]
    footprint = measures["artifact_footprint_by_class"]
    assert footprint["rule"].startswith("Footprint classes are advisory")
    classes = {entry["id"]: entry for entry in footprint["classes"]}
    assert set(classes) >= {
        "active_execplans",
        "archived_execplans",
        "review_artifacts",
        "current_memory_notes",
        "durable_memory_notes",
        "generated_outputs",
        "local_only_state",
        "large_docs_or_package_surfaces",
    }
    assert classes["archived_execplans"]["role"] == "historical evidence"
    assert classes["durable_memory_notes"]["role"] == "durable knowledge"
    assert classes["generated_outputs"]["role"] == "derived reproducible artifact"


def test_operational_compression_reports_artifact_footprint_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(target / ".agentic-workspace" / "memory" / "repo" / "current" / "legacy.md", "# Legacy\n")
    _write(target / ".agentic-workspace" / "planning" / "reviews" / "old.review.json", "{}\n")
    _write(target / "generated" / "adapter.json", "{}\n")
    _write(target / "docs" / "large.md", "\n".join(f"line {index}" for index in range(401)))

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    footprint = payload["answer"]["measures"]["artifact_footprint_by_class"]
    classes = {entry["id"]: entry for entry in footprint["classes"]}
    assert classes["current_memory_notes"]["pressure"] == "attention"
    assert classes["review_artifacts"]["pressure"] == "attention"
    assert classes["generated_outputs"]["count"] >= 1
    assert classes["large_docs_or_package_surfaces"]["pressure"] == "attention"
    generated_footprint = payload["answer"]["measures"]["generated_output_footprint"]
    assert generated_footprint["status"] == "attention"
    assert generated_footprint["unclassified_generated_output_count"] >= 1
    assert "generated/adapter.json" in generated_footprint["sample_unclassified_generated_outputs"]
    assert any(signal["measure"] == "generated_output_footprint" for signal in payload["answer"]["signals"])
    assert footprint["pressure_class_count"] >= 3
    assert footprint["recommended_cleanup_target"]["action"] == "review-shrink-route-or-retain"
    assert any(signal["measure"] == "artifact_footprint_by_class" for signal in payload["answer"]["signals"])


def test_operational_compression_classifies_generated_output_footprint(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json",
        {
            "packages": [
                {
                    "id": "root-workspace",
                    "program": "agentic-workspace",
                    "targets": [
                        {
                            "kind": "python",
                            "generated_root": "src/agentic_workspace/generated_cli_package",
                            "generation_status": "supported-now",
                            "maturity_level_ref": "metadata-proof-fixture",
                            "test_environment": "python-dev",
                        },
                        {
                            "kind": "typescript",
                            "generated_root": "generated/typescript/workspace-cli",
                            "generation_status": "runnable-read-only-adapter",
                            "maturity_level_ref": "runnable-read-only-adapter",
                            "test_environment": "docker",
                        },
                    ],
                }
            ]
        },
    )
    _write_json(
        target / "src" / "agentic_workspace" / "contracts" / "command_adapter_generation.json",
        {
            "generated_outputs": [
                {
                    "program": "agentic-workspace",
                    "path": "src/agentic_workspace/generated_command_adapters.py",
                }
            ]
        },
    )
    _write(target / "scripts" / "generate" / "generate_command_packages.py", "print('generate')\n")
    _write(target / "scripts" / "check" / "check_generated_command_packages.py", "print('check')\n")
    _write(target / "src" / "agentic_workspace" / "generated_cli_package" / "__init__.py", "# generated\n")
    _write(
        target / "src" / "agentic_workspace" / "generated_cli_package" / "__pycache__" / "__init__.cpython-313.pyc",
        "cache\n",
    )
    _write(target / "src" / "agentic_workspace" / "generated_command_adapters.py", "# generated\n")
    _write(target / "generated" / "typescript" / "workspace-cli" / "package.json", "{}\n")
    _write(target / "generated" / "typescript" / "workspace-cli" / "src" / "cli.mjs", "export {};\n")
    _write(target / "generated" / "typescript" / "Dockerfile", "FROM node:22\n")

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    generated = payload["answer"]["measures"]["generated_output_footprint"]
    assert generated["status"] == "measured"
    assert generated["artifact_count"] >= 5
    assert generated["proof_fixture_count"] == 1
    assert generated["runnable_adapter_count"] == 1
    assert generated["unclassified_generated_output_count"] == 0
    assert generated["freshness"]["status"] == "check-available"
    surfaces = {surface["id"]: surface for surface in generated["generated_surfaces"]}
    assert surfaces["root-workspace:python"]["role"] == "proof-fixture"
    assert surfaces["root-workspace:typescript"]["role"] == "runnable-read-only-adapter"
    assert surfaces["typescript:proof-container-support"]["role"] == "proof-container-support"


def test_report_distinguishes_legacy_archive_distillation_debt(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    archive_dir = target / ".agentic-workspace" / "planning" / "execplans" / "archive"
    legacy_missing = archive_dir / "legacy-missing.plan.json"
    compressed = archive_dir / "compressed-lane.plan.json"
    current_missing = archive_dir / "current-missing.plan.json"
    _write_json(legacy_missing, {"kind": "planning-execplan/v1", "active_milestone": {"status": "completed"}})
    _write_json(
        compressed,
        {
            "kind": "planning-execplan/v1",
            "active_milestone": {"status": "completed"},
            "closeout_distillation": {
                "buckets": {
                    "continuation": [{"summary": "Parent remains open.", "owner": "planning", "source": "test"}],
                    "discard": [],
                    "memory": [],
                    "config_check": [],
                    "docs": [],
                    "issue_follow_up": [],
                }
            },
        },
    )
    _write_json(current_missing, {"kind": "planning-execplan/v1", "active_milestone": {"status": "completed"}})
    os.utime(legacy_missing, (1_000_000, 1_000_000))
    os.utime(compressed, (2_000_000, 2_000_000))
    os.utime(current_missing, (3_000_000, 3_000_000))

    assert cli.main(["report", "--target", str(target), "--section", "operational_compression", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    measure = payload["answer"]["measures"]["archived_plan_distillation"]
    assert measure["missing_distillation_count"] == 2
    assert measure["legacy_missing_distillation_count"] == 1
    assert measure["post_contract_missing_distillation_count"] == 1
    assert measure["distillation_contract_anchor"] == "compressed-lane.plan.json"
    signal = next(item for item in payload["answer"]["signals"] if item["measure"] == "archived_plan_distillation")
    assert signal["count"] == 1
    archive_retention = payload["answer"]["measures"]["archive_retention_policy"]
    assert archive_retention["status"] == "attention"
    assert archive_retention["before_shrink_or_delete"][0].startswith("promote durable learning")
    assert any(candidate["recommended_outcome"] == "promote-summary-elsewhere" for candidate in archive_retention["candidates"])
    assert any(candidate["recommended_outcome"] == "stub" for candidate in archive_retention["candidates"])
    retention_signal = next(item for item in payload["answer"]["signals"] if item["measure"] == "archive_retention_policy")
    assert retention_signal["count"] == archive_retention["candidate_count"]


def test_report_section_selector_returns_external_work_delta(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "previous_items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "Old open task",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                }
            ],
            "items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "Old open task",
                    "status": "closed",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                },
                {
                    "system": "manual",
                    "id": "TASK-2",
                    "title": "New follow-up",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "required",
                },
            ],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_delta", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "external_work_delta"}
    answer = payload["answer"]
    assert answer["status"] == "delta-present"
    assert answer["new_count"] == 1
    assert answer["changed_count"] == 1
    assert answer["closed_count"] == 1
    assert answer["recommended_next_lane"]["id"] == "TASK-2"


def test_report_section_selector_rejects_schema_invalid_external_work_delta(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "items": [{"system": "manual", "id": "", "status": "open"}],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_delta", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["status"] == "invalid"
    assert "schema validation failed" in answer["reason"]
    assert any("items.0.id" in finding for finding in answer["schema_findings"])


def test_report_section_selector_returns_external_work_reconciliation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / ".agentic-workspace" / "planning" / "external-intent-evidence.json",
        {
            "kind": "planning-external-intent-evidence/v1",
            "refreshed_at": "2026-04-27T12:00:00+00:00",
            "refresh_metadata": {"adapter": "manual-fixture", "item_count": 1, "open_count": 1, "closed_count": 0},
            "items": [
                {
                    "system": "manual",
                    "id": "TASK-1",
                    "title": "External follow-up",
                    "status": "open",
                    "kind": "task",
                    "parent_id": "",
                    "planning_residue_expected": "optional",
                }
            ],
        },
    )

    assert cli.main(["report", "--target", str(target), "--section", "external_work_reconciliation", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "report"
    assert payload["selector"] == {"section": "external_work_reconciliation"}
    answer = payload["answer"]
    assert answer["kind"] == "planning-external-work-reconciliation/v1"
    assert answer["freshness"]["fresh_enough_to_trust"] is True
    assert answer["freshness"]["refresh_metadata"]["adapter"] == "manual-fixture"
    assert answer["external_work_state"]["open_count"] == 1
    assert answer["external_work_state"]["untracked_open_count"] == 1
    promotion_action = answer["promotion_action"]
    assert promotion_action["action"] == "promote-external-work-to-planning"
    assert promotion_action["provider_neutral"] is True
    assert promotion_action["target_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/<lane>.plan.json",
    ]
    assert "do not duplicate active state" in promotion_action["state_rule"]
    assert answer["workspace_report_view"]["delta_section"] == "external_work_delta"


def test_report_section_selector_accepts_current_work_alias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "current_work", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "current_work", "resolved_section": "effective_authority.current_work"}
    assert payload["answer"]["status"] in {"absent", "direct-or-no-active-plan"}


def test_report_section_selector_accepts_current_external_work_alias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--section", "current_external_work", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"section": "current_external_work", "resolved_section": "external_work_reconciliation"}
    assert payload["answer"]["kind"] == "planning-external-work-reconciliation/v1"


def test_report_section_selector_error_recommends_compact_recovery(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["report", "--target", str(target), "--section", "currnt_work", "--format", "json"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "Did you mean: current_work" in stderr
    assert "agentic-workspace summary --format json" in stderr
    assert "--section next_action" in stderr
    assert "--section external_work_reconciliation" in stderr


def test_report_routes_roadmap_backed_work_to_planning_before_broad_execution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = []\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = [\n"
        "  { id = 'dogfooding-guardrail', title = 'Dogfooding guardrail', priority = 'first', issues = ['#322'], outcome = 'Make planned work use planning.', reason = 'A broad run bypassed active planning.', promotion_signal = 'Promote before broad work.', suggested_first_slice = 'Add readiness guardrail.' },\n"
        "]\n"
        "candidates = [\n"
        "  { priority = 'first', summary = 'Dogfooding guardrail' },\n"
        "]\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    execution_shape = payload["execution_shape"]
    assert execution_shape["task_shape"]["id"] == "roadmap-backed-no-active-plan"
    assert [shape["id"] for shape in execution_shape["task_shape_recommender"]["shapes"]] == [
        "direct",
        "light-plan",
        "checked-in-execplan",
    ]
    assert execution_shape["recommendation"]["id"] == "promote-before-broad-work"
    assert execution_shape["recommendation"]["consult"] == ["agentic-workspace summary --format json"]
    assert execution_shape["recommendation"]["allowed_execution_methods"] == [
        "single-agent fallback for narrow work",
        "planning-backed execution after promotion",
    ]
    assert "chat or issue context alone" in execution_shape["deviation_rule"]


def test_report_surfaces_default_branch_commit_risk(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _set_git_branch(target, current="master", default="master")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "branch_workflow_posture" in payload["schema"]["shared_fields"]
    assert "local_memory" in payload["schema"]["shared_fields"]
    posture = payload["branch_workflow_posture"]
    assert posture["status"] == "present"
    assert posture["current_branch"] == "master"
    assert posture["default_branch"] == "master"
    assert posture["on_default_branch"] is True
    assert posture["risk"] == "default-branch-commit-risk"
    assert "do not switch branches unless the user decides" in posture["recommended_next_action"]
    policy = posture["branch_mutation_policy"]
    assert policy["advisory_only"] is True
    assert "switch-branch" in policy["guarded_actions"]
    assert "explicit user intent" in policy["rule"]


def test_report_closeout_trust_surfaces_package_workflow_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    plan = target / ".agentic-workspace" / "planning" / "execplans" / "package-use.plan.json"
    _write_json(
        plan,
        {
            "kind": "planning-execplan/v1",
            "title": "Package Use",
            "active_milestone": {"id": "package-use", "status": "active"},
            "delegated_judgment": {
                "requested outcome": "Use package workflow.",
                "hard constraints": "Stay portable.",
                "agent may decide locally": "Exact signal shape.",
                "escalate when": "Package workflow is unavailable.",
            },
            "immediate_next_action": ["Use package workflow."],
            "completion_criteria": ["Package workflow evidence is visible."],
            "validation_commands": ["uv run agentic-workspace proof --target . --format json"],
            "intent_continuity": {
                "larger intended outcome": "Close broad package workflow lane.",
                "this slice completes the larger intended outcome": "no",
                "continuation surface": ".agentic-workspace/planning/state.toml",
            },
            "required_continuation": {
                "required follow-on for the larger intended outcome": "yes",
                "owner surface": ".agentic-workspace/planning/state.toml",
                "activation trigger": "after proof passes",
            },
            "iterative_follow_through": {
                "what this slice enabled": "package workflow evidence",
                "intentionally deferred": "broad package workflow lane closeout",
                "discovered implications": "validation proof is not intent closure",
                "proof achieved now": "yes",
                "validation still needed": "lane follow-on",
                "next likely slice": "continue broad workflow lane",
            },
            "context_budget": {
                "live working set": "report output and closeout trust",
                "recoverable later": "archived plan",
                "externalize before shift": "state.toml",
                "pre-work config pull": "uv run agentic-workspace summary --format json",
                "pre-work memory pull": "uv run agentic-workspace report --format json",
                "tiny resumability note": "validation proof is separate from lane closure",
                "context-shift triggers": "larger intent remains open",
            },
            "execution_run": {
                "run status": "active",
                "executor": "test",
                "handoff source": "uv run agentic-workspace preflight --format json",
                "what happened": "Used agentic-workspace report --target . --format json and proof-selected validation.",
                "scope touched": "test",
                "changed surfaces": "test",
                "validations run": "uv run agentic-workspace summary --format json; uv run agentic-workspace reconcile --format json",
                "result for continuation": "continue",
                "next step": "finish",
            },
            "proof_report": {
                "validation proof": "uv run agentic-workspace proof passed",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "focused report test fixture",
            },
            "closure_check": {
                "slice status": "active",
                "larger-intent status": "open",
                "closure decision": "archive-but-keep-lane-open",
                "why this decision is honest": "The proof passed but the broader workflow lane still has follow-on work.",
                "evidence carried forward": ".agentic-workspace/planning/state.toml",
                "reopen trigger": "follow-on remains open",
            },
        },
    )
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'package-use', title = 'Package use', surface = '.agentic-workspace/planning/execplans/package-use.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    evidence = payload["closeout_trust"]["package_workflow_evidence"]
    assert evidence["status"] == "present"
    assert evidence["trust"] == "normal"
    assert evidence["required_for_broad_work"] is True
    assert evidence["used_surfaces"] == ["preflight", "summary", "report", "proof", "reconcile"]
    assert evidence["missing_expected_surfaces"] == []
    intent_check = payload["closeout_trust"]["intent_satisfaction_check"]
    assert intent_check["status"] == "present"
    assert intent_check["trust"] == "follow-up-required"
    closure_scope = intent_check["closure_scope"]
    assert closure_scope["validation_proof"]["status"] == "separate-answer"
    assert closure_scope["validation_proof"]["not_sufficient_for_closure"] is True
    assert closure_scope["validation_proof"]["proof_expectation_count"] == 1
    assert closure_scope["requested_slice"]["status"] == "active"
    assert closure_scope["lane_or_system_intent"]["status"] == "follow-up-required"
    assert closure_scope["lane_or_system_intent"]["required_follow_on"] == "yes"
    assert closure_scope["larger_intent_closure"]["status"] == "open"
    assert closure_scope["larger_intent_closure"]["closure_decision"] == "archive-but-keep-lane-open"
    assert closure_scope["non_substitution_rule"] == "Validation success alone is not closure evidence."
    residue_action = payload["closeout_trust"]["durable_residue_action"]
    assert residue_action["action"] == "route-durable-residue"
    assert residue_action["command"] == "agentic-workspace report --target ./repo --section closeout_trust --format json"
    assert residue_action["run"] == residue_action["command"]
    assert residue_action["risk"] == "read-only routing; mutations happen only through the selected owner surface"
    assert residue_action["required_inputs"] == ["validation result", "issue or lane scope", "future relevance of any learning"]
    assert "Memory" in residue_action["destinations"]
    assert "future work goes to planning" in residue_action["destination_rule"]
    assert "rerun summary/reconcile" in residue_action["next_proof"]
    terminal_action = payload["closeout_trust"]["terminal_action"]
    assert terminal_action["blocking"] is False
    assert terminal_action["next_command"] == "none"
    assert "No closeout trust blocker" in terminal_action["why"]
    assert "proof, intent satisfaction, issue state" in terminal_action["changes_closure"]


def test_report_closeout_trust_lowers_trust_when_active_plan_has_no_package_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    plan = target / ".agentic-workspace" / "planning" / "execplans" / "bypassed-workflow.plan.json"
    _write_json(
        plan,
        {
            "kind": "planning-execplan/v1",
            "title": "Bypassed Workflow",
            "active_milestone": {"id": "bypassed-workflow", "status": "active"},
            "delegated_judgment": {
                "requested outcome": "Implement broad work.",
                "hard constraints": "Keep workflow evidence visible.",
                "agent may decide locally": "Implementation details.",
                "escalate when": "Workflow unavailable.",
            },
            "immediate_next_action": ["Finish the lane."],
            "completion_criteria": ["Closeout trust can detect missing package evidence."],
            "validation_commands": ["make check"],
            "intent_continuity": {
                "larger intended outcome": "Close a broad workflow lane.",
                "this slice completes the larger intended outcome": "yes",
                "continuation surface": "none",
            },
            "required_continuation": {
                "required follow-on for the larger intended outcome": "no",
                "owner surface": "none",
                "activation trigger": "none",
            },
            "iterative_follow_through": {
                "what this slice enabled": "absence detection",
                "intentionally deferred": "external enforcement",
                "discovered implications": "none",
                "proof achieved now": "pending",
                "validation still needed": "make check",
                "next likely slice": "none",
            },
            "context_budget": {
                "live working set": "closeout trust",
                "recoverable later": "archive",
                "externalize before shift": "plan",
                "pre-work config pull": "",
                "pre-work memory pull": "",
                "tiny resumability note": "missing package evidence",
                "context-shift triggers": "closeout",
            },
            "execution_run": {
                "run status": "active",
                "executor": "test",
                "handoff source": "chat only",
                "what happened": "Implemented without recording package workflow use.",
                "scope touched": "test",
                "changed surfaces": "test",
                "validations run": "make check",
                "result for continuation": "close",
                "next step": "close",
            },
            "proof_report": {
                "validation proof": "make check",
                "proof achieved now": "pending",
                'evidence for "proof achieved" state': "none",
            },
            "closure_check": {
                "slice status": "active",
                "larger-intent status": "open",
                "closure decision": "archive-and-close",
                "why this decision is honest": "fixture",
                "evidence carried forward": "none",
                "reopen trigger": "missing evidence",
            },
        },
    )
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'bypassed-workflow', title = 'Bypassed workflow', surface = '.agentic-workspace/planning/execplans/bypassed-workflow.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    closeout = payload["closeout_trust"]
    assert closeout["trust"] == "lower-trust"
    assert closeout["lower_trust_closeout_count"] == 1
    assert closeout["planning_residue_lower_trust_count"] == 0
    assert closeout["package_evidence_lower_trust_count"] == 1
    assert "missing preflight, summary, report, proof" in closeout["absence_signals"][0]
    evidence = closeout["package_workflow_evidence"]
    assert evidence["trust"] == "lower-trust"
    assert evidence["missing_expected_surfaces"] == ["preflight", "summary", "report", "proof"]


def test_report_surfaces_local_only_memory_status(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n\n[local_memory]\nenabled = true\npath = ".agentic-workspace/local/memory.toml"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    local_memory = payload["local_memory"]
    assert local_memory["status"] == "enabled"
    assert local_memory["path"] == ".agentic-workspace/local/memory.toml"
    assert local_memory["git_ignored"] is True
    assert local_memory["safe_to_delete"] is True
    assert local_memory["scratch"]["root"] == ".agentic-workspace/local/scratch"
    assert local_memory["scratch"]["exists"] is True
    assert "checked-in Memory" in local_memory["promotion_guidance"]


def test_preflight_surfaces_local_only_memory_status(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n[local_memory]\nenabled = true\n",
        encoding="utf-8",
    )

    assert cli.main(["preflight", "--target", str(target), "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["local_memory"]["status"] == "enabled"
    assert payload["local_memory"]["path"] == ".agentic-workspace/local/memory.toml"


def test_preflight_surfaces_non_default_branch_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _set_git_branch(target, current="feature/work", default="master")

    assert cli.main(["preflight", "--target", str(target), "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    posture = payload["branch_workflow_posture"]
    assert posture["status"] == "present"
    assert posture["current_branch"] == "feature/work"
    assert posture["default_branch"] == "master"
    assert posture["on_default_branch"] is False
    assert posture["risk"] == "normal"
    assert posture["branch_mutation_policy"]["requires_user_intent_before"][0] == "changing the execution branch"


def test_report_handles_modules_with_empty_findings_lists(tmp_path: Path, monkeypatch, capsys) -> None:
    from repo_memory_bootstrap import installer as memory_installer
    from repo_planning_bootstrap import installer as planning_installer

    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    original_planning_report = planning_installer.planning_report
    original_memory_report = memory_installer.memory_report

    def _planning_report_without_findings(*, target=None):
        report = original_planning_report(target=target)
        report["findings"] = []
        return report

    def _memory_report_without_findings(*, target=None):
        report = original_memory_report(target=target)
        report["findings"] = []
        return report

    monkeypatch.setattr(planning_installer, "planning_report", _planning_report_without_findings)
    monkeypatch.setattr(memory_installer, "memory_report", _memory_report_without_findings)

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []


def test_doctor_module_filter_checks_llms_against_installed_modules(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "llms.txt: external-agent handoff file differs from the current workspace contract" not in payload["warnings"]
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    llms_action = next(action for action in workspace_report["actions"] if action["path"] == "llms.txt")
    assert llms_action["kind"] == "current"


def test_report_surfaces_planning_intent_validation_findings(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "EXT-quiet-open",
                        "title": "Quiet but open",
                        "status": "open",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any("Open external planning item EXT-quiet-open" in finding["message"] for finding in payload["findings"])
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    assert planning_report["intent_validation"]["counts"]["untracked_external_open_count"] == 1


def test_external_intent_refresh_github_writes_provider_agnostic_evidence(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "github",
                        "id": "#1",
                        "title": "Previous",
                        "status": "open",
                        "kind": "issue",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        assert command[:2] == ["gh", "issue"]
        assert command[command.index("--state") + 1] == "all"
        assert cwd == target
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert check is False
        return Result(
            json.dumps(
                [
                    {
                        "number": 1,
                        "title": "Open work",
                        "state": "OPEN",
                        "url": "https://github.com/acme/project/issues/1",
                        "labels": [{"name": "planning"}],
                        "createdAt": "2026-04-01T00:00:00Z",
                        "updatedAt": "2026-04-27T00:00:00Z",
                        "body": "## Issue kind\n\nChild slice\n\n## Parent issue or lane\n\n#10\n\n## Closed lane(s) to revisit\n\n#8, #9\n",
                        "comments": [{"body": "closeout"}],
                    },
                    {
                        "number": 2,
                        "title": "Closed work",
                        "state": "CLOSED",
                        "url": "https://github.com/acme/project/issues/2",
                        "labels": [],
                        "createdAt": "2026-04-01T00:00:00Z",
                        "updatedAt": "2026-04-26T00:00:00Z",
                        "body": "",
                        "comments": 0,
                    },
                ]
            )
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "external-intent-refresh/v1"
    assert payload["written"] is True
    assert payload["repository"] == "acme/project"
    assert payload["storage"] == "cache"
    assert payload["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert payload["state"] == "all"
    assert payload["state_source"] == "explicit"
    assert payload["limit_source"] == "product_default"
    assert payload["item_count"] == 2
    refreshed = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert refreshed["kind"] == "planning-external-intent-evidence/v1"
    assert refreshed["refresh_metadata"]["adapter"] == "github-gh-cli"
    assert refreshed["refresh_metadata"]["repository"] == "acme/project"
    assert refreshed["refresh_metadata"]["state"] == "all"
    assert refreshed["refresh_metadata"]["limit"] == 1000
    assert "previous_items" not in refreshed
    assert refreshed["items"][0]["id"] == "#1"
    assert refreshed["items"][0]["kind"] == "slice"
    assert refreshed["items"][0]["parent_id"] == "#10"
    assert refreshed["items"][0]["reopens"] == ["#8", "#9"]
    assert refreshed["items"][0]["labels"] == ["planning"]
    assert refreshed["items"][1]["status"] == "closed"


def test_external_intent_refresh_github_accepts_bom_and_recomputes_counts(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    previous = {
        "kind": "planning-external-intent-evidence/v1",
        "refresh_metadata": {"item_count": 1, "open_count": 1, "closed_count": 0},
        "items": [{"system": "github", "id": "#1", "status": "open"}],
    }
    evidence_path.write_bytes(("\ufeff" + json.dumps(previous, indent=2) + "\n").encode("utf-8"))

    class Result:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            [
                {
                    "number": 1,
                    "title": "Open work",
                    "state": "OPEN",
                    "url": "https://github.com/acme/project/issues/1",
                    "labels": [],
                    "createdAt": "2026-04-01T00:00:00Z",
                    "updatedAt": "2026-04-27T00:00:00Z",
                    "body": "",
                    "comments": 0,
                },
                {
                    "number": 2,
                    "title": "Closed work",
                    "state": "CLOSED",
                    "url": "https://github.com/acme/project/issues/2",
                    "labels": [],
                    "createdAt": "2026-04-01T00:00:00Z",
                    "updatedAt": "2026-04-27T00:00:00Z",
                    "body": "",
                    "comments": 0,
                },
            ]
        )

    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: Result())

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "all",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    refreshed_bytes = evidence_path.read_bytes()
    refreshed = json.loads(refreshed_bytes.decode("utf-8"))
    assert payload["previous_item_count"] == 1
    assert not refreshed_bytes.startswith(b"\xef\xbb\xbf")
    assert refreshed["refresh_metadata"]["item_count"] == 2
    assert refreshed["refresh_metadata"]["open_count"] == 1
    assert refreshed["refresh_metadata"]["closed_count"] == 1


def test_external_intent_refresh_github_rejects_count_drift(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refresh_metadata": {"item_count": 2, "open_count": 2, "closed_count": 0},
                "items": [{"system": "github", "id": "#1", "status": "open"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def fail_run(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("refresh should reject invalid existing evidence before calling gh")

    monkeypatch.setattr(cli.subprocess, "run", fail_run)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )

    assert excinfo.value.code == 2
    assert "refresh_metadata.item_count must equal 1 from items" in capsys.readouterr().err


def test_external_intent_refresh_github_uses_product_defaults_instead_of_previous_cache_scope(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    evidence_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refresh_metadata": {
                    "state": "all",
                    "limit": 600,
                },
                "items": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    observed_commands: list[list[str]] = []

    class Result:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, cwd, capture_output, text, encoding, check):
        observed_commands.append(command)
        assert cwd == target
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        assert check is False
        return Result("[]")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert observed_commands[-1][observed_commands[-1].index("--state") + 1] == "all"
    assert observed_commands[-1][observed_commands[-1].index("--limit") + 1] == "1000"
    assert payload["state"] == "all"
    assert payload["limit"] == 1000
    assert payload["state_source"] == "product_default"
    assert payload["limit_source"] == "product_default"
    refreshed = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert refreshed["refresh_metadata"]["state"] == "all"
    assert refreshed["refresh_metadata"]["limit"] == 1000
    assert refreshed["refresh_metadata"]["state_source"] == "product_default"
    assert refreshed["refresh_metadata"]["limit_source"] == "product_default"

    assert (
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--state",
                "open",
                "--limit",
                "50",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert observed_commands[-1][observed_commands[-1].index("--state") + 1] == "open"
    assert observed_commands[-1][observed_commands[-1].index("--limit") + 1] == "50"
    assert payload["state_source"] == "explicit"
    assert payload["limit_source"] == "explicit"


def test_external_intent_refresh_github_missing_gh_fails_without_snapshot_write(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    def fake_run(command, cwd, capture_output, text, encoding, check):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "external-intent",
                "refresh-github",
                "--target",
                str(target),
                "--repo",
                "acme/project",
                "--format",
                "json",
            ]
        )

    assert excinfo.value.code == 2
    assert not (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").exists()
    assert not (target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json").exists()


def test_report_surfaces_finished_work_inspection_findings(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    archive_dir = target / ".agentic-workspace" / "planning" / "execplans" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "system-intent-and-planning-trust-2026-04-21.md").write_text(
        "# System Intent And Planning Trust\n\n"
        "## Intent Satisfaction\n\n"
        "- Was original intent fully satisfied?: yes\n\n"
        "## Closure Check\n\n"
        "- Closure decision: archive-and-close\n"
        "- Larger-intent status: closed\n\n"
        "Implemented #220.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#260",
                        "title": "Finished-work intent inspection",
                        "status": "open",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                        "reopens": ["#220"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any("Archived closeout" in finding["message"] for finding in payload["findings"])
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    assert planning_report["finished_work_inspection"]["counts"]["likely_premature_closeout_count"] == 1


def test_report_surfaces_compact_lower_trust_closeout_summary(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#closed-without-residue",
                        "title": "Closed without planning residue",
                        "status": "closed",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["closeout_trust"]["status"] == "present"
    assert payload["closeout_trust"]["trust"] == "lower-trust"
    assert payload["closeout_trust"]["lower_trust_closeout_count"] == 1
    assert any("Closed external planning item #closed-without-residue" in item for item in payload["closeout_trust"]["sample_signals"])
    action = payload["closeout_trust"]["durable_residue_action"]
    assert action["action"] == "route-durable-residue"
    assert "lower-trust closeout signals" in action["summary"]


def test_report_text_surfaces_compact_lower_trust_closeout_summary(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace" / "planning" / "external-intent-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#closed-without-residue",
                        "title": "Closed without planning residue",
                        "status": "closed",
                        "kind": "lane",
                        "parent_id": "",
                        "planning_residue_expected": "required",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target)]) == 0

    text = capsys.readouterr().out
    assert "Maintenance pressure:" in text
    assert "attention" in text
    assert "maintenance-pressure detail" in text


def test_report_surfaces_active_planning_in_standing_intent_view(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        (target / ".agentic-workspace" / "planning" / "state.toml"),
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'standing-intent-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/standing-intent-slice.md', why_now = 'standing intent needs a durable owner.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "execplans" / "standing-intent-slice.md").write_text(
        "# Standing Intent Slice\n\n"
        "## Goal\n\n"
        "- Give standing intent a durable owner.\n\n"
        "## Non-Goals\n\n"
        "- None.\n\n"
        "## Intent Continuity\n\n"
        "- Larger intended outcome: make durable repo guidance recoverable.\n"
        "- This slice completes the larger intended outcome: no\n"
        "- Continuation surface: state.toml candidate lane `standing-intent-durability`\n\n"
        "## Required Continuation\n\n"
        "- Required follow-on for the larger intended outcome: yes\n"
        "- Owner surface: .agentic-workspace/planning/state.toml\n"
        "- Activation trigger: precedence rules still need to land.\n\n"
        "## Iterative Follow-Through\n\n"
        "- What this slice enabled: standing intent is classifiable.\n"
        "- Intentionally deferred: precedence rules.\n"
        "- Discovered implications: reporting should surface effective standing intent.\n"
        "- Proof achieved now: pending\n"
        "- Validation still needed: pending\n"
        "- Next likely slice: precedence and supersession.\n\n"
        "## Delegated Judgment\n\n"
        "- Requested outcome: Give standing intent a durable owner.\n"
        "- Hard constraints: Keep the first slice compact.\n"
        "- Agent may decide locally: the smallest report shape.\n"
        "- Escalate when: a new source of truth would be required.\n\n"
        "## Active Milestone\n\n"
        "- Status: in-progress\n"
        "- Scope: ship standing-intent classification and reporting.\n"
        "- Ready: ready\n"
        "- Blocked: none\n"
        "- optional_deps: none\n\n"
        "## Immediate Next Action\n\n"
        "- Add the standing-intent report view.\n\n"
        "## Blockers\n\n"
        "- None.\n\n"
        "## Touched Paths\n\n"
        "- .agentic-workspace/docs/standing-intent-contract.md\n\n"
        "## Invariants\n\n"
        "- Standing intent stays subordinate to owner surfaces.\n\n"
        "## Validation Commands\n\n"
        "- uv run agentic-workspace report --target ./repo --format json\n\n"
        "## Completion Criteria\n\n"
        "- Standing intent is visible in reporting.\n\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    standing_classes = {item["class"]: item for item in payload["standing_intent"]["effective_view"]["items"]}
    active_direction = standing_classes["active_directional_intent"]
    assert active_direction["status"] == "present"
    assert active_direction["owner_surface"] == ".agentic-workspace/planning/execplans/standing-intent-slice.md"
    assert active_direction["summary"] == "Add the standing-intent report view."
    assert active_direction["requested_outcome"] == "Give standing intent a durable owner."
    assert payload["standing_intent"]["precedence_order"][1]["rule"] == (
        "Active planning direction governs the current bounded slice unless it conflicts with checked-in hard policy."
    )
    assert payload["standing_intent"]["supersession_rules"][2]["rule"] == "active_lane_direction_is_slice_scoped"
    assert payload["standing_intent"]["stronger_home_model"]["candidate_classes"][1]["class"] == "active_directional_intent"


def test_report_surfaces_combined_execution_shape_for_planning_backed_slice(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.local.toml").write_text(
        "schema_version = 1\n\n"
        "[runtime]\n"
        "supports_internal_delegation = true\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = true\n\n"
        "[handoff]\n"
        "prefer_internal_delegation_when_available = true\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'execution-shape-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/execution-shape-slice.md', why_now = 'make default execution shape visible.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "planning" / "execplans").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "execplans" / "execution-shape-slice.md").write_text(
        "# Execution Shape Slice\n\n"
        "## Goal\n\n"
        "- Make default execution shape visible.\n\n"
        "## Non-Goals\n\n"
        "- Add scheduler behavior.\n\n"
        "## Intent Continuity\n\n"
        "- Larger intended outcome: make config-backed execution posture decisive.\n"
        "- This slice completes the larger intended outcome: yes\n"
        "- Continuation surface: none\n\n"
        "## Required Continuation\n\n"
        "- Required follow-on for the larger intended outcome: no\n"
        "- Owner surface: none\n"
        "- Activation trigger: none\n\n"
        "## Iterative Follow-Through\n\n"
        "- What this slice enabled: one compact execution-shaping answer.\n"
        "- Intentionally deferred: none\n"
        "- Discovered implications: deviations should stay visible.\n"
        "- Proof achieved now: pending\n"
        "- Validation still needed: pending\n"
        "- Next likely slice: none.\n\n"
        "## Delegated Judgment\n\n"
        "- Requested outcome: Make default execution shape visible.\n"
        "- Hard constraints: Keep it advisory and config-driven.\n"
        "- Agent may decide locally: the smallest combined report surface.\n"
        "- Escalate when: a new source of truth would be required.\n\n"
        "## Capability Posture\n\n"
        "- Execution class: boundary-shaping\n"
        "- Recommended strength: strong\n"
        "- Preferred location: either\n"
        "- Delegation friendly: yes\n"
        "- Strong external reasoning: allowed\n"
        "- Why: contract shaping needs stronger judgment before bounded follow-through.\n\n"
        "## Active Milestone\n\n"
        "- ID: execution-shape\n"
        "- Status: in-progress\n"
        "- Scope: expose one combined execution recommendation.\n"
        "- Ready: ready\n"
        "- Blocked: none\n"
        "- optional_deps: none\n\n"
        "## Immediate Next Action\n\n"
        "- Add the combined execution-shape report answer.\n\n"
        "## Blockers\n\n"
        "- None.\n\n"
        "## Touched Paths\n\n"
        "- src/agentic_workspace/cli.py\n\n"
        "## Invariants\n\n"
        "- Config remains posture rather than scheduler policy.\n\n"
        "## Validation Commands\n\n"
        "- uv run pytest tests/test_workspace_cli.py -q\n\n"
        "## Completion Criteria\n\n"
        "- One combined execution-shape answer is visible.\n\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    execution_shape = payload["execution_shape"]
    assert execution_shape["status"] == "present"
    assert execution_shape["task_shape"]["id"] == "planning-backed-broad-work"
    assert execution_shape["default_posture"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert execution_shape["default_posture"]["handoff_preference"] == "prefer-internal-when-safe"
    assert execution_shape["capability_posture"]["execution class"] == "boundary-shaping"
    assert execution_shape["recommendation"]["id"] == "planner-first-then-bounded-executor"
    assert execution_shape["recommendation"]["consult"] == ["agentic-planning handoff --format json"]
    assert execution_shape["recommendation"]["best_target_fits"] == []
    assert execution_shape["current_slice"]["task_id"] == "execution-shape-slice"
    assert execution_shape["resolved_targets"] == []
    assert "active execplan" in execution_shape["task_shape"]["summary"]


def test_report_surfaces_agent_efficiency_output_contract_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["output_contract"]["optimization_bias"] == "agent-efficiency"
    assert payload["output_contract"]["optimization_bias_source"] == "repo-config"
    assert payload["output_contract"]["report_density"] == "compact"
    assert "execution method" in payload["output_contract"]["must_not_change"]
    assert payload["operating_posture"]["optimization_bias"]["mode"] == "agent-efficiency"
    assert payload["operating_posture"]["optimization_bias"]["residue_density"] == "compact-carry-forward"


def test_report_text_mentions_agent_efficiency_bias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\noptimization_bias = "agent-efficiency"\n',
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target)]) == 0

    text = capsys.readouterr().out
    assert "Output bias: agent-efficiency (repo-config)" in text
    assert "Rendering: keep this view terse" in text


def test_default_command_outputs_stay_router_sized(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    budgets = {
        "start": (["start", "--target", str(target), "--format", "json"], 9000),
        "summary": (["summary", "--target", str(target), "--format", "json"], 13000),
        "report": (["report", "--target", str(target), "--format", "json"], 18000),
        "proof": (
            ["proof", "--target", str(target), "--changed", ".agentic-workspace/config.toml", "--format", "json"],
            9000,
        ),
        "status": (["status", "--target", str(target), "--format", "json"], 25000),
    }
    for command_name, (args, budget) in budgets.items():
        assert cli.main(args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(json.dumps(payload, sort_keys=True)) <= budget, command_name

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert "mixed_agent" not in status_payload["config"]
    assert status_payload["config"]["detail_command"] == "agentic-workspace config --target ./repo --profile compact --format json"
    assert status_payload["deeper_detail"]["report_command"] == "agentic-workspace report --target ./repo --profile full --format json"


def test_report_surfaces_large_file_hotspots_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "balanced"\n',
        encoding="utf-8",
    )
    (target / "src").mkdir()
    (target / "src" / "big_module.py").write_text("\n".join(f"line_{index}" for index in range(450)) + "\n")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "balanced"
    assert payload["repo_friction"]["initiative_posture"] == "bounded-evidence-backed-action"
    assert payload["repo_friction"]["large_file_hotspots"]["count"] == 1
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["path"] == "src/big_module.py"
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["line_count"] == 450
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["kind"] == "code"
    hotspot = payload["repo_friction"]["large_file_hotspots"]["items"][0]
    assert hotspot["classification"] == "large-source-hotspot"
    assert hotspot["suggested_action"] == "inspect-symbols-before-refactor"
    assert "Use search and focused symbols first" in hotspot["context_strategy"]
    assert hotspot["primary_next_action"]["action"] == "inspect-symbols-before-refactor"
    assert hotspot["primary_next_action"]["run"] == hotspot["primary_next_action"]["command"]
    signal = payload["improvement_intake"]["improvement_signal_candidates"][0]
    assert signal["candidate_kind"] == "workspace-improvement-signal-candidate/v1"
    assert signal["kind"] == "architecture_cost"
    assert signal["suspected_owner"] == "src/big_module.py"
    assert signal["immediate_action"] == "route"
    assert signal["classification"] == "large-source-hotspot"
    assert signal["suggested_action"] == "inspect-symbols-before-refactor"
    assert signal["primary_next_action"]["action"] == "inspect-symbols-before-refactor"


def test_report_does_not_promote_regenerable_cache_as_large_file_friction(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    cache_path = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("\n".join(f"line_{index}" for index in range(950)) + "\n", encoding="utf-8")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    large_files = payload["repo_friction"]["large_file_hotspots"]
    assert large_files["count"] == 0
    assert large_files["ignored_regenerable_cache_count"] == 1
    ignored = large_files["ignored_regenerable_caches"][0]
    assert ignored["path"] == ".agentic-workspace/local/cache/external-intent-evidence.json"
    assert ignored["surface_role"] == "regenerable-local-cache"
    assert ignored["suggested_action"] == "do-not-refactor"
    assert "local cache" in large_files["cache_rule"]
    assert payload["improvement_intake"]["improvement_signal_candidates"] == []


def test_report_surfaces_concept_hotspots_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "docs").mkdir()
    _write(
        (target / "docs" / "routing-contract.md"),
        "\n".join(f"line_{index}" for index in range(220)) + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["concept_surface_hotspots"]["count"] == 1
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["path"] == "docs/routing-contract.md"
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["kind"] == "docs"
    assert payload["repo_friction"]["concept_surface_hotspots"]["items"][0]["surface_role"] == "canonical-doc"


def test_report_consumes_external_codebase_map_when_present(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "tools").mkdir()
    (target / "tools" / "codebase-map.json").write_text(
        json.dumps(
            {
                "large_modules": [
                    {
                        "path": "src/generated_hotspot.py",
                        "line_count": 900,
                        "function_count": 12,
                        "class_count": 1,
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
        "external_evidence",
    ]
    assert payload["repo_friction"]["external_evidence"][0]["kind"] == "codebase-map"
    assert payload["repo_friction"]["external_evidence"][0]["path"] == "tools/codebase-map.json"
    assert payload["repo_friction"]["external_evidence"][0]["status"] == "loaded"
    assert payload["repo_friction"]["external_evidence"][0]["items"][0]["path"] == "src/generated_hotspot.py"
    assert payload["repo_friction"]["external_evidence"][0]["items"][0]["line_count"] == 900


def test_report_surfaces_promotable_setup_findings_as_repo_friction_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "tools").mkdir()
    (target / "tools" / "setup-findings.json").write_text(
        json.dumps(
            {
                "kind": "workspace-setup-findings/v1",
                "findings": [
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Validation repeatedly fails after agents hand-author schema shape.",
                        "confidence": 0.9,
                        "path": "src/agentic_workspace/cli.py",
                        "observed_during": "uv run pytest tests/test_workspace_cli.py",
                        "signal_kind": "validation_friction",
                        "cost": "Agents spend extra repair loops fixing shape that a writer helper could construct.",
                        "suspected_owner": "agentic-workspace create-review",
                        "likely_remediation": "scaffold",
                        "recurrence": "repeated",
                        "validation_failure_class": "interface_design_error",
                        "refs": [".agentic-workspace/docs/reporting-contract.md"],
                    },
                    {
                        "class": "repo_friction_evidence",
                        "summary": "Low-confidence note stays transient.",
                        "confidence": 0.4,
                        "path": "src/ignored.py",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["evidence_classes"] == [
        "large_file_hotspots",
        "concept_surface_hotspots",
        "planning_friction",
        "validation_friction",
        "external_evidence",
    ]
    setup_findings = next(evidence for evidence in payload["repo_friction"]["external_evidence"] if evidence["kind"] == "setup-findings")
    assert setup_findings["path"] == "tools/setup-findings.json"
    assert setup_findings["items"][0]["path"] == "src/agentic_workspace/cli.py"
    assert setup_findings["items"][0]["validation_failure_class"] == "interface_design_error"
    assert setup_findings["items"][0]["promotion_reason"] == "grounded friction evidence is worth preserving"
    signal = payload["improvement_intake"]["improvement_signal_candidates"][0]
    assert signal["kind"] == "validation_friction"
    assert signal["observed_during"] == "uv run pytest tests/test_workspace_cli.py"
    assert signal["suspected_owner"] == "agentic-workspace create-review"
    assert signal["likely_remediation"] == "scaffold"
    assert signal["recurrence"] == "repeated"
    assert signal["validation_failure_class"] == "interface_design_error"
    assert payload["improvement_intake"]["setup_findings"]["status"] == "loaded"
    assert payload["improvement_intake"]["setup_findings"]["loaded_count"] == 2
    assert payload["improvement_intake"]["setup_findings"]["promotable_counts"]["repo_friction_evidence"] == 1
    assert payload["improvement_intake"]["setup_findings"]["transient_count"] == 1


def test_report_surfaces_reporting_only_repo_friction_posture(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nimprovement_latitude = "reporting"\n',
        encoding="utf-8",
    )
    (target / "docs").mkdir()
    (target / "docs" / "big_note.md").write_text("\n".join(f"line_{index}" for index in range(450)) + "\n")

    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "reporting"
    assert payload["repo_friction"]["policy_target"] == "repo-directed-improvement"
    assert payload["repo_friction"]["friction_response_order"][2]["action"] == "avoid-externalizing-honestly-absorbable-friction"
    assert payload["repo_friction"]["initiative_posture"] == "reporting-only"
    assert payload["repo_friction"]["incidental_finding_policy"]["status"] == "required-reporting"
    assert "separate acted-on improvements" in payload["repo_friction"]["incidental_finding_policy"]["report_how"][1]
    assert payload["repo_friction"]["rule"] == (
        "Surface notable friction through bounded reporting or residue; do not act on it without explicit direction."
    )
    assert payload["repo_friction"]["reporting_destinations"] == [
        "agentic-workspace report --target ./repo --format json",
        "review outputs",
        ".agentic-workspace/planning/state.toml or the active execplan when the current slice already owns planning residue",
    ]


def test_status_real_init_reports_workspace_health(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "status"
    assert payload["modules"] == ["planning", "memory"]
    assert "health" in payload
    assert payload["registry"][0]["name"] == "planning"
    assert payload["registry"][1]["installed"] is True
    assert not any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])
    assert not any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_status_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])


def test_doctor_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "OWNERSHIP.toml").unlink()
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_doctor_json_exposes_standardised_summary_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "WORKFLOW.md"), "# Workflow\n")
    _write((tmp_path / ".agentic-workspace" / "OWNERSHIP.toml"), "schema_version = 1\n")
    _write((tmp_path / ".agentic-workspace" / "docs" / "module-map.md"), "# Installed Module Map\n")
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "REGISTRY.json"),
        '{"schema_version":"skill-registry.v1","owner":"agentic-workspace","source_kind":"installed-workspace-skills","skills":[]}\n',
    )
    _write((tmp_path / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.md"), "# Workspace Startup\n")
    _write((tmp_path / ".agentic-workspace" / "skills" / "workspace-work-shape" / "SKILL.md"), "# Workspace Work Shape\n")
    _write(
        (tmp_path / ".agentic-workspace" / "skills" / "workspace-setup-jumpstart" / "SKILL.md"),
        "# Workspace Setup Jumpstart\n",
    )
    _write((tmp_path / ".agentic-workspace" / "system-intent" / "WORKFLOW.md"), "# System Intent Workflow\n")
    _write(
        (tmp_path / "AGENTS.md"),
        "# Agent Instructions\n\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        'For non-trivial requests, first run `agentic-workspace start --profile tiny --task "<task>" --format json` using the user\'s request as `<task>`; follow `immediate_next_allowed_action` and `skill_routing` before opening raw `.agentic-workspace` files. Use `preflight` for takeover or recovery. If unavailable, read `.agentic-workspace/WORKFLOW.md`.\n'
        "<!-- agentic-workspace:workflow:end -->\n\n"
        "Local repo instructions.\n",
        encoding="utf-8",
    )
    (tmp_path / "llms.txt").write_text(cli._external_agent_handoff_text(selected_modules=["planning", "memory"]))
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["doctor", "--modules", "planning,memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["created"] == ["planning", "memory"]
    assert payload["updated_managed"] == []
    assert payload["preserved_existing"] == []
    assert payload["needs_review"] == []
    assert payload["generated_artifacts"] == []
    assert payload["registry"][0]["name"] == "planning"


def test_status_warns_when_redundant_memory_pointer_block_remains(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    agents_path = target / "AGENTS.md"
    _write(
        agents_path,
        agents_path.read_text(encoding="utf-8").replace(
            "<!-- agentic-workspace:workflow:end -->\n",
            "<!-- agentic-workspace:workflow:end -->\n\n"
            "<!-- agentic-memory:workflow:start -->\n"
            "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
            "<!-- agentic-memory:workflow:end -->\n",
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any("redundant top-level memory workflow pointer block still present" in warning for warning in payload["warnings"])


def test_doctor_real_init_preserves_package_contract_shortlists_in_reports(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_report = next(report for report in payload["reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["reports"] if report["module"] == "memory")

    assert any(
        action["path"] == ".agentic-workspace/planning/agent-manifest.json"
        and "compatibility contract files:" in action["detail"]
        and "AGENTS.md" in action["detail"]
        for action in planning_report["actions"]
    )
    assert any(
        action["path"] == ".agentic-workspace/memory/UPGRADE-SOURCE.toml"
        and "lower-stability helper files:" in action["detail"]
        and ".agentic-workspace/memory/UPGRADE-SOURCE.toml" in action["detail"]
        for action in memory_report["actions"]
    )


def test_doctor_text_output_shows_package_contract_shortlists(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "[planning] Doctor report" in output
    assert "[memory] Doctor report" in output
    assert "compatibility contract files:" in output
    assert "lower-stability helper files:" in output


def test_doctor_real_init_reports_stale_planning_generated_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    (target / "tools" / "AGENT_ROUTING.md").write_text("stale generated routing\n")
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "healthy"
    assert not any(".agentic-workspace/planning/agent-manifest.json" in item for item in payload["needs_review"])


def test_preflight_command_active_only_returns_compact_planning_state(capsys) -> None:
    """Test that preflight --active-only returns only active planning state for efficient polling."""
    assert cli.main(["preflight", "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "preflight-response/v1"
    assert payload["mode"] == "active-state-only"
    assert "planning_record" in payload
    assert "timestamp_hint" in payload


def test_preflight_command_full_returns_bundled_takeover_context(capsys) -> None:
    """Test that preflight returns bundled startup + config + active state for takeover recovery."""
    assert cli.main(["preflight", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "preflight-response/v1"
    assert payload["mode"] == "full-takeover-context"
    assert "startup_guidance" in payload
    assert "resolved_config" in payload
    assert "active_planning_state" in payload
    assert "timestamp_hint" in payload

    # Verify startup guidance is present and correct
    startup = payload["startup_guidance"]
    assert startup["context_router"]["kind"] == "workspace-context-router-family/v1"
    assert startup["context_router"]["views"][0]["view"] == "start"
    assert startup["entrypoint"] == "AGENTS.md"
    assert "first_compact_queries" in startup
    assert any("agentic-workspace" in q for q in startup["first_compact_queries"])
    assert startup["primary_next_action"]["action"] in {"continue-active-planning-record", "use-preflight-context"}
    assert startup["primary_next_action"]["risk"] == "read-only routing"
    assert startup["primary_next_action"]["required_inputs"] == ["target repo", "current task"]
    assert startup["primary_next_action"]["next_proof"] == "select proof after changed paths are known"
    assert startup["work_intent_gate"]["levels"][2]["id"] == "lane"
    assert "checked-in planning" in startup["work_intent_gate"]["rule"]
    assert "vague_outcome_orientation" not in startup
    assert startup["skill_routing"]["status"] == "advisory"
    configured_cli = payload["resolved_config"]["workspace_config"]["cli_invoke"]
    assert startup["skill_routing"]["query"] == f'{configured_cli} skills --target ./repo --task "<task>" --format json'
    assert "planning-autopilot" not in {route["skill"] for route in startup["skill_routing"]["preferred_routes"]}
    assert startup["skill_routing"]["enabled_advanced_routes"] == ["external_adapters", "review_artifacts"]

    # Verify config is present
    config = payload["resolved_config"]
    assert "workspace_config" in config
    assert "agent_instructions_file" in config
    assert config["agent_instructions_file"] == "AGENTS.md"


def test_preflight_command_with_target_argument(tmp_path: Path, capsys) -> None:
    """Test that preflight --target works to specify a target repository."""
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["preflight", "--target", str(target), "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "preflight-response/v1"
    assert target.as_posix() in payload["target"]


def test_preflight_task_surfaces_vague_outcome_orientation(capsys) -> None:
    assert (
        cli.main(
            [
                "preflight",
                "--task",
                "I want this repo to feel more trustworthy when agents hand work back after a long task",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    orientation = payload["startup_guidance"]["vague_outcome_orientation"]
    assert orientation["status"] == "applicable"
    assert orientation["applies_to_current_task"] is True
    assert orientation["first_surface"].startswith("startup_guidance.primary_next_action")
    assert "agentic-workspace start" in orientation["compact_commands"][1]
    assert "intended outcome" in orientation["answer_contract"][0]


def test_preflight_command_emits_gate_token(capsys) -> None:
    assert cli.main(["preflight", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["issued_at"]
    assert payload["preflight_token"].startswith("preflight-v1:")


def test_preflight_surfaces_closeout_workflow_obligations_for_active_scope(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[workflow_obligations.dogfooding_lane_closeout]\n"
        'summary = "Run dogfooding closeout review."\n'
        'stage = "closeout"\n'
        'scope_tags = ["planning", "memory", "dogfooding"]\n'
        'commands = ["agentic-workspace skills --target . --task dogfooding --format json"]\n'
        'review_hint = "Route lane friction before claiming completion."\n',
    )
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'dogfood-closeout', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/dogfood.plan.json', why_now = 'closeout should not be optional.', next_action = 'make closeout obligations visible.', done_when = 'preflight surfaces closeout obligations.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
    )

    assert cli.main(["preflight", "--target", str(target), "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    obligations = payload["closeout_obligations"]["required_before_lane_closeout"]
    assert payload["workflow_obligations"]["configured_count"] == 1
    assert payload["workflow_obligations"]["match_evidence"]["match_count"] == 1
    assert payload["workflow_obligations"]["match_evidence"]["matching"][0]["matched_scope_tags"] == ["planning"]
    assert payload["closeout_obligations"]["status"] == "present"
    primary = payload["closeout_obligations"]["primary_next_action"]
    assert primary["action"] == "run-closeout-obligation"
    assert primary["id"] == "dogfooding_lane_closeout"
    assert primary["command"] == "agentic-workspace skills --target . --task dogfooding --format json"
    assert primary["required_inputs"] == ["active planning record", "validation results", "issue or lane scope"]
    assert "route durable residue" in primary["next_proof"]
    assert obligations[0]["id"] == "dogfooding_lane_closeout"
    assert obligations[0]["stage"] == "closeout"


def test_preflight_surfaces_closeout_workflow_obligations_as_standing_requirement(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[workspace]\n"
        'improvement_latitude = "proactive"\n'
        'optimization_bias = "agent-efficiency"\n\n'
        "[workflow_obligations.dogfooding_lane_closeout]\n"
        'summary = "Run dogfooding closeout review without explicit prompting."\n'
        'stage = "closeout"\n'
        'scope_tags = ["planning", "dogfooding", "self-improvement"]\n'
        'commands = ["agentic-workspace report --target . --section workflow_obligations --format json"]\n'
        'review_hint = "Surface actionable findings clearly."\n',
    )

    assert cli.main(["preflight", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    obligations = payload["closeout_obligations"]["required_before_lane_closeout"]
    assert payload["workflow_obligations"]["match_evidence"]["match_count"] == 0
    assert payload["closeout_obligations"]["status"] == "present"
    assert payload["closeout_obligations"]["primary_next_action"]["id"] == "dogfooding_lane_closeout"
    assert obligations[0]["review_hint"] == "Surface actionable findings clearly."
    posture = payload["operating_posture"]
    assert posture["improvement_latitude"]["mode"] == "proactive"
    assert posture["improvement_latitude"]["initiative_posture"] == "bounded-standalone-action-allowed"
    assert posture["optimization_bias"]["mode"] == "agent-efficiency"
    assert posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert posture["incidental_finding_policy"]["status"] == "required-reporting"


def test_preflight_active_only_includes_active_todo_without_execplan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'preflight-recovery-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/preflight-recovery.plan.json', why_now = 'takeover recovery should still surface the active lane.', next_action = 'land the preflight fix.', done_when = 'active state remains visible without an execplan.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
    )

    assert cli.main(["preflight", "--target", str(target), "--active-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["operating_posture"]["surface"] == "preflight"
    assert "incidental_finding_policy" not in payload["operating_posture"]
    assert payload["planning_record"]["status"] == "unavailable"
    active_state = payload["active_planning_state"]
    assert active_state["todo"]["active_count"] == 1
    assert active_state["todo"]["active_items"][0]["id"] == "preflight-recovery-slice"
    assert active_state["execplans"]["active_count"] == 0


def test_preflight_full_includes_active_todo_without_execplan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'preflight-recovery-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/preflight-recovery.plan.json', why_now = 'takeover recovery should still surface the active lane.', next_action = 'land the preflight fix.', done_when = 'active state remains visible without an execplan.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
    )

    assert cli.main(["preflight", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    active_state = payload["active_planning_state"]
    assert active_state["planning_record"]["status"] == "unavailable"
    assert active_state["todo"]["active_count"] == 1
    assert active_state["todo"]["active_items"][0]["next_action"] == "land the preflight fix."
    guidance = payload["startup_guidance"]
    assert guidance["entry_query"] == 'uv run agentic-workspace start --profile tiny --task "<task>" --format json'
    assert guidance["escalation_rules"][0]["load_next"][0] == "uv run agentic-workspace defaults --section startup --format json"
    assert guidance["skill_routing"]["preferred_routes"][0]["fallback"] == "uv run agentic-workspace summary --format json"


def test_start_command_returns_minimum_safe_startup_context(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "    { id = 'startup-slice', status = 'in-progress', surface = '.agentic-workspace/planning/execplans/startup.plan.json', why_now = 'keep startup cheap.', next_action = 'run the compact startup path.', done_when = 'startup is bounded.' }\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\n"
        "lanes = []\n"
        "candidates = []\n",
    )

    assert cli.main(["start", "--target", str(target), "--changed", "src/agentic_workspace/cli.py", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    assert "cli_compatibility" not in payload
    assert payload["kind"] == "startup-context/v1"
    assert payload["startup_sequence"][0]["surface"] == "AGENTS.md"
    assert payload["startup_sequence"][1]["command"] == "uv run agentic-workspace preflight --format json"
    assert payload["startup_sequence"][2]["command"] == "uv run agentic-workspace summary --format json"
    assert payload["context_router"]["views"][0]["command"] == "uv run agentic-workspace start --target ./repo --profile tiny --format json"
    assert payload["feature_tier"]["active"]["id"] == "planning"
    assert payload["feature_tier"]["active"]["modules"] == ["planning"]
    assert payload["feature_tier"]["active"]["source"] == "selected_modules"
    assert "available_tiers" not in payload["feature_tier"]
    assert payload["immediate_next_allowed_action"]["read_first"] == [
        "uv run agentic-workspace summary --format json",
    ]
    assert payload["immediate_next_allowed_action"]["action"] == "continue-active-planning-record"
    assert payload["immediate_next_allowed_action"]["command"] == "uv run agentic-workspace summary --format json"
    assert payload["immediate_next_allowed_action"]["risk"] == "read-only routing"
    assert payload["immediate_next_allowed_action"]["required_inputs"] == ["target repo", "current task"]
    assert payload["immediate_next_allowed_action"]["next_proof"] == "run proof selection once changed paths are known"
    assert payload["active_state_summary"]["todo_active_count"] == 1
    assert payload["authority_markers"][0] == {
        "path": "AGENTS.md",
        "authority": "adapter",
        "canonical_source": ".agentic-workspace/config.toml + agentic-workspace start --format json",
        "safe_to_edit": True,
        "refresh_command": None,
    }
    assert payload["immediate_next_allowed_action"]["summary"] == "run the compact startup path."
    assert "vague_outcome_orientation" not in payload
    assert payload["skill_routing"]["status"] == "advisory"
    assert payload["skill_routing"]["query"] == 'uv run agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert "planning-autopilot" not in {route["skill"] for route in payload["skill_routing"]["preferred_routes"]}
    assert payload["skill_routing"]["available_advanced_route_command"] == "uv run agentic-workspace modules --target ./repo --format json"
    assert payload["skill_routing"]["fallback_when_skills_unavailable_count"] == 3
    assert "compact CLI routers" in payload["skill_routing"]["fallback_detail"]
    assert payload["workflow_obligations"]["configured_count"] == 0
    assert "configured" not in payload["workflow_obligations"]
    assert payload["closeout_obligations"]["required_before_lane_closeout_count"] == 0
    assert "required_before_lane_closeout" not in payload["closeout_obligations"]
    assert payload["memory_consult"]["kind"] == "agentic-workspace/memory-consult/v1"
    assert payload["memory_consult"]["do_not_bulk_read"] is True
    posture = payload["operating_posture"]
    assert posture["surface"] == "start"
    assert posture["improvement_latitude"]["mode"] == "conservative"
    assert posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert posture["detail_sections"]["improvement"] == (
        "uv run agentic-workspace report --target ./repo --section repo_friction --format json"
    )
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"]["mode"] == "suggest"
    assert payload["delegation_decision"]["decision"] in {
        "stay-local",
        "suggest-delegation",
        "suggest-downroute",
        "suggest-escalation",
        "manual-handoff",
        "ask-human",
    }
    assert len(json.dumps(payload, sort_keys=True)) < 15300
    assert payload["proof"]["required_commands"] == [
        "uv run pytest tests -q",
        "uv run ruff check src tests",
        "agentic-workspace defaults --section root_cli_authority --format json",
    ]
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "hand-owned-executable"
    assert payload["path_boundaries"] == [
        {
            "path": "src/agentic_workspace/cli.py",
            "authority": "source",
            "warning": None,
            "requires_attention": False,
        }
    ]


def test_start_tiny_profile_returns_first_contact_projection(capsys) -> None:
    task = "Start the way the repo instructs a new agent to start. Do not implement anything yet."
    assert cli.main(["start", "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded) < 6500
    assert payload["kind"] == "startup-context/v1"
    assert payload["startup_sequence"] == [
        {
            "id": "entrypoint",
            "command": None,
            "surface": "AGENTS.md",
            "why": "configured ordinary repo startup entrypoint",
        }
    ]
    assert payload["context_router"]["first_view"] == "start"
    assert (
        payload["context_router"]["detail_commands"]["known_changed_paths"]
        == "agentic-workspace implement --profile tiny --changed <paths> --format json"
    )
    assert payload["context_router"]["detail_commands"]["takeover_or_recovery"] == "agentic-workspace preflight --format json"
    assert payload["active_state_summary"]["todo_active_count"] >= 0
    assert payload["immediate_next_allowed_action"]["action"] in {"choose-smallest-workflow-shape", "continue-active-planning-record"}
    assert "implement --profile tiny --changed <paths>" in payload["immediate_next_allowed_action"]["summary"]
    assert payload["skill_routing"]["query"] == 'uv run agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"]["mode"] == "suggest"
    assert payload["delegation_decision"]["required_next_action"] in {
        "continue-local",
        "mention-suggestion",
        "prepare-handoff",
        "execute-when-safe",
        "stop-and-ask-human",
    }
    assert "durable_intent" not in payload
    assert "cli_compatibility" not in payload
    assert "proof" not in payload
    assert len(payload["authority_markers"]) == 1


def test_start_tiny_respects_ask_first_clarification_mode(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[clarification]",
                'mode = "ask-first"',
            ]
        ),
    )

    assert cli.main(["start", "--target", str(tmp_path), "--profile", "tiny", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    decision = payload["delegation_decision"]
    assert decision["decision"] == "ask-human"
    assert decision["required_next_action"] == "stop-and-ask-human"
    assert decision["manual_prompt"]["target"] == "human-or-external-strong-general-purpose-model"
    assert decision["clarification_mode"] == "ask-first"


def test_start_task_surfaces_vague_outcome_orientation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--task",
                "Agents keep making me repeat what I meant after they finish",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    orientation = payload["vague_outcome_orientation"]
    assert orientation["status"] == "applicable"
    assert orientation["raw_read_rule"].startswith("Open raw .agentic-workspace files only after compact output")
    assert "skill_routing" in payload


def test_start_task_includes_compact_skill_recommendations(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--task",
                "decompose an epic into lanes before execplans",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    recommendations = payload["skill_routing"]["task_recommendations"]
    assert recommendations["status"] == "recommended"
    assert recommendations["top_recommendations"][0]["id"] == "planning-decompose"
    assert recommendations["top_recommendations"][0]["path"] == ".agentic-workspace/planning/skills/planning-decompose/SKILL.md"
    assert "reasons" not in recommendations["top_recommendations"][0]


def test_preflight_task_includes_skill_recommendations(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning", "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "preflight",
                "--target",
                str(target),
                "--task",
                "tighten a new execplan before coding",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    recommendations = payload["startup_guidance"]["skill_routing"]["task_recommendations"]
    assert recommendations["status"] == "recommended"
    assert recommendations["top_recommendations"][0]["id"] == "planning-new-plan-tighten"
    assert "phrase match" in " ".join(recommendations["top_recommendations"][0]["reasons"])


def test_summary_command_includes_memory_consult(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["memory_consult"]["kind"] == "agentic-workspace/memory-consult/v1"
    assert payload["memory_consult"]["do_not_bulk_read"] is True


def test_memory_consult_uses_local_cli_invoke_for_memory_helpers(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["report", "--target", str(target), "--section", "memory_consult", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_consult = payload["answer"]
    assert memory_consult["capture_helper"].startswith("uv run agentic-memory capture-note")
    assert memory_consult["promotion_pressure"]["command"].startswith("uv run agentic-memory promotion-report")


def test_repo_config_cli_invoke_is_ignored_as_machine_local_policy(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["cli_invoke"] == "agentic-workspace"
    assert payload["workspace"]["cli_invoke_source"] == "product-default"
    assert payload["warnings"] == [".agentic-workspace/config.toml [workspace] contains unsupported field(s): cli_invoke."]


def test_config_reports_satisfied_repo_owned_cli_compatibility_expectation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[cli_compatibility]\n"
        'enforcement = "blocking"\n'
        'minimum_version = "0.0.0"\n'
        'source_classes = ["source-checkout"]\n'
        'target_relations = ["outside-target"]\n'
        'command = "uv run agentic-workspace"\n',
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="satisfied")
    assert compatibility["configured"] is True
    assert compatibility["enforcement"] == "blocking"
    assert compatibility["expected_command"] == "uv run agentic-workspace"
    assert compatibility["failed_checks"] == []
    checks = {check["name"]: check for check in compatibility["checks"]}
    assert checks["minimum_version"]["satisfied"] is True
    assert checks["source_class"]["satisfied"] is True
    assert checks["target_relation"]["satisfied"] is True


def test_status_reports_advisory_cli_compatibility_drift(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "advisory"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="advisory-drift")
    assert compatibility["enforcement"] == "advisory"
    assert compatibility["failed_checks"] == ["exact_version"]
    assert payload["health"] == "attention-needed"
    assert payload["executable_drift_warnings"][0].startswith("executable compatibility advisory-drift")
    assert compatibility["drift_findings"][0]["class"] == "executable-version-drift"
    assert compatibility["remediation"]["payload_drift_separate"] is True


def test_doctor_reports_cli_executable_drift_with_concrete_next_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "blocking"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="blocking-drift")
    assert payload["health"] == "attention-needed"
    assert compatibility["failed_checks"] == ["exact_version"]
    assert compatibility["remediation"]["action"] == "upgrade-or-select-cli"
    action = payload["manual_review_actions"][0]
    assert action["id"] == "resolve-cli-executable-drift"
    assert action["severity"] == "error"
    assert action["cli_compatibility"]["payload_drift_separate"] is True
    assert "wrong CLI" in action["current_fault_summary"] or action["run"] == "agentic-workspace"


def test_start_reports_blocking_cli_compatibility_drift_without_health_remediation(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "blocking"\nexact_version = "999.0.0"\n',
    )

    assert cli.main(["start", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    compatibility = _assert_cli_compatibility(payload, status="blocking-drift")
    _assert_cli_compatibility_schema(payload, schema_name="startup_context.schema.json")
    assert compatibility["enforcement"] == "blocking"
    assert compatibility["failed_checks"] == ["exact_version"]
    assert "next_action" not in compatibility


def test_implement_command_returns_bounded_context_and_boundary_warnings(capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--changed",
                "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
                "src/agentic_workspace/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context/v1"
    assert payload["inspect_files"] == [
        "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
        "src/agentic_workspace/cli.py",
    ]
    assert payload["required_validation_commands"] == [
        "cd packages/planning && uv run pytest tests/test_installer.py",
        "cd packages/planning && uv run ruff check .",
        "uv run pytest tests -q",
        "uv run ruff check src tests",
        "agentic-workspace defaults --section root_cli_authority --format json",
        "uv run pytest tests/test_workspace_cli.py -q",
    ]
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "hand-owned-executable"
    assert payload["orientation"]["status"] == "changed-path-context"
    assert "preflight" in payload["orientation"]["preflight_command"]
    assert "lowers continuation and review trust" in payload["orientation"]["trust_note"]
    assert "unstated intent" in payload["inference_limits"]["rule"]
    assert payload["execution_posture"]["kind"] == "agentic-workspace/execution-posture/v1"
    assert payload["execution_posture"]["delegation_control"]["effective_mode"] == "suggest"
    assert payload["execution_posture"]["delegation_control"]["execution_permitted"] is False
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"] == payload["execution_posture"]["delegation_decision"]
    assert payload["delegation_decision"]["mode"] == "suggest"
    assert "quality" in payload["execution_posture"]["quality_tradeoff"]
    assert "Token saving" in payload["execution_posture"]["token_tradeoff"]
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert payload["durable_intent"]["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert (
        "whether proof commands were actually executed unless evidence is recorded elsewhere" in payload["inference_limits"]["cannot_infer"]
    )
    assert payload["path_boundaries"][0]["authority"] == "payload"
    assert payload["path_boundaries"][0]["requires_attention"] is True
    assert payload["authority_markers"][0]["safe_to_edit"] is False
    assert payload["next_allowed_action"] == "Resolve boundary warnings before editing."


def test_implement_tiny_profile_returns_next_decision_without_diagnostics(capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--profile",
                "tiny",
                "--changed",
                "src/agentic_workspace/cli.py",
                "--task",
                "apply output profile policy",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert payload["next"]["action"] == "Inspect only the listed files and run the required validation commands."
    assert payload["scope"]["inspect_files"] == ["src/agentic_workspace/cli.py"]
    assert "uv run pytest tests -q" in payload["proof"]["required_commands"]
    assert payload["routing"]["work_shape"] == "bounded"
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"]["mode"] == "suggest"
    assert "package_boundary" not in payload
    assert "authority_markers" not in payload
    assert "durable_intent" not in payload
    assert "inference_limits" not in payload
    assert len(encoded) < 4000


def test_implement_task_routes_broad_issue_ingestion_to_planning(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--task",
                "ingest and implement all open GitHub issues",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["task_routing"]["status"] == "needs-planning"
    assert payload["task_routing"]["broad_external_work"] is True
    assert (
        payload["next_allowed_action"] == "Promote/create an active planning record, or narrow to one explicit issue before implementation."
    )
    assert payload["handoff_requirements"]["stop_when"][0] == ("task routing status is needs-planning for broad external-work ingestion")


def test_implement_task_allows_narrow_single_issue_context(capsys) -> None:
    assert cli.main(["implement", "--task", "implement issue #424", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["task_routing"]["status"] == "narrow-external-work"
    assert payload["task_routing"]["issue_refs"] == ["#424"]
    assert payload["task_routing"]["broad_external_work"] is False
    assert payload["next_allowed_action"] == "Inspect only the listed files and run the required validation commands."


def test_implement_command_surfaces_reasoning_heavy_execution_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
                "",
                "[delegation]",
                'mode = "manual"',
                "",
                "[delegation_targets.planner]",
                'strength = "strong"',
                'location = "local"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["internal"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
                "--task",
                "update delegation config schema",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    posture = payload["execution_posture"]
    assert posture["capability_posture"]["posture"]["execution class"] == "boundary-shaping"
    assert posture["capability_posture"]["work_shape"] == "bounded"
    assert posture["capability_posture"]["proof_burden"] == "high"
    assert "schema" in posture["capability_posture"]["risk_flags"]
    assert "proof route" in posture["capability_posture"]["inspection_evidence_required"]
    assert posture["capability_posture"]["self_assessment_authority"] == "advisory-only"
    assert posture["runtime_resolution"]["recommendation"] == "stronger-reasoning"
    assert posture["runtime_resolution"]["self_assessment"]["authority"] == "advisory-only"
    assert posture["delegation_control"]["effective_mode"] == "manual"
    assert posture["delegation_control"]["execution_permitted"] is False
    assert posture["selected_target"]["name"] == "planner"
    assert posture["capability_handoff_packets"]["packet_types"]["manual_human_clarification"]
    assert posture["ready_handoff"]["kind"] == "agentic-workspace/capability-handoff-packet/v1"
    assert posture["ready_handoff"]["mode"] == "manual"
    assert posture["ready_handoff"]["packet_type"] == "manual_human_clarification"
    assert "quality" in posture["ready_handoff"]["prompt"]
    assert posture["delegation_decision"]["decision"] == "suggest-escalation"
    assert posture["delegation_decision"]["required_next_action"] == "prepare-handoff"
    assert posture["delegation_decision"]["handoff_command"] == "agentic-planning handoff --target . --format json"
    assert payload["delegation_decision"] == posture["delegation_decision"]


def test_ownership_path_answer_includes_authority_marker_and_boundary_warning(capsys) -> None:
    assert cli.main(["ownership", "--path", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["authority_marker"] == {
        "path": "llms.txt",
        "authority": "generated-adapter",
        "canonical_source": "src/agentic_workspace/cli.py:_external_agent_handoff_text",
        "safe_to_edit": False,
        "refresh_command": "make maintainer-surfaces",
    }
    assert answer["boundary_warning"]["requires_attention"] is True


def test_authority_marker_policy_representative_paths_match_runtime() -> None:
    policy = authority_markers_manifest()

    for marker in policy["markers"]:
        for path in marker["representative_paths"]:
            actual = cli._authority_marker_for_path(path)  # type: ignore[attr-defined]
            assert actual["authority"] == marker["authority"]
            assert actual["safe_to_edit"] == marker["safe_to_edit"]
            assert actual["refresh_command"] == marker["refresh_command"]


def test_proof_changed_selector_returns_path_based_validation_lane(capsys) -> None:
    assert cli.main(["proof", "--changed", ".agentic-workspace/planning/state.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"changed": [".agentic-workspace/planning/state.toml"]}
    answer = payload["answer"]
    assert answer["kind"] == "proof-selection/v1"
    assert answer["selected_lanes"][0]["id"] == "planning_surfaces"
    assert answer["required_commands"] == ["agentic-workspace doctor --target ./repo --modules planning --format json"]
    assert answer["validation_plan"]["kind"] == "validation-plan/v1"
    assert answer["validation_plan"]["status"] == "inspect-before-run"
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["order"] == 1
    assert first_step["command"] == "agentic-workspace doctor --target ./repo --modules planning --format json"
    assert first_step["cwd"] == "."
    assert first_step["run"].endswith("agentic-workspace doctor --target ./repo --modules planning --format json")
    assert first_step["required"] is True
    assert first_step["lane_id"] == "planning_surfaces"
    assert first_step["action"] == "run-validation-command"
    assert first_step["risk"] == "read-only validation"
    assert first_step["required_inputs"] == ["changed_paths", "selected_lanes"]
    assert first_step["next_proof"] == "continue to the next required step, then rerun proof selection if changed paths expand"
    assert answer["validation_plan"]["primary_next_action"] == first_step
    assert answer["validation_plan"]["next_proof"] == "proof is complete when all required steps pass for the current changed paths"
    assert answer["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert any(item.startswith("Relevant durable intent may add proof") for item in answer["escalate_when"])


def test_proof_tiny_profile_returns_next_validation_action(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--profile",
                "tiny",
                "--changed",
                "src/agentic_workspace/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["kind"] == "proof-next-decision/v1"
    assert payload["selector"] == {"changed": ["src/agentic_workspace/cli.py"]}
    assert payload["next"]["action"] == "run-validation-command"
    assert payload["next"]["command"] == "uv run pytest tests -q"
    assert "uv run ruff check src tests" in payload["required_commands"]
    assert payload["warnings"] == []
    assert "answer" not in payload
    assert "selected_lanes" not in encoded
    assert "validation_plan" not in encoded
    assert len(encoded) < 2500


def test_proof_changed_validation_plan_uses_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", ".agentic-workspace/planning/state.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    step = payload["answer"]["validation_plan"]["required"][0]
    assert step["command"] == "agentic-workspace doctor --target ./repo --modules planning --format json"
    assert step["run"] == "uv run agentic-workspace doctor --target ./repo --modules planning --format json"


def test_proof_changed_includes_active_assurance_concern_profiles(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
strict_closeout = true

[assurance.proof_profiles.access_control]
required_commands = ["uv run pytest tests/test_access_control.py"]
optional_commands = ["uv run pytest tests/test_auth_integration.py"]
review_aids = [".agentic-workspace/agent-aids/access-control.md"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove concern-based proof." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "plan-alpha.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Plan Alpha",
        item_id="plan-alpha",
        status="in-progress",
        why_now="prove concern-based proof.",
        next_action="run proof selection.",
        done_when="concern proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "reason": "touches access control",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["security_refs"],
        "proof_profiles": ["access_control"],
        "required_gates": ["security-review"],
    }
    record["traceability_refs"] = {"security_refs": ["SEC-1"]}
    record["control_gates"] = [
        {
            "id": "security-review",
            "owner_role": "security",
            "required_for": ["access-control"],
            "status": "pending",
            "evidence": [],
            "blocking": True,
            "next_action": "obtain security review",
        }
    ]
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_access_control.py" in answer["required_commands"]
    assert "uv run pytest tests/test_auth_integration.py" in answer["optional_commands"]
    assert answer["planning_assurance"]["adaptive_assurance"]["level"] == "high"
    assert answer["planning_assurance"]["missing_required_refs"] == []
    assert answer["planning_assurance"]["closeout_status"] == "blocked"
    assert answer["planning_assurance"]["trust_state"]["assurance_level"] == "high"
    assert answer["planning_assurance"]["trust_state"]["assurance_level_source"] == "explicit-slice-field"
    assert answer["planning_assurance"]["trust_state"]["gate_states"][0]["enforcement"] == "blocking"
    assert answer["planning_assurance"]["trust_state"]["ref_states"][0]["trust"] == "satisfied"
    assert answer["planning_assurance"]["trust_state"]["proof_profile_states"][0]["state"] == "selected"
    assert answer["planning_assurance"]["trust_state"]["proof_execution_evidence"]["counts"]["missing"] >= 1
    assert answer["planning_assurance"]["pending_blocking_gates"][0]["id"] == "security-review"
    concern_step = [step for step in answer["validation_plan"]["required"] if step.get("lane_id") == "concern:access_control"][0]
    assert concern_step["command"] == "uv run pytest tests/test_access_control.py"
    assert answer["selected_lanes"][-1]["id"] == "concern:access_control"
    assert answer["selected_lanes"][-1]["review_aids"] == [".agentic-workspace/agent-aids/access-control.md"]


def test_proof_changed_reports_compact_proof_execution_evidence_states(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
strict_closeout = true

[assurance.proof_profiles.assurance_matrix]
required_commands = [
  "pass-command",
  "fail-command",
  "skip-command",
  "unavailable-command",
  "waived-command",
]
optional_commands = []
review_aids = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "proof-evidence", status = "in-progress", surface = ".agentic-workspace/planning/execplans/proof-evidence.plan.json", why_now = "prove evidence states." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "proof-evidence.plan.json"
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Proof Evidence",
        item_id="proof-evidence",
        status="in-progress",
        why_now="prove evidence states.",
        next_action="run proof selection.",
        done_when="proof evidence states appear.",
    )
    record["adaptive_assurance"] = {
        "level": "critical",
        "strict_closeout": True,
        "proof_profiles": ["assurance_matrix"],
    }
    record["proof_report"] = {
        "validation proof": "synthetic assurance commands",
        "proof achieved now": "mixed",
        "proof execution evidence": json.dumps(
            [
                {"command": "pass-command", "status": "passed", "evidence_ref": "local:pass"},
                {"command": "fail-command", "status": "failed", "evidence_ref": "local:fail"},
                {"command": "skip-command", "status": "skipped", "reason": "not applicable"},
                {"command": "unavailable-command", "status": "unavailable", "reason": "tool missing"},
                {"command": "waived-command", "status": "waived", "reason": "covered by manual review"},
            ]
        ),
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )

    evidence = json.loads(capsys.readouterr().out)["answer"]["planning_assurance"]["trust_state"]["proof_execution_evidence"]
    assert evidence["counts"] == {
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "unavailable": 1,
        "waived": 1,
        "missing": 1,
    }
    assert evidence["lower_trust_required_count"] == 4
    waived = next(item for item in evidence["commands"] if item["command"] == "waived-command")
    assert waived["trust"] == "satisfied"
    assert waived["waiver_state"] == "waived-with-reason"


def test_adaptive_assurance_end_to_end_closeout_flow(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance]
default_level = "medium"
strict_closeout = true

[assurance.proof_profiles.access_control]
required_commands = ["uv run pytest tests/test_access_control.py"]
optional_commands = ["uv run pytest tests/test_auth_integration.py"]
review_aids = [".agentic-workspace/agent-aids/access-control.md"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "high-assurance", status = "in-progress", surface = ".agentic-workspace/planning/execplans/high-assurance.plan.json", why_now = "dogfood assurance closeout.", next_action = "run proof selection.", done_when = "closeout gates are proved." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    def completed_record(item_id: str, title: str, status: str = "completed") -> dict[str, object]:
        record = planning_installer._build_execplan_record_from_todo_item(
            title=title,
            item_id=item_id,
            status=status,
            why_now="dogfood assurance flow.",
            next_action="archive the plan.",
            done_when="archive gate is satisfied.",
        )
        record["delegated_judgment"] = {
            "requested outcome": "prove the assurance workflow",
            "hard constraints": "keep this synthetic and generic",
            "agent may decide locally": "fixture details",
            "escalate when": "closeout gates are unclear",
        }
        record["execution_summary"] = {
            "outcome delivered": "Synthetic assurance flow proved.",
            "validation confirmed": "uv run pytest tests/test_workspace_cli.py",
            "follow-on routed to": "none; issue closeout can proceed",
            "post-work posterity capture": "the test preserves the workflow contract",
            "resume from": "no further action",
        }
        record["proof_report"] = {
            "validation proof": "uv run pytest tests/test_workspace_cli.py",
            "proof achieved now": "proof and archive gates passed",
            'evidence for "proof achieved" state': "synthetic fixture exercised the flow",
        }
        record["intent_satisfaction"] = {
            "original intent": "prove adaptive assurance end to end",
            "was original intent fully satisfied?": "yes",
            "evidence of intent satisfaction": "summary, proof, and archive gate were exercised",
            "unsolved intent passed to": "none",
        }
        record["closure_check"] = {
            "slice status": "bounded slice complete",
            "larger-intent status": "closed",
            "closure decision": "archive-and-close",
            "why this decision is honest": "all synthetic acceptance signals passed",
            "evidence carried forward": "this regression test",
            "reopen trigger": "assurance output stops blocking missing gates",
        }
        return record

    high_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "high-assurance.plan.json"
    high = completed_record("high-assurance", "High Assurance", status="in-progress")
    high["adaptive_assurance"] = {
        "level": "high",
        "reason": "synthetic access-control slice",
        "agent_may_escalate": True,
        "agent_may_deescalate": False,
        "strict_closeout": True,
        "required_refs": ["security_refs"],
        "proof_profiles": ["access_control"],
        "required_gates": ["security-review"],
    }
    high["traceability_refs"] = {"security_refs": []}
    high["control_gates"] = [{"id": "security-review", "status": "pending", "blocking": True, "evidence": []}]
    high["implementation_blockers"] = [{"id": "policy", "status": "blocked", "do_not_implement": True}]
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    low_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "low-assurance.plan.json"
    low = completed_record("low-assurance", "Low Assurance")
    planning_installer._write_execplan_record(record_path=low_path, record=low)

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")
    assert summary["planning_record"]["adaptive_assurance"]["level"] == "high"

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "--format",
                "json",
            ]
        )
        == 0
    )
    proof_answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_access_control.py" in proof_answer["required_commands"]
    assert proof_answer["planning_assurance"]["closeout_status"] == "blocked"
    assert proof_answer["planning_assurance"]["missing_required_refs"] == ["security_refs"]
    assert proof_answer["planning_assurance"]["pending_blocking_gates"][0]["id"] == "security-review"

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "high-assurance", status = "completed", surface = ".agentic-workspace/planning/execplans/high-assurance.plan.json", why_now = "dogfood assurance closeout.", next_action = "archive after gate.", done_when = "closeout gates are proved." },
  { id = "low-assurance", status = "completed", surface = ".agentic-workspace/planning/execplans/low-assurance.plan.json", why_now = "prove low ceremony.", next_action = "archive directly.", done_when = "low ceremony remains cheap." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    high["active_milestone"]["status"] = "completed"
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    blocked = planning_installer.archive_execplan("high-assurance", target=tmp_path, dry_run=True)
    assert any(warning["warning_class"] == "archive_adaptive_assurance_blocked" for warning in blocked.warnings)

    high["traceability_refs"] = {"security_refs": ["SEC-1"]}
    high["control_gates"] = [{"id": "security-review", "status": "waived", "blocking": True, "evidence": ["waiver:SEC-1"]}]
    high["implementation_blockers"] = [{"id": "policy", "status": "waived", "do_not_implement": True}]
    planning_installer._write_execplan_record(record_path=high_path, record=high)

    satisfied = planning_installer.archive_execplan("high-assurance", target=tmp_path, dry_run=True)
    assert not [warning for warning in satisfied.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked"]
    assert any(action.kind == "would remove" for action in satisfied.actions)

    low_result = planning_installer.archive_execplan("low-assurance", target=tmp_path, dry_run=True)
    assert not [warning for warning in low_result.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked"]
    assert any(action.kind == "would remove" for action in low_result.actions)


def test_summary_uses_immediate_next_action_and_warns_on_duplicate_drift(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = [
  { id = "drifted", title = "Drifted", maturity = "active", status = "active", path = ".agentic-workspace/planning/execplans/drifted.plan.json", durable_residue = "pending", residue_owner = "this-execplan", residue_promotion_trigger = "closeout" },
]

[active]
execplans = [
  ".agentic-workspace/planning/execplans/drifted.plan.json",
]

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Drifted",
        item_id="drifted",
        status="active",
        why_now="prove next action drift.",
        next_action="legacy markdown-like next action.",
        done_when="summary uses the machine next step.",
    )
    record["machine_readable_contract"] = {
        "execution": {
            "next_step": "canonical machine next action.",
        }
    }
    planning_installer._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace" / "planning" / "execplans" / "drifted.plan.json",
        record=record,
    )

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")

    assert summary["planning_record"]["next_action"] == "legacy markdown-like next action."
    assert summary["resumable_contract"]["current_next_action_source"] == "immediate_next_action[0]"
    assert any(
        warning["warning_class"] == "execplan_next_action_projection_drift" for warning in summary["planning_surface_health"]["warnings"]
    )


def test_archive_plan_reports_exact_required_traceability_ref_paths(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    record = planning_installer._build_execplan_record_from_todo_item(
        title="Missing Traceability",
        item_id="missing-traceability",
        status="completed",
        why_now="prove closeout field paths.",
        next_action="archive after proof.",
        done_when="archive warning is actionable.",
    )
    record.update(
        {
            "delegated_judgment": {
                "requested outcome": "prove strict closeout paths",
                "hard constraints": "synthetic only",
                "agent may decide locally": "fixture shape",
                "escalate when": "paths are ambiguous",
            },
            "execution_summary": {
                "outcome delivered": "Synthetic strict closeout path proved.",
                "validation confirmed": "pytest",
                "follow-on routed to": "none",
                "post-work posterity capture": "test",
                "resume from": "none",
            },
            "proof_report": {
                "validation proof": "pytest",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "test",
            },
            "intent_satisfaction": {
                "original intent": "prove strict closeout paths",
                "was original intent fully satisfied?": "yes",
                "evidence of intent satisfaction": "test",
                "unsolved intent passed to": "none",
            },
            "closure_check": {
                "slice status": "complete",
                "larger-intent status": "closed",
                "closure decision": "archive-and-close",
                "why this decision is honest": "synthetic proof exists",
                "evidence carried forward": "test",
                "reopen trigger": "warning loses field paths",
            },
            "adaptive_assurance": {
                "strict_closeout": True,
                "required_refs": ["security_refs"],
            },
            "traceability_refs": {
                "requirement_refs": ["#1"],
            },
            "durable_residue": {
                "status": "none",
                "learned constraint": "No reusable product constraint in this synthetic fixture.",
                "motivation worth preserving": "Only the archive-size guardrail behavior matters.",
                "canonical owner now": "none",
                "promotion trigger": "none",
                "retention after promotion": "retain",
            },
        }
    )
    planning_installer._write_execplan_record(
        record_path=tmp_path / ".agentic-workspace" / "planning" / "execplans" / "missing-traceability.plan.json",
        record=record,
    )

    result = planning_installer.archive_execplan("missing-traceability", target=tmp_path, dry_run=True)

    warning = next(warning for warning in result.warnings if warning["warning_class"] == "archive_adaptive_assurance_blocked")
    assert "traceability_refs.security_refs" in warning["message"]
    assert "adaptive_assurance.required_refs names traceability_refs field names" in warning["message"]


def test_archive_plan_blocks_oversized_archive_before_write(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / "src" / "agentic_workspace" / "contracts" / "structured_file_inventory.json",
        """
{
  "entries": [
    {
      "pattern": ".agentic-workspace/planning/execplans/archive/*.plan.json",
      "guardrails": {
        "max_bytes": 300
      }
    }
  ]
}
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Too Large",
        item_id="too-large",
        status="completed",
        why_now="prove archive guardrail.",
        next_action="archive after distillation.",
        done_when="archive refuses oversized records.",
    )
    record.update(
        {
            "goal": ["x" * 600],
            "delegated_judgment": {
                "requested outcome": "prove archive size guardrail",
                "hard constraints": "synthetic only",
                "agent may decide locally": "fixture shape",
                "escalate when": "archive writes too early",
            },
            "execution_summary": {
                "outcome delivered": "Synthetic archive size guardrail proved.",
                "validation confirmed": "pytest",
                "follow-on routed to": "none",
                "post-work posterity capture": "test",
                "resume from": "none",
            },
            "proof_report": {
                "validation proof": "pytest",
                "proof achieved now": "yes",
                'evidence for "proof achieved" state': "test",
            },
            "intent_satisfaction": {
                "original intent": "prove archive size guardrail",
                "was original intent fully satisfied?": "yes",
                "evidence of intent satisfaction": "test",
                "unsolved intent passed to": "none",
            },
            "closure_check": {
                "slice status": "complete",
                "larger-intent status": "closed",
                "closure decision": "archive-and-close",
                "why this decision is honest": "synthetic proof exists",
                "evidence carried forward": "test",
                "reopen trigger": "archive writes oversized record",
            },
            "durable_residue": {
                "status": "none",
                "learned constraint": "No reusable product constraint in this synthetic fixture.",
                "motivation worth preserving": "Only the archive-size guardrail behavior matters.",
                "canonical owner now": "none",
                "promotion trigger": "none",
                "retention after promotion": "retain",
            },
        }
    )
    record_path = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "too-large.plan.json"
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    result = planning_installer.archive_execplan("too-large", target=tmp_path, dry_run=True, retain_archive=True)

    assert record_path.exists()
    assert not (tmp_path / ".agentic-workspace" / "planning" / "execplans" / "archive" / "too-large.plan.json").exists()
    warning = next(warning for warning in result.warnings if warning["warning_class"] == "archive_size_guardrail_blocked")
    assert "max_bytes=300" in warning["message"]
    assert any(action.kind == "manual review" for action in result.actions)


def test_summary_surfaces_broad_work_planning_guard_for_narrow_direct_state(tmp_path: Path) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

work_items = []

[active]
execplans = []

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )

    summary = planning_installer.planning_summary(target=tmp_path, profile="compact")

    guard = summary["execution_readiness"]["broad_work_planning_guard"]
    assert guard["status"] == "available-if-work-widens"
    assert "high-assurance" in guard["applies_to"]
    assert "repo-visible durable state" in guard["durable_state_rule"]
    assert ".agentic-workspace/planning/execplans/<id>.plan.json" in guard["canonical_durable_state_surfaces"]
    assert "new-plan" in guard["new_plan_command"]
    assert "do not create product" in guard["planning_only_rule"]
    assert "do not stop at a proposal" in guard["prep_only_route"]["required_action"]
    assert any("planning/records" in item for item in guard["prep_only_route"]["do_not_do"])
    assert any("HANDOFF" in item and "package" in item for item in guard["prep_only_route"]["do_not_do"])
    assert summary["execution_readiness"]["direct_work_allowed"] is True


def test_proof_changed_selector_routes_generated_command_packages(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "generated/typescript/workspace-cli/src/commandPackage.ts",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["selected_lanes"][0]["id"] == "generated_command_packages"
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["generated_command_packages", "cli_authority"]
    assert "route back through command-package checks" in answer["selected_lanes"][0]["recovery_signal"]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker",
        "uv run python scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
        "agentic-workspace defaults --section root_cli_authority --format json",
    ]
    assert [step["lane_id"] for step in answer["validation_plan"]["required"]] == [
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "cli_authority",
    ]
    assert answer["validation_plan"]["required_count"] == len(answer["required_commands"])
    assert answer["validation_plan"]["optional"][0]["required"] is False
    review = answer["cli_authority_review"]
    assert review["status"] == "blocked-direct-edit-route-to-source"
    assert review["blocked_direct_edit_paths"] == ["generated/typescript/workspace-cli/src/commandPackage.ts"]
    generated = review["classifications"][0]
    assert generated["role"] == "projection"
    assert generated["direct_edit_allowed"] is False
    assert generated["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert generated["regeneration_path"] == "uv run python scripts/check/check_generated_command_packages.py"


def test_proof_changed_selector_routes_contract_only_changes_to_focused_lane(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/contracts/structured_file_inventory.json",
                "scripts/check/check_structured_file_inventory.py",
                "tests/test_structured_file_inventory.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["contract_tooling"]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success",
        "uv run python scripts/check/check_structured_file_inventory.py --quiet-success",
        "uv run ruff check src/agentic_workspace/contracts scripts/check tests/test_structured_file_inventory.py",
    ]
    assert "uv run pytest tests -q" not in answer["required_commands"]


def test_proof_changed_selector_routes_agent_aid_changes_to_manifest_lane(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json",
                ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["agent_aid_manifests"]
    assert answer["required_commands"] == ["uv run python scripts/check/check_agent_aids.py --quiet-success"]
    assert "candidate aids" in answer["selected_lanes"][0]["recovery_signal"]
    assert "uv run pytest tests -q" not in answer["required_commands"]


def test_proof_changed_selector_flags_direct_cli_edits(capsys) -> None:
    assert cli.main(["proof", "--changed", "src/agentic_workspace/cli.py", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "workspace_cli",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
    ]
    authority_review = answer["cli_authority_review"]
    assert authority_review["status"] == "review-ready"
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    root_cli = authority_review["classifications"][0]
    assert root_cli["role"] == "hand-owned-executable"
    assert root_cli["direct_edit_allowed"] is True
    assert root_cli["source_contract"].endswith("src/agentic_workspace/contracts/python_runtime_boundary.json")
    assert authority_review["authority_query"] == "agentic-workspace defaults --section root_cli_authority --format json"
    review = payload["answer"]["direct_cli_edit_review"]
    assert review["status"] == "review-needed"
    assert review["changed_paths"] == ["src/agentic_workspace/cli.py"]
    assert "normal interface authoring belongs in command contracts" in review["rule"]
    assert "runtime primitive implementation and live workspace inspection" in review["allowed_direct_cli_work"]
    assert "route interface or generated-surface changes back" in review["recovery_signal"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["id"] == "workspace-cli-runtime"


def test_proof_changed_selector_broadens_contract_plus_cli_changes(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "src/agentic_workspace/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "contract_tooling",
        "workspace_cli",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "uv run pytest tests -q" in answer["required_commands"]


def test_proof_changed_selector_escalates_for_cross_lane_changes(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "src/agentic_workspace/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "planning_package",
        "workspace_cli",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    package_step = answer["validation_plan"]["required"][0]
    assert package_step["command"] == "cd packages/planning && uv run pytest tests/test_installer.py"
    assert package_step["cwd"] == "packages/planning"
    assert package_step["run"] == "uv run pytest tests/test_installer.py"
    assert package_step["lane_id"] == "planning_package"


def test_proof_changed_selector_accepts_existing_durable_surface_update(tmp_path: Path, capsys) -> None:
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "report_contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/report_contract.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["kind"] == "surface-value-review/v1"
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["surface_class"] == "workspace_contract_surface"
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert (
        review["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json"
    )


def test_proof_changed_selector_flags_additive_only_durable_surface(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/new-first-line-concept.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "attention-needed"
    assert review["accepted_count"] == 0
    assert review["flagged_count"] == 1
    assert review["reviewed_paths"][0]["result"] == "flagged"
    assert review["reviewed_paths"][0]["disposition"] == "additive-only durable surface candidate"
    assert "what repeated cost does this remove?" in review["reviewed_paths"][0]["required_answers"]


def test_proof_changed_selector_accepts_deleted_durable_surface(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@example.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Agent"], cwd=tmp_path, check=True)
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "old_surface.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    contract_path.unlink()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/old_surface.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["answer"]["surface_value_review"]
    assert review["status"] == "accepted"
    assert review["accepted_count"] == 1
    assert review["flagged_count"] == 0
    assert review["reviewed_paths"][0]["result"] == "accepted"
    assert review["reviewed_paths"][0]["disposition"] == "removed durable surface"


def test_upgrade_strict_preflight_requires_token(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "upgrade",
                "--target",
                str(tmp_path),
                "--strict-preflight",
                "--dry-run",
            ]
        )

    assert excinfo.value.code == 2
    assert "Strict preflight gate is enabled" in capsys.readouterr().err


def test_upgrade_strict_preflight_rejects_stale_token(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        cli.main(
            [
                "upgrade",
                "--target",
                str(tmp_path),
                "--strict-preflight",
                "--preflight-token",
                "preflight-v1:1",
                "--preflight-max-age-seconds",
                "60",
                "--dry-run",
            ]
        )

    assert excinfo.value.code == 2
    assert "Stale preflight token" in capsys.readouterr().err


def test_invalid_command_shows_preflight_fallback_hint(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["prefliht"])

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert "Did you mean: preflight?" in stderr
    assert 'agentic-workspace start --profile tiny --task "<task>" --format json' in stderr
    assert "agentic-workspace preflight --format json" in stderr


def test_planning_help_command_returns_lifecycle_guidance(capsys) -> None:
    assert cli.main(["planning", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/planning-help/v1"
    assert any("new-plan" in command for command in payload["lifecycle_commands"])
    assert "schema-valid scaffold" in payload["post_new_plan_tightening"]["rule"]
    assert "execution_bounds" in payload["post_new_plan_tightening"]["tighten_before_implementation"]
    assert "one lane at a time" in payload["sequential_lane_execution"]["rule"]
    assert "unrelated lanes" in payload["sequential_lane_execution"]["do_not"]
    assert "new-plan" in payload["durable_state_bridge"]["preferred_command"]
    assert "--prep-only" in payload["durable_state_bridge"]["prep_only_route"]["preferred_command"]
    assert "PLAN.md" in payload["durable_state_bridge"]["must_not_create"]
    assert "do not create product source" in payload["durable_state_bridge"]["planning_only_rule"]
    prep_route = payload["durable_state_bridge"]["prep_only_route"]
    assert "Create or continue canonical checked-in Planning state" in prep_route["required_action"]
    assert "then stop" in prep_route["required_action"]
    assert any("planning/records" in item for item in prep_route["do_not_do"])
    assert any("HANDOFF" in item and "package" in item for item in prep_route["do_not_do"])
    assert "reference_validity_rule" in payload["durable_state_bridge"]
    assert "proposed/future" in payload["durable_state_bridge"]["reference_validity_rule"]
    assert any("Do not invent" in rule for rule in payload["rules"])
    assert any("tighten scaffold" in rule for rule in payload["rules"])
    assert any("one lane at a time" in rule for rule in payload["rules"])
    assert any("WORKFLOW.md as task state" in rule for rule in payload["rules"])
    assert any("architecture assumptions" in rule for rule in payload["rules"])
    assert any("verify it, and stop" in rule for rule in payload["rules"])
    assert payload["runtime_native_bridge"]["status"] == "allowed-as-local-aid"
    assert "not repo-shared execution authority" in payload["runtime_native_bridge"]["rule"]
    assert "do not invent reset flags" in payload["unsafe_state_recovery"]["manual_fallback"]


def test_planning_help_text_is_actionable(capsys) -> None:
    assert cli.main(["planning"]) == 0
    output = capsys.readouterr().out

    assert "Planning lifecycle" in output
    assert "Durable repo-visible state bridge" in output
    assert "Prep-only" in output
    assert "Reference validity" in output
    assert "agentic-planning new-plan" in output
    assert "After new-plan" in output
    assert "Ordered lanes" in output
    assert "planning-execplan/v1" in output
    assert "Runtime-native planning bridge" in output
    assert "Unsafe-state recovery" in output


def test_upgrade_json_collects_summary_categories(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "upgrade"
    assert payload["updated_managed"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert payload["preserved_existing"] == ["AGENTS.md"]
    assert payload["generated_artifacts"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert payload["needs_review"] == ["README.md: inspect manually"]
    assert payload["warnings"] == []
    assert payload["stale_generated_surfaces"] == [".agentic-workspace/planning/agent-manifest.json"]
    safety = payload["lifecycle_plan"]["mutation_safety"]
    assert safety["classification"] == "lifecycle-mutation"
    assert safety["dry_run_apply_separation"]["status"] == "dry-run-only"
    assert safety["review_required_before_apply"] is True
    assert safety["strict_preflight"]["available"] is True
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["upgrade dry-run on installed repo"]["status"] == "covered"


def test_doctor_json_does_not_report_dry_run_actions_as_mutations(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["doctor", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == []
    assert payload["updated_managed"] == []
    assert payload["reports"][0]["actions"][0]["kind"] == "would update"


@pytest.mark.parametrize(
    ("args", "expected_modules"),
    [
        (["--modules", "memory"], ["memory"]),
        (["--modules", "planning"], ["planning"]),
        (["--preset", "full"], ["planning", "memory"]),
    ],
)
def test_upgrade_lifecycle_plan_advertises_root_front_door_for_module_selections(
    monkeypatch, tmp_path: Path, capsys, args: list[str], expected_modules: list[str]
) -> None:
    _init_git_repo(tmp_path)
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["upgrade", "--target", str(tmp_path), *args, "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    front_door = payload["lifecycle_plan"]["root_upgrade_front_door"]
    assert front_door["status"] == "authoritative-host-repo-path"
    assert front_door["selected_modules"] == expected_modules
    assert front_door["dry_run_first"] is True
    assert front_door["package_specific_upgrade_role"] == "fallback-debug-only"
    assert front_door["ordinary_sequence"][0]["step"] == "inspect"
    assert front_door["ordinary_sequence"][0]["safe"] is True
    assert "--dry-run" in front_door["ordinary_sequence"][0]["command"]
    assert "selected modules" in front_door["ordinary_sequence"][0]["reason"]
    assert front_door["ordinary_sequence"][1]["step"] == "apply"
    assert "--dry-run" not in front_door["ordinary_sequence"][1]["command"]
    assert front_door["ordinary_sequence"][2]["command"].startswith("agentic-workspace doctor --target ")
    assert [(module_name, command_name) for module_name, command_name, _kwargs in calls] == [
        (module_name, "upgrade") for module_name in expected_modules
    ]


def test_lifecycle_plan_uses_resolved_cli_invoke_for_next_actions(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["upgrade", "--target", str(tmp_path), "--modules", "planning", "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    lifecycle_plan = payload["lifecycle_plan"]
    assert lifecycle_plan["next_safe_command"]["command"].startswith("uv run agentic-workspace upgrade ")
    primary_action = lifecycle_plan["primary_next_action"]
    assert primary_action["action"] == "apply-lifecycle-plan"
    assert primary_action["command"].startswith("uv run agentic-workspace upgrade ")
    assert primary_action["run"] == primary_action["command"]
    assert primary_action["risk"] == "may mutate repo-managed workspace surfaces"
    assert primary_action["required_inputs"] == ["target repo", "selected modules", "dry-run plan"]
    assert primary_action["next_proof"] == "run doctor after apply and inspect surface classifications"
    freshness = lifecycle_plan["module_update_freshness"][0]["freshness"]
    assert freshness["status"] in {"fresh", "unknown"}
    assert freshness["next_action"] is None or freshness["next_action"]["command"].startswith("uv run agentic-workspace upgrade ")
    front_door = lifecycle_plan["root_upgrade_front_door"]
    assert front_door["ordinary_sequence"][0]["command"].startswith("uv run agentic-workspace upgrade ")
    assert front_door["ordinary_sequence"][1]["command"].startswith("uv run agentic-workspace upgrade ")
    assert front_door["ordinary_sequence"][2]["command"].startswith("uv run agentic-workspace doctor ")
    assert payload["next_steps"][0].startswith("Run uv run agentic-workspace doctor ")


@pytest.mark.parametrize("dry_run_arg", [["--dry-run"], []])
def test_upgrade_lifecycle_surface_classifications_cover_reason_classes(
    monkeypatch, tmp_path: Path, capsys, dry_run_arg: list[str]
) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))
    _write(tmp_path / ".agentic-workspace" / "local" / "memory.toml", 'kind = "local-memory"\n')
    _write(
        tmp_path / "ROADMAP.md",
        "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->\n# ROADMAP\n",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), *dry_run_arg, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    classifications = payload["lifecycle_plan"]["surface_classifications"]
    entries = classifications["entries"]
    by_path = {entry["path"]: entry for entry in entries}
    reason_classes = {entry["reason_class"] for entry in entries}
    assert classifications["kind"] == "workspace-lifecycle-surface-classifications/v1"
    assert by_path[".agentic-workspace/planning/agent-manifest.json"]["reason_class"] == "core refreshed"
    assert by_path["AGENTS.md"]["reason_class"] == "repo-owned preserved"
    assert by_path["README.md"]["reason_class"] == "ambiguous ownership manual-review"
    assert by_path[".agentic-workspace/local/memory.toml"]["reason_class"] == "local-only preserved"
    assert "legacy unsupported; migration/refusal required" in reason_classes
    assert classifications["summary_by_class"]["core refreshed"] >= 1


def test_uninstall_lifecycle_surface_classifications_include_refused_destructive_action(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    classifications = payload["lifecycle_plan"]["surface_classifications"]
    assert classifications["summary_by_class"]["refused destructive action"] >= 1
    assert any(
        entry["reason_class"] == "ambiguous ownership manual-review" and entry["review_required"] is True
        for entry in classifications["entries"]
    )


def test_upgrade_text_output_keeps_surface_classification_detail_in_json(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "Surface classifications:" in output
    assert "lifecycle_plan.surface_classifications.entries" in output
    assert "[planning] upgrade planning" not in output
    assert "README.md: inspect manually" in output


def test_uninstall_dry_run_requires_review_for_ambiguous_workspace_payload(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert (
        ".agentic-workspace/WORKFLOW.md: local workspace shared-layer file differs from managed payload; remove manually if intended"
        in payload["needs_review"]
    )
    lifecycle_plan = payload["lifecycle_plan"]
    assert lifecycle_plan["review_required"] is True
    assert lifecycle_plan["next_safe_command"]["status"] == "review-required"
    primary_action = lifecycle_plan["primary_next_action"]
    assert primary_action["action"] == "resolve-lifecycle-review"
    assert primary_action["command"].startswith("agentic-workspace uninstall ")
    assert "--dry-run" in primary_action["command"]
    assert primary_action["run"] == primary_action["command"]
    assert primary_action["risk"] == "blocked until review items are resolved"
    assert primary_action["required_inputs"] == ["target repo", "selected modules", "review items"]
    assert primary_action["next_proof"] == "rerun the lifecycle dry-run after resolving review items"
    safety = lifecycle_plan["mutation_safety"]
    assert safety["classification"] == "destructive-mutation"
    assert ".agentic-workspace/WORKFLOW.md" not in safety["destructive_risk"]["planned_removals"]
    assert safety["review_required_before_apply"] is True
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["ambiguous ownership uninstall refuses deletion"]["status"] == "covered"


def test_uninstall_apply_refuses_workspace_payload_removal_when_ambiguous(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    workflow_path = target / ".agentic-workspace" / "WORKFLOW.md"
    ownership_path = target / ".agentic-workspace" / "OWNERSHIP.toml"
    workflow_path.write_text(workflow_path.read_text(encoding="utf-8") + "\nLocal owner edit.\n", encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert workflow_path.exists()
    assert ownership_path.exists()
    assert (
        ".agentic-workspace/WORKFLOW.md: local workspace shared-layer file differs from managed payload; remove manually if intended"
        in payload["needs_review"]
    )
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    actions_by_path = {action["path"]: action for action in workspace_report["actions"]}
    assert actions_by_path[".agentic-workspace/OWNERSHIP.toml"]["kind"] == "skipped"
    assert "blocked by ambiguous workspace shared-layer ownership" in actions_by_path[".agentic-workspace/OWNERSHIP.toml"]["detail"]
    assert payload["lifecycle_plan"]["next_safe_command"]["status"] == "review-required"


def test_uninstall_dry_run_and_apply_agree_for_safe_managed_payloads(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    local_memory = target / ".agentic-workspace" / "local" / "memory.toml"
    local_memory.parent.mkdir(parents=True, exist_ok=True)
    local_memory.write_text('kind = "local-memory"\n', encoding="utf-8")
    agents_path = target / "AGENTS.md"
    agents_text = agents_path.read_text(encoding="utf-8")

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    dry_run_payload = json.loads(capsys.readouterr().out)
    dry_run_removals = set(dry_run_payload["lifecycle_plan"]["mutation_safety"]["destructive_risk"]["planned_removals"])

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    apply_payload = json.loads(capsys.readouterr().out)
    apply_removals = set(apply_payload["lifecycle_plan"]["mutation_safety"]["destructive_risk"]["planned_removals"])
    assert dry_run_removals == apply_removals
    assert ".agentic-workspace/WORKFLOW.md" in apply_removals
    assert ".agentic-workspace/OWNERSHIP.toml" in apply_removals
    assert agents_path.read_text(encoding="utf-8") == agents_text
    assert local_memory.read_text(encoding="utf-8") == 'kind = "local-memory"\n'
    assert not (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert not (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()


def test_uninstall_invokes_selected_module_uninstall(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [(module_name, command_name) for module_name, command_name, _kwargs in calls] == [("planning", "uninstall")]
    assert payload["modules"] == ["planning"]
    assert payload["reports"][0]["module"] == "planning"


def test_upgrade_apply_preserves_local_only_memory_and_integration_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    local_memory = target / ".agentic-workspace" / "local" / "memory.toml"
    local_integration = target / ".agentic-workspace" / "local" / "integrations" / "tool" / "state.txt"
    local_memory.parent.mkdir(parents=True, exist_ok=True)
    local_integration.parent.mkdir(parents=True)
    local_memory.write_text('kind = "local-memory"\n', encoding="utf-8")
    local_integration.write_text("private state\n", encoding="utf-8")

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert local_memory.read_text(encoding="utf-8") == 'kind = "local-memory"\n'
    assert local_integration.read_text(encoding="utf-8") == "private state\n"
    safety = payload["lifecycle_plan"]["mutation_safety"]
    assert safety["local_only_preservation"]["status"] == "preserve-by-default"
    scenarios = {entry["scenario"]: entry for entry in safety["fixture_coverage"]}
    assert scenarios["local-only memory/integration preservation"]["status"] == "covered"


@pytest.mark.parametrize(
    ("modules", "expected_modules"),
    [
        ("memory", ["memory"]),
        ("planning", ["planning"]),
        (None, ["planning", "memory"]),
    ],
)
def test_root_lifecycle_fixture_matrix_covers_upgrade_shapes(
    tmp_path: Path, capsys, modules: str | None, expected_modules: list[str]
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    init_args = ["init", "--target", str(target), "--format", "json"]
    if modules is not None:
        init_args.extend(["--modules", modules])

    assert cli.main(init_args) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    upgrade_payload = json.loads(capsys.readouterr().out)
    assert upgrade_payload["modules"] == expected_modules
    assert upgrade_payload["lifecycle_plan"]["root_upgrade_front_door"]["selected_modules"] == expected_modules

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["modules"] == expected_modules

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["modules"] == expected_modules


def test_root_lifecycle_fixture_matrix_classifies_entry_states(monkeypatch, tmp_path: Path, capsys) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    _init_git_repo(empty)
    assert cli.main(["init", "--target", str(empty), "--dry-run", "--format", "json"]) == 0
    empty_payload = json.loads(capsys.readouterr().out)
    assert empty_payload["repo_state"] == "blank_or_unmanaged_repo"
    assert empty_payload["mode"] == "install"

    routing_only = tmp_path / "routing-only"
    routing_only.mkdir()
    _init_git_repo(routing_only)
    _write(routing_only / "AGENTS.md", "# Local agent instructions\n")
    _write(routing_only / "llms.txt", "# Local external-agent adapter\n")
    assert cli.main(["init", "--target", str(routing_only), "--dry-run", "--format", "json"]) == 0
    routing_payload = json.loads(capsys.readouterr().out)
    assert routing_payload["repo_state"] == "docs_heavy_existing_repo"
    assert routing_payload["inferred_policy"] == "require_explicit_handoff"
    assert sorted(routing_payload["detected_surfaces"]) == ["AGENTS.md", "llms.txt"]

    partial = tmp_path / "partial"
    partial.mkdir()
    _init_git_repo(partial)
    _write(partial / "TODO.md", "# Existing TODO\n")
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(partial, calls))
    assert cli.main(["init", "--target", str(partial), "--dry-run", "--format", "json"]) == 0
    partial_payload = json.loads(capsys.readouterr().out)
    assert partial_payload["repo_state"] == "partial_or_placeholder_state"
    assert partial_payload["prompt_requirement"] == "required"
    assert "TODO.md: partial module state detected" in partial_payload["needs_review"]


def test_root_lifecycle_fixture_matrix_classifies_legacy_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md",
        "# Task Context\n\n<CURRENT_FOCUS>\n",
    )
    compat_notice = "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->"
    _write(target / "TODO.md", f"{compat_notice}\n# TODO\n")
    _write(target / "ROADMAP.md", f"{compat_notice}\n# ROADMAP\n")

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    flattened_actions = [
        action
        for report in payload["reports"]
        for action in report.get("actions", [])
        if isinstance(report, dict) and isinstance(action, dict)
    ]
    assert any(
        action.get("role") == "current-memory-migration" and action.get("path") == ".agentic-workspace/memory/repo/current/task-context.md"
        for action in flattened_actions
    )
    assert any(
        action.get("kind") in {"warning", "suggested fix"}
        and action.get("path") == "ROADMAP.md"
        and "ROADMAP" in str(action.get("detail", ""))
        for action in flattened_actions
    )


def test_lifecycle_safety_payload_advertises_root_fixture_matrix(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["upgrade", "--target", str(target), "--dry-run", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    matrix = payload["lifecycle_plan"]["mutation_safety"]["fixture_matrix"]
    states = {entry["state"]: entry for entry in matrix}
    assert set(states) == {
        "empty repo",
        "routing-only installed",
        "memory-only installed",
        "planning-only installed",
        "full installed",
        "old current-memory residue",
        "old optional planning surfaces",
        "custom AGENTS.md",
        "partial managed state",
        "local-only state",
        "ambiguous ownership state",
    }
    advertised_commands = {command for entry in matrix for command in entry["commands"]}
    assert advertised_commands >= {"init", "install", "adopt", "upgrade", "uninstall", "status", "doctor"}
    assert states["old optional planning surfaces"]["expected_result"] == (
        "classified as unsupported legacy surfaces with migration/refusal guidance"
    )


def test_upgrade_preserves_repo_owned_agents_content_outside_workspace_fence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    agents_path = target / "AGENTS.md"
    original = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(
        f"# Repo Instructions\n\nKeep this repo-specific guidance.\n\n{original}\nMore local instructions.\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    updated = agents_path.read_text(encoding="utf-8")
    assert payload["health"] == "healthy"
    assert "# Repo Instructions" in updated
    assert "Keep this repo-specific guidance." in updated
    assert "More local instructions." in updated
    assert "<!-- agentic-workspace:workflow:start -->" in updated
    assert 'start --profile tiny --task "<task>"' in updated


def test_upgrade_dry_run_syncs_module_update_source_metadata_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in payload["updated_managed"]
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(
        action["path"] == ".agentic-workspace/planning/UPGRADE-SOURCE.toml" and action["kind"] == "would update"
        for action in workspace_report["actions"]
    )


def test_status_warns_when_module_update_source_metadata_drifts_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / ".agentic-workspace/config.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["status", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/planning/UPGRADE-SOURCE.toml" in warning for warning in payload["warnings"])


def test_adapt_action_supports_slotted_dataclass(tmp_path: Path) -> None:
    action = SlottedAction(kind="copied", path=tmp_path / "demo.txt", detail="ok")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "copied", "path": "demo.txt", "detail": "ok"}


def test_adapt_action_prefers_to_dict_protocol(tmp_path: Path) -> None:
    action = DictAction(tmp_path / "nested" / "demo.txt")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "converted", "path": "nested/demo.txt", "detail": "used to_dict"}


def test_adapt_module_result_handles_optional_warnings(tmp_path: Path) -> None:
    result = FakeResult(
        target_root=tmp_path,
        message="status memory",
        dry_run=False,
        actions=[FakeAction(kind="recorded", path=tmp_path / "memory", detail="ran status")],
    )
    delattr(result, "warnings")

    report = adapt_module_result(module="memory", result=result)

    assert report.to_dict()["warnings"] == []


def test_invoke_module_command_uses_descriptor_command_args(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _doctor_handler(**kwargs):
        captured.update(kwargs)
        return FakeResult(
            target_root=tmp_path,
            message="doctor planning",
            dry_run=False,
            actions=[],
            warnings=[],
        )

    descriptor = cli.ModuleDescriptor(
        name="planning",
        description="planning module",
        commands={"doctor": _doctor_handler},
        detector=lambda detected_root: True,
        selection_rank=10,
        include_in_full_preset=True,
        install_signals=(Path("TODO.md"),),
        workflow_surfaces=(Path("TODO.md"),),
        generated_artifacts=(),
        command_args={"doctor": ("target",)},
        startup_steps=(),
        sources_of_truth=(),
        root_agents_cleanup_blocks=(),
        capabilities=(),
        dependencies=(),
        conflicts=(),
        result_contract=cli.ModuleResultContract(
            schema_version="workspace-module-report/v1",
            guaranteed_fields=("module",),
            action_fields=("kind",),
            warning_fields=("message",),
        ),
    )

    report = cli._invoke_module_command(
        command_name="doctor",
        module_name="planning",
        descriptor=descriptor,
        target_root=tmp_path,
        dry_run=True,
        force=True,
    )

    assert captured == {"target": str(tmp_path)}
    assert report["module"] == "planning"


def test_selected_modules_uses_descriptor_owned_presets(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    config = cli._load_workspace_config(target_root=tmp_path, descriptors=descriptors)

    selected_modules, preset_name = cli._selected_modules(
        command_name="init",
        preset_name="full",
        module_arg=None,
        target_root=tmp_path,
        descriptors=descriptors,
        config=config,
    )

    assert preset_name == "full"
    assert selected_modules == ["planning", "memory"]


def test_selected_modules_rejects_declared_missing_dependency(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    memory_descriptor = descriptors["memory"]
    descriptors["memory"] = cli.ModuleDescriptor(
        name=memory_descriptor.name,
        description=memory_descriptor.description,
        commands=memory_descriptor.commands,
        detector=memory_descriptor.detector,
        selection_rank=memory_descriptor.selection_rank,
        include_in_full_preset=memory_descriptor.include_in_full_preset,
        install_signals=memory_descriptor.install_signals,
        workflow_surfaces=memory_descriptor.workflow_surfaces,
        generated_artifacts=memory_descriptor.generated_artifacts,
        command_args=memory_descriptor.command_args,
        startup_steps=memory_descriptor.startup_steps,
        sources_of_truth=memory_descriptor.sources_of_truth,
        root_agents_cleanup_blocks=memory_descriptor.root_agents_cleanup_blocks,
        capabilities=memory_descriptor.capabilities,
        dependencies=("planning",),
        conflicts=(),
        result_contract=memory_descriptor.result_contract,
    )

    with pytest.raises(cli.ModuleSelectionError, match="requires: planning"):
        cli._validate_selected_module_contract(selected_modules=["memory"], descriptors=descriptors)


def test_selected_modules_rejects_declared_conflict(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    planning_descriptor = descriptors["planning"]
    descriptors["planning"] = cli.ModuleDescriptor(
        name=planning_descriptor.name,
        description=planning_descriptor.description,
        commands=planning_descriptor.commands,
        detector=planning_descriptor.detector,
        selection_rank=planning_descriptor.selection_rank,
        include_in_full_preset=planning_descriptor.include_in_full_preset,
        install_signals=planning_descriptor.install_signals,
        workflow_surfaces=planning_descriptor.workflow_surfaces,
        generated_artifacts=planning_descriptor.generated_artifacts,
        command_args=planning_descriptor.command_args,
        startup_steps=planning_descriptor.startup_steps,
        sources_of_truth=planning_descriptor.sources_of_truth,
        root_agents_cleanup_blocks=planning_descriptor.root_agents_cleanup_blocks,
        capabilities=planning_descriptor.capabilities,
        dependencies=(),
        conflicts=("memory",),
        result_contract=planning_descriptor.result_contract,
    )

    with pytest.raises(cli.ModuleSelectionError, match="conflicts with: memory"):
        cli._validate_selected_module_contract(selected_modules=["planning", "memory"], descriptors=descriptors)


def test_workspace_agents_template_keeps_descriptor_guidance_out_of_root_entrypoint(tmp_path: Path) -> None:
    descriptor = cli.ModuleDescriptor(
        name="signals",
        description="signals module",
        commands={},
        detector=lambda detected_root: False,
        selection_rank=30,
        include_in_full_preset=True,
        install_signals=(Path("signals.md"),),
        workflow_surfaces=(Path("signals.md"),),
        generated_artifacts=(),
        command_args={},
        startup_steps=("Read `signals.md` when the signals module is installed.",),
        sources_of_truth=("Signal routing: `signals.md`",),
        root_agents_cleanup_blocks=(),
        capabilities=("signal-routing",),
        dependencies=(),
        conflicts=(),
        result_contract=cli.ModuleResultContract(
            schema_version="workspace-module-report/v1",
            guaranteed_fields=("module",),
            action_fields=("kind",),
            warning_fields=("message",),
        ),
    )

    rendered = cli._workspace_agents_template(selected_modules=["signals"], descriptors={"signals": descriptor})

    assert "Read `signals.md` when the signals module is installed." not in rendered
    assert "Signal routing: `signals.md`" not in rendered
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in rendered
    assert 'start --profile tiny --task "<task>"' in rendered
    assert "## Module Notes" not in rendered


def _fake_descriptors(target_root: Path, calls: list[tuple[str, str, dict[str, object]]]) -> dict[str, cli.ModuleDescriptor]:
    def _build_handler(module_name: str, command_name: str):
        def _handler(**kwargs):
            calls.append((module_name, command_name, kwargs))
            return FakeResult(
                target_root=target_root,
                message=f"{command_name} {module_name}",
                dry_run=bool(kwargs.get("dry_run", False)),
                actions=[FakeAction(kind="created", path=target_root / module_name, detail=f"ran {command_name}")],
                warnings=[],
            )

        return _handler

    commands = ("install", "adopt", "upgrade", "uninstall", "doctor", "status")
    return {
        module_name: cli.ModuleDescriptor(
            name=module_name,
            description=f"{module_name} module",
            commands={command_name: _build_handler(module_name, command_name) for command_name in commands},
            detector=lambda detected_root, module_name=module_name: (detected_root / module_name).exists(),
            selection_rank=10 if module_name == "planning" else 20,
            include_in_full_preset=True,
            install_signals=(
                (Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning"))
                if module_name == "planning"
                else (Path(".agentic-workspace/memory/repo/index.md"), Path("memory/current"), Path(".agentic-workspace/memory"))
            ),
            workflow_surfaces=(
                (
                    Path("AGENTS.md"),
                    Path("TODO.md"),
                    Path(".agentic-workspace/planning/state.toml"),
                    Path(".agentic-workspace/planning/execplans"),
                    Path("docs/maintainer/contributor-playbook.md"),
                    Path(".agentic-workspace/planning"),
                )
                if module_name == "planning"
                else (
                    Path("AGENTS.md"),
                    Path(".agentic-workspace/memory/repo/index.md"),
                    Path("memory/current"),
                    Path(".agentic-workspace/memory"),
                )
            ),
            generated_artifacts=((Path(".agentic-workspace/planning/agent-manifest.json"),) if module_name == "planning" else ()),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(
                (
                    cli.RootAgentsCleanupBlock(
                        block=cli.MEMORY_POINTER_BLOCK,
                        start_marker=cli.MEMORY_WORKFLOW_MARKER_START,
                        end_marker=cli.MEMORY_WORKFLOW_MARKER_END,
                        label="memory workflow pointer block",
                    ),
                )
                if module_name == "memory"
                else ()
            ),
            capabilities=(
                ("active-execution-state", "execplan-routing")
                if module_name == "planning"
                else ("durable-repo-knowledge", "anti-rediscovery-memory", "runbook-routing")
            ),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
        for module_name in ("planning", "memory")
    }


def _descriptors_with_mixed_actions(target_root: Path) -> dict[str, cli.ModuleDescriptor]:
    def _upgrade_handler(**kwargs):
        return FakeResult(
            target_root=target_root,
            message="upgrade planning",
            dry_run=bool(kwargs.get("dry_run", False)),
            actions=[
                FakeAction(
                    kind="would update",
                    path=target_root / ".agentic-workspace" / "planning" / "agent-manifest.json",
                    detail="refresh planning manifest from managed payload",
                ),
                FakeAction(kind="skipped", path=target_root / "AGENTS.md", detail="repo-owned surface left unchanged"),
                FakeAction(kind="manual review", path=target_root / "README.md", detail="inspect manually"),
            ],
            warnings=[],
        )

    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description="planning module",
            commands={
                "install": _upgrade_handler,
                "adopt": _upgrade_handler,
                "upgrade": _upgrade_handler,
                "uninstall": _upgrade_handler,
                "doctor": _upgrade_handler,
                "status": _upgrade_handler,
            },
            detector=lambda detected_root: True,
            selection_rank=10,
            include_in_full_preset=True,
            install_signals=(Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=(Path("AGENTS.md"), Path(".agentic-workspace/planning/agent-manifest.json")),
            generated_artifacts=(Path(".agentic-workspace/planning/agent-manifest.json"),),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(),
            capabilities=("active-execution-state",),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
    }


def _descriptors_with_install_signals(
    target_root: Path, calls: list[tuple[str, str, dict[str, object]]]
) -> dict[str, cli.ModuleDescriptor]:
    descriptors = _fake_descriptors(target_root, calls)
    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description=descriptors["planning"].description,
            commands=descriptors["planning"].commands,
            detector=lambda detected_root: (
                (detected_root / "TODO.md").exists()
                and (detected_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            selection_rank=descriptors["planning"].selection_rank,
            include_in_full_preset=descriptors["planning"].include_in_full_preset,
            install_signals=(Path("TODO.md"), Path(".agentic-workspace/planning/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=descriptors["planning"].workflow_surfaces,
            generated_artifacts=descriptors["planning"].generated_artifacts,
            command_args=descriptors["planning"].command_args,
            startup_steps=descriptors["planning"].startup_steps,
            sources_of_truth=descriptors["planning"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["planning"].root_agents_cleanup_blocks,
            capabilities=descriptors["planning"].capabilities,
            dependencies=descriptors["planning"].dependencies,
            conflicts=descriptors["planning"].conflicts,
            result_contract=descriptors["planning"].result_contract,
        ),
        "memory": cli.ModuleDescriptor(
            name="memory",
            description=descriptors["memory"].description,
            commands=descriptors["memory"].commands,
            detector=lambda detected_root: (
                (detected_root / "memory" / "index.md").exists() and (detected_root / ".agentic-workspace" / "memory").exists()
            ),
            selection_rank=descriptors["memory"].selection_rank,
            include_in_full_preset=descriptors["memory"].include_in_full_preset,
            install_signals=(Path(".agentic-workspace/memory/repo/index.md"), Path("memory/current"), Path(".agentic-workspace/memory")),
            workflow_surfaces=descriptors["memory"].workflow_surfaces,
            generated_artifacts=descriptors["memory"].generated_artifacts,
            command_args=descriptors["memory"].command_args,
            startup_steps=descriptors["memory"].startup_steps,
            sources_of_truth=descriptors["memory"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["memory"].root_agents_cleanup_blocks,
            capabilities=descriptors["memory"].capabilities,
            dependencies=descriptors["memory"].dependencies,
            conflicts=descriptors["memory"].conflicts,
            result_contract=descriptors["memory"].result_contract,
        ),
    }


def test_startup_discovery_sequence_for_generic_agents(tmp_path: Path, capsys) -> None:
    """Verify that generic agents can follow the startup discovery sequence without errors.

    This test validates issue #255 (startup discoverability) by simulating the path
    a generic agent would take:
    1. Read AGENTS.md router
    2. Run agentic-workspace start for ordinary compact startup context
    3. Run agentic-workspace preflight only when takeover context is needed
    4. Run agentic-workspace config to get resolved posture
    5. Run agentic-workspace summary to get active state
    """
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    # Step 1: defaults command should provide startup guidance with correct commands
    assert cli.main(["defaults", "--section", "startup", "--format", "json"]) == 0
    defaults_output = capsys.readouterr().out
    defaults_payload = json.loads(defaults_output)

    startup_answer = defaults_payload.get("answer", {})
    assert startup_answer.get("default_canonical_agent_instructions_file") == "AGENTS.md"

    # Verify the entry and follow-up compact queries use agentic-workspace (not stale bootstrap)
    tiny_safe = startup_answer.get("tiny_safe_model", {})
    assert tiny_safe.get("entrypoint") == "AGENTS.md"
    assert tiny_safe.get("entry_query") == 'agentic-workspace start --profile tiny --task "<task>" --format json'
    queries = tiny_safe.get("first_compact_queries", [])
    assert not any("agentic-workspace preflight --format json" in q for q in queries)
    assert any("agentic-workspace start --target ./repo" in q for q in queries)
    assert any("agentic-workspace config --target" in q for q in queries)
    assert any("agentic-workspace summary" in q for q in queries)
    # Ensure NO stale bootstrap references in startup queries (most critical part)
    assert not any("agentic-planning summary" in q for q in queries)

    # Step 2: preflight should provide the bundled compact takeover context
    assert cli.main(["preflight", "--target", str(target), "--format", "json"]) == 0
    preflight_output = capsys.readouterr().out
    preflight_payload = json.loads(preflight_output)
    assert preflight_payload.get("kind") == "preflight-response/v1"
    assert "startup_guidance" in preflight_payload
    assert preflight_payload["startup_guidance"]["entry_query"] == 'agentic-workspace start --profile tiny --task "<task>" --format json'
    assert "agentic-workspace preflight --format json" not in preflight_payload["startup_guidance"]["first_compact_queries"]
    assert preflight_payload["startup_guidance"]["escalation_rules"][0]["load_next"][0].startswith("agentic-workspace ")
    assert "resolved_config" in preflight_payload
    assert "active_planning_state" in preflight_payload

    # Step 3: config command should work and be reasonably compact
    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0
    config_output = capsys.readouterr().out
    config_payload = json.loads(config_output)
    assert "workspace" in config_payload
    assert "mixed_agent" in config_payload

    # Step 4: summary command should work
    assert cli.main(["summary", "--format", "json"]) == 0
    summary_output = capsys.readouterr().out
    summary_payload = json.loads(summary_output)
    assert summary_payload.get("kind") == "planning-summary/v1"
    assert summary_payload.get("profile") == "compact"

    # Step 5: report command should work (though larger output)
    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0
    report_output = capsys.readouterr().out
    # Don't parse full report, just verify it produces output
    assert report_output  # Report should produce output


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)


def _set_git_branch(target: Path, *, current: str, default: str) -> None:
    (target / ".git" / "HEAD").write_text(f"ref: refs/heads/{current}\n", encoding="utf-8")
    (target / ".git" / "refs" / "remotes" / "origin" / "HEAD").write_text(
        f"ref: refs/remotes/origin/{default}\n",
        encoding="utf-8",
    )


def _write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write(path, json.dumps(payload, indent=2) + "\n")
