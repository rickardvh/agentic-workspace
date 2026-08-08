"""Planning-owned context-authority result operation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def planning_context_authority_owner_operation(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
    if kwargs.get("source_specific"):
        raise ValueError("planning owner operation derives semantic evidence from its canonical subsystem")
    from agentic_workspace._context_authority_owner_protocol import _issue_owner_result
    from agentic_workspace.workspace_runtime_core import _planning_owner_admission_payload

    chosen: Path = kwargs["chosen"]
    try:
        state_data = tomllib.loads(chosen.read_text(encoding="utf-8"))
        admission = _planning_owner_admission_payload(target_root=kwargs["root"], state_data=state_data)
    except Exception as exc:  # pragma: no cover - defensive package boundary.
        admission = {"status": "unavailable", "error": str(exc)}
    admission_status = str(admission.get("status") or "")
    accepted = {"accepted", "admitted", "current", "none"}
    current = admission_status in accepted
    status = "current" if current else "stale"
    reason = "" if current else f"planning-owner-admission-{admission_status or 'missing'}"
    producer = "agentic_planning.state"
    operation_id = "planning.summary.report"
    boundary = "Planning current-work admission contract"
    schema = {
        "source_format": "toml",
        "parse_status": "valid" if current else "invalid",
        "planning_owner_admission": admission,
        "accepted_statuses": sorted(accepted),
        "population": {"status": "present" if current else "invalid"},
    }
    return _issue_owner_result(
        surface="planning",
        producer=producer,
        result_kind="agentic-planning/current-work-selection/v1",
        operation_id=operation_id,
        owner=kwargs.get("owner"),
        root=kwargs["root"],
        chosen=chosen,
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
        population=dict(schema["population"]),
        supersession={
            "status": "not-superseded" if current else "unknown-until-repair",
            "supersedes": "",
            "superseded_by": "",
            "currentness_basis": "Planning admission and selected owner revision",
        },
        surface_specific={"planning_owner_admission": admission, "accepted_statuses": sorted(accepted)},
        executor="repo_planning_bootstrap.context_authority_owner.planning_context_authority_owner_operation",
    )
