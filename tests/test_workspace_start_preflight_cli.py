from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


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
    assert cli.main(["preflight", "--profile", "full", "--format", "json"]) == 0

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


def test_preflight_default_returns_tiny_takeover_router(capsys) -> None:
    assert cli.main(["preflight", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "preflight-response/v1"
    assert payload["mode"] == "tiny-takeover-router"
    assert "active_state_summary" in payload
    assert "startup_guidance" not in payload
    assert payload["immediate_next_allowed_action"]["action"] == "recover-orientation"
    assert payload["detail_commands"]["full_takeover"].endswith("preflight --target . --profile full --format json")


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
                "--profile",
                "full",
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

    assert cli.main(["preflight", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

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
                "--profile",
                "full",
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

    assert cli.main(["preflight", "--target", str(target), "--profile", "full", "--format", "json"]) == 0

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

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(target),
                "--changed",
                "src/agentic_workspace/cli.py",
                "--profile",
                "full",
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
    assert len(json.dumps(payload, sort_keys=True)) < 16600
    assert payload["proof"]["required_commands"] == [
        "make test-workspace",
        "make lint-workspace",
        "uv run agentic-workspace defaults --section root_cli_authority --format json",
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
    assert len(encoded) < 7800
    assert payload["kind"] == "startup-context/v1"
    adaptive = payload["adaptive_routing"]
    assert adaptive["current_need"] in {"first-contact-routing", "continue-active-planning"}
    assert adaptive["read_budget"]["profile"] == "tiny"
    assert adaptive["read_budget"]["raw_file_reads"].startswith("only after")
    assert "task_scoped_state" in adaptive["detail_commands"]
    assert "raw planning files" in adaptive["not_needed_now"]
    assert payload["cli_invocation"]["primary"].endswith("agentic-workspace")
    assert "config.local.toml" in payload["cli_invocation"]["fallback_when_unavailable"]
    assert "stale installed selector" in payload["cli_invocation"]["stale_bare_command_warning"]
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
        == "Use task_intent.implement_changed_command after changed paths are known."
    )
    assert payload["context_router"]["detail_commands"]["takeover_or_recovery"] == "agentic-workspace preflight --format json"
    assert payload["active_state_summary"]["todo_active_count"] >= 0
    assert payload["immediate_next_allowed_action"]["action"] in {"choose-smallest-workflow-shape", "continue-active-planning-record"}
    assert "implement --profile tiny --changed <paths>" in payload["task_intent"]["implement_changed_command"]
    assert payload["skill_routing"]["query"] == 'uv run agentic-workspace skills --target ./repo --task "<task>" --format json'
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"]["mode"] in {"suggest", "auto"}
    assert payload["delegation_decision"]["required_next_action"] in {
        "continue-local",
        "mention-suggestion",
        "prepare-handoff",
        "execute-when-safe",
        "stop-and-ask-human",
    }
    assert payload["task_intent"]["status"] == "present"
    assert payload["task_intent"]["implement_changed_command"] == (
        f'uv run agentic-workspace implement --profile tiny --changed <paths> --task "{task}" --format json'
    )
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert "cli_compatibility" not in payload
    assert "proof" not in payload
    assert len(payload["authority_markers"]) == 1


def test_start_tiny_keeps_moderate_task_carry_forward_command_executable(capsys) -> None:
    task = (
        "Add robust CSV row importing to this Python package. Implement import_rows_from_csv(text, *, "
        "required_fields=None, delimiter=',') in sample_app, exporting it from sample_app.__init__. "
        "It should parse CSV text with the standard library, normalize headers, validate row data, "
        "accumulate row-level errors instead of raising for bad rows, add focused pytest coverage, "
        "update README with a concise usage example, and run the relevant tests."
    )

    assert cli.main(["start", "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    command = payload["task_intent"]["implement_changed_command"]
    assert payload["task_intent"]["task_argument_mode"] == "inline"
    assert "--task-file" not in command
    assert f'--task "{task}"' in command


def test_start_tiny_routes_existing_task_paths_to_implement_surface(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "fixture\n")

    task = "Prepare for a narrow README.md wording edit, but do not edit files yet."
    assert cli.main(["start", "--target", str(tmp_path), "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = payload["immediate_next_allowed_action"]
    assert action["action"] == "inspect-known-task-paths"
    assert action["detected_paths"] == ["README.md"]
    assert action["command"] == (
        'agentic-workspace implement --profile tiny --changed README.md --task "Prepare for a narrow README.md wording edit, but do not edit files yet." --format json'
    )
    assert action["read_first"] == [action["command"]]


def test_start_tiny_routes_config_posture_questions_to_tiny_config(capsys) -> None:
    task = (
        "Inspect this repo enough to answer how a small follow-up should be reported. "
        "Keep the answer aligned with the repo's configured operating and reporting posture."
    )

    assert cli.main(["start", "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = payload["immediate_next_allowed_action"]
    assert action["action"] == "inspect-effective-config"
    assert action["command"] == "uv run agentic-workspace config --profile tiny --format json"
    assert action["read_first"] == [action["command"]]
    assert "tiny config surface" in action["summary"]
    assert len(json.dumps(payload, sort_keys=True)) < 8100


def test_start_tiny_compacts_long_task_carry_forward_command(capsys) -> None:
    task = " ".join(
        [
            "Implement a deliberately long follow-up request that asks the agent to preserve acceptance reconciliation, "
            "avoid repeating large prompts in every generated command, keep objective-drift checks connected to the original "
            "task intent, and make the next command compact enough for weak model startup surfaces.",
            "Also ensure closeout still maps requested outcomes to proof and delivered files.",
        ]
        * 5
    )

    assert cli.main(["start", "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    command = payload["task_intent"]["implement_changed_command"]
    assert payload["task_intent"]["task_argument_mode"] == "task-file"
    assert "--task-file .agentic-workspace/local/scratch/task-intent.txt" in command
    assert "--task " not in command
    assert task not in command
    assert payload["task_intent"]["task_file"] == ".agentic-workspace/local/scratch/task-intent.txt"
    assert "Write the original request once" in payload["task_intent"]["task_file_instruction"]
    assert len(payload["task_intent"]["task_digest"]) == 16
    assert payload["task_intent"]["task_text_length"] == len(task)
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
    assert cli.main(["start", "--target", str(target), "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = payload["immediate_next_allowed_action"]
    assert action["action"] == "create-prep-only-planning-state"
    assert action["command"].startswith("agentic-planning new-plan")
    assert "--prep-only" in action["command"]
    assert action["next_proof"] == "agentic-workspace summary --profile compact --format json"
    assert action["read_first"] == []
    assert "do not create product source" in action["summary"]
    prep_only = payload["prep_only_handoff"]
    assert prep_only["first_command"].startswith("agentic-planning new-plan")
    assert prep_only["reference_command"] == "agentic-workspace planning --format json"
    assert "--prep-only" in prep_only["preferred_mutation_command_template"]
    assert prep_only["after_write"] == "agentic-workspace summary --profile compact --format json"
    assert prep_only["stop_after_summary"] is True
    assert "no" in prep_only["open_execplan_after_creation"]
    assert "defer unless summary reports" in prep_only["manual_execplan_tightening"]
    assert any("smallest schema-preserving" in item for item in prep_only["allowed_after_new_plan"])
    assert ".agentic-workspace/planning/execplans/" in prep_only["allowed_write_scope"]
    assert "tests or fixtures" in prep_only["forbidden_until_implementation_requested"]
    assert "manual JSON polishing or ad hoc validation loops" in prep_only["forbidden_until_implementation_requested"]
    assert len(json.dumps(payload, sort_keys=True)) < 8600


def test_start_tiny_routes_paraphrased_prep_only_handoff_to_planning_bridge(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare repository state for future CSV row import feature without implementing it"
    assert cli.main(["start", "--target", str(target), "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["immediate_next_allowed_action"]["action"] == "create-prep-only-planning-state"
    assert payload["prep_only_handoff"]["status"] == "required"


def test_start_tiny_routes_groundwork_without_implementation_to_prep_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare groundwork for CSV row import support without implementing feature"
    assert cli.main(["start", "--target", str(target), "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = payload["immediate_next_allowed_action"]
    assert action["action"] == "create-prep-only-planning-state"
    assert action["command"].startswith("agentic-planning new-plan")
    assert action["read_first"] == []


def test_start_tiny_routes_durable_plan_state_without_code_to_prep_only(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "full", "--format", "json"]) == 0
    capsys.readouterr()

    task = "Prepare durable implementation plan/state for CSV row import feature with no code changes yet"
    assert cli.main(["start", "--target", str(target), "--profile", "tiny", "--task", task, "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    action = payload["immediate_next_allowed_action"]
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

    assert cli.main(["start", "--target", str(tmp_path), "--profile", "tiny", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    decision = payload["delegation_decision"]
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
                "--profile",
                "tiny",
                "--task",
                "redesign workflow delegation policy",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    config_effect = payload["delegation_decision"]["config_effect"]
    assert config_effect["authority"] == "local-config"
    assert config_effect["source_path"] == ".agentic-workspace/config.local.toml"
    assert config_effect["configured_delegation_mode"] == "auto"
    assert config_effect["delegation_mode"] == "suggest"
    assert config_effect["safe_to_auto_run_commands"] is False
    assert "safe_to_auto_run_commands" in config_effect["disabled_reason"]


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
                "--profile",
                "tiny",
                "--task",
                "Can this request be automatically delegated to a cheaper executor under local settings?",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = payload["delegation_decision"]
    assert decision["decision"] == "stay-local"
    assert decision["config_effect"]["delegation_mode"] == "suggest"
    assert decision["config_effect"]["safe_to_auto_run_commands"] is False


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
                "--profile",
                "full",
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

    assert cli.main(["start", "--target", str(tmp_path), "--profile", "tiny", "--task", "Orient and fix README", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["startup_review"]["status"] == "attention"
    assert payload["startup_review"]["items"][0]["path"] == "AGENTS.md"
    assert "claim Agentic Workspace is absent" in payload["startup_review"]["items"][0]["issue"]
    assert "reconcile stale no-workspace wording" in payload["startup_review"]["items"][0]["action"]


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
    assert cli.main(["defaults", "--profile", "full", "--section", "startup", "--format", "json"]) == 0
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
    assert cli.main(["preflight", "--target", str(target), "--profile", "full", "--format", "json"]) == 0
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
    assert cli.main(["report", "--target", str(target), "--profile", "full", "--format", "json"]) == 0
    report_output = capsys.readouterr().out
    # Don't parse full report, just verify it produces output
    assert report_output  # Report should produce output
