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
        "assert p['worker_context']['inputs']['source_work']['producer']=='planning'\n"
        "print(json.dumps({**p['return_contract']['required_identity'],"
        "'kind':'agentic-workspace/delegated-return/v1','result_delivery':'unapplied-patch',"
        "'summary':p['worker_context']['inputs']['source_work']['outcome']['intent']['outcome'],"
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
    dependency = tmp_path / "accepted.txt"
    dependency.write_text("Accepted prerequisite.\n")
    revision = "sha256:" + hashlib.sha256(dependency.read_bytes()).hexdigest()

    contexts = {}

    def call(task, request=None, invocation=None):
        return consume(
            "native",
            shared_core_binary,
            native_cli,
            {
                "target": str(tmp_path),
                "task": task,
                "changed": [],
                **contexts.get(task, {}),
                **({"request": request} if request is not None else {}),
                **({"invocation": invocation} if invocation is not None else {}),
            },
        )

    def act(task, view, operation):
        action = next(a for a in view["decision_packet"]["ready_actions"] if a["operation_id"] == operation)
        return call(task, invocation=action)

    children = []
    for number in (1, 2):
        task = f"Analyse child {number}"
        source = material()
        source.update(
            title=task,
            owner_level="slice",
            intent={"outcome": task},
            blockers=[],
            parent={"lane": "shared-parent"},
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
        choice = next(
            r
            for r in offered["task_requirements"]["execution_configurations"]["requests"]
            if r[-1]["arguments"]["candidate"] == "worker:cli"
        )
        assigned = call(task, [selection, *choice])
        assert assigned["task_requirements"]["assignment"]["result"]["judgment"] is None
        export = assigned["task_requirements"]["handoff"]["requests"][0]
        exported = call(task, export)
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
        assert body["parent"] == {"lane": "shared-parent"}
    assert len({json.dumps(v, sort_keys=True) for v in pending.values()}) == 2
