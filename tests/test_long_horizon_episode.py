from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

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
    assert json.loads((schema_dir / "long-horizon-episode.schema.json").read_text(encoding="utf-8"))["$id"] == module.EPISODE_KIND
    assert json.loads((schema_dir / "long-horizon-evaluation.schema.json").read_text(encoding="utf-8"))["$id"] == module.EVALUATION_KIND

    episode_dir = REPO_ROOT / "tools" / "model-cli-harness" / "episodes"
    for path in [
        episode_dir / "intent-proof-packaging-specifier.json",
        episode_dir / "reuse-abstraction-pluggy.json",
        episode_dir / "intent-proof-click-pager.json",
    ]:
        episode = module.load_episode(path)
        assert episode["modes"]
        assert episode["visible_validation_commands"]


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
    assert "do-not-leak-reference" not in evaluator_prompt
    assert payload["comparison"]["mistake_classes"] == ["weak_proof"]
    assert payload["comparison"]["human_review_required"] is True
    assert payload["comparison"]["recommended_followups"][0]["type"] == "issue"


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
