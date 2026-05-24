from __future__ import annotations

import sys
import types
from pathlib import Path

COMMAND_GENERATION_SRC = Path(__file__).resolve().parents[1] / "packages" / "command-generation" / "src"
if str(COMMAND_GENERATION_SRC) not in sys.path:
    sys.path.insert(0, str(COMMAND_GENERATION_SRC))

GENERATOR_SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "generate"
if str(GENERATOR_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(GENERATOR_SCRIPT_ROOT))

from workspace_command_generation import load_workspace_command_package_ir  # noqa: E402

from command_generation import canonical_command_artifacts, generator  # noqa: E402


def test_canonical_command_artifacts_expose_implementation_independent_truth() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    artifacts = canonical_command_artifacts(load_workspace_command_package_ir(repo_root=repo_root))
    by_key = {(artifact.package_id, artifact.command_name): artifact for artifact in artifacts}

    defaults = by_key[("root-workspace", "defaults")]
    planning_status = by_key[("planning-bootstrap", "status")]
    memory_skills = by_key[("memory-bootstrap", "list-skills")]

    assert defaults.program == "agentic-workspace"
    assert defaults.adapter_id == "defaults.report.cli"
    assert defaults.operation_ref["id"] == "defaults.report"
    assert defaults.runtime_binding["primitive_refs"] == [
        "workspace.defaults.load",
        "workspace.defaults.select",
        "output.emit",
    ]
    assert defaults.conformance_refs == ("defaults.report.process",)
    assert "command identity" in defaults.projection_boundary["universal"]
    assert "parser library" in defaults.projection_boundary["target_specific"]
    assert "defaults payload assembly" in defaults.projection_boundary["runtime_owned"]
    assert planning_status.conformance_refs == ("planning.status.process",)
    assert memory_skills.conformance_refs == ("memory.list-skills.process",)


def test_canonical_command_artifacts_exclude_target_specific_package_fields() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    artifact = next(
        artifact
        for artifact in canonical_command_artifacts(load_workspace_command_package_ir(repo_root=repo_root))
        if artifact.package_id == "root-workspace" and artifact.command_name == "defaults"
    )

    artifact_fields = set(artifact.__dataclass_fields__)
    assert "generated_root" not in artifact_fields
    assert "package_name" not in artifact_fields
    assert "entrypoints" not in artifact_fields
    assert "test_environment" not in artifact_fields
    assert "kind" not in artifact_fields
    rendered = repr(artifact)
    assert "spawnSync" not in rendered
    assert "argparse" not in rendered
    assert "Dockerfile" not in rendered


def test_command_generation_package_does_not_hardcode_host_runtime_modules() -> None:
    package_root = Path(__file__).resolve().parents[1] / "packages" / "command-generation"
    target_specific_runtime = ("_generated_cli_package.py", "_operation_ir_executor.py", "_runtime_cli.py")
    assert not [
        path.relative_to(package_root).as_posix()
        for path in (package_root / "src").rglob("*.py")
        if path.name.endswith(target_specific_runtime)
    ]
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in (package_root / "src").rglob("*.py") if not path.name.endswith(target_specific_runtime)
    )

    assert "agentic_workspace" not in text
    assert "repo_planning_bootstrap" not in text
    assert "repo_memory_bootstrap" not in text


def test_generated_local_runtime_facade_documents_and_preserves_patch_semantics() -> None:
    source_module = types.ModuleType("fake_source_runtime_for_facade")

    def first_value() -> str:
        return "first"

    source_module.runtime_value = first_value
    sys.modules[source_module.__name__] = source_module
    try:
        rendered = generator._python_local_runtime_binding_module(
            {
                "program": "demo-cli",
                "python_runtime_binding": {
                    "operation_executor": {
                        "handlers": [
                            {
                                "primitive": "demo.value",
                                "handler": "function_call",
                                "import_module": source_module.__name__,
                                "function": "runtime_value",
                            }
                        ]
                    }
                },
            },
            {
                "source_import_module": source_module.__name__,
                "module_file": "primitives.demo_runtime",
            },
            source_path="demo_ir.json",
            regenerate_command="generate-demo",
        )
        assert "live source-module lookup at call time" in rendered
        assert "not forwarded back into source modules" in rendered
        facade_globals: dict[str, object] = {}
        exec(rendered, facade_globals)

        assert facade_globals["runtime_value"]() == "first"

        def second_value() -> str:
            return "second"

        source_module.runtime_value = second_value
        assert facade_globals["runtime_value"]() == "second"

        facade_globals["runtime_value"] = lambda: "facade-only"
        assert source_module.runtime_value() == "second"
        assert facade_globals["runtime_value"]() == "facade-only"
    finally:
        sys.modules.pop(source_module.__name__, None)
