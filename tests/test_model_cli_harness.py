from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

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


def test_model_cli_harness_extracts_token_usage_summary() -> None:
    harness = _load_harness()
    stdout = "\n".join(
        [
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
            json.dumps(
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 40,
                        "output_tokens": 20,
                        "reasoning_output_tokens": 5,
                    },
                }
            ),
        ]
    )

    usage = harness._usage_summary_from_stdout(stdout)

    assert usage == {
        "status": "present",
        "turn_count": 1,
        "input_tokens": 100,
        "cached_input_tokens": 40,
        "output_tokens": 20,
        "reasoning_output_tokens": 5,
        "uncached_input_tokens": 60,
        "total_billable_proxy_tokens": 85,
    }


def test_model_cli_harness_default_output_root_uses_workspace_local_scratch() -> None:
    harness = _load_harness()

    assert harness.DEFAULT_OUTPUT_ROOT == REPO_ROOT / ".agentic-workspace" / "local" / "scratch" / "model-cli-harness"


def test_model_cli_harness_validates_stage1_dogfooding_feedback_pack() -> None:
    schema = json.loads(
        (REPO_ROOT / "tools" / "model-cli-harness" / "schemas" / "dogfooding-feedback.schema.json").read_text(encoding="utf-8")
    )
    pack = json.loads(
        (REPO_ROOT / "tools" / "model-cli-harness" / "feedback" / "2026-06-04-codex-copilot-stage1.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(pack))

    assert errors == []
    assert len(pack["benchmark_fixtures"]) >= 3
    assert {finding["failure_class"] for record in pack["records"] for finding in record["findings"]} >= {
        "closeout_reporting_gap",
        "decision_traceability_gap",
        "evaluation_capture_gap",
    }
    assert {agent["model"] for record in pack["records"] for agent in record["agents"]} == {
        "gpt-5.4-mini",
        "claude-sonnet-4.6",
    }


def test_model_cli_harness_reads_configured_startup_instruction_file(tmp_path: Path) -> None:
    harness = _load_harness()
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "GEMINI.md"\n',
        encoding="utf-8",
    )
    (tmp_path / "GEMINI.md").write_text("Use Gemini startup.\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("Wrong startup.\n", encoding="utf-8")

    prompt = harness._startup_instruction_prompt(repo_path=tmp_path, prompt="Do work.")

    assert "Repository startup instruction from GEMINI.md" in prompt
    assert "Use Gemini startup." in prompt
    assert "Wrong startup." not in prompt


def test_model_cli_harness_tolerates_gemini_string_events_and_stats() -> None:
    harness = _load_harness()
    stdout = "\n".join(
        [
            json.dumps("provider banner"),
            json.dumps(
                {
                    "response": "Done.",
                    "stats": {
                        "inputTokens": 7,
                        "outputTokens": 3,
                        "totalTokenCount": 10,
                        "tools": {"byName": {"run_shell_command": {"count": 1}}},
                    },
                }
            ),
        ]
    )

    usage = harness._usage_summary_from_stdout(stdout)
    warnings = harness._execution_warnings(
        result={"returncode": 0, "stdout": stdout, "stderr": ""},
        repo_path=REPO_ROOT,
        mutation_summary={"status": "clean"},
    )

    assert usage["status"] == "present"
    assert usage["input_tokens"] == 7
    assert usage["output_tokens"] == 3
    assert usage["provider_total_tokens"] == 10
    assert usage["provider_stats"]["tools"]["byName"]["run_shell_command"]["count"] == 1
    assert warnings == []


def test_model_cli_harness_extracts_package_read_surface_summary() -> None:
    harness = _load_harness()
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "pwsh -Command 'agentic-workspace start --format json'",
                        "aggregated_output": '{\n  "kind": "startup-context/v1"\n}\n',
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "pwsh -Command 'pytest -q'",
                        "aggregated_output": "1 passed\n",
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            ),
        ]
    )

    summary = harness._package_read_surface_summary_from_stdout(stdout)

    assert summary["status"] == "present"
    assert summary["command_count"] == 1
    assert summary["output_lines"] == 3
    assert summary["output_bytes"] == len('{\n  "kind": "startup-context/v1"\n}\n'.encode())
    assert summary["commands"][0]["exit_code"] == 0
    assert summary["precision"] == "direct"
    assert summary["mixed_command_count"] == 0
    assert "mixed shell commands" in summary["metric_role"]


def test_model_cli_harness_ignores_uv_lock_runtime_byproduct(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    before = harness._file_snapshot(repo)

    (repo / "uv.lock").write_text("# generated by uv\n", encoding="utf-8")

    assert harness._snapshot_diff(before, harness._file_snapshot(repo))["status"] == "clean"


def test_model_cli_harness_separates_source_changes_from_cache_noise(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    before = harness._file_snapshot(repo, include_ignored=True)

    (repo / ".mypy_cache" / "cache.json").parent.mkdir()
    (repo / ".mypy_cache" / "cache.json").write_text("{}", encoding="utf-8")
    (repo / ".ruff_cache" / "cache.bin").parent.mkdir()
    (repo / ".ruff_cache" / "cache.bin").write_text("cache", encoding="utf-8")
    (repo / "src" / "pluggy.egg-info").mkdir(parents=True)
    (repo / "src" / "pluggy.egg-info" / "PKG-INFO").write_text("metadata", encoding="utf-8")
    (repo / "src" / "pluggy" / "_manager.py").parent.mkdir(parents=True)
    (repo / "src" / "pluggy" / "_manager.py").write_text("source", encoding="utf-8")

    diff = harness._snapshot_diff(before, harness._file_snapshot(repo, include_ignored=True))

    assert diff["status"] == "changed"
    assert diff["created"] == ["src/pluggy/_manager.py"]
    assert diff["ignored_noise_count"] == 3
    assert "src/pluggy.egg-info/PKG-INFO" in diff["raw_created"]
    assert "src/pluggy.egg-info/PKG-INFO" in diff["ignored_created"]


def test_model_cli_harness_marks_mixed_package_commands_approximate() -> None:
    harness = _load_harness()
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": 'pwsh -Command "Get-Content .agentic-workspace/config.toml; agentic-workspace start --format json"',
                "aggregated_output": "config\n---\n{}\n",
                "exit_code": 0,
                "status": "completed",
            },
        }
    )

    summary = harness._package_read_surface_summary_from_stdout(stdout)

    assert summary["status"] == "present"
    assert summary["precision"] == "approximate"
    assert summary["mixed_command_count"] == 1
    assert summary["commands"][0]["mixed_shell_command"] is True


