from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_route_memory_adds_routing_baseline_and_runtime_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    required = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "required"}
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/index.md" in required
    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested
    assert ".agentic-workspace/memory/repo/current/project-state.md" not in suggested
    assert ".agentic-workspace/memory/repo/current/task-context.md" not in suggested
    assert result.route_summary["routed_note_count"] == 3
    assert result.route_summary["required_count"] == 1
    assert result.route_summary["optional_count"] == 2
    assert result.route_summary["exceeded_target"] == "no"
    assert result.missing_note_hint == "If routing missed something, record which note was missing."


def test_route_memory_adds_architecture_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["src/architecture/schema.py"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/invariants/README.md" in suggested
    assert ".agentic-workspace/memory/repo/decisions/README.md" in suggested
    assert ".agentic-workspace/memory/repo/current/project-state.md" not in suggested
    assert ".agentic-workspace/memory/repo/current/task-context.md" not in suggested
    assert result.route_summary["exceeded_target"] == "yes"
    assert "justification" in result.route_summary


def test_route_memory_reports_low_confidence_for_index_only_fallbacks(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])

    assert result.route_summary["confidence"] == "low"
    assert result.route_summary["fallback_match_count"] >= 1
    assert "routing relied on fallback signals" in " ".join(result.route_summary["confidence_reasons"])


