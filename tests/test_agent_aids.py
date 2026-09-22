import importlib.util
import json
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "tooling" / "check" / "check_agent_aids.py"
_SPEC = importlib.util.spec_from_file_location("check_agent_aids", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_agent_aids = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check_agent_aids
_SPEC.loader.exec_module(check_agent_aids)

_SCHEMA_SOURCE = Path(__file__).resolve().parents[1] / "src/core/contracts/schemas/agent_aid_manifest.schema.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_selected_executable_static_closure_never_runs_helpers(tmp_path):
    registry = tmp_path / "tools/skills/REGISTRY.json"
    skill = {"id": "example", "executable": {"entrypoint": {"kind": "file", "path": "helper.py"}, "dependencies": ["template.yml"]}}
    _write(registry, json.dumps({"skills": [skill]}))
    _write(tmp_path / "helper.py", "raise RuntimeError('must never execute during validation')")
    assert "template.yml" in check_agent_aids.executable_dependency_findings(tmp_path)[0].message
    _write(tmp_path / "template.yml", "current template")
    assert check_agent_aids.executable_dependency_findings(tmp_path) == []
    skill["executable"]["entrypoint"] = {"kind": "native", "command": "resources"}
    skill["executable"]["dependencies"] = []
    _write(registry, json.dumps({"skills": [skill]}))
    assert check_agent_aids.executable_dependency_findings(tmp_path) == []


def _prepare_schema(root: Path) -> None:
    _write(root / "src/core/contracts/schemas/agent_aid_manifest.schema.json", _SCHEMA_SOURCE.read_text())


def _valid_manifest(**overrides):
    payload = {
        "kind": "agentic-workspace/agent-aid/v1",
        "id": "workspace-validation-wrapper",
        "type": "script",
        "status": "candidate",
        "scope": "repo-shared",
        "portability": "cross-platform",
        "proof_role": "candidate-aid",
        "owner": "workspace",
        "created_because": "Agents repeatedly need a bounded validation wrapper.",
        "use_when": ["validating workspace CLI and contract changes"],
        "entrypoint": ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
        "safety": {
            "read_only": True,
            "writes_repo": False,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        },
        "validation": {"commands": ["uv run python .agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"]},
        "promotion": {
            "target_kind": "check",
            "target": "src/tooling/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts or required by proof routes",
            "retention_after_promotion": "delete",
        },
        "retirement": {
            "trigger": "promoted, obsolete, or no longer lowers repeated operating cost",
            "retention_after_retirement": "delete",
        },
    }
    payload.update(overrides)
    return payload


def test_valid_agent_aid_manifest_passes(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    _write(tmp_path / manifest, json.dumps(_valid_manifest()))
    _write(tmp_path / entrypoint, "print('ok')\n")

    assert check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path) == []


def test_candidate_bundle_uses_passive_selected_procedure_currentness(tmp_path, shared_core_binary):
    from agentic_workspace import start
    from aw_maintainer.native_conformance import route_discovery

    _prepare_schema(tmp_path)
    base = ".agentic-workspace/agent-aids/skills/change-note"
    manifest, skill = f"{base}/manifest.json", f"{base}/SKILL.md"
    aid = _valid_manifest(id="change-note", type="skill", entrypoint=skill, procedure_resource="procedure.md")
    _write(tmp_path / manifest, json.dumps(aid))
    _write(
        tmp_path / skill, "---\nname: change-note\ndescription: Draft a bounded change note.\n---\nRead [helper](src/tooling/helper.py).\n"
    )
    _write(tmp_path / base / "src/tooling/helper.py", "raise RuntimeError('discovery must not execute helpers')\n")
    form = {
        "kind": "agentic-workspace/procedure/v1",
        "id": "note",
        "question": "Does the change affect users?",
        "branches": [{"id": "yes", "description": "User impact", "next": "user.md"}],
    }
    _write(tmp_path / base / "procedure.md", "```agentic-procedure\n" + json.dumps(form) + "\n```\n")
    _write(tmp_path / base / "user.md", "Selected user guidance")
    tracked = [p.relative_to(tmp_path).as_posix() for p in (tmp_path / base).rglob("*") if p.is_file()]
    assert check_agent_aids.agent_aid_findings(tracked, root=tmp_path) == []
    context = {"target": str(tmp_path), "task": "Evaluate a named candidate", "projection": "full"}
    ordinary = start(context)
    assert "change-note" not in json.dumps(ordinary)
    request = next(r for r in ordinary["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/discover/v1")
    request["arguments"]["parent"] = "candidate-skills/change-note"
    selected = start({**context, "request": request})
    assert "Selected user guidance" not in json.dumps(selected)
    selection = selected["procedure"]["requests"][0]
    unresolved = start({**context, "request": selection})
    answer = unresolved["procedure"]["requests"][0]
    answer["arguments"]["answer"] = {"disposition": "answered", "branches": ["yes"], "material": "The evaluated change affects users."}
    current = start({**context, "request": answer})
    assert current["procedure"]["status"] == "current"
    assert current["procedure"]["authority_effect"] == "none"
    _write(tmp_path / "unrelated.txt", "unrelated")
    assert start({**context, "request": answer})["procedure"]["status"] == "current"
    for path in ["src/tooling/helper.py", "SKILL.md", "user.md"]:
        source = tmp_path / base / path
        before = source.read_text()
        source.write_text(before + "\nChanged material\n")
        assert start({**context, "request": answer})["procedure"]["status"] == "stale"
        source.write_text(before)
    roots = route_discovery({"target": str(tmp_path)})
    assert roots["routes"] == [] and "change-note" not in json.dumps(roots)
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
    # Retirement preserves bytes while making retained procedure answers unusable.
    aid["status"] = "retired"
    _write(tmp_path / manifest, json.dumps(aid))
    assert start({**context, "request": answer})["procedure"]["status"] == "unavailable"
    aid["status"] = "candidate"
    # Plain skills use the same identity without acquiring procedural machinery.
    aid.pop("procedure_resource")
    _write(tmp_path / manifest, json.dumps(aid))
    plain = route_discovery({"target": str(tmp_path), "exact": "candidate-skills/change-note"})
    assert plain["routes"][0]["sources"][0]["procedure"]["status"] == "available"
    assert "resource" not in plain["routes"][0]["sources"][0]["procedure"]
    # Standard optional fields retain YAML types; limits count Unicode characters.
    frontmatter = {
        "name": "change-note",
        "description": "é" * 1024,
        "license": "Apache-2.0",
        "compatibility": "界" * 500,
        "metadata": {"version": "1.0"},
        "allowed-tools": "Read Bash(git:*)",
    }
    _write(tmp_path / skill, "---\n" + json.dumps(frontmatter, ensure_ascii=False) + "\n---\nInstructions.\n")
    assert check_agent_aids.agent_aid_findings(tracked, root=tmp_path) == []
    for field, invalid in [
        ("description", "é" * 1025),
        ("compatibility", "界" * 501),
        ("compatibility", ""),
        ("compatibility", 123),
        ("compatibility", None),
        ("metadata", []),
        ("metadata", {"version": 1}),
        ("metadata", None),
        ("allowed-tools", ["Read"]),
        ("allowed-tools", None),
        ("license", 123),
    ]:
        _write(tmp_path / skill, "---\n" + json.dumps({**frontmatter, field: invalid}) + "\n---\nInstructions.\n")
        assert field in check_agent_aids.agent_aid_findings(tracked, root=tmp_path)[0].message
    _write(tmp_path / skill, "---\nname: change-note\ndescription: Valid\nmetadata: {123: value}\n---\nInstructions.\n")
    assert "metadata" in check_agent_aids.agent_aid_findings(tracked, root=tmp_path)[0].message
    _write(tmp_path / skill, "# Arbitrary prose is not a standard skill\n")
    assert "frontmatter" in check_agent_aids.agent_aid_findings(tracked, root=tmp_path)[0].message
    (tmp_path / skill).unlink()
    assert (
        start({**context, "request": request})["semantic_routes"]["discovery"]["detail"]["sources"][0]["procedure"]["status"]
        == "unavailable"
    )


def test_agent_aid_file_requires_nearby_manifest(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([entrypoint], root=tmp_path)

    assert len(findings) == 1
    assert findings[0].path == entrypoint
    assert "manifest.json" in findings[0].message


def test_agent_aid_manifest_requires_safety_and_validation(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest()
    del payload["safety"]
    payload["validation"] = {}
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    messages = [finding.message for finding in findings]
    assert any("'safety' is a required property" in message for message in messages)
    assert any("is not valid under any of the given schemas" in message for message in messages)


def test_agent_aid_manifest_accepts_validation_absent_reason(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/runbooks/release-review/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/runbooks/release-review/review.md"
    payload = _valid_manifest(
        id="release-review",
        type="runbook",
        entrypoint=entrypoint,
        validation={"absent_reason": "Runbook is reviewed through ordinary docs review."},
    )
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "# Review\n")

    assert check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path) == []


def test_executable_agent_aid_requires_validation_commands(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(validation={"absent_reason": "No validation command yet."})
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("executable agent aids must declare validation.commands" in finding.message for finding in findings)


def test_platform_specific_agent_aid_requires_justification(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(portability="platform-specific")
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    messages = [finding.message for finding in findings]
    assert any("'portability_justification' is a required property" in message for message in messages)
    assert any("'checked_in_scope_justification' is a required property" in message for message in messages)


def test_executable_validation_command_must_reference_entrypoint(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(validation={"commands": ["uv run pytest tests/test_workspace_cli.py -q"]})
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("validation.commands must reference the manifest entrypoint" in finding.message for finding in findings)


def test_executable_validation_command_must_not_be_blank(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(validation={"commands": ["   "]})
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("validation.commands must not contain blank commands" in finding.message for finding in findings)


def test_candidate_agent_aid_cannot_be_hidden_required_workflow(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    _write(tmp_path / manifest, json.dumps(_valid_manifest()))
    _write(tmp_path / entrypoint, "print('ok')\n")
    _write(tmp_path / "Makefile", f"check:\n\tuv run python {entrypoint}\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint, "Makefile"], root=tmp_path)

    assert any("hidden required workflow entrypoints" in finding.message for finding in findings)


def test_high_risk_agent_aid_requires_review(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(
        safety={
            "read_only": False,
            "writes_repo": True,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        }
    )
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("must require review" in finding.message for finding in findings)


def test_candidate_agent_aid_cannot_claim_canonical_proof_role(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(proof_role="canonical-proof")
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("only promoted aids may declare proof_role='canonical-proof'" in finding.message for finding in findings)


def test_github_specific_advisory_aid_routes_facts_to_external_intent(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/github-issue-body/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/github-issue-body/new_github_issue_body.py"
    payload = _valid_manifest(
        id="github-issue-body",
        entrypoint=entrypoint,
        authority_boundary={
            "runtime_authority": "none",
            "fact_owner": "agent-aid",
            "agent_decision": "Agent interprets issue intent.",
        },
    )
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any(
        "GitHub-specific advisory aids must route behavior-relevant facts to external-intent evidence" in finding.message
        for finding in findings
    )


def test_agent_aid_manifest_requires_promotion_target_kind(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest()
    del payload["promotion"]["target_kind"]
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("'target_kind' is a required property" in finding.message for finding in findings)


def test_agent_aid_manifest_requires_promotion_discovery_route(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest()
    del payload["promotion"]["discovery_route"]
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("'discovery_route' is a required property" in finding.message for finding in findings)


def test_repo_shared_executable_canonical_proof_aid_must_be_cross_platform(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(
        status="promoted",
        proof_role="canonical-proof",
        portability="platform-specific",
        portability_justification="Only works on one platform.",
        checked_in_scope_justification="Kept for historical platform-specific proof.",
        promotion={
            "target_kind": "check",
            "target": "src/tooling/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts or required by proof routes",
            "retention_after_promotion": "keep",
        },
    )
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("repo-shared executable canonical proof aids must be cross-platform" in finding.message for finding in findings)


def test_promoted_candidate_manifest_cannot_keep_delete_retention(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(status="promoted")
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("promoted candidate manifests cannot retain retention_after_promotion='delete'" in finding.message for finding in findings)


def test_module_component_agent_aid_manifest_passes(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/module-components/review-router/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/module-components/review-router/resource.json"
    payload = _valid_manifest(
        id="review-router",
        type="module-component",
        entrypoint=entrypoint,
        promotion={
            "target_kind": "module-component",
            "target": "src/tooling/contracts/module_components.json",
            "discovery_route": "module-manifest",
            "trigger": "module component is useful across host repos",
            "retention_after_promotion": "delete",
        },
        validation={"absent_reason": "Module component manifests are validated by contract tooling after promotion."},
    )
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "{}\n")

    assert check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path) == []


def test_agent_aid_manifest_type_must_match_subdir(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/checks/workspace-validation/manifest.json"
    entrypoint = ".agentic-workspace/agent-aids/checks/workspace-validation/workspace_validation.py"
    payload = _valid_manifest(entrypoint=entrypoint)
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("manifest type must be 'check'" in finding.message for finding in findings)


def test_agent_aid_manifest_entrypoint_must_stay_inside_aid_directory(tmp_path: Path) -> None:
    _prepare_schema(tmp_path)
    manifest = ".agentic-workspace/agent-aids/scripts/workspace-validation/manifest.json"
    entrypoint = "src/tooling/check/check_workspace_validation.py"
    payload = _valid_manifest(entrypoint=entrypoint)
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("entrypoint must live inside the aid directory" in finding.message for finding in findings)
