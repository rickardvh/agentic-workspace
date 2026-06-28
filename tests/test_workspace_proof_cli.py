from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_proof_runtime_helpers_route_through_proof_owner(tmp_path: Path) -> None:
    assert workspace_runtime_primitives._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_primitives._tiny_proof_payload is workspace_runtime_proof._tiny_proof_payload
    assert workspace_runtime_primitives._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_primitives._active_planning_record_for_proof is workspace_runtime_proof._active_planning_record_for_proof
    assert workspace_runtime_implement._verification_report_payload is workspace_runtime_proof._verification_report_payload
    assert workspace_runtime_implement._tiny_proof_obligations_payload is workspace_runtime_proof._tiny_proof_obligations_payload
    assert workspace_runtime_core._active_planning_record_for_proof(target_root=tmp_path) == {
        "status": "unavailable",
        "reason": "planning state unavailable",
    }


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

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/proof-surfaces-contract.md"
    assert payload["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["default_routes"]["planning_surfaces"] == "agentic-workspace summary --target ./repo --format json"
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

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--route", "workspace_proof", "--format", "json"]) == 0

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

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"current": True}
    assert payload["answer"]["installed_modules"] == ["planning"]
    assert payload["answer"]["status_health"] == "healthy"


def test_proof_route_selector_smoke_works_without_mocked_lifecycle(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--modules", "planning"]) == 0
    capsys.readouterr()

    assert cli.main(["proof", "--verbose", "--target", str(target), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["answer"]["id"] == "workspace_proof"
    assert payload["answer"]["command"] == "agentic-workspace proof --target ./repo --format json"


def test_proof_changed_selector_returns_path_based_validation_lane(capsys) -> None:
    assert cli.main(["proof", "--verbose", "--changed", ".agentic-workspace/planning/state.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"changed": [".agentic-workspace/planning/state.toml"]}
    answer = payload["answer"]
    assert answer["kind"] == "proof-selection/v1"
    assert answer["selected_lanes"][0]["id"] == "planning_surfaces"
    assert answer["required_commands"] == [
        f"{REPO_LOCAL_CLI_INVOKE} summary --target . --format json",
        f"{REPO_LOCAL_CLI_INVOKE} doctor --target . --modules planning --format json",
    ]
    assert answer["validation_plan"]["kind"] == "validation-plan/v1"
    assert answer["validation_plan"]["status"] == "inspect-before-run"
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["order"] == 1
    assert first_step["command"] == f"{REPO_LOCAL_CLI_INVOKE} summary --target . --format json"
    assert first_step["cwd"] == "."
    assert first_step["run"] == f"{REPO_LOCAL_CLI_INVOKE} summary --target . --format json"
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


def test_proof_routine_context_surfaces_workflow_obligation_match(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[workflow_obligations.workspace_closeout]
summary = "Run workspace closeout checks."
stage = "closeout"
force = "required-before-closeout"
scope_tags = ["workspace"]
commands = ["agentic-workspace report --target . --section closeout_trust --format json"]
review_hint = "Workspace orchestration applies to workspace paths."
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    routine = answer["routine_work_context"]
    assert routine["surface"] == "proof"
    assert routine["categories"]["authority"]["status"] == "attention"
    assert routine["categories"]["authority"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["categories"]["evidence_proof"]["status"] == "attention"
    assert routine["categories"]["evidence_proof"]["signals"]["workflow_obligation_matches"] == 1
    assert routine["knowledge_authority_review"]["workflow_obligation_match_count"] == 1


def test_proof_routes_changed_path_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_runbook_review.py", "def test_runbook_review_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.runbook_walkthrough]
protocol_id = "runbook_review"
title = "Runbook walkthrough"
steps = ["Review the recovery runbook"]
expected_observations = ["Recovery steps and owner are visible"]
pass_evidence_labels = ["manual_runbook_review"]
fail_evidence_labels = ["runbook_gap"]

[protocols.runbook_review]
title = "Runbook review"
purpose = "Manual verification for runbook changes."
applies_to_paths = ["docs/runbooks/**"]
scenario_refs = ["runbook_walkthrough"]
steps = ["Run the runbook walkthrough"]
expected_evidence = ["manual_runbook_review"]
review_owner = "ops-review"
review_aids = ["Record observations in the closeout evidence."]

[proof_routes.runbook_review_route]
protocol_refs = ["runbook_review"]
scenario_refs = ["runbook_walkthrough"]
commands = ["uv run pytest tests/test_runbook_review.py"]
review_aids = ["Record route-specific proof notes."]
proof_lane_hint = "runbook-verification"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbooks/recovery.md",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_count"] == 1
    assert answer["verification"]["evidence_status"][0]["state"] == "missing-evidence"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "verification:runbook_review" in lanes
    assert lanes["verification:runbook_review"]["verification_scenario_refs"] == ["runbook_walkthrough"]
    assert lanes["verification:runbook_review"]["verification_proof_route_ids"] == ["runbook_review_route"]
    assert lanes["verification:runbook_review"]["required_commands"] == ["uv run pytest tests/test_runbook_review.py"]
    assert answer["routine_work_context"]["categories"]["evidence_proof"]["signals"]["active_verification_protocols"] == 1


def test_proof_routes_active_assurance_requirement_to_verification_protocol(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "tests" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/test_privacy.py"]
review_aids = ["Review privacy data handling manually."]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["src/privacy/**"]
required_evidence = ["manual_privacy_review"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
review_owner = "privacy-review"
""",
    )
    _write(
        tmp_path / ".agentic-workspace/verification/manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[protocols.privacy_manual_review]
title = "Privacy manual review"
purpose = "Repeatable review protocol for privacy-sensitive code."
applies_to_paths = ["src/privacy/**"]
assurance_requirement_refs = ["privacy_data"]
proof_profiles = ["privacy"]
expected_evidence = ["manual_privacy_review"]
review_owner = "privacy-review"
review_aids = ["Confirm data minimisation and retention assumptions."]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/privacy/export.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["verification"]["active_protocols"][0]["id"] == "privacy_manual_review"
    lanes = {lane["id"]: lane for lane in answer["selected_lanes"]}
    assert "assurance-requirement:privacy_data" in lanes
    assert "verification:privacy_manual_review" in lanes
    status = answer["assurance_requirements"]["evidence_status"][0]
    assert status["verification_protocols"][0]["protocol_id"] == "privacy_manual_review"
    assert status["verification_missing_evidence"] == ["manual_privacy_review"]


def test_proof_accumulates_repeated_changed_flags(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["answer"]["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_proof_cli.py",
    ]


def test_proof_tiny_profile_returns_next_validation_action(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    assert payload["kind"] == "proof-next-decision/v1"
    assert set(payload) <= {
        "kind",
        "target",
        "selector",
        "sufficiency",
        "next",
        "required_commands",
        "proof_command_adjustments",
        "unavailable_proof_commands",
        "proof_strategy",
        "target_proof_capabilities",
        "manual_verification",
        "warnings",
        "intent_proof",
        "detail_command",
        "proof_route_selection",
    }
    assert payload["selector"] == {"changed": ["generated/workspace/python/cli.py"]}
    assert payload["next"]["action"] == "run-validation-command"
    assert payload["next"]["command"] == "make test-workspace"
    assert "make lint-workspace" in payload["required_commands"]
    assert payload["warnings"] == []
    assert "answer" not in payload
    assert "selected_lanes" not in encoded
    assert "validation_plan" not in encoded
    assert len(encoded) < 2700


def test_proof_changed_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n\nmaintainer-surfaces:\n\ttrue\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["make test", "make lint"]
    assert payload["next"]["command"] == "make test"
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["next"]["why"] == "behavior-test intent selected live-adapted-target-capability."
    assert payload["proof_route_selection"]["selected_command"] == {
        "command": "make test",
        "lane": "workspace_cli",
        "route_source": "live-adapted-target-capability",
        "intent_type": "behavior-test",
    }
    assert payload["proof_route_selection"]["route_source"] == "live-adapted-target-capability"
    assert payload["proof_route_selection"]["manual_fallback"] is None
    assert payload["proof_route_selection"]["explanation_field"] == "proof_route_explanation"
    assert "next_action" not in payload["proof_route_selection"]
    assert "required_commands" not in payload["proof_route_selection"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "make test",
            "reason": "target Makefile does not define 'test-workspace'; using available 'test' target",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "make lint",
            "reason": "target Makefile does not define 'lint-workspace'; using available 'lint' target",
        },
    ]
    assert payload["target_proof_capabilities"]["make"]["targets"] == ["lint", "maintainer-surfaces", "test"]


def test_proof_changed_does_not_assume_makefile_exists(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == []
    assert payload["next"]["action"] == "manual-verification"
    assert payload["next"]["command"] is None
    assert payload["proof_route_selection"]["manual_fallback"]["status"] == "required"
    assert payload["proof_route_selection"]["manual_fallback"]["unavailable_command_count"] == 0
    assert payload["proof_route_selection"]["selected_command"] is None
    assert payload["proof_route_selection"]["route_source"] == "manual-fallback"
    assert payload["manual_verification"]["status"] == "required"
    assert "no executable proof route" in payload["manual_verification"]["summary"]
    assert payload.get("unavailable_proof_commands", []) == []
    assert payload["warnings"] == []
    assert payload["manual_verification"]["status"] == "required"


def test_proof_changed_reports_manual_verification_templates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    templates = payload["manual_verification"]["templates"]
    assert templates == [
        {
            "kind": "manual-verification-template/v1",
            "intent_type": "behavior-test",
            "title": "Behavior verification",
            "trust": "lower-than-executable-proof",
            "checklist": [
                "Identify the behavior the changed paths are expected to affect.",
                "Inspect the implementation path and the user-visible or API-facing result.",
                "Exercise the smallest available manual scenario or explain why no scenario is available.",
            ],
            "evidence_to_record": [
                "changed behavior inspected",
                "scenario or reasoning used",
                "residual risk compared with executable tests",
            ],
        }
    ]


def test_proof_verbose_exposes_manual_fallback_decision_layers(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["proof_route_selection"] == answer["proof_route_decision"]
    decision = answer["proof_route_selection"]
    assert decision["next_action"]["action"] == "manual-verification"
    assert decision["selected_command"] is None
    assert decision["manual_fallback"]["status"] == "required"
    assert decision["manual_fallback"]["unavailable_command_count"] == 0
    assert decision["critical_warnings"] == []
    explanation = answer["proof_route_explanation"]
    assert explanation["selected_commands"] == []
    assert explanation["unavailable_commands"] == []
    assert explanation["manual_verification"]["status"] == "required"
    assert explanation["manual_verification"]["templates"][0]["intent_type"] == "behavior-test"
    assert explanation["manual_verification"]["templates"][0]["trust"] == "lower-than-executable-proof"
    assert explanation["proof_execution_evidence"] == {
        "kind": "proof-execution-evidence/v1",
        "status": "not-run",
        "state_model": ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"],
        "expected_commands": [],
        "manual_verification_expected": True,
        "rule": "Proof selection describes expected proof only; closeout must record what actually ran, failed, was skipped, or was manually verified.",
    }


def test_proof_changed_uses_target_package_json_scripts_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["npm test", "npm run lint"]
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["target_proof_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "npm test",
            "reason": "target repo has no Makefile; using package.json script for 'test' proof",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "npm run lint",
            "reason": "target repo has no Makefile; using package.json script for 'lint' proof",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_uses_subrepo_makefile_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/other", "packages/planning"]\n')
    _write(tmp_path / "packages" / "other" / "Makefile", "test:\n\tfalse\n\nlint:\n\tfalse\n")
    _write(
        tmp_path / "packages" / "planning" / "Makefile",
        "test:\n\tpytest\n\nlint:\n\truff check .\n\ntypecheck:\n\tmypy src\n",
    )
    _write(tmp_path / "packages" / "planning" / "src" / "repo_planning_bootstrap" / "installer.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "cd packages/planning && make test",
        "cd packages/planning && make lint",
        "cd packages/planning && make typecheck",
    ]
    assert answer["target_proof_capabilities"]["make"] == {"available": False, "targets": []}
    project_roots = {project_root["path"]: project_root for project_root in answer["target_proof_capabilities"]["project_roots"]}
    assert project_roots["packages/other"]["changed_path_matched"] is False
    assert project_roots["packages/planning"]["changed_path_matched"] is True
    assert project_roots["packages/planning"]["make"]["targets"] == ["lint", "test", "typecheck"]
    assert "cd packages/planning && make test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert "cd packages/planning && make typecheck" in answer["target_proof_capabilities"]["candidate_commands"]
    assert (
        answer["selected_commands"][0].items()
        >= {
            "kind": "proof-command/v1",
            "command": "cd packages/planning && make test",
            "cwd": "packages/planning",
            "run": "make test",
            "selected_from": "live-adapted-target-capability",
            "intent_type": "behavior-test",
            "lane": "planning_package",
            "required": True,
        }.items()
    )
    assert answer["selected_commands"][0]["execution_mode"] == "parallel-ok"
    assert answer["proof_route_selection"]["selected_command"] == {
        "command": "cd packages/planning && make test",
        "lane": "planning_package",
        "route_source": "live-adapted-target-capability",
        "intent_type": "behavior-test",
        "cwd": "packages/planning",
        "run": "make test",
    }
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["command"] == "cd packages/planning && make test"
    assert first_step["cwd"] == "packages/planning"
    assert first_step["run"] == "make test"
    assert answer["validation_plan"]["required"][2]["command"] == "cd packages/planning && make typecheck"
    assert answer.get("manual_verification") is None


def test_proof_changed_uses_subrepo_package_json_for_package_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "pyproject.toml", '[tool.uv.workspace]\nmembers = ["packages/ui"]\n')
    _write(tmp_path / "packages" / "ui" / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(tmp_path / "packages" / "ui" / "src" / "index.ts", "export const value = 1;\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "packages/ui/src/index.ts", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["cd packages/ui && npm test", "cd packages/ui && npm run lint"]
    assert payload["next"]["command"] == "cd packages/ui && npm test"
    assert payload["next"]["cwd"] == "packages/ui"
    assert payload["next"]["run"] == "npm test"
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "cd packages/ui && npm test",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'test' proof in packages/ui",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "cd packages/ui && npm run lint",
            "replacement_cwd": "packages/ui",
            "source_path": "packages/ui/package.json",
            "reason": "target repo has no root Makefile; using subrepo package.json script for 'lint' proof in packages/ui",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_treats_plain_python_project_as_discovery_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["agentic-workspace"]
""",
    )
    _write(tmp_path / "uv.lock", "# lock\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "pyproject.toml", "uv.lock", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest" not in answer["required_commands"]
    assert answer["manual_verification"]["status"] == "required"
    pytest_capability = answer["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "candidate"
    assert pytest_capability["authority"] == "candidate-discovery"
    assert answer["target_proof_capabilities"]["role_commands"] == {}
    learning = answer["host_repo_learning"]
    assert learning["authority_rule"].startswith("Host-repo heuristics may propose discovery candidates")
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["negative_evidence"]["items"] == []
    assert answer["unavailable_commands"] == []


def test_proof_changed_uses_declared_pytest_dependency_as_confirmed_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = ["pytest>=8"]
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "pyproject.toml", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "uv run pytest" in payload["required_commands"]
    pytest_capability = payload["target_proof_capabilities"]["python"]["pytest"]
    assert pytest_capability["status"] == "confirmed"
    assert pytest_capability["evidence"] == [
        {"state": "confirmed", "source": "declared-dependency", "path": "pyproject.toml:project.dependencies"}
    ]


def test_proof_changed_uses_python_pytest_capability_without_makefile(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "pyproject.toml",
        """
[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
""",
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["uv run pytest", "uv run ruff check ."]
    assert payload["target_proof_capabilities"]["python"]["available"] is True
    assert payload["target_proof_capabilities"]["python"]["pytest"]["status"] == "confirmed"
    assert payload["target_proof_capabilities"]["python"]["pytest"]["authority"] == "confirmed-repo-evidence"
    assert payload["target_proof_capabilities"]["role_commands"] == {
        "test": ["uv run pytest"],
        "lint": ["uv run ruff check ."],
    }
    assert payload["proof_command_adjustments"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "replacement": "uv run pytest",
            "reason": "target repo has no Makefile; using detected 'test' proof capability",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "replacement": "uv run ruff check .",
            "reason": "target repo has no Makefile; using detected 'lint' proof capability",
        },
    ]
    assert payload["manual_verification"] is None


def test_proof_changed_reports_rust_go_and_java_capability_candidates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Cargo.toml", '[package]\nname = "demo"\nversion = "0.1.0"\n')
    _write(tmp_path / "go.mod", "module example.com/demo\n")
    _write(tmp_path / "pom.xml", "<project />\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "docs/notes.md", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    capabilities = answer["target_proof_capabilities"]
    assert capabilities["rust"]["available"] is True
    assert capabilities["go"]["available"] is True
    assert capabilities["java"]["available"] is True
    assert capabilities["role_commands"]["test"] == ["cargo test", "go test ./...", "mvn test"]
    assert capabilities["role_commands"]["lint"] == ["cargo clippy --all-targets --all-features", "go vet ./..."]
    assert "cargo test" in capabilities["candidate_commands"]
    assert "go vet ./..." in capabilities["candidate_commands"]
    assert "mvn test" in capabilities["candidate_commands"]


def test_proof_changed_reports_live_confirmed_learned_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                    {
                        "id": "package-json:stale",
                        "intent_type": "static-check",
                        "candidate_command": "npm run stale",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    },
                ],
            }
        ),
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["status"] == "loaded"
    assert hints["confirmed"][0]["candidate_command"] == "npm test"
    assert hints["confirmed"][0]["confirmation"] == "live-confirmed"
    assert hints["stale"][0]["candidate_command"] == "npm run stale"
    assert hints["stale"][0]["confirmation"] == "stale-or-unavailable"
    assert hints["lifecycle"]["state_counts"] == {
        "candidate": 2,
        "confirmed": 0,
        "invalid-authority": 0,
        "negative": 0,
        "stale": 0,
        "superseded": 0,
    }
    assert hints["lifecycle"]["bucket_counts"]["confirmed"] == 1
    assert "invalid-authority" in {state["state"] for state in hints["lifecycle"]["state_model"]}
    decision = answer["proof_route_selection"]
    assert decision["critical_warnings"] == ["1 learned route hint(s) are stale or unavailable."]
    assert decision["selected_command"]["command"] == "npm test"
    explanation = answer["proof_route_explanation"]
    assert explanation["proof_intents"][0]["kind"] == "proof-intent/v1"
    assert explanation["target_capabilities"]["package_json"]["scripts"] == ["lint", "test"]
    assert explanation["setup_adopt_route_learning"] == {
        "kind": "setup-adopt-proof-route-learning/v1",
        "status": "advisory-hints-loaded",
        "persistent_surface": ".agentic-workspace/proof-route-hints.json",
        "hint_count": 2,
        "confirmed_count": 1,
        "stale_count": 1,
        "negative_count": 0,
        "superseded_count": 0,
        "invalid_authority_count": 0,
        "lifecycle_field": "learned_route_hints.lifecycle",
        "route_map_decision": "use-advisory-hints-only",
        "reason": (
            "Setup/adopt-discovered route hints are persisted as advisory memory and must be live-confirmed before command selection."
        ),
        "separation": {
            "configured_policy": "host-owned proof profiles and disallowed commands",
            "live_target_capabilities": "current Makefile, package.json, language, and role-command discovery",
            "setup_adopt_learning": "advisory route hints from lifecycle discovery, never host policy",
        },
    }
    assert explanation["selected_commands"][0]["kind"] == "proof-command/v1"
    assert explanation["proof_execution_evidence"]["status"] == "not-run"
    assert answer["proof_next_decision"]["warnings"] == ["1 learned route hint(s) are stale or unavailable."]


def test_proof_changed_reuses_confirmed_memory_proof_route(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"src","owner":"Memory","provenance":"manual verification passed on 2026-06-02","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["source_counts"]["memory"] == 1
    assert hints["confirmed"][0]["candidate_command"] == "python -m compileall src"
    assert hints["confirmed"][0]["confirmation"] == "learned-confirmed"
    assert answer["proof_route_selection"]["selected_command"]["command"] == "python -m compileall src"
    assert answer["proof_route_selection"]["selected_command"]["route_source"] == "live-adapted-target-capability"
    reliance = answer["proof_route_selection"]["learned_route_reliance"]
    assert reliance["status"] == "present"
    assert reliance["material_to_required_proof"] is True
    assert reliance["items"][0]["command"] == "python -m compileall src"
    assert reliance["items"][0]["provenance"] == "manual verification passed on 2026-06-02"
    assert answer["proof_route_selection"]["closeout_disclosure"]["status"] == "required"
    assert answer["proof_route_explanation"]["learned_route_reliance"] == reliance
    learning = answer["host_repo_learning"]
    assert learning["confirmed_evidence"]["status"] == "present"
    assert "memory capture-note" in learning["confirmed_evidence"]["items"][0]["capture"]["command_to_run"]
    assert learning["actionable_next_steps"]["memory_note_entries"][0].startswith("agentic-workspace-proof-route:")


def test_proof_changed_memory_negative_route_suppresses_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "pytest"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test failed because pytest is not installed","learned_at":"2026-06-02"}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["negative"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["required_commands"] == []
    assert answer["proof_route_selection"]["selected_command"] is None
    assert answer["proof_route_selection"]["critical_warnings"] == ["1 learned negative route(s) suppressed candidate proof commands."]
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "present"
    assert learning["negative_evidence"]["items"][0]["command"] == "npm test"
    assert learning["actionable_next_steps"]["status"] == "present"


def test_proof_changed_reports_proof_route_lifecycle_states(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Proof route lifecycle

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"static-check","candidate_command":"npm run lint","source":"memory","confidence":"high","requires_live_confirmation":false,"scope":"repo","owner":"Memory","provenance":"lint route confirmed in prior closeout","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"stale","intent_type":"behavior-test","candidate_command":"npm run old-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"old route was not found during setup","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"npm test invokes the wrong runner","learned_at":"2026-06-02"}
agentic-workspace-proof-route: {"state":"superseded","intent_type":"behavior-test","candidate_command":"npm run legacy-test","source":"memory","confidence":"medium","requires_live_confirmation":true,"scope":"repo","owner":"Memory","provenance":"legacy route replaced by package lint route","learned_at":"2026-06-02","superseded_by":"npm run lint"}
agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"npm run missing-owner","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    lifecycle = hints["lifecycle"]
    assert lifecycle["state_counts"] == {
        "candidate": 0,
        "confirmed": 1,
        "invalid-authority": 1,
        "negative": 1,
        "stale": 1,
        "superseded": 1,
    }
    assert lifecycle["bucket_counts"] == {
        "confirmed": 1,
        "stale": 1,
        "negative": 1,
        "superseded": 1,
        "invalid": 1,
    }
    assert hints["confirmed"][0]["candidate_command"] == "npm run lint"
    assert hints["negative"][0]["candidate_command"] == "npm test"
    assert hints["superseded"][0]["superseded_by"] == "npm run lint"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert "npm test" not in answer["target_proof_capabilities"]["candidate_commands"]
    warnings = answer["proof_next_decision"]["warnings"]
    assert "1 learned route lesson(s) are missing authoritative provenance metadata." in warnings
    assert "1 learned route hint(s) are stale or unavailable." in warnings
    assert "1 learned negative route(s) suppressed candidate proof commands." in warnings


def test_proof_changed_incomplete_confirmed_memory_route_is_not_authoritative(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "app.py", "print('ok')\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "proof-routes.md",
        """
# Incomplete proof routes

agentic-workspace-proof-route: {"state":"confirmed","intent_type":"behavior-test","candidate_command":"python -m compileall src","source":"memory","confidence":"high","requires_live_confirmation":false}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.py", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["confirmed"] == []
    assert hints["invalid"][0]["original_state"] == "confirmed"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert hints["lifecycle"]["state_counts"]["invalid-authority"] == 1
    assert set(hints["invalid"][0]["missing_fields"]) == {"owner", "scope", "provenance", "learned_at"}
    assert answer["required_commands"] == []
    assert answer["proof_route_selection"]["selected_command"] is None
    learning = answer["host_repo_learning"]
    assert learning["invalid_learning_evidence"]["status"] == "present"
    assert (
        "candidate_command, state, intent_type, owner, scope, provenance, and learned_at" in learning["invalid_learning_evidence"]["rule"]
    )
    assert "recapture this proof-route lesson" in learning["invalid_learning_evidence"]["items"][0]["recovery"]


def test_proof_changed_incomplete_negative_memory_route_does_not_suppress_candidate(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run"}}))
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "proof-routes.md",
        """
# Incomplete failed proof routes

agentic-workspace-proof-route: {"state":"negative","intent_type":"behavior-test","candidate_command":"npm test","source":"memory","confidence":"high","requires_live_confirmation":true}
""",
    )

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    hints = answer["learned_route_hints"]
    assert hints["negative"] == []
    assert hints["invalid"][0]["original_state"] == "negative"
    assert hints["invalid"][0]["state"] == "invalid-authority"
    assert "npm test" in answer["target_proof_capabilities"]["candidate_commands"]
    assert answer["proof_route_selection"]["selected_command"]["command"] == "npm test"
    learning = answer["host_repo_learning"]
    assert learning["negative_evidence"]["status"] == "none"
    assert learning["invalid_learning_evidence"]["items"][0]["command"] == "npm test"


def test_proof_changed_host_policy_disallows_generic_discovered_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _init_git_repo(tmp_path)
    _write(tmp_path / "package.json", json.dumps({"scripts": {"test": "vitest run", "lint": "eslint ."}}))
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.no_npm_test]
required_commands = []
optional_commands = []
review_aids = []
disallowed_commands = ["npm test"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "proof-route-hints.json",
        json.dumps(
            {
                "kind": "agentic-workspace/proof-route-hints/v1",
                "schema_version": "proof-route-hints/v1",
                "source": "lifecycle-discovery",
                "rule": "Advisory proof route hints are not host policy; proof selection must live-confirm them before emitting commands.",
                "hints": [
                    {
                        "id": "package-json:test",
                        "intent_type": "behavior-test",
                        "candidate_command": "npm test",
                        "source": "package-json",
                        "source_path": "package.json",
                        "confidence": "medium",
                        "requires_live_confirmation": True,
                    }
                ],
            }
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.plan.json", why_now = "prove host policy precedence." },
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
        why_now="prove host policy precedence.",
        next_action="run proof selection.",
        done_when="host policy blocks disallowed command.",
    )
    record["adaptive_assurance"] = {
        "level": "medium",
        "reason": "host disallows npm test",
        "proof_profiles": ["no_npm_test"],
    }
    planning_installer._write_execplan_record(record_path=record_path, record=record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "src/app.ts", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["learned_route_hints"]["confirmed"][0]["candidate_command"] == "npm test"
    assert "npm test" not in answer["required_commands"]
    assert "npm run lint" in answer["required_commands"]
    assert answer["configured_policy"][0]["disallowed_commands"] == ["npm test"]
    assert answer["host_policy_blocked_commands"] == [
        {
            "lane": "concern:no_npm_test",
            "proof_profile": "no_npm_test",
            "command": "npm test",
            "configured_command": "npm test",
            "reason": "host-configured proof profile disallows this command",
            "selected_by_lane": "workspace_cli",
        }
    ]
    assert answer["proof_route_selection"]["critical_warnings"] == ["Host proof policy blocked one or more candidate proof commands."]
    assert answer["proof_route_explanation"]["host_policy_blocked_commands"] == answer["host_policy_blocked_commands"]
    assert answer["proof_next_decision"]["warnings"] == ["Host proof policy blocked one or more candidate proof commands."]


def test_proof_verbose_explains_live_discovery_when_no_setup_adopt_route_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    learning = answer["proof_route_explanation"]["setup_adopt_route_learning"]
    assert learning["status"] == "live-discovery-sufficient"
    assert learning["hint_count"] == 0
    assert learning["route_map_decision"] == "no-persisted-route-map-needed"
    assert "live target capability discovery is sufficient" in learning["reason"]
    assert learning["separation"]["setup_adopt_learning"] == "advisory route hints from lifecycle discovery, never host policy"


def test_proof_changed_validation_plan_uses_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

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

    payload = json.loads(capsys.readouterr().out)
    step = payload["answer"]["validation_plan"]["required"][0]
    expected_target = tmp_path.as_posix()
    assert step["command"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'
    assert step["run"] == f'uv run agentic-workspace summary --target "{expected_target}" --format json'


def test_proof_tiny_detail_commands_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["detail_command"].startswith("uv run agentic-workspace proof ")
    assert payload["next"]["command"] is None or not payload["next"]["command"].startswith("agentic-workspace ")


def test_proof_changed_includes_active_assurance_concern_profiles(tmp_path: Path, capsys) -> None:
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


def test_proof_changed_includes_matched_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_privacy.sql",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["changed path matched db/migrations/**"]


def test_proof_changed_marks_missing_path_specific_proof_unavailable(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" not in answer["required_commands"]
    assert answer["unavailable_proof_commands"] == [
        {
            "lane": "assurance-requirement:model_harness",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["unavailable_commands"] == [
        {
            "kind": "proof-command-unavailable/v1",
            "command": "uv run pytest tests/test_model_cli_harness.py -q",
            "lane": "assurance-requirement:model_harness",
            "reason": "selected proof command references path-like arguments absent from the target repo",
            "missing_paths": "tests/test_model_cli_harness.py",
        }
    ]
    assert answer["manual_verification"]["status"] == "required"
    assert answer["manual_verification"]["unavailable_commands"] == answer["unavailable_commands"]


def test_proof_changed_keeps_existing_path_specific_proof_required(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "test_model_cli_harness.py", "def test_harness_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.model_harness]
required_commands = ["uv run pytest tests/test_model_cli_harness.py -q"]

[assurance.requirements.model_harness]
level = "medium"
applies_to_paths = ["scripts/model_cli_harness/**"]
authority_refs = ["docs/maintainer/test-knowledge-inventory.md"]
required_evidence = ["current harness proof selected"]
proof_profile = "model_harness"
force = "required-before-closeout"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "scripts/model_cli_harness/run_model_cli_harness.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/test_model_cli_harness.py -q" in answer["required_commands"]
    assert answer.get("unavailable_proof_commands", []) == []


def test_proof_changed_includes_matched_subsystem_assurance_profile(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "tests" / "audit" / "test_audit.py", "def test_audit_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
[[subsystems]]
id = "audit-log"
paths = ["src/audit/**"]
owns = ["audit trail semantics"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.audit]
required_commands = ["uv run pytest tests/audit -q"]
optional_commands = ["uv run pytest tests/audit_integration -q"]
review_aids = ["docs/reviews/audit.md"]

[assurance.subsystem_profiles.audit-log]
assurance_level = "high"
requirement_refs = ["docs/system-requirements.md#auditability"]
required_evidence = ["requirement_grounding", "manual_review"]
proof_profile = "audit"
force = "required-before-closeout"
blocked_without_evidence = ["auditability-complete"]
claim_boundary = "subsystem-scoped"
""",
    )

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "src/audit/events.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/audit -q" in answer["required_commands"]
    assert "uv run pytest tests/audit_integration -q" in answer["optional_commands"]
    subsystem = answer["assurance_requirements"]["subsystem_assurance"]
    assert subsystem["matched_subsystem_ids"] == ["audit-log"]
    assert subsystem["effective_assurance_level"] == "high"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "subsystem:audit-log"][0]
    assert lane["proof_profile"] == "audit"
    assert lane["applies_because"] == ["changed path matched subsystem audit-log"]


def test_proof_current_includes_active_planning_assurance_requirement_profile(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(tmp_path / "tests" / "privacy" / "test_privacy.py", "def test_privacy_fixture():\n    assert True\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        """
schema_version = 1

[assurance.proof_profiles.privacy]
required_commands = ["uv run pytest tests/privacy -q"]
optional_commands = ["uv run pytest tests/privacy_integration -q"]
review_aids = ["docs/compliance/privacy.md"]

[assurance.requirements.privacy_data]
level = "high"
applies_to_planning_refs = ["privacy_data"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "privacy-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/privacy-plan.plan.json", why_now = "prove privacy requirement." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Privacy Plan",
        item_id="privacy-plan",
        status="in-progress",
        why_now="prove privacy requirement.",
        next_action="run proof selection.",
        done_when="privacy proof appears.",
    )
    record["adaptive_assurance"] = {
        "level": "high",
        "requirement_refs": ["privacy_data"],
        "strict_closeout": True,
    }
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "privacy-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert "uv run pytest tests/privacy -q" in answer["required_commands"]
    assert "uv run pytest tests/privacy_integration -q" in answer["optional_commands"]
    assert answer["assurance_requirements"]["active"][0]["id"] == "privacy_data"
    lane = [item for item in answer["selected_lanes"] if item.get("requirement_id") == "privacy_data"][0]
    assert lane["proof_profile"] == "privacy"
    assert lane["applies_because"] == ["planning ref matched privacy_data"]


def test_proof_current_selects_active_plan_validation_commands(tmp_path: Path, capsys) -> None:
    from repo_planning_bootstrap import installer as planning_installer

    _write(
        tmp_path / "tests" / "test_workspace_proof_cli.py",
        "def test_proof_current_selects_active_plan_validation_commands():\n    assert True\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
[todo]
active_items = [
  { id = "validation-plan", status = "in-progress", surface = ".agentic-workspace/planning/execplans/validation-plan.plan.json", why_now = "prove current validation routing." },
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    record = planning_installer._build_execplan_record_from_todo_item(
        title="Validation Plan",
        item_id="validation-plan",
        status="in-progress",
        why_now="prove current validation routing.",
        next_action="run proof selection.",
        done_when="current proof names the active validation commands.",
    )
    record["validation_commands"] = [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    _write_json(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "validation-plan.plan.json", record)

    assert cli.main(["proof", "--verbose", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    answer = json.loads(capsys.readouterr().out)["answer"]
    assert answer["required_commands"] == [
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    ]
    assert answer["selected_lanes"][0]["id"] == "planning:active_validation"
    assert "manual_verification" not in answer


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
  "selected-command",
  "run-command",
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
                {"command": "selected-command", "status": "selected", "evidence_ref": "local:selected"},
                {"command": "run-command", "status": "run", "evidence_ref": "local:run"},
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

    evidence = json.loads(capsys.readouterr().out)["answer"]["planning_assurance"]["trust_state"]["proof_execution_evidence"]
    assert evidence["state_model"] == ["selected", "run", "passed", "failed", "skipped", "unavailable", "waived", "missing"]
    assert evidence["counts"] == {
        "selected": 1,
        "run": 1,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "unavailable": 1,
        "waived": 1,
        "missing": 2,
    }
    assert evidence["lower_trust_required_count"] == 7
    selected = next(item for item in evidence["commands"] if item["command"] == "selected-command")
    assert selected["trust"] == "lower-trust"
    run = next(item for item in evidence["commands"] if item["command"] == "run-command")
    assert run["trust"] == "lower-trust"
    waived = next(item for item in evidence["commands"] if item["command"] == "waived-command")
    assert waived["trust"] == "satisfied"
    assert waived["waiver_state"] == "waived-with-reason"


def test_proof_changed_selector_routes_agent_aid_changes_to_manifest_lane(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
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


def test_proof_changed_selector_routes_readme_to_docs_review(capsys) -> None:
    assert cli.main(["proof", "--verbose", "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert answer["required_commands"] == [docs_diff]
    assert answer["selected_lanes"][0]["non_local_references"] == ["https://github.com/rickardvh/command-generation/blob/main/README.md"]
    assert "https://github.com" not in answer["required_commands"][0]
    assert "uv run pytest tests -q" not in answer["required_commands"]
    assert answer["surface_value_review"]["reviewed_paths"][0]["surface_class"] == "adapter_or_repo_intent_surface"


def test_proof_changed_selector_routes_package_readmes_to_docs_review(capsys) -> None:
    assert cli.main(["proof", "--verbose", "--changed", "packages/planning/README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert "make test-planning" not in answer["required_commands"]
    assert "git diff -- README.md docs .agentic-workspace/docs" in answer["required_commands"][0]


def test_proof_record_receipt_writes_latest_execution_evidence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "passed",
                "--receipt-plan",
                "plan-alpha",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["status"] == "written"
    assert payload["path"] == ".agentic-workspace/local/proof-receipts/last.json"
    assert receipt["command"] == "uv run pytest tests/test_workspace_proof_cli.py -q"
    assert receipt["result"] == "passed"
    assert receipt["changed_paths"] == ["tests/test_workspace_proof_cli.py"]
    assert receipt["plan_id"] == "plan-alpha"
    assert "repair_retry_ladder" not in receipt
    assert "repair_retry_ladder" not in payload


def test_proof_failed_receipt_includes_repair_retry_ladder(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    ladder = payload["repair_retry_ladder"]
    written_ladder = receipt["repair_retry_ladder"]
    assert ladder == written_ladder
    assert ladder["kind"] == "agentic-workspace/proof-repair-retry-ladder/v1"
    assert ladder["trigger"] == "failed-proof-receipt"
    assert ladder["failed_command"] == "make test-workspace"
    assert ladder["full_selected_proof"] == "make test-workspace"
    assert ladder["full_proof_still_required"] is True
    assert ladder["full_rerun_premature"] is True
    assert ladder["focused_commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][0]["commands"] == ["uv run pytest tests/test_workspace_proof_cli.py -q"]
    assert ladder["steps"][1]["command_source"] == "smallest affected package or workspace subset after the focused failure passes"
    assert ladder["steps"][2]["command"] == "make test-workspace"


def test_proof_failed_receipt_clusters_supplied_log(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".agentic-workspace").mkdir()
    (target / ".agentic-workspace" / "config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    log_path = target / ".agentic-workspace" / "local" / "proof-logs" / "workspace-test.log"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        "\n".join(
            [
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands - AssertionError",
                "FAILED tests/test_workspace_proof_generated_packages_cli.py::test_proof_changed_selector_routes_generated_command_packages - AssertionError",
                "=========================== short test summary info ===========================",
            ]
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "make test-workspace",
                "--receipt-result",
                "failed",
                "--receipt-log",
                ".agentic-workspace/local/proof-logs/workspace-test.log",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    receipt_path = target / ".agentic-workspace" / "local" / "proof-receipts" / "last.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    summary = payload["failure_summary"]
    assert summary == receipt["failure_summary"]
    assert summary["kind"] == "agentic-workspace/proof-failure-summary/v1"
    assert summary["failed_command"] == "make test-workspace"
    assert summary["log_source"]["path"] == ".agentic-workspace/local/proof-logs/workspace-test.log"
    assert summary["summary_trust"] == {
        "level": "higher",
        "source_kind": "repo-local-path",
        "rule": "Repo-local log references preserve audit access.",
    }
    assert summary["failure_line_count"] == 3
    assert summary["cluster_count"] == 2
    assert summary["top_root_cause_clusters"][0]["likely_root"] == "tests/test_workspace_proof_cli.py"
    assert summary["top_root_cause_clusters"][0]["occurrences"] == 2
    assert summary["focused_rerun_commands"][0] == (
        "uv run pytest tests/test_workspace_proof_cli.py::test_proof_current_selects_active_plan_validation_commands -q"
    )
    assert summary["full_suite_rerun_premature"] is True
    assert "Use the referenced full log" in summary["guardrails"][1]


def test_proof_failed_receipt_marks_excerpt_failure_summary_lower_trust(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "proof",
                "--target",
                str(target),
                "--changed",
                "tests/test_workspace_proof_cli.py",
                "--record-receipt",
                "--receipt-command",
                "uv run pytest tests/test_workspace_proof_cli.py -q",
                "--receipt-result",
                "failed",
                "--receipt-log",
                "FAILED tests/test_workspace_proof_cli.py::test_example - AssertionError",
                "--format",
                "json",
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)["failure_summary"]
    assert summary["log_source"]["kind"] == "caller-supplied-excerpt"
    assert summary["summary_trust"] == {
        "level": "lower",
        "source_kind": "caller-supplied-excerpt",
        "rule": "Caller-supplied excerpts are useful repair hints but lower trust than repo-local logs.",
    }


def test_proof_changed_selector_routes_installed_docs_to_docs_review(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                ".agentic-workspace/docs/agent-installation.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert ".agentic-workspace/docs" in answer["required_commands"][0]


def test_proof_changed_selector_reduces_package_docs_prefix_to_review(capsys) -> None:
    assert cli.main(["proof", "--verbose", "--changed", "packages/planning/docs/usage.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["routing_reductions"] == [
        {
            "path": "packages/planning/docs/usage.md",
            "from_lane": "planning_package",
            "to_lane": "repo_docs_review",
            "reason": (
                "Markdown-only package documentation edits use review proof unless behavior, generated payload, install contracts, "
                "or implementation semantics also changed."
            ),
        }
    ]


def test_proof_changed_selector_does_not_escalate_review_only_cross_lane_changes(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "packages/planning/README.md",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review", "contract_tooling"]
    assert {lane["proof_kind"] for lane in answer["selected_lanes"]} == {"diff-review", "surface-check"}
    assert not answer["escalate_when"] or not answer["escalate_when"][0].startswith("changed paths span multiple validation lanes")


def test_proof_changed_selector_includes_schema_reference_docs_for_workspace_schema(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "src/agentic_workspace/contracts/schemas/operation_primitives.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "contract_tooling" in lane_ids
    assert "schema_reference_docs" in lane_ids
    assert "make schema-reference-docs" in answer["required_commands"]
    schema_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "schema_reference_docs")
    assert schema_lane["matched_paths"] == ["src/agentic_workspace/contracts/schemas/operation_primitives.schema.json"]
    assert "generated docs/reference" in schema_lane["when"]
    options = {option["id"]: option for option in answer["completion_options"]}
    assert tuple(options) == (
        "run-proof",
        "claim-slice-complete",
        "claim-work-complete",
        "keep-parent-open",
        "close-parent-lane",
        "route-residue",
        "request-review",
        "stop-with-status",
    )
    assert options["run-proof"]["allowed"] is True
    assert options["claim-slice-complete"]["allowed"] is False
    assert "proof selection is not proof execution" in options["claim-slice-complete"]["why"]
    assert options["claim-work-complete"]["allowed"] is False
    assert options["close-parent-lane"]["allowed"] is False
    assert options["stop-with-status"]["allowed"] is True


def test_proof_changed_surfaces_compact_intent_proof_prompt(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)
    intent_proof = answer["intent_proof"]
    assert intent_proof["status"] == "needs-agent-judgment"
    assert intent_proof["regression_only_risk"] == "possible"
    assert intent_proof["suggested_dimensions"]
    assert "question" in intent_proof
    assert "proof strength" not in json.dumps(answer["required_commands"]).lower()


def test_proof_changed_verbose_surfaces_proof_confidence(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    proof_confidence = answer["proof_confidence"]
    assert proof_confidence["confidence"] == "needs-review"
    assert proof_confidence["claim_boundary"] == "slice"
    assert proof_confidence["proven_dimensions"] == []
    assert proof_confidence["unproven_dimensions"]
    assert "Selected proof" in proof_confidence["residual_risk"]
    proof_adequacy = answer["proof_adequacy"]
    assert proof_adequacy["protocol"] == "Proof Adequacy"
    assert proof_adequacy["proof_surface_role"] == "proof selects evidence for the claim; it does not close work by itself"
    assert proof_adequacy["implement_surface_role"].startswith("implement --changed carries changed-path work context")
    assert proof_adequacy["required_evidence"]["commands"] == answer["required_commands"]
    assert proof_adequacy["confidence_evidence"]["commands"] == answer["optional_commands"]
    assert "completion permission without closeout" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "semantic intent satisfaction" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert "parent issue, lane, or epic closure" in proof_adequacy["claim_boundary"]["does_not_authorize"]
    assert proof_adequacy["proof_confidence"]["claim_boundary"] == "slice"


def test_proof_changed_selector_includes_planning_schema_reference_wrapper(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/contracts/schemas/planning-execplan.schema.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_schema_reference_docs" in lane_ids
    assert "make check-planning" in answer["required_commands"]


def test_proof_changed_selector_includes_planning_source_typecheck_ci_parity(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    lane_ids = [lane["id"] for lane in answer["selected_lanes"]]
    assert "planning_package" in lane_ids
    assert "planning_source_typecheck_ci_parity" in lane_ids
    assert "make typecheck-planning" in answer["required_commands"]
    obligations = answer["proof_obligations"]
    assert obligations["required_proof"]["commands"] == answer["required_commands"]
    assert obligations["required_proof"]["status"] == "required"
    authority = {item["command"]: item for item in obligations["required_proof"]["command_authority"]}
    assert authority["make typecheck-planning"]["lane"] == "planning_source_typecheck_ci_parity"
    assert authority["make typecheck-planning"]["authority_source"]
    assert "agent still owns proof sufficiency" in authority["make typecheck-planning"]["rule"]
    assert obligations["recommended_confidence_checks"]["commands"] == answer["optional_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] != answer["required_commands"]
    assert "do not replace or relax required proof" in obligations["recommended_confidence_checks"]["rule"]
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["claim_boundary"]["completion_rule"] == obligations["completion_claim_rule"]
    assert answer["proof_adequacy"]["selected_lane_ids"][0] == "planning_package"
    assert obligations["compatibility"]["required_commands"] == "unchanged hard-gate field for existing callers"
    typecheck_lane = next(lane for lane in answer["selected_lanes"] if lane["id"] == "planning_source_typecheck_ci_parity")
    assert typecheck_lane["matched_paths"] == ["packages/planning/src/repo_planning_bootstrap/installer.py"]
    typecheck_step = next(step for step in answer["validation_plan"]["required"] if step["command"] == "make typecheck-planning")
    assert typecheck_step["lane_id"] == "planning_source_typecheck_ci_parity"
    typecheck_command = next(command for command in answer["selected_commands"] if command["command"] == "make typecheck-planning")
    assert typecheck_command["intent_type"] == "static-check"


def test_proof_changed_selector_flags_high_impact_skill_behavior_evidence(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "packages/planning/skills/planning-closeout-trust/SKILL.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    answer = json.loads(capsys.readouterr().out)["answer"]
    review = answer["skill_behavior_impact_review"]
    assert review["status"] == "behavior-evidence-required"
    assert review["high_impact_paths"] == ["packages/planning/skills/planning-closeout-trust/SKILL.md"]
    assert "What behavior is this skill meant to steer?" in review["required_answers"]
    assert "Tests passed, so completion is claimable." in json.dumps(answer["proof_strategy"]["anti_rationalization_gates"])


def test_proof_tiny_readme_profile_keeps_docs_only_validation_light(capsys) -> None:
    assert cli.main(["proof", "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    docs_diff = "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md"
    assert payload["kind"] == "proof-next-decision/v1"
    assert payload["next"]["command"] == docs_diff
    assert payload["required_commands"] == [docs_diff]
    assert "uv run pytest tests -q" not in encoded
    assert len(encoded) < 2500


def test_proof_changed_selector_flags_direct_cli_edits(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "workspace_cli",
        "cli_authority",
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    authority_review = answer["cli_authority_review"]
    assert authority_review["status"] == "blocked-direct-edit-route-to-source"
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    root_cli = authority_review["classifications"][0]
    assert root_cli["role"] == "projection"
    assert root_cli["direct_edit_allowed"] is False
    assert root_cli["source_contract"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert root_cli["regeneration_path"] == "uv run python scripts/generate/generate_command_packages.py"
    assert authority_review["authority_query"] == "agentic-workspace defaults --section root_cli_authority --format json"
    review = payload["answer"]["direct_cli_edit_review"]
    assert review["status"] == "review-needed"
    assert review["changed_paths"] == ["generated/workspace/python/cli.py"]
    assert "normal interface authoring belongs in command contracts" in review["rule"]
    assert "runtime primitive implementation and live workspace inspection" in review["allowed_direct_cli_work"]
    assert "route interface or generated-surface changes back" in review["recovery_signal"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["id"] == "workspace-cli-runtime"


def test_proof_changed_selector_broadens_contract_plus_cli_changes(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "src/agentic_workspace/contracts/proof_selection_rules.json",
                "generated/workspace/python/cli.py",
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
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make test-workspace" in answer["required_commands"]


def test_proof_changed_selector_escalates_for_cross_lane_changes(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
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
        "generated_command_packages",
        "subsystem:workspace-cli-runtime",
        "planning_source_typecheck_ci_parity",
        "assurance-requirement:subsystem:workspace-cli-runtime",
        "verification:closeout_intent_satisfaction",
        "verification:generated_adapter_conformance",
        "verification:requirement_grounding_delegation",
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
    assert "make typecheck-planning" in answer["required_commands"]
    package_step = answer["validation_plan"]["required"][0]
    assert package_step["command"] == "make test-planning"
    assert package_step["cwd"] == "."
    assert package_step["run"] == "make test-planning"
    assert package_step["lane_id"] == "planning_package"


def test_proof_changed_selector_accepts_existing_durable_surface_update(tmp_path: Path, capsys) -> None:
    contract_path = tmp_path / "src" / "agentic_workspace" / "contracts" / "report_contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text("{}\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
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
    assert review["review_gate"]["ordinary_path"] == "agentic-workspace proof --target ./repo --changed <paths> --format json"


def test_proof_changed_selector_flags_additive_only_durable_surface(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
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
                "--verbose",
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
