"""Run black-box model CLI dogfooding scenarios in disposable fixtures."""

from __future__ import annotations

import argparse
import json
import os
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


def _run_command(command: list[str], *, cwd: Path, timeout_seconds: int, env: dict[str, str] | None = None) -> dict[str, Any]:
    resolved_command = list(command)
    executable = shutil.which(resolved_command[0])
    if executable is not None:
        resolved_command[0] = executable
    completed = subprocess.run(  # noqa: S603
        resolved_command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
        env=env,
    )
    return {
        "command": resolved_command,
        "original_command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _preflight_requirement(name: str, *, kind: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    return {
        "kind": kind,
        "name": name,
        "status": "present" if resolved else "missing",
        "resolved_path": resolved or "",
        "blocking": resolved is None,
    }


def _adapter_preflight(adapter: dict[str, Any], *, command: list[str]) -> dict[str, Any]:
    requirements: list[dict[str, Any]] = []
    if command:
        requirements.append(_preflight_requirement(command[0], kind="adapter_executable"))
    for name in adapter.get("required_executables", []):
        if not isinstance(name, str):
            raise ValueError("adapter.required_executables entries must be strings")
        requirements.append(_preflight_requirement(name, kind="required_executable"))
    for name in adapter.get("required_shells", []):
        if not isinstance(name, str):
            raise ValueError("adapter.required_shells entries must be strings")
        requirements.append(_preflight_requirement(name, kind="required_shell"))

    missing = [item for item in requirements if item["status"] == "missing"]
    block_on_failure = bool(adapter.get("block_on_preflight_failure", True))
    status = "environment-blocked" if block_on_failure and missing else "ready"
    return {
        "status": status,
        "block_on_failure": block_on_failure,
        "requirements": requirements,
        "missing_count": len(missing),
        "missing": missing,
    }


def _adapter_environment(
    adapter: dict[str, Any],
    *,
    replacements: dict[str, str],
    isolate_provider_home: bool,
) -> dict[str, str]:
    env = dict(os.environ)
    configured = adapter.get("env", {})
    if configured:
        if not isinstance(configured, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in configured.items()):
            raise ValueError("adapter.env must be an object of string values")
        env.update({key: _replace_placeholders(value, replacements=replacements) for key, value in configured.items()})
    provider_home_env = adapter.get("provider_home_env")
    if isolate_provider_home and provider_home_env:
        if not isinstance(provider_home_env, str):
            raise ValueError("adapter.provider_home_env must be a string")
        env[provider_home_env] = _replace_placeholders(str(adapter.get("provider_home_path", "{run_root}/provider-home")), replacements=replacements)
    return env


def _copy_transcript(stdout: str, transcript_path: Path) -> None:
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(stdout, encoding="utf-8")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _execution_warnings(*, stdout: str, repo_path: Path) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_text = json.dumps(event)
        if "pwsh.exe" in event_text and "not recognized" in event_text:
            warnings.append(
                {
                    "warning_class": "model_cli_shell_unavailable",
                    "message": "The model CLI could not run shell commands because pwsh.exe was unavailable.",
                }
            )
        if event.get("type") != "result":
            continue
        usage = event.get("usage", {})
        if not isinstance(usage, dict):
            continue
        code_changes = usage.get("codeChanges", {})
        if not isinstance(code_changes, dict):
            continue
        modified = code_changes.get("filesModified", [])
        if not isinstance(modified, list):
            continue
        external_paths = [
            str(path)
            for item in modified
            if isinstance(item, str)
            for path in [Path(item)]
            if not _is_relative_to(path, repo_path)
        ]
        if external_paths:
            warnings.append(
                {
                    "warning_class": "model_cli_external_write",
                    "message": "The model CLI reported modified files outside the copied scenario repository.",
                    "paths": "; ".join(external_paths),
                }
            )
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning["warning_class"], warning["message"])
        if key not in seen:
            deduped.append(warning)
            seen.add(key)
    return deduped


def run_suite(
    *,
    suite_path: Path,
    adapter_id: str,
    model: str | None,
    scenario_filter: str | None,
    execute: bool,
    output_root: Path,
    timeout_seconds: int | None,
    isolate_provider_home: bool = False,
    allow_environment_blocked: bool = False,
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
        preflight = _adapter_preflight(adapter, command=command)
        adapter_env = _adapter_environment(
            adapter,
            replacements=replacements,
            isolate_provider_home=isolate_provider_home,
        )
        provider_home_env = adapter.get("provider_home_env")
        if isolate_provider_home and isinstance(provider_home_env, str) and provider_home_env in adapter_env:
            Path(adapter_env[provider_home_env]).mkdir(parents=True, exist_ok=True)

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
                        env=adapter_env,
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
            "preflight": preflight,
            "isolate_provider_home": isolate_provider_home,
            "setup_results": setup_results,
            "expected_signals": scenario.get("expected_signals", []),
            "score_notes": scenario.get("score_notes", []),
        }
        if execute and preflight["status"] == "environment-blocked" and not allow_environment_blocked:
            invocation["result"] = {
                "status": "environment-blocked",
                "detail": "Adapter preflight failed; use --allow-environment-blocked to run anyway.",
            }
            invocation["warnings"] = [
                {
                    "warning_class": "model_cli_environment_blocked",
                    "message": "Adapter preflight failed before model execution.",
                    "missing": ", ".join(item["name"] for item in preflight["missing"]),
                }
            ]
        elif execute:
            result = _run_command(command, cwd=paths.repo_path, timeout_seconds=effective_timeout, env=adapter_env)
            _copy_transcript(str(result.get("stdout", "")), paths.transcript_path)
            invocation["result"] = result
            invocation["transcript_path"] = str(paths.transcript_path)
            invocation["share_path"] = str(paths.share_path)
            invocation["warnings"] = _execution_warnings(stdout=str(result.get("stdout", "")), repo_path=paths.repo_path)
        else:
            invocation["result"] = {
                "status": "dry-run",
                "detail": "Use --execute to run the model CLI.",
            }
            invocation["warnings"] = []
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
    parser.add_argument(
        "--isolate-provider-home",
        action="store_true",
        help="Set the adapter provider-home environment variable to a run-local directory when configured.",
    )
    parser.add_argument(
        "--allow-environment-blocked",
        action="store_true",
        help="Run even when adapter preflight reports missing required local tools.",
    )
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
            isolate_provider_home=args.isolate_provider_home,
            allow_environment_blocked=args.allow_environment_blocked,
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
