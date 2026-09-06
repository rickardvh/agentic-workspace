from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agentic_workspace.cli import main as run_cli
from agentic_workspace.operating_decision import CONTEXT_AUTHORITY_REGISTRY, _resolve_context_authority_source, compile_operating_decision
from agentic_workspace.scoped_instructions import (
    INSTRUCTION_DIR,
    _write_scaffold,
    inspect_instructions,
    instruction_program_for_operating_decision,
)
from agentic_workspace.semantic_task_routes import (
    current_semantic_task_route_fact,
    discover_semantic_routes,
    select_semantic_task_routes,
)
from agentic_workspace.workspace_runtime_proof import _proof_selection_for_changed_paths


def _write(root: Path, name: str, text: str) -> Path:
    path = root / INSTRUCTION_DIR / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _admit(root: Path) -> str:
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Source owner",
            "-c",
            "user.email=owner@example.test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Admit exact instruction snapshot",
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    (root / ".agentic-workspace/config.toml").write_text(
        f'schema_version = 1\n[assurance]\ninstruction_revision = "{revision}"\n', encoding="utf-8"
    )
    return revision


def test_instruction_change_during_applicability_cannot_reuse_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import scoped_instructions as instructions

    source = _write(tmp_path, "race", "---\npaths: [src/**]\nprotect: [generated/**]\n---\nRule\n")
    _admit(tmp_path)
    original = instructions.read_instruction

    def read(path: Path, *, root: Path, load_body: bool = False):
        if load_body:
            source.write_text(source.read_text().replace("src/**", "other/**"), encoding="utf-8")
        return original(path, root=root, load_body=load_body)

    monkeypatch.setattr(instructions, "read_instruction", read)
    result = instructions.inspect_instructions(tmp_path, changed_paths=["src/a.py"], include_ir=True)
    assert result["instruction_program"]["clauses"] == []
    assert result["diagnostics"][0]["code"] == "stale-source"


def test_instruction_hard_bindings_require_current_shared_admission(tmp_path: Path) -> None:
    source = _write(
        tmp_path,
        "binding",
        "---\npaths:\n  - src/**\nchecks:\n  - run: pytest -q\nprotect:\n  - generated/**\nuse:\n  - absent-recommendation\n---\n# Rule\n",
    )

    def inspect() -> dict:
        return inspect_instructions(tmp_path, changed_paths=["src/a.py"], include_ir=True)

    assert inspect()["instruction_program"]["capabilities"] == []
    _admit(tmp_path)
    admitted = inspect()
    assert {effect["kind"] for clause in admitted["instruction_program"]["clauses"] for effect in clause["effects"]} >= {
        "require",
        "restrict",
    }
    assert admitted["instruction_program"]["source_diagnostics"] == []
    assert admitted["instruction_program"]["capabilities"][0]["current"] is False
    # A recommendation's disappearance neither grants nor cancels hard authority.
    assert admitted["diagnostics"][0]["code"] == "missing-reference"
    source.with_name("lookalike.md").write_bytes(source.read_bytes())
    lookalike = next(row for row in inspect()["instructions"] if row["id"] == "lookalike")
    assert lookalike["binding_admission"]["status"] == "unadmitted"
    assert lookalike["checks"] == lookalike["protect"] == []
    shared = tmp_path / ".agentic-workspace/config.toml"
    (shared.parent / "config.local.toml").write_bytes(shared.read_bytes())
    shared.write_text("schema_version = 1\n", encoding="utf-8")
    assert inspect()["instruction_program"]["capabilities"] == []
    _admit(tmp_path)
    source.write_text(source.read_text() + "Changed source\n", encoding="utf-8")
    stale = next(row for row in inspect()["instructions"] if row["id"] == "binding")
    assert stale["binding_admission"]["status"] == "stale"
    assert stale["checks"] == stale["protect"] == []


