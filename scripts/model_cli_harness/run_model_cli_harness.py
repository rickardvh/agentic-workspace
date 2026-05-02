"""Run black-box model CLI dogfooding scenarios in disposable fixtures."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "scratch" / "model-cli-harness"


@dataclass(frozen=True)
class HarnessPaths:
    run_root: Path
    fixture_root: Path
    repo_path: Path
    transcript_path: Path
    share_path: Path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _replace_placeholders(value: str, *, replacements: dict[str, str]) -> str:
    rendered = value
    for key, replacement in replacements.items():
        rendered = rendered.replace("{" + key + "}", replacement)
    return rendered


def _render_list(values: list[str], *, replacements: dict[str, str]) -> list[str]:
    return [_replace_placeholders(value, replacements=replacements) for value in values]


def _render_prompt(template: str, *, replacements: dict[str, str]) -> str:
    return _replace_placeholders(template, replacements=replacements)


def _scenario_paths(*, output_root: Path, suite_id: str, scenario_id: str, adapter_id: str, model: str) -> HarnessPaths:
    safe_model = model.replace("/", "_").replace(":", "_").replace(" ", "_")
    run_root = output_root / f"{_now_id()}-{suite_id}-{scenario_id}-{adapter_id}-{safe_model}"
    fixture_root = run_root / "fixture"
    repo_path = run_root / "repo"
    transcript_path = run_root / "transcript.jsonl"
    share_path = run_root / "session.md"
    return HarnessPaths(
        run_root=run_root,
        fixture_root=fixture_root,
        repo_path=repo_path,
        transcript_path=transcript_path,
        share_path=share_path,
    )


def _prepare_fixture(*, suite_path: Path, scenario: dict[str, Any], paths: HarnessPaths) -> None:
    fixture = scenario.get("fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        raise ValueError(f"scenario {scenario.get('id', '<unknown>')} must specify fixture")
    fixture_path = (suite_path.parent / ".." / "fixtures" / fixture).resolve()
    if not fixture_path.exists():
        fixture_path = (REPO_ROOT / fixture).resolve()
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture}")
    paths.run_root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(fixture_path, paths.repo_path)


def _run_command(command: list[str], *, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _copy_transcript(stdout: str, transcript_path: Path) -> None:
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(stdout, encoding="utf-8")


def run_suite(
    *,
    suite_path: Path,
    adapter_id: str,
    model: str | None,
    scenario_filter: str | None,
    execute: bool,
    output_root: Path,
    timeout_seconds: int | None,
) -> dict[str, Any]:
    suite = _load_json(suite_path)
    suite_id = str(suite.get("id", suite_path.stem))
    adapters = suite.get("adapters", {})
    if not isinstance(adapters, dict) or adapter_id not in adapters:
        raise ValueError(f"adapter '{adapter_id}' is not defined in {suite_path}")
    adapter = adapters[adapter_id]
    if not isinstance(adapter, dict):
        raise ValueError(f"adapter '{adapter_id}' must be an object")
    resolved_model = model or str(adapter.get("default_model", "default"))
    adapter_timeout = int(adapter.get("timeout_seconds", 900))
    effective_timeout = timeout_seconds or adapter_timeout
    scenarios = suite.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("suite.scenarios must be a list")

    selected = [item for item in scenarios if not scenario_filter or item.get("id") == scenario_filter]
    if scenario_filter and not selected:
        raise ValueError(f"scenario '{scenario_filter}' is not defined in {suite_path}")

    run_results: list[dict[str, Any]] = []
    for scenario in selected:
        if not isinstance(scenario, dict):
            raise ValueError("scenario entries must be objects")
        scenario_id = str(scenario["id"])
        paths = _scenario_paths(
            output_root=output_root,
            suite_id=suite_id,
            scenario_id=scenario_id,
            adapter_id=adapter_id,
            model=resolved_model,
        )
        _prepare_fixture(suite_path=suite_path, scenario=scenario, paths=paths)
        replacements = {
            "repo": str(paths.repo_path),
            "run_root": str(paths.run_root),
            "share_path": str(paths.share_path),
            "transcript_path": str(paths.transcript_path),
            "model": resolved_model,
            "source_root": str(REPO_ROOT),
        }
        prompt = _render_prompt(str(scenario.get("prompt", "")), replacements=replacements)
        replacements["prompt"] = prompt
        command_template = adapter.get("command")
        if not isinstance(command_template, list) or not all(isinstance(item, str) for item in command_template):
            raise ValueError(f"adapter '{adapter_id}' must define command as a string list")
        command = _render_list(command_template, replacements=replacements)

        setup_results: list[dict[str, Any]] = []
        setup_commands = scenario.get("setup_commands", [])
        if setup_commands and not isinstance(setup_commands, list):
            raise ValueError(f"scenario '{scenario_id}' setup_commands must be a list")
        if execute:
            for setup_command in setup_commands:
                if not isinstance(setup_command, list) or not all(isinstance(item, str) for item in setup_command):
                    raise ValueError(f"scenario '{scenario_id}' setup command must be a string list")
                setup_results.append(
                    _run_command(
                        _render_list(setup_command, replacements=replacements),
                        cwd=paths.repo_path,
                        timeout_seconds=effective_timeout,
                    )
                )

        invocation: dict[str, Any] = {
            "scenario_id": scenario_id,
            "adapter_id": adapter_id,
            "model": resolved_model,
            "execute": execute,
            "repo_path": str(paths.repo_path),
            "run_root": str(paths.run_root),
            "prompt": prompt,
            "command": command,
            "setup_results": setup_results,
            "expected_signals": scenario.get("expected_signals", []),
            "score_notes": scenario.get("score_notes", []),
        }
        if execute:
            result = _run_command(command, cwd=paths.repo_path, timeout_seconds=effective_timeout)
            _copy_transcript(str(result.get("stdout", "")), paths.transcript_path)
            invocation["result"] = result
            invocation["transcript_path"] = str(paths.transcript_path)
            invocation["share_path"] = str(paths.share_path)
        else:
            invocation["result"] = {
                "status": "dry-run",
                "detail": "Use --execute to run the model CLI.",
            }
        _write_json(paths.run_root / "run.json", invocation)
        run_results.append(invocation)

    payload = {
        "schema": "agentic-workspace/model-cli-harness-result/v1",
        "suite": str(suite_path),
        "suite_id": suite_id,
        "adapter": adapter_id,
        "model": resolved_model,
        "execute": execute,
        "result_count": len(run_results),
        "results": run_results,
    }
    _write_json(output_root / f"{_now_id()}-{suite_id}-{adapter_id}-summary.json", payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--adapter", default="copilot")
    parser.add_argument("--model")
    parser.add_argument("--scenario")
    parser.add_argument("--execute", action="store_true", help="Run the model CLI. Defaults to dry-run.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = run_suite(
            suite_path=args.suite.resolve(),
            adapter_id=args.adapter,
            model=args.model,
            scenario_filter=args.scenario,
            execute=args.execute,
            output_root=args.output_root.resolve(),
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        if args.format == "json":
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"model CLI harness failed: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        mode = "executed" if args.execute else "dry-run"
        print(f"{mode} {payload['result_count']} scenario(s) for {payload['adapter']}:{payload['model']}")
        for result in payload["results"]:
            print(f"- {result['scenario_id']}: {result['run_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