def test_model_cli_harness_does_not_mark_task_punctuation_as_mixed_package_command() -> None:
    harness = _load_harness()
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": ('pwsh -Command "agentic-workspace start --task \\"Redesign policy; provide safe next action\\" --format json"'),
                "aggregated_output": "{}\n",
                "exit_code": 0,
                "status": "completed",
            },
        }
    )

    summary = harness._package_read_surface_summary_from_stdout(stdout)

    assert summary["precision"] == "direct"
    assert summary["mixed_command_count"] == 0
    assert summary["commands"][0]["mixed_shell_command"] is False


def test_model_cli_harness_aggregates_package_read_surface_summary() -> None:
    harness = _load_harness()

    summary = harness._aggregate_package_read_surface_summaries(
        [
            {"package_read_surface_summary": {"status": "present", "command_count": 1, "output_bytes": 20, "output_lines": 2}},
            {
                "package_read_surface_summary": {
                    "status": "present",
                    "command_count": 2,
                    "output_bytes": 30,
                    "output_lines": 3,
                    "mixed_command_count": 1,
                }
            },
            {"package_read_surface_summary": {"status": "absent"}},
        ]
    )

    assert summary["status"] == "present"
    assert summary["result_count"] == 2
    assert summary["command_count"] == 3
    assert summary["output_bytes"] == 50
    assert summary["output_lines"] == 5
    assert summary["mixed_command_count"] == 1
    assert summary["precision"] == "approximate"


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
    assert result["package_read_surface_summary"]["status"] == "not-run"
    assert result["preflight"]["status"] == "environment-blocked"
    assert result["command"][0:3] == ["fake-cli", "--model", "fake-model"]
    assert str(repo_path) in result["prompt"]
    assert str(REPO_ROOT) in result["prompt"]
    assert (Path(result["run_root"]) / "run.json").exists()
    assert len(Path(result["run_root"]).name) < 90
    assert payload["completion_followthrough"]["status"] == "dry-run"
    assert payload["completion_followthrough"]["source"] == "default-dry-run"
    assert payload["package_read_surface_summary"]["status"] == "absent"


def test_model_cli_harness_fallback_workflows_stop_when_cli_unavailable() -> None:
    fixture_root = REPO_ROOT / "tools" / "model-cli-harness" / "fixtures"
    workflow_files = list(fixture_root.glob("*/.agentic-workspace/WORKFLOW.md"))

    assert workflow_files
    for workflow_file in workflow_files:
        text = workflow_file.read_text(encoding="utf-8")
        assert "If the CLI is unavailable" in text
        assert "Do not search planning directories, templates, schemas, or unrelated repo files" in text
        assert "Do not invent substitute validation commands" in text
        assert "validation commands are unavailable until the command can run" in text


def test_model_cli_harness_aw_fixtures_use_source_checkout_invocation(tmp_path: Path) -> None:
    harness = _load_harness()
    paths = harness.HarnessPaths(
        run_root=tmp_path / "run",
        fixture_root=tmp_path / "run" / "fixture",
        repo_path=tmp_path / "run" / "repo",
        transcript_path=tmp_path / "run" / "transcript.jsonl",
        share_path=tmp_path / "run" / "session.md",
    )

    harness._prepare_fixture(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        scenario={"id": "unit", "fixture": "aw-minimal-host-repo"},
        paths=paths,
    )

    pyproject = (paths.repo_path / "pyproject.toml").read_text(encoding="utf-8")
    local_config = (paths.repo_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")
    agents = (paths.repo_path / "AGENTS.md").read_text(encoding="utf-8")

    assert 'dependencies = ["agentic-workspace"]' in pyproject
    assert "[tool.uv.sources]" in pyproject
    assert REPO_ROOT.as_posix() in pyproject
    assert 'cli_invoke = "uv run agentic-workspace"' in local_config
    assert "uv run agentic-workspace implement --changed <paths> --format json" in agents


def test_model_cli_harness_records_explicit_completion_followthrough() -> None:
    harness = _load_harness()

    payload = harness._completion_followthrough_payload(
        execute=True,
        completion_followthrough="pushed-to-completion",
    )

    assert payload["kind"] == "agentic-workspace/model-cli-completion-followthrough/v1"
    assert payload["status"] == "pushed-to-completion"
    assert payload["source"] == "cli-argument"
    assert payload["advisory_only"] is True


def test_model_cli_harness_records_pushed_to_completion_turns(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "AGENTS.md").write_text("Plain test repo.\n", encoding="utf-8")
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
                        "timeout_seconds": 10,
                        "block_on_preflight_failure": False,
                        "command": [
                            sys.executable,
                            "-c",
                            "import json,sys; print(json.dumps({'response': sys.argv[1], 'stats': {'inputTokens': 1, 'outputTokens': 2, 'totalTokenCount': 3}}))",
                            "{prompt}",
                        ],
                    }
                },
                "scenarios": [
                    {
                        "id": "completion",
                        "fixture": "repo",
                        "prompt": "first",
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
        scenario_filter="completion",
        execute=True,
        output_root=tmp_path / "out",
        timeout_seconds=None,
        follow_up_prompts=["second"],
        completion_validation_commands=[[sys.executable, "-c", "print('ok')"]],
    )

    result = payload["results"][0]
    loop = result["completion_loop"]
    assert loop["requests_to_completion"] == 2
    assert loop["followup_request_count"] == 1
    assert loop["final_validation_status"] == "passed"
    assert loop["cumulative_usage_summary"]["input_tokens"] == 2
    assert loop["cumulative_usage_summary"]["output_tokens"] == 4
    assert Path(loop["followup_turns"][0]["transcript_path"]).exists()
    assert payload["completion_loop_summary"]["requests_to_completion_total"] == 2


def test_model_cli_harness_can_inject_repo_startup_instructions(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
    (fixture / "AGENTS.md").write_text(
        '<!-- agentic-workspace:workflow:start -->\nRun `agentic-workspace start --task "<task>" --format json` using the user request as `<task>`.\n<!-- agentic-workspace:workflow:end -->\n',
        encoding="utf-8",
    )
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
                        "block_on_preflight_failure": False,
                        "inject_repo_startup_instructions": True,
                        "command": ["fake-cli", "-p", "{prompt}"],
                    }
                },
                "scenarios": [{"id": "orientation", "fixture": "repo", "prompt": "Do the task."}],
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

    prompt = payload["results"][0]["prompt"]
    assert prompt.startswith("Do the task.\n\n")
    assert "Repository startup instruction from AGENTS.md to apply before non-trivial requests:" in prompt
    assert 'start --task "<task>"' in prompt


