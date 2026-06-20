from __future__ import annotations

from pathlib import Path

import pytest
from command_generation.primitive_executor import PrimitiveContext, run_operation_steps


@pytest.fixture()
def primitive_context(tmp_path: Path) -> PrimitiveContext:
    package_root = tmp_path / "package"
    package_root.mkdir()
    (tmp_path / "target").mkdir()
    return PrimitiveContext(cwd=tmp_path, roots={"package": package_root})


def test_operation_fragments_execute_through_pinned_command_generation_dependency(primitive_context: PrimitiveContext) -> None:
    operation = {
        "ir_plan": {
            "fragments": [
                {
                    "id": "assemble-and-emit",
                    "description": "Reusable output fragment.",
                    "steps": [
                        {
                            "id": "assemble",
                            "description": "Build payload.",
                            "uses": "payload.assemble",
                            "arguments": {"fields": {"template": {"message": {"$value": "message"}}}},
                            "outputs": ["result"],
                        },
                        {
                            "id": "emit",
                            "description": "Emit payload.",
                            "uses": "output.emit",
                            "outputs": ["rendered"],
                        },
                    ],
                }
            ],
            "steps": [
                {
                    "id": "call-fragment",
                    "description": "Use the reusable fragment.",
                    "uses_fragment": "assemble-and-emit",
                }
            ],
        }
    }

    result = run_operation_steps(operation, initial_values={"message": "fragment output", "format": "text"}, context=primitive_context)

    assert result["result"] == {"message": "fragment output"}
    assert result["rendered"] == "fragment output\n"


def test_run_operation_steps_accepts_aw_host_domain_primitive_handlers(primitive_context: PrimitiveContext) -> None:
    def handle_promotion_report(values: dict[str, object], _arguments: dict[str, object], _context: PrimitiveContext) -> dict[str, object]:
        return {
            "kind": "memory-promotion-report/test",
            "kwargs": {"target": values["target"], "notes": values["notes"], "mode": values["mode"]},
        }

    operation = {
        "ir_plan": {
            "steps": [
                {
                    "id": "load_report",
                    "uses": "memory.promotion_report.load",
                    "outputs": ["result"],
                }
            ]
        }
    }

    values = run_operation_steps(
        operation,
        initial_values={"target": "repo", "notes": ["note.md"], "mode": "remediation"},
        context=primitive_context,
        handlers={"memory.promotion_report.load": handle_promotion_report},
    )

    assert values["result"] == {
        "kind": "memory-promotion-report/test",
        "kwargs": {"target": "repo", "notes": ["note.md"], "mode": "remediation"},
    }
