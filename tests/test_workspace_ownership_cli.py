from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


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
        'surface = ".agentic-workspace/planning/state.toml"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "current work"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["canonical_doc"] == ".agentic-workspace/docs/ownership-authority-contract.md"
    assert payload["ledger_path"] == ".agentic-workspace/OWNERSHIP.toml"
    assert payload["authority_surfaces"][0]["concern"] == "active-execution-state"
    assert payload["authority_surfaces"][0]["surface"] == ".agentic-workspace/planning/state.toml"
    assert any(entry["surface"] == ".agentic-workspace/planning/" for entry in payload["boundary_review"]["package_owned"]["module_roots"])
    assert any(
        entry["surface"] == ".agentic-workspace/OWNERSHIP.toml" for entry in payload["boundary_review"]["package_owned"]["managed_surfaces"]
    )
    assert len(payload["boundary_review"]["repo_owned"]["authority_surfaces"]) == 1
    assert payload["boundary_review"]["middle_ground"]["managed_fences"][0]["surface"] == "AGENTS.md#agentic-workspace:workflow"
    assert payload["boundary_review"]["smallest_explicit_repo_hook"]["surface"] == "AGENTS.md#agentic-workspace:workflow"
    assert payload["warnings"] == []


def test_ownership_real_init_does_not_settle_repo_root_memory_as_repo_owned_contract(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["ownership", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert any(
        entry["surface"] == ".agentic-workspace/memory/" and entry["owner"] == "memory" and entry["ownership"] == "module_managed"
        for entry in payload["authority_surfaces"]
    )
    assert not any(entry["surface"] == "memory/" for entry in payload["authority_surfaces"])
    assert not any(entry["surface"] == "memory/" for entry in payload["boundary_review"]["repo_owned"]["authority_surfaces"])
    assert payload["boundary_review"]["smallest_explicit_repo_hook"]["surface"] == "AGENTS.md#agentic-workspace:workflow"


def test_ownership_diagnostics_report_startup_adapter_drift_and_ambiguity(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target), "--preset", "planning"]) == 0
    capsys.readouterr()
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8")
        + "\n\nAuthoritative source of truth for this sprint.\nCurrent task handoff: continue the checkout redesign.\n",
        encoding="utf-8",
    )
    _write(target / "llms.txt", "Authoritative source of truth for external agents.\n", encoding="utf-8")

    assert cli.main(["ownership", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    diagnostics = payload["diagnostics"]
    assert diagnostics["status"] == "attention-needed"
    findings = {finding["id"]: finding for finding in diagnostics["findings"]}
    assert findings["startup-adapter-active-state"]["concern"] == "active execution state"
    assert findings["startup-adapter-active-state"]["suspected_drift_surface"] == "AGENTS.md"
    assert findings["startup-authority-ambiguous"]["status"] == "ambiguous-owner"
    assert set(findings["startup-authority-ambiguous"]["claimed_by"]) >= {"AGENTS.md", "llms.txt"}


def test_ownership_diagnostics_report_missing_config_owner(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n", encoding="utf-8")
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    findings = {finding["id"]: finding for finding in payload["diagnostics"]["findings"]}
    assert findings["workspace-policy-missing-owner"]["status"] == "missing-owner"
    assert findings["workspace-policy-missing-owner"]["expected_primary_owner"] == ".agentic-workspace/config.toml"


def test_ownership_concern_selector_returns_compact_contract_answer(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "active-execution-state"\n'
        'surface = ".agentic-workspace/planning/state.toml"\n'
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
    assert payload["answer"]["surface"] == ".agentic-workspace/planning/state.toml"
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


def test_ownership_path_selector_includes_host_repo_subsystems(tmp_path: Path, monkeypatch, capsys) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text(
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[subsystems]]\n"
        'id = "payments"\n'
        'paths = ["src/payments/**"]\n'
        'owns = ["payment orchestration"]\n'
        'does_not_own = ["catalog pricing"]\n'
        'proof = ["npm test -- payments"]\n'
        'escalate_when = ["payment provider contract changes"]\n\n'
        "[[subsystems]]\n"
        'id = "payments-api"\n'
        'paths = ["src/payments/api/**"]\n'
        'owns = ["payment API handlers"]\n'
        'proof = ["npm test -- payments-api"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, []))

    assert cli.main(["ownership", "--target", str(tmp_path), "--path", "src/payments/api/refund.ts", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["matched"] is True
    answer = payload["answer"]
    assert answer["matched_by"] == "subsystem"
    assert answer["primary_subsystem"]["id"] == "payments-api"
    assert answer["subsystem_overlap_count"] == 2
    assert answer["subsystems"][1]["id"] == "payments"
    assert answer["subsystems"][1]["does_not_own"] == ["catalog pricing"]


def test_ownership_path_answer_includes_authority_marker_and_boundary_warning(capsys) -> None:
    assert cli.main(["ownership", "--path", "llms.txt", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    answer = payload["answer"]
    assert answer["authority_marker"] == {
        "path": "llms.txt",
        "authority": "generated-adapter",
        "canonical_source": "src/agentic_workspace/cli.py:_external_agent_handoff_text",
        "safe_to_edit": False,
        "refresh_command": "make maintainer-surfaces",
    }
    assert answer["boundary_warning"]["requires_attention"] is True


def test_authority_marker_policy_representative_paths_match_runtime() -> None:
    policy = authority_markers_manifest()

    for marker in policy["markers"]:
        for path in marker["representative_paths"]:
            actual = cli._authority_marker_for_path(path)  # type: ignore[attr-defined]
            assert actual["authority"] == marker["authority"]
            assert actual["safe_to_edit"] == marker["safe_to_edit"]
            assert actual["refresh_command"] == marker["refresh_command"]
