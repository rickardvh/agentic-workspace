from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *
from repo_memory_bootstrap import _installer_paths as installer_paths
from repo_memory_bootstrap._installer_paths import _find_nested_repo_roots


def test_nested_repo_scan_excludes_only_manifest_owned_harness_evidence(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    owned = target / ".agentic-workspace" / "local" / "scratch" / "owned-run"
    unowned = target / ".agentic-workspace" / "local" / "scratch" / "unowned-run"
    (owned / "repo" / ".git").mkdir(parents=True)
    (unowned / "repo" / ".git").mkdir(parents=True)
    (owned / ".aw-scratch.toml").write_text(
        'owner = "agentic-workspace"\nproducer = "model-cli-harness"\n',
        encoding="utf-8",
    )

    found = _find_nested_repo_roots(target)

    assert owned / "repo" not in found
    assert unowned / "repo" in found


def test_nested_repo_scan_fails_closed_for_junction_like_owned_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "repo"
    owned = target / ".agentic-workspace/local/scratch/owned-run"
    (owned / "repo/.git").mkdir(parents=True)
    (owned / ".aw-scratch.toml").write_text('owner = "agentic-workspace"\nproducer = "model-cli-harness"\n', encoding="utf-8")
    original = getattr(installer_paths.os.path, "isjunction", lambda _path: False)
    monkeypatch.setattr(
        installer_paths.os.path,
        "isjunction",
        lambda path: Path(path) == owned or original(path),
        raising=False,
    )

    assert owned / "repo" in _find_nested_repo_roots(target)


def test_nested_repo_scan_does_not_trust_linked_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    owned = target / ".agentic-workspace/local/scratch/owned-run"
    (owned / "repo/.git").mkdir(parents=True)
    source = tmp_path / "manifest.toml"
    source.write_text('owner = "agentic-workspace"\nproducer = "model-cli-harness"\n', encoding="utf-8")
    try:
        (owned / ".aw-scratch.toml").symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    assert owned / "repo" in _find_nested_repo_roots(target)


def test_memory_doctor_does_not_flag_absent_optional_append_targets_in_clean_repo(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.doctor_bootstrap(target=target)

    assert not any(action.path == target / ".github" / "pull_request_template.md" for action in result.actions)
    assert not any(action.path == target / ".github" / "pull_request_template.md" and action.kind == "missing" for action in result.actions)


def test_memory_note_template_includes_improvement_signal_metadata() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "templates" / "memory-note.template.md").read_text(
        encoding="utf-8"
    )

    assert "## Improvement signal metadata" in text
    assert "## Structured manifest metadata" in text
    assert "`summary`: compact note summary" in text
    assert "`applies_to`: paths, subsystems, commands, or surfaces this note covers" in text
    assert "`use_when`: when an agent should load or apply this note" in text
    assert "`evidence`: source files, checks, commits, or docs that ground this note" in text
    assert "`preferred_remediation`" in text
    assert "`elimination_target`" in text
    assert "`config_treatment`" in text
    assert "`config_note`" in text
    assert "## Closeout-derived residue" in text
    assert "`source_closeout`" in text
    assert "`motivation`" in text
    assert "`why_it_matters`" in text
    assert "`use_when`" in text
    assert "`promotion_target`" in text
    assert "`promotion_trigger`" in text
    assert "`retention_after_promotion`" in text
    assert "Do not paste plan history, milestone logs, validation transcripts, backlog state, or archived-plan narration here." in text


def test_project_state_staleness_reason_mentions_planner_residue() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_PROJECT_STATE_MAX_LINES + 1))

    reason = installer._project_state_staleness_reason(text)

    assert reason is not None
    assert "planner residue" in reason


def test_manifest_loads_structured_note_routing_and_promotion_metadata(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/api-routing.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/api-routing.md"
authority = "canonical"
audience = "human+agent"
summary = "API routing lesson."
canonicality = "agent_only"
task_relevance = "optional"
applies_to = ["src/api/**"]
use_when = ["touching API routing"]
routes_from = ["src/api/**"]
stale_when = ["src/api/**"]
evidence = ["tests/test_api.py"]
memory_role = "improvement_signal"
preferred_remediation = "docs"
improvement_note = "Move stable API routing guidance into docs."
elimination_target = "promote"
promotion_target = "docs/api-routing.md"
promotion_trigger = "API routing guidance stabilises."
retention_after_promotion = "stub"
config_treatment = "promote"
config_note = "Current config favours canonical docs for stable API policy."
""".strip()
        + "\n",
        encoding="utf-8",
    )

    manifest = installer._load_memory_manifest(manifest_path)

    assert manifest is not None
    note = manifest.notes[0]
    assert note.summary == "API routing lesson."
    assert note.applies_to == ("src/api/**",)
    assert note.use_when == ("touching API routing",)
    assert note.evidence == ("tests/test_api.py",)
    assert note.promotion_target == "docs/api-routing.md"
    assert note.promotion_trigger == "API routing guidance stabilises."
    assert note.retention_after_promotion == "stub"

    recommendation = installer._build_remediation_recommendation(
        note,
        note_path=Path(".agentic-workspace/memory/repo/runbooks/api-routing.md"),
        text="# API routing\n\nDurable API routing lesson.\n",
        for_report=False,
    )
    assert recommendation is not None
    assert recommendation.target_path_hint == "docs/api-routing.md"

    state_model = installer._memory_state_model_view(
        manifest=manifest,
        trust_items=[{"path": note.path.as_posix(), "state": "supported"}],
    )
    manifest_record = next(record for record in state_model["records"] if record["note_type"] == "manifest")
    note_record = next(record for record in state_model["records"] if record["path"] == note.path.as_posix())
    assert "summary" in manifest_record["queryable_fields"]
    assert "promotion_target" in manifest_record["queryable_fields"]
    assert note_record["summary"] == "API routing lesson."
    assert note_record["applies_to"] == ["src/api/**"]
    assert note_record["use_when"] == ["touching API routing"]
    assert note_record["evidence"] == ["tests/test_api.py"]
    assert note_record["promotion_target"] == "docs/api-routing.md"
    assert note_record["promotion_trigger"] == "API routing guidance stabilises."
    assert note_record["retention_after_promotion"] == "stub"
