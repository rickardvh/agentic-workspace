from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from command_generation.primitive_executor import PrimitiveContext, run_operation_steps

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _config_report_text_views() -> list[dict[str, object]]:
    operation = json.loads((REPO_ROOT / "generated/workspace/python/operations/config.report.json").read_text(encoding="utf-8"))
    fragment = operation["ir_plan"]["fragments"][0]
    emit_step = fragment["steps"][1]
    return emit_step["arguments"]["text_views"]


def _run_python_config_view_text(payload: dict[str, object], text_views: list[dict[str, object]]) -> str:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from generated.workspace.python.primitives.primitive_executor import _emit_output

        return _emit_output(values={"format": "text", "result": payload}, arguments={"text_views": text_views})
    finally:
        sys.path.remove(str(REPO_ROOT))


def _run_typescript_config_view_text(tmp_path: Path, payload: dict[str, object], text_views: list[dict[str, object]]) -> str:
    if shutil.which("node") is None:
        pytest.skip("node is required for generated TypeScript config view conformance")
    runtime_dir = tmp_path / "generated-runtime"
    runtime_dir.mkdir(exist_ok=True)
    runtime_source = (REPO_ROOT / "generated/workspace/typescript/src/runtime.mjs").read_text(encoding="utf-8")
    (runtime_dir / "runtime.mjs").write_text(runtime_source + "\nexport { emitOutput };\n", encoding="utf-8")
    (runtime_dir / "hostPrimitiveSupport.mjs").write_text(
        "export function executeHostPrimitive() { throw new Error('not used by text view conformance'); }\n",
        encoding="utf-8",
    )
    script = (
        "import { emitOutput } from './runtime.mjs';\n"
        f"const result = {json.dumps(payload)};\n"
        f"const text_views = {json.dumps(text_views)};\n"
        "process.stdout.write(JSON.stringify(emitOutput({ format: 'text', result }, { text_views })));\n"
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=runtime_dir,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_generated_config_text_views_match_across_python_and_typescript(tmp_path: Path) -> None:
    text_views = _config_report_text_views()
    selected_payload = {
        "kind": "agentic-workspace/selected-output/v1",
        "source_command": "config",
        "values": {"workspace.enabled_modules": []},
        "missing": ["missing.path"],
    }
    py_selected = _run_python_config_view_text(selected_payload, text_views)
    ts_selected = _run_typescript_config_view_text(tmp_path, selected_payload, text_views)
    assert py_selected == ts_selected
    assert "Missing:\n- missing.path\n" in py_selected
    assert "- {}\n" not in py_selected

    selected_without_missing = {**selected_payload, "missing": []}
    py_selected_without_missing = _run_python_config_view_text(selected_without_missing, text_views)
    ts_selected_without_missing = _run_typescript_config_view_text(tmp_path, selected_without_missing, text_views)
    assert py_selected_without_missing == ts_selected_without_missing
    assert "Missing:" not in py_selected_without_missing

    full_payload = {
        "target": "repo",
        "config_path": ".agentic-workspace/config.toml",
        "exists": True,
        "workspace": {
            "enabled": True,
            "enabled_source": "repo-config",
            "enabled_modules": [],
            "agent_instructions_file": "AGENTS.md",
            "agent_instructions_file_source": "default",
            "workflow_artifact_profile": "repo-owned",
            "workflow_artifact_profile_source": "default",
            "agent_configuration_substrate": {"canonical_doc": "AGENTS.md", "owner_surface": "repo"},
            "system_intent": {"sources": [], "sources_source": "default"},
            "workflow_obligations": [],
            "improvement_latitude": "proactive",
            "improvement_latitude_source": "default",
            "optimization_bias": "agent-efficiency",
            "optimization_bias_source": "default",
            "advanced_features": [],
            "advanced_features_source": "default",
            "cli_invoke": "uv run agentic-workspace",
            "cli_invoke_source": "default",
        },
        "local_runtime": {
            "delegation_mode": {"value": "auto"},
            "safe_to_auto_run_commands": {"value": True},
        },
        "next_detail": {"select": "agentic-workspace config --select <field>", "verbose": "agentic-workspace config --verbose"},
        "full_profile_command": "agentic-workspace config --verbose",
        "edit_reference": {
            "reference_doc": ".agentic-workspace/docs/workspace-config-contract.md",
            "source_schema": "src/agentic_workspace/contracts/schemas/workspace_config.schema.json",
            "check_command": "agentic-workspace config --format json",
        },
        "update": {"wrapper_rule": "normal update execution stays behind agentic-workspace", "modules": []},
        "mixed_agent": {
            "rule": "repo policy wins",
            "repo_policy": {"path": ".agentic-workspace/config.toml", "source": "repo"},
            "local_override": {"path": ".agentic-workspace/config.local.toml", "status": "absent"},
            "local_integration_area": {"root": ".agentic-workspace/local", "status": "available"},
            "effective_posture": {
                "supports_internal_delegation": {"value": True},
                "strong_planner_available": {"value": True},
                "cheap_bounded_executor_available": {"value": True},
            },
            "delegation_targets": {
                "profiles": [],
                "outcome_artifact": {"path": ".agentic-workspace/local/outcomes.json", "status": "absent"},
            },
        },
        "warnings": [],
    }
    py_clean_full = _run_python_config_view_text(full_payload, text_views)
    ts_clean_full = _run_typescript_config_view_text(tmp_path, full_payload, text_views)
    assert py_clean_full == ts_clean_full
    assert "Warnings:" not in py_clean_full
    assert "Enabled modules: (none)\n" in py_clean_full

    warning_payload = {
        **full_payload,
        "warnings": [
            ".agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level.",
            ".agentic-workspace/config.toml [workspace] contains unsupported field(s): unsupported_workspace_field.",
        ],
    }
    py_warning_full = _run_python_config_view_text(warning_payload, text_views)
    ts_warning_full = _run_typescript_config_view_text(tmp_path, warning_payload, text_views)
    assert py_warning_full == ts_warning_full
    assert "Warnings:\n" in py_warning_full
    assert "- .agentic-workspace/config.toml contains unsupported top-level field(s): unsupported_top_level.\n" in py_warning_full
    assert "- .agentic-workspace/config.toml [workspace] contains unsupported field(s): unsupported_workspace_field.\n" in py_warning_full
    assert "- {}\n" not in py_warning_full
