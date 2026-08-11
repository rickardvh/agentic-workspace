"""Command-generation-owned context-authority operation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from agentic_workspace._context_authority_owner_protocol import _issue_owner_result


def _source_manifest_status(*, root: Path, chosen: Path) -> dict[str, str]:
    launcher_path = root / "scripts" / "run_agentic_workspace.py"
    spec = importlib.util.spec_from_file_location("run_agentic_workspace_context_authority", launcher_path)
    if spec is None or spec.loader is None:
        return {"status": "invalid", "reason": "launcher-unavailable", "auxiliary_witness": "not-evaluated"}
    launcher = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(launcher)
        classifier = launcher.source_cli_fingerprint_manifest_status
    except (AttributeError, OSError, ImportError):
        return {"status": "invalid", "reason": "launcher-unavailable", "auxiliary_witness": "not-evaluated"}
    return classifier(repo_root=root, manifest_path=chosen)


def generated_references_context_authority_owner_operation(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
    if kwargs.get("source_specific"):
        raise ValueError("generated-references owner operation derives semantic evidence from its canonical subsystem")
    try:
        manifest = json.loads(kwargs["chosen"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    expected_identity = manifest.get("git_index_identity")
    legacy_empty_manifest = (
        set(manifest) == {"kind", "source_hashes"}
        and manifest.get("kind") == "generated-cli-source-manifest/v1"
        and not manifest["source_hashes"]
    )
    if legacy_empty_manifest:
        manifest_status = {"status": "current", "reason": "legacy-empty-source-hashes", "auxiliary_witness": "not-applicable"}
    elif manifest.get("kind") != "generated-cli-source-manifest/v1":
        manifest_status = {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
    else:
        manifest_status = _source_manifest_status(root=kwargs["root"], chosen=kwargs["chosen"])
    current = manifest_status["status"] == "current"
    status = "current" if current else "stale"
    reason = "" if current else manifest_status["reason"]
    producer = "agentic_workspace.contract_tooling.generated_references"
    operation_id = "generated-command-packages.refresh"
    boundary = "Generated command package source-manifest authority"
    population = {"status": "present" if current else "invalid"}
    schema = {
        "source_format": "json",
        "parse_status": "valid" if current else "invalid",
        "generated_source_manifest_kind": str(manifest.get("kind") or ""),
        "manifest_identity": str(expected_identity or ""),
        "freshness_reason": manifest_status["reason"],
        "auxiliary_witness": manifest_status["auxiliary_witness"],
        "population": population,
    }
    return _issue_owner_result(
        surface="generated-references",
        producer=producer,
        result_kind="generated-cli-source-manifest/v1",
        operation_id=operation_id,
        owner=kwargs.get("owner"),
        root=kwargs["root"],
        chosen=kwargs["chosen"],
        revision=kwargs["revision"],
        git_head=kwargs["git_head"],
        selection=kwargs["selection"],
        status=status,
        reason=reason,
        owner_boundary=boundary,
        schema_backing=schema,
        lifecycle={
            "status": "current" if current else "repair-required",
            "reason": reason,
            "owner_boundary": boundary,
            "repair_operation_id": operation_id,
            "repair_owner": producer,
        },
        population=population,
        supersession={
            "status": "not-superseded" if current else "unknown-until-repair",
            "supersedes": "",
            "superseded_by": "",
            "currentness_basis": "generated manifest semantic content identity with optional Git index acceleration",
        },
        surface_specific={"generated_source_manifest": manifest},
        executor="agentic_workspace.context_authority_generated_owner.generated_references_context_authority_owner_operation",
    )
