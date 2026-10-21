"""Workspace opt-out ends AW participation without repository task authority."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("projection", ["full", "compact", "carried"])
def test_disabled_start_does_not_compose_ordinary_owners(tmp_path: Path, shared_core_binary, native_cli, projection):
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text('[workspace]\nenabled=false\nagent_instructions_file="AGENTS.md"\n')
    # These unrelated sources must not be interpreted during opt-out.
    (workspace / "planning").mkdir()
    (workspace / "planning/manifest.toml").write_text("not valid TOML [")
    (workspace / "verification").mkdir()
    (workspace / "verification/manifest.toml").write_text("not valid TOML [")
    (workspace / "skills/REGISTRY.json").parent.mkdir()
    (workspace / "skills/REGISTRY.json").write_text("not valid JSON")
    (tmp_path / "AGENTS.md").write_text("Keep the repository review requirements.\n")
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Fix a parser", "projection": projection})
    view = result.get("view", result)
    assert view["status"] == "inactive"
    assert view["configuration"] == {"enabled": False}
    assert not ({"planning", "memory", "verification", "decision_packet", "task_requirements"} & view.keys())
    assert "non_aw_continuation" not in view  # Opt-out stays quiet.
    assert "continue repository work" in view["message"]
    assert before == {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_enablement_override_and_configuration_maintenance(tmp_path: Path, shared_core_binary, native_cli):
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    shared = workspace / "config.toml"
    shared.write_text("[workspace]\nenabled=true\n")
    context = {"target": str(tmp_path), "task": "Maintain repository configuration"}
    enabled = consume("native", shared_core_binary, native_cli, context)
    assert enabled["configuration"]["enabled"] is True
    ordinary_request = enabled["resources"]["requests"][0]
    shared.write_text("[workspace]\nenabled=false\n")
    with pytest.raises(AssertionError, match="ordinary operations are unavailable"):
        consume("native", shared_core_binary, native_cli, {**context, "request": ordinary_request})
    maintenance = consume("native", shared_core_binary, native_cli, {**context, "maintenance": "configuration"})
    assert maintenance["configuration"]["enabled"] is False
    assert not any(b["code"] == "workspace-disabled" for b in maintenance["decision_packet"]["blockers"])
    assert maintenance["configuration_write"]["requests"]
    (workspace / "config.local.toml").write_text("[workspace]\nenabled=true\n")
    overridden = consume("native", shared_core_binary, native_cli, context)
    assert overridden["configuration"]["enabled"] is True
    assert "decision_packet" in overridden
    (workspace / "config.local.toml").write_text("not valid TOML [")
    invalid = consume("native", shared_core_binary, native_cli, context)
    assert invalid["status"] == "blocked"
    assert invalid["failure_class"] == "runtime-repository-contract-incompatible"
    assert invalid["non_aw_continuation"]["restriction_source"] == "/"
    assert invalid["non_aw_continuation"]["aw_admitted"] is False


def test_non_aw_work_preserves_blocked_proof_and_unrelated_facilities(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_proof_producer import fixture
    from tests.test_native_public_cli import pin_instructions

    context = fixture(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/preserve.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\nprotect: [protected.txt]\n---\nPreserve this source.\n")
    protected = tmp_path / "protected.txt"
    protected.write_text("separately protected")
    task_record = tmp_path / "task.md"
    task_record.write_text("User authorizes updating a.txt and checking it with ordinary host tools. Preserve protected.txt.\n")
    pin_instructions(tmp_path)

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    execute = call()["verification"]["execution_requests"][0]
    blocked = call(request=execute)
    outside = blocked["non_aw_continuation"]
    assert outside["restriction_source"] == "/decision_packet/blockers"
    assert outside["authority"] == "independent-user-repository-host-only"
    assert outside["aw_admitted"] is False
    assert outside["record_requires_aw"] is False
    assert "exception_note" not in outside
    assert outside["disclosure"]
    assert blocked["verification"]["execution"]["status"] == "blocked"
    assert blocked["decision_packet"]["primary_action"] is None
    compact = call(request=execute, projection="compact")
    assert compact["non_aw_continuation"] == outside
    assert compact["decision_packet"]["blockers"] == blocked["decision_packet"]["blockers"]
    # Public detail is an exact owner reference, not a second start option.
    # It remains a read of that owner, with the same proof restrictions.
    detail = call(request=execute, projection="full", reference=compact["detail_refs"]["/verification"])
    assert detail["authority"] == "detail-only"
    assert detail["currentness"] == "reobserved"
    assert detail["value"] == blocked["verification"]

    # The permitted alternative uses ordinary tools, not proof.report. Its
    # record lives with this task and acquires no native receipt or custody.
    (tmp_path / "a.txt").write_text("updated source")
    subprocess.run(
        [sys.executable, "-c", "from pathlib import Path; assert Path('a.txt').read_text() == 'updated source'"],
        cwd=tmp_path,
        check=True,
    )
    with task_record.open("a") as record:
        record.write(
            "Acting test agent: AW proof.report lacks an executor declaration for a.txt. "
            "Used the user's authorized direct edit and host check for a.txt; it passed. "
            "No AW proof, ownership admission or independent review was produced.\n"
        )
    fresh = call(request=execute)
    assert fresh["configuration"]["enabled"] is True
    assert fresh["planning"]  # Unrelated AW facilities remain available.
    assert fresh["verification"]["execution"]["status"] == "blocked"
    assert fresh["verification"]["evidence"] == []
    assert fresh["decision_packet"]["primary_action"] is None
    assert protected.read_text() == "separately protected"
    assert not (tmp_path / "count.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()
