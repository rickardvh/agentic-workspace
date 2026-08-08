"""Command-generation-owned context-authority operation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from agentic_workspace._context_authority_owner_protocol import _issue_owner_result


def generated_references_context_authority_owner_operation(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
    if kwargs.get("source_specific"):
        raise ValueError("generated-references owner operation derives semantic evidence from its canonical subsystem")
    try:
        manifest = json.loads(kwargs["chosen"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    paths = manifest.get("file_paths")
    expected_entries = manifest.get("git_index_entries")
    expected_identity = manifest.get("git_index_identity")
    current = manifest.get("kind") == "generated-cli-source-manifest/v1"
    if current and isinstance(paths, list) and isinstance(expected_entries, dict) and isinstance(expected_identity, str):
        process = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=kwargs["root"], capture_output=True, check=False)
        all_entries: dict[str, str] = {}
        if process.returncode == 0:
            for raw in process.stdout.split(b"\0"):
                if not raw:
                    continue
                metadata, _, indexed_path = raw.decode("utf-8").partition("\t")
                fields = metadata.split()
                if len(fields) == 3 and fields[2] == "0":
                    all_entries[indexed_path] = fields[1]
        observed = {str(path): all_entries.get(str(path), "") for path in paths}
        digest = hashlib.sha256()
        for path in paths:
            digest.update(str(path).encode())
            digest.update(b"\0")
            digest.update(observed.get(str(path), "").encode())
            digest.update(b"\0")
        current = observed == expected_entries and digest.hexdigest() == expected_identity
    elif current:
        current = set(manifest) == {"kind", "source_hashes"} and manifest.get("source_hashes") == {}
    status = "current" if current else "stale"
    reason = "" if current else "generated-source-manifest-stale"
    producer = "agentic_workspace.contract_tooling.generated_references"
    operation_id = "generated-command-packages.refresh"
    boundary = "Generated command package source-manifest authority"
    population = {"status": "present" if current else "invalid"}
    schema = {
        "source_format": "json",
        "parse_status": "valid" if current else "invalid",
        "generated_source_manifest_kind": str(manifest.get("kind") or ""),
        "manifest_identity": str(expected_identity or ""),
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
            "currentness_basis": "generated manifest path set and exact Git index identity",
        },
        surface_specific={"generated_source_manifest": manifest},
        executor="agentic_workspace.context_authority_generated_owner.generated_references_context_authority_owner_operation",
    )
