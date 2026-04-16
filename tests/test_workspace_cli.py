from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agentic_workspace import cli
from agentic_workspace.result_adapter import adapt_action, adapt_module_result


@dataclass
class FakeAction:
    kind: str
    path: Path
    detail: str


@dataclass
class FakeResult:
    target_root: Path
    message: str
    dry_run: bool
    actions: list[FakeAction] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class SlottedAction:
    kind: str
    path: Path
    detail: str


class DictAction:
    def __init__(self, path: Path) -> None:
        self.path = path

    def to_dict(self, target_root: Path) -> dict[str, object]:
        return {
            "kind": "converted",
            "path": self.path.relative_to(target_root),
            "detail": "used to_dict",
        }


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    repo_root = Path("./repo")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(repo_root, []))

    assert cli.main(["modules", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in payload["modules"]] == ["planning", "memory"]
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    assert planning_module["install_signals"] == ["TODO.md", "docs/execplans", ".agentic-workspace/planning"]
    assert planning_module["workflow_surfaces"] == [
        "AGENTS.md",
        "TODO.md",
        "ROADMAP.md",
        "docs/execplans",
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
        ".agentic-workspace/planning",
        "tools/AGENT_QUICKSTART.md",
        "tools/AGENT_ROUTING.md",
    ]
    assert planning_module["generated_artifacts"] == [
        "tools/agent-manifest.json",
        "tools/AGENT_QUICKSTART.md",
        "tools/AGENT_ROUTING.md",
    ]
    assert planning_module["autodetects_installation"] is True
    assert planning_module["installed"] is None
    assert planning_module["dry_run_commands"] == ["adopt", "install", "uninstall", "upgrade"]
    assert planning_module["force_commands"] == ["install"]
    assert planning_module["capabilities"] == [
        "active-execution-state",
        "execplan-routing",
        "generated-maintainer-guidance",
    ]
    assert planning_module["dependencies"] == []
    assert planning_module["conflicts"] == []
    assert planning_module["result_contract"]["schema_version"] == "workspace-module-report/v1"
    assert planning_module["lifecycle_hook_expectations"] == [
        "adopt",
        "doctor",
        "install",
        "status",
        "uninstall",
        "upgrade",
    ]
    assert planning_module["command_args"]["install"] == ["target", "dry_run", "force"]
    assert planning_module["command_args"]["doctor"] == ["target"]


def test_defaults_command_reports_machine_readable_default_routes_as_json(capsys) -> None:
    assert cli.main(["defaults", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["startup"]["default_canonical_agent_instructions_file"] == "AGENTS.md"
    assert payload["startup"]["supported_agent_instructions_files"] == ["AGENTS.md", "GEMINI.md"]
    assert payload["compact_contract_profile"]["canonical_doc"] == "docs/compact-contract-profile.md"
    assert payload["compact_contract_profile"]["rule"] == (
        "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump."
    )
    assert payload["compact_contract_profile"]["selectors"]["defaults"] == ("agentic-workspace defaults --section <section> --format json")
    assert payload["lifecycle"]["primary_entrypoint"] == "agentic-workspace"
    assert "agentic-workspace init --target ./repo --preset <memory|planning|full>" == payload["lifecycle"]["default_install_command"]
    assert payload["lifecycle"]["canonical_external_agent_handoff"] == "llms.txt"
    assert payload["lifecycle"]["canonical_bootstrap_next_action"] == ".agentic-workspace/bootstrap-handoff.md"
    assert payload["lifecycle"]["canonical_bootstrap_handoff_record"] == ".agentic-workspace/bootstrap-handoff.json"
    assert payload["setup"]["canonical_doc"] == "docs/jumpstart-contract.md"
    assert payload["setup"]["command"] == "agentic-workspace setup --target ./repo --format json"
    assert payload["setup"]["rule"] == "Setup is a bounded post-bootstrap phase that stays separate from init."
    assert payload["setup"]["phase"] == "post-bootstrap"
    assert payload["setup"]["scope"] == [
        "orient from a compact report first",
        "keep follow-through bounded and reviewable",
    ]
    assert payload["intent"]["canonical_doc"] == "docs/intent-contract.md"
    assert payload["intent"]["command"] == "agentic-workspace defaults --section intent --format json"
    assert payload["intent"]["rule"] == "Confirmed intent stays human-owned; interpreted intent must remain visibly inferred."
    assert payload["intent"]["confirmed_intent"]["summary"] == "the human-owned request before workspace normalization"
    assert payload["intent"]["interpreted_intent"]["summary"] == "the workspace-normalized request carried forward by lifecycle commands"
    assert payload["setup"]["secondary"] == [
        "Do not widen init.",
        "Do not collapse setup into the proof backlog.",
        "Do not turn setup into generic analysis.",
    ]
    assert payload["validation"]["default_routes"]["planning_package"] == "cd packages/planning && uv run pytest tests/test_installer.py"
    workspace_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "workspace_cli")
    assert "root workspace CLI changes" in workspace_lane["when"]
    assert workspace_lane["enough_proof"] == [
        "uv run pytest tests/test_workspace_cli.py -q",
        "uv run ruff check src tests",
    ]
    assert "the change also touches generated maintainer docs" in workspace_lane["broaden_when"]
    assert "the narrow lane cannot prove the change on its own" in workspace_lane["escalate_when"]
    planning_surface_lane = next(lane for lane in payload["validation"]["lanes"] if lane["id"] == "planning_surfaces")
    assert planning_surface_lane["enough_proof"] == ["uv run python scripts/check/check_planning_surfaces.py"]
    assert payload["validation"]["escalation_rule"] == (
        "Broaden validation only when the narrower lane stops proving the touched contract or the change crosses boundaries."
    )
    assert payload["proof_surfaces"]["canonical_doc"] == "docs/proof-surfaces-contract.md"
    assert payload["proof_surfaces"]["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_surfaces"]["default_routes"]["workspace_proof"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_selection"]["canonical_doc"] == "docs/proof-surfaces-contract.md"
    assert payload["proof_selection"]["command"] == "agentic-workspace defaults --section proof_selection --format json"
    assert payload["proof_selection"]["rule"] == (
        "Make proof choice cheap by naming the narrowest lane that still answers the trust question."
    )
    assert payload["proof_selection"]["recommended_lanes"][0]["id"] == "workspace_proof"
    assert payload["proof_selection"]["recommended_lanes"][0]["enough_proof"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["proof_selection"]["recommended_lanes"][2]["id"] == "validation_lane"
    assert "Prefer the smallest queryable proof answer first." in payload["proof_selection"]["rule_of_thumb"]
    assert payload["ownership_mapping"]["canonical_doc"] == "docs/ownership-authority-contract.md"
    assert payload["ownership_mapping"]["command"] == "agentic-workspace ownership --target ./repo --format json"
    assert payload["ownership_mapping"]["ledger"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["combined_install"]["primary"] == "agentic-workspace init --target ./repo --preset full"
    assert payload["recovery"]["canonical_doc"] == "docs/environment-recovery-contract.md"
    assert payload["recovery"]["rule"] == "Inspect state first, refresh contract second, re-run the narrowest proving lane third."
    assert payload["recovery"]["ordered_path"][:2] == [
        "agentic-workspace status --target ./repo",
        "agentic-workspace doctor --target ./repo",
    ]
    assert ".agentic-workspace/bootstrap-handoff.md" in payload["recovery"]["handoff_surfaces"]
    assert ".agentic-workspace/bootstrap-handoff.json" in payload["recovery"]["handoff_surfaces"]
    assert payload["completion"]["rule"] == (
        "When a completed slice came from TODO.md or ROADMAP.md, clear the matched queue residue in the same pass."
    )
    assert payload["completion"]["prefer_surfaces"] == [
        "TODO.md",
        "ROADMAP.md",
        "docs/execplans/README.md",
    ]
    assert payload["delegated_judgment"]["canonical_doc"] == "docs/delegated-judgment-contract.md"
    assert payload["delegated_judgment"]["rule"] == "Improve means locally; do not silently rewrite ends locally."
    assert "requested outcome" in payload["delegated_judgment"]["human_sets"]
    assert "bounded decomposition" in payload["delegated_judgment"]["agent_may_decide"]
    assert "the better-looking solution changes the requested outcome" in payload["delegated_judgment"]["escalate_when"]
    assert payload["delegated_judgment"]["operational_follow_through"] == [
        "use a checked-in execplan when the requested outcome must survive across sessions",
        "preserve escalation boundaries in the machine-readable defaults when the task is broad enough to need them",
        "route durable residue into the correct checked-in surface instead of leaving it in chat",
    ]
    assert payload["mixed_agent"]["rule"] == "Prefer runtime/task inference first, then stable policy, then explicit prompting."
    assert payload["mixed_agent"]["decision_order"] == [
        "runtime/task inference",
        "repo-owned policy",
        "optional local capability/cost override",
        "explicit prompting when still unsafe",
    ]
    assert payload["mixed_agent"]["local_override"]["path"] == "agentic-workspace.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["supported_fields"] == [
        "runtime.supports_internal_delegation",
        "runtime.strong_planner_available",
        "runtime.cheap_bounded_executor_available",
        "handoff.prefer_internal_delegation_when_available",
        "safety.safe_to_auto_run_commands",
        "safety.requires_human_verification_on_pr",
    ]
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["handoff_quality"]["must_recover"] == [
        "current intent",
        "hard constraints",
        "relevant durable context",
        "proof expectations",
        "immediate next action",
    ]
    assert payload["delegation_posture"]["canonical_doc"] == "docs/delegation-posture-contract.md"
    assert payload["delegation_posture"]["command"] == "agentic-workspace defaults --section delegation_posture --format json"
    assert payload["delegation_posture"]["rule"] == (
        "Use the effective mixed-agent posture to decide whether to keep work direct, "
        "split it into planner/implementer/validator subtasks, or escalate to a stronger planner."
    )
    assert payload["delegation_posture"]["preferred_split"] == ["planner", "implementer", "validator"]
    assert payload["delegation_posture"]["config_controls"] == [
        "agentic-workspace.local.toml runtime.supports_internal_delegation",
        "agentic-workspace.local.toml runtime.strong_planner_available",
        "agentic-workspace.local.toml runtime.cheap_bounded_executor_available",
        "agentic-workspace.local.toml handoff.prefer_internal_delegation_when_available",
    ]
    assert payload["delegation_posture"]["secondary"] == [
        "Do not treat config as a scheduler.",
        "Do not delegate when the task stays cheap and direct.",
        "Do not silently rewrite ends.",
    ]
    assert payload["config"]["path"] == "agentic-workspace.toml"
    assert payload["config"]["command"] == "agentic-workspace config --target ./repo --format json"
    assert "workspace.default_preset" in payload["config"]["supported_fields"]
    assert "workspace.workflow_artifact_profile" in payload["config"]["supported_fields"]
    assert payload["workflow_artifact_adapters"]["canonical_doc"] == "docs/workspace-config-contract.md"
    assert (
        payload["workflow_artifact_adapters"]["command"] == "agentic-workspace defaults --section workflow_artifact_adapters --format json"
    )
    assert payload["workflow_artifact_adapters"]["default_profile"] == "repo-owned"
    gemini_profile = next(
        profile for profile in payload["workflow_artifact_adapters"]["supported_profiles"] if profile["profile"] == "gemini"
    )
    assert gemini_profile["native_artifacts"] == ["implementation_plan.md", "task.md", "walkthrough.md"]
    assert gemini_profile["canonical_surfaces"] == ["TODO.md", "docs/execplans/"]
    assert any("ROADMAP.md" in step for step in payload["startup"]["secondary"])
    assert payload["startup"]["workflow_recovery"] == [
        (
            "When startup or workflow routing is unclear, prefer "
            "`agentic-workspace defaults --format json`, then use `llms.txt` "
            "or `AGENTS.md` when those surfaces are present, before "
            "repo-local workaround guidance."
        ),
    ]
    assert any("skills --target ./repo --task" in step for step in payload["skill_discovery"]["primary"])


def test_defaults_command_text_emphasises_primary_and_secondary_routes(capsys) -> None:
    assert cli.main(["defaults"]) == 0

    text = capsys.readouterr().out
    assert "Startup:" in text
    assert "agentic-workspace defaults --format json" in text
    assert "Lifecycle:" in text
    assert "primary entrypoint: agentic-workspace" in text
    assert "bootstrap handoff record: .agentic-workspace/bootstrap-handoff.json" in text
    assert "Setup:" in text
    assert "docs/jumpstart-contract.md" in text
    assert "Intent:" in text
    assert "Confirmed intent stays human-owned" in text
    assert "confirmed:" in text
    assert "interpreted:" in text
    assert "Delegation posture:" in text
    assert "docs/delegation-posture-contract.md" in text
    assert "Compact contract profile:" in text
    assert "docs/compact-contract-profile.md" in text
    assert "Proof surfaces:" in text
    assert "docs/proof-surfaces-contract.md" in text
    assert "Proof selection:" in text
    assert "defaults --section proof_selection" in text
    assert "Ownership mapping:" in text
    assert "docs/ownership-authority-contract.md" in text
    assert "Combined install:" in text
    assert "Recovery:" in text
    assert "docs/environment-recovery-contract.md" in text
    assert "Completion:" in text
    assert "Config:" in text
    assert "Workflow artifact adapters:" in text
    assert "docs/workspace-config-contract.md" in text
    assert "Delegated judgment:" in text
    assert "Delegated judgment follow-through:" in text
    assert "Mixed-agent:" in text
    assert "docs/delegated-judgment-contract.md" in text
    assert "make maintainer-surfaces" in text


def test_external_agent_handoff_text_names_target_repository_and_no_install_assumption() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    assert "repository that contains this file" in text
    assert "Target repository:" in text
    assert "Do not assume agentic-workspace is already installed" in text
    assert "agentic-workspace config --target ./repo --format json" in text
    assert "agentic-planning-bootstrap summary --format json" in text
    assert "agentic-workspace.local.toml is present" in text
    assert "tools/AGENT_QUICKSTART.md" in text
    assert "tools/AGENT_ROUTING.md" in text


def test_external_agent_handoff_text_uses_configured_agent_instructions_filename() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"], agent_instructions_file="GEMINI.md")

    assert "Read GEMINI.md first." in text
    assert "GEMINI.md remains the repo startup entrypoint" in text


def test_external_agent_handoff_text_reports_workflow_artifact_profile() -> None:
    text = cli._external_agent_handoff_text(
        selected_modules=["planning"],
        agent_instructions_file="GEMINI.md",
        workflow_artifact_profile="gemini",
    )

    assert "Workflow artifact profile: gemini." in text
    assert "mirror the durable execution state into TODO.md and the active execplan" in text


def test_config_command_reports_effective_defaults_without_repo_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is False
    assert payload["workspace"]["default_preset"] == "full"
    assert payload["workspace"]["agent_instructions_file"] == "AGENTS.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_profile"] == "repo-owned"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "product-default"
    assert payload["workspace"]["workflow_artifact_adapter"]["canonical_surfaces"] == ["TODO.md", "docs/execplans/"]
    assert payload["update"]["wrapper_rule"] == "normal update execution stays behind agentic-workspace"
    assert {item["module"] for item in payload["update"]["modules"]} == {"planning", "memory"}
    assert payload["mixed_agent"]["status"] == "reporting-only"
    assert payload["mixed_agent"]["repo_policy"]["source"] == "product-defaults"
    assert payload["mixed_agent"]["repo_policy"]["path"] == "agentic-workspace.toml"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is False
    assert payload["mixed_agent"]["local_override"]["path"] == "agentic-workspace.local.toml"
    assert payload["mixed_agent"]["local_override"]["supported"] is True
    assert payload["mixed_agent"]["local_override"]["exists"] is False
    assert payload["mixed_agent"]["local_override"]["applied"] is False
    assert payload["mixed_agent"]["runtime_inference"]["tool_owned"] is True
    assert payload["mixed_agent"]["runtime_inference"]["reported_here"] is False
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {"value": None, "source": "unset"}
    assert payload["mixed_agent"]["success_measures"] == [
        "lower long-run token cost",
        "lower restart and handoff cost",
        "cheap switching across agents and subscriptions",
        "persisted shared knowledge beats rediscovery",
    ]


def test_config_command_autodetects_existing_supported_agent_instructions_file(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Gemini\n", encoding="utf-8")

    assert cli.main(["config", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "autodetected-existing"
    assert payload["workspace"]["detected_agent_instructions_files"] == ["GEMINI.md"]


def test_defaults_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "validation", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "validation"}
    assert payload["matched"] is True
    assert payload["answer"]["rule"] == "Run the narrowest proving lane that matches the touched surface."
    assert "docs/compact-contract-profile.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_section_selector_returns_intent_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "intent", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "intent"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/intent-contract.md"
    assert payload["answer"]["command"] == "agentic-workspace defaults --section intent --format json"
    assert payload["answer"]["rule"] == "Confirmed intent stays human-owned; interpreted intent must remain visibly inferred."
    assert payload["answer"]["confirmed_intent"]["summary"] == "the human-owned request before workspace normalization"
    assert payload["answer"]["interpreted_intent"]["summary"] == "the workspace-normalized request carried forward by lifecycle commands"
    assert "docs/intent-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_defaults_setup_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "setup", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "setup"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/jumpstart-contract.md"
    assert payload["answer"]["phase"] == "post-bootstrap"
    assert "docs/jumpstart-contract.md" in payload["refs"]
    assert "agentic-workspace setup --target ./repo --format json" in payload["refs"]


def test_setup_command_reports_no_new_seed_surfaces_for_mature_repo(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    (target / "memory").mkdir(exist_ok=True)
    (target / "memory" / "index.md").write_text("# Memory index\n", encoding="utf-8")

    assert cli.main(["setup", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-setup/v1"
    assert payload["command"] == "setup"
    assert payload["orientation"]["mode"] == "no-new-seed-surfaces-needed"
    assert "no new seed surfaces are needed" in payload["orientation"]["summary"].lower()
    assert payload["next_action"]["summary"] == "No new seed surfaces needed"
    assert payload["next_action"]["commands"] == ["agentic-workspace report --target ./repo --format json"]


def test_defaults_delegation_posture_section_selector_returns_compact_contract_answer(capsys) -> None:
    assert cli.main(["defaults", "--section", "delegation_posture", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "defaults"
    assert payload["selector"] == {"section": "delegation_posture"}
    assert payload["matched"] is True
    assert payload["answer"]["canonical_doc"] == "docs/delegation-posture-contract.md"
    assert payload["answer"]["preferred_split"] == ["planner", "implementer", "validator"]
    assert "docs/delegation-posture-contract.md" in payload["refs"]
    assert "agentic-workspace defaults --format json" in payload["refs"]


def test_proof_command_reports_routes_and_current_health(tmp_path: Path, monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == "docs/proof-surfaces-contract.md"
    assert payload["command"] == "agentic-workspace proof --target ./repo --format json"
    assert payload["default_routes"]["planning_surfaces"] == "uv run python scripts/check/check_planning_surfaces.py"
    assert payload["current"]["installed_modules"] == ["planning"]
    assert payload["current"]["status_health"] == "healthy"
    assert payload["current"]["doctor_health"] == "healthy"
    assert payload["current"]["warnings"] == []
    assert payload["current"]["needs_review"] == []
    assert calls == []


def test_proof_route_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--route", "workspace_proof", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "proof"
    assert payload["selector"] == {"route": "workspace_proof"}
    assert payload["matched"] is True
    assert payload["answer"] == {
        "id": "workspace_proof",
        "command": "agentic-workspace proof --target ./repo --format json",
    }
    assert payload["target"] == tmp_path.as_posix()


def test_proof_current_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "planning").mkdir()
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))
    monkeypatch.setattr(
        cli,
        "_run_lifecycle_command",
        lambda **kwargs: {
            "health": "healthy",
            "warnings": [],
            "needs_review": [],
            "stale_generated_surfaces": [],
        },
    )

    assert cli.main(["proof", "--target", str(tmp_path), "--current", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"current": True}
    assert payload["answer"]["installed_modules"] == ["planning"]
    assert payload["answer"]["status_health"] == "healthy"


def test_ownership_command_reports_authority_map(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[ownership_classes.repo_owned]\n"
        'summary = "repo-owned"\n\n'
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n\n'
        "[[managed_surfaces]]\n"
        'module = "workspace"\n'
        'path = ".agentic-workspace/OWNERSHIP.toml"\n'
        'kind = "ownership-ledger"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-if-owned"\n\n'
        "[[fences]]\n"
        'name = "workspace-workflow-pointer"\n'
        'module = "workspace"\n'
        'file = "AGENTS.md"\n'
        'start = "<!-- agentic-workspace:workflow:start -->"\n'
        'end = "<!-- agentic-workspace:workflow:end -->"\n'
        'ownership = "managed_fence"\n'
        'uninstall_policy = "remove-fence-only"\n\n'
        "[[authority_surfaces]]\n"
        'concern = "active-execution-state"\n'
        'surface = "TODO.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "current work"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == "docs/ownership-authority-contract.md"
    assert payload["ledger_path"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["authority_surfaces"][0]["concern"] == "active-execution-state"
    assert payload["authority_surfaces"][0]["surface"] == "TODO.md"
    assert payload["warnings"] == []


def test_ownership_concern_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "active-execution-state"\n'
        'surface = "TODO.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "current work"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--concern", "active-execution-state", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["surface"] == "ownership"
    assert payload["selector"] == {"concern": "active-execution-state"}
    assert payload["matched"] is True
    assert payload["answer"]["surface"] == "TODO.md"
    assert payload["answer"]["owner"] == "repo"


def test_ownership_path_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert (
        cli.main(
            [
                "ownership",
                "--target",
                str(tmp_path),
                "--path",
                ".agentic-workspace/planning/agent-manifest.json",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "compact-contract-answer/v1"
    assert payload["selector"] == {"path": ".agentic-workspace/planning/agent-manifest.json"}
    assert payload["matched"] is True
    assert payload["answer"]["owner"] == "planning"
    assert payload["answer"]["matched_by"] == "module_root"


def test_config_command_reports_repo_owned_overrides(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "agentic-workspace.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n'
        'agent_instructions_file = "GEMINI.md"\n'
        'workflow_artifact_profile = "gemini"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] is True
    assert payload["workspace"]["default_preset"] == "planning"
    assert payload["workspace"]["agent_instructions_file"] == "GEMINI.md"
    assert payload["workspace"]["agent_instructions_file_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_profile"] == "gemini"
    assert payload["workspace"]["workflow_artifact_profile_source"] == "repo-config"
    assert payload["workspace"]["workflow_artifact_adapter"]["native_artifacts"] == [
        "implementation_plan.md",
        "task.md",
        "walkthrough.md",
    ]
    planning_policy = next(item for item in payload["update"]["modules"] if item["module"] == "planning")
    assert planning_policy["source"] == "repo-config"
    assert planning_policy["source_ref"] == "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"
    assert planning_policy["source_label"] == "planning feature ref"
    assert planning_policy["recommended_upgrade_after_days"] == 14
    assert payload["mixed_agent"]["repo_policy"]["source"] == "repo-config"
    assert payload["mixed_agent"]["repo_policy"]["authoritative"] is True


def test_config_command_reports_reserved_local_override_presence_without_applying_it(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "agentic-workspace.local.toml").write_text(
        "schema_version = 1\n\n[runtime]\nsupports_internal_delegation = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["local_override"]["exists"] is True
    assert payload["mixed_agent"]["local_override"]["applied"] is True
    assert payload["mixed_agent"]["local_override"]["status"] == "applied"
    assert payload["mixed_agent"]["effective_posture"]["supports_internal_delegation"] == {
        "value": True,
        "source": "local-override",
    }


def test_config_command_reports_narrow_local_override_fields_with_source_attribution(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    (target / "agentic-workspace.local.toml").write_text(
        "schema_version = 1\n\n"
        "[runtime]\n"
        "supports_internal_delegation = true\n"
        "strong_planner_available = true\n"
        "cheap_bounded_executor_available = true\n\n"
        "[handoff]\n"
        "prefer_internal_delegation_when_available = true\n",
        encoding="utf-8",
    )

    assert cli.main(["config", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mixed_agent"]["effective_posture"]["strong_planner_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["cheap_bounded_executor_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["effective_posture"]["prefer_internal_delegation_when_available"] == {
        "value": True,
        "source": "local-override",
    }
    assert payload["mixed_agent"]["derived_mode"]["planner_executor_pattern"] == "strong-planner-cheap-executor-available"
    assert payload["mixed_agent"]["derived_mode"]["handoff_preference"] == "prefer-internal-when-safe"


def test_modules_command_reports_installation_state_for_target(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["modules", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    assert planning_module["installed"] is True
    assert memory_module["installed"] is False


def test_skills_command_lists_registered_workspace_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    skill_ids = {entry["id"] for entry in payload["skills"]}
    assert "planning-autopilot" in skill_ids
    assert "memory-router" in skill_ids
    assert "planning-reporting" in skill_ids
    assert all(entry["registration"] == "explicit" for entry in payload["skills"])
    autopilot = next(entry for entry in payload["skills"] if entry["id"] == "planning-autopilot")
    assert "run autopilot" in autopilot["activation_hints"]["phrases"]


def test_skills_command_recommends_planning_autopilot_for_active_milestone_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "run autopilot and implement the current active milestone from the execplan",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-autopilot"
    assert payload["recommendations"][0]["score"] > 0
    assert any("phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_recommends_planning_reporting_for_setup_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "setup the repo after bootstrap without widening init",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload["recommendations"]] == ["planning-reporting"]
    assert payload["recommendations"][0]["score"] == 10
    assert "setup uses the compact planning reporting surface" in payload["recommendations"][0]["reasons"][0]


def test_skills_command_recommends_memory_router_for_note_selection_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "find the smallest memory note set and route memory for this task",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "memory-router"
    assert payload["recommendations"][0]["source_kind"] == "installed-core-skills"


def test_skills_command_recommends_review_skill_for_natural_review_request(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "perform a review of the planning package",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-review-pass"
    assert any("verb match" in reason or "phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_keeps_repo_owned_memory_and_general_skill_sources_distinct(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_json(
        target / "memory" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-memory-skills",
            "source_kind": "repo-owned-memory-skills",
            "skills": [
                {
                    "id": "package-context-inspection",
                    "path": "package-context-inspection/SKILL.md",
                    "summary": "inspect package context notes",
                },
                {
                    "id": "memory-reporting",
                    "path": "memory-reporting/SKILL.md",
                    "summary": "report memory freshness and cleanup signals",
                },
            ],
        },
    )
    _write(
        target / "memory" / "skills" / "README.md",
        "# Memory skills\n",
    )
    _write(
        target / "memory" / "skills" / "package-context-inspection" / "SKILL.md",
        "# Skill\n",
    )
    _write(
        target / "memory" / "skills" / "memory-reporting" / "SKILL.md",
        "# Skill\n",
    )
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "foundation-stability-check",
                    "path": "foundation-stability-check/SKILL.md",
                    "summary": "recheck operational authority",
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "README.md", "# Tool skills\n")
    _write(target / "tools" / "skills" / "foundation-stability-check" / "SKILL.md", "# Skill\n")

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_skill = next(entry for entry in payload["skills"] if entry["id"] == "package-context-inspection")
    memory_reporting_skill = next(entry for entry in payload["skills"] if entry["id"] == "memory-reporting")
    tool_skill = next(entry for entry in payload["skills"] if entry["id"] == "foundation-stability-check")

    assert memory_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_skill["path"] == "memory/skills/package-context-inspection/SKILL.md"
    assert memory_reporting_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_reporting_skill["path"] == "memory/skills/memory-reporting/SKILL.md"
    assert tool_skill["source_kind"] == "repo-owned-tool-skills"
    assert tool_skill["path"] == "tools/skills/foundation-stability-check/SKILL.md"


def test_init_dispatches_to_full_preset_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "full"
    assert payload["modules"] == ["planning", "memory"]
    assert payload["mode"] == "install"
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_uses_default_preset_from_repo_config(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "agentic-workspace.toml").write_text(
        'schema_version = 1\n\n[workspace]\ndefault_preset = "planning"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "planning"
    assert payload["modules"] == ["planning"]
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_uses_explicit_modules_csv(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--modules", "memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["memory"]
    assert calls == [("memory", "install", {"target": str(tmp_path), "dry_run": False, "force": False})]


def test_init_reports_required_prompt_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Memory\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "TODO.md", "docs/execplans", "memory/index.md"]
    assert payload["agent_instructions_file"] == "AGENTS.md"
    assert payload["handoff_prompt_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert "handoff_prompt" in payload
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["confirmed_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert payload["handoff_record"]["intent"]["interpreted_intent"]["summary"] == "set up this repo for both Planning and Memory"
    assert "must_not_change" in payload["handoff_record"]
    assert "escalate_when" in payload["handoff_record"]
    assert "Intent:" in payload["handoff_prompt"]
    assert "confirmed:" in payload["handoff_prompt"]
    assert "interpreted:" in payload["handoff_prompt"]
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.md").exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert (tmp_path / "llms.txt").exists()
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_can_write_prompt_file(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    prompt_path = tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--write-prompt", str(prompt_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["handoff_prompt_path"] == prompt_path.as_posix()
    assert payload["handoff_record_path"] == (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").as_posix()
    assert prompt_path.exists()
    assert (tmp_path / ".agentic-workspace" / "bootstrap-handoff.json").exists()
    assert "Finish the Agentic Workspace bootstrap" in prompt_path.read_text(encoding="utf-8")


def test_selection_commands_accept_non_interactive_flag() -> None:
    parser = cli.build_parser()

    init_args = parser.parse_args(["init", "--target", ".", "--non-interactive"])
    status_args = parser.parse_args(["status", "--target", ".", "--non-interactive"])
    prompt_args = parser.parse_args(["prompt", "upgrade", "--modules", "planning", "--target", ".", "--non-interactive"])

    assert init_args.non_interactive is True
    assert status_args.non_interactive is True
    assert prompt_args.non_interactive is True


def test_prompt_init_uses_dry_run_workspace_bootstrap(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "init"
    assert payload["dry_run"] is True
    assert "handoff_prompt" in payload
    assert "Finish the Agentic Workspace bootstrap" in payload["handoff_prompt"]
    assert "handoff_record" not in payload
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_prompt_init_non_interactive_marks_prompt_free_handoff(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "do not assume a human can answer prompts or unblock a PTY" in payload["handoff_prompt"]


def test_prompt_init_returns_structured_handoff_record_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["prompt_requirement"] != "none"
    assert payload["handoff_record"]["kind"] == "workspace-bootstrap-handoff/v1"
    assert payload["handoff_record"]["next"]["immediate_brief"] == ".agentic-workspace/bootstrap-handoff.md"


def test_prompt_upgrade_builds_workspace_handoff_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "upgrade"
    assert payload["dry_run"] is True
    assert "Use the workspace CLI as the lifecycle entrypoint" in payload["handoff_prompt"]
    assert "README.md: inspect manually" in payload["handoff_prompt"]


def test_prompt_upgrade_non_interactive_mentions_prompt_free_execution(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--non-interactive", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["non_interactive"] is True
    assert "Run this flow with `--non-interactive`" in payload["handoff_prompt"]


def test_init_uses_recommended_prompt_for_single_existing_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["AGENTS.md"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_autodetects_existing_gemini_file_as_startup_entrypoint(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "GEMINI.md").write_text("# Existing Gemini\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["detected_surfaces"] == ["GEMINI.md"]
    assert "Read GEMINI.md first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


def test_init_treats_multiple_supported_startup_files_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "GEMINI.md").write_text("# Existing Gemini\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "GEMINI.md"]


def test_init_can_create_gemini_startup_file_for_blank_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert (
        cli.main(
            [
                "init",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["agent_instructions_file"] == "GEMINI.md"
    assert (tmp_path / "GEMINI.md").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert "Read GEMINI.md first." in (tmp_path / "llms.txt").read_text(encoding="utf-8")


def test_init_dry_run_rewrites_module_startup_actions_for_custom_agent_file(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert (
        cli.main(
            [
                "init",
                "--modules",
                "planning",
                "--target",
                str(tmp_path),
                "--agent-instructions-file",
                "GEMINI.md",
                "--dry-run",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "GEMINI.md" in payload["preserved_existing"]
    assert "AGENTS.md" not in payload["preserved_existing"]


def test_init_treats_existing_llms_file_as_existing_workspace_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "llms.txt").write_text("# External agent handoff\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "light_existing_workflow"
    assert payload["inferred_policy"] == "preserve_existing_and_adopt"
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["llms.txt"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_docs_heavy_repo_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("# Existing Roadmap\n", encoding="utf-8")
    (tmp_path / "docs" / "contributor-playbook.md").parent.mkdir(parents=True)
    (tmp_path / "docs" / "contributor-playbook.md").write_text("# Contributor Playbook\n", encoding="utf-8")
    (tmp_path / "docs" / "maintainer-commands.md").write_text("# Maintainer Commands\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        "AGENTS.md",
        "ROADMAP.md",
        "TODO.md",
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
    ]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "docs/contributor-playbook.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_existing_handoff_plus_workflow_surface_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# External agent handoff\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "docs_heavy_existing_repo"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "llms.txt"]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "llms.txt: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_partial_module_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Memory\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "memory/index.md: partial module state detected",
        "memory/index.md: reconcile existing workflow surface ownership",
    ]


def test_init_marks_partial_planning_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        "docs/execplans: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        "docs/execplans: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_mixed_module_partial_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Existing memory index\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["repo_state"] == "partial_or_placeholder_state"
    assert payload["inferred_policy"] == "require_explicit_handoff"
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        "docs/execplans: partial module state detected",
        "memory/index.md: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        "docs/execplans: reconcile existing workflow surface ownership",
        "memory/index.md: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_status_detects_installed_modules_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, calls)
    (tmp_path / "planning").mkdir()
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: descriptors)

    assert cli.main(["status", "--target", str(tmp_path)]) == 0

    assert calls == [("planning", "status", {"target": str(tmp_path)})]


def test_init_requires_git_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_preset_conflicts_with_modules(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--preset", "planning", "--modules", "planning", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_real_init_creates_combined_memory_and_planning_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()
    assert (target / "memory" / "index.md").exists()
    assert (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").exists()
    assert (target / "TODO.md").exists()
    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in agents_text
    assert "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules." in agents_text
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself." in agents_text
    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert "<PROJECT_NAME>" not in agents_text


def test_install_real_init_can_use_gemini_as_root_startup_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--agent-instructions-file", "GEMINI.md"]) == 0

    assert (target / "GEMINI.md").exists()
    assert not (target / "AGENTS.md").exists()
    gemini_text = (target / "GEMINI.md").read_text(encoding="utf-8")
    assert "Read `GEMINI.md`." in gemini_text
    assert "2. `GEMINI.md`." in gemini_text
    assert "Read GEMINI.md first." in (target / "llms.txt").read_text(encoding="utf-8")


def test_status_real_init_reports_workspace_shared_layer_surfaces(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(action["path"] == ".agentic-workspace/WORKFLOW.md" and action["kind"] == "current" for action in workspace_report["actions"])
    assert any(
        action["path"] == ".agentic-workspace/OWNERSHIP.toml" and action["kind"] == "current" for action in workspace_report["actions"]
    )


def test_report_real_init_summarizes_combined_workspace_state(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["report", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "workspace-report/v1"
    assert payload["command"] == "report"
    assert payload["schema"]["schema_version"] == "workspace-reporting-schema/v1"
    assert payload["schema"]["command"] == "agentic-workspace report --target ./repo --format json"
    assert "discovery" in payload["schema"]["shared_fields"]
    assert payload["selected_modules"] == ["planning", "memory"]
    assert payload["installed_modules"] == ["planning", "memory"]
    assert payload["health"] == "healthy"
    assert payload["next_action"]["summary"] == "No immediate action"
    assert any(
        item["surface"]
        in {
            "docs/delegated-judgment-contract.md",
            "docs/resumable-execution-contract.md",
            "docs/capability-aware-execution.md",
            "docs/execution-summary-contract.md",
        }
        for item in payload["discovery"]["memory_candidates"]
    )
    assert any(item["surface"] == "TODO.md" for item in payload["discovery"]["planning_candidates"])
    assert any(item["surface"] == "ROADMAP.md" for item in payload["discovery"]["ambiguous"])
    assert payload["reports"][0]["module"] == "planning"
    assert payload["config"]["mixed_agent"]["status"] == "reporting-only"


def test_status_real_init_reports_workspace_health(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "status"
    assert payload["modules"] == ["planning", "memory"]
    assert "health" in payload
    assert payload["registry"][0]["name"] == "planning"
    assert payload["registry"][1]["installed"] is True
    assert not any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])
    assert not any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_status_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])


def test_doctor_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "OWNERSHIP.toml").unlink()
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_doctor_json_exposes_standardised_summary_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workflow\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Agent Instructions\n\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-workspace:workflow:end -->\n\n"
        "Local repo instructions.\n",
        encoding="utf-8",
    )
    (tmp_path / "llms.txt").write_text(cli._external_agent_handoff_text(selected_modules=["planning", "memory"]), encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["doctor", "--modules", "planning,memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["created"] == ["planning", "memory"]
    assert payload["updated_managed"] == []
    assert payload["preserved_existing"] == []
    assert payload["needs_review"] == []
    assert payload["generated_artifacts"] == []
    assert payload["registry"][0]["name"] == "planning"


def test_status_warns_when_redundant_memory_pointer_block_remains(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8").replace(
            "<!-- agentic-workspace:workflow:end -->\n",
            "<!-- agentic-workspace:workflow:end -->\n\n"
            "<!-- agentic-memory:workflow:start -->\n"
            "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
            "<!-- agentic-memory:workflow:end -->\n",
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any("redundant top-level memory workflow pointer block still present" in warning for warning in payload["warnings"])


def test_doctor_real_init_preserves_package_contract_shortlists_in_reports(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_report = next(report for report in payload["reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["reports"] if report["module"] == "memory")

    assert any(
        action["path"] == ".agentic-workspace/planning/agent-manifest.json"
        and "compatibility contract files:" in action["detail"]
        and "AGENTS.md" in action["detail"]
        for action in planning_report["actions"]
    )
    assert any(
        action["path"] == ".agentic-workspace/memory/UPGRADE-SOURCE.toml"
        and "lower-stability helper files:" in action["detail"]
        and "scripts/check/check_memory_freshness.py" in action["detail"]
        for action in memory_report["actions"]
    )


def test_doctor_text_output_shows_package_contract_shortlists(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "[planning] Doctor report" in output
    assert "[memory] Doctor report" in output
    assert "compatibility contract files:" in output
    assert "lower-stability helper files:" in output


def test_doctor_real_init_reports_stale_planning_generated_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    (target / "tools" / "AGENT_ROUTING.md").write_text("stale generated routing\n", encoding="utf-8")
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(
        item
        == (
            "tools/AGENT_ROUTING.md: routing guide is out of sync with "
            ".agentic-workspace/planning/agent-manifest.json; run python scripts/render_agent_docs.py"
        )
        for item in payload["needs_review"]
    )


def test_upgrade_json_collects_summary_categories(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "upgrade"
    assert payload["updated_managed"] == ["tools/AGENT_QUICKSTART.md"]
    assert payload["preserved_existing"] == ["AGENTS.md"]
    assert payload["generated_artifacts"] == ["tools/AGENT_QUICKSTART.md"]
    assert payload["needs_review"] == ["README.md: inspect manually"]
    assert payload["warnings"] == []
    assert payload["stale_generated_surfaces"] == ["tools/AGENT_QUICKSTART.md"]


def test_upgrade_preserves_repo_owned_agents_content_outside_workspace_fence(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    agents_path = target / "AGENTS.md"
    original = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(
        f"# Repo Instructions\n\nKeep this repo-specific guidance.\n\n{original}\nMore local instructions.\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    updated = agents_path.read_text(encoding="utf-8")
    assert payload["health"] == "healthy"
    assert "# Repo Instructions" in updated
    assert "Keep this repo-specific guidance." in updated
    assert "More local instructions." in updated
    assert "<!-- agentic-workspace:workflow:start -->" in updated
    assert "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules." in updated


def test_upgrade_dry_run_syncs_module_update_source_metadata_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / "agentic-workspace.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(target), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert ".agentic-workspace/planning/UPGRADE-SOURCE.toml" in payload["updated_managed"]
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(
        action["path"] == ".agentic-workspace/planning/UPGRADE-SOURCE.toml" and action["kind"] == "would update"
        for action in workspace_report["actions"]
    )


def test_status_warns_when_module_update_source_metadata_drifts_from_repo_config(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--modules", "planning", "--target", str(target)]) == 0
    capsys.readouterr()
    (target / "agentic-workspace.toml").write_text(
        "schema_version = 1\n\n"
        "[workspace]\n"
        'default_preset = "planning"\n\n'
        "[update.modules.planning]\n"
        'source_type = "git"\n'
        'source_ref = "git+https://example.com/agentic-workspace@feature#subdirectory=packages/planning"\n'
        'source_label = "planning feature ref"\n'
        "recommended_upgrade_after_days = 14\n",
        encoding="utf-8",
    )

    assert cli.main(["status", "--modules", "planning", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/planning/UPGRADE-SOURCE.toml" in warning for warning in payload["warnings"])


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


def test_workspace_agents_template_uses_descriptor_guidance(tmp_path: Path) -> None:
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

    assert "Read `signals.md` when the signals module is installed." in rendered
    assert "- Signal routing: `signals.md`" in rendered


def _fake_descriptors(target_root: Path, calls: list[tuple[str, str, dict[str, object]]]) -> dict[str, cli.ModuleDescriptor]:
    def _build_handler(module_name: str, command_name: str):
        def _handler(**kwargs):
            calls.append((module_name, command_name, kwargs))
            return FakeResult(
                target_root=target_root,
                message=f"{command_name} {module_name}",
                dry_run=bool(kwargs.get("dry_run", False)),
                actions=[FakeAction(kind="created", path=target_root / module_name, detail=f"ran {command_name}")],
                warnings=[],
            )

        return _handler

    commands = ("install", "adopt", "upgrade", "uninstall", "doctor", "status")
    return {
        module_name: cli.ModuleDescriptor(
            name=module_name,
            description=f"{module_name} module",
            commands={command_name: _build_handler(module_name, command_name) for command_name in commands},
            detector=lambda detected_root, module_name=module_name: (detected_root / module_name).exists(),
            selection_rank=10 if module_name == "planning" else 20,
            include_in_full_preset=True,
            install_signals=(
                (Path("TODO.md"), Path("docs/execplans"), Path(".agentic-workspace/planning"))
                if module_name == "planning"
                else (Path("memory/index.md"), Path("memory/current"), Path(".agentic-workspace/memory"))
            ),
            workflow_surfaces=(
                (
                    Path("AGENTS.md"),
                    Path("TODO.md"),
                    Path("ROADMAP.md"),
                    Path("docs/execplans"),
                    Path("docs/contributor-playbook.md"),
                    Path("docs/maintainer-commands.md"),
                    Path(".agentic-workspace/planning"),
                    Path("tools/AGENT_QUICKSTART.md"),
                    Path("tools/AGENT_ROUTING.md"),
                )
                if module_name == "planning"
                else (
                    Path("AGENTS.md"),
                    Path("memory/index.md"),
                    Path("memory/current"),
                    Path(".agentic-workspace/memory"),
                )
            ),
            generated_artifacts=(
                (Path("tools/agent-manifest.json"), Path("tools/AGENT_QUICKSTART.md"), Path("tools/AGENT_ROUTING.md"))
                if module_name == "planning"
                else ()
            ),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(
                (
                    cli.RootAgentsCleanupBlock(
                        block=cli.MEMORY_POINTER_BLOCK,
                        start_marker=cli.MEMORY_WORKFLOW_MARKER_START,
                        end_marker=cli.MEMORY_WORKFLOW_MARKER_END,
                        label="memory workflow pointer block",
                    ),
                )
                if module_name == "memory"
                else ()
            ),
            capabilities=(
                ("active-execution-state", "execplan-routing", "generated-maintainer-guidance")
                if module_name == "planning"
                else ("durable-repo-knowledge", "anti-rediscovery-memory", "runbook-routing")
            ),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
        for module_name in ("planning", "memory")
    }


def _descriptors_with_mixed_actions(target_root: Path) -> dict[str, cli.ModuleDescriptor]:
    def _upgrade_handler(**kwargs):
        return FakeResult(
            target_root=target_root,
            message="upgrade planning",
            dry_run=bool(kwargs.get("dry_run", False)),
            actions=[
                FakeAction(
                    kind="would update",
                    path=target_root / "tools" / "AGENT_QUICKSTART.md",
                    detail="render quickstart from manifest",
                ),
                FakeAction(kind="skipped", path=target_root / "AGENTS.md", detail="repo-owned surface left unchanged"),
                FakeAction(kind="manual review", path=target_root / "README.md", detail="inspect manually"),
            ],
            warnings=[],
        )

    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description="planning module",
            commands={
                "install": _upgrade_handler,
                "adopt": _upgrade_handler,
                "upgrade": _upgrade_handler,
                "uninstall": _upgrade_handler,
                "doctor": _upgrade_handler,
                "status": _upgrade_handler,
            },
            detector=lambda detected_root: True,
            selection_rank=10,
            include_in_full_preset=True,
            install_signals=(Path("TODO.md"), Path("docs/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=(Path("AGENTS.md"), Path("tools/AGENT_QUICKSTART.md")),
            generated_artifacts=(Path("tools/AGENT_QUICKSTART.md"),),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
            startup_steps=(),
            sources_of_truth=(),
            root_agents_cleanup_blocks=(),
            capabilities=("active-execution-state",),
            dependencies=(),
            conflicts=(),
            result_contract=cli.ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
        )
    }


def _descriptors_with_install_signals(
    target_root: Path, calls: list[tuple[str, str, dict[str, object]]]
) -> dict[str, cli.ModuleDescriptor]:
    descriptors = _fake_descriptors(target_root, calls)
    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description=descriptors["planning"].description,
            commands=descriptors["planning"].commands,
            detector=lambda detected_root: (
                (detected_root / "TODO.md").exists()
                and (detected_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            selection_rank=descriptors["planning"].selection_rank,
            include_in_full_preset=descriptors["planning"].include_in_full_preset,
            install_signals=(Path("TODO.md"), Path("docs/execplans"), Path(".agentic-workspace/planning")),
            workflow_surfaces=descriptors["planning"].workflow_surfaces,
            generated_artifacts=descriptors["planning"].generated_artifacts,
            command_args=descriptors["planning"].command_args,
            startup_steps=descriptors["planning"].startup_steps,
            sources_of_truth=descriptors["planning"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["planning"].root_agents_cleanup_blocks,
            capabilities=descriptors["planning"].capabilities,
            dependencies=descriptors["planning"].dependencies,
            conflicts=descriptors["planning"].conflicts,
            result_contract=descriptors["planning"].result_contract,
        ),
        "memory": cli.ModuleDescriptor(
            name="memory",
            description=descriptors["memory"].description,
            commands=descriptors["memory"].commands,
            detector=lambda detected_root: (
                (detected_root / "memory" / "index.md").exists() and (detected_root / ".agentic-workspace" / "memory").exists()
            ),
            selection_rank=descriptors["memory"].selection_rank,
            include_in_full_preset=descriptors["memory"].include_in_full_preset,
            install_signals=(Path("memory/index.md"), Path("memory/current"), Path(".agentic-workspace/memory")),
            workflow_surfaces=descriptors["memory"].workflow_surfaces,
            generated_artifacts=descriptors["memory"].generated_artifacts,
            command_args=descriptors["memory"].command_args,
            startup_steps=descriptors["memory"].startup_steps,
            sources_of_truth=descriptors["memory"].sources_of_truth,
            root_agents_cleanup_blocks=descriptors["memory"].root_agents_cleanup_blocks,
            capabilities=descriptors["memory"].capabilities,
            dependencies=descriptors["memory"].dependencies,
            conflicts=descriptors["memory"].conflicts,
            result_contract=descriptors["memory"].result_contract,
        ),
    }


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    _write(path, json.dumps(payload, indent=2) + "\n")
