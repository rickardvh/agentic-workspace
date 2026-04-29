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


def test_sync_proof_classifies_layers_and_intentional_differences(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_sync_proof")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}")
    _write(tmp_path / "packages" / "planning" / "bootstrap" / "tools" / "AGENT_QUICKSTART.md", "# source helper")
    _write(tmp_path / "packages" / "planning" / "bootstrap" / "tools" / "__pycache__" / "helper.pyc", "ignored")
    _write(tmp_path / "packages" / "memory" / "bootstrap" / "AGENTS.template.md", "# adapter")
    _write(tmp_path / "packages" / "memory" / "bootstrap" / ".agentic-workspace" / "memory" / "repo" / "index.md", "# index")
    _write(
        tmp_path / "packages" / "planning" / "pyproject.toml",
        """
        [tool.hatch.build.targets.wheel.force-include]
        "bootstrap/.agentic-workspace/planning/agent-manifest.json" = "src/repo_planning_bootstrap/_payload/.agentic-workspace/planning/agent-manifest.json"
        """,
    )
    _write(
        tmp_path / "packages" / "memory" / "pyproject.toml",
        """
        [tool.hatch.build.targets.wheel.force-include]
        "bootstrap" = "src/repo_memory_bootstrap/_payload"
        """,
    )
    monkeypatch.setattr(mod, "_planning_expected_payload_files", lambda _repo_root: [".agentic-workspace/planning/agent-manifest.json"])
    monkeypatch.setattr(mod, "_memory_expected_payload_files", lambda _repo_root: ["AGENTS.md", ".agentic-workspace/memory/repo/index.md"])

    proof = mod.gather_sync_proof(repo_root=tmp_path)

    assert proof["status"] == "current"
    planning = proof["packages"][0]
    memory = proof["packages"][1]
    assert planning["source_to_payload_inventory"]["status"] == "current"
    assert planning["source_to_payload_inventory"]["classified_source_only_or_generated"][0]["classification"] == "intentional-source-extra"
    assert planning["source_to_payload_inventory"]["classification_counts"] == {"intentional-source-extra": 1}
    assert planning["source_to_payload_inventory"]["unexpected"] == []
    assert "Bytecode and cache files" in planning["source_to_payload_inventory"]["ignored_transient_rule"]
    assert all("__pycache__" not in item["path"] for item in planning["source_to_payload_inventory"]["classified_source_only_or_generated"])
    assert memory["source_to_payload_inventory"]["status"] == "current"
    assert memory["source_to_payload_inventory"]["missing"] == []
    assert memory["intentional_differences"][0]["classification"] == "root-operational-memory"


def test_sync_proof_warns_on_missing_payload_source(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_sync_missing")
    _write_root_surfaces(tmp_path)
    _write(
        tmp_path / "packages" / "planning" / "pyproject.toml",
        """
        [tool.hatch.build.targets.wheel.force-include]
        "bootstrap/.agentic-workspace/planning/agent-manifest.json" = "src/repo_planning_bootstrap/_payload/.agentic-workspace/planning/agent-manifest.json"
        """,
    )
    monkeypatch.setattr(mod, "_planning_expected_payload_files", lambda _repo_root: [".agentic-workspace/planning/agent-manifest.json"])
    monkeypatch.setattr(mod, "_memory_expected_payload_files", lambda _repo_root: [])

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)
    proof = mod.gather_sync_proof(repo_root=tmp_path)

    assert any(warning.warning_class == "payload_inventory_drift" for warning in warnings)
    assert proof["packages"][0]["source_to_payload_inventory"]["status"] == "drift"


