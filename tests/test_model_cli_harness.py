from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = REPO_ROOT / "scripts" / "model_cli_harness" / "run_model_cli_harness.py"


def _load_harness():
    spec = importlib.util.spec_from_file_location("run_model_cli_harness", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_model_cli_harness_dry_run_copies_fixture_and_renders_command(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "AGENTS.md").write_text("Start here.\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "fake": {
                        "default_model": "fake-model",
                        "required_executables": ["definitely-missing-model-cli"],
                        "block_on_preflight_failure": True,
                        "command": ["fake-cli", "--model", "{model}", "--repo", "{repo}", "-p", "{prompt}"],
                    }
                },
                "scenarios": [
                    {
                        "id": "orientation",
                        "fixture": "repo",
                        "prompt": "Use {repo} with {model}. Source is {source_root}.",
                        "expected_signals": ["reads instructions"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()
    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="orientation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    assert payload["result_count"] == 1
    result = payload["results"][0]
    repo_path = Path(result["repo_path"])
    assert (repo_path / "AGENTS.md").read_text(encoding="utf-8") == "Start here.\n"
    assert result["result"]["status"] == "dry-run"
    assert result["preflight"]["status"] == "environment-blocked"
    assert result["command"][0:3] == ["fake-cli", "--model", "fake-model"]
    assert str(repo_path) in result["prompt"]
    assert str(REPO_ROOT) in result["prompt"]
    assert (Path(result["run_root"]) / "run.json").exists()


def test_model_cli_harness_runs_all_prompt_variants(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("fixture\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "fake": {
                        "default_model": "fake-model",
                        "command": ["fake-cli", "-p", "{prompt}", "--repo", "{repo}"],
                    }
                },
                "scenarios": [
                    {
                        "id": "variant-scenario",
                        "fixture": "repo",
                        "prompt_variants": [
                            {"id": "one", "prompt": "Use {repo} variant one."},
                            {"id": "two", "prompt": "Use {repo} variant two."},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()
    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="variant-scenario",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
        prompt_variant="all",
    )

    assert payload["result_count"] == 2
    assert [result["prompt_variant_id"] for result in payload["results"]] == ["one", "two"]
    assert "variant one" in payload["results"][0]["prompt"]
    assert "variant two" in payload["results"][1]["prompt"]


def test_model_cli_harness_rejects_unknown_scenario(tmp_path: Path) -> None:
    suite = tmp_path / "suite.json"
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {"fake": {"command": ["fake"], "default_model": "fake-model"}},
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()
    try:
        harness.run_suite(
            suite_path=suite,
            adapter_id="fake",
            model=None,
            scenario_filter="missing",
            execute=False,
            output_root=tmp_path / "out",
            timeout_seconds=None,
        )
    except ValueError as exc:
        assert "scenario 'missing'" in str(exc)
    else:
        raise AssertionError("expected missing scenario to fail")


def test_model_cli_harness_suite_renders_gemini_adapter(tmp_path: Path) -> None:
    harness = _load_harness()

    payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="gemini",
        model=None,
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    assert payload["adapter"] == "gemini"
    assert payload["model"] == "gemini-3-flash-preview"
    assert result["result"]["status"] == "dry-run"
    assert result["command"][0:5] == [
        "gemini",
        "--model",
        "gemini-3-flash-preview",
        "--prompt",
        result["prompt"],
    ]
    assert "--approval-mode" in result["command"]
    assert "--include-directories" in result["command"]
    assert result["repo_path"] in result["command"]


def test_model_cli_harness_suite_renders_codex_adapter(tmp_path: Path) -> None:
    harness = _load_harness()

    payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="codex",
        model=None,
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    assert payload["adapter"] == "codex"
    assert payload["model"] == "gpt-5.3-codex-spark"
    assert result["result"]["status"] == "dry-run"
    assert result["command"][0:4] == [
        "codex",
        "exec",
        "--model",
        "gpt-5.3-codex-spark",
    ]
    assert "--cd" in result["command"]
    assert result["repo_path"] in result["command"]
    assert "--json" in result["command"]


def test_model_cli_harness_resolves_path_shims(tmp_path: Path, monkeypatch) -> None:
    harness = _load_harness()
    shim = tmp_path / "fake-cli.cmd"
    shim.write_text("@echo off\necho resolved\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))

    result = harness._run_command(["fake-cli", "--version"], cwd=tmp_path, timeout_seconds=10)

    assert result["returncode"] == 0
    assert result["command"][0].lower().endswith("fake-cli.cmd")
    assert result["original_command"] == ["fake-cli", "--version"]
    assert "resolved" in result["stdout"]


def test_model_cli_harness_extracts_execution_warnings(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "tool.execution_complete",
                    "error": {"message": "pwsh.exe is not recognized as an internal or external command"},
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "usage": {
                        "codeChanges": {
                            "filesModified": [
                                str(repo / "inside.md"),
                                str(tmp_path / "outside.md"),
                            ]
                        }
                    },
                }
            ),
        ]
    )

    warnings = harness._execution_warnings(result={"returncode": 0, "stdout": stdout, "stderr": ""}, repo_path=repo)

    assert {warning["warning_class"] for warning in warnings} == {
        "model_cli_shell_unavailable",
        "model_cli_external_write",
    }


def test_model_cli_harness_warns_on_runtime_failures_and_mutations(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 1,
            "stdout": None,
            "stderr": "ModelNotFoundError: Requested entity was not found.\nError: AttachConsole failed\nGaxiosError: Internal error encountered.",
        },
        repo_path=repo,
        mutation_summary={"status": "changed", "created_count": 1, "modified_count": 2, "deleted_count": 0},
    )

    assert {
        "model_cli_nonzero_exit",
        "model_cli_stdout_missing",
        "model_cli_model_not_found",
        "model_cli_runtime_stderr",
        "model_cli_provider_error",
        "model_cli_fixture_mutation",
    }.issubset({warning["warning_class"] for warning in warnings})


def test_model_cli_harness_warns_on_permission_denied_external_output_attempt(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "final_message": (
                "Permission denied and could not request permission from user while writing " + "C:" + "\\temp\\handoff_report.txt."
            ),
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_permission_denied" in classes
    assert "model_cli_external_output_attempt" in classes


def test_model_cli_harness_skips_semantic_scoring_when_model_did_not_answer() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={"returncode": 1, "stdout": "", "stderr": "ModelNotFoundError: Requested entity was not found."},
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


def test_model_cli_harness_scores_runtime_native_planning_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="cli-discovery-before-planning",
        result={
            "stdout": json.dumps(
                {
                    "response": "Verified /plan, /plan copy, Shift+Tab, and Ctrl+X. I would use /plan next.",
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any(warning["warning_class"] == "model_cli_semantic_workflow_failure" for warning in warnings)
    assert any("runtime-native planning commands" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_misplaced_planning_artifacts_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "Created .agentic-workspace/planning/ecommerce-app-planning.json. No automatic summary warnings could be generated."
                    ),
                }
            ),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/ecommerce-app-planning.json"],
        },
    )

    messages = [warning["message"] for warning in warnings]
    assert any("outside canonical Agentic Workspace planning surfaces" in message for message in messages)
    assert any("summary inspection was unavailable" in message for message in messages)


def test_model_cli_harness_scores_unregistered_execplan_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={"stdout": json.dumps({"response": "Created a clean execplan and summary has zero warnings."}), "stderr": ""},
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/execplans/ecommerce.plan.json"],
        },
    )

    assert any("without registering them in planning state" in warning["message"] for warning in warnings)


