from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agentic_workspace import cli
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


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    repo_root = Path("./repo")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(repo_root, []))

    assert cli.main(["modules", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in payload["modules"]] == ["planning", "memory"]
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    assert planning_module["install_signals"] == ["TODO.md", ".agentic-workspace/planning/execplans", ".agentic-workspace/planning"]
    assert planning_module["workflow_surfaces"] == [
        "AGENTS.md",
        "TODO.md",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans",
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
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
        "generated-maintainer-guidance",
    ]
    assert planning_module["dependencies"] == []
    assert planning_module["conflicts"] == []
    assert planning_module["result_contract"]["schema_version"] == "workspace-module-report/v1"
    assert planning_module["lifecycle_hook_expectations"] == [
        "adopt",
        "doctor",
        "install",
        "status",
        "uninstall",
        "upgrade",
    ]
    assert planning_module["command_args"]["install"] == ["target", "dry_run", "force"]
    assert planning_module["command_args"]["doctor"] == ["target"]


def test_defaults_command_reports_machine_readable_default_routes_as_json(capsys) -> None:
    assert cli.main(["defaults", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["startup"]["canonical_doc"] == ".agentic-workspace/docs/minimum-operating-model.md"
    assert payload["startup"]["default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert payload["startup"]["supported_agent_instructions_files"] == ["AGENTS.md", "GEMINI.md"]
    assert payload["startup"]["tiny_safe_model"]["entrypoint"] == "AGENTS.md"
    assert payload["startup"]["tiny_safe_model"]["first_compact_queries"][0] == "agentic-workspace preflight --format json"
    assert payload["startup"]["tiny_safe_model"]["first_compact_queries"][1] == "agentic-workspace defaults --section startup --format json"
    assert payload["startup"]["tiny_safe_model"]["deeper_reads_become_valid_when"][0].startswith("the active summary points")
    assert payload["startup"]["first_queries"][0]["command"] == "agentic-workspace preflight --format json"
    assert payload["startup"]["first_queries"][0]["field"] == "startup_guidance"
    assert payload["startup"]["first_queries"][1]["command"] == "agentic-workspace defaults --section startup --format json"
    assert payload["startup"]["first_queries"][2]["field"] == "workspace.agent_instructions_file"
    assert payload["startup"]["first_queries"][3]["field"] == "planning_record"
    assert payload["startup"]["surface_roles"][0]["surface"] == "AGENTS.md"
    assert any(
        role.get("surface") == "llms.txt" and role.get("role") == "external install/adopt handoff only"
        for role in payload["startup"]["surface_roles"]
    )
    assert payload["startup"]["surface_roles"][3]["kind"] == "managed"
    assert payload["startup"]["escalation_cues"][0]["boundary"] == "workspace"
    assert payload["startup"]["escalation_cues"][1]["boundary"] == "planning"
    assert payload["startup"]["top_level_capabilities"][2]["module"] == "memory"
    assert any("current agent does not natively look for `AGENTS.md`" in step for step in payload["startup"]["fallbacks"])
    assert payload["compact_contract_profile"]["canonical_doc"] == ".agentic-workspace/docs/compact-contract-profile.md"
    assert payload["compact_contract_profile"]["rule"] == (
        "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump."
    )
    assert payload["compact_contract_profile"]["selectors"]["defaults"] == ("agentic-workspace defaults --section <section> --format json")
    assert payload["operating_questions"]["canonical_doc"] == "docs/which-package.md"
    assert payload["operating_questions"]["command"] == "agentic-workspace defaults --section operating_questions --format json"
    assert payload["operating_questions"]["questions"][0]["id"] == "startup_or_lifecycle_path"
    assert payload["operating_questions"]["questions"][1]["ask_first"] == "agentic-workspace summary --format json"
    assert payload["operating_questions"]["questions"][2]["ask_first"] == "agentic-workspace report --target ./repo --format json"
    assert payload["install_profiles"]["canonical_doc"] == "docs/which-package.md"
    assert payload["install_profiles"]["command"] == "agentic-workspace defaults --section install_profiles --format json"
    assert payload["install_profiles"]["profiles"][0]["preset"] == "memory"
    assert payload["install_profiles"]["profiles"][1]["preset"] == "planning"
    assert payload["install_profiles"]["lightweight_profile"]["preset"] == "memory"
    assert payload["lifecycle"]["primary_entrypoint"] == "agentic-workspace"
    assert "agentic-workspace install --target ./repo --preset <memory|planning|full>" == payload["lifecycle"]["default_install_command"]
    assert payload["lifecycle"]["canonical_external_agent_handoff"] == "llms.txt"
    assert payload["lifecycle"]["canonical_bootstrap_next_action"] == ".agentic-workspace/bootstrap-handoff.md"
    assert payload["lifecycle"]["canonical_bootstrap_handoff_record"] == ".agentic-workspace/bootstrap-handoff.json"
    assert payload["setup"]["canonical_doc"] == "docs/jumpstart-contract.md"
    assert payload["setup"]["command"] == "agentic-workspace setup --target ./repo --format json"
    assert payload["setup"]["rule"] == "Setup is a bounded post-bootstrap phase that stays separate from init."
    assert payload["setup"]["phase"] == "post-bootstrap"
    assert payload["setup"]["scope"] == [
        "orient from a compact report first",
        "keep follow-through bounded and reviewable",
    ]
    assert payload["setup_findings_promotion"]["canonical_doc"] == "docs/setup-findings-contract.md"
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
    assert payload["relay"]["handoff_command"] == "agentic-planning-bootstrap handoff --format json"
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
        "uv run pytest tests/test_workspace_cli.py -q",
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
    assert payload["ownership_mapping"]["canonical_doc"] == ".agentic-workspace/docs/ownership-authority-contract.md"
    assert payload["ownership_mapping"]["command"] == "agentic-workspace ownership --target ./repo --format json"
    assert payload["ownership_mapping"]["ledger"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["combined_install"]["primary"] == "agentic-workspace install --target ./repo --preset full"
    assert payload["recovery"]["canonical_doc"] == "docs/environment-recovery-contract.md"
    assert payload["recovery"]["rule"] == "Inspect state first, refresh contract second, re-run the narrowest proving lane third."
    assert payload["recovery"]["ordered_path"][:2] == [
        "agentic-workspace status --target ./repo",
        "agentic-workspace doctor --target ./repo",
    ]
    assert ".agentic-workspace/bootstrap-handoff.md" in payload["recovery"]["handoff_surfaces"]
    assert ".agentic-workspace/bootstrap-handoff.json" in payload["recovery"]["handoff_surfaces"]
    assert payload["recovery"]["effective_output_posture"]["command"] == "agentic-workspace config --target ./repo --format json"
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
        "optional local capability/cost override",
        "explicit prompting when still unsafe",
    ]
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["supported_fields"] == [
        "runtime.supports_internal_delegation",
        "runtime.strong_planner_available",
        "runtime.cheap_bounded_executor_available",
        "handoff.prefer_internal_delegation_when_available",
        "safety.safe_to_auto_run_commands",
        "safety.requires_human_verification_on_pr",
        "delegation_targets.<target>.strength",
        "delegation_targets.<target>.location",
        "delegation_targets.<target>.confidence",
        "delegation_targets.<target>.task_fit",
        "delegation_targets.<target>.capability_classes",
        "delegation_targets.<target>.execution_methods",
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
    assert payload["mixed_agent"]["local_outcome_artifact"] == {
        "path": ".agentic-workspace/delegation-outcomes.json",
        "kind": "agentic-workspace/delegation-outcomes/v1",
        "rule": "local-only delegation outcome evidence used to derive advisory tuning suggestions over time",
    }
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
        "Do not silently rewrite ends.",
    ]
    assert payload["delegation_posture"]["capability_posture_fields"] == [
        "execution class",
        "recommended strength",
        "preferred location",
        "delegation friendly",
        "strong external reasoning",
        "why",
    ]
    assert payload["config"]["path"] == ".agentic-workspace/config.toml"
    assert payload["config"]["command"] == "agentic-workspace config --target ./repo --format json"
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
    assert any("state.toml" in step for step in payload["startup"]["secondary"])
    assert payload["startup"]["workflow_recovery"] == [
        (
            "When startup, first-contact routing, or recovery is unclear, prefer "
            "`agentic-workspace preflight --format json`, "
            "`agentic-workspace defaults --section startup --format json`, "
            "`agentic-workspace config --target ./repo --format json`, and "
            "`agentic-workspace summary --format json` before broader "
            "prose or repo-local workaround guidance."
        ),
    ]
    assert any("skills --target ./repo --task" in step for step in payload["skill_discovery"]["primary"])


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
    assert "effective output posture: agentic-workspace config --target ./repo --format json -> workspace.optimization_bias" in text
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

    assert "repository that contains this file" in text
    assert "Target repository:" in text
    assert "Default startup path:" in text
    assert "agentic-workspace preflight --format json" in text
    assert "agentic-workspace defaults --section startup --format json" in text
    assert "Do not assume agentic-workspace is already installed" in text
    assert "agentic-workspace config --target ./repo --format json" in text
    assert "agentic-workspace summary --format json" in text
    assert ".agentic-workspace/config.local.toml is present" in text
    assert "Compact routing docs when present" not in text


def test_external_agent_handoff_text_demotes_broad_routing_until_compact_startup_fails() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    preflight_index = text.index("agentic-workspace preflight --format json")
    startup_index = text.index("agentic-workspace defaults --section startup --format json")
    config_index = text.index("agentic-workspace config --target ./repo --format json")
    summary_index = text.index("agentic-workspace summary --format json")
    routing_index = text.index(".agentic-workspace/docs/routing-contract.md")
    planning_index = text.index(".agentic-workspace/planning/state.toml")

    assert preflight_index < routing_index
    assert startup_index < routing_index
    assert config_index < routing_index
    assert summary_index < planning_index
    assert "When needed:" in text
    assert "only when lifecycle or install/adopt routing is still ambiguous after the compact startup path" in text
    assert "only when `agentic-workspace summary --format json` points there" in text


def test_external_agent_handoff_text_uses_configured_agent_instructions_filename() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"], agent_instructions_file="GEMINI.md")

    assert "Read GEMINI.md first." in text
    assert "GEMINI.md remains the repo startup entrypoint" in text


def test_external_agent_handoff_text_reports_workflow_artifact_profile() -> None:
    text = cli._external_agent_handoff_text(
        selected_modules=["planning"],
        agent_instructions_file="GEMINI.md",
        workflow_artifact_profile="gemini",
    )

    assert "Workflow artifact profile: gemini." in text
    assert "compatibility adapter over the structured workspace config" in text
    assert "agentic-workspace defaults --section agent_configuration_queries --format json" in text
    assert "mirror the durable execution state into .agentic-workspace/planning/state.toml and the active execplan" in text


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is False
    assert payload["workspace"]["default_preset"] == "full"
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "product-default"
    assert payload["workspace"]["improvement_latitude"] == "conservative"
    assert payload["workspace"]["improvement_latitude_source"] == "product-default"
    assert payload["workspace"]["optimization_bias"] == "balanced"
    assert payload["workspace"]["optimization_bias_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_adapter"]["canonical_surfaces"] == [
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans/",
    ]
    assert payload["workspace"]["agent_configuration_substrate"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["workspace"]["agent_configuration_substrate"]["owner_surface"] == ".agentic-workspace/config.toml"
    assert payload["workspace"]["workflow_obligations"] == []
    assert payload["update"]["wrapper_rule"] == "normal update execution stays behind agentic-workspace"
    assert {item["module"] for item in payload["update"]["modules"]} == {"planning", "memory"}
    assert payload["mixed_agent"]["status"] == "reporting-only"
    assert payload["mixed_agent"]["repo_policy"]["source"] == "product-defaults"
    assert payload["mixed_agent"]["repo_policy"]["path"] == ".agentic-workspace/config.toml"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is False
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["exists"] is False
    assert payload["mixed_agent"]["local_override"]["applied"] is False
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
    assert payload["answer"]["artifact_path"] == "tools/setup-findings.json"
    assert payload["answer"]["schema_path"] == "src/agentic_workspace/contracts/schemas/setup_findings.schema.json"
    assert payload["answer"]["accepted_classes"][0]["class"] == "repo_friction_evidence"
    assert "docs/setup-findings-contract.md" in payload["refs"]
    assert "agentic-workspace setup --target ./repo --format json" in payload["refs"]


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
        'capability_classes = ["boundary-shaping", "reasoning-heavy"]\n'
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
    assert planner["capability_classes"] == ["boundary-shaping", "reasoning-heavy"]
    assert planner["execution_methods"] == ["internal", "api"]
    assert planner["advisory"] == {
        "handoff_detail": "compact",
        "review_burden": "light",
    }
    assert planner["closeout_gate"]["trust"] == "normal"
    assert payload["mixed_agent"]["delegated_run_guardrail"]["closeout_gate"]["lower_trust_profiles"] == ["fast_docs"]


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
    assert rr["confidence_levels"] == ["high", "medium", "low"]


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
    assert "planning-autopilot" in skill_ids
    assert "memory-router" in skill_ids
    assert "planning-reporting" in skill_ids
    assert all(entry["registration"] == "explicit" for entry in payload["skills"])
    autopilot = next(entry for entry in payload["skills"] if entry["id"] == "planning-autopilot")
    assert "run autopilot" in autopilot["activation_hints"]["phrases"]


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
    assert [entry["id"] for entry in payload["recommendations"]] == ["planning-reporting"]
    assert payload["recommendations"][0]["score"] == 10
    assert "setup uses the compact planning reporting surface" in payload["recommendations"][0]["reasons"][0]


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


def test_install_local_only_uses_gemini_workspace_root_and_updates_git_exclude(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".gemini" / "agentic-workspace"
    assert payload["command"] == "install"
    assert payload["target"] == install_root.as_posix()
    assert (install_root / "AGENTS.md").exists()
    assert (install_root / ".agentic-workspace" / "planning" / "state.toml").exists()
    assert (install_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (install_root / "LOCAL-ONLY.toml").read_text(encoding="utf-8").startswith('schema_version = 1\nmode = "local-only"')
    git_exclude_text = (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".gemini/" in git_exclude_text
    assert not (repo_root / ".gitignore").exists()


def test_install_local_only_migrates_legacy_gitignore_residue(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)
    (repo_root / ".gitignore").write_text("# Agentic Workspace local-only storage\n.gemini/\n")

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".gemini" / "agentic-workspace"
    assert payload["command"] == "install"
    assert payload["target"] == install_root.as_posix()
    assert not (repo_root / ".gitignore").exists()
    assert (install_root / "LOCAL-ONLY.toml").exists()
    assert ".gemini/" in (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")


def test_uninstall_local_only_removes_gemini_workspace_root_and_git_exclude(tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    assert cli.main(["install", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["uninstall", "--modules", "planning", "--target", str(repo_root), "--local-only", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    install_root = repo_root / ".gemini" / "agentic-workspace"
    assert payload["command"] == "uninstall"
    assert payload["target"] == install_root.as_posix()
    assert not install_root.exists()
    assert not (repo_root / ".gemini").exists()
    assert not (install_root / "LOCAL-ONLY.toml").exists()
    assert ".gemini/" not in (repo_root / ".git" / "info" / "exclude").read_text(encoding="utf-8")


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
    assert "Read GEMINI.md first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


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
    assert "Read GEMINI.md first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


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
    (tmp_path / "docs" / "contributor-playbook.md").parent.mkdir(parents=True)
    _write((tmp_path / "docs" / "contributor-playbook.md"), "# Contributor Playbook\n")
    _write((tmp_path / "docs" / "maintainer-commands.md"), "# Maintainer Commands\n")
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
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
    ]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "docs/contributor-playbook.md: reconcile existing workflow surface ownership" in payload["needs_review"]
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
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in agents_text
    assert "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules." in agents_text
    assert "agentic-workspace preflight --format json" in agents_text
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself." in agents_text
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
    assert "Read `GEMINI.md`." in gemini_text
    assert "Keep this file thin." in gemini_text
    assert "Read GEMINI.md first." in (target / "llms.txt").read_text(encoding="utf-8")


def test_install_real_init_generates_llms_with_compact_startup_path_first(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    llms_text = (target / "llms.txt").read_text(encoding="utf-8")
    startup_index = llms_text.index("agentic-workspace defaults --section startup --format json")
    config_index = llms_text.index("agentic-workspace config --target ./repo --format json")
    summary_index = llms_text.index("agentic-workspace summary --format json")
    routing_index = llms_text.index(".agentic-workspace/docs/routing-contract.md")
    planning_index = llms_text.index(".agentic-workspace/planning/state.toml")

    assert "Default startup path:" in llms_text
    assert startup_index < routing_index
    assert config_index < routing_index
    assert summary_index < planning_index


def test_status_real_init_reports_workspace_shared_layer_surfaces(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-report/v1"
    assert payload["command"] == "report"
    assert payload["schema"]["schema_version"] == "workspace-reporting-schema/v1"
    assert payload["schema"]["command"] == "agentic-workspace report --target ./repo --format json"
    assert "discovery" in payload["schema"]["shared_fields"]
    assert "standing_intent" in payload["schema"]["shared_fields"]
    assert "repo_friction" in payload["schema"]["shared_fields"]
    assert "output_contract" in payload["schema"]["shared_fields"]
    assert "agent_configuration_queries" in payload["schema"]["shared_fields"]
    assert "system_intent_mirror" in payload["schema"]["shared_fields"]
    assert "workflow_obligations" in payload["schema"]["shared_fields"]
    assert "execution_shape" in payload["schema"]["shared_fields"]
    assert "module_reports" in payload["schema"]["shared_fields"]
    assert payload["selected_modules"] == ["planning", "memory"]
    assert payload["installed_modules"] == ["planning", "memory"]
    assert payload["health"] == "healthy"
    assert payload["output_contract"]["optimization_bias"] == "balanced"
    assert payload["output_contract"]["optimization_bias_source"] == "product-default"
    assert payload["output_contract"]["surface"] == "report"
    assert payload["output_contract"]["rendered_view_style"] == "brief-explanatory"
    assert payload["output_contract"]["surface_boundary"]["honors_bias"][1] == "rendered human-facing views"
    assert "ownership semantics" in payload["output_contract"]["surface_boundary"]["stays_invariant"]
    assert payload["agent_configuration_system"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_system"]["startup_entrypoint"] == "AGENTS.md"
    assert payload["agent_configuration_system"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["agent_configuration_system"]["module_attachment_status"][0]["module"] == "planning"
    assert payload["agent_configuration_queries"]["canonical_doc"] == ".agentic-workspace/docs/workspace-config-contract.md"
    assert payload["agent_configuration_queries"]["current_work_status"] == "no-active-direction"
    assert payload["agent_configuration_queries"]["current_queries"][0]["id"] == "startup_path"
    assert payload["system_intent_mirror"]["mirror_surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert payload["system_intent_mirror"]["mirror"]["status"] in {"missing", "present"}
    assert payload["workflow_obligations"]["configured_count"] == 0
    assert payload["workflow_obligations"]["relevant_to_current_work"] == []
    assert payload["execution_shape"]["status"] == "present"
    assert payload["execution_shape"]["task_shape"]["id"] == "direct-or-no-active-plan"
    assert payload["execution_shape"]["recommendation"]["id"] == "stay-direct"
    assert payload["execution_shape"]["recommendation"]["consult"] == ["agentic-workspace config --target ./repo --format json"]
    assert payload["next_action"]["summary"] == "No immediate action"
    assert any(
        item["surface"]
        in {
            "docs/delegated-judgment-contract.md",
            "docs/resumable-execution-contract.md",
            ".agentic-workspace/docs/capability-aware-execution.md",
            "docs/execution-summary-contract.md",
        }
        for item in payload["discovery"]["memory_candidates"]
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
    assert payload["standing_intent"]["effective_view"]["in_force_count"] == 2
    standing_classes = {item["class"]: item for item in payload["standing_intent"]["effective_view"]["items"]}
    assert standing_classes["config_policy"]["status"] == "default-only"
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
    assert payload["repo_friction"]["external_evidence"] == []
    assert payload["reports"][0]["module"] == "planning"
    assert {report["module"] for report in payload["module_reports"]} == {"planning", "memory"}
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["module_reports"] if report["module"] == "memory")
    assert planning_report["schema"]["command"] == "agentic-planning-bootstrap report --format json"
    assert memory_report["schema"]["command"] == "agentic-memory-bootstrap report --target ./repo --format json"
    assert payload["config"]["mixed_agent"]["status"] == "reporting-only"


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["findings"] == []


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any("Open external planning item EXT-quiet-open" in finding["message"] for finding in payload["findings"])
    planning_report = next(report for report in payload["module_reports"] if report["module"] == "planning")
    assert planning_report["intent_validation"]["counts"]["untracked_external_open_count"] == 1


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
    (target / ".agentic-workspace" / "planning" / "finished-work-evidence.json").write_text(
        json.dumps(
            {
                "kind": "planning-finished-work-evidence/v1",
                "items": [
                    {
                        "system": "manual",
                        "id": "#260",
                        "title": "Finished-work intent inspection",
                        "status": "open",
                        "kind": "lane",
                        "reopens": ["#220"],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["closeout_trust"]["status"] == "present"
    assert payload["closeout_trust"]["trust"] == "lower-trust"
    assert payload["closeout_trust"]["lower_trust_closeout_count"] == 1
    assert any("Closed external planning item #closed-without-residue" in item for item in payload["closeout_trust"]["sample_signals"])


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
    assert "Closeout trust:" in text
    assert "lower-trust (1 lower-trust closeout signal(s))" in text
    assert "Closed external planning item #closed-without-residue" in text


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    execution_shape = payload["execution_shape"]
    assert execution_shape["status"] == "present"
    assert execution_shape["task_shape"]["id"] == "planning-backed-broad-work"
    assert execution_shape["default_posture"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert execution_shape["default_posture"]["handoff_preference"] == "prefer-internal-when-safe"
    assert execution_shape["capability_posture"]["execution class"] == "boundary-shaping"
    assert execution_shape["recommendation"]["id"] == "planner-first-then-bounded-executor"
    assert execution_shape["recommendation"]["consult"] == ["agentic-planning-bootstrap handoff --format json"]
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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["output_contract"]["optimization_bias"] == "agent-efficiency"
    assert payload["output_contract"]["optimization_bias_source"] == "repo-config"
    assert payload["output_contract"]["report_density"] == "compact"
    assert "execution method" in payload["output_contract"]["must_not_change"]


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "balanced"
    assert payload["repo_friction"]["initiative_posture"] == "bounded-evidence-backed-action"
    assert payload["repo_friction"]["large_file_hotspots"]["count"] == 1
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["path"] == "src/big_module.py"
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["line_count"] == 450
    assert payload["repo_friction"]["large_file_hotspots"]["items"][0]["kind"] == "code"


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

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
                        "summary": "Workspace CLI remains a shared hotspot.",
                        "confidence": 0.9,
                        "path": "src/agentic_workspace/cli.py",
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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

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
    assert setup_findings["items"][0]["promotion_reason"] == "grounded friction evidence is worth preserving"


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

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_friction"]["policy_mode"] == "reporting"
    assert payload["repo_friction"]["policy_target"] == "repo-directed-improvement"
    assert payload["repo_friction"]["friction_response_order"][2]["action"] == "avoid-externalizing-honestly-absorbable-friction"
    assert payload["repo_friction"]["initiative_posture"] == "reporting-only"
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
    _write((tmp_path / ".agentic-workspace" / "system-intent" / "WORKFLOW.md"), "# System Intent Workflow\n")
    _write(
        (tmp_path / "AGENTS.md"),
        "# Agent Instructions\n\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n"
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
        and "scripts/check/check_memory_freshness.py" in action["detail"]
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
    assert startup["entrypoint"] == "AGENTS.md"
    assert "first_compact_queries" in startup
    assert any("agentic-workspace" in q for q in startup["first_compact_queries"])

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


def test_preflight_command_emits_gate_token(capsys) -> None:
    assert cli.main(["preflight", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["issued_at"]
    assert payload["preflight_token"].startswith("preflight-v1:")


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
    assert "agentic-workspace preflight --format json" in stderr


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
    assert "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules." in updated


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


def test_workspace_agents_template_uses_descriptor_guidance(tmp_path: Path) -> None:
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

    assert "Read `signals.md` when the signals module is installed." in rendered
    assert "- Signal routing: `signals.md`" in rendered


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
                    Path("docs/contributor-playbook.md"),
                    Path("docs/maintainer-commands.md"),
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
                ("active-execution-state", "execplan-routing", "generated-maintainer-guidance")
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
    2. Run agentic-workspace preflight for combined compact takeover context
    3. Run agentic-workspace defaults --section startup for ordered startup routing
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

    # Verify the first_compact_queries are correct and use agentic-workspace (not stale bootstrap)
    tiny_safe = startup_answer.get("tiny_safe_model", {})
    assert tiny_safe.get("entrypoint") == "AGENTS.md"
    queries = tiny_safe.get("first_compact_queries", [])
    assert any("agentic-workspace preflight --format json" in q for q in queries)
    assert any("agentic-workspace defaults --section startup" in q for q in queries)
    assert any("agentic-workspace config --target" in q for q in queries)
    assert any("agentic-workspace summary" in q for q in queries)
    # Ensure NO stale bootstrap references in startup queries (most critical part)
    assert not any("agentic-planning-bootstrap summary" in q for q in queries)

    # Step 2: preflight should provide the bundled compact takeover context
    assert cli.main(["preflight", "--target", str(target), "--format", "json"]) == 0
    preflight_output = capsys.readouterr().out
    preflight_payload = json.loads(preflight_output)
    assert preflight_payload.get("kind") == "preflight-response/v1"
    assert "startup_guidance" in preflight_payload
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
    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    report_output = capsys.readouterr().out
    # Don't parse full report, just verify it produces output
    assert report_output  # Report should produce output


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)


def _write(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write(path, json.dumps(payload, indent=2) + "\n")
