"""Actual local source and executable observations, no provider sessions."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def fixture(root: Path):
    (root / "a.txt").write_text("current")
    executable = root / ("worker.cmd" if os.name == "nt" else "worker")
    executable.write_text("echo never-run > marker.txt")
    executable.chmod(0o755)
    source = root / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        '[safety]\nsafe_to_auto_run_commands=true\n[delegation]\nassignment_policy="required-best-fit"\ntransport_authority="automatic"\ncurrent_target="local"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n[delegation_targets.worker]\nconfidence=0.4\nconfidence_source="human estimate"\ntransports=[{kind="process",command=['
        + json.dumps(str(executable))
        + "]}]\n"
    )
    return source, executable, {"target": str(root), "task": "Inspect current source", "changed": ["a.txt"]}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_configuration_choice_is_feasibility_not_assignment(tmp_path, shared_core_binary, native_cli, surface):
    source, executable, context = fixture(tmp_path)

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    first = call(context)
    judgment = first["task_requirements"]["requests"][0]
    judgment["arguments"]["required_result_classes"] = ["read-only"]
    offered = call({**context, "request": judgment})["task_requirements"]["execution_configurations"]
    rows = {r["configuration"]["id"]: r for r in offered["configurations"]["candidates"]}
    human = next(row for row in offered["target_context"] if row["target"] == "worker")
    assert human["human_prior"]["confidence"] == 0.4
    comparison = call({**context, "request": judgment})["task_requirements"]["assignment"]["result"]
    prior = next(row for row in comparison["alternatives"] if row["id"] == "worker:cli")
    assert prior["human_prior"]["confidence"] == 0.4
    assert prior["human_prior"]["provenance"] == "human estimate"
    assert rows["local:internal"]["eligible"] is True
    assert rows["worker:cli"]["eligible"] is True
    assert rows["worker:cli"]["configuration"]["result_classes"] == ["read-only", "unapplied-patch"]
    assert rows["worker:manual"]["eligible"] is False
    assert "execution-return-unconstructible" in rows["worker:manual"]["reasons"]
    manual = offered["manual_targets"][0]
    assert manual["source_policy_eligible"] is True
    assert manual["handoff_constructible"] is False
    assert manual["automatic_invocation"] is False
    assert manual["gap"] == "native-manual-input-completeness-unresolved"
    assert manual["target_best_fit"] == "unresolved-not-rejected"
    assert all(r["configuration"]["proof_classes"] == [] and r["configuration"]["independent_context"] is False for r in rows.values())
    request = next(r for r in offered["requests"] if r[-1]["arguments"]["candidate"] == "worker:cli")
    judgment["arguments"]["required_result_classes"] = ["unapplied-patch"]
    mutation_result = call({**context, "request": judgment})
    mutation = mutation_result["task_requirements"]["execution_configurations"]
    mutation_rows = {r["configuration"]["id"]: r for r in mutation["configurations"]["candidates"]}
    assert mutation_rows["local:internal"]["eligible"] is True
    assert mutation_rows["worker:cli"]["eligible"] is True
    assert any(r[-1]["arguments"]["candidate"] == "worker:cli" for r in mutation["requests"])
    assert mutation_result["task_requirements"]["handoff"]["status"] == "not-ready"
    assert mutation_result["decision_packet"]["primary_action"] is None
    judgment["arguments"]["required_result_classes"] = ["already-materialized"]
    unsupported = call({**context, "request": judgment})["task_requirements"]["execution_configurations"]
    unsupported_worker = next(r for r in unsupported["configurations"]["candidates"] if r["configuration"]["id"] == "worker:cli")
    assert unsupported_worker["eligible"] is False
    assert "result-class-unavailable" in unsupported_worker["reasons"]
    selected = call({**context, "request": request})
    assert selected["task_requirements"]["execution_configurations"]["configurations"]["selected"]["id"] == "worker:cli"
    assert selected["decision_packet"].get("primary_action") is None
    assert any("effect:implementation" in row["affects"] for row in selected["decision_packet"]["blockers"])
    assert not (tmp_path / "marker.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
    with pytest.raises(AssertionError, match="stale|changed"):
        call({**context, "task": "A different requested outcome", "request": request})
    before_stat = executable.stat()
    original = executable.read_bytes()
    replacement = original.replace(b"echo", b"ECHO", 1)
    assert replacement != original and len(replacement) == len(original)
    executable.write_bytes(replacement)
    os.utime(executable, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
    assert executable.stat().st_mtime_ns == before_stat.st_mtime_ns

    stale = call({**context, "request": request})["task_requirements"]["execution_configurations"]["configurations"]
    assert stale["reason_code"] == "assignment-configuration-choice-stale"
    source.write_text(source.read_text().replace('transport_authority="automatic"', 'transport_authority="manual"'))
    with pytest.raises(AssertionError, match="stale|changed"):
        call({**context, "request": request})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_missing_capability_and_safety_keep_execution_unavailable(tmp_path, shared_core_binary, native_cli, surface):
    source, executable, context = fixture(tmp_path)
    executable.unlink()

    def preview():
        first = consume(surface, shared_core_binary, native_cli, context)
        request = first["task_requirements"]["requests"][0]
        request["arguments"]["required_result_classes"] = ["read-only"]
        return consume(surface, shared_core_binary, native_cli, {**context, "request": request})["task_requirements"][
            "execution_configurations"
        ]

    rows = {r["configuration"]["id"]: r for r in preview()["configurations"]["candidates"]}
    assert "execution-return-unconstructible" in rows["worker:cli"]["reasons"]
    assert rows["worker:manual"]["eligible"] is False
    assert "execution-return-unconstructible" in rows["worker:manual"]["reasons"]
    source.write_text(source.read_text().replace("safe_to_auto_run_commands=true", "safe_to_auto_run_commands=false"))
    rows = {r["configuration"]["id"]: r for r in preview()["configurations"]["candidates"]}
    assert rows["worker:manual"]["eligible"] is False
    assert "independent-safety-ceiling" in rows["worker:cli"]["reasons"]


def test_unsupported_transport_authoring_fails_closed(tmp_path, shared_core_binary, native_cli):
    source, _, context = fixture(tmp_path)
    baseline = source.read_text()
    for declaration in (
        'kind="native",adapter="provider-owned"',
        'kind="api",command=["ignored"]',
        'kind="process",command=["ignored"],output_mode="json-file"',
        'kind="internal",timeout_seconds=30',
        'kind="process",command=["ignored"],invented=true',
    ):
        source.write_text(baseline + "[delegation_targets.invalid]\ntransports=[{" + declaration + "}]\n")
        before = source.read_bytes()
        invalid = consume("native", shared_core_binary, native_cli, context)
        assert invalid["status"] == "blocked"
        assert invalid["managed_state_interpreted"] is False
        assert source.read_bytes() == before
        assert not (tmp_path / "marker.txt").exists()


def test_oversized_executable_is_unavailable_without_reading_or_running(tmp_path, shared_core_binary, native_cli):
    _, executable, context = fixture(tmp_path)
    with executable.open("r+b") as stream:
        stream.truncate(134_217_729)
    first = consume("json", shared_core_binary, native_cli, context)
    request = first["task_requirements"]["requests"][0]
    request["arguments"]["required_result_classes"] = ["read-only"]
    result = consume("json", shared_core_binary, native_cli, {**context, "request": request})["task_requirements"][
        "execution_configurations"
    ]
    row = next(r for r in result["configurations"]["candidates"] if r["configuration"]["id"] == "worker:cli")
    assert row["configuration"]["constructible"] is False
    assert "execution-return-unconstructible" in row["reasons"]
    assert not (tmp_path / "marker.txt").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_internal_binding_requires_current_host_facts_before_local_comparison(tmp_path, shared_core_binary, native_cli, surface):
    source, _, context = fixture(tmp_path)
    prefix = source.read_text().split("[delegation_targets.worker]")[0]
    internal = prefix + '[delegation_targets.worker]\ntransports=[{kind="internal"}]\n'
    source.write_text(internal)

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    def requirements():
        request = call()["task_requirements"]["requests"][0]
        request["arguments"]["required_result_classes"] = ["unapplied-patch"]
        return call(request)

    def local_choice(state):
        request = state["task_requirements"]["assignment"]["requests"][0]
        request[-1]["arguments"].update(alternative="local:internal", reason="Retain current host after feasibility comparison.")
        return call(request)

    unknown = requirements()
    unresolved = unknown["task_requirements"]["assignment"]["result"]["unresolved_alternatives"]
    assert any(row["gap"] == "host-internal-capability-unbound" and row["status"] == "unknown" for row in unresolved)
    assert local_choice(unknown)["task_requirements"]["implementation_admission"]["status"] == "assessment-required"
    assert not (tmp_path / ".agentic-workspace/local").exists()

    # Bind the intended target to the existing supported bridge, without a new
    # target identity, capability flag, provider registry or dispatch instruction.
    worker = tmp_path / "host.py"
    worker.write_text(
        "import json\nfrom pathlib import Path\n"
        "from agentic_workspace import sealed_codex_transport as host\n"
        "def discover(*args,**kwargs):\n"
        " assert kwargs=={'refresh':True,'persist':False}\n"
        " Path('probe-called.txt').write_text('observed')\n"
        " state=Path('capability-state.txt').read_text()\n"
        " if state=='unknown': raise host.native_transport.ProviderError('discovery-interrupted')\n"
        " return {'revision':state,'expires_at':99999999999,'modes':['fresh'],'parameters':['model'],'models':[{'model':state}]}\n"
        "host.native_transport.discover=discover\n"
        "host.main()\n"
    )
    state_path = tmp_path / "capability-state.txt"
    state_path.write_text("available")
    bound = (
        prefix
        + '[delegation_targets.worker]\ntransports=[{kind="native",adapter="codex-app-server/v1",parameters={model="available"},command='
        + json.dumps([sys.executable, str(worker)])
        + "}]\n"
    )
    source.write_text(bound)
    available = requirements()
    execution = available["task_requirements"]["execution_configurations"]
    row = next(r for r in execution["configurations"]["candidates"] if r["configuration"]["id"] == "worker:native:codex-app-server/v1")
    assert row["eligible"] and row["configuration"]["constructible"]
    assert row["configuration"]["result_classes"] == ["read-only", "unapplied-patch"]
    assert row["configuration"]["execution"]["host_capability"]["status"] == "available"
    assert local_choice(available)["task_requirements"]["implementation_admission"]["status"] == "admitted-local"

    inputs = available["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(input_refs=["a.txt"], complete=False, reason="One exact implementation subject.")
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    ready = call(inputs)["task_requirements"]
    assessment = ready["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(
        alternative="worker:native:codex-app-server/v1", reason="Use the currently available worker for this bounded patch."
    )
    selected = call(assessment)
    assert selected["task_requirements"]["implementation_admission"]["status"] == "admitted-nonlocal"
    export = selected["task_requirements"]["handoff"]["requests"][0]
    frontier = call(export)
    assert any(action["operation_id"] == "delegation.dispatch" for action in frontier["decision_packet"]["ready_actions"])
    assert not (tmp_path / ".agentic-workspace/local").exists()

    (tmp_path / "probe-called.txt").unlink()
    source.write_text(bound.replace('assignment_policy="required-best-fit"', 'assignment_policy="local-preferred"'))
    requirements()
    assert not (tmp_path / "probe-called.txt").exists()
    source.write_text(bound.replace("safe_to_auto_run_commands=true", "safe_to_auto_run_commands=false"))
    requirements()
    assert not (tmp_path / "probe-called.txt").exists()

    state_path.write_text("unavailable")  # complete current model list excludes the configured model
    source.write_text(bound)
    with pytest.raises(AssertionError, match="stale|changed"):
        call(assessment)
    unavailable = requirements()
    assert unavailable["task_requirements"]["assignment"]["result"]["unresolved_alternatives"] == []
    assert local_choice(unavailable)["task_requirements"]["implementation_admission"]["status"] == "admitted-local"
    state_path.write_text("unknown")
    assert local_choice(requirements())["task_requirements"]["implementation_admission"]["status"] == "assessment-required"
    state_path.write_text("available")
    source.write_text(bound.replace('model="available"', 'model="changed"'))
    with pytest.raises(AssertionError, match="stale|changed"):
        call(assessment)
    assert not (tmp_path / ".agentic-workspace/local").exists()