def test_model_cli_harness_uses_postmortem_command_without_repo_context(tmp_path: Path, monkeypatch) -> None:
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
                        "block_on_preflight_failure": False,
                        "command": ["fake-cli", "--repo", "{repo}", "--share", "{share_path}", "-p", "{prompt}"],
                        "postmortem_command": [
                            "fake-cli",
                            "--cwd",
                            "{postmortem_cwd}",
                            "--share",
                            "{share_path}",
                            "-p",
                            "{prompt}",
                        ],
                    }
                },
                "scenarios": [{"id": "orientation", "fixture": "repo", "prompt": "Orient."}],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()

    def fake_run_command(command, *, cwd, timeout_seconds, env=None):  # noqa: ANN001
        assert cwd.exists()
        share_path = Path(command[command.index("--share") + 1])
        share_path.write_text("final\n", encoding="utf-8")
        return {"returncode": 0, "stdout": "ok", "stderr": "", "command": command, "cwd": str(cwd)}

    monkeypatch.setattr(harness, "_run_command", fake_run_command)

    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="orientation",
        execute=True,
        output_root=tmp_path / "out",
        timeout_seconds=None,
        postmortem_feedback=True,
    )

    result = payload["results"][0]
    postmortem = result["postmortem_feedback"]
    assert "--repo" not in postmortem["command"]
    assert result["repo_path"] not in postmortem["command"]
    assert postmortem["result"]["cwd"].endswith("postmortem-context")


def test_copilot_postmortem_feedback_is_marked_unsupported() -> None:
    suite = json.loads((REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json").read_text(encoding="utf-8"))

    adapter = suite["adapters"]["copilot"]
    command = adapter["postmortem_command"]
    assert adapter["env"] == {"COPILOT_ALLOW_ALL": "true"}
    assert adapter["postmortem_feedback_supported"] is False
    assert "--available-tools=" in command
    assert "--no-custom-instructions" in command
    assert "--add-dir" not in command


def test_model_cli_harness_fixtures_use_current_workflow_fallback() -> None:
    workflows = sorted((REPO_ROOT / "tools" / "model-cli-harness" / "fixtures").glob("*/.agentic-workspace/WORKFLOW.md"))
    assert workflows
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        assert "startup-only, orientation-only" in text
        assert "Do not create planning files." in text


def test_model_cli_harness_can_mark_postmortem_feedback_unsupported(tmp_path: Path, monkeypatch) -> None:
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
                        "block_on_preflight_failure": False,
                        "postmortem_feedback_supported": False,
                        "command": ["fake-cli", "--share", "{share_path}", "-p", "{prompt}"],
                    }
                },
                "scenarios": [{"id": "orientation", "fixture": "repo", "prompt": "Orient."}],
            }
        ),
        encoding="utf-8",
    )

    harness = _load_harness()

    def fake_run_command(command, *, cwd, timeout_seconds, env=None):  # noqa: ANN001
        share_path = Path(command[command.index("--share") + 1])
        share_path.write_text("final\n", encoding="utf-8")
        return {"returncode": 0, "stdout": "ok", "stderr": "", "command": command, "cwd": str(cwd)}

    monkeypatch.setattr(harness, "_run_command", fake_run_command)

    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="orientation",
        execute=True,
        output_root=tmp_path / "out",
        timeout_seconds=None,
        postmortem_feedback=True,
    )

    postmortem = payload["results"][0]["postmortem_feedback"]
    assert postmortem["status"] == "unsupported"
    assert postmortem["warnings"][0]["warning_class"] == "model_cli_postmortem_feedback_unsupported"


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
    assert "Repository startup instruction from AGENTS.md" in result["prompt"]


def test_model_cli_harness_suite_renders_copilot_adapter_with_explicit_cwd(tmp_path: Path) -> None:
    harness = _load_harness()

    payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="copilot",
        model=None,
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    command = result["command"]
    cwd_index = command.index("-C")
    assert payload["adapter"] == "copilot"
    assert payload["model"] == "claude-haiku-4.5"
    assert result["result"]["status"] == "dry-run"
    assert command[0:3] == ["copilot", "--model", "claude-haiku-4.5"]
    assert command[cwd_index + 1] == result["repo_path"]
    assert "--allow-all" in command
    assert "--allow-tool=write" in command
    assert "--add-dir" in command
    assert result["repo_path"] in command


def test_model_cli_harness_copilot_uses_per_model_args(tmp_path: Path) -> None:
    harness = _load_harness()

    haiku_payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="copilot",
        model="claude-haiku-4.5",
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "haiku",
        timeout_seconds=None,
    )
    sonnet_payload = harness.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="copilot",
        model="claude-sonnet-4.6",
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "sonnet",
        timeout_seconds=None,
    )

    assert "--effort" not in haiku_payload["results"][0]["command"]
    sonnet_command = sonnet_payload["results"][0]["command"]
    assert sonnet_command[sonnet_command.index("--effort") + 1] == "low"


