"""Fresh selected consumers observe actual Configuration consequences."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_maintainer_logging import events
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
TASK = "Configure the requested repository behavior"
SKILL = Path(".agentic-workspace/skills/workspace-setup-jumpstart")


def helper(target, native_cli, *args):
    folder = target / SKILL
    if not folder.exists():
        shutil.copytree(ROOT / SKILL, folder)
    result = subprocess.run(
        [sys.executable, str(folder / "prepare.py"), "--native-cli", str(native_cli), "--target", str(target), "--task", TASK, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.stdout, result.stderr
    return result.returncode, json.loads(result.stdout)


@pytest.mark.parametrize(
    "key,value,source_name",
    [
        ("workspace.agent_instructions_file", "GUIDE.md", "config.toml"),
        ("session_logging.path_mode", "redacted", "config.local.toml"),
        ("modules.enabled", ["memory"], "config.toml"),
    ],
)
def test_fresh_method_carries_exact_write_to_affected_owner(tmp_path, shared_core_binary, native_cli, monkeypatch, key, value, source_name):
    source = tmp_path / ".agentic-workspace" / source_name
    source.parent.mkdir()
    source.write_text(
        '[session_logging]\nenabled=true\npath_mode="absolute"\n' if key.startswith("session_logging") else "[workspace]\nenabled=true\n"
    )
    (tmp_path / "GUIDE.md").write_text("Read this repository-owned instruction before affected work.\n")
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "configuration-consequence-fixture")
    monkeypatch.delenv("AW_SESSION_LOGGING_DISABLE", raising=False)
    context = {"target": str(tmp_path), "task": TASK}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra})

    current = call()
    request = next(r for r in current["configuration_write"]["requests"] if r["arguments"]["key"] == key)
    request["arguments"]["value"] = value
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.write"
    action_path = tmp_path / "authorized-action.json"
    action_path.write_text(json.dumps(action))
    code, result = helper(tmp_path, native_cli, "--input", str(action_path))
    assert code == 0, result
    assert result["owner_calls"] == 1
    native = result["native_result"]
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
    code, stale = helper(tmp_path, native_cli, "--input", str(action_path))
    assert code == 2
    assert stale["native_result"]["effect_outcome"]["status"] == "rejected-before-effect"
    assert source.read_bytes() == before


def test_assignment_observation_does_not_acquire_a_requirement_writer(tmp_path, shared_core_binary, native_cli):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        '[delegation]\nassignment_policy="required-best-fit"\nrequired_execution_guarantees=["history.non-persisted"]\n[delegation_targets.worker]\ntarget_id="host:worker"\nlocation="external"\ntransports=[{kind="manual"}]\n'
    )
    code, result = helper(tmp_path, native_cli, "--concern", "assignment")
    assert code == 0, result
    behavior = result["native_result"]["configuration_behavior"]
    assert behavior["observation"]["write_boundary"]["status"] == "unavailable"
    assert "history.non-persisted" in json.dumps(behavior)
    assert behavior["completion_authority"] is False
    current = result["native_result"]
    judgment = current["task_requirements"]["requests"][0]
    judgment["arguments"]["required_result_classes"] = ["read-only"]
    observation = current["configuration_write"]["behavior_request"]
    observation["arguments"]["concern"] = "assignment"
    request_path = tmp_path / "judged-behavior.json"
    request_path.write_text(json.dumps([judgment, observation]))
    code, judged = helper(tmp_path, native_cli, "--input", str(request_path))
    assert code == 0, judged
    requirements = judged["native_result"]["configuration_behavior"]["observation"]["requirements"]
    assert requirements["result"]["requirements"]["required_execution_guarantees"] == ["history.non-persisted"]
    candidate = requirements["execution_configurations"]["configurations"]["candidates"][0]
    assert candidate["eligible"] is False
    assert "required-execution-guarantee-unavailable" in candidate["reasons"]
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()


def test_no_change_and_method_currentness_are_selective(tmp_path, native_cli):
    code, initial = helper(tmp_path, native_cli, "--no-change")
    assert code == 0 and initial["owner_calls"] == 0 and initial["retained"] is False
    (tmp_path / "unrelated.txt").write_text("Unrelated work does not change the method.")
    code, same = helper(tmp_path, native_cli, "--no-change", "--expected-method-revision", initial["method_revision"])
    assert code == 0 and same["method_revision"] == initial["method_revision"]
    skill = tmp_path / SKILL / "SKILL.md"
    skill.write_text(skill.read_text() + "\nChanged procedure material.\n")
    code, stale = helper(tmp_path, native_cli, "--concern", "instructions", "--expected-method-revision", initial["method_revision"])
    assert code == 2 and stale["status"] == "stale-method" and stale["owner_calls"] == 0
    assert not (tmp_path / ".agentic-workspace/local").exists()
