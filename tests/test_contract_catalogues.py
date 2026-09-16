from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/generate/generate_contract_catalogues.py"


def _module():
    spec = importlib.util.spec_from_file_location("generate_contract_catalogues", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_catalogue_renders_current_values_and_local_effect_boundary() -> None:
    text = _module().render_cli_catalogue()
    assert "# Current CLI Catalogue" in text
    for command in ["start", "invoke", "resources", "worker"]:
        assert f"`agentic-workspace {command}`" in text
    assert "`agentic-workspace planning new-plan`" not in text
    assert "not native public commands" in text
    assert "same `native_cli` declaration" in text
    assert "Contract digest: `sha256:" in text


def test_surface_catalogue_separates_public_footprint_from_maintenance_profiles() -> None:
    text = _module().render_surface_catalogue()
    assert "# Current Installed-Surface Catalogue" in text
    assert "configuration.repository-adoption" in text
    assert "Optional domain state is never established" in text
    assert "### `necessary-surfaces`" not in text
    maintenance = _module().render_maintenance_catalogue()
    assert "### `necessary-surfaces` + `planning,memory,verification`" in maintenance
    assert "selected-but-unconfigured" in maintenance


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"], ids=["lf-checkout", "crlf-checkout"])
def test_checked_in_catalogues_are_fresh(tmp_path: Path, line_ending: bytes) -> None:
    module = _module()
    for path in [module.CLI_PATH, module.SURFACES_PATH, module.MODULES_PATH, module.SUPPORT_INSTALL_PATH]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", line_ending))
    module.REPO_ROOT = tmp_path
    assert (REPO_ROOT / module.CLI_OUTPUT).read_text(encoding="utf-8") == module.render_cli_catalogue()
    assert (REPO_ROOT / module.SURFACES_OUTPUT).read_text(encoding="utf-8") == module.render_surface_catalogue()
    assert (REPO_ROOT / module.SUPPORT_INSTALL_OUTPUT).read_text(encoding="utf-8") == module.render_support_install()
    content = module.render_surface_catalogue()
    module._write_or_check(module.SURFACES_OUTPUT, content, check=False)
    assert (tmp_path / module.SURFACES_OUTPUT).read_bytes() == content.encode("utf-8")
    source = tmp_path / module.SURFACES_PATH
    source.write_bytes(source.read_bytes().replace(b"adopted-host", b"changed-lifetime"))
    assert module.render_surface_catalogue() != content


def test_support_install_projection_is_immutable_and_hash_bound() -> None:
    text = _module().render_support_install()
    assert "# Current Support-Bearing Install" in text
    assert "uv tool install" in text
    # Renderer parity is distinct from the maintainer's live release-currentness check.
    projection = json.loads((REPO_ROOT / _module().SUPPORT_INSTALL_PATH).read_text(encoding="utf-8"))
    artifact = projection["artifact"]
    assert projection["install_command"] in text
    assert f"{artifact['url']}#sha256={artifact['sha256']}" in text
    assert f"Receipt digest: `sha256:{projection['receipt']['sha256']}`" in text
    assert f"/releases/tag/v{projection['version']}" in text
    assert f"/releases/download/v{projection['version']}/{artifact['name']}" in artifact["url"]
