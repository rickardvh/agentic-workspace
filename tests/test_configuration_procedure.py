"""Fresh selected consumers observe actual Configuration consequences."""

from __future__ import annotations

import json

import pytest
from tests.test_native_maintainer_logging import events
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

TASK = "Configure the requested repository behavior"


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
