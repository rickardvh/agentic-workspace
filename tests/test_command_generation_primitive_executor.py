from __future__ import annotations

import json
from pathlib import Path

import pytest

from command_generation.primitive_executor import (
    PrimitiveContext,
    PrimitiveExecutionError,
    execute_primitive,
    run_operation_steps,
)


@pytest.fixture()
def primitive_context(tmp_path: Path) -> PrimitiveContext:
    package_root = tmp_path / "package"
    package_root.mkdir()
    (package_root / "alpha.txt").write_text("alpha", encoding="utf-8")
    (package_root / "nested").mkdir()
    (package_root / "nested" / "beta.txt").write_text("beta", encoding="utf-8")
    (package_root / "REGISTRY.json").write_text(
        json.dumps({"skills": [{"id": "review", "path": "review/SKILL.md"}]}),
        encoding="utf-8",
    )
    (tmp_path / "target").mkdir()
    return PrimitiveContext(cwd=tmp_path, roots={"package": package_root})


def test_path_target_root_resolve_uses_context_cwd(primitive_context: PrimitiveContext) -> None:
    target_root = execute_primitive(
        "path.target_root.resolve",
        values={"target": "target"},
        context=primitive_context,
    )

    assert target_root == str((primitive_context.cwd / "target").resolve())


def test_filesystem_read_is_rooted(primitive_context: PrimitiveContext) -> None:
    assert (
        execute_primitive(
            "filesystem.read",
            values={},
            arguments={"root": "package", "path": "REGISTRY.json"},
            context=primitive_context,
        )
        == '{"skills": [{"id": "review", "path": "review/SKILL.md"}]}'
    )

    with pytest.raises(PrimitiveExecutionError, match="path escapes primitive root"):
        execute_primitive(
            "filesystem.read",
            values={},
            arguments={"root": "package", "path": "../escape.txt"},
            context=primitive_context,
        )


def test_filesystem_glob_returns_stable_relative_files(primitive_context: PrimitiveContext) -> None:
    files = execute_primitive(
        "filesystem.glob",
        values={},
        arguments={"root": "package", "pattern": "**/*.txt"},
        context=primitive_context,
    )

    assert files == [{"relative_path": "alpha.txt"}, {"relative_path": "nested/beta.txt"}]


def test_filesystem_primitives_can_use_value_roots(primitive_context: PrimitiveContext) -> None:
    target = primitive_context.cwd / "target"
    (target / "feedback.md").write_text("ok", encoding="utf-8")
    (target / "fixtures").mkdir()
    (target / "fixtures" / "case.json").write_text("{}", encoding="utf-8")

    values = {"target_root": str(target)}

    assert execute_primitive(
        "filesystem.exists",
        values=values,
        arguments={"base_value": "target_root", "path": "feedback.md", "kind": "file"},
        context=primitive_context,
    )
    assert execute_primitive(
        "filesystem.glob",
        values=values,
        arguments={"base_value": "target_root", "pattern": "fixtures/*.json"},
        context=primitive_context,
    ) == [{"relative_path": "fixtures/case.json"}]


def test_json_parse_uses_named_source_value(primitive_context: PrimitiveContext) -> None:
    registry = execute_primitive(
        "json.parse",
        values={"registry_text": '{"skills": [{"id": "review"}]}'},
        context=primitive_context,
    )

    assert registry == {"skills": [{"id": "review"}]}


def test_toml_table_counts_returns_stable_counts(primitive_context: PrimitiveContext) -> None:
    target = primitive_context.cwd / "target"
    manifest = target / ".agentic-workspace" / "memory" / "repo"
    manifest.mkdir(parents=True)
    (manifest / "manifest.toml").write_text(
        "\n".join(
            [
                "[notes.required]",
                'task_relevance = "required"',
                "[notes.optional]",
                'task_relevance = "optional"',
                "routing_only = true",
            ]
        ),
        encoding="utf-8",
    )

    result = execute_primitive(
        "toml.table.counts",
        values={"target_root": str(target)},
        arguments={
            "base_value": "target_root",
            "path": ".agentic-workspace/memory/repo/manifest.toml",
            "table": "notes",
            "relevance_field": "task_relevance",
            "required_value": "required",
            "optional_value": "optional",
            "routing_only_field": "routing_only",
        },
        context=primitive_context,
    )

    assert result == {
        "table_counts": {
            "status": "present",
            "note_count": 2,
            "required_count": 1,
            "optional_count": 1,
            "routing_only_count": 1,
            "path": ".agentic-workspace/memory/repo/manifest.toml",
        },
        "table_present": True,
        "table_status": "present",
    }


def test_toml_table_counts_reports_missing_file(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "toml.table.counts",
        values={"target_root": str(primitive_context.cwd / "target")},
        arguments={"base_value": "target_root", "path": "missing.toml", "table": "notes"},
        context=primitive_context,
    )

    assert result["table_counts"]["status"] == "missing"
    assert result["table_present"] is False
    assert result["table_status"] == "missing"


