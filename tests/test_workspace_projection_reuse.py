from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from tests.workspace_cli_support import cli


def _target(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    return tmp_path


def test_doctor_reuses_unchanged_projection_before_full_builder_and_invalidates_on_dependency_change(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    first = json.loads(first_text)
    assert first.get("kind") != "agentic-workspace/unchanged-projection/v1"

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    second_text = capsys.readouterr().out
    second = json.loads(second_text)
    assert second["kind"] == "agentic-workspace/unchanged-projection/v1"
    assert second["work_avoided"]["full_projection_builder_skipped"] is True
    assert second["actionability_delta"] == "unchanged"
    assert second["proof_delta"] == "unchanged"
    assert second["residue_delta"] == "unchanged"
    assert second["next_action_delta"] == "unchanged"
    assert len(second_text) < len(first_text) / 2

    log = target / ".agentic-workspace" / "local" / "logs" / "session" / "command.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text("observational log output\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_log = json.loads(capsys.readouterr().out)
    assert after_log["kind"] == "agentic-workspace/unchanged-projection/v1"

    scratch = target / ".agentic-workspace" / "local" / "scratch" / "diagnostic.txt"
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.write_text("runtime-only scratch artifact\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_scratch = json.loads(capsys.readouterr().out)
    assert after_scratch["kind"] == "agentic-workspace/unchanged-projection/v1"

    external_evidence = target / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    external_evidence.parent.mkdir(parents=True, exist_ok=True)
    external_evidence.write_text('{"kind": "planning-external-intent-evidence/v1", "items": []}\n', encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_evidence = json.loads(capsys.readouterr().out)
    assert after_evidence.get("kind") != "agentic-workspace/unchanged-projection/v1"

    config = target / ".agentic-workspace" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n# dependency changed\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed.get("kind") != "agentic-workspace/unchanged-projection/v1"

    monkeypatch.setenv("AW_PROJECTION_FORCE_REFRESH", "1")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    forced = json.loads(capsys.readouterr().out)
    assert forced.get("kind") != "agentic-workspace/unchanged-projection/v1"


def test_report_reuses_equivalent_router_projection_and_verbose_forces_full_detail(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    unchanged_text = capsys.readouterr().out
    unchanged = json.loads(unchanged_text)

    assert unchanged["kind"] == "agentic-workspace/unchanged-projection/v1"
    assert unchanged["operation"] == "report"
    assert unchanged["work_avoided"]["serialization_of_full_projection_skipped"] is True
    assert len(unchanged_text) < len(first_text) / 2
    assert "--verbose" in unchanged["full_detail"]["command"]

    assert cli.main(["report", "--target", str(target), "--verbose", "--format", "json"]) == 0
    verbose = json.loads(capsys.readouterr().out)
    assert verbose["kind"] != "agentic-workspace/unchanged-projection/v1"


def test_start_implement_and_proof_reuse_the_same_revision_keyed_contract(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    changed = ".agentic-workspace/config.toml"
    capsys.readouterr()

    commands = [
        ["start", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
        ["implement", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
        ["proof", "--target", str(target), "--changed", changed, "--task", "Keep the route narrow.", "--format", "json"],
    ]
    decision_ids: list[str] = []
    for command in commands:
        assert cli.main(command) == 0
        cold = json.loads(capsys.readouterr().out)
        assert cold.get("kind") != "agentic-workspace/unchanged-projection/v1"

        assert cli.main(command) == 0
        warm = json.loads(capsys.readouterr().out)
        assert warm["kind"] == "agentic-workspace/unchanged-projection/v1"
        assert warm["reuse"] == {
            "decision": "reused",
            "enrichment": "reused",
            "invalidation_reasons": [],
            "authority": "operating_decision.compile_operating_decision",
        }
        assert warm["decision_id"] == cold["projection_reuse"]["operating_decision"]["decision_id"]
        assert warm["budgets"] == {"computation_budget_ms": 10000, "serialization_budget_bytes": 65536}
        decision_ids.append(warm["decision_id"])

    assert len(set(decision_ids)) == 1


def test_selected_closeout_and_planning_projections_are_bounded_and_warm_reused(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    capsys.readouterr()
    commands = [
        ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"],
        ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"],
    ]
    for command in commands:
        started = time.perf_counter()
        assert cli.main(command) == 0
        cold_text = capsys.readouterr().out
        cold_elapsed = time.perf_counter() - started
        assert len(cold_text.encode()) <= 65536

        started = time.perf_counter()
        assert cli.main(command) == 0
        warm_text = capsys.readouterr().out
        warm_elapsed = time.perf_counter() - started
        warm = json.loads(warm_text)
        assert warm["kind"] == "agentic-workspace/unchanged-projection/v1"
        assert len(warm_text.encode()) <= 65536
        assert cold_elapsed < 2.0
        assert warm_elapsed < 2.0
        assert warm["work_avoided"]["full_projection_builder_skipped"] is True


def test_invalidation_reasons_cover_each_admitted_authority_input_exactly() -> None:
    from agentic_workspace.projection_reuse import _invalidation_reasons

    previous = {
        "branch": "main",
        "head": "a",
        "task": "a",
        "selected_owner": "a",
        "planning": "a",
        "changed_paths": "a",
        "proof_subject": "a",
        "runtime_compatibility": "a",
        "external_freshness": "a",
        "worktree": "a",
    }
    expected = {
        "branch": "branch-changed",
        "head": "head-changed",
        "task": "task-changed",
        "selected_owner": "selected-owner-changed",
        "planning": "planning-revision-changed",
        "changed_paths": "changed-paths-changed",
        "proof_subject": "proof-subject-changed",
        "runtime_compatibility": "runtime-compatibility-changed",
        "external_freshness": "external-freshness-changed",
        "worktree": "admitted-worktree-changed",
    }
    for field, reason in expected.items():
        current = dict(previous)
        current[field] = "b"
        assert _invalidation_reasons(previous, current) == [reason]


def test_progress_heartbeat_and_cooperative_cancellation_are_bounded(tmp_path: Path, capsys) -> None:
    from agentic_workspace.projection_reuse import ProjectionBudget, ProjectionProgress

    target = _target(tmp_path)
    capsys.readouterr()
    cancel = target / ".agentic-workspace/local/cancellation/proof.cancel"
    cancel.parent.mkdir(parents=True, exist_ok=True)
    cancel.write_text("cancel\n", encoding="utf-8")
    budget = ProjectionBudget(long_command_threshold_seconds=0.0, progress_interval_seconds=0.01)
    with ProjectionProgress(root=target, operation="proof", budget=budget) as progress:
        time.sleep(0.03)
        contract = progress.contract()
    heartbeats = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert 1 <= len(heartbeats) <= 5
    assert heartbeats[0]["status"] == "cancel-requested"
    assert contract["status"] == "cancel-requested"
    assert contract["cancel"]["path"] == ".agentic-workspace/local/cancellation/proof.cancel"


def test_selected_summary_and_report_cancellation_return_bounded_envelopes(tmp_path: Path, capsys) -> None:
    target = _target(tmp_path)
    capsys.readouterr()
    commands = [
        ("summary", ["summary", "--target", str(target), "--select", "planning_revision", "--format", "json"]),
        ("report", ["report", "--target", str(target), "--format", "json"]),
        ("report", ["report", "--target", str(target), "--section", "closeout_trust", "--format", "json"]),
    ]
    for operation, command in commands:
        cancel = target / ".agentic-workspace" / "local" / "cancellation" / f"{operation}.cancel"
        cancel.parent.mkdir(parents=True, exist_ok=True)
        cancel.write_text("cancel\n", encoding="utf-8")
        assert cli.main(command) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == "agentic-workspace/projection-cancelled/v1"
        assert payload["status"] == "cancelled"
        cancel.unlink()


def test_serialization_budget_preserves_semantic_answer_shape_and_bounds_inventories() -> None:
    from agentic_workspace.projection_reuse import enforce_projection_serialization_budget

    payload = {
        "kind": "workspace-report-answer/v1",
        "answer": {
            "installed_state_residue": {"status": "separate_maintenance_residue"},
            "inventory": ["x" * 500 for _ in range(1000)],
        },
    }
    reuse_result = {
        "status": "rebuilt",
        "decision_id": "operating-decision:test",
        "observed_cost": {"serialized_bytes": 500000},
        "budgets": {"serialization_status": "exceeded", "serialization_budget_bytes": 65536},
    }

    bounded = enforce_projection_serialization_budget(
        payload=payload,
        operation="report",
        reuse_result=reuse_result,
        full_detail_command="agentic-workspace report --target . --verbose --format json",
    )

    assert bounded["kind"] == payload["kind"]
    assert bounded["answer"]["installed_state_residue"] == payload["answer"]["installed_state_residue"]
    assert bounded["serialization_budget"]["inventories_materialized_in_response"] is False
    assert len(json.dumps(bounded, indent=2).encode()) <= 65536


def test_summary_reuses_unchanged_projection_and_preserves_decision_deltas(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    capsys.readouterr()

    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    first_text = capsys.readouterr().out
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    unchanged_text = capsys.readouterr().out
    unchanged = json.loads(unchanged_text)

    assert unchanged["kind"] == "agentic-workspace/unchanged-projection/v1"
    assert unchanged["operation"] == "summary"
    assert unchanged["decision_delta"] == "unchanged"
    assert unchanged["proof_delta"] == "unchanged"
    assert unchanged["residue_delta"] == "unchanged"
    assert unchanged["next_action_delta"] == "unchanged"
    assert unchanged["prior_decision"]["health"]
    assert unchanged["prior_decision"]["next_action"]
    assert unchanged["work_avoided"]["full_projection_builder_skipped"] is True
    assert unchanged["work_avoided"]["serialization_of_full_projection_skipped"] is True
    assert len(unchanged_text) < len(first_text) / 2
    assert "--verbose" in unchanged["full_detail"]["command"]

    planning_state = target / ".agentic-workspace" / "planning" / "state.toml"
    planning_state.write_text(planning_state.read_text(encoding="utf-8") + "\n# decision relevant planning change\n", encoding="utf-8")
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed.get("kind") != "agentic-workspace/unchanged-projection/v1"

    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    monkeypatch.setenv("AW_PROJECTION_FORCE_REFRESH", "1")
    assert cli.main(["summary", "--target", str(target), "--format", "json"]) == 0
    forced = json.loads(capsys.readouterr().out)
    assert forced.get("kind") != "agentic-workspace/unchanged-projection/v1"


def test_dependency_digest_tracks_commit_relevant_worktree_and_contract_but_ignores_irrelevant_file(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    (target / "notes.txt").write_text("irrelevant\n", encoding="utf-8")
    irrelevant, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert irrelevant == first
    (target / "src/agentic_workspace/new_runtime.py").parent.mkdir(parents=True, exist_ok=True)
    (target / "src/agentic_workspace/new_runtime.py").write_text("VALUE = 1\n", encoding="utf-8")
    relevant, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert relevant != first
    monkeypatch.setattr(projection_reuse, "_CACHE_CONTRACT_VERSION", 99)
    contract, _ = projection_reuse.dependency_digest(root=target, operation="doctor", query={})
    assert contract != relevant


def test_dependency_digest_invalidates_when_branch_revision_changes(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})
    (target / ".git" / "HEAD").write_text("ref: refs/heads/feature\n", encoding="utf-8")
    (target / "notes.txt").write_text("not summary relevant\n", encoding="utf-8")
    changed, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})

    assert changed != first


def test_dependency_digest_excludes_crash_recovery_worktrees_and_virtualenvs(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, first_dependencies = projection_reuse.dependency_digest(root=target, operation="report", query={})
    runtime_file = (
        target
        / ".agentic-workspace"
        / "local"
        / "chatgpt-review-worktrees"
        / "pr-9999"
        / ".venv"
        / "Lib"
        / "site-packages"
        / "dependency.py"
    )
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("VALUE = 1\n", encoding="utf-8")

    unchanged, dependencies = projection_reuse.dependency_digest(root=target, operation="report", query={})

    assert unchanged == first
    assert dependencies == first_dependencies
    assert not any("chatgpt-review-worktrees" in path or "/.venv/" in path for path in dependencies)


def test_dependency_digest_fails_open_when_git_probe_times_out(tmp_path: Path, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)

    def _timeout(*_args, **_kwargs):
        return projection_reuse.GitProbeResult("unavailable", reason="Git revision probe timed out")

    monkeypatch.setattr(projection_reuse, "_git", _timeout)

    result = projection_reuse.dependency_digest(root=target, operation="report", query={})
    digest, dependencies = result

    assert digest
    assert ".agentic-workspace/config.toml" in dependencies
    assert result.status == "unavailable"
    assert result.findings[0]["section"] == "projection_branch_revision"


def test_admitted_revision_computation_fails_open_above_content_read_budget(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    changed = [f"src/agentic_workspace/generated_{index}.py" for index in range(100)]
    cached, context = projection_reuse.lookup_projection_reuse(
        root=target,
        operation="report",
        query={"changed": changed},
        full_detail_command="agentic-workspace report --target . --verbose --format json",
    )

    assert cached is None
    assert len(context["dependencies"]) <= 64 + 32
    assert context["dependency_status"] == "unavailable"
    assert context["degraded_findings"][-1]["section"] == "projection_changed_path_revision"
    result = projection_reuse.record_projection_reuse(
        root=target, operation="report", query={"changed": changed}, context=context, payload={"status": "ok"}
    )
    assert result == {}


def test_report_git_timeout_disables_reuse_and_names_failed_probe(tmp_path: Path, capsys, monkeypatch) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    capsys.readouterr()
    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()

    def _timeout(*_args, **_kwargs):
        return projection_reuse.GitProbeResult("unavailable", reason="Git revision probe timed out")

    monkeypatch.setattr(projection_reuse, "_git", _timeout)

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload.get("kind") != "agentic-workspace/unchanged-projection/v1"
    finding = payload["projection_reuse"]["findings"][0]
    assert finding["section"] == "projection_branch_revision"
    assert finding["status"] == "unavailable"


def test_volatile_projection_fails_open_and_cache_is_bounded(tmp_path: Path) -> None:
    from agentic_workspace.projection_reuse import lookup_projection_reuse, record_projection_reuse

    target = _target(tmp_path)
    cached, context = lookup_projection_reuse(
        root=target, operation="report", query={"external_freshness_required": True}, full_detail_command="report"
    )
    assert cached is None and context["volatile"] is True
    for index in range(40):
        cached, context = lookup_projection_reuse(root=target, operation="doctor", query={"index": index}, full_detail_command="doctor")
        record_projection_reuse(root=target, operation="doctor", query={"index": index}, context=context, payload={"status": "ok"})
    assert len(list((target / ".agentic-workspace/local/projection-cache").glob("*.json"))) <= 32


def test_projection_cache_does_not_bootstrap_workspace_state(tmp_path: Path) -> None:
    from agentic_workspace.projection_reuse import lookup_projection_reuse, record_projection_reuse

    cached, context = lookup_projection_reuse(root=tmp_path, operation="report", query={}, full_detail_command="report")
    assert cached is None
    record_projection_reuse(root=tmp_path, operation="report", query={}, context=context, payload={"status": "ok"})

    assert not (tmp_path / ".agentic-workspace").exists()


def test_doctor_declares_package_inputs_and_caller_external_freshness_recomputes(tmp_path: Path, capsys, monkeypatch) -> None:
    target = _target(tmp_path)
    capsys.readouterr()
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    capsys.readouterr()
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "agentic-workspace/unchanged-projection/v1"

    package_file = target / "packages/example/src/example.py"
    package_file.parent.mkdir(parents=True)
    package_file.write_text("VALUE = 1\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out).get("kind") != "agentic-workspace/unchanged-projection/v1"

    monkeypatch.setenv("AW_PROJECTION_EXTERNAL_STATE", "1")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out).get("kind") != "agentic-workspace/unchanged-projection/v1"
