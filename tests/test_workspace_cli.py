from __future__ import annotations

# ruff: noqa: F403,F405
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
    assert full["adapter_contracts"]


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