def test_shared_semantic_route_only_activates_independently_admitted_instruction(tmp_path: Path) -> None:
    from agentic_workspace.decision import semantic_route_view
    from agentic_workspace.semantic_task_routes import semantic_route_host_context

    _route_skill_registry(tmp_path)
    source = _write(
        tmp_path,
        "route-binding",
        "---\nroutes:\n  - workspace/ownership/audit\nprotect:\n  - generated/**\n---\n# Binding\n",
    )
    host = semantic_route_host_context(tmp_path, task="Neutral work")
    request = semantic_route_view(host)["requests"][1]
    request["arguments"] = {"posture": "selected", "routes": ["workspace/ownership/audit"]}
    route = semantic_route_view({**host, "request": request})["decision"]["semantic_task_routes"]
    assert inspect_instructions(tmp_path, semantic_route_fact=route)["instructions"][0]["protect"] == []
    _admit(tmp_path)
    assert inspect_instructions(tmp_path, semantic_route_fact=route)["instructions"][0]["protect"] == ["generated/**"]
    host["source"]["revision"] = "sha256:" + "0" * 64
    stale = semantic_route_view({**host, "request": request})["decision"]["semantic_task_routes"]
    assert inspect_instructions(tmp_path, semantic_route_fact=stale)["instructions"][0]["protect"] == []
    source.write_text("---\npaths:\n  - src/**\nprotect:\n  - generated/**\n---\n# Path binding\n", encoding="utf-8")
    _admit(tmp_path)
    exact = inspect_instructions(tmp_path, changed_paths=["src/a.py"], semantic_route_fact=stale, include_ir=True)
    assert exact["instructions"][0]["protect"] == ["generated/**"]
    assert exact["instruction_program"]["facts"][0]["source"]["current"] is True


def _skill(root: Path, name: str) -> None:
    path = root / ".agentic-workspace" / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {name}\n", encoding="utf-8")


def _route_skill_registry(root: Path) -> Path:
    registry = root / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "skill-registry.v1",
        "skills": [
            {
                "id": "issue-shaping",
                "path": "issue-shaping/SKILL.md",
                "summary": "Shape issues.",
                "semantic_routes": [{"id": "github/issues/create", "match": "exact", "priority": 10, "description": "Create issues."}],
            },
            {
                "id": "ownership-audit",
                "path": "ownership-audit/SKILL.md",
                "summary": "Audit ownership.",
                "semantic_routes": [
                    {"id": "workspace/ownership/audit", "match": "exact", "priority": 10, "description": "Audit ownership."}
                ],
            },
        ],
    }
    registry.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for skill in ("issue-shaping", "ownership-audit"):
        path = root / "tools/skills" / skill / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {skill}\n", encoding="utf-8")
    return registry


def test_semantic_routes_are_progressive_current_work_bound_and_instruction_consumed(tmp_path: Path) -> None:
    registry = _route_skill_registry(tmp_path)
    _write(
        tmp_path,
        "issue-work",
        "---\nroutes:\n  - github/issues/**\nuse:\n  - issue-shaping\n---\n\n# Issue work\n\nUse the procedure.\n",
    )
    _write(
        tmp_path,
        "ownership",
        "---\nroutes:\n  - workspace/ownership/audit\nuse:\n  - ownership-audit\n---\n\n# Ownership\n",
    )

    roots = discover_semantic_routes(tmp_path)
    assert [item["id"] for item in roots["routes"]] == ["github", "workspace"]
    assert roots["full_catalogue_emitted"] is False
    branch = discover_semantic_routes(tmp_path, parent="github/issues")
    assert branch["routes"] == [{"id": "github/issues/create", "leaf": True, "child_count": 0}]
    exact = discover_semantic_routes(tmp_path, exact="github/issues/create")
    assert exact["routes"][0]["capabilities"] == ["skill:issue-shaping"]

    stale = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["github/issues/create"],
        expected_source_revision="sha256:" + "0" * 64,
    )
    assert stale["status"] == "blocked"
    assert stale["reason_codes"] == ["route-source-revision-mismatch"]
    selected = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["github/issues/create"],
        expected_source_revision=roots["source_revision"],
    )
    assert selected["status"] == "selected"
    assert selected["fact"]["task_identity"] == {
        "kind": "current-work",
        "id": selected["fact"]["current_work_id"],
    }
    assert selected["fact"]["authority_effect"] == "applicability-only"
    replay = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["github/issues/create"],
        expected_source_revision=roots["source_revision"],
    )
    assert replay["status"] == "already-current"
    assert replay["mutation_applied"] is False
    wrong_work = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["github/issues/create"],
        expected_source_revision=roots["source_revision"],
        current_work_id="different-work",
    )
    assert wrong_work["status"] == "blocked"
    assert wrong_work["reason_codes"] == ["current-work-mismatch"]

    inspection = inspect_instructions(tmp_path, task="words do not classify this task")
    assert [item["id"] for item in inspection["instructions"] if item["applies"]] == ["issue-work"]
    assert inspection["semantic_task_routes"]["status"] == "current"
    program = instruction_program_for_operating_decision(root=tmp_path, task="unrelated prose", changed_paths=[])
    assert next(effect for effect in program["clauses"][0]["effects"] if effect["kind"] == "prefer")["target"] == "skill:issue-shaping"

    multiple = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["workspace/ownership/audit", "github/issues/create"],
        expected_source_revision=roots["source_revision"],
    )
    assert multiple["fact"]["routes"] == ["github/issues/create", "workspace/ownership/audit"]
    assert {item["id"] for item in inspect_instructions(tmp_path)["instructions"] if item["applies"]} == {
        "issue-work",
        "ownership",
    }

    none = select_semantic_task_routes(
        tmp_path,
        posture="none",
        routes=[],
        expected_source_revision=roots["source_revision"],
    )
    assert none["status"] == "classified-none"
    quiet = inspect_instructions(tmp_path, task="create github issue")
    assert quiet["applicable_count"] == 0

    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["skills"][0]["summary"] = "Changed route source."
    registry.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert current_semantic_task_route_fact(tmp_path)["status"] == "stale"
    assert current_semantic_task_route_fact(tmp_path)["stale_reasons"] == ["route-source-changed"]


