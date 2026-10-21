"""Current semantic judgment preserves evidence and Planning authority."""

from __future__ import annotations

import base64
import hashlib
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


def test_confirmed_claim_does_not_admit_unexecuted_instruction_check(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_instruction_write import instruction, repo

    repo(tmp_path)
    (tmp_path / "result.txt").write_text("bounded result")
    context = {"target": str(tmp_path), "task": "Judge the bounded result", "changed": ["result.txt"]}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    _, _, action = instruction(
        call,
        ".agentic-workspace/instructions/check.md",
        "---\npaths: [result.txt]\nchecks:\n  - run: echo executed > instruction-ran.txt\n---\nCheck the result.\n",
    )
    call(invocation=action)
    initial = call()["verification"]
    assert initial["instruction_checks"][0]["status"] == "evidence-required"
    assert initial["execution_requests"]
    request = initial["claim_review"]["request"]
    request["arguments"].update(disposition="satisfied", reason="Reviewed the result; the instruction command remains unexecuted.")
    proposed = call(request=request)
    confirmation = next(
        d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review"
    )["response_request"]
    confirmation["arguments"]["answer"] = "confirm"
    confirmed = call(request=confirmation)["verification"]
    assert confirmed["claim_review"]["status"] == "current"
    assert confirmed["instruction_checks"][0]["status"] == "evidence-required"
    assert confirmed["evidence"] == []
    assert confirmed["status"] == "unresolved"
    assert not (tmp_path / "instruction-ran.txt").exists()


@pytest.mark.parametrize("binding_assignment", [False, True])
def test_exact_claim_review_needs_current_judgment_not_process_success(tmp_path, shared_core_binary, native_cli, binding_assignment):
    from tests.test_native_proof_producer import fixture

    context = fixture(tmp_path)
    # Result identity is byte-based even with Planning enabled and no selected
    # plan. Keep one public proof execution for this mixed source set.
    (tmp_path / ".agentic-workspace/config.toml").write_text('[modules]\nenabled=["planning","verification"]\n')
    binary = tmp_path / "sample.png"
    binary.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="))
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"results": "x" * 700_000}))
    context["changed"] += ["sample.png", "report.json"]
    if binding_assignment:
        (tmp_path / ".agentic-workspace/config.local.toml").write_text(
            '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\n'
            '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
        )

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    execute = call()["verification"]["execution_requests"][0]
    proof = call(invocation=call(request=execute)["decision_packet"]["primary_action"], projection="compact")
    assert proof["value"]["claim_boundary"]["completion_claim_allowed"] is False
    continuation = proof["continuation"]["result"]
    assert "next_step" not in continuation["verification_context"]
    step = continuation["verification_context"]["optional_judgment"]
    assert continuation["verification_context"]["evidence"][0]["proof_sufficient"] is True
    discovered = consume(
        "native",
        shared_core_binary,
        native_cli,
        {**proof["continuation"]["context"], "reference": step["reference"]},
        host_path=os.environ["PATH"],
    )
    request = discovered["value"]
    assert request["arguments"]["evidence_refs"] == [proof["value"]["publication"]["reference"]]
    assert request["arguments"]["disposition"] == "insufficient"
    proposed = consume(
        "native",
        shared_core_binary,
        native_cli,
        {
            **continuation["reentry"],
            "reference": step["reference"],
            "answer": {"disposition": "satisfied", "reason": "Checked the complete requested behavior and current command evidence."},
        },
        host_path=os.environ["PATH"],
    )
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    postimages = proposed["verification"]["claim_review"]["proposal"]["binding"]["postimages"]
    for path in (binary, report):
        assert postimages[path.name] == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    # The full request must reach the same proposal as compact claim reentry,
    # carrying the existing receipt rather than executing the check again.
    full_request = call()["verification"]["claim_review"]["request"]
    full_request["arguments"].update(
        disposition="satisfied",
        reason="Checked the complete requested behavior and current command evidence.",
        evidence_refs=decision["response_request"]["arguments"]["evidence_refs"],
    )
    full = call(request=full_request)
    assert full["verification"]["claim_review"]["proposal"] == proposed["verification"]["claim_review"]["proposal"]
    evidence = decision["material"]["evidence"][0]
    assert evidence["status"] == "admitted"
    assert evidence["admission_scope"] == "selected-command"
    assert evidence["task_judgment"]["status"] == "task-judgment-required"
    assert evidence["gaps"] == []
    assert evidence["limits"] == ["nested-tool-runtime-unobserved"]
    assert decision["material"]["protocol_coverage"]["check"]["status"] == "current-command-evidence-satisfied"
    assert proposed["verification"]["evidence"][0]["runtime_admission"]["sufficiency_currentness"] == "current"
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
    for source in (binary, report):
        original = source.read_bytes()
        source.write_bytes(original + b"\n")
        with pytest.raises(AssertionError, match="stale"):
            call(request=reentry)
        source.write_bytes(original)
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
    if not binding_assignment:
        # Reusable command evidence must not acquire an amended protocol's
        # semantics. A fresh judgment over the carried receipt still needs
        # current protocol evidence; the original command is never replayed.
        manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
        original = manifest.read_bytes()
        manifest.write_bytes(original.replace(b"[protocols.check]", b'[protocols.check]\nsteps=["Inspect the amended requirement"]'))
        request = call()["verification"]["claim_review"]["request"]
        request["arguments"].update(
            disposition="satisfied",
            reason="Reuse only the original command observation against the revised requirements.",
            evidence_refs=answer["arguments"]["evidence_refs"],
        )
        revised = call(request=request)
        claim = revised["verification"]["claim_review"]
        evidence = revised["verification"]["evidence"][0]
        assert evidence["status"] == "admitted"
        assert evidence["checked_scope"]["claim"] == "selected-command-passed"
        assert evidence["runtime_admission"]["status"] == "reusable"
        assert evidence["runtime_admission"]["strategy_coverage"] == "selected-command-covered"
        assert evidence["runtime_admission"]["sufficiency_currentness"] == "changed"
        assert claim["protocol_coverage"]["check"]["status"] == "command-evidence-required"
        assert claim["protocol_coverage"]["check"]["next_requests"]
        recovery = claim["protocol_coverage"]["check"]["next_requests"][0]
        selected = call(request=recovery)["decision_packet"]["primary_action"]
        assert selected["arguments"]["selection"]["strategy"]["protocols"]["check"]["steps"] == ["Inspect the amended requirement"]
        # The compiled public decision carries the exact owner confirmation.
        confirmation = next(
            d for d in revised["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review"
        )["response_request"]
        confirmation["arguments"]["answer"] = "confirm"
        final = call(request=confirmation)["verification"]["claim_review"]
        assert final["status"] == "insufficient"
        assert final["gaps"] == ["protocol-evidence-required:check"]
        manifest.write_bytes(original)
        assert call(request=reentry)["verification"]["claim_review"]["status"] == "current"
        assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    (tmp_path / "a.txt").write_text("Changed resulting work")
    with pytest.raises(AssertionError, match="stale"):
        call(request=reentry)


@pytest.mark.parametrize("route", ["profile:synthetic_required", "synthetic_linked", "domain:synthetic_unlinked"])
def test_profile_proof_claim_continuation_separates_command_admission_and_protocol_authority(
    tmp_path, shared_core_binary, native_cli, route
):
    """Join public invocation, automatic receipt carriage and final confirmation.

    Explicit links reuse one execution across its declared requirements. A
    profile-only or unlinked command cannot acquire another protocol's authority.
    """
    linked = route == "synthetic_linked"
    unlinked = route == "domain:synthetic_unlinked"
    (tmp_path / "sample.txt").write_bytes(b"ok")
    aw = tmp_path / ".agentic-workspace"
    (aw / "verification").mkdir(parents=True)
    if not linked:
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
        + (
            f'[proof_routes.synthetic_linked]\nprotocol_refs=["synthetic_check"]\n'
            f'assurance_requirement_refs=["synthetic_closeout"]\ncommands=[{json.dumps(command)}]\n'
            if linked
            else ""
        )
        + (
            f'[assurance.domain_proof_lanes.synthetic_unlinked]\npurpose="Unlinked matching command"\n'
            f'applies_to_paths=["sample.txt"]\ncommands=[{json.dumps(command)}]\n'
            if unlinked
            else ""
        )
    )
    context = {"target": str(tmp_path), "task": "Validate the synthetic sample and judge the bounded patch", "changed": ["sample.txt"]}
    if linked:
        # Aggregate #3895 case: preserve the real binary/large changed scope
        # while one source-linked execution covers profile and assurance.
        (tmp_path / "sample.png").write_bytes(
            base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")
        )
        (tmp_path / "report.json").write_text(json.dumps({"results": "x" * 700_000}))
        context["changed"] += ["sample.png", "report.json"]

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
    execute = next(r for r in initial["verification"]["execution_requests"] if requests_for(r, route))
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
    step = continuation["result"]["verification_context"]["optional_judgment"]
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
    assert material["gaps"] == ([] if linked else ["protocol-evidence-required:synthetic_check"])
    assert proposed["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == ([command] if unlinked else [])
    coverage = material["protocol_coverage"]["synthetic_check"]
    assert coverage["status"] == ("current-command-evidence-satisfied" if linked else "command-evidence-required")
    assert bool(coverage["evidence_refs"]) is linked
    assert bool(coverage["next_requests"]) is not linked
    assert all(requests_for(r, "protocol:synthetic_check") for r in coverage["next_requests"])
    # The supplied route is executable through the existing selection interface.
    # Do not execute it: identical text supplies no protocol equivalence, and
    # the original committed command must never be rerun for bookkeeping.
    if not linked:
        protocol_action = call({**context, "request": coverage["next_requests"][0]})["decision_packet"]["primary_action"]
        assert protocol_action["operation_id"] == "proof.report"
        assert protocol_action["arguments"]["selection"]["strategy"]["route_id"] == "protocol:synthetic_check"
    confirmation = decision["response_request"]
    confirmation["arguments"]["answer"] = "confirm"
    final_input = {**continuation["context"], "request": confirmation}
    confirmed = call(final_input)
    if not linked:
        assert any(b["code"] == "configuration-assessment-required" for b in confirmed["decision_packet"]["blockers"])
    final = confirmed["verification"]
    assert final["claim_review"]["status"] == ("current" if linked else "insufficient")
    assert final["claim_review"]["gaps"] == ([] if linked else ["protocol-evidence-required:synthetic_check"])
    assert final["strategy_control"]["obligations"][0]["missing_commands"] == ([command] if unlinked else [])
    if linked:
        assert final["status"] == "current", final
        assert final["assurance_owner_gaps"] == []
        assert final["evidence_gaps"] == []
        assert confirmed["decision_packet"]["blockers"] == []
        assert final["strategy_control"]["obligations"][0]["evidence_refs"] == [proof["value"]["publication"]["reference"]]
        # A distinct source-required reviewer remains a real blocker even
        # though the command and the agent's semantic judgment are current.
        original = manifest.read_bytes()
        manifest.write_bytes(
            original.replace(
                b'proof_profile="synthetic_required"',
                b'proof_profile="synthetic_required"\nreview_owner="independent-maintainer"',
            )
        )
        request = call(context)["verification"]["claim_review"]["request"]
        request["arguments"].update(
            disposition="satisfied",
            reason="The result and command are checked; independent reviewer authority remains outstanding.",
            evidence_refs=confirmation["arguments"]["evidence_refs"],
        )
        extra = call({**context, "request": request})
        choice = next(d for d in extra["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
            "response_request"
        ]
        choice["arguments"]["answer"] = "confirm"
        pending = call({**context, "request": choice})
        assert pending["verification"]["claim_review"]["status"] == "current"
        assert pending["verification"]["strategy_control"]["obligations"][0]["missing_commands"] == []
        assert pending["verification"]["assurance_owner_gaps"][0]["missing_admissions"] == ["required-reviewer-result-not-admitted"]
        assert pending["verification"]["assurance_owner_gaps"][0]["recovery"]["status"] == "owner-resolution-unavailable"
        assert pending["verification"]["assurance_owner_gaps"][0]["recovery"]["required_owner"] == "independent-maintainer"
        assert any(b["code"] == "assurance:synthetic_closeout:applicable" for b in pending["decision_packet"]["blockers"])
        manifest.write_bytes(original)

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
    if linked:
        # The prior confirmation is stale, but adding a separate command must
        # not discard current evidence for the unchanged source-linked command.
        fresh = call(context)["verification"]["claim_review"]["request"]
        fresh["arguments"].update(
            disposition="insufficient",
            reason="The added command remains unproved; reuse only the existing command observation.",
            evidence_refs=confirmation["arguments"]["evidence_refs"],
        )
        expanded = call({**context, "request": fresh})["verification"]
        assert expanded["strategy_control"]["obligations"][0]["missing_commands"] == ["echo additional"]
    manifest.write_bytes(original)
    assert call(final_input)["verification"]["evidence"][0]["status"] == "admitted"
    forged = json.loads(json.dumps(final_input))
    forged["request"]["arguments"]["evidence_refs"] = ["proof://local/" + "0" * 64]
    with pytest.raises(AssertionError, match="stale"):
        call(forged)
    assert call(final_input)["verification"]["evidence"][0]["status"] == "admitted"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]


def test_protocol_recovery_bounds_presentation_without_hiding_source_alternatives(tmp_path, shared_core_binary, native_cli):
    (tmp_path / "a.txt").write_text("current source")
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir(parents=True)
    protocol_ids = [f"check_{i:02}" for i in range(8)]
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        + "".join(
            f'[protocols.{name}]\napplies_to_paths=["a.txt"]\ncommands='
            + json.dumps([f"echo {name}-choice-{choice:02}" for choice in range(80)])
            + "\n"
            for name in protocol_ids
        )
    )
    context = {"target": str(tmp_path), "task": "Judge current protocol coverage with many source alternatives", "changed": ["a.txt"]}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    initial = call()
    request = initial["verification"]["claim_review"]["request"]
    request["arguments"].update(disposition="satisfied", reason="Inspect all current source obligations before any execution.")
    proposed = call(request=request)
    claim = proposed["verification"]["claim_review"]
    coverage = claim["protocol_coverage"]
    offered = [request for row in coverage.values() for request in row["next_requests"]]
    assert len(offered) == 1
    assert len(json.dumps(offered).encode()) < 8192
    assert set(coverage) == set(protocol_ids)
    assert all(row["status"] == "command-evidence-required" for row in coverage.values())
    assert sum(row["omitted_request_count"] for row in coverage.values()) == 639
    assert len(proposed["verification"]["execution_requests"]) == 640
    decision = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")
    assert decision["material"]["gaps"] == [f"protocol-evidence-required:{name}" for name in protocol_ids]
    compact = call(request=request, projection="compact")
    compact_decision = next(
        d
        for d in [compact["decision_packet"]["decision_request"], *compact["decision_packet"]["pending_consequences"]["decisions"]]
        if d and d["id"] == "verification-claim-review"
    )
    assert compact_decision["material"]["protocol_coverage"] == coverage
    detail = consume(
        "native",
        shared_core_binary,
        native_cli,
        {**compact["reentry"], "reference": compact["detail_refs"]["/verification"]},
        host_path=os.environ["PATH"],
    )
    assert len(detail["value"]["execution_requests"]) == 640
    assert call(request=offered[0])["decision_packet"]["primary_action"]["operation_id"] == "proof.report"
    # The bounded offer is a candidate, not the sole authorised choice. The last
    # omitted source alternative remains selectable under unchanged authority.
    last = proposed["verification"]["execution_requests"][-1]
    selected = call(request=last)["decision_packet"]["primary_action"]
    assert selected["arguments"]["selection"]["choice"] == {"route_id": "protocol:check_07", "command": "echo check_07-choice-79"}
    # An oversized first candidate is left at the owner, rather than expanding
    # the semantic answer or constructing a replacement catalogue to find one.
    manifest.write_text(manifest.read_text().replace(json.dumps("echo check_00-choice-00"), json.dumps("echo " + "x" * 8100)))
    enlarged = call()
    request = enlarged["verification"]["claim_review"]["request"]
    request["arguments"].update(disposition="satisfied", reason="Keep oversized recovery at its current source owner.")
    bounded = call(request=request)["verification"]
    coverage = bounded["claim_review"]["protocol_coverage"]
    assert all(row["next_requests"] == [] for row in coverage.values())
    assert sum(row["omitted_request_count"] for row in coverage.values()) == 640
    assert len(bounded["execution_requests"]) == 640
    assert not (tmp_path / ".agentic-workspace/local/proof-receipts").exists()


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
        'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.review]\napplies_to_paths=["a.txt"]\nreview_owner="independent-maintainer"\nindependent_required=true\ncommands=[]\n[proof_routes]\n'
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
    required = next(b for b in reviewed["decision_packet"]["blockers"] if b["code"] == "protocol-review-required:review")
    assert required["basis"]["kind"] == "attestation-limit" and required["affects"] == ["attestation:verification"]
    # Reviewer identity alone is metadata, not a second review certificate.
    # External approval remains governed by the repository's actual review policy;
    # the native judgment grants no independent approval, before or after review.
    manifest.write_text(manifest.read_text().replace("independent_required=true\n", ""))
    fresh = call()["verification"]["claim_review"]["request"]
    fresh["arguments"].update(disposition="satisfied", reason="Command-free task inspected; independent approval is a separate stage.")
    proposal = call(request=fresh)
    choice = next(d for d in proposal["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
        "response_request"
    ]
    assert (
        "required-review-producer:review"
        not in next(d for d in proposal["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "verification-claim-review")[
            "material"
        ]["gaps"]
    )
    choice["arguments"]["answer"] = "confirm"
    completed = call(request=choice)
    assert completed["verification"]["claim_review"]["status"] == "current"
    assert all("claim:complete" not in b["affects"] for b in completed["decision_packet"]["blockers"])
