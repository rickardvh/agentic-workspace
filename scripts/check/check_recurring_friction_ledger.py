#!/usr/bin/env python3
"""Advisory check for the repo's recurring-friction ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NamedTuple

from repo_memory_bootstrap._installer_memory import (
    _recurring_friction_promotion_findings,
    _recurring_friction_structure_findings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = REPO_ROOT / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"


class LedgerWarning(NamedTuple):
    warning_class: str
    path: str
    message: str


def gather_ledger_warnings(*, repo_root: Path = REPO_ROOT) -> list[LedgerWarning]:
    ledger_path = repo_root / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"
    if not ledger_path.exists():
        return [
            LedgerWarning(
                "missing_recurring_friction_ledger",
                ledger_path.relative_to(repo_root).as_posix(),
                "Recurring-friction ledger is missing; refresh the installed memory payload before relying on recurring-friction evidence.",
            )
        ]

    text = ledger_path.read_text(encoding="utf-8")
    warnings: list[LedgerWarning] = []
    relative_path = ledger_path.relative_to(repo_root).as_posix()
    for message in _recurring_friction_structure_findings(text):
        warnings.append(LedgerWarning("recurring_friction_structure", relative_path, message))
    for message in _recurring_friction_promotion_findings(text):
        warnings.append(LedgerWarning("recurring_friction_promotion_pressure", relative_path, message))
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    warnings = gather_ledger_warnings()
    if args.format == "json":
        print(
            json.dumps(
                {
                    "kind": "recurring-friction-ledger-report/v1",
                    "warning_count": len(warnings),
                    "warnings": [warning._asdict() for warning in warnings],
                },
                indent=2,
            )
        )
    else:
        print("Recurring friction ledger health report")
        if not warnings:
            print("- No recurring-friction ledger warnings detected.")
        else:
            for warning in warnings:
                print(f"- {warning.warning_class}: {warning.path}: {warning.message}")
    if any(warning.warning_class in {"missing_recurring_friction_ledger", "recurring_friction_structure"} for warning in warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
