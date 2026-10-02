"""Complete manual snapshot and owner-held return after initiating chat is lost."""

from __future__ import annotations

import copy
import json
import subprocess

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize(
    "human,producer,partial",
    [
        (False, "agent", False),
        (True, "agent", False),
        (True, "human", False),
        (False, "agent", True),
    ],
)
def test_manual_snapshot_fresh_return_and_authority(tmp_path, shared_core_binary, native_cli, human, producer, partial):
    config = tmp_path / ".agentic-workspace/config.local.toml"
    config.parent.mkdir()
    (config.parent / "config.toml").write_text('[modules]\nenabled=["verification"]\n')
    config.write_text(
        '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n'
        'required_execution_guarantees=["recipient-workflow"]\n'
        '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
        '[delegation_targets.specialist]\nexecution_guarantees=["recipient-workflow"]\ntransports=[{kind="manual"}]\n'
        + ('owner_kind="human"\ntarget_id="policy-owner"\n' if human else "")
    )
    source = tmp_path / "policy.txt"
    content = "A loan lasts 14 days. One renewal is allowed when nobody has reserved the book.\n" + "Context line.\n" * 1000
    source.write_bytes(content.encode("utf-8"))
    task = "Explain the library loan and renewal rules using only the supplied policy."
    context = {"target": str(tmp_path), "task": task, "changed": []}

    def call(request=None, invocation=None, **updates):
        return consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                **context,
                **updates,
                **({"request": request} if request is not None else {}),
                **({"invocation": invocation} if invocation is not None else {}),
            },
        )

    def worker(action, packet, **other):
        result = subprocess.run(
            [str(native_cli), "worker", "--input", "-", "--format", "json"],
            input=json.dumps({"action": action, "packet": packet, **other}),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    requirements = call()["task_requirements"]["requests"][0]
    requirements["arguments"]["required_result_classes"] = ["read-only"]
    inputs = call(requirements)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(
        input_refs=["policy.txt"],
        complete=False,
        reason="The recipient may receive this synthetic policy; it supplies the complete task context.",
    )
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    assigned = call(inputs)
    assert assigned["task_requirements"]["assignment"]["result"]["judgment"] is None
    export = assigned["task_requirements"]["handoff"]["requests"][0]
    exported = call(export)
    packet = exported["task_requirements"]["handoff"]["packet"]
    presentation = exported["task_requirements"]["handoff"]["manual_presentation"]
    assert presentation == worker("manual", packet)
    assert presentation["recipient_kind"] == ("human" if human else "agent")
    assert presentation["view"]["inputs"]["capsule"][0]["content"] == content
    assert content in presentation["prompt"].replace("\\n", "\n")
    assert "required-lazy" not in presentation["prompt"]
    assert "packet_integrity" not in presentation["prompt"] and '"request"' not in presentation["prompt"]
    assert not presentation["delivery_observed"] and not presentation["execution_observed"]
    retention = exported["task_requirements"]["delegation"]["requests"][0]
    retain_action = call(retention)["decision_packet"]["primary_action"]
    assert retain_action["operation_id"] == "delegation.record-manual"
    retained = call(invocation=retain_action)
    assert retained["status"] == "applied"
    assert call(invocation=retain_action)["value"] == retained["value"]
    assert not (config.parent / "planning").exists()
    assert "retirement" not in call()["task_requirements"]["delegation"]

    # Discard all initiating packet/request context. The native owner locates
    # only this task's retained continuation, without consulting parent chat.
    del requirements, inputs, assigned, export, exported, packet, retention, presentation
    fresh = call()["task_requirements"]["delegation"]["manual_continuation"]
    assert fresh["status"] == "exported"
    assert call(fresh["reentry"]["request"])["task_requirements"]["handoff"]["packet"] == fresh["packet"]
    assert call(task="Unrelated independent work")["task_requirements"]["delegation"].get("manual_continuation") is None
    material = {
        "summary": "A loan lasts 14 days. One renewal is allowed only when no reservation exists.",
        "changed_paths": [],
        "patch": "",
        "stop_conditions_hit": [],
    }
    if partial:
        material["stop_conditions_hit"] = ["An additional renewal duration rule is missing."]
    with pytest.raises(AssertionError, match="immutable identity"):
        worker("return", fresh["packet"], material={**material, "target": "another-target"})
    wrapped = worker("return", fresh["packet"], material=material)
    wrong = copy.deepcopy(wrapped["reentry"]["request"])
    wrong[-1]["arguments"]["returned"]["target"] = "wrong"
    with pytest.raises(AssertionError, match="match current sealed"):
        call(wrong)
    observed = call(wrapped["reentry"]["request"])
    assert observed["task_requirements"]["assignment"]["result_admission"]["status"] == "not-ready"
    report = observed["task_requirements"]["delegation"]["requests"][0]
    report[-1]["arguments"] = {
        "producer_kind": producer,
        "reported_delivery": True,
        "reported_execution": True,
        "provenance": "A synthetic pasted external-model answer; model/product identity is unverified.",
    }
    report_action = call(report)["decision_packet"]["primary_action"]
    reported = call(invocation=report_action)
    assert reported["value"]["status"] == "reported"
    assert not reported["value"]["execution_observed"]
    assert call(invocation=report_action)["value"] == reported["value"]
    if not human and not partial:
        # The owner retained a future commit before publication. A lost local
        # commit is recoverable from a fresh context without repeating work.
        pointer = next((config.parent / "local/delegation-manual").glob("*.json"))
        link = json.loads(pointer.read_bytes())
        terminal = next(
            p
            for p in (config.parent / "local/delegation-runs").glob("*.terminal.json")
            if json.loads(p.read_bytes())["custody"] == link["custody"]
        )
        link["terminal"] = terminal.relative_to(tmp_path).as_posix()
        pointer.write_text(json.dumps(link))
        (tmp_path / link["custody"]["committed"]["path"]).unlink()
        recovery = call()["task_requirements"]["delegation"]["manual_continuation"]
        assert recovery["status"] == "carriage-recovery-required"
        assert call(invocation=recovery["recovery_invocation"])["value"] == reported["value"]
    fresh = call()["task_requirements"]["delegation"]["manual_continuation"]
    assert fresh["status"] == "reported"
    judgment = call(fresh["reentry"]["request"])["task_requirements"]["assignment"]["result_admission"]["requests"][0]
    judgment[-1]["arguments"] = {"answer": "use-result", "reason": "The new analysis matches the supplied policy."}
    human_unsatisfied = human and producer != "human"
    if human_unsatisfied:
        with pytest.raises(AssertionError, match="Human-owned work"):
            call(judgment)
        judgment[-1]["arguments"] = {
            "answer": "repair-required",
            "reason": "The selected owner must supply human-produced work; an external model cannot substitute.",
        }
    admitted = call(judgment)
    admission = admitted["task_requirements"]["assignment"]["result_admission"]
    expected = "repair-required" if human_unsatisfied else "admitted-partial-observation" if partial else "admitted-for-use"
    assert admission["status"] == expected
    assert admission["result_use_allowed"] is (not human_unsatisfied and not partial)
    assert not any(admission["claim_boundary"].values())
    settlement = admitted["task_requirements"]["delegation"]["settlement_requests"][0]
    settled = call(invocation=call(settlement)["decision_packet"]["primary_action"])
    assert settled["value"]["status"] == admission["status"]
    assert call()["task_requirements"]["delegation"]["manual_continuation"]["status"] == admission["status"]
    if partial:
        # A newer snapshot cannot erase the pending partial assignment.
        assert "retirement" not in call()["task_requirements"]["delegation"]
        source.write_text("Changed policy.\n")
        requirements = call()["task_requirements"]["requests"][0]
        requirements["arguments"]["required_result_classes"] = ["read-only"]
        inputs = call(requirements)["task_requirements"]["handoff_inputs"]["requests"][0]
        inputs[-1]["arguments"].update(
            input_refs=["policy.txt"],
            complete=False,
            reason="The changed synthetic policy is sufficient and authorised for this recipient.",
        )
        inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
        inputs[-1]["arguments"]["complete"] = True
        replacement = call(inputs)["task_requirements"]["handoff"]["requests"][0]
        pending = call(replacement)["task_requirements"]["delegation"]
        assert pending["status"] == "prior-manual-disposition-required"
        disposal = pending["requests"][0]
        disposal[-1]["arguments"]["reason"] = (
            "Preserve the old partial observation as historical; the changed source requires new bounded work. External execution is not inferred or repeated."
        )
        action = call(disposal)["decision_packet"]["primary_action"]
        disposed = call(invocation=action)
        assert disposed["value"]["status"] == "disposed"
        assert call(invocation=action)["value"] == disposed["value"]
    source.write_text("Changed policy.\n")
    with pytest.raises(AssertionError, match="changed|stale"):
        call(judgment)
    assert call()["task_requirements"]["delegation"]["manual_continuation"]["status"] == ("disposed" if partial else admission["status"])

    def retire_current():
        retirement = call()["task_requirements"]["delegation"]["retirement"]["requests"][0]
        retirement["arguments"]["reason"] = (
            "The original owner no longer needs this synthetic material; no pending work or evidence references remain."
        )
        held = call(retirement)["task_requirements"]["delegation"]["retirement"]
        assert held["status"] == "retirement-held-by-disposition"
        for pending_work, evidence_needed in ((False, True), (True, False)):
            retirement["arguments"].update(pending_work=pending_work, evidence_needed=evidence_needed)
            held = call(retirement)["task_requirements"]["delegation"]["retirement"]
            assert held["status"] == "retirement-held-by-disposition"
        retirement["arguments"].update(pending_work=False, evidence_needed=False)
        current = call(retirement)
        action = next(a for a in current["decision_packet"]["ready_actions"] if a["operation_id"] == "delegation.retire-manual")
        files = action["arguments"]["files"]
        # Changed evidence invalidates the exact deletion set, before any removal.
        victim = tmp_path / files[0]["path"]
        original = victim.read_bytes()
        victim.write_bytes(original + b" ")
        with pytest.raises(AssertionError, match="custody|evidence|changed"):
            call(invocation=action)
        assert all((tmp_path / f["path"]).exists() for f in files)
        victim.write_bytes(original)
        retired = call(invocation=action)
        assert retired["value"]["status"] == "retired"
        assert not any((tmp_path / f["path"]).exists() for f in files)
        assert call(invocation=action)["value"] == retired["value"]
        assert call()["task_requirements"]["delegation"]["manual_continuation"]["status"] == "retired"
        return retired

    unknown = config.parent / "local/delegation-runs/unknown.keep"
    unknown.write_bytes(b"Unrelated material must be preserved.")
    retired = retire_current()
    assert unknown.read_bytes() == b"Unrelated material must be preserved."
    if not human and not partial:
        # All original snapshots are already gone. Withhold the local cleanup
        # commit and recover from its small, exact owner journal in a fresh turn.
        pointer = next((config.parent / "local/delegation-manual").glob("*.json"))
        link = json.loads(pointer.read_bytes())
        link["status"] = "retiring"
        link["custody"]["committed"] = None
        pointer.write_text(json.dumps(link))
        (tmp_path / link["planned_custody"]["committed"]["path"]).unlink()
        original_link = pointer.read_bytes()
        link["invocation"]["arguments"]["files"][0]["path"] = ".agentic-workspace/local/delegation-runs/unknown.keep"
        pointer.write_text(json.dumps(link))
        with pytest.raises(AssertionError, match="custody|differs"):
            call()
        assert unknown.read_bytes() == b"Unrelated material must be preserved."
        pointer.write_bytes(original_link)
        recovery = call()["task_requirements"]["delegation"]["retirement"]["recovery_invocation"]
        assert call(invocation=recovery)["value"] == retired["value"]

        # Repeat distinct assignments for the same direct task. Each lifecycle
        # retires its full snapshots and its predecessor's small cleanup receipt.
        for index in range(2):
            source.write_bytes((f"Current loan duration: {21 + index} days.\n" + "Context line.\n" * 1000).encode())
            requirements = call()["task_requirements"]["requests"][0]
            requirements["arguments"]["required_result_classes"] = ["read-only"]
            inputs = call(requirements)["task_requirements"]["handoff_inputs"]["requests"][0]
            inputs[-1]["arguments"].update(
                input_refs=["policy.txt"], complete=False, reason="This synthetic snapshot supplies the complete authorised context."
            )
            inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
            inputs[-1]["arguments"]["complete"] = True
            export = call(inputs)["task_requirements"]["handoff"]["requests"][0]
            offered = call(export)
            retention = offered["task_requirements"]["delegation"]["requests"][0]
            call(invocation=call(retention)["decision_packet"]["primary_action"])
            packet = call()["task_requirements"]["delegation"]["manual_continuation"]["packet"]
            wrapped = worker(
                "return",
                packet,
                material={
                    "summary": f"The current loan duration is {21 + index} days.",
                    "patch": "",
                    "changed_paths": [],
                    "stop_conditions_hit": [],
                },
            )
            report = call(wrapped["reentry"]["request"])["task_requirements"]["delegation"]["requests"][0]
            report[-1]["arguments"] = {
                "producer_kind": "agent",
                "reported_delivery": True,
                "reported_execution": True,
                "provenance": "Synthetic explicitly reported material.",
            }
            call(invocation=call(report)["decision_packet"]["primary_action"])
            fresh = call()["task_requirements"]["delegation"]["manual_continuation"]
            judgment = call(fresh["reentry"]["request"])["task_requirements"]["assignment"]["result_admission"]["requests"][0]
            judgment[-1]["arguments"] = {"answer": "use-result", "reason": "The new material matches the captured policy."}
            settlement = call(judgment)["task_requirements"]["delegation"]["settlement_requests"][0]
            call(invocation=call(settlement)["decision_packet"]["primary_action"])
            retire_current()
            residue = [
                *pointer.parent.glob("*.json"),
                *(config.parent / "local/effects").glob("*.json"),
                *(config.parent / "local/delegation-runs").glob("manual-*.json"),
            ]
            assert len(residue) == 3
            assert sum(p.stat().st_size for p in residue) < 30_000
            assert all(b"Context line." not in p.read_bytes() for p in residue)
            assert unknown.read_bytes() == b"Unrelated material must be preserved."
