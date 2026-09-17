"""Configuration's public foothold lifecycle preserves repository ownership."""

import copy
import json
import os
import subprocess

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def test_repository_foothold_currentness_removal_and_reentry(tmp_path, shared_core_binary, native_cli):
    initial = consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Configure repository integration"})
    assert "repository_adoption_request" not in initial["configuration_write"]
    assert not (tmp_path / ".agentic-workspace").exists()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    instructions = tmp_path / "AGENTS.md"
    instructions.write_text("# Repository policy\nPreserve this text.\n", encoding="utf-8")
    # A former mirror converges only exact known package bytes.
    contract = json.loads((ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text())
    retired = contract["retired_package_surfaces"][0]["path"]
    old = tmp_path / retired
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes((ROOT / "src/agentic_workspace/_payload" / retired).read_bytes())
    unknown = tmp_path / ".agentic-workspace/unknown.txt"
    unknown.write_text("Preserve unknown material")
    context = {"target": str(tmp_path), "task": "Configure repository integration"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def read():
        request = call()["configuration_write"]["repository_adoption_request"]
        return call(request=request)["configuration_write"]

    def action(mode):
        discovery = read()
        request = next(r for r in discovery["adoption_requests"] if r["arguments"]["mode"] == mode)
        proposed = call(request=request)
        decisions = proposed["decision_packet"]["pending_consequences"]["decisions"]
        answer = next(d for d in decisions if d["id"] == "repository-adoption-authorization")["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(request=answer)["decision_packet"]["primary_action"]

    assert read()["status"] == "unadopted"
    prepared = action("adopt")
    forged = copy.deepcopy(prepared)
    forged["arguments"]["binding"]["state"]["updates"]["AGENTS.md"]["after"] = "Forged"
    with pytest.raises(AssertionError):
        call(invocation=forged)
    result = call(invocation=prepared)
    assert result["effect_outcome"]["status"] == "committed"
    assert instructions.read_text().startswith("# Repository policy\nPreserve this text.\n")
    identity = tmp_path / ".agentic-workspace/adoption.json"
    assert identity.is_file()
    ignored = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", ".agentic-workspace/local/effects/adoption.prepared.json"],
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    assert not old.exists()
    assert unknown.read_text() == "Preserve unknown material"
    assert not (tmp_path / ".agentic-workspace/config.toml").exists()
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    request = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "adopt")
    assert call(request=request)["configuration_write"]["status"] == "already-current"
    # Lost outcome evidence recovers without replaying published files.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    partial = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    expected = partial.read_bytes()
    partial.unlink()
    recovery = read()["recovery_requests"][0]
    proposed = call(request=recovery)
    answer = next(
        d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "repository-adoption-authorization"
    )["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    recovered = call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    assert recovered["effect_outcome"]["status"] == "committed"
    assert partial.read_bytes() == expected

    def exposure(mode):
        request = call()["configuration_write"]["skill_exposure_request"]
        row = next(
            row for row in call(request=request)["configuration_write"]["skill_exposure"] if row["state"]["name"] == "workspace-startup"
        )
        proposed = call(request=row[mode + "_request"])
        answer = proposed["configuration_write"]["authorization_request"]
        answer["arguments"]["answer"] = "authorize-write"
        return call(invocation=call(request=answer)["decision_packet"]["primary_action"])

    assert exposure("expose")["effect_outcome"]["status"] == "committed"
    request = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "remove")
    assert call(request=request)["configuration_write"]["status"] == "remove-owned-skill-exposures-first"
    assert exposure("remove")["effect_outcome"]["status"] == "committed"
    preserved = tmp_path / ".agentic-workspace/planning/retained.md"
    preserved.parent.mkdir()
    preserved.write_text("Independent durable work")
    removed = call(invocation=action("remove"))
    assert removed["effect_outcome"]["status"] == "committed"
    assert not identity.exists()
    assert preserved.read_text() == "Independent durable work"
    assert "Preserve this text." in instructions.read_text()
    assert "agentic-workspace:workflow" not in instructions.read_text()
    # Deliberate re-adoption needs no removal tombstone or registry reset.
    assert call(invocation=action("adopt"))["effect_outcome"]["status"] == "committed"
    skill = tmp_path / ".agentic-workspace/skills/workspace-startup/SKILL.md"
    skill.write_text(skill.read_text() + "\nUser edits\n")
    removal = next(r for r in read()["adoption_requests"] if r["arguments"]["mode"] == "remove")
    blocked = call(request=removal)["configuration_write"]
    assert blocked["status"] == "preserved-blocked"
    assert any("edited or unowned" in b for b in blocked["repository_adoption"]["blockers"])
    assert skill.read_text().endswith("User edits\n")
