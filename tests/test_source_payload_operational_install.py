from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

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


def _write_workspace_surface_manifest(root: Path, *, include_target: bool = True, include_undeclared_toml_reference: bool = False) -> None:
    payload_files = [
        ".agentic-workspace/skills/workspace-startup/SKILL.md",
        ".agentic-workspace/fallback/no-cli-policy.json",
        ".agentic-workspace/fallback/no_cli_startup.py",
        *([".agentic-workspace/runtime.toml"] if include_undeclared_toml_reference else []),
        *([".agentic-workspace/docs/module-map.md"] if include_target else []),
    ]
    manifest = {
        "payload_files": payload_files,
        "necessary_surface_files": payload_files,
        "module_surface_files": {
            "memory": [".agentic-workspace/memory/repo/index.md"],
            "planning": [".agentic-workspace/planning/state.toml"],
            "verification": [".agentic-workspace/verification/manifest.toml"],
        },
        "required_references": [
            {
                "source": ".agentic-workspace/skills/workspace-startup/SKILL.md",
                "target": ".agentic-workspace/docs/module-map.md",
                "kind": "installed-local",
                "profiles": ["necessary-surfaces", "full-mirror"],
                "modules": [],
            },
            {
                "source": ".agentic-workspace/skills/workspace-startup/SKILL.md",
                "target": ".agentic-workspace/fallback/no_cli_startup.py",
                "kind": "installed-local",
                "profiles": ["necessary-surfaces", "full-mirror"],
                "modules": [],
            },
            *[
                {
                    "source": ".agentic-workspace/fallback/no-cli-policy.json",
                    "target": target,
                    "kind": "installed-local",
                    "profiles": ["necessary-surfaces", "full-mirror"],
                    "modules": required_modules,
                }
                for target, required_modules in (
                    (".agentic-workspace/config.toml", []),
                    (".agentic-workspace/skills/workspace-startup/SKILL.md", []),
                    (".agentic-workspace/docs/module-map.md", []),
                    (".agentic-workspace/memory/repo/index.md", ["memory"]),
                    (".agentic-workspace/planning/state.toml", ["planning"]),
                    (".agentic-workspace/verification/manifest.toml", ["verification"]),
                )
            ],
        ],
        "reference_discovery": {
            "source_globs": [
                ".agentic-workspace/**/*.json",
                ".agentic-workspace/**/*.md",
                ".agentic-workspace/**/*.py",
                ".agentic-workspace/**/*.toml",
            ],
            "installed_source_roots": [{"repo_path": "src/agentic_workspace/_payload", "installed_prefix": ""}],
            "generated_source_authorities": [],
        },
        "no_cli_fallback": {
            "entrypoint": ".agentic-workspace/fallback/no_cli_startup.py",
            "policy": ".agentic-workspace/fallback/no-cli-policy.json",
            "forbidden_actions": [
                "mutate-managed-state-by-hand",
                "bypass-planning-safety-gate",
                "claim-completion-without-proof",
            ],
            "next_safe_action": "continue-from-installed-startup-without-managed-state-mutation",
        },
    }
    _write(root / "src" / "agentic_workspace" / "contracts" / "workspace_surfaces.json", json.dumps(manifest))
    _write(
        root / "src" / "agentic_workspace" / "_payload" / ".agentic-workspace/skills/workspace-startup/SKILL.md",
        "Use `.agentic-workspace/docs/module-map.md`; if the CLI is absent run `.agentic-workspace/fallback/no_cli_startup.py`.",
    )
    fallback_source = (WORKSPACE_ROOT / "src/agentic_workspace/_payload/.agentic-workspace/fallback/no_cli_startup.py").read_text(
        encoding="utf-8"
    )
    _write(root / "src/agentic_workspace/_payload/.agentic-workspace/fallback/no_cli_startup.py", fallback_source)
    policy = {
        "kind": "agentic-workspace/no-cli-policy/v1",
        "required_surfaces": [
            ".agentic-workspace/config.toml",
            ".agentic-workspace/skills/workspace-startup/SKILL.md",
            ".agentic-workspace/docs/module-map.md",
        ],
        "forbidden_actions": manifest["no_cli_fallback"]["forbidden_actions"],
        "next_safe_action": manifest["no_cli_fallback"]["next_safe_action"],
        "module_boundaries": {
            "memory": {"surface": ".agentic-workspace/memory/repo/index.md", "boundary": "memory"},
            "planning": {"surface": ".agentic-workspace/planning/state.toml", "boundary": "planning"},
            "verification": {"surface": ".agentic-workspace/verification/manifest.toml", "boundary": "verification"},
        },
    }
    _write(
        root / "src/agentic_workspace/_payload/.agentic-workspace/fallback/no-cli-policy.json",
        json.dumps(policy),
    )
    if include_undeclared_toml_reference:
        _write(
            root / "src/agentic_workspace/_payload/.agentic-workspace/runtime.toml",
            'reference = ".agentic-workspace/docs/undeclared-runtime.md"',
        )
    if include_target:
        _write(
            root / "src" / "agentic_workspace" / "_payload" / ".agentic-workspace/docs/module-map.md",
            "## Memory\n## Planning\n## Verification",
        )


