"""Owner-captured patch baselines and exact public return/integration lineage."""

from __future__ import annotations

import copy
import json
import sys

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_native_readonly_handoff import BASE


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_patch_return_preserves_concurrent_work_and_replays(tmp_path, shared_core_binary, native_cli, surface):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "p=json.load(sys.stdin)\n"
        "with Path('launches.txt').open('a') as f: f.write('once\\n')\n"
        "print(json.dumps({**p['return_contract']['required_identity'],"
        "'kind':'agentic-workspace/delegated-return/v1','result_delivery':'unapplied-patch',"
        "'changed_paths':['src/main.txt','src/sibling.txt'],'patch':json.dumps([{'path':'src/main.txt',"
        "'diff':'--- original\\n+++ modified\\n@@ -2 +2 @@\\n-two\\n+worker\\n'},"
        "{'path':'src/sibling.txt','diff':'--- original\\n+++ modified\\n@@ -1 +1 @@\\n-before\\n+sibling\\n'}]),"
        "'summary':'Replace the second line with worker.','stop_conditions_hit':[]}))\n"
    )
    config = BASE.replace("[delegation]", "[safety]\nsafe_to_auto_run_commands=true\n[delegation]")
    config = config.replace('transport_authority="manual"', 'transport_authority="automatic"')
    config = config.replace(
        'transports=[{kind="manual"}]',
        'transports=[{kind="process",command=' + json.dumps([sys.executable, str(worker)]) + ",timeout_seconds=30}]",
    )
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(config)
    main = tmp_path / "src/main.txt"
    main.parent.mkdir()
    before = "one\ntwo\nthree\nfour\nfive\nsix\n"
    main.write_bytes(before.replace("\n", "\r\n").encode())
    sibling = tmp_path / "src/sibling.txt"
    sibling.write_bytes(b"before\n")
    (tmp_path / "dependency.txt").write_text("Current exact task constraint.\n")
    context = {"target": str(tmp_path), "task": "Update the second line from the supplied source", "changed": ["src/*.txt"]}

    def call(request=None, **updates):
        return consume(surface, shared_core_binary, native_cli, {**context, **updates, **({"request": request} if request else {})})

    plan_path = None
    if surface == "native":
        from tests.test_native_planning_create import material

        creation = call()["planning"]["creation_requests"][0]
        creation["arguments"] = {"material": material()}
        created = call(invocation=call(creation)["decision_packet"]["primary_action"])
        plan_path = tmp_path / created["value"]["owner_path"]
        selection = call()["planning"]["created_owner"]["selection_request"]
        call(invocation=call(selection)["decision_packet"]["primary_action"])

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["unapplied-patch"]
    inputs = call(task)["task_requirements"]["handoff_inputs"]["requests"][0]
    assert inputs[-1]["request_kind"] == "assignment/judge-patch-inputs/v1"
    inputs[-1]["arguments"].update(
        input_refs=["src/main.txt", "src/sibling.txt", "dependency.txt", "worker.py"],
        mutation_paths=["src/main.txt", "src/sibling.txt"],
        complete=False,
        reason="The source and independent task constraint fully describe the bounded change.",
    )
    forbidden = copy.deepcopy(inputs)
    forbidden[-1]["arguments"].update(
        input_refs=[".agentic-workspace/config.local.toml"], mutation_paths=[".agentic-workspace/config.local.toml"]
    )
    with pytest.raises(AssertionError, match="dedicated owner"):
        call(forbidden)
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    assessment = call(inputs)["task_requirements"]["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(alternative="expert:cli", reason="Use the feasible configured process for this exact patch.")
    export = call(assessment)["task_requirements"]["handoff"]["requests"][0]
    dispatch = call(export)["task_requirements"]["delegation"]["requests"][0]
    action = call(dispatch)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "delegation.dispatch"
    sealed = action["arguments"]["packet"]
    assert sealed["assignment_identity"]["mutation_paths"] == ["src/main.txt", "src/sibling.txt"]
    assert sealed["worker_context"]["scope"]["class"] == "unapplied-patch"
    result = call(invocation=action)
    assert result["value"]["status"] == "returned-unproven", result
    assert main.read_bytes() == before.replace("\n", "\r\n").encode()
    assert call(invocation=action)["value"] == result["value"]
    reentry = result["value"]["reentry"]["request"]

    # Only the sealed mutation baseline is historical. Independent dependencies
    # and policy still observe current source bytes on every return.
    dependency = tmp_path / "dependency.txt"
    old = dependency.read_bytes()
    dependency.write_text("Changed task constraint.\n")
    with pytest.raises(AssertionError, match="changed|stale"):
        call(reentry)
    dependency.write_bytes(old)
    forged = copy.deepcopy(reentry)
    observation = next(r for r in forged if r["request_kind"] == "assignment/observe-patch-return/v1")
    observation["arguments"]["returned"]["summary"] = "Forged worker attribution."
    with pytest.raises(AssertionError, match="differs|retained"):
        call(forged)

    # The concurrent edit is in the same file and allowed pattern. It is never
    # attributed to the worker; only the worker's exact second-line delta is.
    main.write_bytes(before.replace("six", "concurrent").replace("\n", "\r\n").encode())
    judged = call(reentry)["task_requirements"]["assignment"]["result_admission"]["requests"][0]
    judged[-1]["arguments"].update(answer="use-result", reason="The returned delta satisfies the bounded assignment.")
    admitted = call(judged)
    assert admitted["planning"]["adoption_requests"] == []
    proposal = admitted["task_requirements"]["patch_integration"]
    assert proposal["status"] == "proposal-ready", proposal
    request = proposal["requests"][0]
    if surface == "native":
        # The complete escaped carrier, not merely each text file, must fit
        # the recovery reader. Rejection precedes attempt admission.
        ordinary = main.read_bytes()
        main.write_bytes(ordinary + b"\x01" * 180000 + b"\r\n")
        oversized = call(judged)["task_requirements"]["patch_integration"]["requests"][0]
        oversized_action = call(oversized)["decision_packet"]["primary_action"]
        preserved = main.read_bytes()
        with pytest.raises(AssertionError, match="carrier exceeds"):
            call(invocation=oversized_action)
        assert main.read_bytes() == preserved
        assert not (tmp_path / ".agentic-workspace/local/patch-integrations").exists()
        main.write_bytes(ordinary)
    ready = call(request)
    integrate = ready["decision_packet"]["primary_action"]
    assert integrate is not None, json.dumps(ready["decision_packet"], indent=2)
    assert integrate["operation_id"] == "assignment.integrate-patch"
    concurrent_before = main.read_bytes()
    main.write_bytes(concurrent_before.replace(b"two", b"conflicting"))
    with pytest.raises(AssertionError, match="overlaps|changed"):
        call(invocation=integrate)
    assert b"conflicting" in main.read_bytes()
    main.write_bytes(concurrent_before)
    if surface == "native":
        from concurrent.futures import ThreadPoolExecutor

        lock = tmp_path / ".agentic-workspace/local/effects/patch-integration.lock"
        lock.write_bytes(b"Preserve unrecognized lock content.")
        with pytest.raises(AssertionError, match="unrecognized patch integration lock"):
            call(invocation=integrate)
        assert lock.read_bytes() == b"Preserve unrecognized lock content."
        lock.unlink()

        def invoke_same():
            try:
                return call(invocation=integrate)
            except AssertionError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(pool.map(lambda _: invoke_same(), range(2)))
        successful = [result for result in attempts if isinstance(result, dict)]
        assert successful, attempts
        integrated = successful[0]
        assert all(result["value"] == integrated["value"] for result in successful)
    else:
        integrated = call(invocation=integrate)
    expected = before.replace("two", "worker").replace("six", "concurrent").replace("\n", "\r\n").encode()
    assert main.read_bytes() == expected
    assert integrated["value"]["changed_paths"] == ["src/main.txt", "src/sibling.txt"]
    assert sibling.read_bytes() == b"sibling\n"
    assert integrated["value"]["proof_authority"] is False
    assert integrated["value"]["completion_authority"] is False
    assert call(invocation=integrate)["value"] == integrated["value"]
    continued = call(integrated["value"]["reentry"]["request"])
    assert continued["task_requirements"]["patch_integration"]["status"] == "integrated"
    assert continued["task_requirements"]["assignment"]["result_admission"]["integration"]["status"] == "integrated"
    # A committed result cannot silently replay after a target is reverted.
    main.write_bytes(concurrent_before)
    with pytest.raises(AssertionError, match="recovery target"):
        call(invocation=integrate)
    main.write_bytes(expected)
    # Model publication interruption in this isolated fixture: exact retained
    # custody recovers the missing commit without another worker launch.
    commit = tmp_path / integrated["custody"]["committed"]["path"]
    commit.unlink()
    assert call(invocation=integrate)["value"] == integrated["value"]
    # Model an interruption before target publication under the same owner.
    commit.unlink()
    main.write_bytes(concurrent_before)
    assert call(invocation=integrate)["value"] == integrated["value"]
    assert main.read_bytes() == expected
    assert sibling.read_bytes() == b"sibling\n"
    assert (tmp_path / "launches.txt").read_text() == "once\n"
    if plan_path is not None:
        adoption = call(integrated["value"]["reentry"]["request"])["planning"]["adoption_requests"][0]
        adopt_action = call(adoption)["decision_packet"]["primary_action"]
        assert adopt_action["operation_id"] == "planning.update"
        assert adopt_action["arguments"]["consumed_return"]["integration"]["changed_paths"] == ["src/main.txt", "src/sibling.txt"]
        call(invocation=adopt_action)
        assert json.loads(plan_path.read_bytes())["continuation"]["frontier"] == "Replace the second line with worker."