def test_model_cli_harness_counts_summary_command_from_full_transcript() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={
            "final_message": (
                "### Copilot\n"
                "Running validation.\n\n"
                "```powershell\nagentic-workspace summary --target . --format json\n```\n\n"
                "### Copilot\n"
                "Created durable planning state. Warnings: 0."
            ),
            "stdout": "",
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                ".agentic-workspace/planning/state.toml",
            ],
        },
    )

    assert not any("did not report running `agentic-workspace summary`" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_broad_prep_product_files_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="broad-work-decomposition",
        result={
            "stdout": json.dumps({"response": "Prepared a bounded slice and created app folders."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                "ecommerce-app/README.md",
                "ecommerce-app/docs/slice-1-handoff.md",
            ],
            "modified": ["README.md"],
        },
    )

    assert any("planning-only broad-work preparation" in warning["message"] for warning in warnings)
    assert any("README.md" in warning.get("evidence", "") for warning in warnings)


def test_model_cli_harness_scores_broad_prep_proposal_only() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="broad-work-decomposition",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "Proposed strategy: create durable state in .agentic-workspace/planning/records/. "
                        "I'll wait for your agreement before drafting the formal plan."
                    ),
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean", "created": []},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("proposal instead of creating durable repo-visible planning state" in message for message in messages)
    assert any("non-canonical `.agentic-workspace/planning/records/`" in message for message in messages)


