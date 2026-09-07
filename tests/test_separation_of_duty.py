"""Identity uncertainty must not become evidence of independent review."""

import json
import subprocess
from pathlib import Path

import pytest

from agentic_workspace.workspace_runtime_proof import _separation_of_duty_gate


def test_independent_node_and_json_consume_same_separation_owner(shared_core_binary):
    root = Path(__file__).resolve().parents[1]
    module = (root / "bindings/node/semantic-decision.mjs").as_uri()
    for reviewer, expected in [("unknown", "blocked"), ("reviewer", "satisfied")]:
        context = {"required_mode": "separate-actor", "implementer": {"actor_id": "executor"}, "reviewer": {"actor_id": reviewer}}
        direct = subprocess.run(
            [str(shared_core_binary)], input=json.dumps({"separation_of_duty": context}), text=True, capture_output=True, check=True
        )
        node = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                f"import {{separationOfDuty}} from {json.dumps(module)}; console.log(JSON.stringify(separationOfDuty(JSON.parse(process.argv[1]))));",
                json.dumps(context),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        assert json.loads(direct.stdout) == json.loads(node.stdout) == _separation_of_duty_gate(**context)
        assert json.loads(direct.stdout)["status"] == expected


@pytest.mark.parametrize("mode", ["separate-actor", "distinct-provider", "human"])
@pytest.mark.parametrize("missing", [None, "", " ", "unknown"])
@pytest.mark.parametrize("side", ["implementer", "reviewer"])
def test_missing_identity_never_establishes_separation(mode, missing, side):
    actors = {
        "implementer": {"actor_id": "executor", "provider": "one"},
        "reviewer": {"actor_id": "reviewer", "provider": "two", "role": "human-approver"},
    }
    actors[side]["actor_id"] = missing
    assert _separation_of_duty_gate(required_mode=mode, **actors)["status"] == "blocked"


@pytest.mark.parametrize(
    ("mode", "reviewer", "expected"),
    [
        ("none", None, "not-applicable"),
        ("", None, "not-applicable"),
        ("not-applicable", None, "not-applicable"),
        ("separate-actor", None, "required"),
        ("separate-actor", {"role": "reviewer"}, "blocked"),
        ("separate-actor", {"actor_id": "executor"}, "blocked"),
        ("separate-actor", {"actor_id": "other"}, "satisfied"),
        ("distinct-provider", {"actor_id": "other"}, "blocked"),
        ("distinct-provider", {"actor_id": "other", "provider": "one"}, "blocked"),
        ("distinct-provider", {"actor_id": "other", "provider": "two"}, "satisfied"),
        ("human", {"actor_id": "other", "role": "human-approver"}, "satisfied"),
        ("human", {"actor_id": "other", "role": "reviewer"}, "blocked"),
        ("fresh-context", {"actor_id": "executor", "fresh_context": True}, "satisfied"),
        ("fresh-context", {"actor_id": "other", "fresh_context": False}, "blocked"),
        ("fresh-context", {"actor_id": "other", "fresh_context": "false"}, "blocked"),
        ("invented", {"actor_id": "other"}, "blocked"),
    ],
)
def test_each_existing_mode_has_its_own_evidence_requirement(mode, reviewer, expected):
    result = _separation_of_duty_gate(required_mode=mode, implementer={"actor_id": "executor", "provider": "one"}, reviewer=reviewer)
    assert result["status"] == expected


def test_original_missing_actor_counterexample_is_blocked():
    assert _separation_of_duty_gate(required_mode="separate-actor", implementer={}, reviewer={"role": "reviewer"})["status"] == "blocked"
