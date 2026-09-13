"""Canonical source/derivation and real Rust tool journeys for the C53 interface."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

from agentic_workspace.config import workspace_pointer_block

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".agentic-workspace/skills/workspace-startup/SKILL.md"
spec = importlib.util.spec_from_file_location("agent_interface_generator", ROOT / "scripts/generate/generate_agent_interface.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def test_bootstrap_payload_and_registry_have_one_ordinary_procedure():
    assert generator.synchronize(check=True) == []
    pointer = workspace_pointer_block("different-host-tool")
    agents = (ROOT / "AGENTS.md").read_text()
    assert pointer in agents
    assert len(pointer.encode()) < 800
    assert "start --target" not in pointer and "invoke --" not in pointer
    assert "cargo build" not in pointer and "cargo build" in agents
    registry = json.loads((ROOT / ".agentic-workspace/skills/REGISTRY.json").read_text())
    assert [skill["id"] for skill in registry["skills"] if skill["visibility"] == "ordinary-default"] == ["workspace-startup"]
    assert "workspace-operating-loop" not in {skill["id"] for skill in registry["skills"]}
    assert MAIN in (ROOT / ".agentic-workspace/WORKFLOW.md").read_text()
    skill = (ROOT / MAIN).read_text()
    assert "remain **unknown**" in skill
    assert "Do not mutate managed owner state" in skill
    ledger = tomllib.loads((ROOT / ".agentic-workspace/OWNERSHIP.toml").read_text())
    assert ledger["workspace"]["main_skill_path"] == MAIN


def test_canonical_procedure_preserves_correction_retention_boundary():
    # This is a prose contract regression, not proof of a persistence owner.
    # The existing drift guard also requires these instructions in shipped bytes.
    skill = (ROOT / MAIN).read_text()
    section = skill.split("## Corrections and retention\n", 1)[1].split("\n## ", 1)[0]
    for obligation in (
        "explicit user or reviewer correction intended to change future behavior",
        "as reconciliation input",
        "current correction/instruction owner",
        "current scope and retention semantics",
        "Keep one-off requests non-retained",
        "verify its outcome before claiming the correction was retained",
        "surface the exact owner/path gap",
        "retention is not established",
        "Do not substitute an apology, chat promise, Memory note, invented persistence",
    ):
        assert obligation in section


def test_source_lifecycle_retires_only_exact_package_bytes(tmp_path):
    # Source maintenance lifecycle is tested here; it is not an installed Python host.
    from agentic_workspace import workspace_runtime_core as owner

    retired = owner._WORKSPACE_SURFACES_MANIFEST["retired_surface_files"][0]
    previous = subprocess.check_output(
        ["git", "show", "efc18f52719bb69f652ef4bf2fa2c4826f05619b:src/agentic_workspace/_payload/" + retired["path"]], cwd=ROOT
    )
    path = tmp_path / retired["path"]
    path.parent.mkdir(parents=True)
    path.write_bytes(previous)
    assert owner._retired_workspace_surface_actions(target_root=tmp_path, dry_run=True)[0]["kind"] == "would remove"
    assert path.exists()
    assert owner._retired_workspace_surface_actions(target_root=tmp_path, dry_run=False)[0]["kind"] == "removed"
    path.write_text("Repository-owned procedure edits")
    assert owner._retired_workspace_surface_actions(target_root=tmp_path, dry_run=False)[0]["kind"] == "manual review"
    assert path.read_text() == "Repository-owned procedure edits"
    path.write_bytes(b"\xff\xfe")
    assert owner._retired_workspace_surface_actions(target_root=tmp_path, dry_run=False)[0]["kind"] == "manual review"
    assert path.read_bytes() == b"\xff\xfe"
    owner._workspace_required_payload_actions(target_root=tmp_path, dry_run=False)
    assert (tmp_path / MAIN).read_text() == (ROOT / MAIN).read_text()
    ledger = tomllib.loads(owner._host_ownership_ledger_text())
    assert ledger["workspace"]["main_skill_path"] == MAIN


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_fresh_skill_consumer_queries_then_performs_bounded_write(tmp_path, shared_core_binary, native_cli, surface):
    (tmp_path / "AGENTS.md").write_text(workspace_pointer_block())
    main = tmp_path / MAIN
    main.parent.mkdir(parents=True)
    main.write_text((ROOT / MAIN).read_text())
    context = {"target": str(tmp_path), "task": "Configure this repository invocation"}
    first = consume(surface, shared_core_binary, native_cli, context)
    assert first["decision_packet"]["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace/local").exists()
    first = consume(
        surface, shared_core_binary, native_cli, {**context, "request": first["configuration_write"]["creation_discovery_request"]}
    )
    request = next(r for r in first["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "workspace.cli_invoke")
    request["arguments"]["value"] = "aw-native"
    context["request"] = request
    proposal = consume(surface, shared_core_binary, native_cli, {**context, "projection": "compact"})
    answered = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            **context,
            "projection": "carried",
            "reference": proposal["detail_refs"]["/decision_packet/decision_request"],
            "answer": "authorize-write",
        },
    )
    action = answered["view"]["decision_packet"]["primary_action"]
    result = consume(surface, shared_core_binary, native_cli, {"invocation": answered["carriage"], "reference": action["reference"]})
    assert result["effect_outcome"]["status"] == "committed"
    assert result["continuation"]["retry_effect"] is False
    assert (tmp_path / "AGENTS.md").read_text() == workspace_pointer_block()
    assert (tmp_path / MAIN).read_text() == (ROOT / MAIN).read_text()


@pytest.mark.parametrize("mirror", [False, True])
def test_source_lifecycle_converges_without_replacing_repo_instructions(tmp_path, capsys, shared_core_binary, monkeypatch, mirror):
    from tests.workspace_cli_support import cli

    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(shared_core_binary))
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    agents = tmp_path / "AGENTS.md"
    agents.write_text("Repository instruction: preserve this line.\n")
    for operation in ("init", "upgrade", "upgrade"):
        options = ["--mirror-payload"] if operation == "init" and mirror else []
        assert cli.main([operation, "--target", str(tmp_path), *options, "--format", "json"]) == 0
        capsys.readouterr()
        assert agents.read_text().startswith("Repository instruction: preserve this line.")
        assert agents.read_text().count(workspace_pointer_block()) == 1
        assert (tmp_path / MAIN).read_text() == (ROOT / MAIN).read_text()
        assert not (tmp_path / ".agentic-workspace/skills/workspace-operating-loop/SKILL.md").exists()
    assert cli.main(["uninstall", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert agents.read_text().strip() == "Repository instruction: preserve this line."
    assert not (tmp_path / MAIN).exists()


def test_generated_fresh_bootstrap_is_only_an_activation_pointer():
    from agentic_workspace import workspace_runtime_core as owner

    rendered = owner._workspace_agents_template(selected_modules=[], descriptors={})
    assert rendered.count(workspace_pointer_block()) == 1
    assert "start --target" not in rendered
    assert len(rendered.encode()) < 900


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_known_leaf_returns_current_procedure_and_shared_applicability(tmp_path, shared_core_binary, native_cli, surface):
    from jsonschema import Draft202012Validator

    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "inspect", "path": "inspect/SKILL.md", "semantic_routes": ["repository/inspect"]}]}))
    procedure = registry.parent / "inspect/SKILL.md"
    procedure.parent.mkdir()
    procedure.write_text("Inspect the relevant repository sources.")
    instruction = tmp_path / ".agentic-workspace/instructions/inspection.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\nroutes: [repository/inspect]\n---\nExplain the selected source.")
    memory = tmp_path / ".agentic-workspace/memory/repo"
    memory.mkdir(parents=True)
    (memory / "context.md").write_text("Historical observation; advisory only.")
    (memory / "manifest.toml").write_text(
        'version=1\n[notes.".agentic-workspace/memory/repo/context.md"]\n'
        'note_type="decision"\nauthority="canonical"\nsemantic_routes=["repository/inspect"]\n'
    )
    context = {"target": str(tmp_path), "task": "Discuss the words repository inspect"}

    def call(extra=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **(extra or {})})

    quiet = call()
    assert not quiet["instructions"]["sources"][0]["guidance"]
    assert not quiet["memory"]["selected_notes"]
    request = next(r for r in quiet["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
    request["arguments"] = {"posture": "selected", "routes": ["repository/inspect"]}
    selected = call({"request": request})
    fact = selected["decision_packet"]["semantic_task_routes"]
    schema = json.loads((ROOT / "src/agentic_workspace/contracts/schemas/semantic_task_routes.schema.json").read_text())
    validator = Draft202012Validator({**schema, "oneOf": [{"$ref": "#/$defs/resolved_task_fact"}]})
    validator.validate(fact)
    assert fact["status"] == "current"
    assert selected["instructions"]["sources"][0]["guidance"]
    assert len(selected["memory"]["selected_notes"]) == 1
    assert selected["memory"]["authority_effect"] == "advisory-only"
    assert not selected["decision_packet"]["ready_actions"]
    detail = selected["semantic_routes"]["discovery"]["detail"]
    source = detail["sources"][0]["procedure"]
    assert source["status"] == "available"
    assert "body" not in source
    assert call({"request": request})["decision_packet"]["semantic_task_routes"] == fact
    carried = call({"request": request, "projection": "carried"})
    assert carried["view"]["decision_packet"]["semantic_task_routes"] == fact
    assert carried["view"]["procedure_refs"] == detail["sources"]
    assert call({"request": request, "projection": "compact"})["procedure_refs"] == detail["sources"]
    reference = carried["view"]["detail_refs"]["/semantic_routes"]
    resumed = consume(surface, shared_core_binary, native_cli, {"request": carried["carriage"], "reference": reference})
    assert resumed["value"]["decision"]["semantic_task_routes"] == fact
    procedure.write_text("Changed procedure; read the new bytes.")
    fresh = call({"request": request})
    assert fresh["semantic_routes"]["discovery"]["detail"]["sources"][0]["procedure"] != source
    assert fresh["decision_packet"]["semantic_task_routes"] == fact
    with pytest.raises(AssertionError, match="operating reference stale"):
        consume(surface, shared_core_binary, native_cli, {"request": carried["carriage"], "reference": reference})
    for change in ("task", "registry"):
        if change == "registry":
            registry.write_text(registry.read_text() + "\n")
        stale = call({"request": request, **({"task": "Different work"} if change == "task" else {})})
        validator.validate(stale["decision_packet"]["semantic_task_routes"])
        assert stale["decision_packet"]["semantic_task_routes"]["status"] == "stale"
        assert not stale["instructions"]["sources"][0]["guidance"]
        assert not stale["memory"]["selected_notes"]
        assert "detail" not in stale["semantic_routes"]["discovery"]
    assert not (tmp_path / ".agentic-workspace/local").exists()
