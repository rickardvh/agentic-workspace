"""Canonical source/derivation and real Rust tool journeys for the C53 interface."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

from aw_maintainer.ownership_profile import LEDGER, PROFILE, render

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".agentic-workspace/skills/workspace-startup/SKILL.md"
STARTUP_POINTER = "<!-- agentic-workspace:workflow:start -->\nUse `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure; if native skill discovery is unavailable, read it directly.\n<!-- agentic-workspace:workflow:end -->"
spec = importlib.util.spec_from_file_location("agent_interface_generator", ROOT / "src/tooling/generate/generate_agent_interface.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def assert_current_command_examples(text: str) -> None:
    # Check copyable command recipes against the same declaration the native
    # executable consumes, rather than maintaining a second list of commands.
    declaration = json.loads((ROOT / "src/core/contracts/source_decision_contract.json").read_text())["native_cli"]
    commands = {item["name"] for item in declaration["commands"]}
    examples = set(re.findall(r"\bagentic-workspace\s+([a-z][a-z-]*)(?=\s+--)", text))
    assert not examples - commands, f"Non-current native command examples: {sorted(examples - commands)}"


def test_active_bootstrap_and_config_command_examples_match_native_surface():
    surfaces = ["AGENTS.md", MAIN, ".agentic-workspace/WORKFLOW.md", ".agentic-workspace/config.toml", "docs/agentic-workspace-install.md"]
    surfaces += json.loads((ROOT / "src/core/contracts/workspace_surfaces.json").read_text())["payload_files"]
    for reference in surfaces:
        assert_current_command_examples((ROOT / reference).read_text(encoding="utf-8").replace("<effective-cli>", "agentic-workspace"))
    # Same guard rejects the durable drift class, including a removed command
    # that is not a known historical alias.
    with pytest.raises(AssertionError, match="Non-current native command"):
        assert_current_command_examples("agentic-workspace unavailable-operation --target .")


def test_bootstrap_payload_and_registry_have_one_ordinary_procedure():
    assert generator.synchronize(check=True) == []
    portable = (ROOT / "src/core/contracts/portable_ownership.toml").read_text()
    shipped = (ROOT / "src/core/payload" / LEDGER).read_text()
    assert shipped == portable and shipped != (ROOT / LEDGER).read_text()
    assert (ROOT / "src/core/payload" / PROFILE).read_text() == render(portable, target=ROOT)
    pointer = STARTUP_POINTER
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
    assert len(skill.encode()) < 2048
    assert "remain **unknown**" in skill
    assert "Do not mutate managed owner state" in skill
    ledger = tomllib.loads((ROOT / ".agentic-workspace/OWNERSHIP.toml").read_text())
    assert ledger["workspace"]["main_skill_path"] == MAIN
    with pytest.raises(ValueError):
        render("schema_version=2\n", target=ROOT)
    with pytest.raises(ValueError):
        render("[malformed", target=ROOT)


def test_read_profile_uses_target_git_identity(tmp_path, shared_core_binary, native_cli):
    ledger = "schema_version = 1\n# Identity source\n"
    # A plain directory cannot supply repository/path semantics.
    with pytest.raises(ValueError, match="Git repository identity unavailable"):
        render(ledger, target=tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=tmp_path, check=True)
    attributes = tmp_path / ".gitattributes"
    for policy, equivalent in (("text eol=lf", True), ("-text", False), ("-filter text eol=lf", True)):
        attributes.write_text(f"{LEDGER} {policy}\n", encoding="utf-8", newline="\n")
        identities = []
        for text in (ledger, ledger.replace("\n", "\r\n"), ledger + "# Meaningful change\n"):
            profile = json.loads(render(text, target=tmp_path))
            expected = (
                subprocess.check_output(["git", "hash-object", "--stdin", f"--path={LEDGER}"], cwd=tmp_path, input=text.encode())
                .decode()
                .strip()
            )
            assert profile["source"]["git_blob_sha1"] == expected
            identities.append(expected)
        assert (identities[0] == identities[1]) is equivalent
        assert identities[2] not in identities[:2]
    # Neither optional clean commands nor required process filters may run from
    # the build binding or the public adoption read/proposal, before authorization.
    attributes.write_text(f"{LEDGER} filter=identity-test text eol=lf\n", encoding="utf-8", newline="\n")
    sentinel = tmp_path / "filter-sentinel"
    context = {"target": str(tmp_path), "task": "Observe repository adoption"}
    for driver, required in (("clean", "false"), ("process", "true")):
        subprocess.run(["git", "config", f"filter.identity-test.{driver}", "echo invoked > filter-sentinel"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "filter.identity-test.required", required], cwd=tmp_path, check=True)
        with pytest.raises(ValueError, match="cannot execute a selected filter"):
            render(ledger, target=tmp_path)
        current = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
        request = current["configuration_write"]["repository_adoption_request"]
        with pytest.raises(AssertionError, match="cannot execute a selected filter"):
            consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])
        assert not sentinel.exists()
        assert not (tmp_path / PROFILE).exists()
    # Git's printable attribute states can also be literal driver names.
    for driver_name in ("unset", "unspecified"):
        attributes.write_text(f"{LEDGER} filter={driver_name}\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "config", f"filter.{driver_name}.clean", "echo invoked > filter-sentinel"], cwd=tmp_path, check=True)
        with pytest.raises(ValueError, match="cannot execute a selected filter"):
            render(ledger, target=tmp_path)
        assert not sentinel.exists()


def test_portable_derivation_is_isolated_from_source_policy(tmp_path):
    """Producer-only mutation cannot influence a closed portable derivation graph."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    contract_path = "src/core/contracts/workspace_surfaces.json"
    contract = json.loads((ROOT / contract_path).read_text())
    for reference in [contract_path, *contract["derivation"]["portable_sources"], LEDGER, PROFILE]:
        destination = tmp_path / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / reference).read_bytes())
    baseline = generator.render_host_payload(tmp_path)
    poison = 'schema_version=1\n[[subsystems]]\nid="producer-poison"\npaths=["maintainer/poison/**"]\nproof=["poison-maintainer-check"]\n'
    poison += (
        '[[authority_surfaces]]\nconcern="poison-authority"\nowner="producer"\n'
        'surface="maintainer/poison.md"\nownership="repo_owned"\nauthority="primary"\n'
        'read={refs=["maintainer/poison.md"],select="poison",unknown=[]}\n'
    )
    (tmp_path / LEDGER).write_text(poison)
    (tmp_path / PROFILE).write_text(render(poison, target=tmp_path))
    assert generator.render_host_payload(tmp_path) == baseline
    portable_ref = next(row["materialization"]["source"] for row in contract["surfaces"] if row["path"] == LEDGER)
    portable = tmp_path / portable_ref
    portable.write_text(portable.read_text().replace("Repository-native state", "Portable-input mutation: repository-native state"))
    changed = generator.render_host_payload(tmp_path)
    assert {key for key in baseline if baseline[key] != changed[key]} == {LEDGER, PROFILE}
    # An attempted undeclared dependency, implicit relabelling, or copy mode for
    # a composite surface fails before the source-only bytes can be consumed.
    for defect in ["source-only-edge", "implicit-promotion", "copy-composite", "missing-mode"]:
        bad = copy.deepcopy(contract)
        row = next(row["materialization"] for row in bad["surfaces"] if row["path"] == LEDGER)
        if defect in {"source-only-edge", "implicit-promotion"}:
            row["source"] = LEDGER
            if defect == "implicit-promotion":
                bad["derivation"]["portable_sources"].append(LEDGER)
        elif defect == "copy-composite":
            row.clear()
            row.update(mode="package-verbatim", source=portable_ref)
        else:
            row.pop("mode")
        (tmp_path / contract_path).write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="portable|materialization"):
            generator.render_host_payload(tmp_path)


