"""Owner repair operations used by composed-operation gate revalidation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def clear_overlapping_mutation_claims(*, target: Path) -> dict[str, Any]:
    claims_path = target / ".agentic-workspace" / "local" / "mutation-claims.json"
    if not claims_path.exists():
        return {"kind": "agentic-workspace/mutation-claim-repair/v1", "status": "not-needed"}
    _write_json(
        claims_path,
        {"kind": "agentic-workspace/mutation-claims/v1", "checked_in_repo_effect": "none", "claims": []},
    )
    return {
        "kind": "agentic-workspace/mutation-claim-repair/v1",
        "status": "applied",
        "operation": "inspect-overlap-owner",
        "source": ".agentic-workspace/local/mutation-claims.json",
    }


def admit_delegated_return_result(*, target: Path) -> dict[str, Any]:
    path = target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json"
    _write_json(path, {"status": "admitted", "revision": "repair"})
    return {
        "kind": "agentic-workspace/delegated-return-repair/v1",
        "status": "applied",
        "operation": "admit-or-repair-return",
        "source": ".agentic-workspace/local/delegation/returned-result.json",
    }


def restore_runtime_availability(*, target: Path) -> dict[str, Any]:
    path = target / ".agentic-workspace" / "local" / "runtime" / "availability.json"
    _write_json(path, {"status": "restored"})
    return {
        "kind": "agentic-workspace/runtime-readiness-repair/v1",
        "status": "applied",
        "operation": "restore-runtime",
        "source": ".agentic-workspace/local/runtime/availability.json",
    }


def replace_external_observation(*, target: Path, source: str) -> dict[str, Any]:
    path = target / source
    _write_json(path, {"status": "current", "observation": "valid"})
    return {
        "kind": "agentic-workspace/external-observation-repair/v1",
        "status": "applied",
        "operation": "request-valid-observation",
        "source": source,
    }


def restore_workspace_startup_skill(*, target: Path) -> dict[str, Any]:
    missing = target / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.missing"
    restored = missing.with_suffix(".md")
    if missing.exists():
        missing.rename(restored)
    return {
        "kind": "agentic-workspace/skill-routing-repair/v1",
        "status": "applied" if restored.exists() else "blocked",
        "operation": "install-or-select-supported-skill",
        "source": ".agentic-workspace/skills/workspace-startup/SKILL.md",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
