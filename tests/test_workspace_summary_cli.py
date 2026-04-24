from __future__ import annotations

import json
from pathlib import Path

from repo_planning_bootstrap.installer import install_bootstrap

from agentic_workspace import cli


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _minimal_execplan() -> str:
    return (
        "# Plan Alpha\n\n"
        "## Goal\n\n"
        "- Requested outcome: Keep scope clear.\n\n"
        "## Next Action\n\n"
        "- Add one checker.\n\n"
        "## Completion Criteria\n\n"
        "- Warning classes are emitted for known drift.\n\n"
        "## Proof\n\n"
        "- uv run pytest tests/test_check_planning_surfaces.py\n\n"
        "## Milestone Status\n\n"
        "- Status: active\n"
    )


def test_workspace_summary_json_defaults_to_compact_profile(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(
        tmp_path / ".agentic-workspace/planning/state.toml",
        """
[todo]
active_items = [
  { id = "plan-alpha", status = "in-progress", surface = ".agentic-workspace/planning/execplans/plan-alpha.md", why_now = "keep compact startup cheap." }
]
queued_items = []

[roadmap]
lanes = [
  { id = "tracked-lane", title = "Tracked lane", priority = "first", issues = ["EXT-1"], outcome = "Keep tracked.", reason = "Needed.", promotion_signal = "Promote when needed.", suggested_first_slice = "Do the thing." },
]
candidates = [
  { priority = "first", summary = "Tracked lane" },
]
""",
    )
    _write(tmp_path / ".agentic-workspace/planning/execplans/plan-alpha.md", _minimal_execplan())

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["profile"] == "compact"
    assert payload["schema"]["schema_version"] == "planning-summary-compact-schema/v1"
    assert "candidate_lanes" not in payload["roadmap"]


def test_workspace_summary_json_accepts_full_profile(tmp_path: Path, capsys) -> None:
    install_bootstrap(target=tmp_path)
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")

    exit_code = cli.main(["summary", "--target", str(tmp_path), "--format", "json", "--profile", "full"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["profile"] == "full"
    assert payload["schema"]["schema_version"] == "planning-summary-schema/v1"
