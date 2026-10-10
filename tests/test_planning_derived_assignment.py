"""Two source-shaped children keep independent work and return custody."""

from __future__ import annotations

import hashlib
import json
import sys

from tests.test_native_planning_create import material
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_two_children_keep_source_context_and_returns(tmp_path, shared_core_binary, native_cli):
    config = tmp_path / ".agentic-workspace/config.local.toml"
    config.parent.mkdir()
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json,sys\np=json.load(sys.stdin)\n"
        "from pathlib import Path\nPath('worker-ran.txt').write_text('dispatched')\n"
        "assert p['worker_context']['inputs']['source_work']['producer']=='planning'\n"
        "print(json.dumps({**p['return_contract']['required_identity'],"
        "'kind':'agentic-workspace/delegated-return/v1','result_delivery':'unapplied-patch',"
        "'summary':p['worker_context']['inputs']['source_work']['outcome']['intent']['outcome'],"
        "'patch':'','changed_paths':[],'stop_conditions_hit':[]}))\n"
    )
    config.write_text(
        "[safety]\nsafe_to_auto_run_commands=true\n[delegation]\n"
        'assignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="automatic"\n'
        '[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
        '[delegation_targets.worker]\nexecution_guarantees=["bounded-analysis"]\n'
        'transports=[{kind="process",command=' + json.dumps([sys.executable, str(worker)]) + ",timeout_seconds=30}]\n"
    )
    dependency = tmp_path / "accepted.txt"
    dependency.write_text("Accepted prerequisite.\n")
    revision = "sha256:" + hashlib.sha256(dependency.read_bytes()).hexdigest()
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        '[execution_posture."repo/child-analysis"]\npreferred_execution_guarantees=["bounded-analysis"]\n'
    )
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "child-analysis", "semantic_routes": ["repo/child-analysis"]}]}))

    contexts = {}

    def call(task, request=None, invocation=None):
        retained = contexts.get(task, {})
        if invocation is not None:
            retained = {key: value for key, value in retained.items() if key != "request"}
        if request is not None:
            supplied = request if isinstance(request, list) else [request]
            peer_routes = [
                r
                for r in contexts.get(task, {}).get("request", [])
                if r["owner"] == "semantic-routes"
                and not any(s["owner"] == r["owner"] and s["request_kind"] == r["request_kind"] for s in supplied)
            ]
            request = [*peer_routes, *[r for r in supplied if r not in peer_routes]]
        return consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                "target": str(tmp_path),
                "task": task,
                "changed": [],
                **retained,
                **({"request": request} if request is not None else {}),
                **({"invocation": invocation} if invocation is not None else {}),
            },
        )

    def act(task, view, operation):
        action = next(a for a in view["decision_packet"]["ready_actions"] if a["operation_id"] == operation)
        result = call(task, invocation=action)
        if result.get("continuation_status") == "current":
            contexts[task] = result["continuation"]["context"]
        return result

    parent_task = "Coordinate and integrate two independently shaped child analyses"
    parent_material = material()
    parent_material.update(
        title=parent_task,
        owner_level="lane",
        intent={"outcome": parent_task},
        blockers=[],
        scope={
            "included": ["Coordinate the two bounded child outcomes and integrate their results"],
            "excluded": ["Reauthor accepted child context"],
        },
        canonical_core={"children": ["Analyse child 1", "Analyse child 2"], "parent_work": "Coupled coordination and integration"},
        continuation={"frontier": "The child definitions reuse accepted.txt; the parent coordinates their results."},
        proof={"remaining": ["Keep each child's accepted sources and return custody distinct."]},
    )
    parent_creation = call(parent_task)["planning"]["creation_requests"][0]
    parent_creation["arguments"]["material"] = parent_material
    parent_created = act(parent_task, call(parent_task, parent_creation), "planning.create")
    contexts[parent_task] = parent_created["continuation"]["context"]
    parent_id = parent_created["value"]["owner_id"]
    requirements = call(parent_task)["task_requirements"]["requests"][0]
    requirements["arguments"]["required_result_classes"] = ["read-only"]
    parent_choice = call(parent_task, requirements)["task_requirements"]["assignment"]["requests"][0]
    parent_choice[-1]["arguments"].update(
        alternative="local:internal",
        reason="Keep coupled parent coordination and integration local; compare the already shaped independent children separately.",
    )
    parent_admitted = call(parent_task, parent_choice)
    assert parent_admitted["task_requirements"]["implementation_admission"]["status"] == "admitted-local"
    parent_compact = consume(
        "native",
        shared_core_binary,
        native_cli,
        {
            **contexts[parent_task],
            "task": parent_task,
            "request": parent_choice,
            "projection": "compact",
        },
    )
    assert parent_compact["assignment_context"]["handoff_preparation"]["planning_definition"] == "not-declared"
    assert not (tmp_path / "worker-ran.txt").exists()

    children = []
    for number in (1, 2):
        task = f"Analyse child {number}"
        source = material()
        source.update(
            title=task,
            owner_level="slice",
            intent={"outcome": task},
            blockers=[],
            parent={"lane": parent_id},
            scope={
                "included": ["Inspect the accepted prerequisite for this child"],
                "excluded": ["Mutate files or grant proof/completion authority"],
            },
            proof={"remaining": ["Return bounded source observations for this child."]},
            continuation={"frontier": task},
            relationships={"dependencies": {"refs": ["accepted.txt"]}},
            assignment_inputs={
                "result_class": "read-only",
                "input_refs": [],
                "mutation_paths": [],
                "required_proof_classes": [],
                "accepted_dependencies": [{"reference": "accepted.txt", "revision": revision}],
            },
        )
        creation = call(task)["planning"]["creation_requests"][0]
        creation["arguments"]["material"] = source
        created = act(task, call(task, creation), "planning.create")
        contexts[task] = created["continuation"]["context"]
        reference = created["value"]["owner_path"]
        selection = call(task)["planning"]["selection_requests"][0]
        selection["arguments"]["owner_ref"] = reference
        ready = call(task, selection)
        route = next(r for r in ready["semantic_routes"]["requests"] if r["request_kind"] == "semantic-routes/select/v1")
        route["arguments"].update(posture="selected", routes=["repo/child-analysis"])
        contexts[task]["request"] = [selection, route]
        ready = call(task)
        assert ready["task_requirements"]["source_work"]["status"] == "ready"
        if number == 1:
            dependency.write_text("Changed prerequisite.\n")
            changed = call(task, selection)["task_requirements"]
            assert changed["source_work"]["status"] == "shaping-required"
            assert changed["result"]["status"] == "unresolved"
            dependency.unlink()
            assert call(task, selection)["task_requirements"]["source_work"]["status"] == "shaping-required"
            dependency.write_text("Accepted prerequisite.\n")
        inputs = ready["task_requirements"]["handoff_inputs"]["requests"][0]
        assert inputs[-1]["arguments"]["input_refs"] == ["accepted.txt"]
        inputs[-1]["arguments"]["complete"] = True
        offered = call(task, [selection, *inputs])
        assert offered["task_requirements"]["result"]["execution_posture"]["preferred_execution_guarantees"] == ["bounded-analysis"]
        compact = consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                **contexts[task],
                "task": task,
                "request": [selection, route, *inputs],
                "projection": "compact",
            },
        )
        preparation = compact["assignment_context"]["handoff_preparation"]
        assert preparation["source_work"]["producer"] == "planning"
        assert preparation["input_refs"] == ["accepted.txt"]
        assert preparation["observed_inputs"] == [{"reference": "accepted.txt", "revision": revision}]
        assert preparation["status"] == "ready" and preparation["prompt_authoring_required"] is False
        assert not (tmp_path / "worker-ran.txt").exists()
        comparison = offered["task_requirements"]["assignment"]["requests"][0]
        comparison[-1]["arguments"].update(
            alternative="worker:cli",
            reason="The independent child reuses its accepted captured source; bounded-analysis preference favors this eligible worker while parent coordination stays local.",
        )
        assigned = call(task, comparison)
        assert assigned["task_requirements"]["assignment"]["result"]["judgment"] is not None
        assert assigned["task_requirements"]["handoff"]["status"] == "export-ready", {
            "assignment_status": assigned["task_requirements"]["assignment"]["result"]["status"],
            "selected": assigned["task_requirements"]["assignment"]["result"]["selected"],
            "inputs_status": assigned["task_requirements"]["handoff_inputs"]["status"],
            "input_gaps": assigned["task_requirements"]["handoff_inputs"]["gaps"],
        }
        ordinary = consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                **contexts[task],
                "task": task,
                "request": comparison,
                "projection": "compact",
            },
        )
        export = ordinary["assignment_context"]["handoff_preparation"]["next_step"]
        exported = consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                **ordinary["reentry"],
                "reference": export["reference"],
                "answer": {},
                "projection": "full",
            },
        )
        act(task, exported, "planning.update")
        children.append((task, reference))

    pending = {}
    for task, reference in children:
        selection = call(task)["planning"]["selection_requests"][0]
        selection["arguments"]["owner_ref"] = reference
        selected = call(task, selection)
        if any(a["operation_id"] == "planning.reconcile" for a in selected["decision_packet"]["ready_actions"]):
            act(task, selected, "planning.reconcile")
            selection = call(task)["planning"]["selection_requests"][0]
            selection["arguments"]["owner_ref"] = reference
            selected = call(task, selection)
        held = selected["planning"]["handoff_continuation"]["retained"]
        assert held["status"] == "assigned"
        pending[reference] = held["assignment_identity"]
        dispatched = act(task, call(task, held["reentry"]["request"]), "delegation.dispatch")
        assert dispatched["value"]["status"] == "returned-unproven"
        observed = call(task, dispatched["value"]["reentry"]["request"])
        act(task, observed, "planning.update")
        selection = call(task)["planning"]["selection_requests"][0]
        selection["arguments"]["owner_ref"] = reference
        retained = call(task, selection)["planning"]["handoff_continuation"]["retained"]
        assert retained["status"] == "returned"
        admission = call(task, retained["reentry"]["request"])["task_requirements"]["assignment"]["result_admission"]["requests"][0]
        admission[-1]["arguments"]["reason"] = "The bounded result matches this child's source outcome."
        accepted = call(task, admission)
        assert accepted["task_requirements"]["assignment"]["result_admission"]["result_use_allowed"] is True
        act(task, accepted, "planning.update")
        body = json.loads((tmp_path / reference).read_bytes())
        assert body["continuation"]["frontier"] == task
        assert body["parent"] == {"lane": parent_id}
    assert len({json.dumps(v, sort_keys=True) for v in pending.values()}) == 2
