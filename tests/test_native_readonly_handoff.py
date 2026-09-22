"""Self-sufficient current read-only handoffs, never reviewer authentication."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shlex
import sys

import pytest
from tests import native_artifact_consumers
from tests.test_native_npm_routes import packed as packed
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n[delegation_targets.expert]\ntransports=[{kind="manual"}]\n'


@pytest.mark.parametrize(
    "surface,fault",
    [
        ("native", None),
        ("json", None),
        ("python", None),
        ("typescript", None),
        ("native", "host"),
        ("native", "repair-evaluation"),
        ("native", "identity"),
        ("native", "malformed"),
        ("native", "truncated"),
        ("native", "source-drift"),
        ("native", "stopped"),
    ],
)
def test_current_process_handoff_executes_once_without_admitting_worker_claims(tmp_path, shared_core_binary, native_cli, surface, fault):
    host = fault == "host"
    repair_evaluation = fault == "repair-evaluation"
    if host or repair_evaluation:
        fault = None
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "packet=json.load(sys.stdin)\n"
        "with Path('launches.txt').open('a') as f: f.write('launched\\n')\n"
        "print(json.dumps({**packet['return_contract']['required_identity'],"
        "'kind':'agentic-workspace/delegated-return/v1','result_delivery':'unapplied-patch',"
        "'changed_paths':[],'patch':'','summary':packet['worker_context']['inputs']['capsule'][0]['content'],"
        "'stop_conditions_hit':[]}))\n"
    )
    if fault == "identity":
        worker.write_text(
            worker.read_text().replace(
                "packet=json.load(sys.stdin)",
                "packet=json.load(sys.stdin); packet['return_contract']['required_identity']['target']='different-target'",
            )
        )
    elif fault == "malformed":
        worker.write_text(
            worker.read_text().replace("'summary':packet['worker_context']['inputs']['capsule'][0]['content']", "'summary':None")
        )
    elif fault == "truncated":
        worker.write_text(
            worker.read_text().replace("'summary':packet['worker_context']['inputs']['capsule'][0]['content']", "'summary':'x'*100000")
        )
    elif fault == "source-drift":
        worker.write_text(
            worker.read_text().replace(
                "packet=json.load(sys.stdin)",
                "packet=json.load(sys.stdin); Path('dependency.md').write_text('Changed during worker execution.')",
            )
        )
    elif fault == "stopped":
        worker.write_text(worker.read_text().replace("'stop_conditions_hit':[]", "'stop_conditions_hit':['required input unavailable']"))
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    config = BASE.replace("[delegation]", "[safety]\nsafe_to_auto_run_commands=true\n[delegation]")
    config = config.replace('transport_authority="manual"', 'transport_authority="automatic"')
    config = config.replace(
        'transports=[{kind="manual"}]',
        'transports=[{kind="process",command=' + json.dumps([sys.executable, str(worker)]) + ",timeout_seconds=30}]",
    )
    if host:
        if native_artifact_consumers.CURRENT is not None:
            # The provider primitive is shipped in the wheel; do not import it
            # from the source checkout when proving installed handoffs.
            installed_command = [str(native_artifact_consumers.CURRENT["python"]), "-I", str(worker)]
            config = config.replace(json.dumps([sys.executable, str(worker)]), json.dumps(installed_command))
        else:
            installed_command = [sys.executable, str(worker)]
        process_transport = '{kind="process",command=' + json.dumps(installed_command) + ",timeout_seconds=30}"
        native_transport = process_transport.replace(
            'kind="process",command=', 'kind="native",adapter="codex-app-server/v1",parameters={model="fixture"},command='
        )
        config = config.replace(process_transport, process_transport + "," + native_transport)
        worker.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "from agentic_workspace import sealed_codex_transport as host\n"
            "host.native_transport.discover=lambda *a,**k: {'revision':'fixture','expires_at':99999999999,'modes':['fresh'],'parameters':['model'],'models':[{'model':'fixture'}]}\n"
            "def execute(root,snapshot,selection,prompt,schema,**kw):\n"
            " assert selection['parameters']=={'model':'fixture'} and selection['mode']=='fresh'\n"
            " assert set(schema['properties'])=={'summary','patch','changed_paths','stop_conditions_hit','result_delivery'}\n"
            " assert all('type' in value for value in schema['properties'].values())\n"
            " assert schema['properties']['result_delivery']=={'type':'string','const':'unapplied-patch'}\n"
            " with Path('launches.txt').open('a') as f: f.write('launched\\n')\n"
            " return {'returned_work':{'summary':json.loads(prompt)['captured_inputs'][0]['content'],'patch':'','changed_paths':[],'stop_conditions_hit':[],'result_delivery':'unapplied-patch'}}\n"
            "host.native_transport.execute=execute\n"
            "host.main()\n"
        )
    source.write_text(config)
    config_revision = hashlib.sha256(source.read_bytes()).hexdigest()
    dependency = tmp_path / "dependency.md"
    dependency.write_text("A bounded source observation.\n")
    expected_frontier = (
        ("repair-required: " + dependency.read_bytes().decode().strip()) if repair_evaluation else dependency.read_bytes().decode()
    )
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("Preserve concurrent work.\n")
    context = {"target": str(tmp_path), "task": "Return the supplied source observation", "changed": []}

    def call(request=None, **updates):
        return consume(surface, shared_core_binary, native_cli, {**context, **updates, **({"request": request} if request else {})})

    if fault is None:
        from tests.test_native_planning_create import material

        creation = call()["planning"]["creation_requests"][0]
        creation["arguments"] = {"material": material()}
        destination = "frontier"
        if surface == "typescript":
            # A new admitted return must still acquire consumption custody when
            # its semantic summary already exists. Volatile frontier text is
            # separate from the accepted progress carried to a fresh consumer.
            destination = "accepted_progress"
            creation["arguments"]["material"]["material_lifetimes"]["continuation_frontier"] = "observation"
            creation["arguments"]["material"]["continuation"][destination] = dependency.read_bytes().decode()
        created = call(invocation=call(creation)["decision_packet"]["primary_action"])
        plan_path = tmp_path / created["value"]["owner_path"]
        selection = call()["planning"]["created_owner"]["selection_request"]
        call(invocation=call(selection)["decision_packet"]["primary_action"])
        original_plan = json.loads(plan_path.read_bytes())
        if surface == "json":
            oversized = call()["planning"]["update_requests"][0]
            oversized["arguments"]["material"] = material()
            oversized["arguments"]["material"].update(lifecycle=original_plan["lifecycle"], phase=original_plan["phase"])
            oversized["arguments"]["material"]["next_action"] = "\x01" * 60000
            oversized_action = call(oversized)["decision_packet"]["primary_action"]
            saved = plan_path.read_bytes()
            effects = set((tmp_path / ".agentic-workspace/local/effects").iterdir())
            with pytest.raises(AssertionError, match="bounded source size"):
                call(invocation=oversized_action)
            assert plan_path.read_bytes() == saved
            assert set((tmp_path / ".agentic-workspace/local/effects").iterdir()) == effects
        plan_ref = plan_path.relative_to(tmp_path).as_posix()
        (tmp_path / "verify_frontier.py").write_text(
            "import json\nfrom pathlib import Path\np=json.loads(Path(" + repr(plan_ref) + ").read_bytes())\n"
            f"assert p['continuation'][{destination!r}] == {expected_frontier!r}\nprint('Exact source frontier retained')\n"
        )
        executable = "& '" + sys.executable.replace("'", "''") + "'" if os.name == "nt" else shlex.quote(sys.executable)
        manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            'schema_version="agentic-workspace/verification-manifest/v1"\n[protocols.frontier]\napplies_to_paths=['
            + json.dumps(plan_ref)
            + ',"dependency.md","verify_frontier.py"]\n[proof_routes.frontier]\nprotocol_refs=["frontier"]\ncommands=['
            + json.dumps(executable + " verify_frontier.py")
            + "]\n"
        )

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    if fault is None:
        task = [call()["planning"]["requests"][0], task]
    inputs = call(task)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(
        input_refs=["dependency.md"], complete=False, reason="The one source is sufficient for this bounded task."
    )
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    offered = call(inputs)["task_requirements"]
    if host:
        candidates = offered["execution_configurations"]["configurations"]["candidates"]
        variants = {row["configuration"]["id"]: row["configuration"] for row in candidates if row["eligible"]}
        assert variants["expert:cli"]["execution"]["adapter"]["kind"] == "process"
        assert variants["expert:native:codex-app-server/v1"]["execution"]["adapter"]["adapter"] == "codex-app-server/v1"
    assessment = offered["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(
        alternative="expert:native:codex-app-server/v1" if host else "expert:cli",
        reason="Use the configured independent process for the bounded observation.",
    )
    local_assessment = copy.deepcopy(assessment)
    local_assessment[-1]["arguments"].update(
        alternative="local:internal", reason="Matched retained-local feasibility control for the same bounded task."
    )
    local = call(local_assessment)
    assert local["task_requirements"]["assignment"]["result"]["status"] == "assigned-current-target"
    assert local["task_requirements"]["delegation"]["requests"] == []
    assert not (tmp_path / ".agentic-workspace/local/delegation-runs").exists()
    export = call(assessment)["task_requirements"]["handoff"]["requests"][0]
    if fault is None:
        export.append(call()["planning"]["requests"][0])
        before_retention = call(export)["planning"]["current_owner"]["reconciliation"]["subject"]["revision"]
        retention = call(export)["planning"]["handoff_retention_requests"][0]
        forged_retention = copy.deepcopy(retention)
        forged_retention[-1]["id"] = "client-chosen-retention"
        with pytest.raises(AssertionError, match="exact request"):
            call(forged_retention)
        retain_action = next(a for a in call(export)["decision_packet"]["ready_actions"] if a["operation_id"] == "planning.update")
        assert retain_action == next(
            a for a in call(retention)["decision_packet"]["ready_actions"] if a["operation_id"] == "planning.update"
        )
        assert retain_action["operation_id"] == "planning.update"
        call(invocation=retain_action)
        assert call(invocation=retain_action)["status"] == "applied"
        fresh = call()
        if fresh["planning"]["status"] != "current":
            call(invocation=call(fresh["planning"]["requests"][0])["decision_packet"]["primary_action"])
        fresh = call()
        held = fresh["planning"]["handoff_continuation"]["retained"]
        assert held["status"] == "assigned"
        assert held["reentry"]["task"] == context["task"]
        export = held["reentry"]["request"]
        assert call(export)["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] == before_retention
    dispatch = call(export)["task_requirements"]["delegation"]["requests"][0]
    dispatch_view = call(export)
    assert next(a for a in dispatch_view["decision_packet"]["ready_actions"] if a["operation_id"] == "delegation.dispatch") == next(
        a for a in call(dispatch)["decision_packet"]["ready_actions"] if a["operation_id"] == "delegation.dispatch"
    )
    action = next(action for action in dispatch_view["decision_packet"]["ready_actions"] if action["operation_id"] == "delegation.dispatch")
    assert action["operation_id"] == "delegation.dispatch"
    assert not (tmp_path / "launches.txt").exists()
    result = call(invocation=action)
    cost = result["value"]["context_cost"]
    assert cost["assignment_packet_bytes"] == len(
        json.dumps(action["arguments"]["packet"], ensure_ascii=False, separators=(",", ":")).encode()
    )
    assert cost["rendered_prompt_bytes"] == cost["assignment_packet_bytes"]
    assert cost["elapsed_ms"] == result["value"]["process"]["duration_ms"]
    assert all(cost[field] is None for field in ("effective_input_tokens", "cached_input_tokens", "output_tokens", "retry_count"))
    assert "provider_prompt_framing" in cost["unknown_fields"]
    if fault:
        assert result["value"]["status"] == "censored-or-invalid-return"
        assert result["value"]["returned"] is None and result["value"]["reentry"] is None
        assert not any(result["value"]["claim_boundary"].values())
        if fault == "source-drift":
            with pytest.raises(AssertionError, match="changed|stale"):
                call(invocation=action)
        else:
            assert call(invocation=action)["value"] == result["value"]
        assert (tmp_path / "launches.txt").read_text() == "launched\n"
        assert unrelated.read_text() == "Preserve concurrent work.\n"
        return
    assert result["value"]["status"] == "returned-unproven"
    assert result["value"]["returned"]["summary"] == dependency.read_bytes().decode()
    assert result["value"]["claim_boundary"] == {"proof": False, "planning_progress": False, "completion": False}
    assert call(invocation=action)["value"] == result["value"]
    if surface == "native":
        runs = tmp_path / ".agentic-workspace/local/delegation-runs"
        completion = next(runs.glob("*.completed.json"))
        terminal = next(runs.glob("*.terminal.json"))
        held = json.loads(terminal.read_text())
        commit = tmp_path / held["custody"]["committed"]["path"]
        # Fresh invocation recovers both publication boundaries without another
        # external worker. These deletions model an interrupted fixture writer.
        completion.unlink()
        assert call(invocation=action)["value"] == result["value"]
        completion.unlink()
        commit.unlink()
        assert call(invocation=action)["value"] == result["value"]
        completion.unlink()
        original = terminal.read_bytes()
        terminal.unlink()
        pending = call(export)
        assert not any(a["operation_id"] == "delegation.dispatch" for a in pending["decision_packet"]["ready_actions"])
        assert any(b["code"] == "delegation-execution-uncertain" for b in pending["decision_packet"]["blockers"])
        assert (tmp_path / "launches.txt").read_text() == "launched\n"
        terminal.write_bytes(original)
        held["outcome"]["value"]["returned"]["summary"] = "invented recovery"
        terminal.write_text(json.dumps(held))
        with pytest.raises(AssertionError, match="custody|differs"):
            call(invocation=action)
        assert not completion.exists()
        terminal.write_bytes(original)
        assert call(invocation=action)["value"] == result["value"]
    assert (tmp_path / "launches.txt").read_text() == "launched\n"
    if host:
        original_config = source.read_bytes()
        source.write_text(config.replace("delegation_targets.expert", "delegation_targets.replacement"))
        replacement_task = call()["task_requirements"]["requests"][0]
        replacement_task["arguments"]["required_result_classes"] = ["read-only"]
        replacement_inputs = call(replacement_task)["task_requirements"]["handoff_inputs"]["requests"][0]
        replacement_inputs[-1]["arguments"].update(
            input_refs=["dependency.md"], complete=False, reason="Same bounded input for replacement."
        )
        replacement_inputs = call(replacement_inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
        replacement_inputs[-1]["arguments"]["complete"] = True
        replacement_choice = next(
            r
            for r in call(replacement_inputs)["task_requirements"]["execution_configurations"]["requests"]
            if r[-1]["arguments"]["candidate"] == "replacement:native:codex-app-server/v1"
        )
        replacement_assessment = call(replacement_choice)["task_requirements"]["assignment"]["requests"][0]
        replacement_assessment[-1]["arguments"].update(
            alternative="replacement:native:codex-app-server/v1", reason="Current replacement for the same bounded work."
        )
        replacement_export = call(replacement_assessment)["task_requirements"]["handoff"]["requests"][0]
        offered = call(replacement_export)["task_requirements"]["delegation"]["requests"]
        prior = next(r for r in offered if r[-1]["request_kind"] == "delegation/reconcile-prior-result/v1")
        prior[-1]["arguments"]["custody"] = result["value"]["reentry"]["request"][-1]["arguments"]["custody"]
        prior_commit = tmp_path / prior[-1]["arguments"]["custody"]["committed"]["path"]
        prior_bytes = prior_commit.read_bytes()
        prior_commit.unlink()
        with pytest.raises(AssertionError, match="invalid-source-decision"):
            call(prior)
        prior_commit.write_bytes(prior_bytes)
        preserved = call(prior)["task_requirements"]["delegation"]["prior_result"]
        assert preserved["outcome"] == result["value"] or preserved["outcome"]["returned"] == result["value"]["returned"]
        replacement_dispatch = call(prior)["task_requirements"]["delegation"]["requests"][0]
        replacement_action = next(
            action
            for action in call(replacement_dispatch)["decision_packet"]["ready_actions"]
            if action["operation_id"] == "delegation.dispatch"
        )
        assert call(invocation=replacement_action)["value"]["status"] == "returned-unproven"
        prior[-1]["arguments"]["disposition"] = "reuse-readonly"
        late = call(prior)["task_requirements"]["delegation"]["observation"]
        assert late["status"] == "current-executed-observation"
        assert late["origin_assignment"]["selected"]["target"] == "expert"
        assert late["assignment_identity"]["selected"]["target"] == "replacement"
        assert call(prior)["task_requirements"]["delegation"]["observation"] == late
        dependency.write_text("Changed input invalidates late return.")
        with pytest.raises(AssertionError, match="changed|stale"):
            call(prior)
        dependency.write_text("A bounded source observation.\n")
        source.write_bytes(original_config)
    reentry = result["value"]["reentry"]
    assert reentry["request"][-2]["arguments"]["returned"] == result["value"]["returned"]
    observed = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **reentry})
    assert observed["task_requirements"]["handoff"]["observation"]["proof_current"] is False
    execution = observed["task_requirements"]["delegation"]["observation"]
    assert execution["status"] == "current-executed-observation"
    assert execution["returned"] == result["value"]["returned"]
    assert execution["context_cost"] == cost
    assert not any(execution["claim_boundary"].values())
    retention = observed["planning"]["handoff_retention_requests"][0]
    retain_action = call(retention)["decision_packet"]["primary_action"]
    assert retain_action["operation_id"] == "planning.update"
    call(invocation=retain_action)
    assert call(invocation=retain_action)["status"] == "applied"
    fresh = call()
    if fresh["planning"]["status"] != "current":
        call(invocation=call(fresh["planning"]["requests"][0])["decision_packet"]["primary_action"])
    held = call()["planning"]["handoff_continuation"]["retained"]
    assert held["status"] == "returned"
    assert call(export)["planning"]["handoff_retention_requests"] == []
    assert "assignment" not in json.loads(plan_path.read_bytes())["relationships"]
    if surface == "json":
        # Only the exact prior continuation survives an observation-only update.
        changed_envelope = copy.deepcopy(held["reentry"]["request"])
        next(r for r in changed_envelope if r["request_kind"] == "planning/continuation/v1")["id"] = "different-answer"
        with pytest.raises(AssertionError, match="changed|stale"):
            call(changed_envelope)
        original_bytes = plan_path.read_bytes()
        original_body = json.loads(original_bytes)
        commit = tmp_path / original_body["update_provenance"]["custody"]["committed"]["path"]
        committed_bytes = commit.read_bytes()
        commit.unlink()
        with pytest.raises(AssertionError, match="changed|stale|pending|uncertain"):
            call(held["reentry"]["request"])
        commit.write_bytes(committed_bytes)
        foreign = copy.deepcopy(original_body)
        foreign["phase"] = "review"
        plan_path.write_text(json.dumps(foreign))
        with pytest.raises(AssertionError, match="changed|stale"):
            call(held["reentry"]["request"])
        plan_path.write_bytes(original_bytes)
        material = copy.deepcopy(retain_action["arguments"]["request"]["arguments"]["material"])
        material["relationships"] = original_body["relationships"]
        update = call()["planning"]["update_requests"][0]
        update["arguments"]["material"] = copy.deepcopy(material)
        update["arguments"]["material"]["next_action"] = "A materially different continuation."
        call(invocation=call(update)["decision_packet"]["primary_action"])
        with pytest.raises(AssertionError, match="changed|stale"):
            call(held["reentry"]["request"])
        update = call()["planning"]["update_requests"][0]
        update["arguments"]["material"] = material
        call(invocation=call(update)["decision_packet"]["primary_action"])
        fresh = call()
        call(invocation=call(fresh["planning"]["requests"][0])["decision_packet"]["primary_action"])
        from tests.test_native_planning_create import material as new_material

        def other_call(request=None, **updates):
            return call(request, task="A different independent Planning task", **updates)

        unrelated_request = other_call()["planning"]["requests"][0]
        unrelated_request["arguments"].update(answer="independent", task_posture="planned")
        creation = other_call(unrelated_request)["planning"]["creation_requests"][0]
        creation["arguments"] = {"material": new_material()}
        creation["arguments"]["material"]["title"] = "A different selected Planning owner"
        other_call(invocation=other_call([unrelated_request, creation])["decision_packet"]["primary_action"])
        selection = other_call()["planning"]["created_owner"]["selection_request"]
        other_call(invocation=other_call(selection)["decision_packet"]["primary_action"])
        with pytest.raises(AssertionError, match="changed|stale"):
            call(held["reentry"]["request"])
        selection = call()["planning"]["requests"][0]
        selection["arguments"]["owner_ref"] = plan_ref
        selection = call(selection)["planning"]["requests"][0]
        call(invocation=call(selection)["decision_packet"]["primary_action"])
    observed = call(held["reentry"]["request"])
    assert observed["task_requirements"]["assignment"]["result_admission"]["status"] == "judgment-required"
    judgment = observed["task_requirements"]["assignment"]["result_admission"]["requests"][0]
    judgment[-1]["arguments"] = {"answer": "use-result", "reason": "The returned observation exactly matches the supplied source."}
    admitted = call(judgment)
    admission = admitted["task_requirements"]["assignment"]["result_admission"]
    assert admission["status"] == "admitted-for-use" and admission["result_use_allowed"] is True
    assert not any(admission["claim_boundary"].values())
    assert not any(b["code"] == "current-nonlocal-assignment-handoff-required" for b in admitted["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/delegation-outcomes.json").exists()
    assert admitted["task_requirements"]["bounded_outcome_evidence"] == []
    for answer, status in [("repair-required", "repair-required"), ("reject-result", "rejected")]:
        negative = copy.deepcopy(judgment)
        negative[-1]["arguments"] = {"answer": answer, "reason": "The orchestrator has not accepted this result for use."}
        rejected = call(negative)
        assert rejected["task_requirements"]["assignment"]["result_admission"]["status"] == status
        assert any(b["code"] == "current-nonlocal-assignment-handoff-required" for b in rejected["decision_packet"]["blockers"])
    missing_provenance = [r for r in judgment if r["request_kind"] != "delegation/read-result/v1"]
    with pytest.raises(AssertionError, match="executed result required"):
        call(missing_provenance)
    forged = copy.deepcopy(reentry)
    forged["request"][-2]["arguments"]["returned"]["summary"] = "Worker text cannot manufacture a retained outcome."
    with pytest.raises(AssertionError, match="retained execution"):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **forged})
    if repair_evaluation:
        judgment[-1]["arguments"] = {"answer": "repair-required", "reason": dependency.read_bytes().decode()}
        admitted = call(judgment)
    adoption = admitted["planning"]["adoption_requests"][0]
    adopt_action = next(a for a in admitted["decision_packet"]["ready_actions"] if a["operation_id"] == "planning.update")
    assert adopt_action == call(adoption)["decision_packet"]["primary_action"]
    assert adopt_action["operation_id"] == "planning.update"
    assert adopt_action["arguments"]["document"]["continuation"][destination] == expected_frontier
    tampered = copy.deepcopy(adopt_action)
    tampered["arguments"]["document"]["continuation"]["frontier"] = "A caller-substituted result"
    before_adoption = plan_path.read_bytes()
    with pytest.raises(AssertionError):
        call(invocation=tampered)
    assert plan_path.read_bytes() == before_adoption
    applied = call(invocation=adopt_action)
    assert applied["status"] == "applied"
    adopted_plan = json.loads(plan_path.read_bytes())
    assert adopted_plan["continuation"][destination] == expected_frontier
    for field in ["id", "scope", "relationships", "proof", "intent", "next_action"]:
        assert adopted_plan[field] == original_plan[field]
    fresh = call()
    call(invocation=call(fresh["planning"]["requests"][0])["decision_packet"]["primary_action"])
    assert call()["planning"]["current_owner"]["current"] is True
    assert call()["planning"]["handoff_continuation"] is None
    before_reobservation = plan_path.read_bytes()
    if surface == "native" and not repair_evaluation:
        continued = [r for r in judgment if r["owner"] != "planning"]
        continued.append(call()["planning"]["requests"][0])
        # Adoption changed the semantic Planning subject. Reusing the old
        # requirement judgment cannot manufacture another progress update.
        with pytest.raises(AssertionError, match="task requirements source changed"):
            call(continued)
        assert not any(a["operation_id"] == "planning.update" for a in call()["decision_packet"]["ready_actions"])
        assert plan_path.read_bytes() == before_reobservation
    proof_context = {**context, "changed": [plan_ref, "dependency.md", "verify_frontier.py"]}
    proof_start = consume(surface, shared_core_binary, native_cli, proof_context, host_path=os.environ["PATH"])
    continuation = proof_start["planning"]["requests"][0]
    continuation["arguments"]["answer"] = "continue-selected"
    proof_ready = consume(surface, shared_core_binary, native_cli, {**proof_context, "request": continuation}, host_path=os.environ["PATH"])
    proof_request = proof_ready["verification"]["execution_requests"][0]
    proof_action = consume(
        surface, shared_core_binary, native_cli, {**proof_context, "request": [continuation, proof_request]}, host_path=os.environ["PATH"]
    )["decision_packet"]["primary_action"]
    assert proof_action["operation_id"] == "proof.report" and continuation in proof_action["source_requests"]
    checked = consume(surface, shared_core_binary, native_cli, {**proof_context, "invocation": proof_action}, host_path=os.environ["PATH"])
    assert checked["value"]["process"]["status"] == "passed" and checked["value"]["publication"]["status"] == "published"
    assert checked["value"]["claim_boundary"]["completion_claim_allowed"] is False

    def proof_view(request=continuation, **updates):
        return consume(
            surface, shared_core_binary, native_cli, {**proof_context, "request": request, **updates}, host_path=os.environ["PATH"]
        )

    claim = proof_view()["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [checked["value"]["publication"]["reference"]]
    evidence_requests = [continuation, claim]
    current = proof_view(evidence_requests)
    evidence = current["task_requirements"]["bounded_outcome_evidence"]
    assert len(evidence) == 1 and evidence[0]["claim"] == (
        "responsible-owner-repair-evaluation-retained-and-checked" if repair_evaluation else "result-retained-and-selected-command-passed"
    )
    assert evidence[0]["support"]["observed_outcomes"] == 1 and not any(evidence[0]["claim_boundary"].values())
    assert proof_view(evidence_requests)["task_requirements"]["bounded_outcome_evidence"] == evidence
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config_revision
    requirements = current["task_requirements"]["requests"][0]
    requirements["arguments"]["required_result_classes"] = ["read-only"]
    comparison = proof_view([*evidence_requests, requirements])["task_requirements"]["assignment"]
    alternatives = comparison["result"]["alternatives"]
    executed_variant = "expert:native:codex-app-server/v1" if host else "expert:cli"
    assert next(a for a in alternatives if a["id"] == executed_variant)["contextual_evidence"] == evidence
    if host:
        assert next(a for a in alternatives if a["id"] == "expert:cli")["contextual_evidence"] == []
    assert next(a for a in alternatives if a["target"] == "local")["contextual_evidence"] == []
    assert comparison["result"]["selected"] is None
    comparison_request = comparison["requests"][0]
    comparison_request[-1]["arguments"].update(
        alternative=executed_variant,
        reason="This exact eligible configuration has one current retained-and-checked outcome; broader suitability remains uncertain.",
    )
    assert proof_view(comparison_request)["task_requirements"]["assignment"]["result"]["selected"]["target"] == "expert"
    unrelated_task = consume(
        surface, shared_core_binary, native_cli, {**proof_context, "task": "An unrelated outcome"}, host_path=os.environ["PATH"]
    )
    assert unrelated_task["task_requirements"]["bounded_outcome_evidence"] == []
    assert not (tmp_path / ".agentic-workspace/delegation-outcomes.json").exists()
    with pytest.raises(AssertionError, match="changed|stale"):
        call(adoption)
    dependency.write_text("Changed after execution.\n")
    assert proof_view(evidence_requests)["task_requirements"]["bounded_outcome_evidence"] == []
    with pytest.raises(AssertionError, match="source changed|stale"):
        proof_view(comparison_request)
    with pytest.raises(AssertionError, match="changed|stale"):
        call(invocation=action)
    with pytest.raises(AssertionError, match="changed|stale"):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **reentry})
    with pytest.raises(AssertionError, match="changed|stale"):
        call(judgment)
    supersede = call()["planning"]["update_requests"][0]
    supersede["arguments"]["material"] = copy.deepcopy(adopt_action["arguments"]["request"]["arguments"]["material"])
    supersede["arguments"]["material"]["relationships"] = adopted_plan["relationships"]
    supersede["arguments"]["material"]["next_action"] = "The owner now continues beyond the consumed result."
    call(invocation=call(supersede)["decision_packet"]["primary_action"])
    recovery = call()["planning"]["requests"][0]
    call(invocation=call(recovery)["decision_packet"]["primary_action"])
    assert call()["planning"]["consumed_result"] is None
    assert (tmp_path / "launches.txt").read_text() == "launched\n" * (2 if host else 1)
    assert unrelated.read_text() == "Preserve concurrent work.\n"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_capsule_and_typed_return_without_parent_context(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    dependency = tmp_path / "dependency.md"
    dependency.write_text("Domain rule: blå means blue.\n", encoding="utf-8", newline="\n")
    context = {"target": str(tmp_path), "task": "Explain the supplied domain rule in English; return findings only.", "changed": []}
    input_refs = ["dependency.md"]
    if surface == "native":
        from tests.repo_procedure_fixture import install_method, question

        from agentic_workspace import start

        input_refs += install_method(tmp_path, "delegation-handoff", "host/collaboration")
        selected, answer = question(context, "host/collaboration")
        assert "Carry the current frontier" not in json.dumps(selected)
        for disposition, branches in [("unknown", []), ("answered", ["local"]), ("answered", ["delegate"]), ("answered", ["handoff"])]:
            answer["arguments"]["answer"] = {"disposition": disposition, "branches": branches}
            result = start({**context, "projection": "full", "request": answer})
            assert result["procedure"]["status"] == "current"
            assert result["task_requirements"]["assignment"]["result"]["selected"] is None
            assert result["task_requirements"]["delegation"]["requests"] == []
        fragment = result["procedure"]["next"][0]["resource"]
        input_refs += [fragment, "frontier.md"]
        (tmp_path / "frontier.md").write_text(
            "Outcome: explain the supplied domain rule; read-only scope.\n"
            "Judgment: a bounded independent explanation is useful; Assignment must admit the target.\n"
            "Current procedure: " + fragment + "\n"
            "Stop if required input is missing or scope widens. No parent completion or review authority.\n"
            "Return observations only through the sealed return contract; proof remains with Verification.\n",
            encoding="utf-8",
        )
        (tmp_path / "unrelated.txt").write_text("not worker context", encoding="utf-8")
        assert start({**context, "projection": "full", "request": answer})["procedure"]["status"] == "current"
        method = tmp_path / "tools/skills/host-method/procedure.md"
        original = method.read_bytes()
        method.write_bytes(original + b"\nChanged method\n")
        assert start({**context, "projection": "full", "request": answer})["procedure"]["status"] == "stale"
        method.write_bytes(original)

    transcript = []
    parent_inputs = []

    def call(request=None, **updates):
        payload = {**context, **updates, **({"request": request} if request else {})}
        parent_inputs.append(payload)
        value = consume(surface, shared_core_binary, native_cli, payload)
        transcript.append(value)
        return value

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    before = call(task)
    manual = next(
        r
        for r in before["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"]
    inputs = before["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(
        input_refs=input_refs,
        complete=False,
        reason="The domain rule and selected semantic frontier are sufficient for this bounded explanation.",
    )
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    offered = call(inputs)
    assert "blå means" not in json.dumps(offered, ensure_ascii=False)
    assessment = offered["task_requirements"]["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(
        alternative="expert:manual", reason="The configured expert is preferred for this domain explanation."
    )
    current = call(assessment)
    assert current["task_requirements"]["assignment"]["result"]["status"] == "assigned-nonlocal-handoff-required"
    export = current["task_requirements"]["handoff"]["requests"][0]
    exported = call(export)["task_requirements"]["handoff"]
    packet = exported["packet"]
    worker = packet["worker_context"]
    assert worker["intent"]["outcome"] == context["task"]
    assert worker["inputs"]["capsule"] == [
        {
            "reference": ref,
            "revision": "sha256:" + hashlib.sha256((tmp_path / ref).read_bytes()).hexdigest(),
            "content": (tmp_path / ref).read_bytes().decode("utf-8"),
        }
        for ref in input_refs
    ]
    assert "not worker context" not in json.dumps(worker)
    assert worker["effects"]["allowed"] == ["read-provided-inputs", "return-observations"]
    assert worker["proof"]["worker_authority"] is False
    assert worker["inputs"]["task_requirements"]["requirements"]["required_result_classes"] == ["read-only"]
    reentry = copy.deepcopy(worker["return_contract"]["reentry"])
    returned = {
        **worker["return_contract"]["required_identity"],
        "kind": "agentic-workspace/delegated-return/v1",
        "result_delivery": "unapplied-patch",
        "changed_paths": [],
        "patch": "",
        "summary": "The supplied Swedish word means blue.",
        "stop_conditions_hit": [],
    }
    reentry["request"][-1]["arguments"]["returned"] = returned
    if surface == "native":
        # Native argv -> shared Rust projection; existing compact packet parity
        # covers retained adapters without repeating this semantic journey.
        import subprocess
        from time import perf_counter

        helper_io = []

        def worker_call(action, **extra):
            payload = json.dumps({"action": action, "packet": packet, **extra})
            began = perf_counter()
            response = subprocess.run(
                [str(native_cli), "worker", "--input", "-", "--format", "json"],
                input=payload,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            helper_io.append(
                {
                    "input_bytes": len(payload.encode()),
                    "output_bytes": len(response.stdout.encode()),
                    "elapsed_ms": round((perf_counter() - began) * 1000, 1),
                }
            )
            return json.loads(response.stdout)

        entry = worker_call("entry")
        assert "reentry" not in entry["view"]["return_contract"]
        assert "required_identity" not in entry["view"]["return_contract"]
        assert entry["view"]["effects"] == worker["effects"]
        assert entry["burden"]["host_skill_context_bytes"] == {"status": "unknown"}
        for item, captured in zip(entry["view"]["inputs"]["capsule"], worker["inputs"]["capsule"], strict=True):
            assert worker_call("expand", reference=item["detail_ref"])["input"] == captured
        material = {key: returned[key] for key in ["summary", "changed_paths", "patch", "stop_conditions_hit"]}
        assembled = worker_call("return", material=material)
        assert assembled["reentry"] == reentry
        from tests.test_native_public_cli import ROOT

        # A declared fixture consumer reads precisely these procedures. This is
        # reproducible source delivery, not a claim about hidden host injection.
        skill_refs = [
            ".agentic-workspace/skills/workspace-startup/SKILL.md",
            ".agentic-workspace/planning/skills/planning-assignment/SKILL.md",
            ".agentic-workspace/planning/skills/planning-assignment/references/manual.md",
            ".agentic-workspace/planning/skills/planning-assignment/references/return.md",
        ]
        skills = sum(len((ROOT / ref).read_bytes()) for ref in skill_refs)

        def byte_size(value):
            return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())

        measurement = {
            **entry["burden"],
            "fixture_skill_refs": skill_refs,
            "fixture_skill_bytes": skills,
            "parent_owner_calls_before_worker": len(transcript),
            "parent_owner_response_bytes": sum(byte_size(value) for value in transcript),
            "parent_owner_request_bytes": sum(byte_size(value) for value in parent_inputs),
            "worker_helper_io_single_sample": helper_io,
            "worker_entry_expand_return_calls": 2 + len(input_refs),
            "return_owner_calls": 1,
            "required_detail_fetches": 0,
            "optional_detail_fetches_exercised": len(input_refs),
            "worker_return_material_bytes": byte_size(material),
            "legacy_worker_return_bytes": byte_size(returned),
            "baseline_skills_entry_return_bytes": skills + byte_size(worker) + byte_size(returned),
            "bounded_skills_entry_return_bytes": skills + byte_size(entry["view"]) + byte_size(material),
            "fixture_parent_semantic_answers": 8,
            "method_owner_calls_before_handoff": 9,
            "method_owner_io_bytes": "not measured; excluded from handoff-only byte comparison",
            "fixture_worker_material_submissions": 1,
            "fixture_user_steering": 0,
            "fixture_protocol_repairs": 0,
            "fixture_persistent_worker_files": 0,
            "actual_model_semantic_turns": "unknown",
            "token_counts": "unknown",
            "provider_economics": "unknown",
        }
        assert measurement["bounded_skills_entry_return_bytes"] < measurement["baseline_skills_entry_return_bytes"]
        reentry = assembled["reentry"]
    # Fresh process consumes only this sealed packet's explicit re-entry context.
    admitted = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **reentry})
    if surface == "native":
        measurement["return_owner_response_bytes"] = byte_size(admitted)
        measurement["return_owner_request_bytes"] = byte_size({"target": str(tmp_path), **reentry})
        measurement["worker_helper_additional_transport_bytes"] = sum(item["input_bytes"] + item["output_bytes"] for item in helper_io)
        shared_cost = measurement["parent_owner_response_bytes"] + byte_size(admitted)
        measurement["full_fixture_baseline_bytes"] = shared_cost + measurement["baseline_skills_entry_return_bytes"]
        measurement["full_fixture_bounded_bytes"] = shared_cost + measurement["bounded_skills_entry_return_bytes"]
        print("WORKER_BURDEN=" + json.dumps(measurement, sort_keys=True))
    observed = admitted["task_requirements"]["handoff"]["observation"]
    assert observed["status"] == "current-unproven-observation"
    assert observed["proof_current"] is False and observed["authenticated_reviewer"] is False
    assert any(b["code"] == "current-nonlocal-assignment-handoff-required" for b in admitted["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/local").exists()
    wrong = copy.deepcopy(reentry)
    wrong["request"][-1]["arguments"]["returned"]["target"] = "other"
    with pytest.raises(AssertionError, match="match"):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **wrong})
    mutation = copy.deepcopy(reentry)
    mutation["request"][-1]["arguments"]["returned"]["patch"] = "invented diff"
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **mutation})
    if surface == "native":
        method.write_bytes(original + b"\nChanged upstream procedure\n")
        with pytest.raises(AssertionError, match="changed|stale"):
            consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **reentry})
        method.write_bytes(original)
    dependency.write_text("Changed domain rule.\n")
    with pytest.raises(AssertionError, match="changed|stale"):
        call(export)
    assert source.read_text() == BASE


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_missing_or_unreviewed_inputs_never_construct_manual_assignment(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    context = {"target": str(tmp_path), "task": "Explain a bounded supplied rule", "changed": []}

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)
    request = offered["task_requirements"]["handoff_inputs"]["requests"][0]
    request[-1]["arguments"].update(input_refs=["missing.md"], reason="This named input is necessary.", complete=True)
    with pytest.raises(AssertionError, match="observed|changed"):
        call(request)
    request[-1]["arguments"]["complete"] = False
    missing = call(request)
    assert "missing" in str(missing["task_requirements"]["handoff_inputs"]["gaps"])
    complete = missing["task_requirements"]["handoff_inputs"]["requests"][0]
    complete[-1]["arguments"]["complete"] = True
    still_missing = call(complete)
    manual = next(
        r
        for r in still_missing["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"]
    assert any(b["code"] == "current-binding-assignment-required" for b in still_missing["decision_packet"]["blockers"])
    (tmp_path / "missing.md").write_text("The required rule is now supplied.")
    with pytest.raises(AssertionError, match="changed"):
        call(complete)
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_readonly_handoff_does_not_gain_mutation_capability(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    context = {"target": str(tmp_path), "task": "Prepare a bounded file change", "changed": []}

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["unapplied-patch"]
    request = call(task)["task_requirements"]["handoff_inputs"]["requests"][0]
    request[-1]["arguments"].update(reason="The task description is the complete input.", complete=False)
    current = call(request)["task_requirements"]["handoff_inputs"]["requests"][0]
    current[-1]["arguments"]["complete"] = True
    result = call(current)
    manual = next(
        r
        for r in result["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"] and "result-class-unavailable" in manual["reasons"]
    assert result["task_requirements"]["handoff"]["requests"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_shared_seal_preserves_only_exact_known_unicode_checksum(tmp_path, shared_core_binary):
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    installed = native_artifact_consumers.CURRENT
    packet = {
        "assignment_id": "a",
        "assignment_revision": "revision",
        "run_id": "r",
        "target": "worker",
        "assignment_identity": {"human_intent": "Explain blå", "allowed_paths": []},
        "return_contract": {"required_fields": ["assignment_revision"]},
    }

    def call(action, value):
        payload = {"action": action, "packet": value}
        env = {**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
        # Seal/integrity is a shared-core fixture, not an installed public language API.
        command = [str(shared_core_binary)]
        stdin = json.dumps({"assignment_packet": payload})
        if installed:
            env = {
                k: v for k, v in os.environ.items() if k not in {"AGENTIC_WORKSPACE_CORE_BINARY", "PYTHONPATH", "PYTHONHOME", "NODE_PATH"}
            }
            env["PATH"] = ""
        result = subprocess.run(
            command, input=stdin, text=True, encoding="utf-8", capture_output=True, env=env, cwd=installed["cwd"] if installed else root
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    sealed = call("seal", packet)
    blank = copy.deepcopy(sealed)
    blank["packet_integrity"] = ""
    for contract in [blank["return_contract"], blank["worker_context"]["return_contract"]]:
        contract["required_identity"]["packet_integrity"] = ""

    def checksum(ascii_only):
        return (
            "sha256:"
            + hashlib.sha256(json.dumps(blank, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only).encode()).hexdigest()
        )

    assert sealed["packet_integrity"] == checksum(True)
    legacy = copy.deepcopy(sealed)
    legacy["packet_integrity"] = checksum(False)
    for contract in [legacy["return_contract"], legacy["worker_context"]["return_contract"]]:
        contract["required_identity"]["packet_integrity"] = legacy["packet_integrity"]
    assert call("integrity", legacy)["integrity"] == legacy["packet_integrity"]
    assert call("seal", legacy)["packet_integrity"] == sealed["packet_integrity"]
    changed = copy.deepcopy(legacy)
    changed["assignment_identity"]["human_intent"] = "Other work"
    assert call("integrity", changed)["integrity"] != legacy["packet_integrity"]
    unknown = copy.deepcopy(legacy)
    unknown["packet_integrity"] = "sha256:unknown-codec"
    assert call("integrity", unknown)["integrity"] != "sha256:unknown-codec"


def test_real_packed_packet_owner_without_python_or_checkout(packed, tmp_path):
    import os
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node
    from aw_maintainer.native_conformance import assignment_packet

    payload = {
        "action": "seal",
        "packet": {
            "assignment_id": "a",
            "assignment_revision": "r",
            "run_id": "one",
            "target": "manual",
            "assignment_identity": {"human_intent": "A bounded explanation", "input_capsule": []},
            "return_contract": {},
        },
    }
    # Fixture construction uses the source owner; the isolated installed worker
    # entry consumes only this sealed packet through its current public CLI.
    sealed = assignment_packet(payload)
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    result = subprocess.run(
        [
            node,
            str(packed / "src/cli.mjs"),
            "worker",
            "--input",
            "-",
            "--format",
            "json",
        ],
        cwd=tmp_path,
        input=json.dumps({"action": "entry", "packet": sealed}),
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["view"]["intent"]["outcome"] == "A bounded explanation"
    assert packet["view"]["proof"]["worker_authority"] is False
