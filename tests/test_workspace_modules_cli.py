from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    repo_root = Path("./repo")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(repo_root, []))

    assert cli.main(["modules", "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload["module_profiles"]] == [
        "routing-only",
        "planning",
        "memory",
        "full",
    ]
    full_profile = next(entry for entry in payload["module_profiles"] if entry["id"] == "full")
    assert full_profile["profile_kind"] == "installer-preset"
    assert full_profile["selected_modules"] == ["planning", "memory"]
    assert full_profile["selection_rule"] == "expands to every bundled module marked include_in_full_preset"
    assert payload["feature_tiers_compatibility"]["canonical_field"] == "module_profiles"
    assert [entry["id"] for entry in payload["feature_tiers"]] == [
        "routing-only",
        "planning",
        "memory",
        "full",
    ]
    footprint = payload["package_footprint"]
    assert footprint["decision"] == "bundle-first-party-modules-for-now"
    assert "unconditionally" in footprint["python_package_dependency_model"]
    assert "not Python package dependencies" in footprint["repo_footprint_rule"]
    assert footprint["bounded_by"] == ["#490", "#510"]
    component_model = payload["component_model"]
    assert component_model["schema_version"] == "agentic-workspace/module-components/v1"
    assert component_model["runtime_dependency"] == "none"
    assert {entry["id"] for entry in component_model["component_classes"]} == {
        "resource",
        "tool",
        "prompt",
        "schema",
        "root",
    }
    assert "FastMCP or MCP runtime dependencies" in " ".join(component_model["adapter_boundary"]["adapter_must_not"])
    workspace_components = payload["workspace_components"]
    assert workspace_components["scope"]["audience"] == "shipped-host-repo"
    assert "source-checkout maintainer tooling" in workspace_components["scope"]["excludes"]
    root_components = workspace_components["components"]
    assert {resource["uri"] for resource in root_components["resources"]} >= {
        "workspace://config",
        "workspace://summary",
        "workspace://report",
        "workspace://proof",
    }
    workspace_install = next(tool for tool in root_components["tools"] if tool["name"] == "workspace.install")
    assert workspace_install["read_only"] is False
    assert workspace_install["requires_dry_run"] is True
    assert workspace_install["result_schema"] == "workspace-lifecycle-plan/v1"
    workspace_uninstall = next(tool for tool in root_components["tools"] if tool["name"] == "workspace.uninstall")
    assert workspace_uninstall["destructive"] is True
    assert "destructive" in workspace_uninstall["safety"]["requires_approval_when"]
    assert {prompt["name"] for prompt in root_components["prompts"]} == {"workspace.startup"}
    assert {root["id"] for root in root_components["roots"]} >= {
        "workspace-root",
        "workspace-local-root",
    }
    full_tier = next(entry for entry in payload["feature_tiers"] if entry["id"] == "full")
    assert full_tier["modules"] == ["planning", "memory"]
    assert "does not imply source-checkout maintainer tooling" in full_tier["cost_model"]
    assert "maintainer-dogfooding" not in {entry["id"] for entry in payload["feature_tiers"]}
    assert {entry["id"] for entry in payload["advanced_features"]} == {
        "review_artifacts",
        "external_adapters",
    }
    assert {entry["tier"] for entry in payload["advanced_features"]} == {"reusable-diagnostics"}
    assert all(entry["default_enabled"] is False for entry in payload["advanced_features"])
    shipped_catalog = json.dumps(
        {
            "feature_tiers": payload["feature_tiers"],
            "advanced_features": payload["advanced_features"],
        },
        sort_keys=True,
    )
    for source_checkout_only in (
        "maintainer-dogfooding",
        "command_generation",
        "autopilot_loops",
        "self-improvement",
        "codegen",
    ):
        assert source_checkout_only not in shipped_catalog
    assert [entry["name"] for entry in payload["modules"]] == ["planning", "memory"]
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    assert planning_module["install_signals"] == ["TODO.md", ".agentic-workspace/planning/execplans", ".agentic-workspace/planning"]
    assert planning_module["workflow_surfaces"] == [
        "AGENTS.md",
        "TODO.md",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/execplans",
        "docs/maintainer/contributor-playbook.md",
        ".agentic-workspace/planning",
    ]
    assert planning_module["generated_artifacts"] == [".agentic-workspace/planning/agent-manifest.json"]
    assert planning_module["autodetects_installation"] is True
    assert planning_module["installed"] is None
    assert planning_module["dry_run_commands"] == ["adopt", "install", "uninstall", "upgrade"]
    assert planning_module["force_commands"] == ["install"]
    assert planning_module["capabilities"] == [
        "active-execution-state",
        "execplan-routing",
    ]
    assert planning_module["dependencies"] == []
    assert planning_module["conflicts"] == []
    planning_components = planning_module["components"]
    assert {resource["uri"] for resource in planning_components["resources"]} >= {
        "planning://state",
        "planning://summary",
    }
    planning_install = next(tool for tool in planning_components["tools"] if tool["name"] == "planning.install")
    assert planning_install["read_only"] is False
    assert planning_install["requires_dry_run"] is True
    assert planning_install["result_schema"] == "workspace-module-report/v1"
    assert "ambiguous_ownership" in planning_install["safety"]["requires_approval_when"]
    assert {prompt["name"] for prompt in planning_components["prompts"]} >= {
        "planning.autopilot",
        "planning.reporting",
    }
    assert {root["id"] for root in planning_components["roots"]} >= {"planning-root"}
    assert planning_module["result_contract"]["schema_version"] == "workspace-module-report/v1"
    assert planning_module["lifecycle_hook_expectations"] == [
        "adopt",
        "doctor",
        "install",
        "status",
        "uninstall",
        "upgrade",
    ]
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    memory_components = memory_module["components"]
    assert {resource["uri"] for resource in memory_components["resources"]} >= {
        "memory://index",
        "memory://manifest",
    }
    memory_upgrade = next(tool for tool in memory_components["tools"] if tool["name"] == "memory.upgrade")
    assert memory_upgrade["read_only"] is False
    assert memory_upgrade["requires_dry_run"] is True
    assert memory_upgrade["safety"]["dry_run_command"].startswith("agentic-workspace upgrade --modules memory")
    assert {prompt["name"] for prompt in memory_components["prompts"]} >= {
        "memory.router",
        "memory.capture",
    }
    assert planning_module["command_args"]["install"] == ["target", "dry_run", "force"]
    assert planning_module["command_args"]["doctor"] == ["target"]


def test_root_command_manifest_classifies_host_repo_command_surface() -> None:
    manifest = cli_commands_manifest()
    commands = manifest["commands"]
    command_roles = {command["name"]: command["role"] for command in commands}
    command_audiences = {command["name"]: command["audience"] for command in commands}

    assert set(command_roles) == {
        "modules",
        "planning",
        "memory",
        "summary",
        "start",
        "implement",
        "defaults",
        "proof",
        "setup",
        "ownership",
        "config",
        "system-intent",
        "note-delegation-outcome",
        "skills",
        "report",
        "reconcile",
        "external-intent",
        "preflight",
        "install",
        "init",
        "prompt",
        "status",
        "doctor",
        "upgrade",
        "uninstall",
    }
    assert command_roles["install"] == "core_lifecycle"
    assert command_roles["upgrade"] == "core_lifecycle"
    assert command_roles["start"] == "core_context_router"
    assert command_roles["planning"] == "core_context_router"
    assert command_roles["report"] == "core_context_router"
    assert command_roles["modules"] == "module_delegation_front_door"
    assert command_roles["setup"] == "reusable_host_repo_diagnostics"
    assert command_roles["external-intent"] == "reusable_host_repo_diagnostics"
    assert command_audiences["note-delegation-outcome"] == "local_only"
    assert command_audiences["setup"] == "advanced_host_repo"
    assert all(command["classification_note"] for command in commands)
    assert "source_checkout_only_maintainer_development" not in set(command_roles.values())
    assert "remove_or_hide" not in set(command_roles.values())

    prompt = next(command for command in commands if command["name"] == "prompt")
    assert {subcommand["name"] for subcommand in prompt["subcommands"]} == {"init", "upgrade", "uninstall"}
    assert {subcommand["role"] for subcommand in prompt["subcommands"]} == {"core_lifecycle"}

    external_intent = next(command for command in commands if command["name"] == "external-intent")
    assert external_intent["subcommands"][0]["audience"] == "advanced_host_repo"


def test_modules_command_does_not_advertise_current_memory_as_ordinary_surface(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["modules", "--verbose", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    ordinary_surfaces = memory_module["install_signals"] + memory_module["workflow_surfaces"]
    assert ".agentic-workspace/memory/repo/current" not in ordinary_surfaces
    assert ".agentic-workspace/memory/repo/current/" not in ordinary_surfaces


def test_modules_command_reports_installation_state_for_target(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# TODO\n")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    _write((tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json"), "{}\n")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["modules", "--verbose", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    assert planning_module["installed"] is True
    assert memory_module["installed"] is False


def test_adapt_action_supports_slotted_dataclass(tmp_path: Path) -> None:
    action = SlottedAction(kind="copied", path=tmp_path / "demo.txt", detail="ok")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "copied", "path": "demo.txt", "detail": "ok"}


def test_adapt_action_prefers_to_dict_protocol(tmp_path: Path) -> None:
    action = DictAction(tmp_path / "nested" / "demo.txt")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "converted", "path": "nested/demo.txt", "detail": "used to_dict"}


def test_adapt_module_result_handles_optional_warnings(tmp_path: Path) -> None:
    result = FakeResult(
        target_root=tmp_path,
        message="status memory",
        dry_run=False,
        actions=[FakeAction(kind="recorded", path=tmp_path / "memory", detail="ran status")],
    )
    delattr(result, "warnings")

    report = adapt_module_result(module="memory", result=result)

    assert report.to_dict()["warnings"] == []


def test_invoke_module_command_uses_descriptor_command_args(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _doctor_handler(**kwargs):
        captured.update(kwargs)
        return FakeResult(
            target_root=tmp_path,
            message="doctor planning",
            dry_run=False,
            actions=[],
            warnings=[],
        )

    descriptor = cli.ModuleDescriptor(
        name="planning",
        description="planning module",
        commands={"doctor": _doctor_handler},
        detector=lambda detected_root: True,
        selection_rank=10,
        include_in_full_preset=True,
        install_signals=(Path("TODO.md"),),
        workflow_surfaces=(Path("TODO.md"),),
        generated_artifacts=(),
        command_args={"doctor": ("target",)},
        startup_steps=(),
        sources_of_truth=(),
        root_agents_cleanup_blocks=(),
        capabilities=(),
        dependencies=(),
        conflicts=(),
        result_contract=cli.ModuleResultContract(
            schema_version="workspace-module-report/v1",
            guaranteed_fields=("module",),
            action_fields=("kind",),
            warning_fields=("message",),
        ),
    )

    report = cli._invoke_module_command(
        command_name="doctor",
        module_name="planning",
        descriptor=descriptor,
        target_root=tmp_path,
        dry_run=True,
        force=True,
    )

    assert captured == {"target": str(tmp_path)}
    assert report["module"] == "planning"


def test_selected_modules_uses_descriptor_owned_presets(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    config = cli._load_workspace_config(target_root=tmp_path, descriptors=descriptors)

    selected_modules, preset_name = cli._selected_modules(
        command_name="init",
        preset_name="full",
        module_arg=None,
        target_root=tmp_path,
        descriptors=descriptors,
        config=config,
    )

    assert preset_name == "full"
    assert selected_modules == ["planning", "memory"]


def test_selected_modules_rejects_declared_missing_dependency(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    memory_descriptor = descriptors["memory"]
    descriptors["memory"] = cli.ModuleDescriptor(
        name=memory_descriptor.name,
        description=memory_descriptor.description,
        commands=memory_descriptor.commands,
        detector=memory_descriptor.detector,
        selection_rank=memory_descriptor.selection_rank,
        include_in_full_preset=memory_descriptor.include_in_full_preset,
        install_signals=memory_descriptor.install_signals,
        workflow_surfaces=memory_descriptor.workflow_surfaces,
        generated_artifacts=memory_descriptor.generated_artifacts,
        command_args=memory_descriptor.command_args,
        startup_steps=memory_descriptor.startup_steps,
        sources_of_truth=memory_descriptor.sources_of_truth,
        root_agents_cleanup_blocks=memory_descriptor.root_agents_cleanup_blocks,
        capabilities=memory_descriptor.capabilities,
        dependencies=("planning",),
        conflicts=(),
        result_contract=memory_descriptor.result_contract,
    )

    with pytest.raises(cli.ModuleSelectionError, match="requires: planning"):
        cli._validate_selected_module_contract(selected_modules=["memory"], descriptors=descriptors)


def test_selected_modules_rejects_declared_conflict(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, [])
    planning_descriptor = descriptors["planning"]
    descriptors["planning"] = cli.ModuleDescriptor(
        name=planning_descriptor.name,
        description=planning_descriptor.description,
        commands=planning_descriptor.commands,
        detector=planning_descriptor.detector,
        selection_rank=planning_descriptor.selection_rank,
        include_in_full_preset=planning_descriptor.include_in_full_preset,
        install_signals=planning_descriptor.install_signals,
        workflow_surfaces=planning_descriptor.workflow_surfaces,
        generated_artifacts=planning_descriptor.generated_artifacts,
        command_args=planning_descriptor.command_args,
        startup_steps=planning_descriptor.startup_steps,
        sources_of_truth=planning_descriptor.sources_of_truth,
        root_agents_cleanup_blocks=planning_descriptor.root_agents_cleanup_blocks,
        capabilities=planning_descriptor.capabilities,
        dependencies=(),
        conflicts=("memory",),
        result_contract=planning_descriptor.result_contract,
    )

    with pytest.raises(cli.ModuleSelectionError, match="conflicts with: memory"):
        cli._validate_selected_module_contract(selected_modules=["planning", "memory"], descriptors=descriptors)


def test_workspace_agents_template_keeps_descriptor_guidance_out_of_root_entrypoint(tmp_path: Path) -> None:
    descriptor = cli.ModuleDescriptor(
        name="signals",
        description="signals module",
        commands={},
        detector=lambda detected_root: False,
        selection_rank=30,
        include_in_full_preset=True,
        install_signals=(Path("signals.md"),),
        workflow_surfaces=(Path("signals.md"),),
        generated_artifacts=(),
        command_args={},
        startup_steps=("Read `signals.md` when the signals module is installed.",),
        sources_of_truth=("Signal routing: `signals.md`",),
        root_agents_cleanup_blocks=(),
        capabilities=("signal-routing",),
        dependencies=(),
        conflicts=(),
        result_contract=cli.ModuleResultContract(
            schema_version="workspace-module-report/v1",
            guaranteed_fields=("module",),
            action_fields=("kind",),
            warning_fields=("message",),
        ),
    )

    rendered = cli._workspace_agents_template(selected_modules=["signals"], descriptors={"signals": descriptor})

    assert "Read `signals.md` when the signals module is installed." not in rendered
    assert "Signal routing: `signals.md`" not in rendered
    assert "Open module, planning, memory, or deeper routing files only when the compact answers point there." not in rendered
    assert 'start --task "<task>"' in rendered
    assert "## Module Notes" not in rendered


def test_workspace_agents_template_renders_resolved_cli_invocation() -> None:
    rendered = cli._workspace_agents_template(selected_modules=[], descriptors={}, cli_invoke="uv run agentic-workspace")

    assert "- canonical_source: `.agentic-workspace/config.toml` and `uv run agentic-workspace start --target . --format json`" in rendered
    assert "use `uv run agentic-workspace` as the effective Agentic Workspace CLI invocation" in rendered
    assert 'run `uv run agentic-workspace start --task "<task>" --format json`' in rendered
    assert "use the effective CLI invocation from `agentic-workspace start" not in rendered
