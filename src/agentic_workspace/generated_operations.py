# Generated from the external consumer profile. Do not edit.
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .client import invoke_operation


def agent_guidance_delete(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.delete",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_edit(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.edit",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_merge(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.merge",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_promote(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.promote",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_retire(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.retire",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_revalidate(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.revalidate",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_split(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.split",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_supersede(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.supersede",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_suppress(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.suppress",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def agent_guidance_weaken(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "agent-guidance.weaken",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_admit(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.admit",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_cleanup(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.cleanup",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_close(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.close",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_dispatch(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.dispatch",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_export(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.export",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_import(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.import",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_integrate(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.integrate",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_override(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.override",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_reassign(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.reassign",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_reject(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.reject",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def assignment_repair(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "assignment.repair",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def config_report(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "config.report",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_correct_dispute(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.correct-dispute",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_identity_init(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.identity-init",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_prune_compact(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.prune-compact",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_query(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.query",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_submit(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.submit",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def correction_event_withdraw_supersede(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "correction-event.withdraw-supersede",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def delegation_outcome_append(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "delegation-outcome.append",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_authority_refresh(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.authority-refresh",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_delivery_status(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.delivery-status",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_external_adapter_receipt(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.external-adapter-receipt",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_external_delivery(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.external-delivery",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_external_host_result_import(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.external-host-result-import",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_external_request(
    values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None
) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.external-request",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_local_delivery(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.local-delivery",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_observe(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.observe",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_report_preview(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.report-preview",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def evaluation_retry(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "evaluation.retry",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def external_evidence_query(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "external-evidence.query",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def external_evidence_submit(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "external-evidence.submit",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_check(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.check",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_create(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.create",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_explain(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.explain",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_list(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.list",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_migrate(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.migrate",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_route_select(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.route-select",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )


def instructions_routes(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation(
        "instructions.routes",
        values,
        target=target,
        invocation=invocation,
        allow_runtime_backed=True,
    )
