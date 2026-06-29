from __future__ import annotations

# ruff: noqa: F403,F405
import copy
import hashlib
import re
from datetime import date

from tests.workspace_cli_support import *


def test_json_payload_budget_failure_reports_largest_contributors() -> None:
    payload = {
        "small": "ok",
        "context": {
            "large": "x" * 80,
            "nested": {"medium": "y" * 40},
        },
        "items": [{"detail": "z" * 30}],
    }

    with pytest.raises(AssertionError) as excinfo:
        _assert_json_payload_under(payload, 50, label="example tiny payload")

    message = str(excinfo.value)
    assert "example tiny payload JSON payload is" in message
    assert "Largest JSON contributors:" in message
    assert "context" in message
    assert "context.large" in message


def test_repeated_module_flags_accumulate_module_selection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--modules", "memory", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["planning", "memory"]


def test_repeated_singular_module_alias_accumulates_module_selection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--module", "memory", "--module", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["planning", "memory"]


def test_lifecycle_guidance_uses_canonical_modules_option(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--modules", "planning,memory", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    command_text = json.dumps(payload["lifecycle_plan"])
    assert "--modules planning,memory" in command_text
    assert "--module planning --module memory" not in command_text


def test_start_context_adapter_routes_through_startup_owner_facade() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    start_command = (repo_root / "generated" / "workspace" / "python" / "commands" / "start_context.py").read_text(encoding="utf-8")
    startup_facade = (repo_root / "generated" / "workspace" / "python" / "primitives" / "workspace_startup_runtime.py").read_text(
        encoding="utf-8"
    )

    assert "from ..primitives.workspace_startup_runtime import _run_start_context_adapter" in start_command
    assert "from agentic_workspace.workspace_runtime_startup import _run_start_context_adapter" in startup_facade
    assert workspace_runtime_primitives._run_start_context_adapter is workspace_runtime_startup._run_start_context_adapter


def test_active_planning_record_helpers_route_through_planning_owner(tmp_path: Path) -> None:
    assert workspace_runtime_primitives._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_primitives._raw_active_planning_record_for_closeout is (
        workspace_runtime_planning._raw_active_planning_record_for_closeout
    )
    assert workspace_runtime_startup._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_implement._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_proof._active_planning_record_for_report_section is (
        workspace_runtime_planning._active_planning_record_for_report_section
    )
    assert workspace_runtime_core._active_planning_record_for_report_section(target_root=tmp_path) == {}


def test_reconcile_report_adapter_routes_through_planning_owner() -> None:
    assert workspace_runtime_primitives._run_reconcile_report_adapter is workspace_runtime_planning._run_reconcile_report_adapter
    assert workspace_runtime_core._run_reconcile_report_adapter.__module__ == "agentic_workspace.workspace_runtime_core"


def test_upgrade_preserves_host_owned_ownership_subsystems(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    ownership_path = target / ".agentic-workspace" / "OWNERSHIP.toml"
    ownership_path.write_text(
        ownership_path.read_text(encoding="utf-8").rstrip() + '\n\n[[subsystems]]\nid = "api"\npaths = ["api/**"]\nowns = ["host api"]\n',
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--target", str(target), "--modules", "planning,memory", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    ownership_text = ownership_path.read_text(encoding="utf-8")
    assert 'id = "api"' in ownership_text
    assert 'paths = ["api/**"]' in ownership_text
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    ownership_action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/OWNERSHIP.toml")
    assert "host-owned subsystem overlay" in ownership_action["detail"]


def test_upgrade_refreshes_module_upgrade_source_recorded_at(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    source_path = target / ".agentic-workspace" / "planning" / "UPGRADE-SOURCE.toml"
    source_path.write_text(
        re.sub(r'recorded_at = "[^"]+"', 'recorded_at = "2025-01-01"', source_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert f'recorded_at = "{date.today().isoformat()}"' in source_path.read_text(encoding="utf-8")
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    action = next(action for action in workspace_report["actions"] if action["path"] == ".agentic-workspace/planning/UPGRADE-SOURCE.toml")
    assert "recorded_at after successful upgrade" in action["detail"]


def test_verbose_aliases_full_diagnostic_output_for_major_workspace_commands(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("# Fixture\n", encoding="utf-8")

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    cases = [
        (["defaults", "--verbose", "--format", "json"], lambda payload: "startup" in payload),
        (["modules", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: "terminology" in payload),
        (["summary", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["profile"] == "full"),
        (["report", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["kind"] == "workspace-report/v1"),
        (["config", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["target"] == tmp_path.as_posix()),
        (
            ["preflight", "--target", str(tmp_path), "--verbose", "--format", "json"],
            lambda payload: payload["mode"] == "full-takeover-context",
        ),
        (["proof", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: "default_routes" in payload),
        (
            ["implement", "--target", str(tmp_path), "--verbose", "--changed", "README.md", "--format", "json"],
            lambda payload: payload["kind"] == "implementer-context/v1",
        ),
        (["status", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["health"] == "healthy"),
        (["doctor", "--target", str(tmp_path), "--verbose", "--format", "json"], lambda payload: payload["health"] == "healthy"),
    ]

    for argv, assertion in cases:
        assert cli.main(argv) == 0
        payload = json.loads(capsys.readouterr().out)
        assert assertion(payload), argv


def test_defaults_text_uses_tiny_router_payload(capsys) -> None:
    assert cli.main(["defaults"]) == 0

    output = capsys.readouterr().out
    assert "Default-route contract sections are available on demand" in output
    assert "Common sections:" in output
    assert "- startup" in output
    assert "agentic-workspace defaults --verbose --format json" in output
    repo_root = Path(__file__).resolve().parents[1]
    view_contract = json.loads((repo_root / "src/agentic_workspace/contracts/workspace_output_views.json").read_text(encoding="utf-8"))
    assert any(view["id"] == "defaults-router.text" for view in view_contract["views"])


def test_planning_front_door_forwards_lane_lifecycle_positionals(monkeypatch, tmp_path: Path, capsys) -> None:
    forwarded: list[list[str]] = []

    def fake_planning_main(argv: list[str]) -> int:
        forwarded.append(argv)
        print(json.dumps({"argv": argv}))
        return 0

    def option_value(argv: list[str], option: str) -> str:
        return argv[argv.index(option) + 1]

    monkeypatch.setattr("repo_planning_bootstrap.cli.main", fake_planning_main)

    assert (
        cli.main(
            [
                "planning",
                "lane-activate",
                "lane-alpha",
                "--current-slice",
                "slice-one",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["argv"] == [
        "lane-activate",
        "lane-alpha",
        "--target",
        str(tmp_path),
        "--current-slice",
        "slice-one",
        "--format",
        "json",
    ]

    assert cli.main(["planning", "lane-close", "lane-alpha", "--proof", "proof passed", "--format", "json"]) == 0
    forwarded_close = json.loads(capsys.readouterr().out)["argv"]
    assert forwarded_close[:2] == ["lane-close", "lane-alpha"]
    assert option_value(forwarded_close, "--proof") == "proof passed"
    assert option_value(forwarded_close, "--format") == "json"

    assert cli.main(["planning", "lane-archive", "lane-alpha", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["argv"] == ["lane-archive", "lane-alpha", "--format", "json"]


def test_summary_and_config_support_exact_field_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "target_root,todo.active_count", "--format", "json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["kind"] == "agentic-workspace/selected-output/v1"
    assert summary["source_command"] == "summary"
    assert summary["selection_cost"]["profile_loaded"] == "tiny"
    assert summary["selection_cost"]["fallback_profile_loaded"] is False
    assert Path(summary["values"]["target_root"]) == tmp_path
    assert summary["values"]["todo.active_count"] == 0
    assert "missing" not in summary

    assert cli.main(["summary", "--target", str(tmp_path), "--select", "planning_record", "--format", "json"]) == 0
    summary_full_field = json.loads(capsys.readouterr().out)
    assert summary_full_field["selection_cost"]["profile_loaded"] == "full"
    assert summary_full_field["selection_cost"]["fallback_profile_loaded"] is True
    assert "planning_record" in summary_full_field["values"]

    assert (
        cli.main(
            [
                "config",
                "--target",
                str(tmp_path),
                "--select",
                "workspace.enabled_modules,mixed_agent.runtime_resolution",
                "--format",
                "json",
            ]
        )
        == 0
    )
    config = json.loads(capsys.readouterr().out)
    assert config["kind"] == "agentic-workspace/selected-output/v1"
    assert config["source_command"] == "config"
    assert config["values"]["workspace.enabled_modules"] == ["planning", "memory"]
    assert "recommendation" in config["values"]["mixed_agent.runtime_resolution"]
    assert "missing" not in config


def test_summary_fresh_session_digest_is_selector_backed(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#1680",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "[Workspace]: Reduce AW-induced completion cost",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1680 lane",
                "--changed",
                "docs/reviews/example.md",
                "--select",
                "fresh_session_digest",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    digest = payload["values"]["fresh_session_digest"]

    assert payload["selection_cost"]["profile_loaded"] == "tiny"
    assert digest["kind"] == "agentic-workspace/fresh-session-digest/v1"
    assert digest["issue_refs"] == ["#1680"]
    assert digest["issue_evidence"]["status"] == "available"
    assert digest["issue_evidence"]["items"][0]["title"] == "[Workspace]: Reduce AW-induced completion cost"
    assert digest["changed_paths"] == ["docs/reviews/example.md"]
    assert digest["source_artifacts"] == [
        ".agentic-workspace/local/cache/external-intent-evidence.json",
        "docs/reviews/example.md",
        "GitHub issue refs listed in issue_refs",
    ]
    assert digest["closure_boundary"]["may_claim_parent_closure"] is False
    assert "cannot close issues" in digest["closure_boundary"]["rule"]
    assert digest["safe_next_command"].endswith('start --target . --task "<next task>" --format json')
    assert "refresh_issue_evidence" in digest["detail_commands"]


def test_summary_fresh_session_digest_omits_unrelated_lane_artifacts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#42",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "Unrelated docs task",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #42 docs lane",
                "--changed",
                "docs/notes/unrelated.md",
                "--select",
                "fresh_session_digest",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload_text = capsys.readouterr().out
    digest = json.loads(payload_text)["values"]["fresh_session_digest"]

    assert digest["issue_refs"] == ["#42"]
    assert digest["source_artifacts"] == [
        ".agentic-workspace/local/cache/external-intent-evidence.json",
        "docs/notes/unrelated.md",
        "GitHub issue refs listed in issue_refs",
    ]
    assert "#1680" not in payload_text
    assert "aw-completion-cost-session-log-analysis-2026-06-23.md" not in payload_text


def test_start_exposes_workflow_sufficiency_and_continuation_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--select",
                "workflow_sufficiency,continuation_state",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["values"]["workflow_sufficiency"]["kind"] == "agentic-workspace/workflow-sufficiency/v1"
    assert payload["values"]["workflow_sufficiency"]["sufficiency_result"] == "enough-for-first-contact-routing"
    assert payload["values"]["workflow_sufficiency"]["nothing_more_needed"] is True
    continuation = payload["values"]["continuation_state"]
    assert continuation["kind"] == "agentic-workspace/compact-continuation-state/v1"
    assert continuation["fields"] == [
        "goal",
        "current_branch_or_state",
        "files_touched",
        "known_failing_tests",
        "next_intended_step",
        "open_questions",
    ]


def test_start_default_routes_memory_and_installed_state_detail_behind_selectors(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "memory_decision_packet" not in payload
    assert "installed_state_compatibility" not in payload
    assert "memory_decision_packet" in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "memory_decision_packet" in payload["drill_down"]["available_selectors"]
    assert payload["context"]["memory"]["status"] in {"recommended", "not_checked"}


def test_start_surfaces_configured_pre_test_guardrail_without_universal_bug_keyword(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.requirements.test_evidence_change_decision]
level = "high"
applies_to_paths = ["tests/**"]
applies_to_task_markers = ["regression test"]
required_evidence = ["verification_proof_decision_review"]
proof_profile = "test_evidence_change"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix the runtime issue by adding a regression test",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    guardrail = payload["context"]["pre_test_evidence_guardrail"]
    assert guardrail["status"] == "advisory"
    assert guardrail["blocking"] is False
    assert guardrail["source_boundary"]["no_universal_task_keyword_policy"] is True
    assert any("task marker matched regression test" in source for source in guardrail["trigger_sources"])
    assert "package-local-behavior" in guardrail["evidence_owner_options"]
    assert "convert-to-conformance" in guardrail["proof_decision_options"]
    assert any("trust question" in question for question in guardrail["pre_test_decision_questions"])
    assert "pre_test_evidence_guardrail" in payload["action_signals"]["advisory_detail"]["selectors"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix a bug in the README",
                "--format",
                "json",
            ]
        )
        == 0
    )
    quiet_payload = json.loads(capsys.readouterr().out)
    assert "pre_test_evidence_guardrail" not in quiet_payload["context"]
    assert "pre_test_evidence_guardrail" not in quiet_payload["action_signals"]["advisory_detail"]["selectors"]


def test_start_default_compacts_noncompatible_installed_state_signal(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_compatibility" not in payload
    assert "installed_state_compatibility=payload-upgrade-required" in payload["action_signals"]["changed_signals"]
    assert "installed_state_compatibility" in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "installed_state_compatibility" in payload["drill_down"]["available_selectors"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    full = selected["values"]["installed_state_compatibility"]
    assert full["status"] == "payload-upgrade-required"
    assert full["payload"]["provenance"]["status"] == "invalid"
    assert full["action_effect"]["force"] == "required_before_claim"
    assert full["action_effect"]["allowed_now"] == "continue-bounded-work-with-repo-local-invocation"
    assert full["action_effect"]["blocked_until_reconciled"] == [
        "claim-installed-state-fresh",
        "claim-payload-synced",
        "claim-generated-surfaces-current",
    ]
    assert full["action_effect"]["resolution_selector"] == "installed_state_compatibility"
    assert "agentic-workspace upgrade" in full["action_effect"]["resolution_command"]
    assert full["adapter_contracts"]


def test_payload_provenance_payload_uses_portable_path_identities(tmp_path: Path) -> None:
    payload = cli._payload_provenance_payload(target_root=tmp_path)
    encoded = json.dumps(payload, sort_keys=True)

    assert not re.search(r"[A-Za-z]:/|/(?:Users|home|tmp)/", encoded)
    assert payload["installed_by"]["module_path"]
    assert payload["installed_by"]["python_executable"]
    assert payload["command_generation"]["source_identity"]


def test_start_select_installed_state_blocking_drift_blocks_execution(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "blocking"\nexact_version = "999.0.0"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "blocking-drift"
    assert compatibility["executable"]["classification"] == "executable-too-old-or-wrong-version"
    assert compatibility["action_effect"]["force"] == "required_before_execution"
    assert compatibility["action_effect"]["allowed_now"] == "switch-to-compatible-invocation-before-running-workspace-actions"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == [
        "run-workspace-action",
        "claim-installed-state-compatible",
    ]
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "do-not-trust-workspace-action-output-until-the-effective-cli-invocation-is-compatible"
    )


def test_start_select_installed_state_advisory_drift_limits_currentness_claims(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (workspace / "config.toml").write_text(
        'schema_version = 1\n\n[cli_compatibility]\nenforcement = "advisory"\nexact_version = "999.0.0"\n',
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    compatibility = json.loads(capsys.readouterr().out)["values"]["installed_state_compatibility"]

    assert compatibility["status"] == "upgrade-recommended"
    assert compatibility["action_effect"]["force"] == "advisory"
    assert compatibility["action_effect"]["allowed_now"] == "continue-bounded-work-with-compatible-claim-limits"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == [
        "claim-installed-state-current",
        "claim-cli-fully-current",
    ]
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "advisory-cli-drift-does-not-block-ordinary-work-but-limits-strong-compatibility-claims"
    )


def test_start_default_stays_under_tiny_output_budget_for_docs_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Fix one docs typo",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start tiny docs-task payload", sort_keys=False)
    assert payload["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert "memory_decision_packet" not in payload
    assert "installed_state_compatibility" not in payload
    assert "planning_safety_gate" not in payload
    assert "memory_decision_packet" in payload["drill_down"]["available_selectors"]
    assert "routine_work_context" in payload["drill_down"]["available_selectors"]
    assert "workflow_sufficiency" in payload["drill_down"]["available_selectors"]
    assert payload["workflow_participation"]["status"] == "mandatory"
    assert "implementation_allowed cannot bypass workflow" in payload["workflow_participation"]["rule"]


def test_start_routes_high_assurance_milestone_to_planning_before_implementation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement an entire high-assurance milestone",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["workflow_participation"]["status"] == "mandatory"
    assert payload["next_safe_action"]["next_safe_action"] == "create-or-promote-active-execplan"
    assert payload["next_safe_action"]["implementation_allowed"] is False
    assert "continue implementation without active planning ownership" in payload["next_safe_action"]["forbidden_actions"]
    assert payload["action_signals"]["allowed_next_action"] == "create-or-promote-active-execplan"
    assert payload["context"]["planning"]["workflow_sufficiency"]["sufficiency_result"] == "planning-escalation-required"


def test_start_low_risk_docs_task_keeps_checkpoint_detail_selector_only(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1700 checkpoint slice",
                "--issue",
                "#1700",
                "--durable-source",
                "docs/reference/local-chat-checkpoints.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start tiny docs-task payload with checkpoint", sort_keys=False)
    assert "local_chat_checkpoint" not in payload["context"]
    assert "local_chat_checkpoint=present" not in payload["action_signals"]["changed_signals"]
    assert "local_chat_checkpoint" not in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "local_chat_checkpoint" in payload["drill_down"]["available_selectors"]

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume checkpoint slice", "--format", "json"]) == 0
    resume_payload = json.loads(capsys.readouterr().out)
    assert resume_payload["context"]["local_chat_checkpoint"]["status"] == "present"


def test_selector_first_output_policy_note_documents_visibility_tiers() -> None:
    note = Path("docs/reviews/selector-first-output-policy-2026-06-28.md").read_text(encoding="utf-8")
    assert "Always First Packet" in note
    assert "Selector-Only by Default" in note
    assert "Escalates Into First Packet" in note
    assert "local_chat_checkpoint" in note
    assert "dogfooding_signal_status" in note
    assert "pr_comment_attention" in note


def test_start_keeps_planned_and_release_closeout_signals_visible(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue planned lane in stacked PR sequence",
                "--format",
                "json",
            ]
        )
        == 0
    )
    planned = json.loads(capsys.readouterr().out)
    assert planned["context"]["dogfooding_signal_status"]["status"] == "not_checked"
    assert "dogfooding_signal_status=not_checked" in planned["action_signals"]["changed_signals"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Diagnose release recovery after failed semver release",
                "--format",
                "json",
            ]
        )
        == 0
    )
    release = json.loads(capsys.readouterr().out)
    assert release["context"]["dogfooding_signal_status"]["status"] == "not_checked"
    assert "dogfooding_signal_status" in release["action_signals"]["advisory_detail"]["selectors"]


def test_start_surfaces_unresolved_dogfooding_signal_outcome(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"
    cache_path.write_text(
        json.dumps({"status": "unresolved", "signals": ["diagnostic did not change routing"]}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue planned lane in stacked PR sequence",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    status = payload["context"]["dogfooding_signal_status"]
    assert status["status"] == "unresolved"
    assert status["closeout_blocked"] is True
    assert status["durable_residue"] is True
    assert status["sample_signals"] == ["diagnostic did not change routing"]
    assert "dogfooding_signal_status=unresolved" in payload["action_signals"]["changed_signals"]


def test_start_report_meta_task_keeps_routine_context_selector_only_with_background_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Give me an in-chat dogfooding report about this session",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    _assert_json_payload_under(payload, 10_000, label="start report/meta compact payload", sort_keys=False)
    assert "routine_work_context" not in payload["context"]
    assert "routine_work_context" in payload["drill_down"]["available_selectors"]
    assert "installed_state_compatibility" not in payload
    assert "installed_state_drift_triage" not in payload["context"]
    assert "installed_state_drift_triage=background_advisory" in payload["action_signals"]["changed_signals"]
    assert "installed_state_drift_triage" in payload["action_signals"]["advisory_detail"]["selectors"]


def test_start_broad_question_words_do_not_trigger_meta_report_compaction(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "How should we implement the runtime proof selector?",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "routine_work_context" in payload["context"]
    assert "installed_state_drift_triage=waived_for_narrow_work" in payload["action_signals"]["changed_signals"]


def test_start_narrow_source_work_qualifies_unrelated_installed_state_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_drift_triage=waived_for_narrow_work" in payload["action_signals"]["changed_signals"]
    assert "installed_state_drift_triage" in payload["action_signals"]["advisory_detail"]["selectors"]
    assert "installed_state_drift_triage" not in payload["context"]


def test_start_unrelated_changed_path_does_not_make_payload_drift_actionable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/typo.md",
                "--task",
                "Fix one docs typo",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert "installed_state_drift_triage=waived_for_narrow_work" in payload["action_signals"]["changed_signals"]
    assert "installed_state_drift_triage" not in payload["context"]


def test_start_installed_state_drift_triage_is_actionable_for_payload_claims(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    (tmp_path / ".agentic-workspace" / "payload-provenance.json").write_text(
        json.dumps({"kind": "wrong-kind"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Verify payload freshness before release",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    triage = payload["context"]["installed_state_drift_triage"]
    assert triage["status"] == "actionable_now"
    assert triage["claim_relevant"] is True
    assert "agentic-workspace upgrade" in triage["repair_command"]
    assert "installed_state_drift_triage=actionable_now" in payload["action_signals"]["changed_signals"]


def test_start_treats_named_path_question_as_conceptual_reference(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Are you actively applying the dogfooding instructions in AGENTS.md?",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["next_safe_action"]["next_safe_action"] == "choose-smallest-workflow-shape"
    assert payload["context"]["primary_action"]["command"] is None
    path_refs = payload["context"]["task_path_references"]
    assert path_refs["path_reference_kind"] == "conceptual-reference"
    assert path_refs["detected_paths"] == ["AGENTS.md"]
    assert path_refs["path_scoped_paths"] == []
    assert path_refs["agent_decision_required"] is True
    assert "implement --changed AGENTS.md" not in json.dumps(payload)


def test_start_path_scoped_task_text_uses_known_path_inspection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Review AGENTS.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["next_safe_action"]["next_safe_action"] == "inspect-known-task-paths"
    assert payload["context"]["primary_action"]["command"].endswith('implement --changed AGENTS.md --task "Review AGENTS.md" --format json')
    assert payload["context"]["primary_action"]["read_first"] == [payload["context"]["primary_action"]["command"]]
    path_refs = payload["context"]["task_path_references"]
    assert path_refs["path_reference_kind"] == "path-scoped-work"
    assert path_refs["path_scoped_paths"] == ["AGENTS.md"]
    assert path_refs["matched_action_terms"] == ["review"]


def test_start_explicit_changed_path_still_uses_changed_path_startup(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--changed",
                "AGENTS.md",
                "--task",
                "Review AGENTS.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["next_safe_action"]["next_safe_action"] == "select-changed-path-proof"
    assert payload["context"]["primary_action"]["command"].endswith("proof --changed AGENTS.md --format json")


def test_local_chat_checkpoint_write_creates_valid_local_record_and_startup_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Implement #1700 checkpoint slice",
                "--issue",
                "#1700",
                "--pr",
                "1705",
                "--durable-source",
                "docs/reference/local-chat-checkpoints.md",
                "--last-proof",
                "uv run pytest tests/test_workspace_cli.py",
                "--next-safe-command",
                "uv run python scripts/run_agentic_workspace.py start --target . --format json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    written = json.loads(capsys.readouterr().out)
    assert written["status"] == "written"
    assert written["path"] == ".agentic-workspace/local/chat-checkpoint.json"
    assert written["durable_sources"] == ["docs/reference/local-chat-checkpoints.md"]
    write_result_schema = json.loads(
        Path("src/agentic_workspace/contracts/schemas/local_chat_checkpoint_write_result.schema.json").read_text(encoding="utf-8")
    )
    write_result_errors = sorted(Draft202012Validator(write_result_schema).iter_errors(written), key=lambda error: list(error.path))
    assert [error.message for error in write_result_errors] == []

    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    schema = json.loads(Path("src/agentic_workspace/contracts/schemas/local_chat_checkpoint.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(checkpoint), key=lambda error: list(error.path))
    assert [error.message for error in errors] == []
    assert checkpoint["kind"] == "agentic-workspace/local-chat-checkpoint/v2"
    assert checkpoint["limits"]["not_closure_evidence"] is True
    assert "durable_sources" in checkpoint["resume_rule"]
    assert "fresh local/remote truth" in checkpoint["resume_rule"]
    assert checkpoint["volatile_observations"]["repo_root"]["value"] == tmp_path.resolve().as_posix()
    assert checkpoint["volatile_observations"]["branch"]["source"] == "git branch at checkpoint write"
    assert checkpoint["volatile_observations"]["head_commit"]["source"] == "git rev-parse HEAD at checkpoint write"
    assert checkpoint["volatile_observations"]["head_commit"]["observed_at"] == checkpoint["updated_at"]
    assert checkpoint["volatile_observations"]["current_pr"]["value"] == "1705"
    assert checkpoint["volatile_observations"]["current_pr"]["observed_at"] == checkpoint["updated_at"]
    assert checkpoint["volatile_observations"]["remote_comments"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["volatile_observations"]["ci_state"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["volatile_observations"]["dependency_state"]["value"]["status"] == "not-checked-by-local-checkpoint-writer"
    assert checkpoint["local_notes"]["task"] == "Implement #1700 checkpoint slice"
    assert checkpoint["local_notes"]["source"] == "local checkpoint write input; advisory only"
    assert checkpoint["proof_state"]["status"] == "historical-local-summary"
    assert checkpoint["proof_state"]["last_proof"] == ["uv run pytest tests/test_workspace_cli.py"]
    assert "new review or issue comments" in checkpoint["proof_state"]["valid_until_change"]
    assert any("PR or issue comments changed" in item for item in checkpoint["proof_state"]["stale_if"])
    assert "current completion evidence" in checkpoint["proof_state"]["rule"]
    resume_actions = [item["action"] for item in checkpoint["resume_checklist"]]
    assert "fetch latest PR comments and issue comments" in resume_actions
    assert "inspect git status and compare local HEAD with PR head" in resume_actions

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Resume checkpoint slice",
                "--format",
                "json",
            ]
        )
        == 0
    )
    startup = json.loads(capsys.readouterr().out)
    packet = startup["context"]["local_chat_checkpoint"]
    assert packet["status"] == "present"
    assert packet["durable_source_count"] == 1
    assert packet["durable_sources"] == ["docs/reference/local-chat-checkpoints.md"]
    assert packet["volatile_observations"]["head_commit"]["observed_at"] == checkpoint["updated_at"]
    assert packet["volatile_observations"]["current_pr"]["observed_at"] == checkpoint["updated_at"]
    assert packet["proof_state"]["status"] == "historical-local-summary"
    assert any(item["action"].startswith("re-run or re-evaluate proof") for item in packet["resume_checklist"])
    assert "local_chat_checkpoint" in startup["drill_down"]["available_selectors"]
    assert "local_chat_checkpoint=present" in startup["action_signals"]["changed_signals"]


def test_local_chat_checkpoint_surfaces_matching_planning_candidate_routes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1700-local-checkpoints", kind = "lane", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1700", title = "Local checkpoints", outcome = "Experiment with checkpoints.", promotion_signal = "Promote before parent closeout.", suggested_first_slice = "Shape checkpoint work." },
  { id = "github-1704-checkpoint-dogfood", kind = "slice", parent_id = "#1700", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1704", title = "Checkpoint dogfood", outcome = "Dogfood checkpoint resume.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Run checkpoint dogfood." },
  { id = "github-9999-unrelated", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #9999", title = "Unrelated", outcome = "Do something else." },
]
""",
    )

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Dogfood #1700 checkpoint resume",
                "--issue",
                "#1700",
                "--issue",
                "#1704",
                "--durable-source",
                "https://github.com/rickardvh/agentic-workspace/issues/1704",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    routes = selected["planning_candidate_routes"]
    assert routes["status"] == "matched"
    assert routes["issue_refs"] == ["#1700", "#1704"]
    assert routes["candidate_ids"] == ["github-1700-local-checkpoints", "github-1704-checkpoint-dogfood"]
    assert routes["matched_candidate_count"] == 2
    assert routes["route_options"][0]["id"] == "github-1700-local-checkpoints"
    assert routes["route_options"][0]["title"] == "Local checkpoints"
    assert routes["route_options"][0]["matched_issue_refs"] == ["#1700"]
    assert routes["route_options"][0]["route_kind"] == "parent-lane"
    assert routes["route_options"][0]["next_action"] == "promote-roadmap-candidate-to-durable-planning-owner"
    assert routes["route_options"][1]["route_kind"] == "child-slice"
    assert routes["route_options"][1]["parent_id"] == "#1700"
    assert "planning promote-to-plan --item-id github-1700-local-checkpoints" in routes["route_options"][0]["command"]
    assert "--expect-planning-revision" in routes["route_options"][0]["command"]
    assert "github-9999-unrelated" not in json.dumps(routes)
    assert routes["authority"] == "advisory-from-local-checkpoint-and-checked-in-planning"
    assert "Verify checkpoint refs against durable sources" in routes["claim_boundary"]

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume checkpoint slice", "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    context_routes = startup["context"]["local_chat_checkpoint"]["planning_candidate_routes"]
    assert context_routes["candidate_ids"] == routes["candidate_ids"]
    assert context_routes["route_options"][1]["id"] == "github-1704-checkpoint-dogfood"


def test_local_chat_checkpoint_omits_route_suggestions_when_no_candidate_matches(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1700-local-checkpoints", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1700", title = "Local checkpoints" },
]
""",
    )

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Resume unrelated checkpoint",
                "--issue",
                "#1801",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    selected = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert selected["status"] == "present"
    assert "planning_candidate_routes" not in selected

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Resume unrelated checkpoint", "--format", "json"]) == 0
    startup = json.loads(capsys.readouterr().out)
    assert "planning_candidate_routes" not in startup["context"]["local_chat_checkpoint"]


def test_local_chat_checkpoint_write_preserves_and_replaces_values(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "First",
                "--durable-source",
                "docs/first.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Second",
                "--durable-source",
                "docs/second.md",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    preserved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert preserved["durable_sources"] == ["docs/first.md", "docs/second.md"]
    assert preserved["task"] == "Second"

    assert (
        cli.main(
            [
                "checkpoint",
                "write",
                "--target",
                str(tmp_path),
                "--task",
                "Replacement",
                "--durable-source",
                "docs/replacement.md",
                "--replace",
                "--format",
                "json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    replaced = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert replaced["durable_sources"] == ["docs/replacement.md"]
    assert replaced["task"] == "Replacement"


def test_local_chat_checkpoint_startup_reports_absent_stale_and_unreadable(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    absent = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert absent["status"] == "absent"

    checkpoint_path = tmp_path / ".agentic-workspace" / "local" / "chat-checkpoint.json"
    checkpoint_path.write_text(json.dumps({"kind": "old-kind", "durable_sources": ["docs/source.md"]}), encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    stale = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert stale["status"] == "stale"
    assert stale["durable_sources"] == ["docs/source.md"]

    checkpoint_path.write_text(
        json.dumps({"kind": "agentic-workspace/local-chat-checkpoint/v1", "durable_sources": ["docs/source.md"]}),
        encoding="utf-8",
    )
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    stale_v1 = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert stale_v1["status"] == "stale"
    assert stale_v1["checkpoint_kind"] == "agentic-workspace/local-chat-checkpoint/v1"
    assert stale_v1["durable_sources"] == ["docs/source.md"]

    checkpoint_path.write_text("{not json", encoding="utf-8")
    assert cli.main(["start", "--target", str(tmp_path), "--select", "local_chat_checkpoint", "--format", "json"]) == 0
    unreadable = json.loads(capsys.readouterr().out)["values"]["local_chat_checkpoint"]
    assert unreadable["status"] == "unreadable"


def test_start_pr_reference_wording_does_not_route_as_unknown_issue_scope(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Address the reviews on #103",
                "--select",
                "planning_safety_gate,issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    gate = payload["values"]["planning_safety_gate"]
    assert gate["issue_refs"] == []
    assert gate["pr_context"]["status"] == "pr-context-detected"
    assert gate["pr_context"]["refs"] == ["#103"]
    assert payload.get("missing") == ["issue_reference_intent"]


def test_start_issue_reference_wording_keeps_issue_scope_warning(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["next_safe_action"] == "refresh-external-issue-intent"
    assert payload["context"]["issue_reference_intent"]["issue_refs"] == ["#103"]
    effect = payload["context"]["issue_reference_intent"]["action_effect"]
    assert effect["force"] == "required_before_claim"
    assert effect["allowed_now"] == "read-review-and-state-bounded-slice"
    assert effect["blocked_until_reconciled"] == ["claim-external-issue-scope-confirmed", "claim-task-complete"]
    assert effect["resolution_selector"] == "context.issue_reference_intent"
    assert "external-intent refresh-github" in effect["resolution_command"]


def test_start_open_issue_intake_routes_refresh_and_grouping(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "kind": "planning-external-intent-evidence/v1",
                "refreshed_at": "2026-06-26T08:00:00+00:00",
                "refresh_metadata": {"adapter": "fixture", "open_count": 4, "closed_count": 0},
                "items": [
                    {"id": "#1739", "system": "github", "status": "open", "kind": "lane", "title": "Dogfooding friction lane"},
                    {
                        "id": "#1804",
                        "system": "github",
                        "status": "open",
                        "kind": "slice",
                        "parent_id": "#1739",
                        "title": "Warn on unsupported lane status",
                    },
                    {
                        "id": "#1803",
                        "system": "github",
                        "status": "open",
                        "kind": "slice",
                        "parent_id": "#1739",
                        "title": "Repair affordances",
                    },
                    {"id": "#1802", "system": "github", "status": "open", "kind": "issue", "title": "Open issue intake"},
                ],
            }
        ),
        encoding="utf-8",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1739-dogfooding", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1739", title = "Dogfooding friction lane", promotion_signal = "Promote first.", suggested_first_slice = "Review child slices." },
  { id = "github-1802-open-issue-intake", maturity = "candidate", status = "next", priority = "P2", refs = "GitHub #1802", title = "Open issue intake", promotion_signal = "Promote when selected.", suggested_first_slice = "Add intake routing." },
]
""",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Ingest and prioritise open issues",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["next_safe_action"]["next_safe_action"] == "refresh-open-issue-intake"
    intake = payload["context"]["open_issue_intake"]
    assert "external-intent refresh-github" in intake["command_owned_intake"]
    assert "--apply-planning-candidates" in intake["command_owned_intake"]
    assert intake["freshness"]["status"] == "fresh-enough"
    assert intake["counts"]["open_issue_count"] == 4
    assert intake["counts"]["planning_candidate_count"] == 2
    grouping = intake["grouping_hints"]
    assert grouping["parent_lanes"][0]["id"] == "#1739"
    assert grouping["child_issue_clusters"][0]["parent_id"] == "#1739"
    assert grouping["child_issue_clusters"][0]["child_count"] == 2
    assert grouping["standalone_candidates"][0]["id"] == "#1802"
    assert intake["detailed_issue_list_rule"]


def test_start_cached_issue_reference_intent_is_advisory(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    evidence_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "#103",
                        "system": "github",
                        "status": "open",
                        "kind": "issue",
                        "title": "Cached issue-backed intent",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Implement issue #103",
                "--select",
                "issue_reference_intent",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    intent = payload["values"]["issue_reference_intent"]
    assert intent["status"] == "evidence-available"
    effect = intent["action_effect"]
    assert effect["force"] == "advisory"
    assert effect["allowed_now"] == "continue-with-cached-issue-intent"
    assert effect["blocked_until_reconciled"] == []
    assert effect["resolution_selector"] == "context.issue_reference_intent"
    assert effect["resolution_command"] == ""


def test_start_ambiguous_numeric_ref_stays_advisory_without_blocking_read_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Look at #103",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_safe_action"]["read_only_allowed"] is True
    assert payload["context"]["issue_reference_intent"]["status"] == "details-needed"
    assert payload["context"]["issue_reference_intent"]["action_effect"]["force"] == "required_before_claim"
    assert payload["context"]["planning"]["planning_safety_gate"]["workflow_sufficient"] is True


def test_start_default_keeps_skill_catalog_breakdown_behind_command(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    skills = payload["skills"]
    catalog = skills["catalog"]

    assert skills["kind"] == "agentic-workspace/startup-skills-projection/v1"
    assert catalog["available"] is True
    assert catalog["catalog_command_available"] is True
    assert isinstance(catalog["total_count"], int)
    assert isinstance(catalog["warning_count"], int)
    assert "agentic-workspace skills" in catalog["command"]
    assert catalog["detail_visibility"] == "source and owner breakdowns stay behind catalog.command"
    assert "counts_by_source_kind" not in catalog
    assert "counts_by_owner" not in catalog
    assert "sources" not in catalog


def test_compact_skill_catalog_marks_malformed_payload_unavailable() -> None:
    catalog = workspace_runtime_primitives._compact_startup_skill_catalog_summary({"skills": "bad", "warnings": "bad"})

    assert catalog["available"] is False
    assert catalog["catalog_command_available"] is True
    assert catalog["total_count"] == 0
    assert catalog["warning_count"] == 0


def test_start_required_skill_projection_survives_compact_catalog(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue #1680 lane",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    skills = payload["skills"]

    assert skills["status"] == "recommended"
    assert skills["required"][0]["id"] == "planning-reporting"
    assert skills["required"][0]["reason"] == "required by next_safe_action.required_skill"
    assert "catalog" in skills
    assert "counts_by_owner" not in skills["catalog"]


def test_start_select_surfaces_memory_decision_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Shape a workflow issue",
                "--select",
                "memory_decision_packet",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    packet = payload["values"]["memory_decision_packet"]

    assert packet["kind"] == "agentic-workspace/memory-decision-packet/v1"
    assert packet["stage"] == "startup"
    assert packet["pull"]["status"] == "not_checked"
    assert "memory route" in packet["pull"]["recommended_command"]
    assert "--stage startup" in packet["pull"]["recommended_command"]
    assert packet["authority_boundary"]["agent_owns"]
    assert "No keyword-triggered Memory requirement." in packet["limits"]


def test_start_select_surfaces_installed_state_compatibility(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Inspect installed state",
                "--select",
                "installed_state_compatibility",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    compatibility = payload["values"]["installed_state_compatibility"]

    assert compatibility["kind"] == "agentic-workspace/installed-state-compatibility/v1"
    assert compatibility["authority"] == "repo-state-authoritative"
    assert compatibility["executable"]["classification"]
    assert compatibility["payload"]["status"]
    assert compatibility["status"] == "compatible"
    assert compatibility["action_effect"]["force"] == "advisory"
    assert compatibility["action_effect"]["allowed_now"] == "continue-ordinary-work"
    assert compatibility["action_effect"]["blocked_until_reconciled"] == []
    assert (
        compatibility["action_effect"]["claim_boundary"]
        == "installed-state-compatible-does-not-replace-task-proof-or-acceptance-reconciliation"
    )


def test_report_release_recovery_section_exposes_payload_and_semver_recovery_routes(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        cli,
        "_release_recovery_live_state",
        lambda **kwargs: {
            "release_ci_failure": {
                "kind": "agentic-workspace/release-ci-failure-summary/v1",
                "status": "failed-release-run",
                "workflow": "Release From Semver Label",
                "run_url": "https://github.com/example/repo/actions/runs/1",
                "failed_job": "release",
                "failed_step": "Run proof",
                "error_summary": ["ERROR release proof failed"],
                "freshness": {"status": "active_failed_release"},
            },
            "release_publication_state": {
                "status": "failed-release-unpublished",
                "failed_run_url": "https://github.com/example/repo/actions/runs/1",
            },
        },
    )

    assert (
        cli.main(
            [
                "report",
                "--target",
                str(repo_root),
                "--section",
                "release_recovery",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    recovery = payload["answer"]

    assert recovery["kind"] == "agentic-workspace/release-recovery/v1"
    assert recovery["release_model"] == "coordinated-workspace"
    assert recovery["semver_release_action"]["status"] == "not-fetched"
    assert recovery["release_ci_failure"]["status"] == "failed-release-run"
    assert recovery["release_ci_failure"]["failed_step"] == "Run proof"
    assert recovery["release_publication_state"]["status"] == "failed-release-unpublished"
    assert "release_recovery_status.py" in recovery["semver_release_action"]["command"]
    assert "repair_route" in recovery["payload_drift"]
    assert "required_version_paths" in recovery["coordinated_recovery"]["pr_shape"]


def test_start_surfaces_pr_comment_attention_only_for_pr_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--format", "json"]) == 0
    quiet_payload = json.loads(capsys.readouterr().out)
    assert "pr_comment_attention" not in quiet_payload["context"]
    assert "pr_comment_attention" not in quiet_payload["action_signals"]["advisory_detail"]["selectors"]

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue PR #1831 review fixes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    attention = payload["context"]["pr_comment_attention"]
    assert attention["status"] == "pr_comment_status_unavailable"
    assert attention["pr_number"] == "1831"
    assert "pr_comment_delta.py" in attention["recommended_command"]
    assert "pr_comment_attention=pr_comment_status_unavailable" in payload["action_signals"]["changed_signals"]
    assert "pr_comment_attention" in payload["action_signals"]["advisory_detail"]["selectors"]


def test_report_pr_comment_attention_reads_cached_actionable_and_empty_deltas(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "pr-comment-delta.json"
    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "pr_url": "https://github.com/rickardvh/agentic-workspace/pull/1831",
                "new_comment_count": 1,
                "category_counts": {
                    "actionable_code_doc_body_change": 1,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                    "informational_no_local_change": 0,
                },
                "items": [
                    {
                        "kind": "review_thread_comment",
                        "category": "actionable_code_doc_body_change",
                        "path": "src/app.py",
                        "line": 12,
                        "url": "https://example.test/pr#thread",
                        "proof_hint": "Run focused tests.",
                    }
                ],
                "baseline": {"since": "2026-06-28T00:00:00Z"},
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    actionable = json.loads(capsys.readouterr().out)["answer"]
    assert actionable["status"] == "actionable_pr_comments_present"
    assert actionable["actionable_count"] == 1
    assert actionable["sample"][0]["path"] == "src/app.py"

    # Legacy empty caches are not enough to support readiness claims because they
    # do not prove which PR head was observed.
    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "new_comment_count": 0,
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                    "informational_no_local_change": 0,
                },
                "items": [],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    stale_empty = json.loads(capsys.readouterr().out)["answer"]
    assert stale_empty["status"] == "pr_comment_status_unavailable"
    assert stale_empty["cached_status"] == "no_actionable_pr_comments_detected"
    assert stale_empty["degraded_explicitly"] is True

    cache_path.write_text(
        json.dumps(
            {
                "kind": "agentic-workspace/pr-comment-delta/v1",
                "repository": "rickardvh/agentic-workspace",
                "pr_number": 1831,
                "new_comment_count": 0,
                "category_counts": {
                    "actionable_code_doc_body_change": 0,
                    "pr_metadata_body_only_change": 0,
                    "ci_label_only_issue": 0,
                    "ambiguous_needs_human": 0,
                    "informational_no_local_change": 0,
                },
                "items": [],
                "freshness": {
                    "status": "current_at_observed_head",
                    "pr_head_sha": "abc123",
                    "observed_at": "2026-06-28T00:00:00Z",
                },
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "pr_comment_attention", "--format", "json"]) == 0
    fresh_empty = json.loads(capsys.readouterr().out)["answer"]
    assert fresh_empty["status"] == "no_actionable_pr_comments_detected"
    assert fresh_empty["actionable_count"] == 0
    assert fresh_empty["freshness"]["pr_head_sha"] == "abc123"


def test_start_pr_comment_attention_reads_stack_cache_with_concrete_refresh_commands(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "pr-comment-stack.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    unavailable = json.loads(capsys.readouterr().out)
    unavailable_attention = unavailable["context"]["pr_comment_attention"]
    assert unavailable_attention["status"] == "stack_comment_status_unavailable"
    assert unavailable_attention["stack_discovery"]["status"] == "unavailable"
    assert unavailable_attention["stack_member_count"] == 0

    fresh_stack = {
        "repository": "rickardvh/agentic-workspace",
        "stack_members": [
            {
                "pr_number": 1840,
                "branch": "codex/proof-reuse",
                "head_sha": "aaa111",
                "delta": {
                    "category_counts": {
                        "actionable_code_doc_body_change": 0,
                        "pr_metadata_body_only_change": 0,
                        "ci_label_only_issue": 0,
                        "ambiguous_needs_human": 0,
                    },
                    "freshness": {"status": "current_at_observed_head", "pr_head_sha": "aaa111"},
                },
            },
            {
                "pr_number": 1841,
                "branch": "codex/stack-comments",
                "head_sha": "bbb222",
                "delta": {
                    "category_counts": {
                        "actionable_code_doc_body_change": 0,
                        "pr_metadata_body_only_change": 0,
                        "ci_label_only_issue": 0,
                        "ambiguous_needs_human": 0,
                    },
                    "freshness": {"status": "current_at_observed_head", "pr_head_sha": "bbb222"},
                },
            },
        ],
    }
    cache_path.write_text(json.dumps(fresh_stack), encoding="utf-8")

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    current = json.loads(capsys.readouterr().out)
    assert current["context"]["pr_comment_attention"]["status"] == "stack_comments_current"

    actionable_stack = copy.deepcopy(fresh_stack)
    actionable_stack["stack_members"][1]["delta"]["category_counts"]["actionable_code_doc_body_change"] = 1
    cache_path.write_text(
        json.dumps(actionable_stack),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    attention = payload["context"]["pr_comment_attention"]
    assert attention["status"] == "actionable_stack_comments_present"
    assert attention["stack_member_count"] == 2
    assert attention["stack"]["stack_members"][0]["refresh_command"].endswith("--pr 1840 --format json")
    assert attention["stack"]["stack_members"][1]["comment_status"] == "actionable_pr_comments_present"
    assert "pr_comment_attention=actionable_stack_comments_present" in payload["action_signals"]["changed_signals"]

    stale_stack = copy.deepcopy(fresh_stack)
    stale_stack["stack_members"][0]["delta"].pop("freshness")
    cache_path.write_text(json.dumps(stale_stack), encoding="utf-8")
    assert (
        cli.main(
            [
                "start",
                "--target",
                str(tmp_path),
                "--task",
                "Continue stacked PR review fixes",
                "--format",
                "json",
            ]
        )
        == 0
    )
    stale = json.loads(capsys.readouterr().out)
    assert stale["context"]["pr_comment_attention"]["status"] == "stack_comment_status_unavailable"


def test_report_proof_reuse_guidance_classifies_safe_and_stale_receipts(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    changed_path = tmp_path / "src" / "app.py"
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("VALUE = 1\n", encoding="utf-8")
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "proof-reuse.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    unknown = json.loads(capsys.readouterr().out)["answer"]
    assert unknown["status"] == "reuse_unknown"

    minimal_receipt = {
        "prior_head": "abc123",
        "prior_base": "base123",
        "changed_paths": ["src/app.py"],
        "path_fingerprints": {"src/app.py": hashlib.sha256(changed_path.read_bytes()).hexdigest()},
        "proof_groups": [{"command": "uv run pytest tests/test_app.py -q", "status": "passed"}],
    }
    cache_path.write_text(json.dumps(minimal_receipt), encoding="utf-8")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    under_evidenced = json.loads(capsys.readouterr().out)["answer"]
    assert under_evidenced["status"] == "reuse_unknown"
    assert "parent_proof_reference" in under_evidenced["missing_reuse_evidence"]
    assert "command_identity" in under_evidenced["proof_groups"][0]["missing_reuse_evidence"]

    safe_receipt = {
        **minimal_receipt,
        "parent_proof_reference": "proof-receipt:abc123",
        "proof_selection_fingerprint": "selection:runtime-tests",
        "dependency_config_fingerprint": "deps:locked",
        "generated_surface_freshness": {"status": "verified"},
        "proof_groups": [
            {
                "command": "uv run pytest tests/test_app.py -q",
                "command_fingerprint": "cmd:test-app",
                "status": "passed",
            }
        ],
    }
    cache_path.write_text(json.dumps(safe_receipt), encoding="utf-8")

    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    safe = json.loads(capsys.readouterr().out)["answer"]
    assert safe["status"] == "reuse_safe_with_evidence"
    assert safe["proof_groups"][0]["classification"] == "reuse_safe_with_evidence"

    cache_path.write_text(
        json.dumps(
            {
                **safe_receipt,
                "changed_paths": ["src/app.py"],
                "path_fingerprints": {"src/app.py": hashlib.sha256(changed_path.read_bytes()).hexdigest()},
                "proof_groups": [
                    {
                        "command": "uv run pytest tests/test_app.py -q",
                        "command_fingerprint": "cmd:test-app",
                        "status": "passed",
                    },
                    {"command": "make lint-workspace", "command_fingerprint": "cmd:lint", "status": "failed"},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    partial = json.loads(capsys.readouterr().out)["answer"]
    assert partial["status"] == "focused_rerun_required"
    assert partial["proof_groups"][1]["classification"] == "rerun_required"

    changed_path.write_text("VALUE = 2\n", encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "proof_reuse_guidance", "--format", "json"]) == 0
    stale = json.loads(capsys.readouterr().out)["answer"]
    assert stale["status"] == "rerun_required"
    assert stale["changed_fingerprints"] == ["src/app.py"]


def test_report_runtime_mirror_consistency_detects_missing_and_mismatched_shapes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    core = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_core.py"
    primitives = tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py"
    core.parent.mkdir(parents=True, exist_ok=True)
    core.write_text(
        """
def _pr_comment_attention_payload():
    return {"kind": "agentic-workspace/pr-comment-attention/v1", "status": "present", "extra": True}

def _dogfooding_signal_status_payload():
    return {"kind": "agentic-workspace/dogfooding-signal-status/v1", "status": "present"}
""",
        encoding="utf-8",
    )
    primitives.write_text(
        """
def _pr_comment_attention_payload():
    return {"kind": "agentic-workspace/pr-comment-attention/v1", "status": "present"}
""",
        encoding="utf-8",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "runtime_mirror_consistency", "--format", "json"]) == 0
    mirror = json.loads(capsys.readouterr().out)["answer"]

    assert mirror["status"] == "shape_mismatch"
    by_surface = {record["mirrored_surface"]: record for record in mirror["records"]}
    assert by_surface["pr_comment_attention"]["status"] == "shape_mismatch"
    assert by_surface["dogfooding_signal_status"]["status"] == "mirror_missing"

    primitives.write_text(core.read_text(encoding="utf-8"), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "runtime_mirror_consistency", "--format", "json"]) == 0
    in_sync = json.loads(capsys.readouterr().out)["answer"]
    assert in_sync["status"] == "in_sync"


def test_report_dogfooding_signal_status_covers_closeout_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    not_checked = json.loads(capsys.readouterr().out)["answer"]
    assert not_checked["status"] == "not_checked"
    assert not_checked["outcome"] == "not_checked"
    assert not_checked["closeout_blocked"] is False
    assert "session_improvement_intake" in not_checked["detail_command"]

    cache_path.write_text(json.dumps({"status": "checked_none", "reason": "reviewed; no durable signal"}), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    no_signal = json.loads(capsys.readouterr().out)["answer"]
    assert no_signal["status"] == "checked_none"
    assert no_signal["durable_residue"] is False

    cache_path.write_text(
        json.dumps({"status": "recorded_chat_only", "signals": ["in-chat dogfooding note"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    chat_only = json.loads(capsys.readouterr().out)["answer"]
    assert chat_only["status"] == "recorded_chat_only"
    assert chat_only["durability"] == "local_chat_only"
    assert chat_only["canonical_repo_history"] is False

    cache_path.write_text(
        json.dumps({"status": "recorded_session_only", "signals": ["temporary validation friction"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    session_only = json.loads(capsys.readouterr().out)["answer"]
    assert session_only["status"] == "recorded_session_only"
    assert session_only["durability"] == "local_session_only"

    cache_path.write_text(
        json.dumps({"status": "routed_to_issue", "signals": ["startup missed PR comments"], "destinations": ["#1831"]}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    routed = json.loads(capsys.readouterr().out)["answer"]
    assert routed["status"] == "routed_to_issue"
    assert routed["destinations"] == ["#1831"]
    assert routed["closeout_blocked"] is False
    assert routed["durable_residue"] is True

    cache_path.write_text(
        json.dumps({"status": "deferred_to_roadmap", "signals": ["larger design concern"], "deferred_reason": "roadmap batch"}),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    deferred = json.loads(capsys.readouterr().out)["answer"]
    assert deferred["status"] == "deferred_to_roadmap"
    assert deferred["durability"] == "roadmap_or_future_work"

    cache_path.write_text(
        json.dumps(
            {
                "status": "dismissed_with_reason",
                "signals": ["one-off shell typo"],
                "dismissal_reason": "operator typo, not product friction",
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    dismissed = json.loads(capsys.readouterr().out)["answer"]
    assert dismissed["status"] == "dismissed_with_reason"
    assert dismissed["dismissal_reason"] == "operator typo, not product friction"

    cache_path.write_text(json.dumps({"signals": ["unrouted friction"]}), encoding="utf-8")
    assert cli.main(["report", "--target", str(tmp_path), "--section", "dogfooding_signal_status", "--format", "json"]) == 0
    blocked = json.loads(capsys.readouterr().out)["answer"]
    assert blocked["status"] == "unresolved"
    assert blocked["closeout_blocked"] is True
    assert blocked["durable_residue"] is True


def test_session_improvement_intake_separates_session_and_repo_wide_scopes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    cache_path = tmp_path / ".agentic-workspace" / "local" / "cache" / "dogfooding-signal-status.json"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    unavailable = json.loads(capsys.readouterr().out)["answer"]
    assert unavailable["status"] == "unavailable"
    assert unavailable["session_signal_source"]["status"] == "missing"
    assert unavailable["repo_wide_existing"]["included_by_default"] is False
    assert unavailable["repo_wide_existing"]["status"] == "bounded_index_available"
    assert "defaults --section improvement_intake --format json" in unavailable["repo_wide_existing"]["command"]
    assert "report --target ./repo --section improvement_intake --format json" in unavailable["repo_wide_existing"]["full_scan_command"]
    assert "large_file" not in json.dumps(unavailable)

    cache_path.write_text(
        json.dumps(
            {
                "status": "unresolved",
                "signals": ["improvement diagnostics did not change next action"],
                "routing_decision": "route_now",
            }
        ),
        encoding="utf-8",
    )
    assert cli.main(["report", "--target", str(tmp_path), "--section", "session_improvement_intake", "--format", "json"]) == 0
    session = json.loads(capsys.readouterr().out)["answer"]
    assert session["status"] == "session_observed"
    assert session["session_observed_signals"][0]["outcome"] == "unresolved"
    assert session["routing_decisions"][0]["decision"] == "route_now"
    assert session["routing_decisions"][0]["closeout_blocked"] is True

    assert cli.main(["report", "--target", str(tmp_path), "--section", "improvement_intake", "--format", "json"]) == 0
    repo_wide = json.loads(capsys.readouterr().out)["answer"]
    assert repo_wide["intake_scope"]["status"] == "explicit_repo_wide_requested"
    assert "repo_wide_existing_candidates" in repo_wide


def test_start_surfaces_recovery_for_obsolete_default_preset(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                'default_preset = "planning"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/start-recovery/v1"
    assert payload["status"] == "recovery-required"
    assert payload["problem"]["obsolete_field"] == "workspace.default_preset"
    assert payload["problem"]["replacement"] == "[modules] enabled = [...]"
    assert payload["problem"]["config_valid"] is False
    assert payload["automated_repair"]["safe"] is False
    assert payload["next_safe_action"]["implementation_allowed"] is False
    assert payload["recovery_packet"]["next_safe_command"] == "agentic-workspace config --target . --format json"


def test_start_recovery_for_obsolete_default_preset_uses_configured_cli_invoke(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[workspace]",
                'cli_invoke = "uv run aw-dev"',
                'default_preset = "planning"',
            ]
        ),
        encoding="utf-8",
    )

    assert cli.main(["start", "--target", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/start-recovery/v1"
    assert payload["recovery_packet"]["next_safe_command"] == "uv run aw-dev config --target . --format json"


def test_proof_supports_exact_field_selectors_for_sufficiency(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--select",
                "sufficiency,next",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "proof"
    assert payload["values"]["sufficiency"]["sufficiency_result"] == "required-proof-selected"
    assert payload["values"]["next"]["action"] == "run-validation-command"
    assert "missing" not in payload


def test_report_sections_expose_authority_and_compliance_boundaries(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(tmp_path), "--section", "authority_hierarchy", "--format", "json"]) == 0
    authority = json.loads(capsys.readouterr().out)["answer"]
    assert authority["kind"] == "agentic-workspace/authority-hierarchy/v1"
    assert authority["ordered_authority"][-1]["authority"] == "disposable-or-audit-only-unless-promoted"
    assert "generated_summary" in authority["promotion_paths"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "compliance_economics", "--format", "json"]) == 0
    compliance = json.loads(capsys.readouterr().out)["answer"]
    assert compliance["kind"] == "agentic-workspace/compliance-economics/v1"
    assert "cannot force" in compliance["boundary"]
    strengths = {entry["level"]: entry["strength"] for entry in compliance["enforcement_levels"]}
    assert strengths["prompt_instruction"] == "weak"
    assert strengths["schema_validity"] == "strong"


def test_report_exposes_configuration_projection_without_expanding_config_detail(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    projection = router["context"]["configuration_projection"]
    assert projection["projection_status_counts"]["active"] >= 1
    assert projection["unprojected_field_count"] == 0
    assert projection["verification_probe_count"] >= 2
    assert projection["evaluation"]["status"] == "pass"
    assert projection["evaluation"]["detail_section"] == "selective_surfacing_evaluation"
    assert "facts" not in projection
    assert "owner_boundary_exceptions" not in projection
    evaluation = router["context"]["selective_surfacing_evaluation"]
    assert evaluation["status"] == "pass"
    assert evaluation["failing_check_count"] == 0
    assert evaluation["metrics"]["compact_selector_count"] == 1
    hint = next(item for item in router["drill_down"]["section_hints"] if item["section"] == "configuration_projection")
    assert "projection coverage" in hint["purpose_summary"]
    assert hint["volume"] == "normal"
    eval_hint = next(item for item in router["drill_down"]["section_hints"] if item["section"] == "selective_surfacing_evaluation")
    assert "cheap contract checks" in eval_hint["purpose_summary"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "configuration_projection", "--format", "json"]) == 0

    selected = json.loads(capsys.readouterr().out)
    assert selected["selector"] == {"section": "configuration_projection"}
    answer = selected["answer"]
    assert answer["kind"] == "agentic-workspace/configuration-projection/v1"
    assert answer["unprojected_fields"] == []
    assert any(item["owner_boundary"] == "local-human-owned" for item in answer["facts"])
    assert answer["verification"]["non_applicable_suppression"][0]["id"] == "ordinary-report-keeps-detail-sectioned"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "selective_surfacing_evaluation", "--format", "json"]) == 0

    selected_eval = json.loads(capsys.readouterr().out)
    assert selected_eval["selector"] == {"section": "selective_surfacing_evaluation"}
    assert selected_eval["answer"]["kind"] == "agentic-workspace/selective-surfacing-evaluation/v1"
    assert selected_eval["answer"]["status"] == "pass"
    assert selected_eval["answer"]["metrics"]["compact_json_size"] <= 1400


def test_local_overlay_report_section_and_projection(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_overlay", "--format", "json"]) == 0
    absent = json.loads(capsys.readouterr().out)["answer"]
    assert absent["status"] == "absent"

    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.guidance.local_cli]
signal = "local-tool-availability"
category = "tooling"
applies_to_paths = ["tools/**"]
guidance = "Use the checkout-local CLI."
required_commands = ["python -c \\"print('tool ok')\\""]
impact = "advisory"

[local_overlay.high_risk.guardrails.fixtures]
applies_to_paths = ["tests/fixtures/**"]
sensitive_data = ["real customer email"]
synthetic_fixture_guidance = ["Use example.com addresses."]
impact = "claim-limiting"
unsupported_policy_override = true
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_overlay", "--format", "json"]) == 0
    configured = json.loads(capsys.readouterr().out)["answer"]
    assert configured["status"] == "configured"
    assert configured["configured_count"] == 2
    assert configured["ordinary_guidance_count"] == 1
    assert configured["high_risk_profile_count"] == 1
    assert configured["ordinary_guidance"][0]["source_layer"] == "repo-local-override"
    assert configured["high_risk_profile"]["detail_selector"] == "local_high_risk_overlay"
    assert "unsupported_policy_override" in configured["warnings"][0]
    assert "checked-in host policy" in configured["authority_boundary"]["rule"]

    assert cli.main(["report", "--target", str(tmp_path), "--section", "local_high_risk_overlay", "--format", "json"]) == 0
    high_risk = json.loads(capsys.readouterr().out)["answer"]
    assert high_risk["configured_count"] == 1
    assert high_risk["sections"]["guardrails"][0]["source_layer"] == "repo-local-override"

    assert cli.main(["report", "--target", str(tmp_path), "--section", "configuration_projection", "--format", "json"]) == 0
    projection = json.loads(capsys.readouterr().out)["answer"]
    overlay_row = next(row for row in projection["facts"] if row["field"] == "local_overlay.*")
    assert overlay_row["projection_status"] in {"active", "selector-backed"}
    assert "local_overlay" in overlay_row["ordinary_path_routes"][0]


def test_local_overlay_ordinary_guidance_projects_without_high_risk(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        f"""
schema_version = 1

[workspace]
cli_invoke = "{REPO_LOCAL_CLI_INVOKE}"
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        """
schema_version = 1

[local_overlay.guidance.local_cli]
signal = "local-tool-availability"
category = "tooling"
applies_to_paths = ["tools/**"]
guidance = "Use the checkout-local CLI."
required_commands = ["python -c \\"print('tool ok')\\""]
impact = "advisory"

[local_overlay.guidance.stack]
signal = "branch-stack-convention"
category = "workflow"
applies_to_task_markers = ["stacked pr"]
guidance = "Keep local stack order when preparing PRs."
impact = "claim-limiting"
""",
    )
    _write(tmp_path / "tools" / "run.py", "print('ok')\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "tools/run.py", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["local_overlay"]["status"] == "active"
    assert payload["local_overlay"]["ordinary_guidance_count"] == 1
    assert payload.get("high_risk_overlay") is None


def test_report_ordinary_agent_path_is_phase_question_first(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    ordinary_path = router["context"]["report_profile"]["ordinary_agent_path"]
    assert ordinary_path["primary_design_unit"] == "phase_question"
    assert ordinary_path["rule"] == "Answer the current phase question first; commands are routed affordances, not the workflow."
    assert [item["phase"] for item in ordinary_path["phase_questions"]] == [
        "startup",
        "work_shaping",
        "governing_knowledge",
        "implementation_context",
        "proof",
        "closeout",
        "continuation",
    ]
    assert ordinary_path["phase_questions"][0]["question"] == "What is the smallest safe context before acting?"
    assert "agentic-workspace start" in ordinary_path["phase_questions"][0]["primary_affordance"]
    assert "command inventories" in ordinary_path["phase_questions"][0]["boundary"]
    assert ordinary_path["phase_questions"][3]["phase"] == "implementation_context"
    assert "implement --changed <paths>" in ordinary_path["phase_questions"][3]["primary_affordance"]
    assert "intent-satisfaction judgment" in ordinary_path["phase_questions"][4]["boundary"]
    assert ordinary_path["phase_questions"][6]["question"] == "How can a future agent resume without replaying chat?"


def test_report_ordinary_agent_path_carries_lane_completion_model(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["report", "--target", str(tmp_path), "--format", "json"]) == 0

    router = json.loads(capsys.readouterr().out)
    ordinary_path = router["context"]["report_profile"]["ordinary_agent_path"]
    lane_model = ordinary_path["lane_completion_model"]
    assert lane_model["kind"] == "agentic-workspace/ordinary-lane-completion-model/v1"
    assert lane_model["visibility_disposition"]["question"].startswith("Does this surface change")
    assert "start" in lane_model["visibility_disposition"]["retained_first_contact"]
    assert "preflight" in lane_model["visibility_disposition"]["diagnostic_or_recovery"]
    assert "docs/reference/" in lane_model["visibility_disposition"]["generated_or_reference"]
    assert "claim_boundary" in lane_model["artifact_lifecycle"]["minimal_survivor_shape"]
    assert [scenario["id"] for scenario in lane_model["restart_scenarios"]] == [
        "direct-work",
        "known-changed-paths",
        "active-lane-continuation",
        "takeover-or-recovery",
        "parent-lane-closeout",
    ]
    assert "owner surface before broad reading" in lane_model["affordance_first_rules"]
    assert lane_model["reasoning_skill_boundary"].startswith("Use reasoning skills")
    assert "restart scenarios reviewed or routed" in lane_model["closeout_checks"]


def test_selective_surfacing_evaluation_fails_on_missing_guidance_or_compact_noise(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    config = cli._load_workspace_config(target_root=tmp_path)
    projection = cli._configuration_projection_payload(config=config)
    compact = cli._compact_configuration_projection_payload(projection)

    noisy_compact = {**compact, "facts": projection["facts"]}
    noisy_evaluation = cli._selective_surfacing_evaluation_payload(
        projection_payload=projection,
        compact_projection=noisy_compact,
        cli_invoke=config.cli_invoke,
    )
    noisy_checks = {check["id"]: check for check in noisy_evaluation["checks"]}
    assert noisy_checks["irrelevant-guidance-suppressed-from-compact-output"]["result"] == "fail"
    assert noisy_evaluation["status"] == "fail"

    broken_projection = {**projection, "facts": [{"id": "broken:row", "projection_status": "active"}]}
    missing_evaluation = cli._selective_surfacing_evaluation_payload(
        projection_payload=broken_projection,
        compact_projection=compact,
        cli_invoke=config.cli_invoke,
    )
    missing_checks = {check["id"]: check for check in missing_evaluation["checks"]}
    assert missing_checks["required-guidance-present"]["result"] == "fail"
    assert missing_checks["required-guidance-present"]["evidence"] == ["broken:row"]
    assert missing_evaluation["finding_routing"]["rule"].startswith("Route failed checks")


def test_improvement_intake_includes_repair_recurrence_subtype(capsys) -> None:
    assert cli.main(["defaults", "--verbose", "--section", "improvement_intake", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    subtypes = {item["id"]: item for item in payload["answer"]["payload"]["subtypes"]}
    repair = subtypes["repair_recurrence"]
    assert repair["source"] == "doctor.repair_actions or doctor.manual_review_actions"
    assert repair["selector"] == "agentic-workspace defaults --section repair_recovery --format json"
    assert "affordance" in repair["correct_by_design_remedies"]


def test_summary_task_scoped_profile_omits_historical_audit_detail(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--modules", "planning", "--format", "json"]) == 0
    capsys.readouterr()
    assert (
        cli.main(
            [
                "summary",
                "--target",
                str(target),
                "--task",
                "Implement adaptive read action routing",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-task"
    assert payload["task_scope"]["task_text_available"] is True
    assert payload["task_scope"]["changed_paths"] == ["generated/workspace/python/cli.py"]
    assert "detail_commands" in payload
    assert "historical_audit_pressure" not in payload
    assert payload["omitted_context"]["historical_audit_pressure"].startswith("not relevant")


def test_adaptive_assurance_end_to_end_closeout_flow(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "test_access_control.py", "def test_access_control_fixture():\n    assert True\n")
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
                "--verbose",
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
    record["canonical_core"]["next_action"] = "canonical core next action."
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

    assert summary["planning_record"]["next_action"] == "canonical core next action."
    assert summary["resumable_contract"]["current_next_action_source"] == "canonical_core.next_action"
    assert any(
        warning["warning_class"] == "execplan_canonical_projection_drift" for warning in summary["planning_surface_health"]["warnings"]
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
