"""Symbol-level working-set hints for large runtime files."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any

from agentic_workspace.contract_tooling import python_runtime_projection_inventory_manifest

LARGE_RUNTIME_PATHS = {
    "src/agentic_workspace/workspace_runtime_core.py",
    "src/agentic_workspace/workspace_runtime_primitives.py",
    "packages/planning/src/repo_planning_bootstrap/installer.py",
    "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
}

SOURCE_MODULE_BY_PATH = {
    "src/agentic_workspace/workspace_runtime_core.py": "agentic_workspace.workspace_runtime_core",
    "src/agentic_workspace/workspace_runtime_primitives.py": "agentic_workspace.workspace_runtime_primitives",
    "packages/planning/src/repo_planning_bootstrap/installer.py": "repo_planning_bootstrap.installer",
    "packages/planning/src/repo_planning_bootstrap/runtime_projection.py": "repo_planning_bootstrap.runtime_projection",
    "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py": "repo_memory_bootstrap.runtime_primitives",
}

SYMBOL_PROOF_HINTS = {
    (
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "_run_external_intent_refresh_github_adapter",
    ): [
        'uv run pytest tests/test_workspace_summary_cli.py -q -k "external_intent_refresh_applies_stale_candidate_reconciliation"',
    ],
    (
        "src/agentic_workspace/workspace_runtime_core.py",
        "_run_external_intent_refresh_github_adapter",
    ): [
        'uv run pytest tests/test_workspace_summary_cli.py -q -k "external_intent_refresh_applies_stale_candidate_reconciliation"',
    ],
    (
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "_proof_selection_for_changed_paths",
    ): [
        'uv run pytest tests/test_workspace_implement_cli.py -q -k "proof or changed_path"',
        "uv run pytest tests/test_workspace_proof_cli.py -q",
    ],
    (
        "src/agentic_workspace/workspace_runtime_core.py",
        "_proof_selection_for_changed_paths",
    ): [
        'uv run pytest tests/test_workspace_implement_cli.py -q -k "proof or changed_path"',
        "uv run pytest tests/test_workspace_proof_cli.py -q",
    ],
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _changed_line_ranges_from_git_diff(*, target_root: Path, path: str) -> list[tuple[int, int]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(target_root), "diff", "--unified=0", "--", path],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    ranges: list[tuple[int, int]] = []
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in result.stdout.splitlines():
        match = hunk_pattern.match(line)
        if not match:
            continue
        start = int(match.group(1))
        length = int(match.group(2) or "1")
        ranges.append((start, start if length == 0 else start + length - 1))
    return ranges


def _python_symbol_spans(*, target_root: Path, path: str) -> dict[str, tuple[int, int]]:
    try:
        module = ast.parse((target_root / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    spans: dict[str, tuple[int, int]] = {}
    for node in ast.walk(module):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        spans[node.name] = (node.lineno, int(getattr(node, "end_lineno", node.lineno)))
    return spans


def _ranges_intersect(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _inventory_entries_by_symbol() -> dict[tuple[str, str], dict[str, Any]]:
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception:
        return {}
    accepted = inventory.get("accepted_runtime_boundaries", {})
    entries = accepted.get("entries", []) if isinstance(accepted, dict) else []
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        source_module = str(entry.get("source_module", "")).strip()
        source_symbol = str(entry.get("source_symbol", "")).strip()
        if source_module and source_symbol:
            result[(source_module, source_symbol)] = entry
    return result


def _symbol_inventory_payload(*, path: str, symbol: str, entries_by_symbol: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    entry = entries_by_symbol.get((SOURCE_MODULE_BY_PATH.get(path, ""), symbol))
    if not isinstance(entry, dict):
        return {"status": "not-in-runtime-inventory"}
    return {
        "status": "inventory-backed",
        "owner": entry.get("owner_package", ""),
        "binding_kind": entry.get("binding_kind", ""),
        "runtime_boundary_class": entry.get("runtime_boundary_class", ""),
        "runtime_boundary_reason": entry.get("runtime_boundary_reason", ""),
        "operation_ids": entry.get("operation_ids", []),
        "primitive_refs": entry.get("primitive_refs", []),
        "conformance_ref": entry.get("conformance_ref", ""),
    }


def runtime_symbol_working_set_for_changed_paths(changed_paths: list[str], *, target_root: Path | None = None) -> dict[str, Any]:
    if target_root is None:
        return {"kind": "agentic-workspace/runtime-symbol-working-set/v1", "status": "unavailable", "files": []}
    files: list[dict[str, Any]] = []
    entries_by_symbol = _inventory_entries_by_symbol()
    for path in changed_paths:
        if path not in LARGE_RUNTIME_PATHS:
            continue
        changed_ranges = _changed_line_ranges_from_git_diff(target_root=target_root, path=path)
        if not changed_ranges:
            continue
        spans = _python_symbol_spans(target_root=target_root, path=path)
        symbols: list[dict[str, Any]] = []
        for symbol, span in sorted(spans.items(), key=lambda item: (item[1][0], item[0])):
            if not any(_ranges_intersect(span, changed_range) for changed_range in changed_ranges):
                continue
            proof_hints = SYMBOL_PROOF_HINTS.get((path, symbol), [])
            symbols.append(
                {
                    "name": symbol,
                    "span": {"start": span[0], "end": span[1]},
                    "inventory": _symbol_inventory_payload(path=path, symbol=symbol, entries_by_symbol=entries_by_symbol),
                    "nearest_tests": proof_hints,
                    "smallest_focused_proof": proof_hints[0] if proof_hints else "",
                }
            )
        if symbols:
            files.append(
                {
                    "path": path,
                    "source_module": SOURCE_MODULE_BY_PATH.get(path, ""),
                    "changed_line_ranges": [{"start": start, "end": end} for start, end in changed_ranges],
                    "symbol_count": len(symbols),
                    "symbols": symbols[:8],
                }
            )
    proof_commands = _dedupe(
        [
            command
            for file_payload in files
            for symbol in file_payload.get("symbols", [])
            for command in symbol.get("nearest_tests", [])
            if isinstance(command, str) and command.strip()
        ]
    )
    return {
        "kind": "agentic-workspace/runtime-symbol-working-set/v1",
        "status": "present" if files else "not-applicable",
        "file_count": len(files),
        "files": files,
        "recommended_focused_proof_commands": proof_commands,
        "rule": (
            "Large runtime symbol routing is advisory and is derived from git diff hunks, AST symbol spans, "
            "explicit test hints, and runtime inventories; it does not infer domain ownership from names or prose."
        ),
    }


def tiny_runtime_symbol_working_set_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    if value.get("status") == "selector-backed":
        return {
            key: value.get(key)
            for key in (
                "kind",
                "status",
                "changed_paths",
                "file_count",
                "detail_selector",
                "detail_command",
                "rule",
            )
            if key in value
        }
    if value.get("status") != "present":
        return {}
    files: list[dict[str, Any]] = []
    for file_payload in value.get("files", []) if isinstance(value.get("files"), list) else []:
        if not isinstance(file_payload, dict):
            continue
        symbols: list[dict[str, Any]] = []
        for symbol in file_payload.get("symbols", [])[:5] if isinstance(file_payload.get("symbols"), list) else []:
            if not isinstance(symbol, dict):
                continue
            inventory = symbol.get("inventory", {}) if isinstance(symbol.get("inventory"), dict) else {}
            symbols.append(
                {
                    "name": symbol.get("name", ""),
                    "span": symbol.get("span", {}),
                    "inventory_status": inventory.get("status", "unknown"),
                    "owner": inventory.get("owner", ""),
                    "runtime_boundary_class": inventory.get("runtime_boundary_class", ""),
                    "smallest_focused_proof": symbol.get("smallest_focused_proof", ""),
                }
            )
        files.append(
            {
                "path": file_payload.get("path", ""),
                "symbol_count": file_payload.get("symbol_count", len(symbols)),
                "symbols": symbols,
            }
        )
    return {
        "kind": value.get("kind", "agentic-workspace/runtime-symbol-working-set/v1"),
        "status": value.get("status", "unknown"),
        "file_count": value.get("file_count", len(files)),
        "files": files,
        "recommended_focused_proof_commands": value.get("recommended_focused_proof_commands", [])[:5],
        "rule": value.get("rule", ""),
    }
