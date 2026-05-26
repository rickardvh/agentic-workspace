from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _start_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context", {})
    return context if isinstance(context, dict) else {}


def _start_durable_intent(payload: dict[str, object]) -> dict[str, object]:
    durable_intent = payload.get("durable_intent")
    if isinstance(durable_intent, dict):
        return durable_intent
    context_intent = _start_context(payload).get("durable_intent")
    return context_intent if isinstance(context_intent, dict) else {}


def test_system_intent_command_sync_refreshes_source_metadata_without_mechanical_extraction(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version = 1\n\n[system_intent]\nsources = ["README.md"]\npreferred_source = "README.md"\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Product Direction\n\nKeep the system quiet.\n", encoding="utf-8")

    assert cli.main(["system-intent", "--target", str(tmp_path), "--sync", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-system-intent/v1"
    assert payload["mirror"]["status"] == "present"
    assert (tmp_path / ".agentic-workspace/system-intent/intent.toml").exists()
    mirror_text = (tmp_path / ".agentic-workspace/system-intent/intent.toml").read_text(encoding="utf-8")
    assert 'preferred_source = "README.md"' in mirror_text
    assert 'summary = ""' in mirror_text
    assert "needs_review = true" in mirror_text
    assert "[[source_records]]" in mirror_text
    assert 'path = "README.md"' in mirror_text
    subsystem_text = (tmp_path / ".agentic-workspace/system-intent/subsystems.toml").read_text(encoding="utf-8")
    assert 'kind = "agentic-workspace/subsystem-intent-set/v1"' in subsystem_text
    assert 'id = "planning"' not in subsystem_text
    assert 'id = "memory"' not in subsystem_text
    assert "subsystems = []" in subsystem_text
    assert payload["subsystem_intent"]["subsystem_count"] == 0
    assert payload["decision_projection"]["task_intent"]["role"] == "bounded and closable"


def test_system_intent_rejects_invalid_subsystem_intent_lifecycle(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace/system-intent").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic-workspace/config.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace/system-intent/subsystems.toml").write_text(
        'schema_version = 1\nkind = "agentic-workspace/subsystem-intent-set/v1"\n\n'
        '[[subsystems]]\nid = "ux"\nscope = "frontend"\nstatus = "done"\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["system-intent", "--target", str(tmp_path), "--format", "json"])
    assert exc_info.value.code == 2
    assert "status must be one of" in capsys.readouterr().err


def test_system_intent_rejects_subsystem_intent_ids_missing_from_ownership(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        """
schema_version = 1

[[subsystems]]
id = "planning"
paths = [".agentic-workspace/planning/**"]
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "subsystems.toml",
        """
schema_version = 1
kind = "agentic-workspace/subsystem-intent-set/v1"

[[subsystems]]
id = "invented"
scope = "not in ownership"
status = "active"
summary = "This should not create a second subsystem taxonomy."
decision_tests = ["Is this valid?"]
confidence = "low"
needs_review = true
source_records = [{ source_type = "test", ref = "test", summary = "unknown id" }]
""",
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["system-intent", "--target", str(tmp_path), "--format", "json"])
    assert exc_info.value.code == 2
    error = capsys.readouterr().err
    assert "is not declared in .agentic-workspace/OWNERSHIP.toml [[subsystems]]" in error
    assert "planning" in error


def test_start_does_not_match_durable_intent_from_task_text(capsys) -> None:
    assert cli.main(["start", "--target", ".", "--task", "planning closeout should preserve durable intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "durable_intent" not in payload.get("context", {})


def test_start_matches_subsystem_intent_through_ownership_paths(capsys) -> None:
    assert (
        cli.main(["start", "--target", ".", "--changed", "packages/planning/src/repo_planning_bootstrap/installer.py", "--format", "json"])
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    matches = _start_durable_intent(payload)["subsystem_intent"]["matches"]
    planning_match = next(match for match in matches if match["id"] == "planning")
    assert planning_match["match_source"] == "ownership-path"


def test_preflight_surfaces_compact_durable_intent_for_task(capsys) -> None:
    assert cli.main(["preflight", "--target", ".", "--task", "memory routing should preserve durable context", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    durable_intent = payload.get("durable_intent", payload.get("context", {}).get("durable_intent"))
    assert durable_intent["status"] == "present"
    assert durable_intent["subsystem_intent"]["matched_count"] >= 1
    assert durable_intent["inspect"] == "agentic-workspace report --target ./repo --section durable_intent --format json"


def test_start_matches_durable_intent_across_decision_pressure_types(tmp_path: Path, capsys) -> None:
    _write(
        tmp_path / ".agentic-workspace" / "config.toml",
        "schema_version = 1\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "system-intent" / "subsystems.toml",
        """
schema_version = 1
kind = "agentic-workspace/subsystem-intent-set/v1"
rule = "Subsystem intent is durable scoped decision pressure, not active task state by default."

[[subsystems]]
id = "performance"
scope = "runtime memory usage"
status = "active"
summary = "Keep runtime memory usage bounded."
decision_tests = ["Does this preserve memory ceilings?"]
confidence = "high"
needs_review = false

[[subsystems]]
id = "accessibility"
scope = "UX accessibility"
status = "active"
summary = "Interfaces should stay accessible to elderly users."
decision_tests = ["Can low-vision and elderly users complete the flow?"]
confidence = "medium"
needs_review = true

[[subsystems]]
id = "docs"
scope = "documentation philosophy"
status = "active"
summary = "Prefer self-documenting code over external-facing wikis."
decision_tests = ["Is the durable explanation closest to the code?"]
confidence = "medium"
needs_review = false

[[subsystems]]
id = "audit"
scope = "compliance auditability"
status = "active"
summary = "Access logs must remain auditable."
decision_tests = ["Can a reviewer reconstruct access-log decisions?"]
confidence = "high"
needs_review = false
""",
    )

    assert cli.main(["report", "--target", str(tmp_path), "--section", "durable_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    durable_intent = payload["answer"]
    matches = {match["id"] for match in durable_intent["subsystem_intent"]["matches"]}
    assert {"performance", "accessibility"} <= matches
    assert durable_intent["subsystem_intent"]["matched_count"] == 4


def test_report_durable_intent_section_returns_compact_projection(capsys) -> None:
    assert cli.main(["report", "--target", ".", "--section", "durable_intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["selector"] == {"section": "durable_intent"}
    answer = payload["answer"]
    assert answer["rule"].startswith("Use durable intent as decision pressure")
    assert answer["system_intent"]["surface"] == ".agentic-workspace/system-intent/intent.toml"
    assert answer["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"


def test_proof_changed_paths_include_subsystem_proof_hints(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[subsystems]]\n"
        'id = "workspace-cli"\n'
        'paths = ["generated/workspace/python/cli.py"]\n'
        'owns = ["workspace command routing"]\n'
        'does_not_own = ["planning state semantics"]\n'
        'proof = ["uv run pytest tests/test_workspace_cli.py -q"]\n'
        'escalate_when = ["public command contract changes"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert (
        cli.main(
            [
                "proof",
                "--verbose",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["selector"] == {"changed": ["generated/workspace/python/cli.py"]}
    answer = payload["answer"]
    assert "uv run pytest tests/test_workspace_cli.py -q" in answer["required_commands"]
    subsystem_lanes = [lane for lane in answer["selected_lanes"] if lane["id"] == "subsystem:workspace-cli"]
    assert subsystem_lanes
    assert subsystem_lanes[0]["subsystem"]["does_not_own"] == ["planning state semantics"]
    assert answer["subsystem_ownership"]["matched_subsystems"][0]["matched_paths"] == ["generated/workspace/python/cli.py"]