def test_selected_route_with_unavailable_recommended_procedure_is_non_binding(tmp_path: Path) -> None:
    registry = _route_skill_registry(tmp_path)
    _write(
        tmp_path,
        "issue-work",
        "---\nroutes:\n  - github/issues/create\nuse:\n  - missing-issue-procedure\n---\n\n# Issue work\n",
    )
    discovery = discover_semantic_routes(tmp_path, exact="github/issues/create")
    selected = select_semantic_task_routes(
        tmp_path,
        posture="selected",
        routes=["github/issues/create"],
        expected_source_revision=discovery["source_revision"],
    )
    assert selected["status"] == "selected"

    decision = compile_operating_decision(
        inputs={"target_root": str(tmp_path), "task": "neutral wording", "requested_claim_classes": ["complete"]}
    )

    assert decision["status"] != "blocked"
    assert decision["instruction_clause_projection"]["blockers"] == []
    assert registry.is_file()


def test_repo_pr_review_route_declares_existing_procedure_and_anti_trap(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    route = "github/pr/review"
    discovery = discover_semantic_routes(root, exact=route)
    assert discovery["routes"][0]["capabilities"] == ["skill:pr-review-recheck"]

    monkeypatch.setattr(
        "agentic_workspace.scoped_instructions.current_semantic_task_route_fact",
        lambda _root: {
            "kind": "agentic-workspace/semantic-task-route-fact/v1",
            "status": "current",
            "posture": "selected",
            "routes": [route],
            "current_work_id": "pr-review-fixture",
            "source_revision": discovery["source_revision"],
            "authority_effect": "applicability-only",
        },
    )

    inspection = inspect_instructions(root, task="implementation wording cannot infer this route")
    instruction = next(item for item in inspection["instructions"] if item["id"] == "github-pr-review")
    assert instruction["applies"] is True
    assert instruction["use"] == ["skill:pr-review-recheck"]
    assert instruction["read"] == [".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
    assert "does not grant review" in instruction["guidance"]


def test_global_and_path_scoped_markdown_are_progressively_disclosed(tmp_path: Path) -> None:
    _write(tmp_path, "repository", "# Repository\n\nKeep changes small.\n")
    _write(
        tmp_path,
        "authentication",
        "---\npaths:\n  - src/auth/**\n---\n\n# Authentication\n\nNever log credentials.\n",
    )

    auth = inspect_instructions(tmp_path, task="Update tokens", changed_paths=["src/auth/token.py"])
    docs = inspect_instructions(tmp_path, task="Fix docs", changed_paths=["docs/index.md"])

    assert [item["id"] for item in auth["instructions"] if item["applies"]] == ["authentication", "repository"]
    assert auth["progressive_disclosure"]["irrelevant_bodies_loaded"] == 0
    irrelevant = next(item for item in docs["instructions"] if item["id"] == "authentication")
    assert irrelevant["applies"] is False
    assert irrelevant["body_loaded"] is False
    assert irrelevant["guidance"] == ""
    assert docs["applicable_count"] == 1


def test_five_fields_compile_through_the_bounded_instruction_program(tmp_path: Path) -> None:
    _skill(tmp_path, "security-review")
    (tmp_path / "docs/security").mkdir(parents=True)
    (tmp_path / "docs/security/authentication.md").write_text("canonical source\n", encoding="utf-8")
    _write(
        tmp_path,
        "authentication",
        """---
paths:
  - src/auth/**
read:
  - docs/security/authentication.md
use:
  - security-review
checks:
  - run: pytest tests/auth -q
protect:
  - generated/**
---

# Authentication

Preserve token compatibility.
""",
    )

    _admit(tmp_path)
    program = instruction_program_for_operating_decision(root=tmp_path, task="Update auth", changed_paths=["src/auth/token.py"])
    effects = program["clauses"][0]["effects"]

    assert {effect["kind"] for effect in effects} == {"surface", "prefer", "require", "restrict"}
    assert {effect["target"] for effect in effects if effect["kind"] == "surface"} == {
        "surface:instruction:authentication",
        "surface:docs/security/authentication.md",
    }
    assert next(effect for effect in effects if effect["kind"] == "prefer")["target"] == "skill:security-review"
    assert next(effect for effect in effects if effect["kind"] == "restrict")["target"] == "effect:write:generated/**"
    requirement = next(effect for effect in effects if effect["kind"] == "require")
    assert requirement["target"] == "claim:complete"
    assert requirement["satisfier"].startswith("instruction-check:authentication:")


def test_inline_check_identity_is_stable_and_changes_with_command(tmp_path: Path) -> None:
    path = _write(tmp_path, "tests", "---\nchecks:\n  - run: pytest -q\n---\n\n# Tests\n")
    _admit(tmp_path)
    first = instruction_program_for_operating_decision(root=tmp_path, task="", changed_paths=[])
    second = instruction_program_for_operating_decision(root=tmp_path, task="", changed_paths=[])
    first_id = first["capabilities"][0]["id"]
    assert second["capabilities"][0]["id"] == first_id

    path.write_text("---\nchecks:\n  - run: pytest tests/unit -q\n---\n\n# Tests\n", encoding="utf-8")
    _admit(tmp_path)
    changed = instruction_program_for_operating_decision(root=tmp_path, task="", changed_paths=[])
    assert changed["capabilities"][0]["id"] != first_id


def test_static_check_reports_missing_ambiguous_and_invalid_hard_references_without_execution(tmp_path: Path) -> None:
    _skill(tmp_path, "review")
    nested = tmp_path / ".agents/skills/review/SKILL.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# review\n", encoding="utf-8")
    sentinel = tmp_path / "must-not-exist"
    _write(
        tmp_path,
        "bad",
        f"---\nuse:\n  - missing-skill\nchecks:\n  - run: touch {sentinel}\nprotect:\n  - /absolute/**\n---\n\n# Bad\n",
    )

    result = inspect_instructions(tmp_path)

    assert result["status"] == "invalid"
    assert {item["code"] for item in result["diagnostics"]} >= {"invalid-repo-pattern", "missing-reference"}
    assert not sentinel.exists()
    decision = compile_operating_decision(inputs={"target_root": str(tmp_path), "requested_claim_classes": ["complete"]})
    assert decision["instruction_clause_projection"]["blockers"] == []


def test_qualified_reference_is_deterministic_and_short_ambiguity_is_actionable(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path, "review", "---\nuse:\n  - review\n---\n\n# Review\n")
    monkeypatch.setattr(
        "agentic_workspace.scoped_instructions._capability_candidates",
        lambda _root: {"review": ["skill:review", "operation:review"], "skill:review": ["skill:review"]},
    )
    ambiguous = inspect_instructions(tmp_path)
    assert ambiguous["diagnostics"][0]["code"] == "ambiguous-reference"
    assert "skill:review" in ambiguous["diagnostics"][0]["message"]

    _write(tmp_path, "qualified", "---\nuse:\n  - skill:review\n---\n\n# Qualified\n")
    qualified = inspect_instructions(tmp_path)
    item = next(item for item in qualified["instructions"] if item["id"] == "qualified")
    assert item["use"] == ["skill:review"]


def test_protection_and_check_requirements_affect_the_existing_operating_decision(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "generated",
        "---\npaths:\n  - src/**\nchecks:\n  - run: pytest -q\nprotect:\n  - generated/**\n---\n\n# Generated\n",
    )
    _admit(tmp_path)
    decision = compile_operating_decision(
        inputs={
            "target_root": str(tmp_path),
            "task": "Update source",
            "changed_paths": ["src/a.py", "generated/client.py"],
            "requested_claim_classes": ["complete"],
        }
    )

    projection = decision["instruction_clause_projection"]
    assert {item["reason_code"] for item in projection["blockers"]} == {"denied-effect", "missing-capability"}
    assert decision["scoped_instruction_projection"]["applicable_count"] == 1
    assert decision["status"] == "blocked"


def test_inline_check_enters_the_existing_trusted_proof_route(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "source-tests",
        "---\npaths:\n  - src/**\nchecks:\n  - run: uv run pytest -q\n---\n\n# Source tests\n",
    )

    _admit(tmp_path)
    selection = _proof_selection_for_changed_paths(
        changed_paths=["src/example.py"],
        target_root=tmp_path,
        task_text="Update source",
        include_durable_intent=False,
        include_assurance_requirements=False,
        include_routine_work_context=False,
        include_runtime_diagnostics=False,
        include_test_strategy_check=False,
    )

    selected = next(item for item in selection["selected_commands"] if item["lane"] == "scoped-instruction:source-tests")
    assert selected["command"].endswith("uv run pytest -q")
    assert selected["route_authority"] == "repo-owned-scoped-instruction"
    assert selected["authority_surface"] == ".agentic-workspace/instructions/source-tests.md"
    assert selected["required"] is True


def test_scoped_markdown_can_reference_named_repo_requirement_without_creating_a_second_gate(tmp_path: Path) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        """schema_version = 1

[assurance.requirements.typed_exit]
level = "high"
applies_to_paths = ["src/**"]
required_evidence = ["typed_exit_fixture"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
requirement_class = "invariant"
source_intent_ref = "SYSTEM_INTENT.md#trust"
source_intent_revision = "r1"
source_intent_current = true
evidence_owner = "verification:typed-exit"
detail_route = "agentic-workspace proof --select typed-exit"
""",
        encoding="utf-8",
    )
    _write(
        tmp_path,
        "runtime",
        "---\npaths:\n  - src/**\nchecks:\n  - requirement:typed_exit\n---\n\n# Runtime\n",
    )

    program = instruction_program_for_operating_decision(root=tmp_path, task="", changed_paths=["src/cli.py"])

    assert program["capabilities"] == []
    effects = program["clauses"][0]["effects"]
    assert {item["target"] for item in effects} == {
        "surface:instruction:runtime",
        "surface:requirement:typed_exit",
    }
    assert all(item["kind"] == "surface" for item in effects)