def test_route_memory_reports_high_confidence_for_direct_manifest_matches(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routes_from = ["src/api.py"]
surfaces = ["api"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/api.py"])

    assert result.route_summary["confidence"] == "high"
    assert result.route_summary["direct_match_count"] == 1
    assert result.route_summary["weak_signal_note_count"] == 0


def test_route_memory_uses_stage_as_structured_signal_not_task_prose(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    note = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "startup.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    note.write_text("# Startup\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/startup.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/startup.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["startup"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    first = installer.route_memory(target=target, stage="startup", task="memory memory startup memory")
    second = installer.route_memory(target=target, task="startup memory memory")
    first_optional = {action.source for action in first.actions if action.kind == "optional"}
    second_optional = {action.source for action in second.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/domains/startup.md" in first_optional
    assert ".agentic-workspace/memory/repo/domains/startup.md" not in second_optional
    assert first.route_summary["route_context"]["stage"] == "startup"
    assert first.route_summary["route_context"]["task_supplied"] is True
    assert first.route_summary["route_context"]["task_used_for_matching"] is False
    assert second.route_summary["insufficient_route_signal"] is True
    assert second.route_summary["task_prose_role"] == "context-only"
    assert [item["id"] for item in second.route_summary["recovery_options"]] == ["add-files", "add-surface", "add-stage"]
    assert [item["owner"] for item in second.route_summary["owner_alternatives"]][:2] == ["dismiss", "local_memory"]


def test_route_memory_preserves_explicit_surfaces_separately_from_stage(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="local-tooling",
        summary="Local tooling invocation reminders.",
        applies_to=["scripts/run_agentic_workspace.py"],
        routes_from=["codex"],
    )
    manifest_path = target / ".agentic-workspace/memory/repo/manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(
        manifest_text.replace('routes_from = ["codex"]', 'routes_from = ["codex"]\nsurfaces = ["codex"]'), encoding="utf-8"
    )

    result = installer.route_memory(
        target=target,
        surfaces=["python", "shell", "codex"],
        stage="implement",
        task="Run a Python helper script from PowerShell.",
    )
    context = result.route_summary["route_context"]

    assert context["explicit_surfaces"] == ["codex", "python", "shell"]
    assert context["stage_surface"] == "implement"
    assert set(context["surfaces"]) >= {"codex", "python", "shell", "implement"}
    assert any(action.match_source == "surface" and "codex" in action.detail for action in result.actions)


def test_route_memory_keeps_pending_command_context_separate_from_explicit_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    note = target / ".agentic-workspace" / "local" / "memory" / "local-python-invocation.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    note.write_text("# Local Python Invocation\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/local/memory/local-python-invocation.md"]
note_type = "mistake"
canonical_home = ".agentic-workspace/local/memory/local-python-invocation.md"
authority = "local"
audience = "agent"
canonicality = "local_only"
task_relevance = "optional"
routes_from = ["python", "shell", "local-tooling"]
surfaces = ["python", "shell", "local-tooling"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    routed = installer.route_memory(
        target=target,
        pending_command="python - <<'PY'",
        surfaces=["python", "shell"],
        task="memory memory memory",
    )
    command_only = installer.route_memory(target=target, pending_command="python - <<'PY'")
    task_only = installer.route_memory(target=target, task="python shell local tooling")

    routed_sources = {action.source for action in routed.actions}
    command_only_sources = {action.source for action in command_only.actions}
    task_only_sources = {action.source for action in task_only.actions}
    context = routed.route_summary["route_context"]

    assert ".agentic-workspace/local/memory/local-python-invocation.md" in routed_sources
    assert ".agentic-workspace/local/memory/local-python-invocation.md" not in command_only_sources
    assert ".agentic-workspace/local/memory/local-python-invocation.md" not in task_only_sources
    assert context["explicit_surfaces"] == ["python", "shell"]
    assert "command_surfaces" not in context
    assert context["pending_command_supplied"] is True
    assert context["task_used_for_matching"] is False


def test_capture_note_exposes_non_memory_owner_routes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    payload = installer.suggest_memory_note_capture(
        target=target,
        summary="Repeated workflow correction should be preserved if reusable.",
        stage="closeout",
        task="Finish implementation and route durable learning.",
    )

    assert payload["kind"] == "agentic-memory/capture-recommendation/v1"
    assert payload["status"] == "ready"
    assert "planning" in payload["non_memory_owner_routes"]
    assert "docs" in payload["non_memory_owner_routes"]
    assert payload["route_context"]["stage"] == "closeout"
    assert payload["confidence"] == "low"
    assert payload["storage_decision"]["recommended_owner"] == "local_memory"
    assert [item["owner"] for item in payload["owner_alternatives"]][:3] == ["dismiss", "local_memory", "planning"]


def test_route_memory_does_not_invent_test_remediation_for_plain_mistake_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="local-python-invocation",
        folder="mistakes",
        note_type="mistake",
        summary="Bare python is unavailable in this local shell.",
        applies_to=["scripts/run_agentic_workspace.py"],
        routes_from=["python", "shell"],
        memory_role="durable_truth",
    )

    result = installer.route_memory(target=target, surfaces=["python", "shell"])
    pressure_actions = [action for action in result.actions if action.role == "improvement-pressure"]

    assert pressure_actions == []


def test_route_memory_exposes_selected_note_freshness_trust(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    notes_dir = target / ".agentic-workspace" / "memory" / "repo" / "domains"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (notes_dir / "fresh.md").write_text("# Fresh\n", encoding="utf-8")
    (notes_dir / "expired.md").write_text("# Expired\n", encoding="utf-8")
    (notes_dir / "superseded.md").write_text("# Superseded\n", encoding="utf-8")
    (notes_dir / "replacement.md").write_text("# Replacement\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/fresh.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/fresh.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["src/api.py"]
stale_when = ["src/api.py"]
last_confirmed = "2999-01-01"
valid_until = "2999-12-31"
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/domains/expired.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/expired.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["src/api.py"]
stale_when = ["src/api.py"]
last_confirmed = "1999-01-01"
valid_until = "2000-01-01"
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/domains/superseded.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/superseded.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["src/api.py"]
stale_when = ["src/api.py"]
last_confirmed = "2026-01-01"
superseded_by = [".agentic-workspace/memory/repo/domains/replacement.md"]
memory_role = "durable_truth"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "src").mkdir(parents=True, exist_ok=True)
    (target / "src" / "api.py").write_text("pass\n", encoding="utf-8")

    result = installer.route_memory(target=target, files=["src/api.py"])

    selected_trust = result.route_summary["selected_note_trust"]
    assert selected_trust["status"] == "attention"
    assert selected_trust["attention_count"] == 2
    trust_by_path = {item["path"]: item for item in selected_trust["items"]}
    assert trust_by_path[".agentic-workspace/memory/repo/domains/fresh.md"]["freshness"] == "fresh"
    assert trust_by_path[".agentic-workspace/memory/repo/domains/expired.md"]["freshness"] == "expired"
    assert trust_by_path[".agentic-workspace/memory/repo/domains/superseded.md"]["state"] == "superseded"


def test_route_memory_falls_back_to_index_when_manifest_is_incomplete(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested


def test_route_memory_does_not_treat_routing_baseline_as_surface_coverage(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        _memory_manifest_text(),
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["docker/compose.yml"])
    required = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "required"}
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}
    manual_reviews = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "manual review"}

    assert ".agentic-workspace/memory/repo/index.md" in required
    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested
    assert ".agentic-workspace/memory/repo/index.md" not in manual_reviews


def test_route_memory_only_suggests_task_context_on_explicit_input(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=[".agentic-workspace/memory/repo/current/task-context.md"])

    assert any(
        action.kind == "optional"
        and action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/current/task-context.md"
        and "explicit current-context input" in action.detail
        for action in result.actions
    )


def test_route_memory_uses_manifest_file_globs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/repo_memory_bootstrap/cli.py"])

    assert any(
        action.kind == "optional"
        and action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/domains/cli.md"
        and "manifest path match" in action.detail
        and action.match_source == "file-path"
        for action in result.actions
    )


def test_route_memory_emits_improvement_pressure_for_matched_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(
        ("# Deploy\n\n" + "boundary detail\n") * 80, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["deploy/**/*.yaml"]
stale_when = ["deploy/**/*.yaml"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["deploy/prod/service.yaml"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.kind == "consider"
        and "clearer canonical docs or refactor review" in action.detail
        for action in result.actions
    )


def test_route_memory_emits_strong_warning_for_six_plus_direct_matches(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/a.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/a.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/b.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/b.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/c.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/c.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/d.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/d.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/e.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/e.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/f.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/f.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/service.py"])

    assert result.route_summary["routed_note_count"] == 7
    assert result.route_summary["exceeded_target"] == "yes"
    warning = str(result.route_summary["warning"])
    assert "more than five notes" in warning


def test_sync_memory_without_input_returns_guidance(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.sync_memory(target=target)

    assert len(result.actions) == 1
    assert result.actions[0].kind == "manual review"
    assert "provide --files/--notes" in result.actions[0].detail


def test_sync_memory_with_explicit_file_produces_recommendations(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.sync_memory(target=target, files=["tests/test_cli.py"])

    assert any(action.kind in {"review", "update", "update index"} for action in result.actions)


def test_sync_memory_emits_compact_primary_note_summary(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**"]
stale_when = ["src/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/service/api.py"])

    assert result.sync_summary["status"] == "actionable"
    assert result.sync_summary["primary_note"]["path"] == ".agentic-workspace/memory/repo/domains/cli.md"
    assert "Start with .agentic-workspace/memory/repo/domains/cli.md" in result.sync_summary["summary"]


def test_sync_memory_uses_manifest_staleness_triggers(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
related_validations = ["uv run pytest"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/repo_memory_bootstrap/installer.py"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md"
        and action.kind == "review"
        and "manifest staleness trigger matched" in action.detail
        for action in result.actions
    )


def test_sync_memory_emits_improvement_pressure_for_stale_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(
        ("# Deploy\n\n" + "boundary detail\n") * 80, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/repo_memory_bootstrap/installer.py"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.kind == "consider"
        and "clearer canonical docs or refactor review" in action.detail
        for action in result.actions
    )


def test_sync_memory_appends_improvement_hint_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- Guard this.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
stale_when = ["tests/**/*.py"]
memory_role = "improvement_signal"
preferred_remediation = "test"
improvement_candidate = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["tests/test_api.py"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md"
        and action.kind in {"review", "update"}
        and "consider a regression test" in action.detail
        and action.remediation_kind == "test"
        for action in result.actions
    )


def test_path_match_pattern_treats_double_star_as_zero_or_more_directories() -> None:
    assert installer._path_matches_pattern("tests/test_api.py", "tests/**/*.py")
    assert installer._path_matches_pattern("tests/unit/test_api.py", "tests/**/*.py")


def test_route_memory_json_includes_summary_and_missing_note_hint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    data = json.loads(installer.format_result_json(result))

    assert data["route_summary"]["routed_note_count"] == 3
    assert data["route_summary"]["required_count"] == 1
    assert data["route_summary"]["optional_count"] == 2
    assert data["missing_note_hint"] == "If routing missed something, record which note was missing."


@pytest.mark.parametrize(
    "fixture_name",
    [
        "runtime-basic.json",
        "architecture-basic.json",
        "canonical-doc-precedence.json",
        "optional-pressure.json",
        "missed-note-regression.json",
        "over-routing-regression.json",
    ],
)
def test_route_memory_matches_calibration_fixture_expectations(tmp_path: Path, fixture_name: str) -> None:
    target = tmp_path / fixture_name.removesuffix(".json")
    fixture = _setup_routing_fixture_repo(target, fixture_name)

    fixture_files = [str(item) for item in fixture["files"]] if isinstance(fixture.get("files"), list) else []
    fixture_surfaces = [str(item) for item in fixture["surfaces"]] if isinstance(fixture.get("surfaces"), list) else []
    expected_required = (
        set(str(item) for item in fixture["expected_required"]) if isinstance(fixture.get("expected_required"), list) else set()
    )
    expected_optional = (
        set(str(item) for item in fixture["expected_optional"]) if isinstance(fixture.get("expected_optional"), list) else set()
    )
    unexpected_notes = (
        set(str(item) for item in fixture["unexpected_notes"]) if isinstance(fixture.get("unexpected_notes"), list) else set()
    )
    missing_note_candidates = (
        set(str(item) for item in fixture["missing_note_candidates"]) if isinstance(fixture.get("missing_note_candidates"), list) else set()
    )

    result = installer.route_memory(
        target=target,
        files=fixture_files,
        surfaces=fixture_surfaces,
    )
    required, optional = _routed_note_sets(result, target)

    assert required == expected_required
    assert optional == expected_optional
    assert unexpected_notes.isdisjoint(required | optional)
    if missing_note_candidates:
        assert missing_note_candidates.issubset(required | optional)


def test_route_memory_matches_dot_managed_paths_as_direct_manifest_routes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/dot-managed-route.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/dot-managed-route.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'surfaces = ["architecture"]\n'
        'routes_from = [".agentic-workspace/docs/reporting-contract.md"]\n'
        'stale_when = [".agentic-workspace/docs/reporting-contract.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "dot-managed-route.md").write_text(
        "# Dot Managed Route\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=[".agentic-workspace/docs/reporting-contract.md"])
    required, optional = _routed_note_sets(result, target)

    assert required == {".agentic-workspace/memory/repo/index.md"}
    assert ".agentic-workspace/memory/repo/domains/dot-managed-route.md" in optional
    assert ".agentic-workspace/memory/repo/invariants/example-response-contract.md" not in optional


def test_route_memory_prefers_canonical_doc_when_manifest_marks_note_canonical_elsewhere(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API memory\n", encoding="utf-8")
    (target / "docs" / "api.md").write_text("# API docs\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = "docs/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "canonical_elsewhere"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/service/api.py"])

    assert any(
        action.path == target / "docs" / "api.md" and action.kind == "required" and "canonical doc takes precedence" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and action.kind == "optional"
        and "fallback context only" in action.detail
        for action in result.actions
    )


def test_route_review_handles_missing_feedback_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.review_routes(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md"
        and action.kind == "current"
        and "absent by default" in action.detail
        for action in result.actions
    )


def test_route_review_reports_missed_note_case_that_now_passes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary == {
        "reviewed_case_count": 1,
        "still_missed_count": 0,
        "still_over_routed_count": 0,
        "unresolved_case_count": 0,
    }
    assert result.review_cases[0]["matched"] is True


def test_route_review_reports_missed_note_case_that_still_fails(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: wrong-expected-note\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/runbooks/runtime.md\n"
                "Why it was needed\n"
                "- Pretend this note should have been routed.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["still_missed_count"] == 1
    assert result.review_cases[0]["matched"] is False


def test_route_review_reports_over_routing_case_that_still_fails(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_repo_file(target, ".agentic-workspace/memory/repo/index.md", _memory_index_text())
    _write_repo_file(target, ".agentic-workspace/memory/repo/domains/too-broad.md", "# Too broad\n")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/manifest.toml",
        (
            "version = 1\n\n"
            '[notes.".agentic-workspace/memory/repo/domains/too-broad.md"]\n'
            'note_type = "domain"\n'
            'canonical_home = ".agentic-workspace/memory/repo/domains/too-broad.md"\n'
            'authority = "canonical"\n'
            'audience = "human+agent"\n'
            'canonicality = "agent_only"\n'
            'task_relevance = "optional"\n'
            'routes_from = ["src/**/*.py"]\n'
            'stale_when = ["src/**/*.py"]\n'
        ),
    )
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            over_cases=[
                "### Case: too-broad-domain\n"
                "Task surface summary\n"
                "- Generic src python change.\n"
                "Files\n"
                "- src/service.py\n"
                "Surfaces\n"
                "- api\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "- .agentic-workspace/memory/repo/domains/too-broad.md\n"
                "Unexpected notes\n"
                "- .agentic-workspace/memory/repo/domains/too-broad.md\n"
                "Why they were unnecessary\n"
                "- The note is too broad for this route.\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["still_over_routed_count"] == 1
    assert result.review_cases[0]["matched"] is False


def test_route_review_marks_incomplete_case_unresolved(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=["### Case: incomplete\nTask surface summary\n- Missing explicit files and expected note.\nStatus\n- open"]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["unresolved_case_count"] == 1
    assert result.review_cases[0]["unresolved"] is True


def test_route_review_json_includes_summary_and_cases(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    data = json.loads(installer.format_result_json(installer.review_routes(target=target)))

    assert data["review_summary"]["reviewed_case_count"] == 1
    assert data["review_cases"][0]["case_type"] == "missed_note"


def test_route_report_handles_missing_feedback_and_fixture_inputs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["fixtures"]["fixture_count"] == 0
    assert "No parseable routing-feedback cases yet" in result.route_report_summary["feedback_guidance"]
    assert "No routing fixtures found" in result.route_report_summary["fixture_guidance"]


def test_route_report_supports_feedback_cases_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 1
    assert result.route_report_summary["fixtures"]["fixture_count"] == 0
    assert result.route_report_feedback_cases[0]["matched"] is True


def test_route_report_supports_fixtures_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "architecture-basic.json")

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["fixtures"]["fixture_count"] == 2
    assert result.route_report_summary["fixtures"]["passing_fixture_count"] == 2


def test_route_report_supports_feedback_cases_and_fixtures(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_routing_fixture_file(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- tuned"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["tuned_case_count"] == 1
    assert result.route_report_summary["fixtures"]["fixture_count"] == 1
    assert result.route_report_summary["working_set"]["average_routed_note_count"] == 3.0


def test_route_report_json_includes_summary_feedback_cases_and_fixture_results(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")

    data = json.loads(installer.format_result_json(installer.report_routes(target=target)))

    assert "route_report_summary" in data
    assert "route_report_feedback_cases" in data
    assert "route_report_fixture_results" in data
    assert "missed_note" in data["route_report_summary"]
    assert "over_routing" in data["route_report_summary"]
    assert "routing_confidence" in data["route_report_summary"]
    assert "startup_cost" in data["route_report_summary"]


def test_route_report_keeps_missed_and_over_routing_counts_separate(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: missed\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/runbooks/runtime.md\n"
                "Why it was needed\n"
                "- Missing note case.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ],
            over_cases=[
                "### Case: over\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Unexpected notes\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why they were unnecessary\n"
                "- Over-routing case.\n"
                "Status\n"
                "- open"
            ],
        ),
    )

    result = installer.report_routes(target=target)
    feedback = result.route_report_summary["feedback"]

    assert feedback["missed_note_case_count"] == 1
    assert feedback["over_routing_case_count"] == 1
    assert feedback["still_missed_count"] == 1
    assert feedback["still_over_routed_count"] == 1


def test_route_report_handles_invalid_fixture_without_crashing(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_routing_fixture_file(target, "invalid.json", raw_text="{ not json }\n")

    result = installer.report_routes(target=target)

    assert result.route_report_summary["fixtures"]["invalid_fixture_count"] == 1
    assert result.route_report_fixture_results[0]["valid"] is False
    assert "invalid JSON" in result.route_report_fixture_results[0]["error"]


def test_route_report_fixture_counts_and_working_set_metrics_are_correct(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "architecture-basic.json")
    failing = _load_routing_fixture("runtime-basic.json")
    failing["name"] = "failing"
    failing["expected_optional"] = [".agentic-workspace/memory/repo/domains/wrong.md"]
    _write_routing_fixture_file(target, "failing.json", payload=failing)

    result = installer.report_routes(target=target)
    summary = result.route_report_summary["fixtures"]

    assert summary["fixture_count"] == 3
    assert summary["passing_fixture_count"] == 2
    assert summary["failing_fixture_count"] == 1
    assert summary["invalid_fixture_count"] == 0
    assert summary["average_routed_note_count"] == 3.0
    assert summary["average_required_note_count"] == 1.0
    assert summary["average_optional_note_count"] == 2.0
    assert summary["max_routed_note_count"] == 3
    assert summary["fixture_count_exceeding_target"] == 0
    assert summary["fixture_count_exceeding_strong_warning"] == 0
    assert summary["average_routed_line_count"] > 0
    assert summary["max_routed_line_count"] > 0
    confidence = result.route_report_summary["routing_confidence"]
    assert confidence["high_confidence_fixture_count"] >= 0
    assert confidence["medium_confidence_fixture_count"] >= 0
    assert confidence["low_confidence_fixture_count"] >= 0


def test_route_report_generated_outputs_preserve_failure_detail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    failing = _load_routing_fixture("runtime-basic.json")
    failing["name"] = "failing"
    failing["expected_optional"] = [".agentic-workspace/memory/repo/domains/wrong.md"]
    _write_routing_fixture_file(target, "failing.json", payload=failing)
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=["### Case: unresolved\nTask surface summary\n- Missing explicit routing data.\nStatus\n- open"]
        ),
    )

    assert cli.main(["route-report", "--target", str(target), "--verbose", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    serialized = json.dumps(payload)

    assert "fixture 'failing' fails" in serialized
    assert "case 'unresolved' is unresolved" in serialized
    assert "fixture 'runtime-basic' fails" not in serialized

    assert cli.main(["route-report", "--target", str(target), "--verbose"]) == 0
    output = capsys.readouterr().out

    assert "Routing report" in output
    assert "Feedback:" in output
    assert "Fixtures:" in output


def test_route_report_excludes_externalized_feedback_cases_from_live_counts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: externalized\n"
                "Task surface summary\n"
                "- Skill recommendation moved elsewhere.\n"
                "Files\n"
                "- AGENTS.md\n"
                "Surfaces\n"
                "- review\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- tools/skills/review/SKILL.md\n"
                "Why it was needed\n"
                "- Not a Memory routing issue anymore.\n"
                "Expected routing signal\n"
                "- handled by another product surface\n"
                "Status\n"
                "- externalized on 2026-04-17 via another checked-in skill-discovery surface"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["feedback"]["externalized_case_count"] == 1
    assert result.route_report_feedback_cases[0]["externalized"] is True
    assert not any(action.kind == "manual review" and "externalized" in action.detail for action in result.actions)


def test_route_report_does_not_emit_combined_routing_score(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")

    data = json.loads(installer.format_result_json(installer.report_routes(target=target)))

    assert "routing_score" not in data
    assert "routing_score" not in data["route_report_summary"]
