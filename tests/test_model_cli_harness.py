from __future__ import annotations

import importlib.util
import json
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
    assert payload["model"] == "gemini-3-flash"
    assert result["result"]["status"] == "dry-run"
    assert result["command"][0:5] == [
        "gemini",
        "--model",
        "gemini-3-flash",
        "--prompt",
        result["prompt"],
    ]
    assert "--approval-mode" in result["command"]
    assert "--include-directories" in result["command"]
    assert result["repo_path"] in result["command"]


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
