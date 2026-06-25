from __future__ import annotations

from agentic_workspace.workspace_runtime_projection import (
    _authority_boundary_payload,
    _compact_authority_boundary,
    _compact_authority_text,
    _tiny_action_effect,
)


def test_authority_boundary_payload_classifies_hard_gate_before_advisory() -> None:
    payload = _authority_boundary_payload(
        surface="implement.workflow_sufficiency",
        enforced_by_aw=["proof execution evidence before closeout"],
        recommended_by_aw=["inspect changed paths"],
        agent_owned_decisions=["semantic work shape"],
    )

    assert payload["kind"] == "agentic-workspace/authority-boundary/v1"
    assert payload["authority_class"] == "hard-gate"
    assert payload["enforced_by_aw"] == ["proof execution evidence before closeout"]
    assert payload["recommended_by_aw"] == ["inspect changed paths"]
    assert payload["agent_owned_decisions"] == ["semantic work shape"]


def test_tiny_action_effect_preserves_resolution_command_shape() -> None:
    effect = _tiny_action_effect(
        {
            "force": "required_before_claim",
            "allowed_now": "run-proof",
            "blocked_until_reconciled": ["claim-task-complete"],
            "resolution_selector": "proof.required",
            "resolution_command": "make test-workspace",
            "resolution_commands": ["make test-workspace", "make lint-workspace"],
            "extra": "ignored",
        },
        include_allowed=False,
    )

    assert effect == {
        "force": "required_before_claim",
        "blocked_until_reconciled": ["claim-task-complete"],
        "resolution_selector": "proof.required",
        "resolution_command": "make test-workspace",
        "resolution_commands": ["make test-workspace", "make lint-workspace"],
    }


def test_compact_authority_boundary_limits_and_rewrites_authority_text() -> None:
    compact = _compact_authority_boundary(
        {
            "kind": "agentic-workspace/authority-boundary/v1",
            "surface": "planning_safety_gate",
            "authority_class": "advisory-support",
            "enforced_by_aw": ["first", "second", "third"],
            "observed_by_aw": ["observed", "ignored"],
            "recommended_by_aw": ["whether delegation improves quality or cost without lowering proof"],
            "candidate_routes": ["candidate"],
            "agent_owned_decisions": ["whether Planning is needed when no hard blocker applies"],
        }
    )

    assert compact["enforced_by_aw"] == ["first", "second"]
    assert compact["observed_by_aw"] == ["observed"]
    assert compact["recommended_by_aw"] == ["delegation fit without lowering proof"]
    assert compact["agent_owned_decisions"] == ["planning need when no hard blocker applies"]


def test_compact_authority_text_truncates_long_unknown_text() -> None:
    text = "x" * 90

    assert _compact_authority_text(text) == ("x" * 77) + "..."
