"""Generated target-local operation composition helpers.

Source: src/agentic_workspace/contracts/command_package_ir.json
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

# DO NOT EDIT DIRECTLY.
# Operation composition behavior changes belong in command_generation.operation_composition.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def operation_fragments(operation: dict[str, Any], *, error_type: type[Exception] = RuntimeError) -> dict[str, list[dict[str, Any]]]:
    raw_fragments = operation.get("ir_plan", {}).get("fragments", [])
    if raw_fragments in (None, []):
        return {}
    if not isinstance(raw_fragments, list):
        raise error_type("operation ir_plan.fragments must be a list")
    fragments: dict[str, list[dict[str, Any]]] = {}
    for raw_fragment in raw_fragments:
        if not isinstance(raw_fragment, dict):
            raise error_type("operation ir_plan fragment must be an object")
        fragment_id = str(raw_fragment.get("id", "")).strip()
        if not fragment_id:
            raise error_type("operation ir_plan fragment id is required")
        if fragment_id in fragments:
            raise error_type(f"duplicate operation ir_plan fragment: {fragment_id!r}")
        fragment_steps = raw_fragment.get("steps", [])
        if not isinstance(fragment_steps, list) or not fragment_steps:
            raise error_type(f"operation ir_plan fragment {fragment_id!r} must declare non-empty steps")
        fragments[fragment_id] = fragment_steps
    return fragments


def expand_operation_steps(
    steps: Sequence[Any],
    *,
    fragments: Mapping[str, list[dict[str, Any]]],
    error_type: type[Exception] = RuntimeError,
    stack: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for raw_step in steps:
        if not isinstance(raw_step, dict):
            raise error_type("operation ir_plan step must be an object")
        uses = str(raw_step.get("uses", "")).strip()
        uses_fragment = str(raw_step.get("uses_fragment", "")).strip()
        if uses and uses_fragment:
            raise error_type(f"step {raw_step.get('id', uses)!r} cannot declare both uses and uses_fragment")
        if uses_fragment:
            if raw_step.get("arguments") not in (None, {}):
                raise error_type(f"fragment step {raw_step.get('id', uses_fragment)!r} cannot declare arguments")
            if raw_step.get("outputs") not in (None, []):
                raise error_type(f"fragment step {raw_step.get('id', uses_fragment)!r} cannot declare outputs")
            if uses_fragment in stack:
                cycle = " -> ".join((*stack, uses_fragment))
                raise error_type(f"operation ir_plan fragment cycle: {cycle}")
            try:
                fragment_steps = fragments[uses_fragment]
            except KeyError as exc:
                raise error_type(f"unknown operation ir_plan fragment: {uses_fragment!r}") from exc
            expanded.extend(
                expand_operation_steps(
                    fragment_steps,
                    fragments=fragments,
                    error_type=error_type,
                    stack=(*stack, uses_fragment),
                )
            )
            continue
        if not uses:
            raise error_type(f"step {raw_step.get('id', '<unknown>')!r} must declare uses or uses_fragment")
        expanded.append(raw_step)
    return expanded
