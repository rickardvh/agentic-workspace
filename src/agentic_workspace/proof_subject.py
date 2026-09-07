"""Host runtime observations for the shared dependency-scoped proof owner.

The Rust owner reads confined semantic inputs and owns identity/currentness.
Python-issued subjects retain their actual recorder runtime for compatibility;
this adapter does not turn caller observations into evidence authority.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from agentic_workspace.decision import proof_subject

PROOF_SUBJECT_KIND = "agentic-workspace/proof-subject/v1"


def proof_dependency_role(path: str, *, semantic_input_paths: list[str] | None = None) -> dict[str, str]:
    return proof_subject({"action": "dependency-role", "path": path, "semantic_input_paths": semantic_input_paths})


def build_proof_subject(
    *,
    target_root: Path,
    changed_paths: list[str],
    command: str,
    claim_classes: list[str] | None = None,
    effect_scope: list[str] | None = None,
    semantic_input_paths: list[str] | None = None,
) -> dict[str, Any]:
    return proof_subject(
        {
            "action": "build",
            "target": str(target_root),
            "changed_paths": changed_paths,
            "command": command,
            "claim_classes": claim_classes,
            "effect_scope": effect_scope,
            "semantic_input_paths": semantic_input_paths,
            "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        }
    )


def classify_proof_subject(*, target_root: Path, receipt: dict[str, Any], changed_paths: list[str], command: str) -> dict[str, Any]:
    return proof_subject(
        {
            "action": "classify",
            "target": str(target_root),
            "receipt": receipt,
            "changed_paths": changed_paths,
            "command": command,
            "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        }
    )


def compare_proof_subjects(*, stored: dict[str, Any], current: dict[str, Any], minimum_rerun_command: str = "") -> dict[str, Any]:
    return proof_subject({"action": "compare", "stored": stored, "current": current, "minimum_rerun_command": minimum_rerun_command})


def classify_proof_subjects(*, target_root: Path, receipts: list[dict[str, Any]], changed_paths: list[str]) -> list[dict[str, Any]]:
    """Transport one evaluation in bounded batches; retain no reuse cache."""
    runtime = {"implementation": platform.python_implementation(), "version": platform.python_version()}
    results: list[dict[str, Any]] = []
    for offset in range(0, len(receipts), 128):
        results.extend(
            proof_subject(
                {
                    "action": "classify-many",
                    "target": str(target_root),
                    "receipts": receipts[offset : offset + 128],
                    "changed_paths": changed_paths,
                    "runtime": runtime,
                }
            )["results"]
        )
    return results
