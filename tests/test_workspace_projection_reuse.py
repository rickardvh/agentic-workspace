from __future__ import annotations

import json
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
    scratch.write_text("decision-relevant local diagnostic\n", encoding="utf-8")
    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0
    after_scratch = json.loads(capsys.readouterr().out)
    assert after_scratch.get("kind") != "agentic-workspace/unchanged-projection/v1"

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
