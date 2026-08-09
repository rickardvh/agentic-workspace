"""Compatibility alias for the canonical workspace runtime implementation.

All runtime behavior is owned by :mod:`agentic_workspace.workspace_runtime_core`.
This module remains only because generated and third-party integrations import its
historical private symbol paths.
"""

from __future__ import annotations

import sys

from agentic_workspace import workspace_runtime_core as _canonical_runtime
from agentic_workspace import workspace_runtime_implement as _implement_owner
from agentic_workspace import workspace_runtime_planning as _planning_owner
from agentic_workspace import workspace_runtime_proof as _proof_owner
from agentic_workspace import workspace_runtime_startup as _startup_owner

_COMPATIBILITY_EXPORTS = {
    _startup_owner: (
        "_hydrate_selected_start_advisory_payloads",
        "_run_start_context_adapter",
        "_selector_first_start_payload",
        "_start_payload",
        "_tiny_start_payload",
    ),
    _implement_owner: (
        "_change_impact_payload",
        "_implement_payload",
        "_objective_drift_payload",
        "_run_implement_context_adapter",
        "_tiny_implement_payload",
    ),
    _planning_owner: (
        "_active_execplan_record_payload",
        "_active_planning_record",
        "_active_planning_record_for_report_section",
        "_is_bounded_current_task_route",
        "_planning_candidate_pressure_payload",
        "_planning_safety_gate_payload",
        "_pr_comment_repair_context_payload",
        "_raw_active_planning_record_for_closeout",
        "_run_reconcile_report_adapter",
    ),
    _proof_owner: (
        "_active_planning_record_for_proof",
        "_closeout_report_payload",
        "_proof_obligations_payload",
        "_proof_payload",
        "_proof_receipt_reconciliation_payload",
        "_proof_selection_for_changed_paths",
        "_tiny_proof_obligations_payload",
        "_tiny_proof_payload",
        "_verification_report_payload",
    ),
}
for _owner, _names in _COMPATIBILITY_EXPORTS.items():
    for _name in _names:
        setattr(_canonical_runtime, _name, getattr(_owner, _name))

# Preserve module identity, including monkeypatch semantics, for compatibility users.
sys.modules[__name__] = _canonical_runtime
