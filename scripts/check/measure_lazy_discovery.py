#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from agentic_workspace import cli


def _capture_json(args: list[str]) -> dict[str, Any]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = cli.main(args)
    if exit_code != 0:
        raise RuntimeError(f"CLI command failed: {' '.join(args)}")
    return json.loads(buffer.getvalue())


def _approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _measure_case(*, label: str, question: str, full_args: list[str], narrow_args: list[str]) -> dict[str, Any]:
    full_payload = _capture_json(full_args)
    narrow_payload = _capture_json(narrow_args)
    full_text = _render_json(full_payload)
    narrow_text = _render_json(narrow_payload)
    full_chars = len(full_text)
    narrow_chars = len(narrow_text)
    full_bytes = len(full_text.encode("utf-8"))
    narrow_bytes = len(narrow_text.encode("utf-8"))
    full_tokens = _approx_tokens(full_text)
    narrow_tokens = _approx_tokens(narrow_text)
    return {
        "label": label,
        "question": question,
        "full_command": " ".join(full_args),
        "narrow_command": " ".join(narrow_args),
        "full_chars": full_chars,
        "narrow_chars": narrow_chars,
        "chars_saved": full_chars - narrow_chars,
        "char_reduction_percent": round(((full_chars - narrow_chars) / full_chars) * 100, 1),
        "full_bytes": full_bytes,
        "narrow_bytes": narrow_bytes,
        "bytes_saved": full_bytes - narrow_bytes,
        "byte_reduction_percent": round(((full_bytes - narrow_bytes) / full_bytes) * 100, 1),
        "full_approx_tokens": full_tokens,
        "narrow_approx_tokens": narrow_tokens,
        "approx_tokens_saved": full_tokens - narrow_tokens,
        "approx_token_reduction_percent": round(((full_tokens - narrow_tokens) / full_tokens) * 100, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure lazy-discovery savings for compact contract selectors.")
    parser.add_argument("--target", default=".", help="Repository target path for proof/ownership measurements.")
    args = parser.parse_args(argv)
    target = Path(args.target).resolve().as_posix()

    measurements = [
        _measure_case(
            label="validation_lane",
            question="How do I choose the proof lane?",
            full_args=["defaults", "--format", "json"],
            narrow_args=["defaults", "--section", "validation", "--format", "json"],
        ),
        _measure_case(
            label="current_proof_state",
            question="What is the current proof state for this repo?",
            full_args=["proof", "--target", target, "--format", "json"],
            narrow_args=["proof", "--target", target, "--current", "--format", "json"],
        ),
        _measure_case(
            label="active_execution_owner",
            question="Who owns active execution state?",
            full_args=["ownership", "--target", target, "--format", "json"],
            narrow_args=["ownership", "--target", target, "--concern", "active-execution-state", "--format", "json"],
        ),
    ]

    totals = {
        "full_bytes": sum(item["full_bytes"] for item in measurements),
        "narrow_bytes": sum(item["narrow_bytes"] for item in measurements),
        "bytes_saved": sum(item["bytes_saved"] for item in measurements),
        "full_approx_tokens": sum(item["full_approx_tokens"] for item in measurements),
        "narrow_approx_tokens": sum(item["narrow_approx_tokens"] for item in measurements),
        "approx_tokens_saved": sum(item["approx_tokens_saved"] for item in measurements),
    }
    totals["byte_reduction_percent"] = round((totals["bytes_saved"] / totals["full_bytes"]) * 100, 1)
    totals["approx_token_reduction_percent"] = round(
        (totals["approx_tokens_saved"] / totals["full_approx_tokens"]) * 100,
        1,
    )

    payload = {
        "schema_version": "lazy-discovery-measurements/v1",
        "target": target,
        "method": {
            "rule": "Compare full machine-readable contract outputs against the selector-shaped narrow answer for the same question.",
            "token_proxy": "approx_tokens = ceil(character_count / 4)",
            "notes": [
                "This is a cheap retrieval-size proxy, not model-exact token accounting.",
                "The first framework measures one-answer retrieval cost for the current defaults/proof/ownership selector path.",
            ],
        },
        "measurements": measurements,
        "totals": totals,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
