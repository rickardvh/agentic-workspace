from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.workspace_cli_support import _init_git_repo, cli


def _target(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
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


def test_dependency_digest_ignores_revision_only_changes_for_declared_dependencies(tmp_path: Path) -> None:
    from agentic_workspace import projection_reuse

    target = _target(tmp_path)
    first, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})
    (target / ".git" / "HEAD").write_text("ref: refs/heads/feature\n", encoding="utf-8")
    (target / "notes.txt").write_text("not summary relevant\n", encoding="utf-8")
    unchanged, _ = projection_reuse.dependency_digest(root=target, operation="summary", query={})

    assert unchanged == first


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

    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(projection_reuse.subprocess, "run", _timeout)

    digest, dependencies = projection_reuse.dependency_digest(root=target, operation="report", query={})

    assert digest
    assert ".agentic-workspace/config.toml" in dependencies


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