def test_scaffold_is_minimal_and_never_overwrites(tmp_path: Path) -> None:
    global_result = _write_scaffold(tmp_path, name="repository", paths=[])
    _write_scaffold(tmp_path, name="authentication", paths=["src/auth/**"])

    assert global_result["scope"] == ["global"]
    assert not (tmp_path / INSTRUCTION_DIR / "repository.md").read_text(encoding="utf-8").startswith("---")
    scoped = (tmp_path / INSTRUCTION_DIR / "authentication.md").read_text(encoding="utf-8")
    assert "paths:\n  - src/auth/**" in scoped
    assert all(f"{field}:" not in scoped for field in ("read", "use", "checks", "protect"))
    try:
        _write_scaffold(tmp_path, name="authentication", paths=[])
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing instruction must not be overwritten")


def test_cli_create_check_explain_and_migrate_are_one_coherent_surface(tmp_path: Path, capsys) -> None:
    assert run_cli(["instructions", "new", "--name", "auth", "--paths", "src/auth/**", "--target", str(tmp_path), "--format", "json"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["status"] == "created"
    assert run_cli(["instructions", "check", "--target", str(tmp_path), "--format", "json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["status"] == "valid"
    assert (
        run_cli(
            [
                "instructions",
                "explain",
                "--task",
                "Update auth",
                "--changed",
                "src/auth/token.py",
                "--target",
                str(tmp_path),
                "--format",
                "json",
            ]
        )
        == 0
    )
    explained = json.loads(capsys.readouterr().out)
    assert explained["instructions"][0]["reason"] == "src/auth/token.py matches src/auth/**"

    (tmp_path / "AGENTS.md").write_text("# Adapter\n\n## Auth\n\nGuidance\n", encoding="utf-8")
    assert run_cli(["instructions", "migrate", "--from", "AGENTS.md", "--target", str(tmp_path), "--format", "json"]) == 0
    migrated = json.loads(capsys.readouterr().out)
    assert migrated["candidate_headings"] == ["Auth"]
    assert migrated["writes_applied"] is False


def test_public_contract_stays_smaller_than_internal_ir_and_names_shared_targets() -> None:
    contract = json.loads(Path("src/agentic_workspace/contracts/scoped_markdown_instructions.json").read_text(encoding="utf-8"))
    client = Path("generated/workspace/typescript/src/client.mjs").read_text(encoding="utf-8")

    assert contract["frontmatter_fields"] == ["paths", "routes", "read", "use", "checks", "protect"]
    assert set(contract["forbidden_public_fields"]) >= {"when", "surface", "prefer", "require", "restrict", "allow"}
    assert {item["id"] for item in contract["operations"]} == {
        "instructions.list",
        "instructions.create",
        "instructions.check",
        "instructions.explain",
        "instructions.routes",
        "instructions.route-select",
        "instructions.migrate",
    }
    assert "export function invokeJson" in client


def test_semantic_task_route_disposition_records_subtractive_consumer_migrations() -> None:
    disposition = json.loads(Path("docs/maintainer/semantic-task-route-disposition.json").read_text(encoding="utf-8"))

    assert disposition["kind"] == "agentic-workspace/semantic-task-route-disposition/v1"
    assert disposition["shared_contract"]["authority_effect"] == "applicability-only"
    assert disposition["shared_contract"]["persistent_history"] == "none"
    by_surface = {item["surface"]: item for item in disposition["surfaces"]}
    assert by_surface["specialized skill recommendations"]["disposition"] == "consume-semantic-route"
    assert by_surface["Memory context-authority curation"]["disposition"] == "consume-semantic-route"
    assert by_surface["assurance requirements"]["stronger_facts_retained"]
    assert by_surface["Verification protocols"]["stronger_facts_retained"]
    assert disposition["net_reduction"]["new_peer_engines"] == 0
    assert len(disposition["net_reduction"]["removed_equal_authority_paths"]) >= 2


def test_repo_dogfooding_migration_is_scoped_and_keeps_bootstrap_thin() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "AGENTS.md").read_text(encoding="utf-8")
    relevant = inspect_instructions(root, changed_paths=["src/agentic_workspace/operating_decision.py"])
    irrelevant = inspect_instructions(root, changed_paths=["README.md"])

    assert "Repo-specific obligation" not in source
    dogfood = next(item for item in relevant["instructions"] if item["id"] == "workspace-dogfooding")
    assert dogfood["applies"] is True and dogfood["body_loaded"] is True
    suppressed = next(item for item in irrelevant["instructions"] if item["id"] == "workspace-dogfooding")
    assert suppressed["applies"] is False and suppressed["body_loaded"] is False


def test_context_authority_uses_canonical_instruction_directory_with_adapter_fallback(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "Authority marker:\n\n<!-- agentic-workspace:workflow:start -->\nOrdinary route:\n",
        encoding="utf-8",
    )
    _skill(tmp_path, "workspace-startup")
    _write(tmp_path, "repository", "# Repository\n\nKeep changes bounded.\n")
    item = next(item for item in CONTEXT_AUTHORITY_REGISTRY if item["surface"] == "scoped-instructions")

    canonical = _resolve_context_authority_source(
        item=item,
        target_root=tmp_path,
        consumer="skills",
        task="explain instruction routing",
        paths=[],
    )
    assert canonical["status"] == "current"
    assert canonical["source_id"] == ".agentic-workspace/instructions"
    assert canonical["admission"]["owner_result"]["compatibility_source"] == "canonical-scoped-markdown"

    instruction = tmp_path / INSTRUCTION_DIR / "repository.md"
    instruction.unlink()
    instruction.parent.rmdir()
    fallback = _resolve_context_authority_source(
        item=item,
        target_root=tmp_path,
        consumer="skills",
        task="explain instruction routing",
        paths=[],
    )
    assert fallback["status"] == "current"
    assert fallback["source_id"] == "AGENTS.md"
    assert fallback["admission"]["owner_result"]["compatibility_source"] == "thin-agent-adapter"
