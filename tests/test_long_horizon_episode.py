from __future__ import annotations

import importlib.util
import json
import posixpath
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "scripts" / "model_cli_harness"
EPISODE_PATH = HARNESS_DIR / "long_horizon_episode.py"


def _load_episode_module():
    if str(HARNESS_DIR) not in sys.path:
        sys.path.insert(0, str(HARNESS_DIR))
    spec = importlib.util.spec_from_file_location("long_horizon_episode", EPISODE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_suite(tmp_path: Path, *, evaluator_code: str | None = None) -> Path:
    fixtures = tmp_path / "fixtures"
    for fixture_name in ("aw-fixture", "baseline-fixture"):
        fixture = fixtures / fixture_name
        fixture.mkdir(parents=True)
        (fixture / "README.md").write_text(f"{fixture_name}\n", encoding="utf-8")
    (fixtures / "aw-fixture" / ".agentic-workspace").mkdir()
    (fixtures / "aw-fixture" / "AGENTS.md").write_text("Use AW.\n", encoding="utf-8")

    writer_code = (
        "import pathlib, sys; "
        "repo = pathlib.Path(sys.argv[1]); "
        "phase = sys.argv[2]; "
        "share = pathlib.Path(sys.argv[3]); "
        "prompt = sys.argv[4]; "
        "(repo / (phase + '.txt')).write_text(prompt, encoding='utf-8'); "
        "share.write_text('phase ' + phase, encoding='utf-8')"
    )
    if evaluator_code is None:
        evaluator_code = (
            "import json, pathlib, sys; "
            "repo = pathlib.Path(sys.argv[1]); "
            "share = pathlib.Path(sys.argv[3]); "
            "prompt = sys.argv[4]; "
            "(repo / 'evaluator-prompt.txt').write_text(prompt, encoding='utf-8'); "
            "share.write_text(json.dumps({"
            "'kind': 'agentic-workspace/long-horizon-evaluation/v1', "
            "'scenario': 'toy', "
            "'mode': 'aw-assisted', "
            "'result': {"
            "'intent_satisfied': 'partial', "
            "'scope_respected': True, "
            "'proof_sufficient': False, "
            "'proof_matches_intent': False, "
            "'restartable_from_repo_state': True, "
            "'completion_claim_honest': True"
            "}, "
            "'mistake_classes': ['weak_proof'], "
            "'aw_effect': {'helped': ['repo state'], 'hurt_or_overhead': [], 'missed_affordance': ['proof hint']}, "
            "'evidence': [{'kind': 'file', 'ref': 'README.md', 'why': 'fixture evidence'}], "
            "'human_review_required': True, "
            "'recommended_followup': {'type': 'issue', 'summary': 'tighten proof affordance'}"
            "}), encoding='utf-8')"
        )

    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit-long-horizon",
                "adapters": {
                    "fake-a": {
                        "default_model": "fake-a-model",
                        "block_on_preflight_failure": False,
                        "command": [sys.executable, "-c", writer_code, "{repo}", "{phase_id}", "{share_path}", "{prompt}"],
                    },
                    "fake-b": {
                        "default_model": "fake-b-model",
                        "block_on_preflight_failure": False,
                        "command": [sys.executable, "-c", writer_code, "{repo}", "{phase_id}", "{share_path}", "{prompt}"],
                    },
                    "fake-evaluator": {
                        "default_model": "fake-eval-model",
                        "block_on_preflight_failure": False,
                        "command": [sys.executable, "-c", evaluator_code, "{repo}", "{phase_id}", "{share_path}", "{prompt}"],
                    },
                    "fake-sbx": {
                        "default_model": "fake-sbx-model",
                        "block_on_preflight_failure": False,
                        "sandbox": {
                            "backend": "docker-sandbox",
                            "agent": "codex",
                            "template": "docker/sandbox-templates:codex",
                        },
                        "command": [sys.executable, "-c", writer_code, "{repo}", "{phase_id}", "{share_path}", "{prompt}"],
                    },
                },
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    return suite


def _write_episode(tmp_path: Path, *, evaluator: bool = True, modes: list[dict] | None = None) -> Path:
    episode = {
        "kind": "agentic-workspace/long-horizon-episode/v1",
        "id": "toy-continuity",
        "title": "Toy continuity episode",
        "task_prompt": "Complete the toy task.",
        "modes": modes
        or [
            {"id": "aw-assisted", "aw_enabled": True, "fixture": "aw-fixture"},
        ],
        "visible_validation_commands": [[sys.executable, "-c", "print('validation-ok')"]],
        "hidden_oracle": {"secret": "do-not-leak-reference"},
        "phases": [
            {
                "id": "phase-one",
                "prompt": "Record secret-from-phase-one.",
                "adapter": "fake-a",
            },
            {
                "id": "phase-two",
                "prompt": "Resume without prior chat.",
                "adapter": "fake-b",
                "hide_transcript_for_resume": True,
            },
        ],
        "known_traps": ["restart"],
        "expected_mistake_classes": ["weak_proof", "restart_failed"],
        "rubric": {"intent_satisfied": "Toy task completes."},
    }
    if evaluator:
        episode["evaluator"] = {"adapter": "fake-evaluator"}
    path = tmp_path / "episode.json"
    path.write_text(json.dumps(episode), encoding="utf-8")
    return path


def test_long_horizon_episode_validates_sample_pack_and_schema_files() -> None:
    module = _load_episode_module()

    schema_dir = REPO_ROOT / "tools" / "model-cli-harness" / "schemas"
    episode_schema = json.loads((schema_dir / "long-horizon-episode.schema.json").read_text(encoding="utf-8"))
    evaluation_schema = json.loads((schema_dir / "long-horizon-evaluation.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(episode_schema)
    Draft202012Validator.check_schema(evaluation_schema)
    episode_validator = Draft202012Validator(episode_schema)
    evaluation_validator = Draft202012Validator(evaluation_schema)

    assert episode_schema["$id"] == module.EPISODE_KIND
    assert evaluation_schema["$id"] == module.EVALUATION_KIND

    episode_dir = REPO_ROOT / "tools" / "model-cli-harness" / "episodes"
    for path in [
        episode_dir / "intent-proof-packaging-specifier.json",
        episode_dir / "reuse-abstraction-pluggy.json",
        episode_dir / "intent-proof-click-pager.json",
        episode_dir / "managed-planning-state-agentic-workspace.json",
    ]:
        episode = module.load_episode(path)
        episode_validator.validate(episode)
        assert episode["modes"]
        assert episode["visible_validation_commands"]

    evaluation_validator.validate(
        {
            "kind": module.EVALUATION_KIND,
            "scenario": "schema-smoke",
            "mode": "aw-assisted",
            "result": {
                "intent_satisfied": "partial",
                "scope_respected": True,
                "proof_sufficient": False,
                "proof_matches_intent": False,
                "restartable_from_repo_state": True,
                "completion_claim_honest": True,
            },
            "mistake_classes": ["weak_proof"],
            "aw_effect": {
                "helped": [],
                "hurt_or_overhead": [],
                "missed_affordance": ["reference comparison"],
            },
            "evidence": [{"kind": "file", "ref": "README.md"}],
            "human_review_required": True,
            "recommended_followup": {"type": "harness", "summary": "schema smoke"},
        }
    )


def test_long_horizon_episode_rejects_unknown_mistake_class(tmp_path: Path) -> None:
    module = _load_episode_module()
    path = _write_episode(tmp_path)
    episode = json.loads(path.read_text(encoding="utf-8"))
    episode["expected_mistake_classes"] = ["not-a-real-class"]

    try:
        module.validate_episode(episode)
    except ValueError as exc:
        assert "unknown mistake classes" in str(exc)
    else:
        raise AssertionError("expected invalid mistake class to fail")


def test_long_horizon_episode_rejects_malformed_evaluation_contract(tmp_path: Path) -> None:
    module = _load_episode_module()
    schema_path = REPO_ROOT / "tools" / "model-cli-harness" / "schemas" / "long-horizon-episode.schema.json"
    episode_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    episode_validator = Draft202012Validator(episode_schema)
    path = _write_episode(tmp_path)
    episode = json.loads(path.read_text(encoding="utf-8"))

    episode["evaluation_contract"] = {
        "blocked_full_completion": [
            {
                "mistake_class": "weak_proof",
                "reason": "misspelled gate key should not be accepted",
            }
        ]
    }
    assert list(episode_validator.iter_errors(episode))
    try:
        module.validate_episode(episode)
    except ValueError as exc:
        assert "unknown fields" in str(exc)
    else:
        raise AssertionError("expected misspelled contract key to fail")

    episode["evaluation_contract"] = {
        "blocked_full_completion_when": [
            {
                "reason": "missing mistake class would silently fail to gate claims",
            }
        ]
    }
    assert list(episode_validator.iter_errors(episode))
    try:
        module.validate_episode(episode)
    except ValueError as exc:
        assert "mistake_class is required" in str(exc)
    else:
        raise AssertionError("expected missing mistake_class to fail")


def test_long_horizon_episode_runs_two_phase_hidden_restart(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(tmp_path)

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=True,
        evaluator=False,
    )

    mode = payload["modes"][0]
    repo = Path(mode["repo_path"])
    phase_one = (repo / "phase-one.txt").read_text(encoding="utf-8")
    phase_two = (repo / "phase-two.txt").read_text(encoding="utf-8")

    assert "secret-from-phase-one" in phase_one
    assert "secret-from-phase-one" not in phase_two
    assert "Resume from repository state only" in phase_two
    assert mode["phases"][1]["prior_transcript_included"] is False
    assert mode["phases"][1]["mutation_summary"]["modified"] == []
    assert mode["phases"][1]["validation_results"][0]["returncode"] == 0


def test_long_horizon_episode_records_agent_switch_and_aw_modes(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(
        tmp_path,
        evaluator=False,
        modes=[
            {"id": "baseline", "aw_enabled": False, "fixture": "baseline-fixture"},
            {"id": "aw-assisted", "aw_enabled": True, "fixture": "aw-fixture"},
        ],
    )

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
    )

    assert payload["mode_count"] == 2
    assert [mode["aw_enabled"] for mode in payload["modes"]] == [False, True]
    for mode in payload["modes"]:
        assert [phase["adapter_id"] for phase in mode["phases"]] == ["fake-a", "fake-b"]
        assert [phase["model"] for phase in mode["phases"]] == ["fake-a-model", "fake-b-model"]


def test_long_horizon_episode_supports_same_agent_phase_override(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(
        tmp_path,
        evaluator=False,
        modes=[
            {
                "id": "same-agent",
                "aw_enabled": True,
                "fixture": "aw-fixture",
                "phase_overrides": {
                    "phase-two": {
                        "adapter": "fake-a",
                        "model": "same-agent-model",
                        "prompt": "Resume as the same agent.",
                    }
                },
            },
        ],
    )

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
    )

    phases = payload["modes"][0]["phases"]
    assert [phase["adapter_id"] for phase in phases] == ["fake-a", "fake-a"]
    assert phases[1]["model"] == "same-agent-model"
    assert "Resume as the same agent" in phases[1]["prompt"]


def test_long_horizon_episode_cli_adapter_override_marks_sandbox(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(tmp_path)

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        adapter_override="fake-sbx",
        evaluator_adapter_override="fake-sbx",
    )

    mode = payload["modes"][0]
    assert {phase["adapter_id"] for phase in mode["phases"]} == {"fake-sbx"}
    assert {phase["sandbox"]["evidence"] for phase in mode["phases"]} == {"sandbox-backed"}
    assert mode["evaluation"]["adapter_id"] == "fake-sbx"
    assert mode["evaluation"]["sandbox"]["identity"] == "docker-sandbox:codex:fake-sbx"


def test_long_horizon_episode_comparison_reports_same_agent_vs_switch(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(
        tmp_path,
        evaluator=False,
        modes=[
            {"id": "agent-switch", "aw_enabled": True, "fixture": "aw-fixture"},
            {
                "id": "same-agent",
                "aw_enabled": True,
                "fixture": "aw-fixture",
                "phase_overrides": {
                    "phase-two": {
                        "adapter": "fake-a",
                    }
                },
            },
        ],
    )

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
    )

    comparison = payload["comparison"]["continuation_comparison"]
    kinds = {mode["mode_id"]: mode["continuation_kind"] for mode in comparison["modes"]}
    assert comparison["status"] == "present"
    assert comparison["has_same_agent_continuation"] is True
    assert comparison["has_agent_switch_continuation"] is True
    assert comparison["continuation_contribution_by_mode"]["agent-switch"] == "no-op"
    assert kinds == {
        "agent-switch": "agent-switch-continuation",
        "same-agent": "same-agent-continuation",
    }


def test_long_horizon_episode_paths_stay_short_for_windows_clone(tmp_path: Path) -> None:
    module = _load_episode_module()

    paths = module._episode_paths(
        episode={"id": "very-long-real-repository-episode-id-that-would-otherwise-expand-the-run-directory"},
        mode_id="aw-assisted-restart-with-a-verbose-mode-name",
        output_root=tmp_path,
    )

    assert len(paths.run_root.name) <= 70
    assert paths.repo_path == paths.run_root / "repo"


def test_long_horizon_episode_bootstraps_aw_mode_for_pinned_repo_dry_run(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(
        tmp_path,
        evaluator=False,
        modes=[
            {
                "id": "baseline",
                "aw_enabled": False,
                "repo_url": "https://example.invalid/repo.git",
                "base_commit": "abc123",
            },
            {
                "id": "aw-assisted",
                "aw_enabled": True,
                "repo_url": "https://example.invalid/repo.git",
                "base_commit": "abc123",
            },
        ],
    )

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
    )

    baseline_repo = Path(payload["modes"][0]["repo_path"])
    aw_repo = Path(payload["modes"][1]["repo_path"])

    assert not (baseline_repo / ".agentic-workspace").exists()
    assert (aw_repo / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert "uv run agentic-workspace start" in (aw_repo / "AGENTS.md").read_text(encoding="utf-8")
    assert 'cli_invoke = "uv run agentic-workspace"' in (aw_repo / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")
    setup_summary = payload["modes"][1]["setup_mutation_summary"]
    assert setup_summary["status"] == "clean"
    assert setup_summary["raw_status"] == "changed"
    assert setup_summary["harness_setup_count"] > 0


def test_long_horizon_episode_bootstraps_aw_mode_into_configured_startup_file(tmp_path: Path) -> None:
    module = _load_episode_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".agentic-workspace").mkdir()
    (repo / ".agentic-workspace" / "config.toml").write_text(
        'schema_version = 1\n\n[workspace]\nagent_instructions_file = "GEMINI.md"\n',
        encoding="utf-8",
    )
    (repo / "GEMINI.md").write_text("# Gemini\n", encoding="utf-8")

    module._bootstrap_aw_mode(repo)

    assert "<!-- agentic-workspace:workflow:start -->" in (repo / "GEMINI.md").read_text(encoding="utf-8")
    assert not (repo / "AGENTS.md").exists()


def test_long_horizon_episode_evaluator_excludes_hidden_oracle_and_reports_comparison(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(tmp_path)

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=True,
        evaluator=True,
    )

    mode = payload["modes"][0]
    repo = Path(mode["repo_path"])
    evaluator_prompt = (repo / "evaluator-prompt.txt").read_text(encoding="utf-8")

    assert mode["evaluation"]["status"] == "valid"
    assert mode["evaluation"]["hidden_oracle_excluded"] is True
    assert mode["evaluation"]["post_score_reference"]["status"] == "available-after-primary-score"
    assert mode["evaluation"]["post_score_reference"]["reference"]["secret"] == "do-not-leak-reference"
    assert payload["comparison"]["post_score_reference_by_mode"]["aw-assisted"]["status"] == "available-after-primary-score"
    assert "do-not-leak-reference" not in evaluator_prompt
    assert payload["comparison"]["mistake_classes"] == ["weak_proof"]
    assert payload["comparison"]["human_review_required"] is True
    assert payload["comparison"]["recommended_followups"][0]["type"] == "issue"


def test_long_horizon_episode_contract_blocks_full_completion_on_configured_mistake(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path)
    episode = _write_episode(tmp_path)
    episode_payload = json.loads(episode.read_text(encoding="utf-8"))
    episode_payload["evaluation_contract"] = {
        "issue_refs": ["#1917"],
        "failure_path_summary": "Visible tests passed, but semantic proof stayed narrow.",
        "agent_facing_claim_boundary": "Visible validation success is not semantic proof sufficiency.",
        "required_reconciliation": ["Run broader semantic checks before claiming full completion."],
        "blocked_full_completion_when": [
            {
                "mistake_class": "weak_proof",
                "reason": "The proof path is too narrow for the intent.",
            }
        ],
    }
    episode.write_text(json.dumps(episode_payload), encoding="utf-8")

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=True,
        evaluator=True,
    )

    mode = payload["modes"][0]
    evaluator_prompt = (Path(mode["repo_path"]) / "evaluator-prompt.txt").read_text(encoding="utf-8")
    phase_prompt = mode["phases"][0]["prompt"]
    assessment = mode["evaluation"]["contract_assessment"]

    assert "Completion and proof guidance for this episode" in phase_prompt
    assert "Visible validation success is not semantic proof sufficiency" in phase_prompt
    assert "Run broader semantic checks before claiming full completion." in phase_prompt
    assert "Visible validation success is not semantic proof sufficiency" in evaluator_prompt
    assert assessment["status"] == "full-completion-blocked"
    assert assessment["claim_level"] == "partial-progress"
    assert assessment["blocking_rules"][0]["mistake_class"] == "weak_proof"
    assert payload["comparison"]["claim_gate"]["status"] == "full-completion-blocked"
    assert payload["comparison"]["claim_gate"]["blocking_modes"] == ["aw-assisted"]


def test_long_horizon_episode_invalid_evaluator_json_is_failure(tmp_path: Path) -> None:
    module = _load_episode_module()
    suite = _write_suite(tmp_path, evaluator_code="import pathlib, sys; pathlib.Path(sys.argv[3]).write_text('not json', encoding='utf-8')")
    episode = _write_episode(tmp_path)

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=True,
        evaluator=True,
    )

    evaluation = payload["modes"][0]["evaluation"]
    assert evaluation["status"] == "invalid"
    assert "evaluator did not return" in evaluation["payload"]["error"]
    assert payload["comparison"]["human_review_required"] is True
    assert payload["comparison"]["claim_gate"]["status"] == "invalid-primary-evaluation"
    assert payload["comparison"]["invalid_evaluations_by_mode"]["aw-assisted"]["schema_errors"]
    assert payload["comparison"]["recommended_followups"][0]["type"] == "evaluation-harness"


def test_long_horizon_episode_repairs_missing_evaluator_identity_from_context(tmp_path: Path) -> None:
    module = _load_episode_module()
    evaluator_code = (
        "import json, pathlib, sys; "
        "share = pathlib.Path(sys.argv[3]); "
        "share.write_text(json.dumps({"
        "'kind': 'agentic-workspace/long-horizon-evaluation/v1', "
        "'mode': 'aw-assisted', "
        "'result': {"
        "'intent_satisfied': 'yes', "
        "'scope_respected': True, "
        "'proof_sufficient': True, "
        "'proof_matches_intent': True, "
        "'restartable_from_repo_state': True, "
        "'completion_claim_honest': True"
        "}, "
        "'mistake_classes': [], "
        "'aw_effect': {'helped': [], 'hurt_or_overhead': [], 'missed_affordance': []}, "
        "'evidence': [{'kind': 'summary', 'ref': 'final', 'why': 'context identity repair'}]"
        "}), encoding='utf-8')"
    )
    suite = _write_suite(tmp_path, evaluator_code=evaluator_code)
    episode = _write_episode(tmp_path)

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=True,
        evaluator=True,
    )

    evaluation = payload["modes"][0]["evaluation"]
    assert evaluation["status"] == "valid"
    assert evaluation["payload"]["scenario"] == "toy-continuity"
    assert evaluation["payload"]["harness_repairs"] == ["filled missing scenario from episode context"]
    assert payload["comparison"]["invalid_evaluations_by_mode"] == {}


def test_long_horizon_episode_evaluator_prompt_compacts_bulky_phase_output() -> None:
    module = _load_episode_module()
    large_stdout = "large stdout line\n" * 5000
    prompt = module._evaluation_prompt(
        episode={
            "id": "compact-evaluator",
            "title": "Compact evaluator",
            "rubric": {},
            "known_traps": [],
            "expected_mistake_classes": [],
        },
        mode_result={
            "mode_id": "aw-assisted",
            "aw_enabled": True,
            "repo_path": posixpath.join(posixpath.sep, "tmp", "repo"),
            "run_root": posixpath.join(posixpath.sep, "tmp", "run"),
            "setup_mutation_summary": {"status": "clean"},
            "setup_results": [],
            "phases": [
                {
                    "phase_id": "repair",
                    "adapter_id": "codex-sbx",
                    "model": "gpt-test",
                    "prompt": large_stdout,
                    "result": {"status": "completed", "returncode": 0, "stdout": large_stdout, "final_message": "done"},
                    "validation_results": [{"command": ["check"], "returncode": 0, "stdout": large_stdout}],
                    "mutation_summary": {
                        "status": "changed",
                        "created": ["src/pkg.py", *[f".venv/Lib/site-packages/pkg{index}.py" for index in range(100)]],
                    },
                    "sandbox_failure": {"status": "absent"},
                }
            ],
        },
    )

    payload = json.loads(prompt.split("Evidence bundle:\n", 1)[1])
    phase = payload["mode_result"]["phases"][0]

    assert len(prompt) < 40_000
    assert '"scenario": "compact-evaluator"' in prompt
    assert payload["compaction"]["kind"] == "agentic-workspace/long-horizon-evaluator-compaction/v1"
    assert phase["prompt"]["truncated"] is True
    assert phase["result"]["stdout"]["truncated"] is True
    assert phase["result"]["stdout"]["char_count"] == len(large_stdout)
    assert phase["result"]["final_message"]["text"] == "done"
    assert phase["validation_results"][0]["stdout"]["truncated"] is True
    assert phase["mutation_summary"]["created"]["items"] == ["src/pkg.py"]
    assert phase["mutation_summary"]["created"]["omitted_noisy_count"] == 100
    assert ".venv/Lib/site-packages/pkg99.py" not in prompt


def test_long_horizon_episode_sandbox_timeout_is_executor_followup() -> None:
    module = _load_episode_module()
    comparison = module._comparison_summary(
        [
            {
                "mode_id": "managed-state",
                "aw_enabled": True,
                "phases": [
                    {
                        "phase_id": "repair",
                        "sandbox_failure": {
                            "status": "present",
                            "failure_class": "sandbox-timeout",
                            "boundary": "sandbox-executor-timeout",
                            "phase_id": "repair",
                            "sandbox": "docker-sandbox:codex:codex-sbx",
                            "sandbox_name": "aw-lh-123",
                            "share_artifact_exists": False,
                            "transcript_exists": False,
                        },
                    }
                ],
                "evaluation": {"status": "not-run", "payload": {"status": "not-run"}},
            }
        ]
    )

    followup = comparison["recommended_followups"][0]
    assert comparison["human_review_required"] is True
    assert comparison["sandbox_runtime_failures_by_mode"]["managed-state"][0]["boundary"] == "sandbox-executor-timeout"
    assert followup["type"] == "rerun-executor"
    assert followup["phase_id"] == "repair"
    assert followup["sandbox_name"] == "aw-lh-123"
    assert followup["share_artifact_exists"] is False
    assert followup["transcript_exists"] is False
    assert followup["aw_improvement_scope"] == "separate-from-agent-performance-finding"


def test_long_horizon_episode_preflights_windows_external_clone_longpaths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_episode_module()
    long_root = tmp_path / ("very-long-output-root-" + ("x" * 170))
    paths = module.harness.HarnessPaths(
        run_root=long_root,
        fixture_root=long_root / "fixture",
        repo_path=long_root / "repo",
        transcript_path=long_root / "transcript.jsonl",
        share_path=long_root / "share.md",
    )

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(
        module.harness,
        "_run_command",
        lambda command, *, cwd, timeout_seconds, env=None: {"returncode": 1, "stdout": "", "stderr": ""},
    )

    with pytest.raises(RuntimeError, match="core.longpaths true"):
        module._prepare_mode_repo(
            suite_path=tmp_path / "suites" / "suite.json",
            mode={"id": "external", "repo_url": "https://example.invalid/repo.git", "base_commit": "abc123"},
            paths=paths,
            execute=True,
        )


def test_long_horizon_episode_uses_model_args_by_phase_model(tmp_path: Path) -> None:
    module = _load_episode_module()
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "repo"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("repo\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "fake": {
                        "default_model": "haiku",
                        "model_args": ["--effort", "low"],
                        "model_args_by_model": {"haiku": []},
                        "command": ["fake", "--model", "{model}", "{model_args}", "-p", "{prompt}"],
                    }
                },
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    episode_payload = {
        "kind": "agentic-workspace/long-horizon-episode/v1",
        "id": "model-args",
        "title": "Model args",
        "task_prompt": "Run phases.",
        "modes": [{"id": "mode", "aw_enabled": False, "fixture": "repo"}],
        "visible_validation_commands": [[sys.executable, "-c", "print('ok')"]],
        "phases": [
            {"id": "phase-one", "prompt": "Use default.", "adapter": "fake"},
            {"id": "phase-two", "prompt": "Use sonnet.", "adapter": "fake", "model": "sonnet"},
        ],
        "known_traps": ["model-options"],
        "expected_mistake_classes": ["restart_failed"],
        "rubric": {"intent_satisfied": "phases run"},
    }
    episode = tmp_path / "episode-model-args.json"
    episode.write_text(json.dumps(episode_payload), encoding="utf-8")
    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
    )

    commands = [phase["command"] for phase in payload["modes"][0]["phases"]]
    assert "--effort" not in commands[0]
    assert commands[1][commands[1].index("--effort") + 1] == "low"