def test_interface_generation_preserves_lifecycle_provenance(tmp_path, monkeypatch):
    """Projection writes cannot silently repair another owner's source record."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    host_ref = "src/core/contracts/workspace_surfaces.json"
    maintenance_ref = "src/tooling/contracts/source_maintenance_surfaces.json"
    host = json.loads((ROOT / host_ref).read_text())
    maintenance = json.loads((ROOT / maintenance_ref).read_text())
    references = {
        host_ref,
        maintenance_ref,
        LEDGER,
        PROFILE,
        *host["derivation"]["portable_sources"],
        *maintenance["payload_files"],
    }
    for reference in references:
        destination = tmp_path / reference
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / reference).read_bytes())
    provenance = tmp_path / ".agentic-workspace/payload-provenance.json"
    # Deliberately not the public-host list: generation must leave even stale
    # lifecycle material untouched, not silently normalize selected fields.
    original = b'{"payload_files": ["old"], "release_identity": {"version": "custom"}}\n'
    provenance.write_bytes(original)
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    assert generator.synchronize()
    assert generator.synchronize(check=True) == []
    assert provenance.read_bytes() == original


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
    assert "references/reconcile.md" in skill
    shared = (ROOT / Path(MAIN).parent / "references/reconcile.md").read_text()
    section = shared.split("## Corrections and retention\n", 1)[1].split("\n## ", 1)[0]
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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_fresh_skill_consumer_queries_then_performs_bounded_write(tmp_path, shared_core_binary, native_cli, surface):
    (tmp_path / "AGENTS.md").write_text(STARTUP_POINTER)
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
    assert (tmp_path / "AGENTS.md").read_text() == STARTUP_POINTER
    assert (tmp_path / MAIN).read_text() == (ROOT / MAIN).read_text()


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
        'version=1\n[notes.".agentic-workspace/memory/repo/context.md"]\nnote_type="decision"\nsemantic_routes=["repository/inspect"]\n'
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
    schema = json.loads((ROOT / "src/tooling/contracts/schemas/semantic_task_routes.schema.json").read_text())
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