def test_model_cli_harness_prompt_transport_writes_large_prompt_to_file(tmp_path: Path) -> None:
    fixture = tmp_path / "fixtures" / "repo"
    fixture.mkdir(parents=True)
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
                        "block_on_preflight_failure": False,
                        "prompt_transport": {
                            "threshold_chars": 20,
                            "mode": "file-attachment",
                            "file_args": ["--attachment", "{prompt_file}"],
                            "file_prompt": "Read {prompt_file}.",
                        },
                        "command": ["fake-cli", "-p", "{prompt}", "{prompt_transport_args}"],
                    }
                },
                "scenarios": [{"id": "large", "fixture": "repo", "prompt": "x" * 80}],
            }
        ),
        encoding="utf-8",
    )
    harness = _load_harness()

    payload = harness.run_suite(
        suite_path=suite,
        adapter_id="fake",
        model=None,
        scenario_filter="large",
        execute=False,
        output_root=tmp_path / "out",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    prompt_transport = result["prompt_transport"]
    command = result["command"]
    prompt_file = Path(prompt_transport["prompt_file"])
    assert prompt_transport["mode"] == "file-attachment"
    assert prompt_file.exists()
    assert prompt_file.read_text(encoding="utf-8") == "x" * 80
    assert command[command.index("-p") + 1].startswith("Read ")
    assert "--attachment" in command
    assert str(prompt_file) in command


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


def test_model_cli_harness_timeout_returns_adapter_blocked(tmp_path: Path, monkeypatch) -> None:
    harness = _load_harness()
    killed: list[int] = []
    monkeypatch.setattr(harness, "_terminate_process_tree", lambda pid: killed.append(pid))

    result = harness._run_command(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        cwd=tmp_path,
        timeout_seconds=0.1,
    )

    assert result["status"] == "adapter_blocked"
    assert result["timed_out"] is True
    assert killed


def test_model_cli_harness_runtime_failure_gets_structured_status(tmp_path: Path) -> None:
    harness = _load_harness()

    result = {
        "returncode": 3221225477,
        "stdout": "",
        "stderr": "",
    }
    result["status"] = harness._classify_result_status(result)
    warnings = harness._execution_warnings(result=result, repo_path=tmp_path, mutation_summary={"status": "clean"})

    assert result["status"] == "runtime_failed"
    assert "model_cli_runtime_failed" in {warning["warning_class"] for warning in warnings}


def test_model_cli_harness_adapter_configuration_rejection_gets_structured_status(tmp_path: Path) -> None:
    harness = _load_harness()

    result = {
        "returncode": 1,
        "stdout": "",
        "stderr": "model does not support reasoning effort configuration",
    }
    result["status"] = harness._classify_result_status(result)
    warnings = harness._execution_warnings(result=result, repo_path=tmp_path, mutation_summary={"status": "clean"})

    assert result["status"] == "adapter_configuration_rejected"
    assert "model_cli_adapter_configuration_rejected" in {warning["warning_class"] for warning in warnings}


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
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "Get-Content README.md",
                        "aggregated_output": "execution error: invalid directory",
                        "exit_code": -1,
                        "status": "failed",
                    },
                }
            ),
        ]
    )

    warnings = harness._execution_warnings(result={"returncode": 0, "stdout": stdout, "stderr": ""}, repo_path=repo)

    assert {warning["warning_class"] for warning in warnings} == {
        "model_cli_shell_unavailable",
        "model_cli_external_write",
        "model_cli_command_execution_failed",
    }
    failed = next(warning for warning in warnings if warning["warning_class"] == "model_cli_command_execution_failed")
    assert "Get-Content README.md" in failed["evidence"]


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


