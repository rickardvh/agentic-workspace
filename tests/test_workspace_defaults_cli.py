from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_defaults_command_reports_machine_readable_default_routes_as_json(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--format", "json"]) == 0

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
    assert payload["startup"]["tiny_safe_model"]["entry_query"] == 'agentic-workspace start --task "<task>" --format json'
    assert (
        payload["startup"]["tiny_safe_model"]["first_compact_queries"][0]
        == 'agentic-workspace start --target ./repo --task "<task>" --format json'
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
    assert payload["startup"]["first_queries"][0]["command"] == 'agentic-workspace start --task "<task>" --format json'
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
    assert planning_load_next[1] == "agentic-workspace summary --format json --verbose"
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
    assert payload["install_profiles"]["rule"].startswith("Use an installed public workspace entrypoint")
    assert payload["install_profiles"]["cli_availability"]["preferred"].startswith("Use `agentic-workspace` already installed")
    assert "not the default host-repo install path" in payload["install_profiles"]["cli_availability"]["temporary_fallback"]
    assert payload["install_profiles"]["recommendation_order"] == ["memory", "planning", "full"]
    assert payload["install_profiles"]["profiles"][0]["preset"] == "memory"
    assert payload["install_profiles"]["profiles"][1]["preset"] == "planning"
    assert payload["install_profiles"]["lightweight_profile"]["preset"] == "memory"
    assert payload["lifecycle"]["primary_entrypoint"] == "agentic-workspace"
    assert "agentic-workspace install --target ./repo --preset <memory|planning|full>" == payload["lifecycle"]["default_install_command"]
    assert "if missing, install it before bootstrap" in payload["lifecycle"]["cli_availability_rule"]
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
        "Use a strong planner to normalize the vague prompt, then hand compact exploration, implementation, or validation contracts to bounded executors without prescribing the execution method."
    )
    assert payload["relay"]["handoff_command"] == "agentic-planning handoff --format json"
    assert payload["relay"]["execution_methods"][1]["id"] == "external cli or api"
    assert payload["relay"]["planner_role"]["summary"] == (
        "shape confirmed and interpreted intent, choose the proof lane, and freeze the smallest safe contract."
    )
    assert payload["relay"]["explorer_role"]["summary"] == (
        "answer one bounded repo-inspection question without owning writes or implementation direction."
    )
    assert payload["relay"]["memory_bridge"]["summary"] == (
        "when routed Memory is installed, borrow durable repo understanding before freezing the compact contract."
    )
    assert payload["setup"]["secondary"] == [
        "Do not widen init.",
        "Do not collapse setup into the proof backlog.",
        "Do not turn setup into generic analysis.",
    ]
    assert payload["validation"]["default_routes"]["planning_package"] == "make test-planning"
    workspace_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "workspace_cli")
    assert "root workspace CLI changes" in workspace_lane["when"]
    assert workspace_lane["enough_proof"] == [
        "make test-workspace",
        "make lint-workspace",
    ]
    assert workspace_lane["proof_kind"] == "targeted-test"
    assert "the change also touches generated maintainer docs" in workspace_lane["broaden_when"]
    assert "the narrow lane cannot prove the change on its own" in workspace_lane["escalate_when"]
    planning_surface_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "planning_surfaces")
    assert planning_surface_lane["enough_proof"] == [
        "agentic-planning summary --target ./repo --verbose --format json",
        "agentic-workspace doctor --target ./repo --modules planning --format json",
    ]
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
    assert "reserve uvx/pipx for explicit temporary fallback" in payload["combined_install"]["cli_availability_rule"]
    assert payload["combined_install"]["full_when"].startswith("Use --preset full only when both")
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
        "optional local machine/runtime override",
        "explicit prompting when still unsafe",
    ]
    assert payload["mixed_agent"]["local_override"]["path"] == ".agentic-workspace/config.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["supported_fields"] == [
        "workspace.cli_invoke",
        "workspace.shared_config_path",
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
        "split it into planner/explorer/implementer/validator subtasks, or escalate to a stronger planner."
    )
    assert payload["delegation_posture"]["preferred_split"] == ["planner", "explorer", "implementer", "validator"]
    assert payload["delegation_posture"]["post_decomposition_checkpoint"]["route_candidates"] == [
        "keep-local",
        "delegate-exploration",
        "delegate-implementation",
        "delegate-validation",
        "escalate-review",
        "no-safe-route",
    ]
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
    assert payload["delegation_posture"]["outcome_feedback_fields"] == [
        "route chosen",
        "route skipped reason",
        "expected savings",
        "actual friction",
        "proof result",
        "quality concern",
        "decomposition adjustment",
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
            '`agentic-workspace start --task "<task>" --format json`, then '
            "`agentic-workspace preflight --format json`, "
            "`agentic-workspace defaults --section startup --format json`, "
            "`agentic-workspace config --target ./repo --format json`, and "
            "`agentic-workspace summary --format json` before broader "
            "prose or repo-local workaround guidance."
        ),
    ]
    assert any("skills --target ./repo --task" in step for step in payload["skill_discovery"]["primary"])