def test_model_cli_harness_metadata_scoring_warns_on_write_and_response_rules(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".agentic-workspace").mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "broad-work-decomposition",
            "allowed_write_patterns": [".agentic-workspace/planning/**"],
            "forbidden_write_patterns": ["README.md", "src/**"],
            "required_command_mentions": ["agentic-workspace summary"],
            "required_executed_commands": ["agentic-workspace config"],
            "forbidden_executed_commands": [".agentic-workspace/config.toml"],
            "forbidden_response_phrases": ["/plan"],
            "required_artifact_patterns": [".agentic-workspace/planning/execplans/*.plan.json"],
        },
        result={
            "stdout": "\n".join(
                [
                    json.dumps({"response": "I used /plan and created source."}),
                    json.dumps({"command": "Get-Content -Path .agentic-workspace\\config.toml"}),
                ]
            ),
            "stderr": "",
        },
        mutation_summary={"status": "changed", "created": ["src/app.ts"], "modified": ["README.md"]},
        repo_path=repo,
    )

    messages = [warning["message"] for warning in warnings]
    assert any("outside the scenario's allowed write patterns" in message for message in messages)
    assert any("forbidden write patterns" in message for message in messages)
    assert any("required command" in message for message in messages)
    assert any("did not execute a required command" in message for message in messages)
    assert any("avoidable or forbidden" in message for message in messages)
    assert any("forbidden response phrase" in message for message in messages)
    assert any("required artifact pattern" in message for message in messages)


def test_model_cli_harness_metadata_scoring_uses_full_transcript_for_required_commands(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    plan = repo / ".agentic-workspace" / "planning" / "execplans" / "ecommerce.plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text("{}", encoding="utf-8")

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "planning-artifact-integrity",
            "allowed_write_patterns": [".agentic-workspace/planning/**"],
            "required_command_mentions": ["agentic-workspace summary"],
            "required_artifact_patterns": [".agentic-workspace/planning/execplans/*.plan.json"],
        },
        result={
            "final_message": "Final answer: durable planning created.",
            "stdout": "tool command: agentic-workspace summary --target . --format json",
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                ".agentic-workspace/docs/system-intent-contract.md",
            ],
        },
        repo_path=repo,
    )

    messages = [warning["message"] for warning in warnings]
    assert any("outside the scenario's allowed write patterns" in message for message in messages)
    assert not any("required command" in message for message in messages)


