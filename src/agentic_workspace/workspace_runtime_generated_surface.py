"""Generated-surface trust runtime packet helpers.

This module owns generated-surface trust projections extracted from
``workspace_runtime_primitives`` while preserving the old private import names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _runtime_attr(name: str) -> Any:
    from agentic_workspace import workspace_runtime_primitives as runtime

    return getattr(runtime, name)


class _RuntimeValue:
    def __init__(self, name: str) -> None:
        self._name = name

    def _value(self) -> Any:
        return _runtime_attr(self._name)

    def __getitem__(self, key: Any) -> Any:
        return self._value()[key]

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return self._value().get(*args, **kwargs)

    def __iter__(self):
        return iter(self._value())

    def __bool__(self) -> bool:
        return bool(self._value())


def _as_dict(*args: Any, **kwargs: Any) -> Any:
    return _runtime_attr("_as_dict")(*args, **kwargs)


def _generated_surface_trust_path_payload(*args: Any, **kwargs: Any) -> Any:
    return _runtime_attr("_generated_surface_trust_path_payload")(*args, **kwargs)


def _list_payload(*args: Any, **kwargs: Any) -> Any:
    return _runtime_attr("_list_payload")(*args, **kwargs)


def _selector_tokens(*args: Any, **kwargs: Any) -> Any:
    return _runtime_attr("_selector_tokens")(*args, **kwargs)


def _generated_surface_trust_payload(
    *, target_root: Path, changed_paths: list[str], proof: dict[str, Any], cli_invoke: str
) -> dict[str, Any]:
    items = [
        item
        for path in changed_paths
        for item in [_generated_surface_trust_path_payload(target_root=target_root, path=path, proof=proof, cli_invoke=cli_invoke)]
        if item is not None
    ]
    blocked_paths = [item["path"] for item in items if not item["direct_edit_allowed"]]
    resolution_commands = list(
        dict.fromkeys(
            command
            for item in items
            for command in _list_payload(_as_dict(item.get("action_effect")).get("resolution_commands"))
            if str(command).strip()
        )
    )
    action_effect = {
        "force": "required_before_claim" if items else "advisory",
        "allowed_now": "continue-implementation-but-refresh-generated-surfaces-before-claim" if items else "continue-implementation",
        "blocked_until_reconciled": ["claim-generated-surfaces-fresh", "claim-task-complete"] if items else [],
        "claim_boundary": (
            "generated-surface-freshness-must-be-reconciled-before-completion-claim" if items else "no-generated-surface-freshness-warning"
        ),
        "resolution_selector": "generated_surface_trust",
        "resolution_commands": resolution_commands,
    }
    return {
        "kind": "agentic-workspace/generated-surface-trust/v1",
        "status": "present" if items else "not-applicable",
        "changed_path_count": len(items),
        "items": items,
        "direct_edit_blocked_paths": blocked_paths,
        "action_effect": action_effect,
        "rule": (
            "Generated surfaces are derived artifacts. Edit the canonical source first, refresh the generated output, "
            "and run the validation command before trusting freshness."
        ),
        "detail_selector": "generated_surface_trust",
    }


def _selector_requests_generated_surface_trust(select: str | None) -> bool:
    return any(token == "generated_surface_trust" or token.startswith("generated_surface_trust.") for token in _selector_tokens(select))


def _generated_cli_freshness_payload(
    *,
    changed_paths: list[str],
    selected_lanes: list[dict[str, Any]],
    required_commands: list[str],
) -> dict[str, Any] | None:
    lane_ids = [str(lane.get("id", "")) for lane in selected_lanes if isinstance(lane, dict)]
    relevant_lane_ids = [
        lane_id
        for lane_id in lane_ids
        if lane_id in {"generated_command_packages", "cli_authority", "verification:generated_adapter_conformance"}
    ]
    related_commands = [
        command
        for command in required_commands
        if "check_generated_command_packages.py" in command or "generate_command_packages.py" in command
    ]
    if not relevant_lane_ids and not related_commands:
        return None
    freshness_check = "uv run python scripts/generate/generate_command_packages.py --check"
    refresh_command = "uv run python scripts/generate/generate_command_packages.py"
    validation_command = next(
        (command for command in related_commands if "check_generated_command_packages.py" in command),
        "uv run python scripts/check/check_generated_command_packages.py",
    )
    obligation = "required" if related_commands else "advisory"
    return {
        "kind": "agentic-workspace/generated-cli-freshness/v1",
        "status": obligation,
        "triggered_by": changed_paths,
        "selected_lanes": relevant_lane_ids,
        "freshness_check_command": freshness_check,
        "refresh_command": refresh_command,
        "validation_command": validation_command,
        "required_commands": related_commands,
        "obligation": obligation,
        "generated_target_parity": {
            "kind": "agentic-workspace/generated-target-parity/v1",
            "status": "required" if obligation == "required" else "advisory",
            "target_families": ["python", "typescript"],
            "freshness_evidence": [
                "scripts/generate/generate_command_packages.py --check compares rendered outputs for all generated Python and TypeScript package targets without writing files",
                "scripts/check/check_generated_command_packages.py performs static generated-package proof across Python and TypeScript surfaces",
            ],
            "stale_detection": {
                "python": "generated/*/python/** outputs must match command-generation render output",
                "typescript": "generated/*/typescript/** outputs must match command-generation render output",
            },
            "claim_rule": (
                "Do not claim generated CLI freshness from Python-only proof; relevant generated CLI proof must name "
                "both Python and TypeScript generated targets or record why one family is not applicable."
            ),
        },
        "rule": (
            "Generated CLI freshness is relevant only for generated command package surfaces. "
            "Run the check path before trusting generated CLI output; refresh only when the check reports stale output."
        ),
    }


def _tiny_surface_compatibility_review(changed_paths: list[str]) -> dict[str, Any]:
    risky_paths = [
        path
        for path in changed_paths
        if path
        in {
            "src/agentic_workspace/workspace_runtime_primitives.py",
            "src/agentic_workspace/contracts/schemas/startup_context.schema.json",
            "src/agentic_workspace/contracts/schemas/implementer_context.schema.json",
        }
        or path.startswith("tests/test_workspace_start_preflight_cli.py")
        or path.startswith("tests/test_workspace_implement_cli.py")
        or path.startswith("tests/test_workspace_summary_cli.py")
    ]
    if not risky_paths:
        return {"status": "not-applicable"}
    return {
        "kind": "agentic-workspace/tiny-surface-compatibility-review/v1",
        "status": "required",
        "changed_paths": risky_paths,
        "rule": "New facts usually belong behind selector, verbose, or nested context unless they are essential to the tiny next action.",
        "risk": "Tiny/default start, implement, preflight, and summary payloads are weak-agent startup contracts with size and shape budgets.",
        "expected_proof": [
            "focused tiny/default payload shape tests",
            "size-budget assertions when existing tests define one",
            "selector/full-surface assertion for any new diagnostic field",
        ],
    }
