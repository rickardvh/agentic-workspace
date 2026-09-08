"""Common action dependencies retain source requests without creating authority."""

from copy import deepcopy
from pathlib import Path

import pytest
from tests.test_shared_core import VECTORS, _compile, _expanded

from agentic_workspace.decision import DecisionContractError, admit_invocation


def test_source_dependencies_preserve_old_actions_and_reject_stale_requests(shared_core_binary: Path) -> None:
    payload = _expanded(next(v["input"] for v in VECTORS["cases"] if v["id"] == "typed-public-request-returns-an-exact-owner-action"))
    owner = payload["contributions"][0]
    owner.pop("request_response", None)
    request = payload["intent"].pop("public_request")
    baseline = _compile(payload)
    original = baseline["primary_action"]
    assert "source_requests" not in original
    owner["actions"][0]["source_requests"] = []
    assert _compile(payload) == baseline
    owner["actions"][0]["source_requests"] = [request]
    current = _compile(payload)
    action = current["primary_action"]
    assert action["source_requests"] == [request]
    assert action["idempotency_key"] == original["idempotency_key"]
    assert action["expected_dependency_revision"] != original["expected_dependency_revision"]
    assert admit_invocation(current, action)["disposition"] == "execute"
    with pytest.raises(DecisionContractError, match="stale"):
        admit_invocation(current, original)
    for key in ("owner_revision", "capability_revision", "task_identity"):
        invalid = deepcopy(payload)
        invalid["contributions"][0]["actions"][0]["source_requests"][0][key] = "stale"
        with pytest.raises(DecisionContractError):
            _compile(invalid)
    owner["actions"][0]["source_requests"] = [request, request]
    with pytest.raises(DecisionContractError, match="duplicate"):
        _compile(payload)
