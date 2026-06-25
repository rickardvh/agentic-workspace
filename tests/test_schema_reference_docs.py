from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_generator():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "generate" / "generate_schema_reference.py"
    spec = importlib.util.spec_from_file_location("generate_schema_reference", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_schema_reference_generator_renders_workspace_config_annotations() -> None:
    module = _load_generator()

    text = module.render_schema_reference(module.DEFAULT_SCHEMA)

    assert "Source schema: `src/agentic_workspace/contracts/schemas/workspace_config.schema.json`" in text
    assert "`modules.enabled`" in text
    assert '`["planning", "memory"]`' in text
    assert "`workspace.agent_instructions_file`" in text
    assert '`"CLAUDE.md"`' in text
    assert '`".cursor/rules/project.mdc"`' in text
    assert "x-agentic-workspace-effective-default-source" in text
    assert "`update.modules.memory.source_ref`" in text


def test_schema_reference_annotation_check_covers_workspace_config() -> None:
    module = _load_generator()

    assert module._annotation_errors(module.DEFAULT_SCHEMA) == []


def test_schema_reference_default_targets_cover_all_contract_schemas() -> None:
    module = _load_generator()
    schemas = sorted(path.relative_to(module.REPO_ROOT) for path in (module.REPO_ROOT / module.SCHEMA_ROOT).glob("*.schema.json"))

    assert sorted(target.schema_path for target in module.DEFAULT_TARGETS) == schemas


def test_schema_reference_generator_rewrites_crlf_only_output_to_lf(tmp_path: Path) -> None:
    module = _load_generator()
    schema = tmp_path / "schema.schema.json"
    output = tmp_path / "reference.md"
    schema.write_text(
        """
{
  "title": "Fixture Schema",
  "description": "Fixture schema for generated reference tests.",
  "type": "object",
  "x-agentic-workspace-doc-role": "fixture",
  "properties": {
    "name": {
      "type": "string",
      "description": "Human-readable name."
    }
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    target = module.ReferenceTarget(schema.relative_to(tmp_path), output.relative_to(tmp_path))
    rendered = module.render_schema_reference(target.schema_path, repo_root=tmp_path)
    output.write_bytes(rendered.replace("\n", "\r\n").encode("utf-8"))

    assert module.generate(targets=(target,), repo_root=tmp_path, check=True) == [target.output_path]
    assert module.generate(targets=(target,), repo_root=tmp_path, check=False) == []
    rewritten = output.read_bytes()
    assert b"\r\n" not in rewritten
    assert rewritten == rendered.encode("utf-8")


def test_schema_reference_generator_still_detects_semantic_staleness(tmp_path: Path) -> None:
    module = _load_generator()
    schema = tmp_path / "schema.schema.json"
    output = tmp_path / "reference.md"
    schema.write_text(
        """
{
  "title": "Fixture Schema",
  "description": "Fixture schema for generated reference tests.",
  "type": "object",
  "x-agentic-workspace-doc-role": "fixture",
  "properties": {
    "name": {
      "type": "string",
      "description": "Human-readable name."
    }
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    target = module.ReferenceTarget(schema.relative_to(tmp_path), output.relative_to(tmp_path))
    output.write_text("stale\n", encoding="utf-8")

    assert module.generate(targets=(target,), repo_root=tmp_path, check=True) == [target.output_path]


def test_schema_reference_scaffold_includes_required_doc_metadata(tmp_path: Path) -> None:
    module = _load_generator()
    schema_path = Path("src/agentic_workspace/contracts/schemas/example.schema.json")

    module.write_schema_scaffold(
        schema_path=schema_path,
        title="Example Schema",
        fields=[("name", "string"), ("count", "integer")],
        doc_role="fixture",
        repo_root=tmp_path,
    )

    schema = (tmp_path / schema_path).read_text(encoding="utf-8")
    assert '"x-agentic-workspace-doc-role": "fixture"' in schema
    assert "Describe the name field for generated schema reference docs." in schema
    assert module._annotation_errors(schema_path, repo_root=tmp_path) == []


def test_schema_reference_scaffold_refuses_existing_file_without_force(tmp_path: Path) -> None:
    module = _load_generator()
    schema_path = Path("src/agentic_workspace/contracts/schemas/example.schema.json")
    (tmp_path / schema_path).parent.mkdir(parents=True)
    (tmp_path / schema_path).write_text("{}\n", encoding="utf-8")

    try:
        module.write_schema_scaffold(
            schema_path=schema_path,
            title="Example Schema",
            fields=[],
            doc_role="fixture",
            repo_root=tmp_path,
        )
    except FileExistsError as exc:
        assert "pass --force" in str(exc)
    else:  # pragma: no cover - explicit failure branch for readability
        raise AssertionError("expected FileExistsError")


def test_schema_reference_curated_descriptions_cover_high_value_schemas() -> None:
    module = _load_generator()

    startup = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/startup_context.schema.json"))
    report = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/workspace_report.schema.json"))
    aid = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/agent_aid_manifest.schema.json"))

    assert "minimum safe context for entering or resuming work" in startup
    assert "Ordered surfaces and commands an agent should use" in startup
    assert "`context.pre_test_evidence_guardrail`" in startup
    assert "Selector-first location for the optional non-blocking pre-test evidence-owner advisory" in startup
    assert "Combined workspace report payload for installed modules" in report
    assert "Recommended next action derived from report health" in report
    assert "Manifest for a checked-in agent aid" in aid
    assert "Observed friction or repeated need that justified creating the aid" in aid
