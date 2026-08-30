from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

METRICS_KIND = "agentic-workspace/assignment-transport-metrics/v1"


def parse_codex_jsonl(text: str) -> dict[str, Any]:
    usage: dict[str, Any] = {}
    orientation_commands = 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
        item = event.get("item")
        if event.get("type") == "item.completed" and isinstance(item, dict) and item.get("type") == "command_execution":
            orientation_commands += 1
    metrics: dict[str, Any] = {
        "kind": METRICS_KIND,
        "orientation_command_count": orientation_commands,
    }
    for source, target in (
        ("input_tokens", "effective_input_tokens"),
        ("cached_input_tokens", "cached_input_tokens"),
        ("output_tokens", "output_tokens"),
    ):
        value = usage.get(source)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            metrics[target] = value
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Codex as an AW assignment adapter and emit only neutral cost metrics.")
    parser.add_argument("--metrics-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--output-schema", type=Path, required=True)
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--codex-command", default=shutil.which("codex.cmd") or shutil.which("codex") or "codex")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = sys.stdin.read()
    command = [
        args.codex_command,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--config",
        "project_doc_max_bytes=0",
        "--approve-for-me",
        "--cd",
        str(args.target_root.resolve()),
        "--model",
        args.model,
        "--json",
        "--output-schema",
        str(args.output_schema.resolve()),
        "--output-last-message",
        str(args.output_file.resolve()),
        "-",
    ]
    completed = subprocess.run(command, input=prompt, text=True, capture_output=True, check=False)
    metrics = parse_codex_jsonl(completed.stdout)
    args.metrics_file.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