def test_long_horizon_episode_adapter_override_uses_override_adapter_default_model(tmp_path: Path) -> None:
    module = _load_episode_module()
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "repo"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("repo\n", encoding="utf-8")
    suite = tmp_path / "suites" / "suite.json"
    suite.parent.mkdir()
    suite.write_text(
        json.dumps(
            {
                "schema": "agentic-workspace/model-cli-harness-suite/v1",
                "id": "unit",
                "adapters": {
                    "native": {
                        "default_model": "native-default",
                        "command": ["native", "--model", "{model}", "{prompt}"],
                    },
                    "override": {
                        "default_model": "override-default",
                        "command": ["override", "--model", "{model}", "{prompt}"],
                    },
                },
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    episode_payload = {
        "kind": "agentic-workspace/long-horizon-episode/v1",
        "id": "adapter-override-model",
        "title": "Adapter override model",
        "task_prompt": "Run phase.",
        "modes": [{"id": "mode", "aw_enabled": False, "fixture": "repo"}],
        "phases": [{"id": "phase-one", "prompt": "Do work.", "adapter": "native", "model": "native-special"}],
        "known_traps": ["model-options"],
        "expected_mistake_classes": ["restart_failed"],
        "rubric": {"intent_satisfied": "override adapter default is used"},
    }
    episode = tmp_path / "episode-adapter-override-model.json"
    episode.write_text(json.dumps(episode_payload), encoding="utf-8")

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=False,
        adapter_override="override",
    )

    command = payload["modes"][0]["phases"][0]["command"]
    assert command[:3] == ["override", "--model", "override-default"]
    assert "native-special" not in command


def test_long_horizon_episode_evaluator_uses_prompt_file_transport(tmp_path: Path) -> None:
    module = _load_episode_module()
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "repo"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("repo\n", encoding="utf-8")
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
                        "command": [sys.executable, "-c", "import sys; sys.exit(0)", "{repo}", "{phase_id}", "{share_path}", "{prompt}"],
                    },
                    "fake-evaluator": {
                        "default_model": "fake-eval-model",
                        "block_on_preflight_failure": False,
                        "prompt_transport": {
                            "threshold_chars": 20,
                            "mode": "file-attachment",
                            "file_args": ["--attachment", "{prompt_file}"],
                            "file_prompt": "Read {prompt_file}.",
                        },
                        "command": [
                            sys.executable,
                            "-c",
                            "import sys; sys.exit(0)",
                            "{repo}",
                            "{phase_id}",
                            "{share_path}",
                            "{prompt}",
                            "{prompt_transport_args}",
                        ],
                    },
                },
                "scenarios": [],
            }
        ),
        encoding="utf-8",
    )
    episode_payload = {
        "kind": "agentic-workspace/long-horizon-episode/v1",
        "id": "transport",
        "title": "Transport",
        "task_prompt": "Run evaluator with a large prompt.",
        "modes": [{"id": "mode", "aw_enabled": False, "fixture": "repo"}],
        "visible_validation_commands": [[sys.executable, "-c", "print('ok')"]],
        "phases": [{"id": "phase-one", "prompt": "Do work.", "adapter": "fake"}],
        "known_traps": ["large-prompt"],
        "expected_mistake_classes": ["weak_proof"],
        "rubric": {"intent_satisfied": "prompt is transported"},
        "evaluator": {"adapter": "fake-evaluator"},
    }
    episode = tmp_path / "episode-transport.json"
    episode.write_text(json.dumps(episode_payload), encoding="utf-8")

    payload = module.run_episode(
        episode_path=episode,
        suite_path=suite,
        output_root=tmp_path / "out",
        execute=False,
        evaluator=True,
    )

    evaluation = payload["modes"][0]["evaluation"]
    prompt_transport = evaluation["prompt_transport"]
    prompt_file = Path(prompt_transport["prompt_file"])
    assert prompt_transport["mode"] == "file-attachment"
    assert prompt_file.exists()
    assert "--attachment" in evaluation["command"]
    assert str(prompt_file) in evaluation["command"]


def test_long_horizon_episode_classifies_phase_contribution() -> None:
    module = _load_episode_module()

    assert module._phase_contribution({"created": ["src/pluggy/_manager.py"], "modified": [], "deleted": []})["kind"] == "changed-source"
    assert (
        module._phase_contribution({"created": ["testing/test_pluginmanager.py"], "modified": [], "deleted": []})["kind"] == "changed-tests"
    )
    assert (
        module._phase_contribution({"created": [], "modified": [], "deleted": [], "raw_status": "changed"})["kind"]
        == "ignored-or-setup-only"
    )
    assert module._phase_contribution({"created": [], "modified": [], "deleted": [], "raw_status": "clean"})["kind"] == "no-op"