def test_defaults_command_routes_through_generated_adapter(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, str | None, str | None]] = []

    def fake_defaults_handler(args) -> int:
        calls.append((args.command, args.format, getattr(args, "section", None), getattr(args, "select", None)))
        print('{"ok": true}')
        return 0

    monkeypatch.setitem(cli._GENERATED_RUNTIME_HANDLERS, "defaults.report", fake_defaults_handler)

    assert cli.main(["defaults", "--verbose", "--section", "startup", "--format", "json"]) == 0

    assert json.loads(capsys.readouterr().out) == {"ok": True}
    assert calls == [("defaults", "json", "startup", None)]


def test_defaults_command_text_emphasises_primary_and_secondary_routes(capsys) -> None:
    assert cli.main(["defaults", "--verbose"]) == 0

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
    assert ("effective output posture: agentic-workspace config --target ./repo --format json -> workspace.optimization_bias") in text
    assert "Completion:" in text
    assert "Config:" in text
    assert "Workflow artifact adapters:" in text
    assert ".agentic-workspace/docs/workspace-config-contract.md" in text
    assert "Delegated judgment:" in text
    assert "Delegated judgment follow-through:" in text
    assert "Mixed-agent:" in text
    assert "docs/delegated-judgment-contract.md" in text
    assert "make maintainer-surfaces" in text


def test_defaults_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "validation", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "intent", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "agent_aid_storage", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "clarification", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "prompt_routing", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "relay", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "improvement_latitude", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "surface_value_guardrail", "--format", "json"]) == 0

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
    assert answer["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --changed <paths> --format json"


def test_defaults_section_selector_returns_effective_authority_view(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "effective_authority", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "root_cli_authority", "--format", "json"]) == 0

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


def test_defaults_supports_selector_drilldown_for_full_payload(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--select", "startup.canonical_doc,root_cli_authority.command", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "defaults"
    assert payload["values"] == {
        "startup.canonical_doc": ".agentic-workspace/docs/minimum-operating-model.md",
        "root_cli_authority.command": "agentic-workspace defaults --section root_cli_authority --format json",
    }
    assert "available_selectors" not in payload


def test_defaults_supports_selector_drilldown_for_section_payload(capsys) -> None:
    assert cli.main(["defaults", "--section", "root_cli_authority", "--select", "answer.command", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "defaults"
    assert payload["values"] == {
        "answer.command": "agentic-workspace defaults --section root_cli_authority --format json",
    }


def test_defaults_selector_reports_available_fields_for_missing_selector(capsys) -> None:
    assert cli.main(["defaults", "--section", "root_cli_authority", "--select", "answer.nope", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["missing"] == ["answer.nope"]
    assert "answer.command" in payload["available_selectors"]


def test_defaults_section_selector_returns_optimization_bias_answer(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "optimization_bias", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "setup", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "agent_configuration_system", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "agent_configuration_queries", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "agent_configuration_workflow_extensions", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "setup_findings_promotion", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "improvement_intake", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "improvement_signal", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "operating_questions", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "install_profiles", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "install_profiles"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/which-package.md"
    assert payload["answer"]["default_entrypoint"] == "agentic-workspace"
    assert "target repo's environment" in payload["answer"]["cli_availability"]["preferred"]
    assert payload["answer"]["default_answer"].startswith("Start with `memory`")
    assert payload["answer"]["recommendation_order"] == ["memory", "planning", "full"]
    assert payload["answer"]["profiles"][0]["preset"] == "memory"
    assert payload["answer"]["profiles"][2]["preset"] == "full"
    assert payload["answer"]["partial_adoption"][1]["combination"] == "planning only"
    assert payload["answer"]["lightweight_profile"]["preset"] == "memory"
    assert "docs/which-package.md" in payload["refs"]


def test_defaults_system_intent_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "system_intent", "--format", "json"]) == 0

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
    assert cli.main(["defaults", "--verbose", "--section", "durable_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "durable_intent"}
    answer = payload["answer"]
    assert answer["intent_scopes"][0]["id"] == "task"
    assert answer["intent_scopes"][1]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert "subsystem-intent" in answer["promotion_choices"]
    assert answer["promotion_rule"].startswith("Promotion from task evidence creates reviewable")


def test_defaults_delegation_posture_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "delegation_posture", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "delegation_posture"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == ".agentic-workspace/docs/delegation-posture-contract.md"
    assert payload["answer"]["preferred_split"] == ["planner", "explorer", "implementer", "validator"]
    assert "delegate-exploration" in payload["answer"]["post_decomposition_checkpoint"]["route_candidates"]
    assert ".agentic-workspace/docs/delegation-posture-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_command_reports_runtime_resolution_policy(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--format", "json"]) == 0

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
    assert "exploration_probe" in packets["packet_types"]
    assert "strong_target_downrouting" in packets["packet_types"]
    assert "no_safe_route" in packets["packet_types"]


def test_defaults_command_reports_strong_handoff_packet_template(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--format", "json"]) == 0

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


def test_defaults_repair_recovery_section_reports_fault_taxonomy(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "repair_recovery", "--format", "json"]) == 0

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
