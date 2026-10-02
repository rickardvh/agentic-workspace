"""A failed native check can be investigated without turning analysis into proof."""

from __future__ import annotations

import copy
import json
import os
import shlex
import sys

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_failed_check_to_source_derived_analysis_without_planning(tmp_path, shared_core_binary, native_cli):
    config = tmp_path / ".agentic-workspace/config.local.toml"
    config.parent.mkdir()
    (config.parent / "config.toml").write_text('[modules]\nenabled=["verification"]\n')
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json,sys\np=json.load(sys.stdin)\nw=p['worker_context']['inputs']['source_work']\n"
        "assert w['producer']=='verification' and w['accepted_context']['result']=='failed'\n"
        "assert 'execute-commands' in p['assignment_identity']['prohibited_effects']\n"
        "assert any('expected 2, received 1' in i['content'] for i in p['worker_context']['inputs']['capsule'])\n"
        "print(json.dumps({**p['return_contract']['required_identity'],"
        "'kind':'agentic-workspace/delegated-return/v1','result_delivery':'unapplied-patch',"
        "'summary':'The check expected 2 but received 1. Compare the implementation with the required value; rerun through Verification after a separately scoped repair.',"
        "'patch':'','changed_paths':[],'stop_conditions_hit':[]}))\n"
    )
    config.write_text(
        "[safety]\nsafe_to_auto_run_commands=true\n[delegation]\n"
        'assignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="automatic"\n'
        'required_execution_guarantees=["bounded-analysis"]\n'
        '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
        '[delegation_targets.worker]\nexecution_guarantees=["bounded-analysis"]\n'
        'transports=[{kind="process",command=' + json.dumps([sys.executable, str(worker)]) + ",timeout_seconds=30}]\n"
    )
    (tmp_path / "check.py").write_text(
        "from pathlib import Path\np=Path('count.txt')\np.write_text(p.read_text()+'run\\n' if p.exists() else 'run\\n')\n"
        "print('expected 2, received 1')\nraise SystemExit(1)\n"
    )
    executable = "& '" + sys.executable.replace("'", "''") + "'" if os.name == "nt" else shlex.quote(sys.executable)
    manifest = config.parent / "verification/manifest.toml"
    manifest.parent.mkdir()
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[protocols.check]\napplies_to_paths=["check.py"]\n'
        '[protocols.check.analysis]\nquestion="Explain the exact mismatch and identify the next supported check or repair decision."\n'
        'input_refs=["check.py"]\nstop_conditions=["Do not infer absent requirements or run commands."]\n'
        '[proof_routes.check]\nprotocol_refs=["check"]\ncommands=[' + json.dumps(executable + " check.py") + "]\n"
    )
    context = {"target": str(tmp_path), "task": "Investigate the selected failing check", "changed": ["check.py"]}

    def call(request=None, invocation=None):
        return consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                **context,
                **({"request": request} if request is not None else {}),
                **({"invocation": invocation} if invocation is not None else {}),
            },
            host_path=os.environ["PATH"],
        )

    first = call()
    proof = call(first["verification"]["execution_requests"][0])["decision_packet"]["primary_action"]
    assert proof["operation_id"] == "proof.report"
    checked = call(invocation=proof)
    assert checked["value"]["process"]["status"] == "failed"
    assert call(invocation=proof)["value"] == checked["value"]
    assert (tmp_path / "count.txt").read_text() == "run\n"
    requirement = call()["task_requirements"]["verification_requirements"]["request"]
    requirement["arguments"].update(
        obligation_ref=".agentic-workspace/verification/manifest.toml#protocols.check",
        analysis_receipt_ref=checked["value"]["publication"]["reference"],
    )
    derived = call(requirement)["task_requirements"]
    assert derived["result"]["status"] == "resolved"
    assert derived["source_work"]["status"] == "ready"
    assert len(derived["source_work"]["definition"]["input_refs"]) == 2
    inputs = derived["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    offered = call(inputs)
    choice = next(
        r for r in offered["task_requirements"]["execution_configurations"]["requests"] if r[-1]["arguments"]["candidate"] == "worker:cli"
    )
    assigned = call(choice)
    assert assigned["task_requirements"]["assignment"]["result"]["judgment"] is None
    export = assigned["task_requirements"]["handoff"]["requests"][0]
    exported = call(export)
    dispatch = next(a for a in exported["decision_packet"]["ready_actions"] if a["operation_id"] == "delegation.dispatch")
    executed = call(invocation=dispatch)
    assert executed["value"]["status"] == "returned-unproven"
    reentry = executed["value"]["reentry"]["request"]
    observed = call(reentry)
    admission = observed["task_requirements"]["assignment"]["result_admission"]["requests"][0]
    admission[-1]["arguments"]["reason"] = "The explanation matches the supplied failed log; accept analysis for the follow-up decision."
    accepted = call(admission)
    analysis = accepted["verification"]["analysis"]
    assert analysis["analysis_use_allowed"] is True
    assert analysis["trust_level"] == "unproven-analysis"
    assert not any(analysis["claim_boundary"].values())
    assert checked["value"]["receipt"]["result"] == "failed"
    assert not (config.parent / "planning").exists()
    assert (tmp_path / "count.txt").read_text() == "run\n"
    forbidden = copy.deepcopy(admission)
    next(r for r in forbidden if r["request_kind"] == "assignment/judge-task-requirements/v1")["arguments"]["required_result_classes"] = [
        "unapplied-patch"
    ]
    with pytest.raises(AssertionError, match="read-only analysis"):
        call(forbidden)
    (tmp_path / "unrelated.txt").write_text("Unrelated observation")
    assert call(admission)["verification"]["analysis"]["analysis_use_allowed"] is True
    (tmp_path / "check.py").write_text("print('materially changed check')\n")
    with pytest.raises(AssertionError, match="changed|current|stale"):
        call(admission)
    assert call(requirement)["task_requirements"]["source_work"]["status"] == "shaping-required"
