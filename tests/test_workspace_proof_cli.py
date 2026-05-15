from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


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
    assert payload["default_routes"]["planning_surfaces"] == "agentic-workspace summary --target ./repo --verbose --format json"
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

    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
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
        "uv run agentic-workspace summary --target . --verbose --format json",
        "uv run agentic-workspace doctor --target . --modules planning --format json",
    ]
    assert answer["validation_plan"]["kind"] == "validation-plan/v1"
    assert answer["validation_plan"]["status"] == "inspect-before-run"
    first_step = answer["validation_plan"]["required"][0]
    assert first_step["order"] == 1
    assert first_step["command"] == "uv run agentic-workspace summary --target . --verbose --format json"
    assert first_step["cwd"] == "."
    assert first_step["run"].endswith("agentic-workspace summary --target . --verbose --format json")
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
    assert payload["selector"] == {"changed": ["generated/workspace/python/cli.py"]}
    assert payload["next"]["action"] == "run-validation-command"
    assert payload["next"]["command"] == "make test-workspace"
    assert "make lint-workspace" in payload["required_commands"]
    assert payload["warnings"] == []
    assert "answer" not in payload
    assert "selected_lanes" not in encoded
    assert "validation_plan" not in encoded
    assert len(encoded) < 2500


def test_proof_changed_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n\nmaintainer-surfaces:\n\ttrue\n")

    assert cli.main(["proof", "--target", str(tmp_path), "--changed", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["required_commands"] == ["make test", "make lint"]
    assert payload["next"]["command"] == "make test"
    assert payload["next"]["route_source"] == "live-adapted-target-capability"
    assert payload["next"]["why"] == "behavior-test intent selected live-adapted-target-capability."
    assert payload["proof_route_decision"]["selected_command"] == {
        "command": "make test",
        "lane": "workspace_cli",
        "route_source": "live-adapted-target-capability",
        "intent_type": "behavior-test",
    }
    assert payload["proof_route_decision"]["route_source"] == "live-adapted-target-capability"
    assert payload["proof_route_decision"]["manual_fallback"] is None
    assert payload["proof_route_decision"]["explanation_field"] == "proof_route_explanation"
    assert "next_action" not in payload["proof_route_decision"]
    assert "required_commands" not in payload["proof_route_decision"]
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
    assert payload["proof_route_decision"]["manual_fallback"]["status"] == "required"
    assert payload["proof_route_decision"]["manual_fallback"]["unavailable_command_count"] == 2
    assert payload["proof_route_decision"]["selected_command"] is None
    assert payload["proof_route_decision"]["route_source"] == "manual-fallback"
    assert payload["manual_verification"]["status"] == "required"
    assert "no executable proof route" in payload["manual_verification"]["summary"]
    assert payload["unavailable_proof_commands"] == [
        {
            "lane": "workspace_cli",
            "command": "make test-workspace",
            "reason": "target repo has no Makefile and no matching package.json script, so make-based package proof was not selected",
        },
        {
            "lane": "workspace_cli",
            "command": "make lint-workspace",
            "reason": "target repo has no Makefile and no matching package.json script, so make-based package proof was not selected",
        },
    ]
    assert payload["proof_strategy"]["selection_order"][0] == "match changed paths to proof intent"
    assert payload["target_proof_capabilities"]["candidate_commands"] == []
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
    decision = answer["proof_route_decision"]
    assert decision["next_action"]["action"] == "manual-verification"
    assert decision["selected_command"] is None
    assert decision["manual_fallback"]["status"] == "required"
    assert decision["manual_fallback"]["unavailable_command_count"] == 2
    assert decision["critical_warnings"] == ["Some selected proof commands are unavailable in this target repo."]
    explanation = answer["proof_route_explanation"]
    assert explanation["selected_commands"] == []
    assert [command["command"] for command in explanation["unavailable_commands"]] == ["make test-workspace", "make lint-workspace"]
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
    _write(tmp_path / "packages" / "planning" / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")
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
    assert answer["required_commands"] == ["cd packages/planning && make test", "cd packages/planning && make lint"]
    assert answer["target_proof_capabilities"]["make"] == {"available": False, "targets": []}
    project_roots = {project_root["path"]: project_root for project_root in answer["target_proof_capabilities"]["project_roots"]}
    assert project_roots["packages/other"]["changed_path_matched"] is False
    assert project_roots["packages/planning"]["changed_path_matched"] is True
    assert project_roots["packages/planning"]["make"]["targets"] == ["lint", "test"]
    assert "cd packages/planning && make test" in answer["target_proof_capabilities"]["candidate_commands"]
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
    assert answer["proof_route_decision"]["selected_command"] == {
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
    decision = answer["proof_route_decision"]
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
    assert answer["proof_route_decision"]["critical_warnings"] == ["Host proof policy blocked one or more candidate proof commands."]
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
    assert step["command"] == f'uv run agentic-workspace summary --target "{expected_target}" --verbose --format json'
    assert step["run"] == f'uv run agentic-workspace summary --target "{expected_target}" --verbose --format json'


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


def test_proof_changed_selector_routes_generated_command_packages(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
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
    assert answer["selected_lanes"][0]["proof_responsibility"] == "local-serial"
    assert answer["selected_lanes"][0]["execution_mode"] == "serial"
    weak_agent_routing = answer["selected_lanes"][0]["weak_agent_safe_routing"]
    assert weak_agent_routing["status"] == "proof-gated"
    assert "generated-package static plus conformance proof pass" in weak_agent_routing["rule"]
    assert "serially" in answer["selected_lanes"][0]["ci_relationship"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "generated_command_packages",
        "cli_authority",
    ]
    assert "route back through command-package checks" in answer["selected_lanes"][0]["recovery_signal"]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
        "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker",
        "uv run python scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
        "uv run agentic-workspace defaults --section root_cli_authority --format json",
    ]
    assert [step["lane_id"] for step in answer["validation_plan"]["required"]] == [
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "generated_command_packages",
        "cli_authority",
    ]
    generated_steps = [step for step in answer["validation_plan"]["required"] if step["lane_id"] == "generated_command_packages"]
    assert {step["execution_mode"] for step in generated_steps} == {"serial"}
    assert {step["proof_responsibility"] for step in generated_steps} == {"local-serial"}
    assert all("serially" in step["ci_relationship"] for step in generated_steps)
    generated_commands = [command for command in answer["selected_commands"] if command["lane"] == "generated_command_packages"]
    assert {command["execution_mode"] for command in generated_commands} == {"serial"}
    assert {command["proof_responsibility"] for command in generated_commands} == {"local-serial"}
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


def test_proof_changed_selector_routes_python_generated_packages_to_python_docker(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--changed",
                "generated/workspace/python/__init__.py",
                "scripts/check/check_generated_command_packages.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert [lane["id"] for lane in answer["selected_lanes"]] == [
        "generated_command_packages",
        "cli_authority",
        "subsystem:workspace-cli-runtime",
    ]
    assert answer["required_commands"] == [
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
        "uv run agentic-workspace defaults --section root_cli_authority --format json",
        "uv run pytest tests/test_workspace_cli.py -q",
    ]
    assert (
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker"
        in answer["required_commands"]
    )
    assert "CI may repeat generated-package proof" in answer["selected_lanes"][0]["ci_relationship"]
    generated_steps = [step for step in answer["validation_plan"]["required"] if step["lane_id"] == "generated_command_packages"]
    assert generated_steps
    assert {step["execution_mode"] for step in generated_steps} == {"serial"}
    assert all("serially" in step["ci_relationship"] for step in generated_steps)


def test_proof_changed_selector_routes_contract_only_changes_to_focused_lane(capsys) -> None:
    assert (
        cli.main(
            [
                "proof",
                "--verbose",
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
    docs_diff = (
        "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md "
        "packages/memory/README.md packages/command-generation/README.md"
    )
    assert [lane["id"] for lane in answer["selected_lanes"]] == ["repo_docs_review"]
    assert answer["selected_lanes"][0]["proof_kind"] == "diff-review"
    assert answer["required_commands"] == [docs_diff]
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


def test_proof_tiny_readme_profile_keeps_docs_only_validation_light(capsys) -> None:
    assert cli.main(["proof", "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload)
    docs_diff = (
        "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md "
        "packages/memory/README.md packages/command-generation/README.md"
    )
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
    ]
    assert answer["escalate_when"][0] == "changed paths span multiple validation lanes; run all selected commands or split the work"
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
