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
    assert "`workspace.default_preset`" in text
    assert '`"full"`' in text
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


def test_schema_reference_curated_descriptions_cover_high_value_schemas() -> None:
    module = _load_generator()

    startup = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/startup_context.schema.json"))
    report = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/workspace_report.schema.json"))
    aid = module.render_schema_reference(Path("src/agentic_workspace/contracts/schemas/agent_aid_manifest.schema.json"))

    assert "minimum safe context for entering or resuming work" in startup
    assert "Ordered surfaces and commands an agent should use" in startup
    assert "Combined workspace report payload for installed modules" in report
    assert "Recommended next action derived from report health" in report
    assert "Manifest for a checked-in agent aid" in aid
    assert "Observed friction or repeated need that justified creating the aid" in aid