def test_model_cli_harness_marks_agentic_workspace_permission_denied_as_adapter_limitation(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "final_message": "agentic-workspace start: Permission denied and could not request permission from user",
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_permission_denied" in classes
    assert "model_cli_adapter_tooling_limitation" in classes


def test_model_cli_harness_marks_missing_shell_tool_as_adapter_limitation(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": "I would run `agentic-workspace start --format json`.",
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    assert "model_cli_adapter_tooling_limitation" in {warning["warning_class"] for warning in warnings}


def test_model_cli_harness_warns_on_raw_planning_before_fallback_workflow(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": ("I will list `.agentic-workspace/planning` first.\nLater I read `.agentic-workspace/WORKFLOW.md`.\n"),
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )
    signals = harness._quality_signals(
        scenario_id="next-decision-output-profile",
        result={"stdout": "agentic-workspace implement --changed README.md --format json"},
        mutation_summary={"status": "clean"},
        warnings=warnings,
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_adapter_tooling_limitation" in classes
    assert "model_cli_raw_workspace_before_fallback" in classes
    assert any(signal["id"] == "read_surface_under_read" and signal["status"] == "weak" for signal in signals)


def test_model_cli_harness_warns_on_shorthand_planning_before_fallback_workflow(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": ("I will search within the `planning` directory first.\nLater I read `.agentic-workspace/WORKFLOW.md`.\n"),
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_raw_workspace_before_fallback" in classes


def test_model_cli_harness_warns_on_cli_unavailable_substitute_validation(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": (
                "Intended command: `uv run agentic-workspace implement --changed README.md --format json`\n"
                "Validation command list:\n"
                "1. `grep README README.md`\n"
                "2. `read_file README.md`\n"
            ),
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_cli_unavailable_substitute_validation" in classes


def test_model_cli_harness_accepts_cli_unavailable_validation_unavailable(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._execution_warnings(
        result={
            "returncode": 0,
            "stdout": (
                "Intended command: `uv run agentic-workspace implement --changed README.md --format json`\n"
                "Validation command list: unavailable until the command can run.\n"
            ),
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        repo_path=repo,
        mutation_summary={"status": "clean"},
    )

    classes = {warning["warning_class"] for warning in warnings}
    assert "model_cli_cli_unavailable_substitute_validation" not in classes


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


def test_model_cli_harness_scores_unsupported_planning_promotion_command() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={"stdout": json.dumps({"response": "Next run agentic-planning promote-lane --id checkout."}), "stderr": ""},
        mutation_summary={"status": "changed", "created": [".agentic-workspace/planning/decompositions/ecommerce.json"]},
    )

    assert any("unsupported planning lifecycle command" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_false_valid_missing_execplan_refs(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={
            "cwd": str(repo),
            "stdout": json.dumps(
                {"response": ("All referenced paths are valid. Next action uses .agentic-workspace/planning/execplans/checkout.plan.json.")}
            ),
            "stderr": "",
        },
        mutation_summary={"status": "changed", "created": [".agentic-workspace/planning/decompositions/ecommerce.json"]},
    )

    assert any("missing execplan files" in warning["message"] for warning in warnings)


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


def test_model_cli_harness_scores_aw_handoff_product_files_as_semantic_failure() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="broad-handoff-aw",
        result={
            "stdout": json.dumps({"response": "Prepared a durable planning note."}),
            "stderr": "",
        },
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/README-CSV-IMPORT.md",
                ".agentic-workspace/planning/execplans/csv-import-first-slice.json",
                "src/sample_app/csv_import.py",
            ],
            "modified": [],
        },
    )

    messages = [warning["message"] for warning in warnings]
    assert any("likely planning artifacts outside canonical" in message for message in messages)
    assert any("product or handoff files" in message for message in messages)


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
            "final_message": ("See [config](" + "C:" + "\\Users\\ricka\\scratch\\repo\\.agentic-workspace\\config.toml#L1)."),
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
    assert any("local absolute path" in message for message in messages)
    assert any("required artifact pattern" in message for message in messages)


def test_model_cli_harness_metadata_scoring_ignores_configured_write_byproducts(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "csv-import",
            "allowed_write_patterns": ["src/**", "tests/**", "README.md"],
            "ignored_write_patterns": ["uv.lock"],
        },
        result={"stdout": "", "stderr": "", "returncode": 0},
        mutation_summary={"status": "changed", "created": ["src/app.py", "uv.lock"], "modified": []},
        repo_path=repo,
    )

    assert not any("outside the scenario's allowed write patterns" in warning["message"] for warning in warnings)


def test_model_cli_harness_flags_no_aw_baseline_contamination(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(
        "# Agent Instructions\n\nThis repository does not use Agentic Workspace.\n",
        encoding="utf-8",
    )

    warnings = harness._metadata_workflow_warnings(
        scenario={"id": "plain-token-baseline", "no_agentic_workspace_baseline": True},
        result={
            "stdout": "\n".join(
                [
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "command_execution",
                                "command": "agentic-workspace start --format json",
                            },
                        }
                    ),
                    json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}),
                ]
            ),
            "stderr": "",
            "returncode": 0,
        },
        mutation_summary={"status": "clean", "created": [], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert any("no-AW baseline was contaminated" in warning["message"] for warning in warnings)


def test_model_cli_harness_requires_explicit_no_aw_fixture_instructions(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={"id": "plain-token-baseline", "no_agentic_workspace_baseline": True},
        result={"stdout": json.dumps({"response": "Done."}), "stderr": "", "returncode": 0},
        mutation_summary={"status": "clean", "created": [], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert any("lacks explicit plain-repo agent instructions" in warning["message"] for warning in warnings)


def test_model_cli_harness_does_not_score_missing_workspace_execution_when_tool_unavailable(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "startup-orientation",
            "required_executed_commands": ["agentic-workspace start"],
        },
        result={
            "stdout": "I attempted `agentic-workspace start --format json`.",
            "stderr": 'Error executing tool run_shell_command: Tool "run_shell_command" not found.',
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert warnings == []


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


def test_model_cli_harness_forbidden_response_phrases_ignore_tool_echo(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "broad-work-decomposition",
            "forbidden_response_phrases": [".agentic-workspace/planning/records/"],
        },
        result={
            "final_message": "Created canonical Planning state and verified summary.",
            "stdout": "WORKFLOW.md says: Do not route durable Planning state to .agentic-workspace/planning/records/.",
            "stderr": "",
        },
        mutation_summary={"status": "changed", "created": [".agentic-workspace/planning/state.toml"]},
        repo_path=repo,
    )

    assert not any("forbidden response phrase" in warning["message"] for warning in warnings)


def test_model_cli_harness_forbidden_response_phrases_ignore_command_prompt_payload(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(
        "# Agent Instructions\n\nThis repository does not use Agentic Workspace.\n",
        encoding="utf-8",
    )

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "plain-token-baseline",
            "no_agentic_workspace_baseline": True,
            "forbidden_response_phrases": ["agentic-workspace"],
        },
        result={
            "stdout": json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": 'codex exec "This prompt mentions agentic-workspace only as injected fixture text."',
                    },
                }
            ),
            "final_message": "Updated README without using the workspace package.",
            "stderr": "",
            "returncode": 0,
        },
        mutation_summary={"status": "changed", "modified": ["README.md"]},
        repo_path=repo,
    )

    assert not any("forbidden response phrase" in warning["message"] for warning in warnings)


def test_model_cli_harness_forbidden_response_phrases_ignore_local_file_link_targets(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(
        "# Agent Instructions\n\nThis repository does not use Agentic Workspace.\n",
        encoding="utf-8",
    )

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "plain-token-baseline",
            "no_agentic_workspace_baseline": True,
            "forbidden_response_phrases": ["agentic-workspace"],
        },
        result={
            "final_message": (
                "Changed [README.md](" + "C:" + "/" + "Users/example/Documents/src/agentic-workspace/scratch/run/repo/README.md)."
            ),
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        },
        mutation_summary={"status": "changed", "modified": ["README.md"]},
        repo_path=repo,
    )

    assert not any("forbidden response phrase" in warning["message"] for warning in warnings)


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


