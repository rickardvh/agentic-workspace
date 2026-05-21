from __future__ import annotations

import argparse

from agentic_workspace.contract_tooling import skill_specs_manifest

# ruff: noqa: F403,F405,I001
from tests.workspace_cli_support import *


def _assert_next_safe_action_valid(packet: dict[str, object]) -> None:
    from agentic_workspace.contract_tooling import contract_schema

    schema = contract_schema("startup_context.schema.json")["$defs"]["next_safe_action"]
    errors = list(Draft202012Validator(schema).iter_errors(packet))
    assert errors == []


def _start_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context", {})
    return context if isinstance(context, dict) else {}


def _preflight_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context", {})
    return context if isinstance(context, dict) else payload


def _preflight_next(payload: dict[str, object]) -> dict[str, object]:
    next_action = payload.get("next")
    if isinstance(next_action, dict):
        return next_action
    legacy = payload.get("immediate_next_allowed_action")
    return legacy if isinstance(legacy, dict) else {}


def _start_primary_action(payload: dict[str, object]) -> dict[str, object]:
    action = payload.get("immediate_next_allowed_action")
    if isinstance(action, dict):
        return action
    context_action = _start_context(payload).get("primary_action")
    return context_action if isinstance(context_action, dict) else {}


def _start_active_state(payload: dict[str, object]) -> dict[str, object]:
    active = payload.get("active_state_summary")
    if isinstance(active, dict):
        return active
    context_active = _start_context(payload).get("active_state")
    return context_active if isinstance(context_active, dict) else {}


def _start_skill_routing(payload: dict[str, object]) -> dict[str, object]:
    routing = payload.get("skill_routing")
    if isinstance(routing, dict):
        return routing
    context_routing = _start_context(payload).get("skill_routing")
    return context_routing if isinstance(context_routing, dict) else {}


def _start_task_context(payload: dict[str, object]) -> dict[str, object]:
    task = payload.get("task_intent")
    if isinstance(task, dict):
        return task
    context_task = _start_context(payload).get("task")
    return context_task if isinstance(context_task, dict) else {}


def _start_context_value(payload: dict[str, object], key: str) -> object:
    return payload[key] if key in payload else _start_context(payload)[key]


def _start_planning_safety_gate(payload: dict[str, object]) -> dict[str, object]:
    gate = payload.get("planning_safety_gate")
    if isinstance(gate, dict):
        return gate
    context_gate = _start_context(payload).get("planning_safety_gate")
    if isinstance(context_gate, dict):
        return context_gate
    planning = _start_context(payload).get("planning", {})
    if isinstance(planning, dict) and isinstance(planning.get("planning_safety_gate"), dict):
        return planning["planning_safety_gate"]
    raise KeyError("planning_safety_gate")


def _start_workflow_sufficiency(payload: dict[str, object]) -> dict[str, object]:
    sufficiency = payload.get("workflow_sufficiency")
    if isinstance(sufficiency, dict):
        return sufficiency
    context_sufficiency = _start_context(payload).get("workflow_sufficiency")
    if isinstance(context_sufficiency, dict):
        return context_sufficiency
    planning = _start_context(payload).get("planning", {})
    if isinstance(planning, dict) and isinstance(planning.get("workflow_sufficiency"), dict):
        return planning["workflow_sufficiency"]
    raise KeyError("workflow_sufficiency")


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
    assert cli.main(["preflight", "--verbose", "--format", "json"]) == 0

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
    assert startup["skill_routing"]["query"] == f'{configured_cli} skills --target . --task "<task>" --format json'
    assert "planning-autopilot" not in {route["skill"] for route in startup["skill_routing"]["preferred_routes"]}
    assert startup["skill_routing"]["enabled_advanced_routes"] == ["external_adapters", "review_artifacts"]

    # Verify config is present
    config = payload["resolved_config"]
    assert "workspace_config" in config
    assert "agent_instructions_file" in config
    assert config["agent_instructions_file"] == "AGENTS.md"


