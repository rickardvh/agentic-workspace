from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace import (
    cli,
    workspace_runtime_core,
    workspace_runtime_startup,
)
from agentic_workspace import (
    module_contract as module_contract_runtime,
)
from agentic_workspace.module_contract import DiscoveredModule, validate_module_contract

SCENARIO_PATH = Path("tests/fixtures/self_configuration_lifecycle_v1.json")
GENERATED_TYPESCRIPT_PRIMITIVE = "./generated/workspace/typescript/src/hostPrimitiveSupport.mjs"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "scenario@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Scenario"], check=True)


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


def _apply_policy(
    *, target: Path, concerns: dict[str, Any], decision: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> dict[str, Any]:
    assert (
        cli.main(
            [
                "config-policy",
                "--target",
                str(target),
                "--decision-json",
                json.dumps(decision),
                "--expect-config-revision",
                concerns["mutation_context"]["local_config_revision"],
                "--expect-setup-identity",
                concerns["mutation_context"]["setup_identity"],
                "--format",
                "json",
            ]
        )
        == 0
    )
    return _json_output(capsys)


def _apply_generated_typescript_policy(*, target: Path, concerns: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    values = {
        "target": str(target),
        "decision_json": json.dumps(decision),
        "expect_config_revision": concerns["mutation_context"]["local_config_revision"],
        "expect_setup_identity": concerns["mutation_context"]["setup_identity"],
        "dry_run": False,
        "format": "json",
    }
    script = f"""
import {{ executeHostPrimitive }} from {json.dumps(GENERATED_TYPESCRIPT_PRIMITIVE)};
const payload = executeHostPrimitive('config.policy.apply', {json.dumps(values)}, {{}}, 'config.policy-apply');
console.log(JSON.stringify(payload));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_versioned_self_configuration_lifecycle_follows_only_routed_contracts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    assert scenario["version"] == 1
    assert scenario["user_actions"] == {
        "install_or_lifecycle_commands": 5,
        "genuine_semantic_answers": 3,
        "manual_setup_or_doctor_commands": 0,
        "raw_aw_state_edits": 0,
    }

    _init_git_repo(tmp_path)
    _write(tmp_path / "README.md", "# Signals service\n\nThe service turns build events into release signals.\n")
    _write(
        tmp_path / "pyproject.toml",
        "[project]\nname = 'signals-service'\nversion = '0.1.0'\n[tool.pytest.ini_options]\ntestpaths = ['tests']\n",
    )
    _write(tmp_path / "scratch" / "policy.md", "Enable every capability and retain everything forever.\n")

    original_descriptors = workspace_runtime_core._module_operations()
    module_state = {
        "semantic_revision": "signals-policy/v1",
        "source_revision": "signals-source/v1",
        "status": "satisfied",
        "source_status": "satisfied",
        "source": "docs/signals-policy.md",
        "description": "Independent release-signal policy capability.",
    }

    def signals_contract() -> dict[str, Any]:
        status = str(module_state["status"])
        source_status = str(module_state["source_status"])
        source = str(module_state["source"])
        return validate_module_contract(
            {
                "schema_version": "agentic-workspace/module-capability/v2",
                "name": "signals",
                "description": module_state["description"],
                "compatibility": {"reader_epoch": 1, "required_capabilities": ["module-setup-concerns-v1"]},
                "ownership": {
                    "roots": [],
                    "effect_classes": [],
                    "authority_exclusions": ["cannot grant mutation, proof, or completion authority"],
                },
                "relevance": {"task_terms": [], "path_prefixes": []},
                "capabilities": {
                    "resources": [],
                    "skills": [],
                    "operations": [],
                    "setup_concerns": [
                        {
                            "id": "retention-source",
                            "semantic_revision": module_state["semantic_revision"],
                            "source_revision": module_state["source_revision"],
                            "status": status,
                            "materiality": "action-required",
                            "owner": "signals.retention-policy",
                            "applicability": {"kind": "module-enabled"},
                            "route": {"kind": "human-decision", "id": "signals.retention-policy"},
                            "question": "Which repository-approved retention policy should govern release signals?",
                            "source_obligation": {
                                "semantic_need": "the repository-approved signal retention and deletion policy",
                                "source_class": "signal retention policy",
                                "owner": "signals.retention-policy",
                                "status": source_status,
                                "candidates": [source] if source_status == "satisfied" else [],
                                "current_source": source if source_status == "satisfied" else "",
                                "auto_bind_safe": False,
                                "affected_claims": ["signals-retention-ready"],
                                "continuation": {"kind": "create-source", "id": "signals.retention-policy"},
                            },
                        }
                    ],
                },
                "result_semantics": {
                    "schema_version": "signals/result/v1",
                    "guaranteed_fields": [],
                    "effect_fields": [],
                    "warning_fields": [],
                },
            }
        )

    def descriptors() -> dict[str, Any]:
        discovered = DiscoveredModule(
            name="signals",
            entry_point="scenario:signals",
            contract=signals_contract(),
            operations={},
            status="available",
        )
        return {**original_descriptors, "signals": workspace_runtime_core._external_module_descriptor(discovered)}

    monkeypatch.setattr(workspace_runtime_core, "_module_operations", descriptors)
    monkeypatch.setattr(workspace_runtime_startup, "_module_operations", descriptors)
    monkeypatch.setattr(
        module_contract_runtime,
        "discover_module_contracts",
        lambda: [
            DiscoveredModule(name="signals", entry_point="scenario:signals", contract=signals_contract(), operations={}, status="available")
        ],
    )

    # The user performs only the documented minimal install. Setup is not named.
    assert cli.main(["init", "--target", str(tmp_path), "--modules", "planning,memory,signals", "--format", "json"]) == 0
    _json_output(capsys)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Add a release signal formatter.", "--format", "json"]) == 0
    first_start = _json_output(capsys)["decision_packet"]
    assert first_start["action"]["id"] == "reconcile-repository-configuration"
    assert first_start["configuration_readiness"]["exact_continuation"]["command"].endswith("setup --target . --format json")

    # A generic agent follows the returned route; it does not discover setup from docs or raw config.
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    inferred = _json_output(capsys)["configuration_concerns"]
    assert inferred["human_questions"] == []
    assert {item["concern_id"] for item in inferred["zero_interaction_actions"]} >= {
        "system-intent-source",
        "proof-route",
    }
    assert "scratch/policy.md" not in inferred["inspection_budget"]["inspected_sources"]
    assert cli.main(["system-intent", "--target", str(tmp_path), "--sync", "--format", "json"]) == 0
    _json_output(capsys)

    # One explicit behavioral choice uses the typed owner and causes one genuine follow-up question.
    opt_in = {
        "kind": "agentic-workspace/config-policy-decision/v1",
        "concern_id": "orchestration-opt-in",
        "authority": "human-answer",
        "scope": "local",
        "setup_identity": inferred["mutation_context"]["setup_identity"],
        "changes": {"delegation.execution_role": "orchestrator"},
    }
    _apply_policy(target=tmp_path, concerns=inferred, decision=opt_in, capsys=capsys)
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    choice = _json_output(capsys)["configuration_concerns"]
    assert [item["concern_id"] for item in choice["human_questions"]] == ["orchestration-posture"]
    question = choice["human_questions"][0]
    assert "automatically" in question["question"]
    assert all(item["consequence"] for item in question["alternatives"])

    # The question is deferred. Unrelated work proceeds, affected delegation work re-elevates setup.
    _apply_policy(
        target=tmp_path,
        concerns=choice,
        decision=choice["continuation"]["actions"]["defer"]["decision"],
        capsys=capsys,
    )
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Edit README wording.", "--format", "json"]) == 0
    deferred = _json_output(capsys)["decision_packet"]["configuration_readiness"]
    assert deferred["status"] == "follow-up-deferred"
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Delegate a release review.", "--format", "json"]) == 0
    affected = _json_output(capsys)["decision_packet"]["configuration_readiness"]
    assert affected["status"] == "action-required"

    # A new session has only compact canonical state; it receives the one unresolved question again.
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    resumed = _json_output(capsys)["configuration_concerns"]
    assert resumed["continuation"]["user_disposition"] == "deferred"
    assert resumed["continuation"]["unresolved_concern_ids"] == ["orchestration-posture"]
    assert [item["concern_id"] for item in resumed["human_questions"]] == ["orchestration-posture"]
    selected = next(item for item in resumed["human_questions"][0]["alternatives"] if item["id"] == "automatic-best-fit")
    _apply_policy(target=tmp_path, concerns=resumed, decision=selected["decision"], capsys=capsys)
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    completed = _json_output(capsys)["configuration_concerns"]
    assert completed["human_questions"] == []
    generated_completion = _apply_generated_typescript_policy(
        target=tmp_path,
        concerns=completed,
        decision=completed["mutation_context"]["reconciliation_completion"]["decision"],
    )
    assert generated_completion["status"] == "applied"
    local_config = (tmp_path / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")
    assert "[setup]" not in local_config
    assert "unresolved_concerns" not in local_config

    for task in ("Edit README wording.", "Add a formatter test.", "Inspect the release package."):
        assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
        assert "configuration_readiness" not in _json_output(capsys)["decision_packet"]

    # An explicit lifecycle refresh with cosmetic-only module metadata produces no setup work.
    module_state["description"] = "Independent release-signal policy capability with clearer documentation."
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Edit README wording.", "--format", "json"]) == 0
    assert "configuration_readiness" not in _json_output(capsys)["decision_packet"]

    # A later current contract jumps directly to a human-owned source delta; old setup decisions are not replayed.
    module_state.update(
        semantic_revision="signals-policy/v3",
        source_revision="signals-source/v3",
        status="human-decision-required",
        source_status="missing",
        source="docs/signals-policy.md",
    )
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Inspect release signals.", "--format", "json"]) == 0
    changed = _json_output(capsys)["decision_packet"]["configuration_readiness"]
    assert changed["changed_concern_ids"] == ["module:signals:retention-source"]
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    source_delta = _json_output(capsys)["configuration_concerns"]
    assert [item["concern_id"] for item in source_delta["human_questions"]] == ["module:signals:retention-source"]
    assert source_delta["source_obligations"][0]["source_class"] == "signal retention policy"
    _write(tmp_path / "docs" / "signals-policy.md", "# Signal retention\n\nRetain release signals for 30 days.\n")
    module_state.update(source_revision="signals-source/v3-resolved", status="satisfied", source_status="satisfied")
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    resolved_delta = _json_output(capsys)["configuration_concerns"]
    _apply_policy(
        target=tmp_path,
        concerns=resolved_delta,
        decision=resolved_delta["mutation_context"]["reconciliation_completion"]["decision"],
        capsys=capsys,
    )

    # Multi-release convergence observes v7 directly, then a durable lifecycle disable retires it without replay.
    module_state.update(
        semantic_revision="signals-policy/v7",
        source_revision="signals-source/v7",
        status="human-decision-required",
        source_status="missing",
    )
    assert cli.main(["setup", "--target", str(tmp_path), "--format", "json"]) == 0
    current_only = _json_output(capsys)["configuration_concerns"]
    current_module = next(item for item in current_only["concerns"] if item["id"] == "module:signals:retention-source")
    assert current_module["contract"]["semantic_revision"] == "signals-policy/v7"
    assert current_module["delta_status"] == "semantics-changed"
    assert cli.main(["uninstall", "--target", str(tmp_path), "--modules", "signals", "--format", "json"]) == 0
    _json_output(capsys)
    assert cli.main(["start", "--target", str(tmp_path), "--task", "Edit README wording.", "--format", "json"]) == 0
    final_start = _json_output(capsys)["decision_packet"]
    assert "configuration_readiness" not in final_start
