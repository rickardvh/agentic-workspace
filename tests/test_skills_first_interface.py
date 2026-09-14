"""Canonical source/derivation and real Rust tool journeys for the C53 interface."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

from agentic_workspace.config import workspace_pointer_block
from agentic_workspace.static_read_profile import LEDGER, PROFILE, render

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".agentic-workspace/skills/workspace-startup/SKILL.md"
spec = importlib.util.spec_from_file_location("agent_interface_generator", ROOT / "scripts/generate/generate_agent_interface.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def assert_current_command_examples(text: str) -> None:
    # Check copyable command recipes against the same declaration the native
    # executable consumes, rather than maintaining a second list of commands.
    declaration = json.loads((ROOT / "src/agentic_workspace/contracts/source_decision_contract.json").read_text())["native_cli"]
    commands = {item["name"] for item in declaration["commands"]}
    examples = set(re.findall(r"\bagentic-workspace\s+([a-z][a-z-]*)(?=\s+--)", text))
    assert not examples - commands, f"Non-current native command examples: {sorted(examples - commands)}"


def test_active_bootstrap_and_config_command_examples_match_native_surface():
    surfaces = ["AGENTS.md", MAIN, ".agentic-workspace/WORKFLOW.md", ".agentic-workspace/config.toml", "docs/agentic-workspace-install.md"]
    surfaces += json.loads((ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())["payload_files"]
    for module in ("memory", "planning"):
        surfaces += [path.relative_to(ROOT).as_posix() for path in (ROOT / f"packages/{module}/bootstrap").rglob("*.md")]
    for reference in surfaces:
        assert_current_command_examples((ROOT / reference).read_text(encoding="utf-8").replace("<effective-cli>", "agentic-workspace"))
    # Same guard rejects the durable drift class, including a removed command
    # that is not a known historical alias.
    with pytest.raises(AssertionError, match="Non-current native command"):
        assert_current_command_examples("agentic-workspace unavailable-operation --target .")


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
    with pytest.raises(ValueError, match="Unsupported ownership ledger"):
        render("schema_version=2\n")
    with pytest.raises(tomllib.TOMLDecodeError):
        render("[malformed")


def test_tree_only_reader_follows_selected_owner_refs_and_blob_currentness():
    """Consumer access is fetch/list only; no AW, shell, or renderer is called.

    Selection here is explicit example agent judgment, not a product classifier.
    The harness supplies Git blob identities as a repository API would.
    """

    def blob(content):
        raw = content.encode()
        return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

    files = {ref: (ROOT / ref).read_text() for ref in ["AGENTS.md", MAIN, LEDGER, PROFILE]}
    plan = ".agentic-workspace/planning/execplans/selected.plan.json"
    manifest = ".agentic-workspace/memory/repo/manifest.toml"
    note = ".agentic-workspace/memory/repo/domains/relevant.md"
    instruction = ".agentic-workspace/instructions/selected.md"
    proof = ".agentic-workspace/verification/manifest.toml"
    files.update(
        {
            ".agentic-workspace/planning/state.toml": f'[[active.execplans]]\nid="selected"\nsurface="{plan}"\n',
            plan: json.dumps(
                {
                    "kind": "planning-execplan/v1",
                    "intent": {"outcome": "Preserve the API", "non_goals": ["No release"]},
                    "scope": {"owned": ["src/api.rs"]},
                    "proof": {"refs": [proof]},
                    "blockers": [],
                    "next_action": "Check the changed response",
                    "continuation": {"residual_intent": "Independent acceptance remains"},
                }
            ),
            manifest: f'version=1\n[notes."{note}"]\nroutes_from=["src/api.rs"]\nnote_type="domain"\n[notes."{note}".dependencies]\n"src/api.rs"="recorded earlier source"\n',
            note: "Advisory: consumers rely on the existing response shape.",
            instruction: "---\npaths: [src/api.rs]\nprotect: [review]\n---\nPreserve response compatibility.",
            proof: "version=1\n# Independent review remains required; no fresh receipt is present.\n",
            "src/api.rs": "current API source",
            ".agentic-workspace/planning/execplans/archive/unrelated.plan.json": "Unrelated history",
            ".agentic-workspace/memory/repo/domains/unrelated.md": "Unrelated lesson",
        }
    )
    fetched = {}

    def fetch(ref):
        content = files[ref]
        fetched[ref] = blob(content)
        return content

    assert MAIN in fetch("AGENTS.md")
    assert PROFILE in fetch(MAIN)
    profile = json.loads(fetch(PROFILE))
    assert profile["kind"] == "agentic-workspace/repository-read-profile/v1"
    assert profile["source"]["git_blob_sha1"] == blob(fetch(profile["source"]["path"]))
    entries = {entry["concern"]: entry for entry in profile["entries"]}
    # Planning/shaping: choose the intended owner, not an inferred local selector.
    state = tomllib.loads(fetch(entries["bounded-planning-continuity"]["refs"][0]))
    selected = json.loads(fetch(state["active"]["execplans"][0]["surface"]))
    assert selected["intent"] == {"outcome": "Preserve the API", "non_goals": ["No release"]}
    assert selected["continuation"]["residual_intent"] == "Independent acceptance remains"
    assert "local selected owner" in entries["bounded-planning-continuity"]["unknown"]
    # Review: metadata and the explicit task scope identify just these sources.
    assert instruction.startswith(entries["startup-instructions"]["refs"][1])
    assert "protect: [review]" in fetch(instruction)
    assert fetch(entries["verification-manifest"]["refs"][0]) == files[proof]
    notes = tomllib.loads(fetch(entries["memory-shared-support"]["refs"][0]))["notes"]
    assert notes[note]["routes_from"] == ["src/api.rs"]
    assert fetch(note).startswith("Advisory:")
    for ref in notes[note]["dependencies"]:
        fetch(ref)
    assert "factual freshness" in entries["memory-shared-support"]["unknown"]
    assert not any("unrelated" in ref or "/local/" in ref for ref in fetched)
    # The read set carries exact repository facts, not an active decision.
    files["unrelated.txt"] = "An unrelated repository change"
    assert all(blob(files[ref]) == revision for ref, revision in fetched.items())
    files["src/api.rs"] += " changed"
    assert [ref for ref, revision in fetched.items() if blob(files[ref]) != revision] == ["src/api.rs"]
    files[LEDGER] += "\n# Changed owner descriptor\n"
    assert profile["source"]["git_blob_sha1"] != blob(files[LEDGER])
    assert "stale" in profile["recovery"] and "Do not guess" in profile["recovery"]
    assert "no mutation" in profile["authority"] and "issue-close" in profile["authority"]


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
    installed = json.loads((tmp_path / PROFILE).read_text())
    assert installed == json.loads(render((tmp_path / LEDGER).read_text()))
    assert len((tmp_path / PROFILE).read_bytes()) < 8_000


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
    # Static profile damage cannot become an executable semantic dependency.
    (tmp_path / PROFILE).write_text('{"kind":"unsupported-profile/v2"}')
    assert consume(surface, shared_core_binary, native_cli, context)["decision_packet"] == first["decision_packet"]
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
    retained = {}
    for reference in (
        ".agentic-workspace/memory/repo/retained.md",
        ".agentic-workspace/planning/retained.md",
        ".agentic-workspace/local/instructions/retained.md",
    ):
        path = tmp_path / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Current owner state; preserve this meaning.\n")
        retained[reference] = path.read_bytes()
    for operation in ("init", "upgrade", "upgrade"):
        options = ["--mirror-payload"] if operation == "init" and mirror else []
        assert cli.main([operation, "--target", str(tmp_path), *options, "--format", "json"]) == 0
        capsys.readouterr()
        assert agents.read_text().startswith("Repository instruction: preserve this line.")
        assert agents.read_text().count(workspace_pointer_block()) == 1
        assert (tmp_path / MAIN).read_text() == (ROOT / MAIN).read_text()
        assert not (tmp_path / ".agentic-workspace/skills/workspace-operating-loop/SKILL.md").exists()
        for reference in ("AGENTS.md", MAIN, ".agentic-workspace/config.toml"):
            assert_current_command_examples((tmp_path / reference).read_text())
    assert cli.main(["uninstall", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()
    assert agents.read_text().strip() == "Repository instruction: preserve this line."
    assert not (tmp_path / MAIN).exists()
    for reference, original in retained.items():
        assert (tmp_path / reference).read_bytes() == original


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


@pytest.mark.parametrize("module", ["memory", "planning"])
def test_shipped_package_lifecycle_preserves_domain_state_and_current_guidance(tmp_path, monkeypatch, module):
    import importlib

    owner = importlib.import_module(f"repo_{module}_bootstrap.installer")
    ownership = importlib.import_module(f"repo_{module}_bootstrap._ownership")
    monkeypatch.setattr(ownership, "_workspace_manifest_path", lambda: None)
    ownership._ownership_data.cache_clear()
    try:
        ledger = ownership._ownership_data()
        for row in ledger["module_roots"]:
            if row["module"] in {"memory", "planning"}:
                assert row["ownership"] == "repo_owned"
                assert row["uninstall_policy"] == "preserve-current-owner-state"
        template = (ROOT / f"packages/{module}/bootstrap/AGENTS.template.md").read_text(encoding="utf-8")
        assert_current_command_examples(template.replace("<effective-cli>", "agentic-workspace"))
        assert "skills/workspace-startup/SKILL.md" in template
        assert "repository-owned and must be preserved" in template
        if module == "planning":
            projected = owner._ownership_review(tmp_path)
            assert ".agentic-workspace/planning/" not in projected["package_owned_roots"]
            assert ".agentic-workspace/memory/" not in projected["package_owned_roots"]
        else:
            shared = importlib.import_module("repo_memory_bootstrap._installer_shared")
            assert_current_command_examples(shared.WORKSPACE_POINTER_BLOCK)
        (tmp_path / ".git").mkdir()
        retained = {}
        for reference in (
            "AGENTS.md",
            ".agentic-workspace/memory/repo/retained.md",
            ".agentic-workspace/planning/retained.md",
            ".agentic-workspace/local/instructions/retained.md",
        ):
            path = tmp_path / reference
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Repository-owned meaning must survive.\n", encoding="utf-8", newline="\n")
            retained[reference] = path.read_bytes()
        for operation in (owner.install_bootstrap, owner.upgrade_bootstrap, owner.upgrade_bootstrap):
            operation(target=tmp_path)
            agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
            assert_current_command_examples(agents.replace("<effective-cli>", "agentic-workspace"))
            assert agents.startswith(retained["AGENTS.md"].decode())
        owner.uninstall_bootstrap(target=tmp_path)
        for reference, expected in retained.items():
            assert (tmp_path / reference).read_bytes() == expected
    finally:
        ownership._ownership_data.cache_clear()
