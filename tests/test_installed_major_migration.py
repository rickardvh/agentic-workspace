"""Public Configuration composition under a synthetic future installed major.

This tests current source, not the withdrawn immutable 2.0.0 distribution.
The historical records are fixture inputs; migration itself uses public effects.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest
from tests.test_coordinated_release import _load_module
from tests.test_native_public_cli import ROOT, consume


@pytest.fixture(scope="module")
def installed_major_pair(tmp_path_factory):
    coordinated_release = _load_module()
    fixture = tmp_path_factory.mktemp("installed-major")
    source = fixture / "source"
    # Copy tracked working bytes so the candidate includes uncommitted repairs,
    # while excluding local owner state, build products and credentials.
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, tracked):
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    for name, content in coordinated_release.staging_files(coordinated_release.load_ownership(), head, "9.0.0").items():
        (source / name).write_text(content, encoding="utf-8", newline="\n")
    # One isolated compilation, with a reusable cache outside the copied source.
    target = ROOT / "target/installed-major-fixture"
    subprocess.run(["cargo", "build", "--locked", "--workspace", "--bins", "--target-dir", str(target)], cwd=source, check=True)
    binaries = fixture / "installed"
    binaries.mkdir()
    suffix = ".exe" if os.name == "nt" else ""
    for name in ("agentic-workspace", "agentic-workspace-core"):
        shutil.copy2(target / "debug" / (name + suffix), binaries / (name + suffix))
    return binaries / ("agentic-workspace-core" + suffix), binaries / ("agentic-workspace" + suffix)


def test_installed_major_setup_answer_commits_both_scopes_then_refreshes(tmp_path, installed_major_pair):
    core, cli = installed_major_pair
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    config = workspace / "config.toml"
    local_config = workspace / "config.local.toml"
    config.write_text('[workspace]\nenabled=true\n[payload]\npolicy="required-before-work"\n', encoding="utf-8")
    local_config.write_text('[session_logging]\nenabled=false\n[clarification]\nmode="ask-first"\n', encoding="utf-8")
    context = {"target": str(tmp_path), "task": "Migrate this installed consumer while preserving repository intent", "changed": []}

    def call(data=None):
        return consume("json", core, cli, context | (data or {}), custom_core=True, host_path=os.environ["PATH"])

    def commit(proposed, operation="configuration.write"):
        action = proposed["decision_packet"]["primary_action"]
        if not action:
            answer = next(
                row["response_request"]
                for row in proposed["decision_packet"]["pending_consequences"]["decisions"]
                if row["owner"] == "configuration"
            )
            answer["arguments"]["answer"] = "authorize-write"
            action = call({"request": answer})["decision_packet"]["primary_action"]
        assert action and action["operation_id"] == operation
        result = call({"invocation": action})
        assert result["effect_outcome"]["status"] == "committed", result
        return result

    def adoption(mode):
        read = call()["configuration_write"]["repository_adoption_request"]
        choices = call({"request": read})["configuration_write"]["adoption_requests"]
        return next(row for row in choices if row["arguments"]["mode"] == mode)

    commit(call({"request": adoption("adopt")}), "configuration.repository-adoption")
    records = [workspace / "configuration-assessment.json", workspace / "local/configuration-assessment.json"]
    # Seed known prior-major assessments using the public record grammar and
    # current dependency observations. No source trust or development reassessment.
    for path, scope in zip(records, ("repository", "machine-local"), strict=True):
        read = call()["configuration_write"]["setup_assessment"]["request"]
        read["arguments"]["scope"] = scope
        value = call({"request": read})["configuration_write"]["setup_assessment"]["record_request"]["arguments"]["value"]
        value.update(
            runtime_version="8.11.0",
            coverage="Accepted prior installed setup",
            dispositions=[{"subject": "Optional setup", "status": "excluded", "reason": "No optional capabilities requested"}],
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    provenance_path = workspace / "payload-provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["release_identity"]["version"] = "8.11.0"
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    startup = workspace / "skills/workspace-startup/SKILL.md"
    startup.write_bytes(startup.read_bytes() + b"\n<!-- Prior installed package seed -->\n")
    sentinel = workspace / "memory/repo/notes/retained.md"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("Preserve repository intent through upgrade.\n", encoding="utf-8")
    preserved = {path: path.read_bytes() for path in (config, local_config, sentinel)}

    def selected(scope, projection="full"):
        job = call()["configuration_write"]["setup_job_request"]
        job["arguments"] = {"job": "assess-setup", "concern": "preferences", "scope": scope}
        return call({"request": job, "projection": projection})

    assert call()["configuration_write"]["setup_assessment"]["status"] == "major-transition"
    # Missing provenance must expose a gap, never an answerable migration that
    # could publish a current record and thereby bypass maintenance admission.
    prior_provenance = provenance_path.read_bytes()
    prior_record = records[0].read_bytes()
    provenance_path.unlink()
    blocked = selected("repository")
    assert blocked["setup_context"]["status"] == "preserved-blocked"
    assert not blocked["setup_context"]["choices"]
    assert "record_request" not in blocked["configuration_write"]["setup_assessment"]
    unsupported = blocked["configuration_write"]["concern_assessment_request"]
    unsupported["arguments"].update(judgment="working", reason="Missing package identity cannot support migration")
    with pytest.raises(AssertionError, match="no supported migration"):
        call({"request": unsupported})
    assert records[0].read_bytes() == prior_record
    assert not provenance_path.exists()
    provenance_path.write_bytes(prior_provenance)

    for index, scope in enumerate(("repository", "machine-local")):
        current = selected(scope)
        assert current["configuration_write"]["setup_assessment"]["status"] == "migration-assessment-required"
        step = selected(scope, "compact")["setup_context"]["next_step"]
        proposed = call(
            step["input"]
            | {
                "answer": {
                    "judgment": "working",
                    "reason": "Observed standing preferences retain their meaning in the supported major transition",
                }
            }
        )
        assert proposed["decision_packet"]["primary_action"]
        committed = commit(proposed)
        assert committed["setup_result"]["effect"] == "committed"
        saved = json.loads(records[index].read_text(encoding="utf-8"))
        assert saved["runtime_version"] == "9.0.0"
        assert saved["package_migration"]["reason"]
        if index == 0:
            # Existing local judgment remains independently required.
            assert call({"request": adoption("reconcile-payload")})["configuration_write"]["status"] == "preserved-blocked"

    refresh = call()["configuration_write"]["setup_job_request"]
    refresh["arguments"] = {"job": "refresh-payload"}
    choices = call({"request": refresh})["configuration_write"]["payload_choices"]
    assert next(row for row in choices if row["source"] == ".agentic-workspace/skills/workspace-startup/SKILL.md")["status"] != "current"
    for choice in choices:
        if choice["status"] != "current":
            commit(call({"request": choice["request"]}))
    fresh = call()
    assert fresh["configuration_write"]["setup_assessment"]["status"] == "settled"
    assert fresh["configuration_write"]["local_setup_assessment"]["status"] == "settled"
    assert fresh["configuration_write"]["managed_refresh"]["required"] is False
    assert json.loads(provenance_path.read_text(encoding="utf-8"))["release_identity"]["version"] == "9.0.0"
    assert all(path.read_bytes() == content for path, content in preserved.items())