def test_model_cli_harness_does_not_accept_bare_command_for_uv_requirement(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "startup-orientation",
            "required_executed_commands": ["uv run agentic-workspace start"],
        },
        result={
            "stdout": json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": 'agentic-workspace start --task "Fix README" --format json',
                    },
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
        repo_path=repo,
    )

    assert any("did not execute a required command" in warning["message"] for warning in warnings)


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


def test_model_cli_harness_counts_copilot_plain_shell_block_as_executed_command(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = harness._metadata_workflow_warnings(
        scenario={
            "id": "next-decision-output-profile",
            "required_executed_commands": ["uv run agentic-workspace implement --changed"],
        },
        result={
            "stdout": """
● Get implementation guidance for README.md changes (shell)
  │ uv run agentic-workspace implement --changed README.md --task "make a narrow
  │ README.md edit" --format json
  └ 411 lines...
""",
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
                    "response": "I inspected the repository configuration via `agentic-workspace config --target . --format json`.",
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


def test_model_cli_harness_scores_deleted_planning_templates() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={"stdout": json.dumps({"response": "Created a checked-in plan from the template."}), "stderr": ""},
        mutation_summary={
            "status": "changed",
            "created": [".agentic-workspace/planning/execplans/ecommerce.plan.json"],
            "deleted": [".agentic-workspace/planning/execplans/TEMPLATE.plan.json"],
        },
    )

    assert any("deleted shipped planning templates" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_planning_only_side_docs() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="planning-artifact-integrity",
        result={"stdout": json.dumps({"response": "Created a checked-in plan and architecture handoff."}), "stderr": ""},
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/ecommerce.plan.json",
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/ARCHITECTURE.md",
            ],
        },
    )

    assert any("separate architecture or handoff docs" in warning["message"] for warning in warnings)


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

    assert any(signal["id"] == "direct_task_stayed_direct" and signal["status"] == "satisfied" for signal in direct)
    assert any(signal["id"] == "read_surface_entrypoint_used" and signal["status"] == "weak" for signal in direct)
    assert any(signal["id"] == "read_surface_over_read" and signal["status"] == "satisfied" for signal in direct)
    assert any(signal["id"] == "broad_task_created_durable_planning" and signal["status"] == "satisfied" for signal in broad)
    assert any(signal["id"] == "planning_only_avoided_product_scaffold" and signal["status"] == "weak" for signal in broad)
    assert any(signal["id"] == "read_surface_under_read" and signal["status"] == "satisfied" for signal in broad)


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


def test_model_cli_harness_quality_signals_flag_read_surface_over_read() -> None:
    harness = _load_harness()

    signals = harness._quality_signals(
        scenario_id="direct-task-minimal-overhead",
        mutation_summary={"status": "changed", "modified": ["README.md"]},
        warnings=[],
        result={
            "stdout": json.dumps({"response": "I ran agentic-workspace summary --verbose and read .agentic-workspace/planning/state.toml."})
        },
    )

    assert any(signal["id"] == "read_surface_entrypoint_used" and signal["status"] == "satisfied" for signal in signals)
    assert any(signal["id"] == "read_surface_over_read" and signal["status"] == "weak" for signal in signals)


def test_model_cli_harness_reports_small_work_proportionality_metrics() -> None:
    harness = _load_harness()
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "command": "uv run agentic-workspace implement --changed README.md --format json",
                        "aggregated_output": '{"kind":"implementer-context-tiny/v1"}\n',
                        "exit_code": 0,
                        "status": "completed",
                    },
                }
            )
        ]
    )
    result = {"stdout": stdout, "final_message": "Changed README.md and inspected the diff."}
    package_summary = harness._package_read_surface_summary_from_stdout(stdout)

    metrics = harness._proportionality_metrics(
        scenario={"id": "direct-task-minimal-overhead", "proportionality_guardrail": True},
        result=result,
        mutation_summary={"status": "changed", "modified": ["README.md"]},
        package_read_surface_summary=package_summary,
        completion_loop={"requests_to_completion": 1},
    )

    assert metrics["status"] == "present"
    assert metrics["package_command_count"] == 1
    assert metrics["workspace_command_count"] == 1
    assert metrics["changed_files_count"] == 1
    assert metrics["planning_files_created"] == 0
    assert metrics["requests_to_completion"] == 1


