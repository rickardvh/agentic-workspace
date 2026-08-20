from __future__ import annotations

import importlib.util
from pathlib import Path

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
    assert "`agentic-workspace planning new-plan`" in text
    assert "`--switch-active`" in text
    assert "Shared-state mutability and ignored local diagnostics are separate" in text
    assert "Contract digest: `sha256:" in text


def test_surface_catalogue_renders_profile_cells_and_selected_unconfigured_state() -> None:
    text = _module().render_surface_catalogue()
    assert "# Current Installed-Surface Catalogue" in text
    assert "### `necessary-surfaces` + `planning,memory,verification`" in text
    assert "`.agentic-workspace/verification/manifest.toml`" in text
    assert "selected-but-unconfigured" in text
    assert "| Module-owned |" in text


def test_checked_in_catalogues_are_fresh() -> None:
    module = _module()
    assert (REPO_ROOT / module.CLI_OUTPUT).read_text(encoding="utf-8") == module.render_cli_catalogue()
    assert (REPO_ROOT / module.SURFACES_OUTPUT).read_text(encoding="utf-8") == module.render_surface_catalogue()
    assert (REPO_ROOT / module.SUPPORT_INSTALL_OUTPUT).read_text(encoding="utf-8") == module.render_support_install()


def test_support_install_projection_is_immutable_and_hash_bound() -> None:
    text = _module().render_support_install()
    assert "# Current Support-Bearing Install" in text
    assert "uv tool install" in text
    assert "#sha256=91293e2b" in text
    assert "Receipt digest: `sha256:38e53f2d" in text