def test_installed_reference_closure_covers_every_footprint_module_cell(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_reference_closure")
    _write_workspace_surface_manifest(tmp_path)

    closure = mod.gather_installed_reference_closure(repo_root=tmp_path)

    assert closure["status"] == "passed"
    assert len(closure["matrix"]) == 16
    assert {cell["no_cli_fallback"] for cell in closure["matrix"]} == {"preserved"}
    empty_cell = next(cell for cell in closure["matrix"] if cell["profile"] == "necessary-surfaces" and not cell["modules"])
    all_cell = next(
        cell
        for cell in closure["matrix"]
        if cell["profile"] == "necessary-surfaces" and cell["modules"] == ["memory", "planning", "verification"]
    )
    assert set(all_cell["installed_sources"]) - set(empty_cell["installed_sources"]) == {
        ".agentic-workspace/memory/repo/index.md",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/verification/manifest.toml",
    }


def test_installed_reference_closure_fails_when_required_target_is_missing(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_reference_closure_missing")
    _write_workspace_surface_manifest(tmp_path, include_target=False)

    closure = mod.gather_installed_reference_closure(repo_root=tmp_path)

    assert closure["status"] == "failed"
    assert {gap["reason"] for cell in closure["matrix"] for gap in cell["gaps"]} == {"target-absent"}


def test_installed_reference_discovery_rejects_undeclared_toml_reference(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_reference_closure_toml")
    _write_workspace_surface_manifest(tmp_path, include_undeclared_toml_reference=True)

    closure = mod.gather_installed_reference_closure(repo_root=tmp_path)

    assert closure["status"] == "failed"
    assert closure["errors"] == [
        "discovered installed reference is missing from required_references: "
        ".agentic-workspace/runtime.toml -> .agentic-workspace/docs/undeclared-runtime.md"
    ]


@pytest.mark.parametrize(
    "modules",
    list(
        (
            (),
            ("memory",),
            ("planning",),
            ("verification",),
            ("memory", "planning"),
            ("memory", "verification"),
            ("planning", "verification"),
            ("memory", "planning", "verification"),
        )
    ),
)
def test_no_cli_black_box_preserves_boundaries_for_each_module_combination(tmp_path: Path, modules: tuple[str, ...]) -> None:
    mod = _load_module(_checker_script_path(), f"source_payload_no_cli_{'_'.join(modules) or 'none'}")
    host_root = tmp_path / "clean-host"
    host_root.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=host_root, check=True)
    command = [
        sys.executable,
        str(WORKSPACE_ROOT / "scripts/run_agentic_workspace.py"),
        "install",
        "--target",
        str(host_root),
        "--non-interactive",
        "--format",
        "json",
    ]
    command.extend(["--modules", ",".join(modules) if modules else "none"])
    completed = subprocess.run(command, cwd=WORKSPACE_ROOT, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    manifest = json.loads((WORKSPACE_ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text(encoding="utf-8"))

    cli_available = (host_root / "bin" / "agentic-workspace").exists()
    result = mod.evaluate_no_cli_fallback(
        host_root=host_root,
        modules=modules,
        manifest=manifest,
        cli_available=cli_available,
    )

    assert result["status"] == "passed", result
    assert result["network_access"] == "not-required"
    assert result["implementation_allowed"] is False
    assert result["completion_claim_allowed"] is False
    assert set(result["selected_modules"]) == set(modules)
    assert result["forbidden_actions"] == [
        "mutate-managed-state-by-hand",
        "bypass-planning-safety-gate",
        "claim-completion-without-proof",
    ]
    assert result["next_safe_action"] == "continue-from-installed-startup-without-managed-state-mutation"


def test_no_cli_black_box_fails_when_required_fallback_target_is_removed(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_no_cli_missing_target")
    host_root = tmp_path / "clean-host"
    host_root.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=host_root, check=True)
    completed = subprocess.run(
        [
            sys.executable,
            str(WORKSPACE_ROOT / "scripts/run_agentic_workspace.py"),
            "install",
            "--target",
            str(host_root),
            "--non-interactive",
            "--modules",
            "memory",
            "--format",
            "json",
        ],
        cwd=WORKSPACE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    manifest = json.loads((WORKSPACE_ROOT / "src/agentic_workspace/contracts/workspace_surfaces.json").read_text(encoding="utf-8"))
    (host_root / ".agentic-workspace/memory/repo/index.md").unlink()

    result = mod.evaluate_no_cli_fallback(
        host_root=host_root,
        modules=("memory",),
        manifest=manifest,
        cli_available=False,
    )

    assert result["status"] == "failed"
    assert any("memory/repo/index.md" in error for error in result["errors"])


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
    assert planning["source_to_payload_inventory"]["classified_source_only_or_generated"] == []
    assert planning["source_to_payload_inventory"]["classification_counts"] == {}
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


def test_boundary_checker_warns_on_bootstrap_helper_directories(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_helper_dirs")
    _write_root_surfaces(tmp_path)
    _write(tmp_path / "packages" / "memory" / "bootstrap" / "scripts" / "check" / "helper.py", "print('bad')")
    _write(tmp_path / "packages" / "memory" / "bootstrap" / "optional" / "Makefile.fragment.mk", "bad")
    _write(tmp_path / "packages" / "planning" / "bootstrap" / "scripts" / "render_agent_docs.py", "print('bad')")
    _write(tmp_path / "packages" / "planning" / "bootstrap" / "tools" / "AGENT_QUICKSTART.md", "# bad")
    _write(
        tmp_path / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "scripts" / "render_agent_docs.py",
        "print('bad')",
    )

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)
    warning_paths = {warning.path.replace("\\", "/") for warning in warnings if warning.warning_class == "package_local_install_drift"}

    assert any(path.endswith("packages/memory/bootstrap/scripts") for path in warning_paths)
    assert any(path.endswith("packages/memory/bootstrap/optional") for path in warning_paths)
    assert any(path.endswith("packages/planning/bootstrap/scripts") for path in warning_paths)
    assert any(path.endswith("packages/planning/bootstrap/tools") for path in warning_paths)
    assert any(path.endswith("packages/planning/bootstrap/.agentic-workspace/planning/scripts") for path in warning_paths)


def test_boundary_checker_warns_on_executable_bootstrap_payload(tmp_path: Path) -> None:
    mod = _load_module(_checker_script_path(), "source_payload_boundary_executable_payload")
    _write_root_surfaces(tmp_path)
    _write(
        tmp_path / "packages" / "memory" / "bootstrap" / ".agentic-workspace" / "memory" / "repo" / "templates" / "helper.py",
        "print('bad')",
    )
    _write(
        tmp_path / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "execplans" / "apply",
        "#!/usr/bin/env bash\nexit 0\n",
    )

    warnings = mod.gather_boundary_warnings(repo_root=tmp_path)
    executable_warnings = [warning for warning in warnings if warning.warning_class == "executable_payload_drift"]
    proof = mod.gather_sync_proof(repo_root=tmp_path)

    assert {warning.path for warning in executable_warnings} == {"packages/memory/bootstrap", "packages/planning/bootstrap"}
    assert "helper.py" in executable_warnings[0].message or "helper.py" in executable_warnings[1].message
    assert "execplans/apply" in executable_warnings[0].message or "execplans/apply" in executable_warnings[1].message
    assert proof["packages"][0]["executable_payload_guard"]["executable_files"] == [".agentic-workspace/planning/execplans/apply"]
    assert proof["packages"][1]["executable_payload_guard"]["executable_files"] == [".agentic-workspace/memory/repo/templates/helper.py"]


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
