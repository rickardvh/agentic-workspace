from __future__ import annotations

# ruff: noqa: F403,F405
import json
from typing import Any

from tests.workspace_cli_support import *


def _field_count(value: object) -> int:
    if isinstance(value, dict):
        return len(value) + sum(_field_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_field_count(item) for item in value)
    return 0


def _assert_budget(payload: dict[str, Any], budget: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(encoded) <= int(budget["max_json_bytes"])
    assert _field_count(payload) <= int(budget["max_field_count"])
    assert (len(encoded) + 3) // 4 <= int(budget["max_estimated_tokens"])


def _run_json(capsys: Any, argv: list[str]) -> dict[str, Any]:
    assert cli.main([*argv, "--format", "json"]) == 0
    return json.loads(capsys.readouterr().out)


def _semantic_signature(surface: str, payload: dict[str, Any]) -> tuple[Any, ...]:
    if surface == "start":
        return (payload.get("kind"), payload.get("next_safe_action", {}).get("next_safe_action"), payload.get("workflow_participation"))
    if surface == "report":
        return (payload.get("kind"), payload.get("next_action"), payload.get("report_profile"))
    if surface == "doctor":
        return (payload.get("kind"), payload.get("status"), payload.get("scoped_health"))
    return (payload.get("kind"), payload.get("profile"), payload.get("status"))


def test_all_declared_ordinary_profiles_obey_authoritative_output_budgets(tmp_path: Path, capsys: Any) -> None:
    _init_git_repo(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("fixture\n", encoding="utf-8")

    cold_init = _run_json(capsys, ["init", "--target", str(tmp_path), "--dry-run"])
    applied_init = _run_json(capsys, ["init", "--target", str(tmp_path)])
    warm_init = _run_json(capsys, ["init", "--target", str(tmp_path), "--dry-run"])
    operational = _run_json(capsys, ["report", "--target", str(tmp_path), "--section", "operational_compression"])["answer"]
    contract = operational["measures"]["ordinary_default_output_budget"]
    budgets = {item["surface"]: item for item in contract["representative_surfaces"]}

    commands = {
        "start": ["start", "--target", str(tmp_path), "--task", "Fix one docs typo"],
        "implement": ["implement", "--target", str(tmp_path), "--changed", "README.md", "--task", "Fix one docs typo"],
        "summary": ["summary", "--target", str(tmp_path)],
        "report": ["report", "--target", str(tmp_path)],
        "proof": ["proof", "--target", str(tmp_path), "--changed", "README.md"],
        "doctor": ["doctor", "--target", str(tmp_path)],
    }
    samples: dict[str, dict[str, Any]] = {"init": warm_init}
    for surface, argv in commands.items():
        samples[surface] = _run_json(capsys, argv)

    assert set(samples) == set(budgets)
    for surface, payload in samples.items():
        _assert_budget(payload, budgets[surface])
        assert budgets[surface]["proof"] == "test_all_declared_ordinary_profiles_obey_authoritative_output_budgets"

    for payload in (cold_init, applied_init, warm_init):
        _assert_budget(payload, budgets["init"])
    assert cold_init.keys() == warm_init.keys()

    for surface in ("start", "report", "doctor"):
        cold = samples[surface]
        warm = _run_json(capsys, commands[surface])
        _assert_budget(warm, budgets[surface])
        assert _semantic_signature(surface, cold) == _semantic_signature(surface, warm)

    for surface, argv in {"init": ["init", "--target", str(tmp_path), "--dry-run"], **commands}.items():
        assert cli.main(argv) == 0
        lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
        assert len(lines) <= int(budgets[surface]["max_human_lines"])

    verbose_init = _run_json(capsys, ["init", "--target", str(tmp_path), "--dry-run", "--verbose"])
    assert "module_reports" in verbose_init
    selected_start = _run_json(capsys, ["start", "--target", str(tmp_path), "--task", "Fix one docs typo", "--select", "next_safe_action"])
    assert selected_start["values"]["next_safe_action"]