def test_model_cli_harness_warns_on_small_work_ceremony() -> None:
    harness = _load_harness()
    long_closeout = "Done. " * 80
    result = {
        "stdout": "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "uv run agentic-workspace summary --verbose",
                            "aggregated_output": "{}\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "Get-Content .agentic-workspace/memory/repo/index.md",
                            "aggregated_output": "# memory\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "pytest",
                            "aggregated_output": "1 passed\n",
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                ),
            ]
        ),
        "final_message": f"I read .agentic-workspace/memory/repo/index.md. {long_closeout}",
    }
    scenario = {
        "id": "direct-task-minimal-overhead",
        "proportionality_guardrail": True,
        "proportionality_limits": {
            "workspace_command_count": 1,
            "verbose_or_full_diagnostic_count": 0,
            "final_answer_length": 40,
        },
        "proportionality_avoid_broad_proof_commands": ["pytest"],
    }
    metrics = harness._proportionality_metrics(
        scenario=scenario,
        result=result,
        mutation_summary={
            "status": "changed",
            "created": [
                ".agentic-workspace/planning/execplans/readme.plan.json",
                ".agentic-workspace/memory/repo/readme.md",
            ],
            "modified": ["README.md"],
        },
        package_read_surface_summary=harness._package_read_surface_summary_from_stdout(result["stdout"]),
    )
    warnings = harness._proportionality_warnings(scenario=scenario, result=result, metrics=metrics)
    classes = {warning["warning_class"] for warning in warnings}
    mistakes = {warning["mistake_class"] for warning in warnings}

    assert "model_cli_proportionality_over_planning" in classes
    assert "model_cli_proportionality_memory_ceremony" in classes
    assert "model_cli_proportionality_over_reading" in classes
    assert "model_cli_proportionality_over_proofing" in classes
    assert "model_cli_proportionality_closeout_ceremony" in classes
    assert {
        "over_planning",
        "memory_ceremony",
        "verbose_diagnostics_for_tiny_task",
        "raw_workspace_spelunking",
        "over_proofing",
        "closeout_ceremony",
    }.issubset(mistakes)


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
    assert "This is not a repository task." in prompt
    assert "Do not run startup commands, inspect paths, read files, search, or edit." in prompt
    assert prompt.startswith("TASK: Analyze a completed model-run transcript")
    assert "Use only the evidence block above." in prompt
    assert "The evidence block is complete for this analysis." in prompt
    assert "EVIDENCE BLOCK START" in prompt
    assert "EVIDENCE BLOCK END" in prompt
    assert "Warnings: Too much raw reading." in prompt
    assert "Mutation: status=clean" in prompt
    assert prompt.index("Warnings:") < prompt.index("Scenario prompt excerpt:")
    assert "What was ambiguous, missing, or more verbose than necessary?" in prompt
    assert "What would have reduced token usage without reducing safety or proof quality?" in prompt
    assert "Did the package make you read too much, too little, or the right amount for this task?" in prompt
    assert "Separate model/provider limitations from product or harness improvements." in prompt
    assert "If a field says none or missing, name that field instead of looking elsewhere." in prompt
    assert "Keep the answer under 200 words." in prompt
    assert len(prompt) < 2200


def test_model_cli_harness_postmortem_prompt_truncates_long_evidence() -> None:
    harness = _load_harness()

    prompt = harness._postmortem_feedback_prompt(
        scenario={"id": "startup-orientation"},
        invocation={
            "scenario_id": "startup-orientation",
            "prompt_variant_id": "default",
            "prompt": "P" * 2000,
            "mutation_summary": {"status": "changed", "created_count": 3, "modified_count": 4, "deleted_count": 0},
            "warnings": [{"warning_class": "model_cli_semantic_workflow_failure", "message": "Raw file scan"}],
            "result": {"final_message": "O" * 2000},
        },
    )

    assert "Warnings: Raw file scan" in prompt
    assert "Mutation: status=changed, created=3, modified=4, deleted=0" in prompt
    assert len(prompt) < 2500


def test_model_cli_harness_postmortem_feedback_warns_on_missing_evidence_claim() -> None:
    harness = _load_harness()

    warnings = harness._postmortem_feedback_warnings(
        result={"stdout": "The evidence block is missing. Please provide the complete evidence.", "stderr": ""}
    )

    assert warnings == [
        {
            "warning_class": "model_cli_postmortem_feedback_failure",
            "message": "The postmortem agent claimed supplied evidence was missing.",
        }
    ]


def test_model_cli_harness_postmortem_feedback_warns_on_repo_inspection() -> None:
    harness = _load_harness()

    warnings = harness._postmortem_feedback_warnings(
        result={"stdout": "● Read AGENTS.md\n✗ List files (shell)\nPermission denied", "stderr": ""}
    )

    messages = [warning["message"] for warning in warnings]
    assert "The postmortem agent inspected files or attempted commands despite the no-inspection rule." in messages


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