def test_preflight_default_returns_tiny_takeover_router(capsys) -> None:
    assert cli.main(["preflight", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "preflight-response/v1"
    assert payload["mode"] == "tiny-takeover-router"
    assert set(payload) <= {"kind", "mode", "target", "issued_at", "preflight_token", "next", "context", "drill_down"}
    assert "active_state_summary" in _preflight_context(payload)
    assert "startup_guidance" not in payload
    assert _preflight_next(payload)["action"] == "recover-orientation"
    assert payload["drill_down"]["detail_commands"]["full_takeover"].endswith("preflight --target . --verbose --format json")


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
                "--verbose",
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
    assert payload["workflow_obligations"]["match_evidence"]["matching"][0]["force"] == "required-before-closeout"
    assert payload["workflow_obligations"]["match_evidence"]["matching"][0]["gate_status"] == "required-before-closeout"
    assert payload["closeout_obligations"]["status"] == "present"
    primary = payload["closeout_obligations"]["primary_next_action"]
    assert primary["action"] == "run-closeout-obligation"
    assert primary["id"] == "dogfooding_lane_closeout"
    assert primary["command"] == "agentic-workspace skills --target . --task dogfooding --format json"
    assert primary["required_inputs"] == ["task scope or active planning record", "changed paths or proof scope", "validation results"]
    assert "route durable residue" in primary["next_proof"]
    assert obligations[0]["id"] == "dogfooding_lane_closeout"
    assert obligations[0]["stage"] == "closeout"
    assert obligations[0]["force"] == "required-before-closeout"


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

    assert cli.main(["preflight", "--target", str(target), "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    obligations = payload["closeout_obligations"]["required_before_lane_closeout"]
    assert payload["workflow_obligations"]["match_evidence"]["match_count"] == 0
    assert payload["closeout_obligations"]["status"] == "present"
    assert payload["closeout_obligations"]["primary_next_action"]["id"] == "dogfooding_lane_closeout"
    assert obligations[0]["review_hint"] == "Surface actionable findings clearly."
    assert obligations[0]["force"] == "required-before-closeout"
    posture = payload["operating_posture"]
    assert posture["improvement_latitude"]["mode"] == "proactive"
    assert posture["improvement_latitude"]["initiative_posture"] == "bounded-standalone-action-allowed"
    assert posture["optimization_bias"]["mode"] == "agent-efficiency"
    assert posture["closeout_nudge"]["field"] == "improvement_signal_review"
    assert posture["incidental_finding_policy"]["status"] == "required-reporting"


def test_preflight_matches_planless_workflow_obligations_from_task_text(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n"
        "[workflow_obligations.workspace_closeout]\n"
        'summary = "Run workspace closeout checks."\n'
        'stage = "closeout"\n'
        'force = "required-before-closeout"\n'
        'scope_tags = ["workspace"]\n'
        'commands = ["agentic-workspace report --target . --section closeout_trust --format json"]\n'
        'review_hint = "Workspace orchestration applies even without active Planning."\n\n'
        "[workflow_obligations.dogfooding_closeout]\n"
        'summary = "Route dogfooding residue."\n'
        'stage = "closeout"\n'
        'force = "required-before-closeout"\n'
        'scope_tags = ["dogfooding"]\n'
        'commands = ["agentic-workspace skills --target . --task dogfooding --format json"]\n'
        'review_hint = "Do not bypass dogfooding just because no execplan exists."\n',
    )

    assert (
        cli.main(
            [
                "preflight",
                "--target",
                str(target),
                "--task",
                "Fix workspace workflow obligations during dogfooding closeout without writing a plan",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    workflow = payload["workflow_obligations"]
    assert workflow["match_evidence"]["observed_scope_source"] == "task text"
    assert workflow["match_evidence"]["match_count"] == 2
    assert workflow["current_scope_tags"] == ["dogfooding", "planning", "self-improvement", "workspace"]
    assert {item["id"] for item in workflow["relevant_to_current_work"]} == {"workspace_closeout", "dogfooding_closeout"}
    assert payload["closeout_obligations"]["status"] == "present"


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

    assert cli.main(["preflight", "--target", str(target), "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    active_state = payload["active_planning_state"]
    assert active_state["planning_record"]["status"] == "unavailable"
    assert active_state["todo"]["active_count"] == 1
    assert active_state["todo"]["active_items"][0]["next_action"] == "land the preflight fix."
    guidance = payload["startup_guidance"]
    assert guidance["entry_query"] == 'uv run agentic-workspace start --task "<task>" --format json'
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

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--changed",
                "generated/workspace/python/cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    _assert_invoked_cli_identity(payload, target_relation="outside-target")
    assert "cli_compatibility" not in payload
    assert payload["kind"] == "startup-context/v1"
    assert payload["startup_sequence"][0]["surface"] == "AGENTS.md"
    assert payload["startup_sequence"][1]["command"] == "uv run agentic-workspace preflight --format json"
    assert payload["startup_sequence"][2]["command"] == "uv run agentic-workspace summary --format json"
    assert payload["context_router"]["views"][0]["command"] == "uv run agentic-workspace start --target ./repo --format json"
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
    assert payload["skill_routing"]["query"].startswith('uv run agentic-workspace skills --target "')
    assert payload["skill_routing"]["query"].endswith('" --task "<task>" --format json')
    assert "planning-autopilot" not in {route["skill"] for route in payload["skill_routing"]["preferred_routes"]}
    assert payload["skill_routing"]["available_advanced_route_command"].startswith('uv run agentic-workspace modules --target "')
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
    assert payload["delegation_decision"]["mode"] in {"suggest", "auto"}
    assert payload["delegation_decision"]["decision"] in {
        "stay-local",
        "suggest-delegation",
        "suggest-downroute",
        "suggest-escalation",
        "delegate-bounded-slice",
        "manual-handoff",
        "ask-human",
    }
    assert len(json.dumps(payload, sort_keys=True)) < 18200
    assert payload["proof"]["required_commands"] == [
        "uv run agentic-workspace defaults --section root_cli_authority --format json",
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
    ]
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "hand-owned-executable"
    assert payload["path_boundaries"] == [
        {
            "path": "generated/workspace/python/cli.py",
            "authority": "repo-owned",
            "warning": None,
            "requires_attention": False,
        }
    ]


def test_start_surfaces_maintainer_mode_dogfooding_routes_from_local_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[workspace]
maintainer_mode = true
""".strip(),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    maintainer_mode = _start_context_value(payload, "maintainer_mode")
    assert maintainer_mode["status"] == "enabled"
    assert maintainer_mode["source"] == "local-override"
    assert [route["section"] for route in maintainer_mode["dogfooding_reports"]] == [
        "improvement_intake",
        "repo_friction",
        "successful_completion_cost",
    ]
    relative_target = os.path.relpath(target.resolve(), Path.cwd().resolve()).replace("\\", "/")
    assert maintainer_mode["primary_next_action"]["command"] == (
        f"agentic-workspace report --target {relative_target} --section improvement_intake --format json"
    )
    assert maintainer_mode["primary_next_action"]["summary"].startswith("Use compact dogfooding report routes")


def test_start_tiny_profile_returns_first_contact_projection(capsys) -> None:
    task = "Start the way the repo instructs a new agent to start. Do not implement anything yet."
    assert cli.main(["start", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded) < 15000
    assert payload["kind"] == "startup-context/v1"
    assert payload["drill_down"]["rule"].startswith("Use --select")
    assert "cli_invocation" in payload["drill_down"]["available_selectors"]
    assert _start_active_state(payload)["todo_active_count"] >= 0
    assert _start_primary_action(payload)["action"] in {
        "choose-smallest-workflow-shape",
        "continue-active-planning-record",
        "promote-or-create-active-execplan",
        "record-delegation-decision",
    }
    assert "implement --changed <paths>" in _start_task_context(payload)["implement_changed_command"]
    assert _start_context(payload)["acceptance"]["status"] == "inferred"
    assert _start_context(payload)["acceptance"]["closeout_required"] is True
    assert payload["skills"]["catalog"]["command"] == 'uv run agentic-workspace skills --target . --task "<task>" --format json'
    assert _start_task_context(payload)["status"] == "present"
    assert _start_task_context(payload)["implement_changed_command"] == (
        f'uv run agentic-workspace implement --changed <paths> --task "{task}" --format json'
    )
    assert "durable_intent" not in _start_context(payload)
    assert "cli_compatibility" not in payload
    assert "proof" not in payload
    assert "authority_markers" not in payload


def test_start_default_returns_selector_first_router(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    task = "Promote actionable findings to issues"
    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert len(encoded) < 9000
    assert payload["kind"] == "startup-context/v1"
    assert set(payload) == {"kind", "target", "next_safe_action", "skills", "context", "drill_down"}
    competing_top_level_decision_fields = {
        "immediate_next_allowed_action",
        "skill_routing",
        "workflow_sufficiency",
        "task_intent",
        "acceptance",
        "planning_safety_gate",
        "delegation_decision",
        "adaptive_routing",
        "context_router",
        "invoked_cli_identity",
    }
    assert competing_top_level_decision_fields.isdisjoint(payload)
    assert _start_primary_action(payload)["action"] in {
        "choose-smallest-workflow-shape",
        "continue-active-planning-record",
    }
    packet = payload["next_safe_action"]
    _assert_next_safe_action_valid(packet)
    assert packet["kind"] == "agentic-workspace/next-safe-action/v1"
    assert packet["next_safe_action"] == _start_primary_action(payload)["action"]
    assert packet["module_slot"] in {"workspace", "planning"}
    assert packet["preferred_cli_effect"] in {"none", "reporting"}
    assert packet["cli_availability"] in {"not-needed", "unknown"}
    assert packet["allowed_next_actions"]
    assert isinstance(packet["closure_blockers"], list)
    assert isinstance(packet["continuation_owner_required"], bool)
    assert packet["memory_consultation_status"] in {"recommended", "unknown"}
    assert packet["source_fields"] == [
        "immediate_next_allowed_action",
        "workflow_sufficiency",
        "skill_routing",
        "memory_consult",
    ]
    profile = payload["drill_down"]["ordinary_profile"]
    assert "primary=next_safe_action" in profile
    assert "skills=proj" in profile
    assert "legacy=select/context" in profile
    assert _start_active_state(payload)["todo_active_count"] >= 0
    assert payload["skills"]["required"] or payload["skills"]["recommended"] or payload["skills"]["catalog"]["available"]
    for recommendation in payload["skills"]["recommended"]:
        assert recommendation["path"]
        assert recommendation["reasons"]
    assert payload["skills"]["catalog"]["command"].startswith("agentic-workspace skills --target")
    assert "--target ./repo" not in payload["skills"]["catalog"]["command"]
    assert _start_task_context(payload)["implement_changed_command"] == (
        f'agentic-workspace implement --changed <paths> --task "{task}" --format json'
    )
    startup_text = json.dumps(_start_primary_action(payload), sort_keys=True)
    assert "preflight" not in startup_text
    assert "defaults" not in startup_text
    assert "config --" not in startup_text
    assert "report --" not in startup_text
    assert "summary --" not in startup_text or _start_primary_action(payload)["action"] == "continue-active-planning-record"
    assert _start_context(payload)["acceptance"]["items"]
    assert _start_context(payload)["acceptance"]["items"][0]["status"] == "unchecked"
    assert "acceptance" in payload["drill_down"]["available_selectors"]
    assert "durable_intent_promotion" in payload["drill_down"]["available_selectors"]
    assert "available_selectors" in payload["drill_down"]
    assert "cli_invocation" in payload["drill_down"]["available_selectors"]


def test_next_safe_action_schema_rejects_missing_typed_fields() -> None:
    from agentic_workspace.contract_tooling import contract_schema

    schema = contract_schema("startup_context.schema.json")["$defs"]["next_safe_action"]
    packet = {
        "kind": "agentic-workspace/next-safe-action/v1",
        "next_safe_action": "choose-smallest-workflow-shape",
        "why": "fixture",
    }

    errors = list(Draft202012Validator(schema).iter_errors(packet))

    assert {tuple(error.path) for error in errors}
    assert any("required_skill" in error.message for error in errors)
    assert any("preferred_cli_effect" in error.message for error in errors)


def test_start_changed_path_next_safe_action_marks_proof_required(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["start", "--target", str(target), "--changed", "README.md", "--format", "json"]) == 0

    packet = json.loads(capsys.readouterr().out)["next_safe_action"]
    _assert_next_safe_action_valid(packet)
    assert packet["proof_required"] is True
    assert packet["module_slot"] == "workspace.proof"
    assert packet["preferred_cli"] == "agentic-workspace proof --changed README.md --format json"
    assert packet["preferred_cli_effect"] == "validating"


def test_start_completion_question_requires_closeout_trust_when_followup_remains(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n\n[assurance]\nstrict_closeout = true\n",
    )
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "epic-continuation", maturity = "candidate", status = "next", priority = "P1", refs = "package-owned-only", title = "Continue epic", outcome = "Finish the original epic intent.", reason = "A completed lane did not satisfy the larger intent.", promotion_signal = "Promote before closeout.", suggested_first_slice = "Promote the next lane." },
]
""",
    )
    _write_json(
        target / ".agentic-workspace" / "planning" / "decompositions" / "epic-continuation.decomposition.json",
        {
            "kind": "planning-decomposition/v1",
            "title": "Epic continuation",
            "outcome": "Finish the original epic intent.",
            "status": "ready-for-lane-promotion",
            "lanes": [
                {
                    "id": "next-lane",
                    "title": "Next lane",
                    "readiness": "ready",
                    "owner_surface": ".agentic-workspace/planning/state.toml",
                }
            ],
        },
    )

    assert cli.main(["start", "--target", str(target), "--task", "Can I mark this work complete?", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "inspect-closeout-trust-before-completion-answer"
    assert action["command"] == "agentic-workspace report --target ./repo --section closeout_trust --format json"
    packet = payload["next_safe_action"]
    _assert_next_safe_action_valid(packet)
    assert packet["preferred_cli_effect"] == "reporting"
    assert packet["continuation_owner_required"] is True
    assert "claim completion before closeout trust is reconciled" in packet["closure_blockers"]
    closeout = _start_context_value(payload, "closeout_trust_inspection")
    assert closeout["status"] == "required"
    assert closeout["trust"] == "lower-trust"
    assert closeout["strict_closeout_gate"]["status"] == "blocked"
    assert closeout["intent_satisfaction"]["trust"] == "follow-up-required"
    assert "completion_options" not in payload
    assert "completion_options" not in closeout
    assert "closeout_trust_inspection" in payload["drill_down"]["available_selectors"]


def test_start_select_returns_requested_startup_fields(capsys) -> None:
    task = "Promote actionable findings to issues"
    assert cli.main(["start", "--task", task, "--select", "cli_invocation,durable_intent.missing", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "start"
    assert payload["values"]["cli_invocation"]["primary"] == "uv run agentic-workspace"
    assert payload["missing"] == ["durable_intent.missing"]
    assert "skill_routing" in payload["available_selectors"]


def test_start_select_returns_acceptance_and_durable_promotion(capsys) -> None:
    task = "Default outputs should stay compact and drill-down based going forward"
    assert cli.main(["start", "--task", task, "--select", "acceptance,durable_intent_promotion", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    acceptance = payload["values"]["acceptance"]
    assert acceptance["status"] == "inferred"
    assert acceptance["closeout_required"] is True
    assert acceptance["items"][0]["id"] == "A1"
    promotion = payload["values"]["durable_intent_promotion"]
    assert promotion["status"] == "candidate"
    assert "should" in promotion["matched_markers"]
    assert "going forward" in promotion["matched_markers"]


def test_start_tiny_flags_repo_local_cli_invocation_mismatch(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert cli.main(["start", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    invocation = payload["cli_invocation"]
    assert invocation["primary"] == "uv run agentic-workspace"
    assert invocation["source"] == "local-override"
    assert invocation["mismatch"]["status"] == "attention"
    assert invocation["mismatch"]["invoked_target_relation"] == "outside-target"
    assert "outside the target repo" in invocation["mismatch"]["reasons"][0]
    assert invocation["mismatch"]["trust"] == "lower-trust-until-confirmed"
    assert "configured cli_invocation.primary" in invocation["mismatch"]["required_next_action"]


def test_start_tiny_keeps_moderate_task_carry_forward_command_executable(capsys) -> None:
    task = (
        "Add robust CSV row importing to this Python package. Implement import_rows_from_csv(text, *, "
        "required_fields=None, delimiter=',') in sample_app, exporting it from sample_app.__init__. "
        "It should parse CSV text with the standard library, normalize headers, validate row data, "
        "accumulate row-level errors instead of raising for bad rows, add focused pytest coverage, "
        "update README with a concise usage example, and run the relevant tests."
    )

    assert cli.main(["start", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    task_context = _start_task_context(payload)
    command = task_context["implement_changed_command"]
    assert task_context["task_argument_mode"] == "inline"
    assert "--task-file" not in command
    assert f'--task "{task}"' in command


def test_start_tiny_routes_existing_task_paths_to_implement_surface(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "fixture\n")

    task = "Prepare for a narrow README.md wording edit, but do not edit files yet."
    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "inspect-known-task-paths"
    assert action["detected_paths"] == ["README.md"]
    assert action["command"] == (
        'agentic-workspace implement --changed README.md --task "Prepare for a narrow README.md wording edit, but do not edit files yet." --format json'
    )
    assert action["read_first"] == [action["command"]]


def test_start_tiny_routes_config_posture_questions_to_tiny_config(capsys) -> None:
    task = (
        "Inspect this repo enough to answer how a small follow-up should be reported. "
        "Keep the answer aligned with the repo's configured operating and reporting posture."
    )

    assert cli.main(["start", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "inspect-effective-config"
    assert action["command"] == "uv run agentic-workspace config --format json"
    assert action["read_first"] == [action["command"]]
    assert "tiny config surface" in action["summary"]
    assert len(json.dumps(payload, sort_keys=True)) < 14500


def test_start_tiny_compacts_long_task_carry_forward_command(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    task = " ".join(
        [
            "Implement a deliberately long follow-up request that asks the agent to preserve acceptance reconciliation, "
            "avoid repeating large prompts in every generated command, keep objective-drift checks connected to the original "
            "task intent, and make the next command compact enough for weak model startup surfaces.",
            "Also ensure closeout still maps requested outcomes to proof and delivered files.",
        ]
        * 5
    )

    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    task_context = _start_task_context(payload)
    command = task_context["implement_changed_command"]
    assert task_context["task_argument_mode"] == "task-file"
    assert "--task-file .agentic-workspace/local/scratch/task-intent.txt" in command
    assert "--task " not in command
    assert task not in command
    assert task_context["task_file"] == ".agentic-workspace/local/scratch/task-intent.txt"
    assert "Write the original request once" in task_context["task_file_instruction"]
    assert len(task_context["task_digest"]) == 16
    assert task_context["task_text_length"] == len(task)
    assert len(json.dumps(payload, sort_keys=True)) < 8800


def test_start_tiny_routes_prep_only_handoff_to_planning_bridge(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = (
        "I want this repository to support importing rows from CSV files, but do not implement the feature yet. "
        "Prepare enough durable state that a later coding pass can safely start from a bounded first slice."
    )
    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "create-prep-only-planning-state"
    assert action["command"].startswith("agentic-workspace planning new-plan")
    assert "--prep-only" in action["command"]
    assert action["next_proof"] == "agentic-workspace summary --verbose --format json"
    assert action["read_first"] == []
    packet = payload["next_safe_action"]
    assert packet["next_safe_action"] == "create-prep-only-planning-state"
    assert packet["module_slot"] == "planning"
    assert packet["preferred_cli"] == action["command"]
    assert packet["completion_claim_allowed"] is False
    assert {"edit product source", "claim implementation complete"} <= set(packet["forbidden_actions"])
    assert packet["proof_required"] is True
    assert "do not create product source" in action["summary"]
    prep_only = _start_context_value(payload, "prep_only_handoff")
    assert prep_only["first_command"].startswith("agentic-workspace planning new-plan")
    assert prep_only["reference_command"] == "agentic-workspace planning --format json"
    assert "--prep-only" in prep_only["preferred_mutation_command_template"]
    assert prep_only["after_write"] == "agentic-workspace summary --verbose --format json"
    assert prep_only["stop_after_summary"] is True
    assert "no" in prep_only["open_execplan_after_creation"]
    assert "defer unless summary reports" in prep_only["manual_execplan_tightening"]
    assert any("smallest schema-preserving" in item for item in prep_only["allowed_after_new_plan"])
    assert ".agentic-workspace/planning/execplans/" in prep_only["allowed_write_scope"]
    assert "tests or fixtures" in prep_only["forbidden_until_implementation_requested"]
    assert "manual JSON polishing or ad hoc validation loops" in prep_only["forbidden_until_implementation_requested"]
    assert len(json.dumps(payload, sort_keys=True)) < 9500


def test_start_tiny_routes_paraphrased_prep_only_handoff_to_planning_bridge(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare repository state for future CSV row import feature without implementing it"
    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert _start_primary_action(payload)["action"] == "create-prep-only-planning-state"
    assert _start_context_value(payload, "prep_only_handoff")["status"] == "required"


def test_start_tiny_routes_groundwork_without_implementation_to_prep_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare groundwork for CSV row import support without implementing feature"
    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "create-prep-only-planning-state"
    assert action["command"].startswith("agentic-workspace planning new-plan")
    assert action["read_first"] == []


def test_start_tiny_routes_durable_plan_state_without_code_to_prep_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare durable implementation plan/state for CSV row import feature with no code changes yet"
    assert cli.main(["start", "--target", str(target), "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = _start_primary_action(payload)
    assert action["action"] == "create-prep-only-planning-state"
    assert "--prep-only" in action["command"]


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

    assert cli.main(["start", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    decision = _start_context_value(payload, "delegation_decision")
    assert decision["decision"] == "ask-human"
    assert decision["required_next_action"] == "stop-and-ask-human"
    assert decision["manual_prompt"]["target"] == "human-or-external-strong-general-purpose-model"
    assert decision["clarification_mode"] == "ask-first"


def test_start_tiny_surfaces_auto_delegation_safety_gate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
            ]
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "redesign workflow delegation policy",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    config_effect = _start_context_value(payload, "delegation_decision")["config_effect"]
    assert config_effect["authority"] == "local-config"
    assert config_effect["source_path"] == ".agentic-workspace/config.local.toml"
    assert config_effect["configured_delegation_mode"] == "auto"
    assert config_effect["delegation_mode"] == "suggest"
    assert config_effect["safe_to_auto_run_commands"] is False
    assert "safe_to_auto_run_commands" in config_effect["disabled_reason"]


def test_start_tiny_prepares_manual_external_relay_for_early_epic_shaping(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape an epic around product intent and user-facing policy before implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    decision = _start_context_value(json.loads(capsys.readouterr().out), "delegation_decision")
    assert decision["required_next_action"] == "prepare-manual-handoff"
    effort = decision["effort_recommendation"]
    assert effort["orchestrator"] == "medium"
    assert effort["planner"] == "external-high-judgment"
    assert effort["cost_posture"] == "human-interrupt-only-if-worth-it"
    assert decision["delegation_next_step"]["status"] == "prepare-or-report"
    assert decision["delegation_next_step"]["must_report_if_not_run"] is True
    assert decision["config_effect"]["execution_authority"] == "manual-relay-only"
    relay = decision["manual_external_relay"]
    assert relay["status"] == "appropriate"
    assert relay["interrupt_cost"] == "human-relay-required"
    assert decision["manual_prompt"]["kind"] == "agentic-workspace/manual-external-relay-prompt/v1"
    assert "not asked to code" in decision["manual_prompt"]["copy_paste"]
    assert "Do not write code" in decision["manual_prompt"]["constraints"][0]


def test_start_tiny_keeps_config_effect_when_auto_mode_is_safety_downgraded(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
            ]
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Can this request be automatically delegated to a cheaper executor under local settings?",
                "--select",
                "delegation_decision",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = payload["values"]["delegation_decision"]
    assert decision["decision"] == "stay-local"
    assert decision["config_effect"]["delegation_mode"] == "suggest"
    assert decision["config_effect"]["safe_to_auto_run_commands"] is False


def test_start_surfaces_decomposed_active_work_delegation_candidates_and_auto_skip(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = false",
                "",
                "[delegation_targets.mini]",
                'strength = "medium"',
                'location = "local"',
                'capability_classes = ["mixed", "mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        "\n".join(
            [
                'kind = "agentic-planning-state"',
                'schema_version = "planning-state/v1"',
                "",
                "[todo]",
                'active_items = [{ id = "dogfood", surface = ".agentic-workspace/planning/execplans/dogfood.plan.json", next_action = "Continue decomposed work." }]',
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "dogfood.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Dogfood delegation opportunities",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Expose concrete delegation opportunities.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "validation-slice",
                        "title": "Validation slice",
                        "readiness": "ready",
                        "outcome": "Run and report focused validation.",
                        "owner_surface": ".agentic-workspace/planning/execplans/validation-slice.plan.json",
                        "proof": "Focused CLI tests pass.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused CLI tests pass."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue active decomposed docs validation work",
                "--format",
                "json",
            ]
        )
        == 0
    )

    decision = _start_context_value(json.loads(capsys.readouterr().out), "delegation_decision")
    decomposition = decision["decomposition_delegation"]
    assert decomposition["status"] == "present"
    assert decomposition["candidates"][0]["lane_id"] == "validation-slice"
    assert decomposition["candidates"][0]["route_candidate"] == "delegate-implementation"
    assert decision["delegation_candidates"][0]["owner_surface"].endswith("validation-slice.plan.json")
    audit = decision["auto_delegation_audit"]
    assert audit["status"] == "skipped"
    assert audit["must_report_if_not_run"] is True
    assert audit["skipped_targets"][0]["name"] == "mini"
    assert "safe_to_auto_run_commands" in audit["skipped_targets"][0]["reasons"][0]


def test_start_decomposition_only_delegation_requires_lane_promotion_before_handoff(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "dogfood.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Dogfood delegation opportunities",
                "status": "shaping",
                "larger_intended_outcome": "Expose concrete delegation opportunities.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "validation-slice",
                        "title": "Validation slice",
                        "readiness": "needs-shaping",
                        "outcome": "Run and report focused validation.",
                        "owner_surface": "",
                        "proof": "Focused CLI tests pass.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused CLI tests pass."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the decomposed epic with reusable worker delegation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    decision = _start_context_value(json.loads(capsys.readouterr().out), "delegation_decision")
    assert decision["decision"] == "suggest-delegation"
    assert decision["required_next_action"] == "select-or-promote-bounded-lane"
    assert decision["decomposition_delegation"]["status"] == "available-without-active-planning"
    assert "handoff_command" not in decision
    assert decision["delegation_next_step"]["status"] == "prepare-or-report"
    assert decision["delegation_next_step"]["command"] is None
    assert decision["delegation_next_step"]["handoff_contract_status"] == "unavailable-without-active-planning"
    assert "Select or promote" in decision["delegation_next_step"]["precondition"]


def test_start_exposes_decomposition_without_prompt_text_blocking(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "dogfood.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Dogfood planning safety",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Prevent broad work from bypassing planning.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "safety-slice",
                        "title": "Safety slice",
                        "readiness": "ready",
                        "outcome": "Implement the planning safety gate.",
                        "owner_surface": ".agentic-workspace/planning/execplans/safety-slice.plan.json",
                        "proof": "Focused workspace tests pass.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused workspace tests pass."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue the dogfooding epic safety-slice implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "planning_safety_gate" not in _start_context(payload).get("planning", {})
    assert _start_workflow_sufficiency(payload)["decision"] == "enough-for-first-contact-routing"
    assert _start_primary_action(payload)["action"] == "choose-smallest-workflow-shape"
    decision = _start_context_value(payload, "delegation_decision")
    assert decision["decomposition_delegation"]["status"] == "available-without-active-planning"


def test_implement_flags_scope_growth_without_active_execplan(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/memory/python/__init__.py",
                "src/agentic_workspace/contracts/command_package_ir.json",
                "generated/memory/python/cli.py",
                "tests/test_generated_command_package_proof_runner.py",
                "--task",
                "Small generated command cleanup",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "escalation-required"
    assert gate["changed_path_classification"]["dirty_shape"] == "implementation-only"
    assert "generated artifacts changed with source or tests" in gate["changed_path_classification"]["scope_growth_reasons"]
    assert _start_workflow_sufficiency(payload)["decision"] == "planning-escalation-required"
    assert payload["next"]["action"] == "Create or promote an active execplan before continuing implementation."


def test_implement_allows_routine_pr_comment_repair_without_plan_scaffold(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "tests/test_workspace_start_preflight_cli.py",
                ".agentic-workspace/memory/repo/current/routing-feedback.md",
                "--task",
                "Address PR #1057 review comment",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "clear"
    assert gate["decision"] == "direct-work-allowed"
    assert gate["implementation_allowed"] is True
    assert gate["repair_route"]["status"] == "retired"
    assert gate["work_shape_facts"]["hard_blockers"] == []
    assert gate["work_shape_facts"]["agent_decision_required"] is True
    assert gate["work_shape_facts"]["suggested_shape"] == "direct"
    assert gate["changed_path_classification"]["scope_growth_detected"] is False
    assert gate["changed_path_classification"]["ancillary_paths"] == [".agentic-workspace/memory/repo/current/routing-feedback.md"]
    assert _start_workflow_sufficiency(payload)["decision"] == "enough-for-bounded-implementation"
    assert payload["next"]["action"] != "Create or promote an active execplan before continuing implementation."


def test_implement_allows_single_issue_followthrough_with_memory_feedback_note(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "tests/test_workspace_start_preflight_cli.py",
                ".agentic-workspace/memory/repo/current/routing-feedback.md",
                "--task",
                "Do #1058 as well",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "clear"
    assert gate["decision"] == "direct-work-allowed"
    assert gate["implementation_allowed"] is True
    assert gate["repair_route"]["status"] == "retired"
    assert gate["work_shape_facts"]["hard_blockers"] == []
    assert gate["work_shape_facts"]["agent_decision_required"] is True
    assert gate["work_shape_facts"]["suggested_shape"] == "direct"
    assert gate["work_shape_facts"]["scope_factors"]["issue_refs"] == ["#1058"]
    assert gate["changed_path_classification"]["ancillary_paths"] == [".agentic-workspace/memory/repo/current/routing-feedback.md"]
    assert _start_workflow_sufficiency(payload)["decision"] == "enough-for-bounded-implementation"


def test_implement_distinguishes_planning_recovery_from_mixed_wip(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                "generated/workspace/python/cli.py",
                "--task",
                "Recover planning state while code is dirty",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "violation"
    assert gate["changed_path_classification"]["dirty_shape"] == "planning-plus-implementation"
    assert _start_workflow_sufficiency(payload)["decision"] == "implementation-owner-missing"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/recovery.plan.json",
                "--task",
                "Recover planning state",
                "--format",
                "json",
            ]
        )
        == 0
    )
    planning_only = _start_planning_safety_gate(json.loads(capsys.readouterr().out))
    assert planning_only["status"] == "clear"
    assert planning_only["changed_path_classification"]["dirty_shape"] == "planning-only"


def test_implement_does_not_require_active_plan_delegation_for_direct_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "mechanical-lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/mechanical-lane.plan.json", why_now = "prove delegation gate." },
]
queued_items = []
""",
    )
    _write(
        target / ".agentic-workspace/planning/execplans/mechanical-lane.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "mechanical-lane",
                "status": "in-progress",
                "post_decomposition_delegation": {"status": "pending"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--task",
                "Investigate how workflow obligations are currently enforced",
                "--format",
                "json",
            ]
        )
        == 0
    )

    startup = json.loads(capsys.readouterr().out)
    assert startup["next_safe_action"]["next_safe_action"] != "record-delegation-decision"
    assert _start_workflow_sufficiency(startup)["decision"] != "delegation-decision-required"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--task",
                "Investigate how workflow obligations are currently enforced",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["decision"] == "planning-backed"
    assert gate["delegation_decision_required"] is False
    assert gate["active_delegation_requirement"]["status"] == "delegation-decision-not-needed-for-direct-task"


def test_implement_requires_delegation_decision_for_active_decomposed_lane(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "mechanical-lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/mechanical-lane.plan.json", why_now = "prove delegation gate." },
]
queued_items = []
""",
    )
    plan_path = target / ".agentic-workspace/planning/execplans/mechanical-lane.plan.json"
    _write(
        plan_path,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "mechanical-lane",
                "status": "in-progress",
                "post_decomposition_delegation": {"status": "pending"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--task",
                "Continue the decomposed mechanical lane implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "blocked"
    assert gate["decision"] == "delegation-decision-required"
    assert "planning delegation-decision" in gate["delegation_decision_command"]
    assert _start_workflow_sufficiency(payload)["decision"] == "delegation-decision-required"

    _write(
        plan_path,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "mechanical-lane",
                "status": "in-progress",
                "post_decomposition_delegation": {
                    "status": "recorded",
                    "route chosen": "keep-local",
                    "decision command": "agentic-planning delegation-decision",
                    "recorded at": "2026-05-21T15:04:09+00:00",
                },
            }
        ),
    )
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--task",
                "Continue the decomposed mechanical lane implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )
    recorded = _start_planning_safety_gate(json.loads(capsys.readouterr().out))
    assert recorded["status"] == "satisfied"


def test_implement_rejects_hand_edited_active_plan_delegation_decision(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "mechanical-lane", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/mechanical-lane.plan.json", why_now = "prove delegation gate." },
]
queued_items = []
""",
    )
    _write(
        target / ".agentic-workspace/planning/execplans/mechanical-lane.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "mechanical-lane",
                "status": "in-progress",
                "post_decomposition_delegation": {"status": "recorded", "route chosen": "keep-local"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--task",
                "Continue the decomposed mechanical lane implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    gate = _start_planning_safety_gate(json.loads(capsys.readouterr().out))
    assert gate["status"] == "blocked"
    assert gate["decision"] == "delegation-decision-required"
    assert gate["active_delegation_requirement"]["status"] == "delegation-decision-untrusted-shared-state"


def test_implement_blocks_stale_parent_decomposition_for_active_epic_plan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "safety-slice", maturity = "active", status = "active", surface = ".agentic-workspace/planning/execplans/safety-slice.plan.json", why_now = "prove parent decomposition gate." },
]
queued_items = []
""",
    )
    _write(
        target / ".agentic-workspace/planning/execplans/safety-slice.plan.json",
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "id": "safety-slice",
                "status": "in-progress",
                "active_milestone": {"id": "safety-slice", "status": "in-progress"},
                "post_decomposition_delegation": {
                    "status": "recorded",
                    "route chosen": "keep-local",
                    "decision command": "agentic-planning delegation-decision",
                    "recorded at": "2026-05-21T15:04:09+00:00",
                },
            }
        ),
    )
    decomposition_path = target / ".agentic-workspace/planning/decompositions/dogfood.decomposition.json"
    _write(
        decomposition_path,
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Dogfood planning safety",
                "status": "ready-for-lane-promotion",
                "larger_intended_outcome": "Prevent stale epic decomposition from becoming invisible.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "safety-slice",
                        "title": "Safety slice",
                        "readiness": "ready",
                        "outcome": "Implement the planning safety gate.",
                        "owner_surface": ".agentic-workspace/planning/execplans/safety-slice.plan.json",
                        "proof": "Focused workspace tests pass.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused workspace tests pass."],
                "promotion_rule": "Promote ready lanes only.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Continue active epic-backed safety-slice implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = _start_planning_safety_gate(payload)
    assert gate["status"] == "blocked"
    assert gate["decision"] == "parent-decomposition-decision-required"
    assert gate["implementation_allowed"] is False
    assert gate["active_parent_decomposition_requirement"]["decomposition"].endswith("dogfood.decomposition.json")
    assert "skip decision" in " ".join(gate["active_parent_decomposition_requirement"]["required_before_implementation"])
    assert _start_workflow_sufficiency(payload)["decision"] == "parent-decomposition-decision-required"

    record = json.loads(decomposition_path.read_text(encoding="utf-8"))
    record["candidate_lanes"][0]["readiness"] = "promoted"
    _write(decomposition_path, json.dumps(record, indent=2))
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Continue active epic-backed safety-slice implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )
    resolved = _start_planning_safety_gate(json.loads(capsys.readouterr().out))
    assert resolved["status"] == "satisfied"
    assert resolved["active_parent_decomposition_requirement"]["status"] == "parent-decomposition-resolved"


def test_planning_archive_plan_front_door_forwards_plan_positionally() -> None:
    args = argparse.Namespace(
        planning_command="archive-plan",
        plan="plan-alpha",
        target=".",
        apply_cleanup=True,
        dry_run=True,
        format="json",
    )

    argv = cli._planning_module_argv(args)

    assert argv[:2] == ["archive-plan", "plan-alpha"]
    assert "--plan" not in argv
    assert "--apply-cleanup" in argv


def test_planning_delegation_decision_front_door_keeps_plan_option() -> None:
    args = argparse.Namespace(
        planning_command="delegation-decision",
        plan="plan-alpha",
        route="keep-local",
        skipped_reason="small coupled slice",
        target=".",
        dry_run=False,
        format="json",
    )

    argv = cli._planning_module_argv(args)

    assert argv[0] == "delegation-decision"
    assert argv[argv.index("--plan") + 1] == "plan-alpha"


def test_planning_closeout_front_door_forwards_plan_positionally() -> None:
    args = argparse.Namespace(
        planning_command="closeout",
        plan="plan-alpha",
        target=".",
        claim_level="lane",
        intent_status="partial",
        residue="planning",
        proof_from="last",
        residue_owner=".agentic-workspace/planning/state.toml",
        dry_run=True,
        discard_archive=False,
        format="json",
    )

    argv = cli._planning_module_argv(args)

    assert argv[:2] == ["closeout", "plan-alpha"]
    assert "--plan" not in argv
    assert argv[argv.index("--claim-level") + 1] == "lane"
    assert argv[argv.index("--intent-status") + 1] == "partial"
    assert argv[argv.index("--residue") + 1] == "planning"
    assert argv[argv.index("--residue-owner") + 1] == ".agentic-workspace/planning/state.toml"


def test_planning_close_item_front_door_forwards_item_positionally() -> None:
    args = argparse.Namespace(
        planning_command="close-item",
        item="done-item",
        reason="completed residue",
        issue="#953",
        target=".",
        dry_run=True,
        format="json",
    )

    argv = cli._planning_module_argv(args)

    assert argv[:2] == ["close-item", "done-item"]
    assert "--item" not in argv
    assert argv[argv.index("--reason") + 1] == "completed residue"
    assert argv[argv.index("--issue") + 1] == "#953"


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
    orientation = _start_context_value(payload, "vague_outcome_orientation")
    assert orientation["status"] == "applicable"
    assert "say you will proceed on that interpretation unless corrected" in orientation["answer_contract"]
    assert orientation["raw_read_rule"].startswith("Open raw .agentic-workspace files only after compact output")
    assert "skills" in payload


def test_start_task_surfaces_stated_assumption_middle_path(tmp_path: Path, capsys) -> None:
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
                "Improve onboarding so agents stop drifting from user intent",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    acknowledgement = _start_context_value(payload, "intent_acknowledgement")
    assert acknowledgement["decision"] == "proceed-with-stated-assumption"
    assert acknowledgement["fields"] == [
        "inferred_intent",
        "concrete_first_slice",
        "non_goals_or_deferred_scope",
        "correction_point",
    ]
    assert acknowledgement["proceed_unless_corrected"] is True
    assert acknowledgement["clarify_only_if_blocked"] is True


def test_start_direct_task_keeps_stated_assumption_out_of_default(tmp_path: Path, capsys) -> None:
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
                "Fix a typo in README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "intent_acknowledgement" not in payload


def test_startup_skillspec_pilot_keeps_direct_work_light_and_blocks_epic_work(tmp_path: Path, capsys) -> None:
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
                "Fix a typo in README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    direct = json.loads(capsys.readouterr().out)
    assert "planning_safety_gate" not in direct
    _assert_next_safe_action_valid(direct["next_safe_action"])
    assert direct["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert direct["next_safe_action"]["proof_required"] is False
    assert direct["next_safe_action"]["module_slot"] == "workspace"

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--task",
                "Decompose an epic into lanes before implementation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    epic = json.loads(capsys.readouterr().out)
    _assert_next_safe_action_valid(epic["next_safe_action"])
    assert "planning_safety_gate" not in _start_context(epic).get("planning", {})
    assert epic["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert _start_skill_routing(epic)["preferred_routes"][0]["skill"] == "planning-reporting"


def _fixture_by_id(fixture_id: str) -> dict[str, object]:
    fixtures = {fixture["id"]: fixture for fixture in skill_specs_manifest()["generated_target_behavior_fixtures"]}
    return fixtures[fixture_id]


def test_generated_target_behavior_fixtures_match_startup_cli_routing(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    direct_fixture = _fixture_by_id("direct-task-cheap-path")
    assert cli.main(["start", "--target", str(target), "--task", str(direct_fixture["task"]), "--format", "json"]) == 0
    direct = json.loads(capsys.readouterr().out)
    direct_packet = direct["next_safe_action"]
    _assert_next_safe_action_valid(direct_packet)

    assert direct_packet["implementation_allowed"] is direct_fixture["implementation_allowed"]
    assert direct_packet["proof_required"] is direct_fixture["proof_required"]
    assert direct_packet["completion_claim_allowed"] is direct_fixture["completion_claim_allowed"]
    assert "planning_safety_gate" not in direct

    lane_fixture = _fixture_by_id("lane-task-planning-gate")
    assert cli.main(["start", "--target", str(target), "--task", str(lane_fixture["task"]), "--format", "json"]) == 0
    lane = json.loads(capsys.readouterr().out)
    lane_packet = lane["next_safe_action"]
    _assert_next_safe_action_valid(lane_packet)

    assert lane_packet["implementation_allowed"] is direct_fixture["implementation_allowed"]
    assert lane_packet["proof_required"] is direct_fixture["proof_required"]
    assert lane_packet["completion_claim_allowed"] is direct_fixture["completion_claim_allowed"]
    assert lane_packet["required_skill"] == ""
    assert _start_skill_routing(lane)["preferred_routes"][0]["skill"] == "planning-reporting"
    for field in lane_fixture["expected_fields"]:
        if str(field).startswith("next_safe_action."):
            assert str(field).split(".", 1)[1] in lane_packet

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    assert cli.main(["skills", "--target", str(target), "--task", str(lane_fixture["task"]), "--format", "json"]) == 0
    recommendations = json.loads(capsys.readouterr().out)["recommendations"]
    assert recommendations[0]["id"] == lane_fixture["required_skill"]

    fallback_fixture = _fixture_by_id("no-cli-conservative-fallback")
    fallback_text = json.dumps(direct_packet, sort_keys=True)
    assert "fallback_if_cli_unavailable" in direct_packet
    assert "preserve forbidden actions" in fallback_text
    assert "fallback_when_cli_unavailable" in fallback_fixture["expected_fields"]
    assert any("WORKFLOW.md" in item for item in fallback_fixture["must_preserve"])


def test_start_does_not_promote_unrelated_roadmap_for_lifecycle_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        target / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "tier-3-memory-first", maturity = "candidate", status = "accepted", priority = "P1", refs = "GitHub #1", title = "Finish Memory first", outcome = "Continue the Memory roadmap.", reason = "Roadmap continuation exists.", promotion_signal = "Promote when roadmap work is requested.", suggested_first_slice = "Pick the next memory slice." },
]
""",
    )

    assert cli.main(["start", "--target", str(target), "--task", "Apply the memory lifecycle upgrade", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_next_safe_action_valid(payload["next_safe_action"])
    assert payload["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert "planning_safety_gate" not in payload["context"]["planning"]
    assert "tier-3-memory-first" not in payload["next_safe_action"].get("preferred_cli", "")


def test_start_routine_issue_intake_uses_skill_without_execplan(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(target), "--task", "Ingest and prioritize issues", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    _assert_next_safe_action_valid(payload["next_safe_action"])
    assert payload["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert "planning_safety_gate" not in payload["context"]["planning"]
    assert payload["skills"]["required"] == []
    assert payload["skills"]["recommended"] == []
    assert 'skills --target "' in payload["skills"]["catalog"]["command"]
    assert payload["skills"]["catalog"]["command"].endswith('--task "<task>" --format json')
    assert "task_recommendations" not in _start_skill_routing(payload)


def test_init_creates_managed_workspace_local_agent_instructions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    local_agents = target / ".agentic-workspace" / "AGENTS.md"
    text = local_agents.read_text(encoding="utf-8")
    assert ".agentic-workspace/AGENTS.md" in payload["created"]
    assert "Do not hand-edit structured state" in text
    assert "Use `agentic-workspace planning ...` and `agentic-workspace memory ...` commands" in text
    assert "route or file an improvement issue" in text

    assert cli.main(["doctor", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)
    assert doctor_payload["health"] == "healthy"
    assert ".agentic-workspace/AGENTS.md" not in doctor_payload["warnings"]


def test_init_uses_configured_workspace_local_agent_instructions_filename(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(
        target / ".agentic-workspace" / "config.toml",
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "GEMINI.md"\n',
    )

    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert ".agentic-workspace/GEMINI.md" in payload["created"]
    assert (target / ".agentic-workspace" / "GEMINI.md").is_file()
    assert (target / "GEMINI.md").is_file()
    assert "Do not hand-edit structured state" in (target / ".agentic-workspace" / "GEMINI.md").read_text(encoding="utf-8")


def test_doctor_offers_scoped_repair_for_missing_workspace_local_agent_instructions(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()
    local_agents = target / ".agentic-workspace" / "AGENTS.md"
    local_agents.unlink()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    doctor_payload = json.loads(capsys.readouterr().out)

    assert doctor_payload["health"] == "attention-needed"
    action = doctor_payload["repair_actions"][0]
    assert action["id"] == "apply-managed-local-instructions-repair"
    assert action["safe_to_apply"] is True
    assert action["affected_surfaces"] == [".agentic-workspace/AGENTS.md"]
    assert "--repair-managed-local-instructions" in action["command"]

    assert cli.main(["upgrade", "--target", str(target), "--repair-managed-local-instructions", "--format", "json"]) == 0
    repair_payload = json.loads(capsys.readouterr().out)

    assert repair_payload["repair_mode"] == "managed-local-instructions"
    assert repair_payload["created"] == [".agentic-workspace/AGENTS.md"]
    assert repair_payload["repair_scope"]["affected_surfaces"] == [".agentic-workspace/AGENTS.md"]
    assert "Do not hand-edit structured state" in local_agents.read_text(encoding="utf-8")


def test_start_narrow_ci_repair_stays_direct_without_execplan(tmp_path: Path, capsys) -> None:
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
                "Fix CI checks for a narrow schema-reference docs repair",
                "--changed",
                "src/agentic_workspace/contracts/schemas/operation_primitives.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    _assert_next_safe_action_valid(payload["next_safe_action"])
    assert "planning_safety_gate" not in payload["context"]["planning"]
    assert payload["next_safe_action"]["next_safe_action"] == "select-changed-path-proof"
    profile = payload["context"].get("repair_plan_profile") or payload.get("repair_plan_profile")
    assert profile["status"] == "direct-no-plan"
    assert profile["required_record"]["continuation_owner"] == "PR/CI result"


def test_start_task_keeps_skill_search_explicit(tmp_path: Path, capsys) -> None:
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
    assert payload["skills"]["status"] == "available"
    assert payload["skills"]["required"] == []
    assert payload["skills"]["recommended"] == []
    assert payload["skills"]["catalog"]["total_count"] > 0
    assert "skills --target" in payload["skills"]["catalog"]["command"]
    assert "task_recommendations" not in _start_skill_routing(payload)


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
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    skill_routing = payload["startup_guidance"]["skill_routing"]
    assert "task_recommendations" not in skill_routing
    assert "skills --target" in skill_routing["query"]
    assert "task_recommendations" not in skill_routing


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
    assert payload["memory_consult"]["consultation_state"] == "checked-with-matches"


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
    assert memory_consult["capture_helper"].startswith("uv run agentic-workspace memory capture-note")
    assert memory_consult["promotion_pressure"]["command"].startswith("uv run agentic-workspace memory promotion-report")


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


def test_start_surfaces_preserved_agentic_workspace_absence_instructions(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "AGENTS.md",
        "# Agent Instructions\n\nThis repository does not use Agentic Workspace. Work from ordinary files.\n",
    )

    assert cli.main(["init", "--target", str(tmp_path), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Orient and fix README", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    startup_review = _start_context_value(payload, "startup_review")
    assert startup_review["status"] == "attention"
    assert startup_review["items"][0]["path"] == "AGENTS.md"
    assert "claim Agentic Workspace is absent" in startup_review["items"][0]["issue"]
    assert "reconcile stale no-workspace wording" in startup_review["items"][0]["action"]


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
    assert cli.main(["defaults", "--verbose", "--section", "startup", "--format", "json"]) == 0
    defaults_output = capsys.readouterr().out
    defaults_payload = json.loads(defaults_output)

    startup_answer = defaults_payload.get("answer", {})
    assert startup_answer.get("default_canonical_agent_instructions_file") == "AGENTS.md"

    # Verify the entry and follow-up compact queries use agentic-workspace (not stale bootstrap)
    tiny_safe = startup_answer.get("tiny_safe_model", {})
    assert tiny_safe.get("entrypoint") == "AGENTS.md"
    assert tiny_safe.get("entry_query") == 'agentic-workspace start --task "<task>" --format json'
    queries = tiny_safe.get("first_compact_queries", [])
    assert not any("agentic-workspace preflight --format json" in q for q in queries)
    assert any("agentic-workspace start --target ./repo" in q for q in queries)
    assert any("agentic-workspace config --target" in q for q in queries)
    assert any("agentic-workspace summary" in q for q in queries)
    # Ensure NO stale bootstrap references in startup queries (most critical part)
    assert not any("agentic-planning summary" in q for q in queries)

    # Step 2: preflight should provide the bundled compact takeover context
    assert cli.main(["preflight", "--target", str(target), "--verbose", "--format", "json"]) == 0
    preflight_output = capsys.readouterr().out
    preflight_payload = json.loads(preflight_output)
    assert preflight_payload.get("kind") == "preflight-response/v1"
    assert "startup_guidance" in preflight_payload
    assert preflight_payload["startup_guidance"]["entry_query"] == 'agentic-workspace start --task "<task>" --format json'
    assert "agentic-workspace preflight --format json" not in preflight_payload["startup_guidance"]["first_compact_queries"]
    assert preflight_payload["startup_guidance"]["escalation_rules"][0]["load_next"][0].startswith("agentic-workspace ")
    assert "resolved_config" in preflight_payload
    assert "active_planning_state" in preflight_payload

    # Step 3: config command should work and be reasonably compact
    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0
    config_output = capsys.readouterr().out
    config_payload = json.loads(config_output)
    assert config_payload["kind"] == "agentic-workspace/config-tiny/v1"
    assert "workspace" in config_payload
    assert "next_detail" in config_payload

    # Step 4: summary command should work
    assert cli.main(["summary", "--format", "json"]) == 0
    summary_output = capsys.readouterr().out
    summary_payload = json.loads(summary_output)
    assert summary_payload.get("kind") == "planning-summary/v1"
    assert summary_payload.get("profile") == "tiny"

    # Step 5: report command should work (though larger output)
    assert cli.main(["report", "--target", str(target), "--verbose", "--format", "json"]) == 0
    report_output = capsys.readouterr().out
    # Don't parse full report, just verify it produces output
    assert report_output  # Report should produce output
