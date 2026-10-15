"""Current semantic judgment preserves evidence and Planning authority."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from tests.native_planning_fixtures import fixture_source
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_claim_result_scope_is_distinct_from_instruction_applicability(tmp_path, shared_core_binary, native_cli):
    instruction = tmp_path / ".agentic-workspace/instructions/broad.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths: [src/**]\n---\nPreserve the feature contract.\n")
    result = tmp_path / "src/result.txt"
    result.parent.mkdir()
    result.write_text("result")
    peer = tmp_path / "src/peer.txt"
    peer.write_text("unrelated")
    context = {"target": str(tmp_path), "task": "Review the bounded result", "changed": ["src/result.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    request = call()["verification"]["claim_review"]["request"]
    request["arguments"].update(disposition="satisfied", reason="Checked the current result.", evidence_refs=[])
    proposed = call(request=request)
    binding = proposed["verification"]["claim_review"]["proposal"]["binding"]
    assert set(binding["postimages"]) == {"src/result.txt"}
    assert any(row["source"]["reference"] == ".agentic-workspace/instructions/broad.md" for row in binding["instructions"])
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "confirm"
    peer.write_text("changed unrelated bytes")
    (peer.parent / "new-peer.txt").write_text("new unrelated consumer")
    assert call(request=answer)["verification"]["claim_review"]["status"] == "current"
    for source in (result, instruction):
        original = source.read_bytes()
        source.write_bytes(original + b"\nChanged basis.\n")
        with pytest.raises(AssertionError, match="stale"):
            call(request=answer)
        source.write_bytes(original)
    assert call(request=answer)["verification"]["claim_review"]["status"] == "current"


@pytest.mark.parametrize("binding_assignment", [False, True])
def test_exact_claim_review_needs_current_judgment_not_process_success(tmp_path, shared_core_binary, native_cli, binding_assignment):
    from tests.test_native_proof_producer import fixture

    context = fixture(tmp_path)
    if binding_assignment:
        (tmp_path / ".agentic-workspace/config.local.toml").write_text(
            '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\n'
            '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
        )

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    execute = call()["verification"]["execution_requests"][0]
    proof = call(invocation=call(request=execute)["decision_packet"]["primary_action"], projection="compact")
    assert proof["value"]["claim_boundary"]["completion_claim_allowed"] is False
    continuation = proof["continuation"]["result"]
    step = continuation["verification_context"]["next_step"]
    assert continuation["verification_context"]["evidence"][0]["proof_sufficient"] is True
    discovered = consume("json", shared_core_binary, native_cli, {**proof["continuation"]["context"], "reference": step["reference"]})
    request = discovered["value"]
    assert request["arguments"]["evidence_refs"] == [proof["value"]["publication"]["reference"]]
    assert request["arguments"]["disposition"] == "insufficient"
    proposed = consume(
        "json",
        shared_core_binary,
        native_cli,
        {
            **continuation["reentry"],
            "reference": step["reference"],
            "answer": {"disposition": "satisfied", "reason": "Checked the complete requested behavior and current command evidence."},
        },
    )
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    evidence = decision["material"]["evidence"][0]
    assert evidence["status"] == "admitted"
    assert evidence["admission_scope"] == "selected-command"
    assert evidence["task_judgment"]["status"] == "task-judgment-required"
    assert evidence["gaps"] == []
    assert evidence["limits"] == ["nested-tool-runtime-unobserved"]
    assert decision["material"]["protocol_coverage"]["check"]["status"] == "current-command-evidence-satisfied"
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reentry = [answer]
    if binding_assignment:
        # The existing task-requirements ingress can report work produced outside
        # AW. A real proof and exact claim judgment must not retrospectively
        # manufacture Assignment admission for those already-present bytes.
        external = call()["task_requirements"]["requests"][0]
        external["arguments"]["required_result_classes"] = ["already-materialized"]
        reentry.append(external)
    reviewed = call(request=reentry)
    assert reviewed["verification"]["claim_review"]["status"] == "current", reviewed["verification"]["claim_review"]
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    assert not any(b["code"] == "verification-evidence-unresolved" for b in reviewed["decision_packet"]["blockers"])
    if binding_assignment:
        admission = reviewed["task_requirements"]["implementation_admission"]
        assert admission["status"] == "returned-unadmitted"
        assert admission["historical_compliance"] == "not-established"
        assert admission["result_use_allowed"] is False
        blocker = next(b for b in reviewed["decision_packet"]["blockers"] if b["code"] == "current-binding-assignment-required")
        assert "claim:complete" in blocker["affects"]
        assert "claim:pr-complete" in blocker["affects"]
        assert "effect:implementation" in blocker["affects"]
        assert any(r["owner"] == "assignment" for r in reviewed["consequence_recovery"])
        blocker = next(b for b in reviewed["decision_packet"]["blockers"] if b["code"] == "implementation-result-unadmitted")
        assert {"effect:implementation", "claim:complete", "claim:pr-complete"} <= set(blocker["affects"])
        # No current transport claims it can produce already-materialized work.
        assert reviewed["task_requirements"]["assignment"]["requests"] == []
    (tmp_path / "a.txt").write_text("Changed resulting work")
    with pytest.raises(AssertionError, match="stale"):
        call(request=reentry)


def test_profile_proof_claim_continuation_separates_command_admission_and_protocol_authority(tmp_path, shared_core_binary, native_cli):
    """Join public invocation, automatic receipt carriage and final confirmation.

    A profile's matching command does not acquire the other route's protocol
    authority. Existing linked-route coverage above supplies the positive case.
    """
    (tmp_path / "sample.txt").write_bytes(b"ok")
    aw = tmp_path / ".agentic-workspace"
    (aw / "verification").mkdir(parents=True)
    (aw / "config.toml").write_text('[modules]\nenabled=["verification"]\n')
    command = (
        'Add-Content count.txt executed; if ((Get-Content -Raw sample.txt) -ne "ok") { exit 1 }'
        if os.name == "nt"
        else 'echo executed >> count.txt; test "$(cat sample.txt)" = ok'
    )
    manifest = aw / "verification/manifest.toml"
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[protocols.synthetic_check]\napplies_to_paths=["sample.txt"]\n'
        f'commands=[{json.dumps(command)}]\nproof_profiles=["synthetic_required"]\n'
        "[assurance.proof_profiles.synthetic_required]\n"
        f"required_commands=[{json.dumps(command)}]\n"
        '[assurance.requirements.synthetic_closeout]\nlevel="medium"\n'
        'force="required-before-closeout"\napplies_to_paths=["sample.txt"]\nproof_profile="synthetic_required"\n'
    )
    context = {"target": str(tmp_path), "task": "Validate the synthetic sample and judge the bounded patch", "changed": ["sample.txt"]}

    def call(value):
        result = subprocess.run(
            [str(native_cli), "invoke" if "invocation" in value else "start", "--input", "-", "--format", "json"],
            input=json.dumps({"projection": "full", **value}),
            capture_output=True,
            text=True,
            env={**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)},
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def requests_for(request, route):
        return any(r.get("arguments", {}).get("route_id") == route for r in (request if isinstance(request, list) else [request]))

    initial = call(context)
    execute = next(r for r in initial["verification"]["execution_requests"] if requests_for(r, "profile:synthetic_required"))
    action = call({**context, "request": execute})["decision_packet"]["primary_action"]
    proof = call({**context, "invocation": action, "projection": "compact"})
    assert proof["effect_outcome"]["status"] == "committed"
    assert proof["value"]["process"]["status"] == "passed"
    assert "task_claim_judgment" not in proof["value"]["receipt"]
    subject = proof["value"]["receipt"]["proof_subject"]
    assert subject["identity_complete"] is True
    continuation = proof["continuation"]
    evidence = continuation["result"]["verification_context"]["evidence"][0]
    assert evidence["status"] == "admitted"
    assert evidence["publication_admission"] == "admitted"
    assert evidence["receipt_admission"]["proof_sufficient"] is True
    assert evidence["runtime_admission"] == evidence["freshness"] == "reusable"
    assert evidence["task_judgment"]["classifications"][0]["reasons"] == ["task-claim-judgment-missing"]
    assert evidence["checked_scope"]["claim"] == "selected-command-passed"
    assert evidence["checked_scope"]["command"] == command
    assert evidence["gaps"] == []
    assert evidence["limits"] == ["nested-tool-runtime-unobserved"]
    step = continuation["result"]["verification_context"]["next_step"]
    proposed = call(
        {
            **continuation["context"],
            "reference": step["reference"],
            "answer": {
                "disposition": "satisfied",
                "reason": "The exact sample check passed; separate protocol and setup authority remain binding.",
            },
        }
    )
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    material = decision["material"]
    assert proposed["verification"]["claim_review"]["proposal"]["binding"]["evidence"][0]["proof_subject"] == subject["id"]
    assert material["evidence"][0]["status"] == "admitted"
    assert material["evidence"][0]["claim"] == "selected-command-passed"
    assert material["evidence"][0]["gaps"] == []
    assert material["gaps"] == ["protocol-evidence-required:synthetic_check"]
    assert proposed["verification"]["strategy_control"]["obligations"][0]["status"] == "current-command-evidence-satisfied"
    coverage = material["protocol_coverage"]["synthetic_check"]
    assert coverage["status"] == "command-evidence-required"
    assert coverage["evidence_refs"] == []
    assert coverage["next_requests"]
    assert all(requests_for(r, "protocol:synthetic_check") for r in coverage["next_requests"])
    # The supplied route is executable through the existing selection interface.
    # Do not execute it: identical text supplies no protocol equivalence, and
    # the original committed command must never be rerun for bookkeeping.
    protocol_action = call({**context, "request": coverage["next_requests"][0]})["decision_packet"]["primary_action"]
    assert protocol_action["operation_id"] == "proof.report"
    assert protocol_action["arguments"]["selection"]["strategy"]["route_id"] == "protocol:synthetic_check"
    confirmation = decision["response_request"]
    confirmation["arguments"]["answer"] = "confirm"
    final_input = {**continuation["context"], "request": confirmation}
    confirmed = call(final_input)
    assert any(b["code"] == "configuration-assessment-required" for b in confirmed["decision_packet"]["blockers"])
    final = confirmed["verification"]
    assert final["claim_review"]["status"] == "insufficient"
    assert final["claim_review"]["gaps"] == ["protocol-evidence-required:synthetic_check"]
    assert final["strategy_control"]["obligations"][0]["missing_commands"] == []

    # Source drift invalidates the proposal; changed manifest strategy is refused
    # at the earlier request-currentness layer. Neither path reruns proof.
    (tmp_path / "sample.txt").write_bytes(b"changed")
    with pytest.raises(AssertionError, match="stale"):
        call(final_input)
    (tmp_path / "sample.txt").write_bytes(b"ok")
    original = manifest.read_bytes()
    manifest.write_bytes(
        original.replace(
            f"required_commands=[{json.dumps(command)}]".encode(),
            f'required_commands=[{json.dumps(command)}, "echo additional"]'.encode(),
        )
    )
    stale = call(final_input)["verification"]
    assert stale["claim_review"]["status"] == "not-requested"
    assert "verification-request-stale" in stale["evidence_gaps"]
    assert stale["strategy_control"]["obligations"][0]["missing_commands"] == [command, "echo additional"]
    manifest.write_bytes(original)
    assert call(final_input)["verification"]["evidence"][0]["status"] == "admitted"
    forged = json.loads(json.dumps(final_input))
    forged["request"]["arguments"]["evidence_refs"] = ["proof://local/" + "0" * 64]
    with pytest.raises(AssertionError, match="stale"):
        call(forged)
    assert call(final_input)["verification"]["evidence"][0]["status"] == "admitted"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_claim_review_keeps_planning_subject_and_unfinished_work(tmp_path, shared_core_binary, native_cli):
    import json

    reference = Path(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    original = fixture_source(reference).read_bytes()
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
    continuation = first["planning"]["selection_requests"][0]
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
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    assert "required-review-producer:review" in decision["material"]["gaps"]
    assert decision["material"]["protocol_obligations"]["review"]["review_owner"] == "independent-maintainer"
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "confirm"
    reviewed = call(request=answer)
    assert reviewed["verification"]["claim_review"]["status"] == "insufficient"
    assert "required-review-producer:review" in reviewed["verification"]["claim_review"]["gaps"]
