"""Verification-owned proof context-authority operation."""

from __future__ import annotations

import tomllib
from typing import Any


def proof_context_authority_owner_operation(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
    if kwargs.get("source_specific"):
        raise ValueError("proof owner operation derives semantic evidence from its canonical subsystem")
    from agentic_workspace._context_authority_owner_protocol import _issue_owner_result

    try:
        manifest = tomllib.loads(kwargs["chosen"].read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        manifest = {}
    scenarios = manifest.get("scenarios")
    current = bool(manifest.get("schema_version")) and isinstance(scenarios, (list, dict)) and bool(scenarios)
    status = "current" if current else "invalid"
    reason = "" if current else "verification-proof-manifest-not-admitted"
    producer = "agentic_verification.proof"
    operation_id = "proof.select"
    boundary = "Verification manifest proof-route contract"
    population = {"status": "present" if current else "invalid"}
    schema = {
        "source_format": "toml",
        "parse_status": "valid" if current else "invalid",
        "missing_required_keys": [] if current else ["schema_version", "scenarios"],
        "scenario_count": len(scenarios) if isinstance(scenarios, (list, dict)) else 0,
        "population": population,
    }
    return _issue_owner_result(
        surface="proof",
        producer=producer,
        result_kind="agentic-workspace/proof-selection/v1",
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
            "currentness_basis": "Verification manifest schema and registered scenario population",
        },
        surface_specific={"verification_manifest_revision": "sha256:" + kwargs["revision"]},
        executor="repo_verification_bootstrap.context_authority_owner.proof_context_authority_owner_operation",
    )
