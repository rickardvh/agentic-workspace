"""Fresh selected consumers observe actual Configuration consequences."""

from __future__ import annotations

import copy
import json

import pytest
from tests.test_native_maintainer_logging import events
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

TASK = "Configure the requested repository behavior"


def test_setup_assessment_routes_integrates_and_reuses_current_sources(tmp_path, shared_core_binary, native_cli):
    """Native-entry recovery, consumer and currentness; not proof that old skills invoke AW."""
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    source = workspace / "config.toml"
    source.write_text("[workspace]\nenabled=true\n")
    (tmp_path / "README.md").write_text("Repository rules live in GUIDE.md and must reach ordinary agents.\n")
    guide = tmp_path / "GUIDE.md"
    guide.write_text("Use the repository's required review convention.\n")
    # Native entry recovers preceding material without a payload policy.
    # This explicit call does not prove that an old skill invokes the runtime.
    old_skill = workspace / "skills/workspace-startup/SKILL.md"
    old_skill.parent.mkdir(parents=True)
    old_skill.write_text("Keep sufficient direct work direct; use native entry for current facts.\n")
    context = {"target": str(tmp_path), "task": "Fix the parser's empty-input handling"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    def assessment():
        discovery = call()["configuration_write"]["setup_assessment"]["request"]
        return call(request=discovery)["configuration_write"]["setup_assessment"]

    initial = call(projection="compact")
    recovery = next(r for r in initial["consequence_recovery"] if r["owner"] == "configuration")
    assert all(c["affects"] == ["claim:configuration-integration-complete"] for c in recovery["consequences"])
    offered = assessment()
    assert offered["status"] == "assessment-required"
    assert "optional" in json.dumps(offered["material"])
    assert not (workspace / "configuration-assessment.json").exists()

    request = next(r for r in call()["configuration_write"]["requests"] if r["arguments"]["key"] == "workspace.agent_instructions_file")
    request["arguments"]["value"] = "GUIDE.md"
    answer = call(request=request)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"  # Standing repository intent, not a new human prompt.
    action = call(request=answer)["decision_packet"]["primary_action"]
    result = call(invocation=action)
    assert result["effect_outcome"]["status"] == "committed"
    assert "required review convention" in json.dumps(result["configuration_behavior"]["observation"])
    assert assessment()["integration_complete"] is False

    behavior_request = call()["configuration_write"]["behavior_request"]
    behavior_request["arguments"]["concern"] = "instructions"
    witness = call(request=behavior_request)["configuration_behavior"]["setup_witness"]
    record = assessment()["record_request"]
    record["arguments"]["value"]["coverage"] = (
        "Reviewed current setup material against README intent; instruction delivery improves ordinary work. Other optional integrations have no established repository need."
    )
    record["arguments"]["value"]["dispositions"] = [
        {
            "subject": "Instruction source",
            "status": "effective",
            "reason": "GUIDE.md is now delivered by the actual startup consumer.",
            "concern": "instructions",
            "observation": witness,
        },
        {
            "subject": "Other current optional setup",
            "status": "irrelevant",
            "reason": "This repository has no delegation, retained planning or diagnostic requirement.",
        },
    ]
    action = call(request=record)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.write"
    assert call(invocation=action)["effect_outcome"]["status"] == "committed"
    saved = (workspace / "configuration-assessment.json").read_bytes()
    context["task"] = "Document a parser example"
    (tmp_path / "unrelated.txt").write_text("Unrelated repository change")
    assert assessment()["status"] == "settled"
    assert (workspace / "configuration-assessment.json").read_bytes() == saved
    # Common repository filenames alone do not make their edits setup changes.
    for name in ("README.md", "AGENTS.md", "SYSTEM_INTENT.md"):
        (tmp_path / name).write_text("Unrelated documentation edit.\n")
        assert assessment()["status"] == "settled"
        assert (workspace / "configuration-assessment.json").read_bytes() == saved
    # Managed-only identity changes request bounded refresh, not semantic review.
    provenance = workspace / "payload-provenance.json"
    provenance.write_text(json.dumps({"release_identity": {"version": "1.1.0"}, "managed_revision": "prior-managed-bytes"}))
    changed = call()["configuration_write"]
    assert changed["managed_refresh"]["required"] is True
    assert changed["setup_assessment"]["status"] == "settled"
    assert changed["setup_assessment"]["assessment_due"] is False
    provenance.write_text(
        json.dumps({"release_identity": {"version": "1.1.0"}, "managed_revision": changed["managed_refresh"]["revision"]})
    )
    assert call()["configuration_write"]["managed_refresh"]["required"] is False
    assert (workspace / "configuration-assessment.json").read_bytes() == saved
    # A skipped compatible version with the same setup basis is quiet. A source
    # material change under the same version is not hidden by a version stamp.
    path = workspace / "configuration-assessment.json"
    baseline = json.loads(saved)
    baseline["runtime_version"] = "1.0.0"
    path.write_text(json.dumps(baseline))
    assert assessment()["status"] == "settled"
    assert "record_request" not in assessment()
    baseline["basis"] = "sha256:preceding-setup-material"
    path.write_text(json.dumps(baseline))
    assert assessment()["status"] == "assessment-required"
    path.write_bytes(saved)
    guide.write_text("Changed review convention.\n")
    assert assessment()["status"] == "assessment-required"
    assert "GUIDE.md" in assessment()["changed_dependencies"]


def test_setup_dispositions_preserve_unfinished_and_incompatible_state(tmp_path, shared_core_binary, native_cli):
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text("[workspace]\nenabled=true\n")
    context = {"target": str(tmp_path), "task": "Implement ordinary repository work"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    def assessment():
        request = call()["configuration_write"]["setup_assessment"]["request"]
        return call(request=request)["configuration_write"]["setup_assessment"]

    record = assessment()["record_request"]
    record["arguments"]["value"]["coverage"] = "Current setup material considered; local diagnostics need a new privacy choice."
    record["arguments"]["value"]["continuation"] = {"task": context["task"]}
    record["arguments"]["value"]["dispositions"] = [
        {
            "subject": "Diagnostics",
            "status": "deferred",
            "reason": "No standing privacy authorisation",
            "resume": "Use Configuration diagnostics with the source owner to resolve local capture policy.",
        }
    ]
    action = call(request=record)["decision_packet"]["primary_action"]
    assert call(invocation=action)["effect_outcome"]["status"] == "committed"
    assert assessment()["status"] == "unfinished"
    context["task"] = "Continue a different ordinary task"
    assert assessment()["record"]["dispositions"][0]["resume"]
    unchanged = call()["configuration_write"]
    assert unchanged["setup_assessment"]["review_complete"] is True
    assert unchanged["setup_assessment"]["integration_complete"] is False
    assert unchanged["setup_assessment"]["assessment_due"] is False
    assert "configuration-assessment-required" not in json.dumps(call()["decision_packet"])
    revisit = unchanged["setup_assessment"]["request"]
    revisit["arguments"]["reconsider"] = True
    assert call(request=revisit)["configuration_write"]["setup_assessment"]["assessment_due"] is True
    local_read = call()["configuration_write"]["setup_assessment"]["request"]
    local_read["arguments"]["scope"] = "machine-local"
    local = call(request=local_read)["configuration_write"]["setup_assessment"]["record_request"]
    for field in ("coverage", "dispositions", "continuation"):
        local["arguments"]["value"][field] = copy.deepcopy(record["arguments"]["value"][field])
    assert call(invocation=call(request=local)["decision_packet"]["primary_action"])["effect_outcome"]["status"] == "committed"
    (workspace / "config.local.toml").write_text("[session_logging]\nenabled=false\n")
    scoped = call()["configuration_write"]
    assert scoped["setup_assessment"]["status"] == "unfinished"
    assert scoped["local_setup_assessment"]["status"] == "assessment-required"

    invalid = assessment()["record_request"]
    invalid["arguments"]["value"]["coverage"] = "reviewed"
    invalid["arguments"]["value"]["dispositions"] = [
        {"subject": "Modules", "status": "effective", "reason": "Enabled flag", "concern": "modules", "observation": {}}
    ]
    with pytest.raises(AssertionError, match="consumer effectiveness"):
        call(request=invalid)

    # The same filename is relevant when deliberately selected for a judgment.
    selected = call()["configuration_write"]["setup_assessment"]["request"]
    selected["arguments"]["dependencies"] = ["README.md"]
    relevant = call(request=selected)["configuration_write"]["setup_assessment"]["record_request"]
    assert call(invocation=call(request=relevant)["decision_packet"]["primary_action"])["effect_outcome"]["status"] == "committed"
    stale = assessment()["record_request"]
    (tmp_path / "README.md").write_text("Changed standing intent")
    assert assessment()["assessment_due"] is True
    assert "README.md" in assessment()["changed_dependencies"]
    with pytest.raises(AssertionError, match="basis changed"):
        call(request=stale)

    path = workspace / "configuration-assessment.json"
    saved = json.loads(path.read_text())
    for version, status in [("99.0.0", "major-transition"), ("1.99.0", "newer-integration-preserved")]:
        saved["runtime_version"] = version
        path.write_text(json.dumps(saved))
        before = path.read_bytes()
        current = assessment()
        assert current["status"] == status
        assert "record_request" not in current
        payload = call()["configuration_write"]["payload_discovery_request"]
        edit = next(
            row["request"]
            for row in call(request=payload)["configuration_write"]["payload_choices"]
            if row["source"] == ".agentic-workspace/OWNERSHIP.toml"
        )
        with pytest.raises(AssertionError, match="preserve package integration"):
            call(request=edit)
        assert path.read_bytes() == before
    path.write_text('{"kind":"future-format"}')
    assert assessment()["status"] == "unavailable"
    (workspace / "config.toml").write_text("[workspace]\nenabled=false\n")
    assert "setup_assessment" not in call()["configuration_write"]


@pytest.mark.parametrize(
    "key,value,source_name",
    [
        ("workspace.agent_instructions_file", "GUIDE.md", "config.toml"),
        ("session_logging.path_mode", "redacted", "config.local.toml"),
        ("modules.enabled", ["memory"], "config.toml"),
    ],
)
def test_native_write_reports_affected_owner_behavior(tmp_path, shared_core_binary, native_cli, monkeypatch, key, value, source_name):
    source = tmp_path / ".agentic-workspace" / source_name
    source.parent.mkdir()
    source.write_text(
        '[session_logging]\nenabled=true\npath_mode="absolute"\n' if key.startswith("session_logging") else "[workspace]\nenabled=true\n"
    )
    (tmp_path / "GUIDE.md").write_text("Read this repository-owned instruction before affected work.\n")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "configuration-consequence-fixture")
    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE", raising=False)
    context = {"target": str(tmp_path), "task": TASK}

    def call(allow_failure=False, **extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, allow_failure=allow_failure)

    current = call()
    request = next(r for r in current["configuration_write"]["requests"] if r["arguments"]["key"] == key)
    request["arguments"]["value"] = value
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.write"
    native = call(invocation=action)
    assert native["effect_outcome"]["status"] == "committed"
    behavior = native["configuration_behavior"]
    assert behavior["status"] == "observed"
    assert behavior["completion_authority"] is False
    observed = behavior["observation"]
    if key == "workspace.agent_instructions_file":
        assert observed["selected_source"] == "GUIDE.md"
        assert "GUIDE.md" in json.dumps(observed["current"])
        assert observed["current"]["status"] == "source-context-delivered"
        assert "Read this repository-owned instruction" in json.dumps(observed["current"]["response"])
    elif key.startswith("session_logging"):
        assert observed["effective_policy"] == {"enabled": True, "path_mode": "redacted"}
        assert native["session_capture"]["status"] == "capturing"
        last = events(tmp_path)[-1]
        assert last["payload"]["entry"]["command"] == "agentic-workspace invoke"
        assert str(tmp_path) not in json.dumps(last)
    else:
        assert observed["enabled"] == ["memory"]
        assert observed["memory"]["status"] == "absent"
        assert observed["memory"]["status"] != "ready"  # Missing module-owned admission stays a gap.
    before = source.read_bytes()
    stale = call(invocation=action, allow_failure=True)
    assert stale["effect_outcome"]["status"] == "rejected-before-effect"
    assert source.read_bytes() == before


def test_assignment_observation_does_not_acquire_a_requirement_writer(tmp_path, shared_core_binary, native_cli):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        '[delegation]\nassignment_policy="required-best-fit"\nrequired_execution_guarantees=["history.non-persisted"]\n[delegation_targets.worker]\ntarget_id="host:worker"\nlocation="external"\ntransports=[{kind="manual"}]\n'
    )

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": TASK, **extra})

    request = call()["configuration_write"]["behavior_request"]
    request["arguments"]["concern"] = "assignment"
    current = call(request=request)
    behavior = current["configuration_behavior"]
    assert behavior["observation"]["write_boundary"]["status"] == "unavailable"
    assert "history.non-persisted" in json.dumps(behavior)
    assert behavior["completion_authority"] is False
    judgment = current["task_requirements"]["requests"][0]
    judgment["arguments"]["required_result_classes"] = ["read-only"]
    observation = current["configuration_write"]["behavior_request"]
    observation["arguments"]["concern"] = "assignment"
    judged = call(request=[judgment, observation])
    requirements = judged["configuration_behavior"]["observation"]["requirements"]
    assert requirements["result"]["requirements"]["required_execution_guarantees"] == ["history.non-persisted"]
    candidate = requirements["execution_configurations"]["configurations"]["candidates"][0]
    assert candidate["eligible"] is False
    assert "required-execution-guarantee-unavailable" in candidate["reasons"]
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()