def test_sync_proof_warns_on_unclassified_source_extra(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_sync_unexpected_extra")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "agent-manifest.json", "{}")
    _write(tmp_path / "packages" / "planning" / "bootstrap" / "unexpected.md", "# unexpected")
    _write(
        tmp_path / "packages" / "planning" / "pyproject.toml",
        """
        [tool.hatch.build.targets.wheel.force-include]
        "bootstrap/.agentic-workspace/planning/agent-manifest.json" = "src/repo_planning_bootstrap/_payload/.agentic-workspace/planning/agent-manifest.json"
        """,
    )
    monkeypatch.setattr(mod, "_planning_expected_payload_files", lambda _repo_root: [".agentic-workspace/planning/agent-manifest.json"])
    monkeypatch.setattr(mod, "_memory_expected_payload_files", lambda _repo_root: [])

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)
    proof = mod.gather_sync_proof(repo_root=tmp_path)

    drift_warnings = [warning for warning in warnings if warning.warning_class == "payload_inventory_drift"]
    assert len(drift_warnings) == 1
    assert "unexpected source extra(s): unexpected.md" in drift_warnings[0].message
    inventory = proof["packages"][0]["source_to_payload_inventory"]
    assert inventory["status"] == "drift"
    assert inventory["missing"] == []
    assert inventory["unexpected"] == ["unexpected.md"]
    assert inventory["classification_counts"] == {"unexpected-source-extra": 1}
    assert inventory["classified_source_only_or_generated"] == [
        {
            "path": "unexpected.md",
            "classification": "unexpected-source-extra",
            "rule": "Unexpected bootstrap source extras require classification before they can be treated as intentional.",
        }
    ]


def test_memory_bootstrap_boundary_flags_repo_specific_payload(monkeypatch, tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_memory_repo_payload")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "memory" / "bootstrap" / ".agentic-workspace" / "memory" / "repo" / "index.md", "# index")
    _write(
        tmp_path / "packages" / "memory" / "bootstrap" / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "README.md",
        "# Runbooks",
    )
    _write(
        tmp_path / "packages" / "memory" / "bootstrap" / ".agentic-workspace" / "memory" / "repo" / "templates" / "runbook.template.md",
        "# Template",
    )
    _write(
        tmp_path
        / "packages"
        / "memory"
        / "bootstrap"
        / ".agentic-workspace"
        / "memory"
        / "repo"
        / "runbooks"
        / "dogfooding-usage-ledger.md",
        "# Repo-specific runbook",
    )
    _write(
        tmp_path / "packages" / "memory" / "pyproject.toml",
        """
        [tool.hatch.build.targets.wheel.force-include]
        "bootstrap" = "src/repo_memory_bootstrap/_payload"
        """,
    )
    monkeypatch.setattr(mod, "_planning_expected_payload_files", lambda _repo_root: [])
    monkeypatch.setattr(mod, "_memory_expected_payload_files", lambda _repo_root: [".agentic-workspace/memory/repo/index.md"])

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)
    proof = mod.gather_sync_proof(repo_root=tmp_path)

    assert any(warning.warning_class == "payload_inventory_drift" for warning in warnings)
    inventory = proof["packages"][1]["source_to_payload_inventory"]
    assert inventory["unexpected"] == [".agentic-workspace/memory/repo/runbooks/dogfooding-usage-ledger.md"]
    assert inventory["classification_counts"] == {"intentional-source-extra": 2, "unexpected-source-extra": 1}


def test_boundary_checker_warns_on_legacy_memory_tree(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_legacy_memory")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "memory" / "memory" / "runbooks" / "dogfooding-usage-ledger.md", "# Legacy")

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)

    assert any(
        warning.warning_class == "package_local_install_drift" and str(warning.path).endswith("packages/memory/memory")
        for warning in warnings
    )


def test_planning_checker_has_single_full_source() -> None:
    canonical = WORKSPACE_ROOT / "packages" / "planning" / "scripts" / "check" / "check_planning_surfaces.py"
    root_wrapper = WORKSPACE_ROOT / "scripts" / "check" / "check_planning_surfaces.py"
    removed_duplicate_paths = [
        WORKSPACE_ROOT / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py",
        WORKSPACE_ROOT / "packages" / "planning" / "bootstrap" / "scripts" / "check" / "check_planning_surfaces.py",
        WORKSPACE_ROOT
        / "packages"
        / "planning"
        / "bootstrap"
        / ".agentic-workspace"
        / "planning"
        / "scripts"
        / "check"
        / "check_planning_surfaces.py",
    ]

    assert canonical.exists()
    assert "def gather_planning_warnings" in canonical.read_text(encoding="utf-8")
    assert root_wrapper.exists()
    wrapper_text = root_wrapper.read_text(encoding="utf-8")
    assert "runpy.run_path" in wrapper_text
    assert "def gather_planning_warnings" not in wrapper_text
    assert not [path for path in removed_duplicate_paths if path.exists()]
