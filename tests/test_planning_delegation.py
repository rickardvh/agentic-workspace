from agentic_workspace.memory_effectiveness import memory_effectiveness_operation


def test_canonical_planning_delegation_requires_matching_typed_contract() -> None:
    record = {
        "relationships": {"delegation": {"state": "recorded", "route": "keep-local"}},
        "specialist_contracts": [{"kind": "planning-delegation/v1", "target": "planning://delegation/keep-local", "revision": 1}],
    }

    assert memory_effectiveness_operation(operation="canonical-planning-delegation", packet=record) == {
        "status": "recorded",
        "route chosen": "keep-local",
        "canonical contract": True,
    }


def test_canonical_planning_delegation_rejects_unmatched_contract() -> None:
    record = {
        "relationships": {"delegation": {"state": "recorded", "route": "keep-local"}},
        "specialist_contracts": [{"kind": "planning-delegation/v1", "target": "planning://delegation/delegate", "revision": 1}],
    }

    assert memory_effectiveness_operation(operation="canonical-planning-delegation", packet=record) == {}
