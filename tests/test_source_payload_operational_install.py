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
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md", "# Memory index\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "WORKFLOW.md", "# Workflow\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "SKILLS.md", "# Skills\n")
    _write(tmp_path / ".agentic-workspace/planning/state.toml", "# TODO\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "execplans" / "README.md", "# Execplans\n")
    _write(tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}\n")


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


def test_planning_readme_payload_claim_parser_reads_exact_payload_block(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_readme_parser")
    readme = tmp_path / "README.md"
    _write(
        readme,
        """
        # Package

        The package ships these payload files:

        - `AGENTS.template.md`
        - `.agentic-workspace/planning/agent-manifest.json`

        It packages:

        - prose outside the checked payload block
        """,
    )

    assert mod._markdown_payload_claims(readme) == [
        "AGENTS.template.md",
        ".agentic-workspace/planning/agent-manifest.json",
    ]


def test_planning_readme_payload_claim_warning_reports_stale_claims(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_readme_drift")
    readme = tmp_path / "packages" / "planning" / "README.md"
    _write(
        readme,
        """
        # Planning

        The package ships these payload files:

        - `AGENTS.template.md`
        - `tools/AGENT_QUICKSTART.md`
        """,
    )
    monkeypatch.setattr(
        mod,
        "_planning_required_payload_claims",
        lambda _repo_root: ["AGENTS.template.md", ".agentic-workspace/planning/agent-manifest.json"],
    )

    warnings = mod._readme_payload_claim_warnings(repo_root=tmp_path)

    assert len(warnings) == 1
    assert warnings[0].warning_class == "doc_installed_surface_drift"
    assert "missing payload claim(s): .agentic-workspace/planning/agent-manifest.json" in warnings[0].message
    assert "stale payload claim(s): tools/AGENT_QUICKSTART.md" in warnings[0].message
