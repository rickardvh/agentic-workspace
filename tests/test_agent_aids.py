import importlib.util
import json
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_agent_aids.py"
_SPEC = importlib.util.spec_from_file_location("check_agent_aids", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_agent_aids = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check_agent_aids
_SPEC.loader.exec_module(check_agent_aids)

_SCHEMA_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "contracts" / "schemas" / "agent_aid_manifest.schema.json"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _prepare_schema(root: Path) -> None:
    _write(root / "src" / "agentic_workspace" / "contracts" / "schemas" / "agent_aid_manifest.schema.json", _SCHEMA_SOURCE.read_text())


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
            "target": "scripts/check/check_workspace_validation.py",
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
    entrypoint = "scripts/check/check_workspace_validation.py"
    payload = _valid_manifest(entrypoint=entrypoint)
    _write(tmp_path / manifest, json.dumps(payload))
    _write(tmp_path / entrypoint, "print('ok')\n")

    findings = check_agent_aids.agent_aid_findings([manifest, entrypoint], root=tmp_path)

    assert any("entrypoint must live inside the aid directory" in finding.message for finding in findings)