def test_payload_assemble_supports_file_and_skill_records(primitive_context: PrimitiveContext) -> None:
    file_payload = execute_primitive(
        "payload.assemble",
        values={
            "target_root": str((primitive_context.cwd / "target").resolve()),
            "files": [{"relative_path": "alpha.txt"}],
        },
        arguments={"fields": {"dry_run": True, "message": "Files", "actions_from": "files"}},
        context=primitive_context,
    )
    skill_payload = execute_primitive(
        "payload.assemble",
        values={"registry": {"skills": [{"id": "review", "path": "review/SKILL.md"}]}},
        arguments={"fields": {"dry_run": True, "message": "Skills", "actions_from": "registry.skills", "mode": "skills"}},
        context=primitive_context,
    )

    assert file_payload["actions"] == [{"kind": "file", "path": "alpha.txt"}]
    assert skill_payload["actions"] == [{"kind": "skill", "id": "review", "path": "review/SKILL.md"}]


def test_payload_assemble_supports_template_records(primitive_context: PrimitiveContext) -> None:
    payload = execute_primitive(
        "payload.assemble",
        values={
            "target_root": str((primitive_context.cwd / "target").resolve()),
            "feedback_exists": True,
            "fixture_files": [{"relative_path": "fixtures/case.json"}],
        },
        arguments={
            "fields": {
                "template": {
                    "target_root": {"$value": "target_root"},
                    "route_report_summary": {
                        "feedback": {
                            "status": {"$exists_status": {"value": "feedback_exists", "present": "present", "missing": "missing"}},
                            "path": {"$join_path": {"base": "target_root", "path": "feedback.md"}},
                        },
                        "fixtures": {
                            "status": {"$count_status": {"value": "fixture_files", "present": "present", "missing": "missing"}},
                            "fixture_count": {"$count": "fixture_files"},
                        },
                    },
                }
            }
        },
        context=primitive_context,
    )

    assert payload["route_report_summary"]["feedback"]["status"] == "present"
    assert payload["route_report_summary"]["fixtures"]["fixture_count"] == 1


def test_output_emit_supports_json_and_text(primitive_context: PrimitiveContext) -> None:
    payload = {
        "dry_run": True,
        "message": "Skills",
        "actions": [{"kind": "skill", "id": "review", "path": "review/SKILL.md"}],
    }

    emitted_json = execute_primitive("output.emit", values={"result": payload, "format": "json"}, context=primitive_context)
    emitted_text = execute_primitive("output.emit", values={"result": payload, "format": "text"}, context=primitive_context)

    assert json.loads(emitted_json)["actions"][0]["id"] == "review"
    assert emitted_text == "Skills\n- review/SKILL.md\n"


def test_python_function_call_resolves_checked_in_arguments(primitive_context: PrimitiveContext) -> None:
    result = execute_primitive(
        "python.function.call",
        values={"payload_text": '{"status": "ok"}'},
        arguments={
            "import_module": "json",
            "function": "loads",
            "kwargs": {
                "s": {"value": "payload_text"},
            },
        },
        context=primitive_context,
    )

    assert result == {"status": "ok"}


def test_python_function_call_rejects_unresolved_targets(primitive_context: PrimitiveContext) -> None:
    with pytest.raises(PrimitiveExecutionError, match="cannot resolve"):
        execute_primitive(
            "python.function.call",
            values={},
            arguments={"import_module": "json", "function": "missing_function", "kwargs": {}},
            context=primitive_context,
        )


def test_python_function_call_rejects_missing_value_bindings(primitive_context: PrimitiveContext) -> None:
    with pytest.raises(PrimitiveExecutionError, match="cannot resolve value"):
        execute_primitive(
            "python.function.call",
            values={},
            arguments={
                "import_module": "json",
                "function": "loads",
                "kwargs": {"s": {"value": "missing"}},
            },
            context=primitive_context,
        )


def test_run_operation_steps_executes_declared_dataflow(primitive_context: PrimitiveContext) -> None:
    operation = {
        "ir_plan": {
            "steps": [
                {
                    "id": "read_registry",
                    "uses": "filesystem.read",
                    "arguments": {"root": "package", "path": "REGISTRY.json"},
                    "outputs": ["registry_text"],
                },
                {"id": "parse_registry", "uses": "json.parse", "outputs": ["registry"]},
                {
                    "id": "assemble",
                    "uses": "payload.assemble",
                    "arguments": {"fields": {"dry_run": True, "message": "Skills", "actions_from": "registry.skills"}},
                    "outputs": ["result"],
                },
                {"id": "emit", "uses": "output.emit", "outputs": ["emitted"]},
            ]
        }
    }

    values = run_operation_steps(operation, initial_values={"format": "json"}, context=primitive_context)

    assert json.loads(values["emitted"])["actions"][0]["id"] == "review"


def test_run_operation_steps_honors_simple_when_conditions(primitive_context: PrimitiveContext) -> None:
    operation = {
        "ir_plan": {
            "steps": [
                {
                    "id": "skip_text",
                    "uses": "payload.assemble",
                    "when": {"value": "format", "equals": "text"},
                    "arguments": {"fields": {"dry_run": True, "message": "Text", "actions_from": "files"}},
                    "outputs": ["result"],
                },
                {
                    "id": "emit_json",
                    "uses": "payload.assemble",
                    "when": {"all": [{"value": "format", "equals": "json"}, {"not": {"value": "verbose", "equals": True}}]},
                    "arguments": {"fields": {"template": {"message": "JSON"}}},
                    "outputs": ["result"],
                },
            ]
        }
    }

    values = run_operation_steps(operation, initial_values={"format": "json", "verbose": False}, context=primitive_context)

    assert values["result"] == {"message": "JSON"}