def test_model_cli_harness_scores_incomplete_handoff_packet() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="handoff-packet-contents",
        result={"stdout": json.dumps({"response": "I will tell the next executor to do the task and report back."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    assert any("omitted key worker-packet fields" in warning["message"] for warning in warnings)


def test_model_cli_harness_accepts_complete_handoff_packet() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="capability-fit-routing",
        prompt_variant_id="handoff-packet-contents",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "Handoff: intent, constraints, read-first refs, owned scope, proof expectations, "
                        "stop conditions, target posture, and return contract with proof result and residue."
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


def test_model_cli_harness_records_capability_routing_followed() -> None:
    harness = _load_harness()

    evaluation = harness._capability_routing_evaluation(
        scenario_id="capability-fit-routing",
        prompt_variant_id="weak-target-high-judgment",
        result={"final_message": "Escalate to a stronger planner before implementation."},
        warnings=[],
    )

    assert evaluation["status"] == "followed"
    assert evaluation["followed_delegation_decision"] is True
    assert evaluation["expected_action"] == "escalate-or-handoff-before-execution"
    assert evaluation["startup_or_config_evidence_used"] is True


def test_model_cli_harness_records_capability_routing_ignored_with_feedback_status() -> None:
    harness = _load_harness()

    evaluation = harness._capability_routing_evaluation(
        scenario_id="capability-fit-routing",
        prompt_variant_id="handoff-packet-contents",
        result={"final_message": "I will tell the next executor to do the work."},
        warnings=[
            {
                "warning_class": "model_cli_semantic_workflow_failure",
                "message": "The handoff packet variant omitted key worker-packet fields.",
            },
            {
                "warning_class": "model_cli_metadata_scoring_failure",
                "message": "The agent did not execute a required command.",
            },
        ],
        postmortem_feedback={
            "status": "unsupported",
            "warnings": [{"warning_class": "model_cli_postmortem_feedback_unsupported"}],
        },
    )

    assert evaluation["status"] == "ignored-or-misread"
    assert evaluation["followed_delegation_decision"] is False
    assert evaluation["expected_action"] == "prepare-complete-worker-packet-and-return-contract"
    assert evaluation["semantic_failure_count"] == 1
    assert evaluation["required_command_miss_count"] == 1
    assert evaluation["postmortem_feedback"]["status"] == "unsupported"
    assert evaluation["postmortem_feedback"]["warning_count"] == 1


def test_model_cli_harness_aggregates_capability_routing_evaluations() -> None:
    harness = _load_harness()

    summary = harness._aggregate_capability_routing_evaluations(
        [
            {"capability_routing_evaluation": {"status": "followed"}},
            {"capability_routing_evaluation": {"status": "ignored-or-misread"}},
            {"capability_routing_evaluation": {"status": "followed-with-hygiene-warning"}},
        ]
    )

    assert summary["status"] == "present"
    assert summary["result_count"] == 3
    assert summary["followed_count"] == 1
    assert summary["ignored_or_misread_count"] == 1
    assert summary["followed_with_hygiene_warning_count"] == 1


def test_model_cli_harness_scores_intent_satisfaction_conflation() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="intent-satisfaction-review",
        prompt_variant_id="passed-tests-partial-intent",
        result={"stdout": json.dumps({"response": "Tests passed, so the original intent is satisfied and complete."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("broader human intent" in message for message in messages)
    assert any("did not route" in message for message in messages)


def test_model_cli_harness_accepts_partial_intent_routing() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="intent-satisfaction-review",
        prompt_variant_id="passed-tests-partial-intent",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "Validation proof passed, but the larger intent is only partially satisfied. "
                        "Local task completion, tests, intent satisfaction, durable residue, and follow-up are separate; "
                        "route a repo-visible planning follow-up for the remaining docs positioning work."
                    )
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


def test_model_cli_harness_scores_vague_outcome_solution_jump() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="intent-satisfaction-review",
        prompt_variant_id="vague-outcome-trust",
        result={"stdout": json.dumps({"response": "I will implement a new README section and write code now."}), "stderr": ""},
        mutation_summary={"status": "clean"},
    )

    messages = [warning["message"] for warning in warnings]
    assert any("did not restate the intended outcome" in message for message in messages)
    assert any("jumped to a solution" in message for message in messages)
    assert not any("local completion" in message for message in messages)


def test_model_cli_harness_scores_vague_outcome_raw_reads_without_compact_startup() -> None:
    harness = _load_harness()

    raw_read_outputs = [
        (
            "posix",
            "Read .agentic-workspace/WORKFLOW.md\n"
            "Read .agentic-workspace/planning/schemas/planning-review.schema.json\n"
            "The intended outcome is handoff trust. Inspect planning-review.schema.json first. "
            "Satisfaction evidence is structured review proof.",
        ),
        (
            "windows",
            "Read .agentic-workspace\\WORKFLOW.md\n"
            "Read .agentic-workspace\\planning\\schemas\\planning-review.schema.json\n"
            "The intended outcome is handoff trust. Inspect planning-review.schema.json first. "
            "Satisfaction evidence is structured review proof.",
        ),
        (
            "later-compact-mention",
            "Read .agentic-workspace\\WORKFLOW.md\n"
            "The intended outcome is handoff trust. Inspect planning first. "
            "Satisfaction evidence is structured proof. Later, a next agent could run "
            "agentic-workspace summary --target . --format json.",
        ),
    ]
    for label, stdout in raw_read_outputs:
        warnings = harness._semantic_workflow_warnings(
            scenario_id="intent-satisfaction-review",
            prompt_variant_id="vague-outcome-trust",
            result={"stdout": stdout, "stderr": ""},
            mutation_summary={"status": "clean"},
        )

        messages = [warning["message"] for warning in warnings]
        assert any("raw workspace files before using compact startup" in message for message in messages), label


def test_model_cli_harness_accepts_vague_outcome_raw_reads_after_compact_startup() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="intent-satisfaction-review",
        prompt_variant_id="vague-outcome-trust",
        result={
            "stdout": (
                'Ran agentic-workspace preflight --task "trust handoff" --format json. '
                "The intended outcome is handoff trust. Inspect summary first, then planning only if routed. "
                "Satisfaction evidence is a repo-visible closeout proof and follow-up route."
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


def test_model_cli_harness_accepts_vague_outcome_resolution() -> None:
    harness = _load_harness()

    warnings = harness._semantic_workflow_warnings(
        scenario_id="intent-satisfaction-review",
        prompt_variant_id="vague-outcome-less-rework",
        result={
            "stdout": json.dumps(
                {
                    "response": (
                        "The intended outcome is less rework by preserving user intent across handoff. "
                        "First inspect preflight and planning summary, then define satisfaction criteria: evidence that "
                        "closeout separates proof, intent, residue, and follow-up. This does not choose a solution yet."
                    )
                }
            ),
            "stderr": "",
        },
        mutation_summary={"status": "clean"},
    )

    assert warnings == []


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


def test_model_cli_harness_snapshot_ignores_ephemeral_runtime_dirs(tmp_path: Path) -> None:
    harness = _load_harness()
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
    before = harness._file_snapshot(repo)
    (repo / ".venv" / "Lib").mkdir(parents=True)
    (repo / ".venv" / "Lib" / "dependency.py").write_text("# generated\n", encoding="utf-8")
    (repo / ".pytest_cache").mkdir()
    (repo / ".pytest_cache" / "CACHEDIR.TAG").write_text("cache\n", encoding="utf-8")
    (repo / ".git").mkdir()
    (repo / ".git" / "index").write_text("index\n", encoding="utf-8")
    (repo / "src" / "app.py").write_text("print('changed')\n", encoding="utf-8")
    after = harness._file_snapshot(repo)

    diff = harness._snapshot_diff(before, after)

    assert diff["created"] == []
    assert diff["modified"] == ["src/app.py"]


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
                    {"warning_class": "model_cli_adapter_tooling_limitation", "message": "tooling limit"},
                ],
            }
        ]
    )

    assert classification["finding_count"] == 3
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
                        "proportionality_metrics": {
                            "status": "present",
                            "workspace_command_count": 1,
                            "package_output_bytes": 100,
                        },
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
                        "proportionality_metrics": {
                            "status": "present",
                            "workspace_command_count": 3,
                            "package_output_bytes": 260,
                        },
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
    assert comparison["proportionality_delta"]["workspace_command_count"] == 2
    assert comparison["proportionality_delta"]["package_output_bytes"] == 160
