"""Workspace opt-out ends AW participation without repository task authority."""

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