def test_model_cli_harness_metadata_scoring_distinguishes_command_mentions_from_execution(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "config-closeout-obligation",
            "required_command_mentions": ["agentic-workspace config"],
            "required_executed_commands": ["agentic-workspace config"],
        },
        result={
            "stdout": json.dumps({"response": 'The config file says commands = ["agentic-workspace config --target . --format json"].'}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    messages = [warning["message"] for warning in warnings]
    assert not any("required command or workflow surface" in message for message in messages)
    assert any("did not execute a required command" in message for message in messages)

    executed = harness._metadata_workflow_warnings(
        scenario={
            "id": "config-closeout-obligation",
            "required_executed_commands": ["agentic-workspace config"],
        },
        result={
            "stdout": json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "command_execution", "command": "agentic-workspace config --target . --format json"},
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert executed == []


def test_model_cli_harness_counts_copilot_powershell_markdown_as_executed_command(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "config-closeout-obligation",
            "required_executed_commands": ["agentic-workspace config"],
        },
        result={
            "final_message": """
### ✅ `powershell`

**Check effective agentic-workspace configuration**

```json
{
  "command": "cd './repo' && agentic-workspace config --target . --format json",
  "description": "Check effective agentic-workspace configuration"
}
```
""",
            "stdout": "",
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert warnings == []


def test_model_cli_harness_counts_gemini_shell_stats_with_command_response_as_executed(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "config-closeout-obligation",
            "required_executed_commands": ["agentic-workspace config"],
        },
        result={
            "stdout": json.dumps(
                {
                    "response": "I inspected the repository configuration via `agentic-workspace config --target . --profile compact --format json`.",
                    "stats": {"tools": {"byName": {"run_shell_command": {"count": 1}}}},
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert warnings == []


def test_model_cli_harness_required_mentions_allow_field_name_prose(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "local-delegation-posture",
            "required_command_mentions": ["delegation.mode", "safe_to_auto_run_commands"],
        },
        result={
            "final_message": "The relevant settings are delegation mode = auto and safe to auto run commands = false.",
            "stdout": "",
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert warnings == []


def test_model_cli_harness_skips_metadata_scoring_when_provider_did_not_run(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "config-closeout-obligation",
            "required_command_mentions": ["agentic-workspace config", "workflow_obligations"],
            "required_executed_commands": ["agentic-workspace config"],
        },
        result={
            "returncode": 1,
            "stdout": "",
            "stderr": "ModelNotFoundError: Requested entity was not found.",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert warnings == []


def test_model_cli_harness_forbidden_slash_phrase_does_not_match_planning_paths(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "broad-work-decomposition",
            "forbidden_response_phrases": ["/plan"],
        },
        result={
            "stdout": json.dumps({"response": "Created .agentic-workspace/planning/execplans/ecommerce.plan.json."}),
            "stderr": "",
        },
        mutation_summary={"status": "changed", "created": [".agentic-workspace/planning/execplans/ecommerce.plan.json"]},
        repo_path=repo,
    )

    assert warnings == []


def test_model_cli_harness_scores_persisted_summary_outputs_as_diagnostic_residue() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="broad-work-decomposition",
        result={"stdout": json.dumps({"response": "Created canonical planning and verified summary."}), "stderr": ""},
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/execplans/ecommerce.plan.json", "summary.json", "summary_full.json"],
        },
    )

    messages = [warning["message"] for warning in warnings]
    assert any("persisted diagnostic command output" in message for message in messages)
    assert not any("product or handoff files" in message for message in messages)


def test_model_cli_harness_quality_signals_capture_proportionality() -> None:
    harness = _load_harness()

    direct = harness._quality_signals(
        scenario_id="direct-task-minimal-overhead",
        mutation_summary={"status": "changed", "modified": ["README.md"]},
        warnings=[],
    )
    broad = harness._quality_signals(
        scenario_id="broad-work-decomposition",
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                "src/app.ts",
            ],
        },
        warnings=[],
    )

    assert direct == [
        {
            "id": "direct_task_stayed_direct",
            "status": "satisfied",
            "evidence": "README.md",
        }
    ]
    assert any(signal["id"] == "broad_task_created_durable_planning" and signal["status"] == "satisfied" for signal in broad)
    assert any(signal["id"] == "planning_only_avoided_product_scaffold" and signal["status"] == "weak" for signal in broad)


def test_model_cli_harness_quality_signals_separate_diagnostic_residue() -> None:
    harness = _load_harness()

    signals = harness._quality_signals(
        scenario_id="broad-work-decomposition",
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                "summary.json",
            ],
        },
        warnings=[],
    )

    assert any(signal["id"] == "planning_only_avoided_product_scaffold" and signal["status"] == "satisfied" for signal in signals)
    assert any(signal["id"] == "diagnostic_output_not_persisted" and signal["status"] == "weak" for signal in signals)


def test_model_cli_harness_postmortem_prompt_keeps_feedback_compact_and_actionable() -> None:
    harness = _load_harness()

    prompt = harness._postmortem_feedback_prompt(
        scenario={"id": "startup-orientation"},
        invocation={
            "scenario_id": "startup-orientation",
            "prompt_variant_id": "default",
            "prompt": "Please inspect the repo and tell me the next step.",
            "mutation_summary": {"status": "clean"},
            "warnings": [{"warning_class": "model_cli_semantic_workflow_failure", "message": "Too much raw reading."}],
            "result": {"final_message": "I read many files and then ran summary."},
        },
    )

    assert "Why did you choose the workflow and commands you used?" in prompt
    assert "What was ambiguous, missing, or more verbose than necessary?" in prompt
    assert "What would have reduced token usage without reducing safety or proof quality?" in prompt
    assert "Separate model/provider limitations from product or harness improvements." in prompt
    assert "Keep the answer under 250 words." in prompt
    assert len(prompt) < 5000


def test_model_cli_harness_parser_accepts_postmortem_feedback_flag() -> None:
    harness = _load_harness()

    args = harness.build_parser().parse_args(["--adapter", "codex", "--execute", "--postmortem-feedback"])

    assert args.adapter == "codex"
    assert args.execute is True
    assert args.postmortem_feedback is True


def test_model_cli_harness_fixtures_do_not_route_to_removed_planning_command() -> None:
    fixture_root = REPO_ROOT / "tools" / "model-cli-harness" / "fixtures"
    offenders = [
        path
        for path in fixture_root.rglob("*")
        if path.is_file() and "agentic-workspace planning" in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert offenders == []


def test_model_cli_harness_scores_config_sensitive_answers_without_config_surface() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="local-delegation-posture",
        result={
            "stdout": json.dumps(
                {
                    "response": ("Based on general best practices, I would automatically delegate this to a cheaper worker."),
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("without reporting use of the effective config surface" in message for message in messages)
    assert any("local config as the authority" in message for message in messages)
    assert any("despite local safety controls" in message for message in messages)


def test_model_cli_harness_config_fixture_scenarios_are_registered(tmp_path: Path) -> None:
    harness = _load_harness()

    payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="codex",
        model=None,
        scenario_filter="config-closeout-obligation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    repo = Path(result["repo_path"])
    assert (repo / ".agentic-workspace/config.toml").exists()
    assert (repo / ".agentic-workspace/config.local.toml").exists()
    assert result["result"]["status"] == "dry-run"


def test_model_cli_harness_scores_inaccessible_workflow_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="startup-orientation",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "AGENTS.md points to .agentic-workspace/WORKFLOW.md, but it is not accessible "
                        "and there is no .agentic-workspace folder."
                    ),
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("startup surface as unavailable" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_manual_invalid_planning_recovery_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "The state is not safe. Change .agentic-workspace/planning/state.toml "
                        'from execplans = ["freehand-lane.plan.json"] to execplans = [].'
                    ),
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("summary diagnostics" in message for message in messages)
    assert any("manual planning-state clearing" in message for message in messages)


def test_model_cli_harness_scores_windows_manual_invalid_planning_recovery() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "stdout": json.dumps(
                {
                    "response": ("Clear the invalid state with rm -r .agentic-workspace\\planning\\execplans\\freehand-lane.plan.json."),
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("manual planning-state clearing" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_copilot_transcript_final_answer_only() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "final_message": (
                "# Copilot CLI Session\n\n"
                "### File view\n`agentic-workspace summary --target . --format json`\n\n"
                "### X Copilot\nClear the invalid state with "
                "rm -r .agentic-workspace\\planning\\execplans\\freehand-lane.plan.json.\n"
                "---\n\n<sub>Generated by [GitHub Copilot CLI](https://github.com/features/copilot/cli)</sub>"
            ),
            "stdout": "",
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("summary diagnostics" in message for message in messages)
    assert any("manual planning-state clearing" in message for message in messages)


def test_model_cli_harness_scores_destructive_vcs_invalid_recovery_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "stdout": json.dumps({"response": "The repo is unsafe. Run git restore . before continuing."}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("destructive VCS cleanup" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_false_safe_invalid_recovery_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "stdout": json.dumps({"response": "You can safely proceed. No recovery command needed."}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("reported invalid planning state as safe" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_weak_target_direct_implementation_as_capability_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="weak-target-high-judgment",
        result={
            "stdout": json.dumps({"response": "I can implement directly. I will implement the workflow redesign now."}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("did not make escalation or handoff" in message for message in messages)
    assert any("offered direct implementation" in message for message in messages)


def test_model_cli_harness_accepts_weak_target_escalation() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="weak-target-high-judgment",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "This executor should not implement directly. The safe action is to escalate "
                        "to a stronger planner or prepare a compact handoff."
                    )
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


def test_model_cli_harness_scores_weak_ambiguous_without_inspection() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="weak-target-ambiguous-inspection",
        result={"stdout": json.dumps({"response": "I can implement this improvement directly now."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("did not require inspection" in message for message in messages)
    assert any("did not preserve escalation" in message for message in messages)


def test_model_cli_harness_scores_strong_target_retaining_mechanical_work() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="strong-target-mechanical",
        result={"stdout": json.dumps({"response": "Keep the strong target and make the edit directly."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("did not consider down-routing" in message for message in messages)
    assert any("without a no-safe-route justification" in message for message in messages)


def test_model_cli_harness_accepts_strong_target_downrouting() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="strong-target-mechanical",
        result={
            "stdout": json.dumps(
                {"response": "Down-route this mechanical docs tweak to the cheaper bounded executor; proof stays obvious."}
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


def test_model_cli_harness_scores_unclear_proof_downrouting_without_guardrails() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="strong-target-mechanical-unclear-proof",
        result={"stdout": json.dumps({"response": "Down-route this to the cheaper executor."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    assert any("proof/source-authority inspection" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_post_run_self_review_without_evidence() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="post-run-self-review",
        result={"stdout": json.dumps({"response": "Everything is fine."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    assert any("rationale, evidence, or prevention" in warning["message"] for warning in warnings)
    assert any("without trust qualification" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_capability_fit_scenario_mutations() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="weak-target-high-judgment",
        result={"stdout": json.dumps({"response": "Escalate to a stronger planner."}), "stderr": ""},
        mutation_summary={"status": "changed", "modified": ["README.md"]},
    )

    assert any("edited files during a no-edit capability-fit" in warning["message"] for warning in warnings)


def test_model_cli_harness_does_not_score_negated_safe_invalid_recovery_as_false_safe() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "stdout": json.dumps({"response": "It is not safe to continue. The planning state is blocked."}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert not any("reported invalid planning state as safe" in warning["message"] for warning in warnings)


def test_model_cli_harness_sets_git_ceiling_to_run_root(tmp_path: Path) -> None:
    harness = _load_harness()

    env = harness._with_git_ceiling({"GIT_CEILING_DIRECTORIES": "existing"}, run_root=tmp_path / "run")

    assert env["GIT_CEILING_DIRECTORIES"].split(os.pathsep)[-1] == str((tmp_path / "run").resolve())


def test_model_cli_harness_scores_direct_task_overplanning_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="direct-task-minimal-overhead",
        result={
            "stdout": json.dumps({"response": "I created an execplan for this lane."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/execplans/readme-update.plan.json"],
        },
    )

    messages = [warning["message"] for warning in warnings]
    assert any("direct wording edit" in message for message in messages)


def test_model_cli_harness_scores_native_plan_without_bridge_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="native-plan-bridge",
        result={
            "stdout": json.dumps({"response": "I made a private plan and a todo list for the cleanup."}),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("runtime-native planning" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_native_plan_misplaced_workspace_artifact() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="native-plan-bridge",
        result={
            "stdout": json.dumps({"response": "I bridged private todos into Agentic Workspace planning."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/doc-cleanup-preparation.json"],
        },
    )

    assert any("outside canonical Agentic Workspace planning surfaces" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_native_plan_workflow_mutation() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="native-plan-bridge",
        result={
            "stdout": json.dumps({"response": "I used private todos and updated the workflow instructions."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "modified": [".agentic-workspace/WORKFLOW.md"],
        },
    )

    assert any("modified workflow instructions" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_native_plan_freehand_root_plan() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="native-plan-bridge",
        result={
            "stdout": json.dumps({"response": "I used private todos and created DOC_CLEANUP_PLAN.md."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": ["DOC_CLEANUP_PLAN.md"],
        },
    )

    assert any("freehand planning or handoff artifact" in warning["message"] for warning in warnings)


def test_model_cli_harness_uses_final_message_for_semantic_scoring() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="invalid-planning-recovery",
        result={
            "final_message": "I would recover by setting execplans = [] in state.toml.",
            "stdout": "",
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert any("manual planning-state clearing" in warning["message"] for warning in warnings)


def test_model_cli_harness_snapshot_diff_reports_fixture_mutations(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "keep.txt").write_text("before\n", encoding="utf-8")
    (repo / "delete.txt").write_text("delete\n", encoding="utf-8")
    before = harness._file_snapshot(repo)

    (repo / "keep.txt").write_text("after\n", encoding="utf-8")
    (repo / "delete.txt").unlink()
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    diff = harness._snapshot_diff(before, harness._file_snapshot(repo))

    assert diff["status"] == "changed"
    assert diff["created"] == ["new.txt"]
    assert diff["modified"] == ["keep.txt"]
    assert diff["deleted"] == ["delete.txt"]


def test_model_cli_harness_blocks_execution_when_preflight_fails(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "AGENTS.md").write_text("Start here.\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "fake": {
                        "default_model": "fake-model",
                        "required_shells": ["definitely-missing-shell"],
                        "command": ["fake-cli", "-p", "{prompt}"],
                    }
                },
                "scenarios": [{"id": "orientation", "fixture": "repo", "prompt": "hello"}],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()
    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="orientation",
        execute=True,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    assert result["result"]["status"] == "environment-blocked"
    assert result["preflight"]["missing"][0]["name"] == "fake-cli"
    assert any(warning["warning_class"] == "model_cli_environment_blocked" for warning in result["warnings"])


def test_model_cli_harness_resolves_candidate_paths_and_prepends_path(tmp_path: Path, monkeypatch) -> None:
    harness = _load_harness()
    tool_dir = tmp_path / "tool"
    tool_dir.mkdir()
    tool = tool_dir / "pwsh.exe"
    tool.write_text("placeholder\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "")

    preflight = harness._adapter_preflight(
        {
            "required_shells": [
                {
                    "name": "pwsh",
                    "candidate_paths": [str(tool)],
                    "add_parent_to_path": True,
                }
            ]
        },
        command=["fake-cli"],
        replacements={},
    )
    env = harness._prepend_env_path({"PATH": "base"}, preflight["path_prepend"])

    assert preflight["status"] == "environment-blocked"
    assert preflight["requirements"][1]["status"] == "present"
    assert preflight["path_prepend"] == [str(tool_dir)]
    assert env["PATH"].startswith(str(tool_dir))


def test_model_cli_harness_can_isolate_provider_home(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "AGENTS.md").write_text("Start here.\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "fake": {
                        "default_model": "fake-model",
                        "provider_home_env": "FAKE_HOME",
                        "provider_home_path": "{run_root}/fake-home",
                        "command": ["fake-cli", "-p", "{prompt}"],
                    }
                },
                "scenarios": [{"id": "orientation", "fixture": "repo", "prompt": "hello"}],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()
    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="orientation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
        isolate_provider_home=True,
    )

    result = payload["results"][0]
    assert result["isolate_provider_home"] is True
    assert (Path(result["run_root"]) / "fake-home").exists()


def test_model_cli_harness_classifies_repeated_findings_across_prompt_variants() -> None:
    harness = _load_harness()

    classification = harness._classify_suite_findings(
        [
            {
                "scenario_id": "broad-work-decomposition",
                "prompt_variant_id": "one",
                "adapter_id": "codex",
                "model": "gpt-5.3-codex-spark",
                "warnings": [{"warning_class": "x", "message": "same"}],
            },
            {
                "scenario_id": "broad-work-decomposition",
                "prompt_variant_id": "two",
                "adapter_id": "codex",
                "model": "gpt-5.3-codex-spark",
                "warnings": [{"warning_class": "x", "message": "same"}],
            },
        ]
    )

    finding = classification["findings"][0]
    assert "repeated_across_prompts" in finding["classification"]


def test_model_cli_harness_ignores_expected_fixture_mutation_in_finding_classification() -> None:
    harness = _load_harness()

    classification = harness._classify_suite_findings(
        [
            {
                "scenario_id": "direct-task-minimal-overhead",
                "prompt_variant_id": "default",
                "adapter_id": "copilot",
                "model": "claude-haiku-4.5",
                "warnings": [
                    {"warning_class": "model_cli_fixture_mutation", "message": "changed"},
                    {"warning_class": "model_cli_permission_denied", "message": "denied"},
                ],
            }
        ]
    )

    assert classification["finding_count"] == 1
    assert "model_cli_permission_denied" in classification["findings"][0]["warning_key"]


def test_model_cli_harness_classifies_provider_runtime_noise_separately() -> None:
    harness = _load_harness()

    classification = harness._classify_suite_findings(
        [
            {
                "scenario_id": "config-closeout-obligation",
                "prompt_variant_id": "default",
                "adapter_id": "gemini",
                "model": "gemini-3-flash-preview",
                "warnings": [
                    {"warning_class": "model_cli_provider_error", "message": "provider error"},
                    {"warning_class": "model_cli_runtime_stderr", "message": "terminal warning"},
                ],
            }
        ]
    )

    assert classification["finding_count"] == 2
    for finding in classification["findings"]:
        assert "environment_or_provider" in finding["classification"]
        assert "first_seen" not in finding["classification"]


def test_model_cli_harness_compares_before_after_runs(tmp_path: Path) -> None:
    harness = _load_harness()
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    baseline.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "warnings": [
                            {"warning_class": "model_cli_semantic_workflow_failure", "message": "old problem"},
                            {"warning_class": "model_cli_semantic_workflow_failure", "message": "still here"},
                        ],
                        "mutation_summary": {"status": "changed"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "warnings": [
                            {"warning_class": "model_cli_semantic_workflow_failure", "message": "still here"},
                            {"warning_class": "model_cli_metadata_scoring_failure", "message": "new problem"},
                        ],
                        "mutation_summary": {"status": "clean"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    comparison = harness.compare_results(baseline_path=baseline, current_path=current)

    assert comparison["product_interpretation"] == "regressed"
    assert [warning["message"] for warning in comparison["resolved_warnings"]] == ["old problem"]
    assert [warning["message"] for warning in comparison["new_warnings"]] == ["new problem"]
    assert comparison["mutation_delta"] == {"baseline_changed_results": 1, "current_changed_results": 0}
