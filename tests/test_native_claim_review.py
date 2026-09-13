"""Current semantic judgment preserves evidence and Planning authority."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_exact_claim_review_needs_current_judgment_not_process_success(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_proof_producer import fixture

    context = fixture(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    execute = call()["verification"]["execution_requests"][0]
    proof = call(invocation=call(request=execute)["decision_packet"]["primary_action"])
    assert proof["value"]["claim_boundary"]["completion_claim_allowed"] is False
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "disposition": "satisfied",
        "reason": "Checked the complete requested behavior and current command evidence.",
        "evidence_refs": [proof["value"]["publication"]["reference"]],
    }
    proposed = call(request=request)
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "current", reviewed["verification"]["claim_review"]
    assert not any(b["code"] == "verification-evidence-unresolved" for b in reviewed["decision_packet"]["blockers"])
    (tmp_path / "a.txt").write_text("Changed resulting work")
    with pytest.raises(AssertionError, match="stale"):
        call(request=answer)


def test_claim_review_keeps_planning_subject_and_unfinished_work(tmp_path, shared_core_binary, native_cli):
    import json

    from tests.test_native_public_cli import ROOT

    reference = Path(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    original = (ROOT / reference).read_bytes()
    plan.write_bytes(original)
    identity = json.loads(original)["id"]
    (plan.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="{identity}"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    (tmp_path / "a.txt").write_text("current source")
    context = {"target": str(tmp_path), "task": "Review exact progress without completing the lane", "changed": ["a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    continuation = first["planning"]["requests"][0]
    call(invocation=call(request=continuation)["decision_packet"]["primary_action"])
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "disposition": "satisfied",
        "reason": "Reviewed the exact selected progress; durable work remains open.",
        "evidence_refs": [],
    }
    proposed = call(request=request)
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "current"
    assert reviewed["verification"]["claim_review"]["claim"]["subject"]["id"] == reviewed["verification"]["judgment_request"]["work_ref"]
    assert reviewed["verification"]["claim_review"]["claim"]["subject"]["id"].startswith("planning:sha256:")
    assert reviewed["decision_packet"]["status"] != "terminal"
    assert plan.read_bytes() == original


def test_claim_review_cannot_impersonate_required_reviewer(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Review scoped work", "changed": ["a.txt"]}
    (tmp_path / "a.txt").write_text("source")

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.review]\napplies_to_paths=["a.txt"]\nreview_owner="independent-maintainer"\n[proof_routes]\n'
    )
    request = call()["verification"]["claim_review"]["request"]
    request["arguments"] = {
        "reason": "A semantic assertion cannot impersonate the required reviewer.",
        "disposition": "satisfied",
        "evidence_refs": [],
    }
    proposed = call(request=request)
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "insufficient"
    assert "required-review-producer:review" in reviewed["verification"]["claim_review"]["gaps"]
