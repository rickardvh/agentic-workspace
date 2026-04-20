from __future__ import annotations

import importlib.util
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _checker_script_path() -> Path:
    return WORKSPACE_ROOT / "scripts" / "check" / "check_source_payload_operational_install.py"


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_root_surfaces(tmp_path: Path) -> None:
    _write(tmp_path / "memory" / "index.md", "# Memory index\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "WORKFLOW.md", "# Workflow\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "SKILLS.md", "# Skills\n")
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / "ROADMAP.md", "# Roadmap\n")
    _write(tmp_path / "docs" / "execplans" / "README.md", "# Execplans\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")
    _write(tmp_path / "tools" / "agent-manifest.json", "{}\n")
    _write(tmp_path / "tools" / "AGENT_QUICKSTART.md", "# Quickstart\n")
    _write(tmp_path / "tools" / "AGENT_ROUTING.md", "# Routing\n")


def test_boundary_checker_passes_for_clean_root_install(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_valid")
    _write_root_surfaces(tmp_path)

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)

    assert warnings == []


def test_boundary_checker_warns_on_package_local_install_clones(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_drift")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "memory" / ".agentic-workspace" / "memory" / "WORKFLOW.md", "# cloned workflow\n")
    _write(tmp_path / "packages" / "planning" / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")
    _write(tmp_path / "packages" / "planning" / "tools" / "AGENT_QUICKSTART.md", "# cloned quickstart\n")

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)

    assert {warning.warning_class for warning in warnings} == {
        "package_local_install_drift",
    }
    assert any(str(warning.path).endswith("packages/memory/.agentic-workspace") for warning in warnings)
    assert any(str(warning.path).endswith("packages/planning/.agentic-workspace") for warning in warnings)
