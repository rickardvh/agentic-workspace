from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from repo_planning_bootstrap.installer import create_execplan_scaffold, install_bootstrap, planning_revision, select_existing_owner

from agentic_workspace.adaptation import (
    admit_bounded_adaptation,
    bounded_adaptation_projection,
    coverage_signal_from_observation,
    execute_bounded_adaptation,
    machine_observed_coverage_signals,
)
from agentic_workspace.authority_envelope import mutation_baseline_payload
from agentic_workspace.module_contract import MODULE_CONTRACT_VERSION, module_contribution, validate_module_contract
from agentic_workspace.operating_decision import compile_context_maintenance_decision
from agentic_workspace.scoped_instructions import read_instruction

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = REPO_ROOT / "tests/fixtures/repo_evolution_scenario.json"


def _load_script(relative_path: str, module_name: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _coverage_observation(*, revision: str) -> dict[str, object]:
    return {
        "source_class": "agent",
        "owner_class": "scoped-instruction",
        "source_owner": ".agentic-workspace/instructions/api.md",
        "observed_addition": "API v2 work requires a compatibility proof procedure.",
        "source_refs": ["src/api/v2/router.py"],
        "evidence_refs": ["tests/api_v2/test_compat.py"],
        "affected_effects": ["procedure", "proof"],
        "operation_id": "instructions.create",
        "owner_revision": revision,
        "recurrence_identity": "api-v2-compatibility",
        "proposed_delta": {
            "action": "append_guidance",
            "heading": "API v2 compatibility",
            "guidance": "Run API v2 compatibility proof after boundary changes.",
            "positive_paths": ["src/api/v2/router.py"],
            "negative_paths": ["docs/api.md"],
        },
        "validation_route": ["pytest tests/api_v2/test_compat.py -q"],
    }


def _module_contract() -> dict[str, object]:
    return {
        "schema_version": MODULE_CONTRACT_VERSION,
        "name": "build-signals",
        "description": "Independent build signal capability.",
        "compatibility": {"reader_epoch": 1, "required_capabilities": ["module-resources-v1"]},
        "ownership": {"roots": [], "effect_classes": [], "authority_exclusions": ["cannot grant mutation authority"]},
        "relevance": {"task_terms": ["build signal"], "path_prefixes": ["build/signals/"]},
        "facts": [],
        "capabilities": {
            "resources": [{"id": "signals.latest", "ref": "signals://latest", "read_only": True}],
            "skills": [],
            "operations": [],
        },
        "result_semantics": {
            "schema_version": "signals/result/v1",
            "guaranteed_fields": ["status"],
            "effect_fields": ["effects"],
            "warning_fields": ["warnings"],
        },
    }


def test_versioned_repo_evolution_scenario_covers_required_sequence() -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    steps = {item["id"]: item for item in scenario["steps"]}
    assert scenario["kind"] == "agentic-workspace/repo-evolution-scenario/v1"
    assert scenario["initial_state"] == "valid-configured-repository"
    assert scenario["explicit_generic_maintenance_steps"] == 0
    assert {
        "generated-source-change",
        "planning-owner-selection",
        "review-topology-change",
        "module-add-remove",
        "rebuildable-manifest",
        "machine-proof-addition",
        "agent-semantic-addition",
        "equivalent-work-repeat",
    } == set(steps)
    assert steps["rebuildable-manifest"]["proof_ref"].endswith(
        "test_manifest_reconcile_repairs_interrupted_publish_without_rerunning_result"
    )


def test_repo_evolution_replay_executes_real_owner_transitions_and_stays_quiet(tmp_path: Path) -> None:
    trace: list[tuple[str, str]] = []

    generator = _load_script("scripts/generate/generate_command_packages.py", "repo_evolution_generator")
    source = tmp_path / "contracts/source.json"
    source.parent.mkdir(parents=True)
    source.write_text('{"revision": 1}\n', encoding="utf-8")

    class SourceWitnessLauncher:
        @staticmethod
        def source_cli_fingerprint_manifests(*, repo_root: Path):
            digest = hashlib.sha256((repo_root / "contracts/source.json").read_bytes()).hexdigest()
            return {"workspace": {"kind": "source-cli-fingerprint", "revision": f"sha256:{digest}"}}

        @staticmethod
        def source_cli_fingerprint_manifest_path(*, repo_root: Path, owner: str):
            return repo_root / "generated" / owner / ".agentic-workspace-cli-fingerprint.json"

    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=SourceWitnessLauncher)
    witness = tmp_path / "generated/workspace/.agentic-workspace-cli-fingerprint.json"
    before = witness.read_bytes()
    source.write_text('{"revision": 2}\n', encoding="utf-8")
    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=SourceWitnessLauncher)
    after = witness.read_bytes()
    generator._write_source_cli_fingerprint_manifests(repo_root=tmp_path, launcher=SourceWitnessLauncher)
    assert before != after and witness.read_bytes() == after
    trace.append(("generated-source-change", "rewritten-once"))

    planning_root = tmp_path / "planning"
    install_bootstrap(target=planning_root)
    create_execplan_scaffold(plan_id="owner-a", title="Owner A", target=planning_root, activate=True)
    create_execplan_scaffold(plan_id="owner-b", title="Owner B", target=planning_root)
    selected = select_existing_owner(
        "owner-b",
        target=planning_root,
        current_work_id="repo-evolution",
        expected_planning_revision=planning_revision(planning_root)["revision_id"],
    )
    repeated_selection = select_existing_owner("owner-b", target=planning_root, current_work_id="repo-evolution")
    assert selected.operation_receipt["outcome"] == "selected"
    assert repeated_selection.operation_receipt["outcome"] == "no-op"
    trace.append(("planning-owner-selection", "selected-then-no-op"))

    topology_root = tmp_path / "topology"
    topology_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=topology_root, check=True)
    subprocess.run(["git", "config", "user.email", "proof@example.invalid"], cwd=topology_root, check=True)
    subprocess.run(["git", "config", "user.name", "Proof"], cwd=topology_root, check=True)
    tracked = topology_root / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=topology_root, check=True)
    subprocess.run(["git", "commit", "-qm", "one"], cwd=topology_root, check=True)
    baseline_one = mutation_baseline_payload(target_root=topology_root, changed_paths=["tracked.txt"])
    tracked.write_text("two\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "two"], cwd=topology_root, check=True)
    baseline_two = mutation_baseline_payload(target_root=topology_root, changed_paths=["tracked.txt"])
    assert baseline_one["head"] != baseline_two["head"]
    assert baseline_one["observed_state"]["enforcement_fingerprint"] != baseline_two["observed_state"]["enforcement_fingerprint"]
    trace.append(("review-topology-change", "baseline-invalidated"))

    contract = validate_module_contract(_module_contract())
    contributed = module_contribution(contract, task="inspect build signal", changed_paths=[])
    removed_contract = _module_contract()
    removed_contract["capabilities"]["resources"] = []
    removed = module_contribution(validate_module_contract(removed_contract), task="inspect build signal", changed_paths=[])
    assert contributed["resources"][0]["id"] == "signals.latest"
    assert removed["resources"] == []
    trace.append(("module-add-remove", "contribution-removed"))

    runner = _load_script("scripts/check/run_compact_command.py", "repo_evolution_compact_runner")
    runner.REPO_ROOT = tmp_path
    runner.LOG_ROOT = tmp_path / "scratch/command-logs"
    runner.RESULT_ROOT = tmp_path / "scratch/validation-results"
    assert runner.main(["--label", "proof", "--run-id", "evolution", "--", sys.executable, "-c", "print('ok')"]) == 0
    run_root = runner.RESULT_ROOT / "evolution"
    result_path = run_root / "proof.json"
    result_mtime = result_path.stat().st_mtime_ns
    manifest_path = run_root / "manifest.json"
    manifest_path.write_text('{"corrupt": true}\n', encoding="utf-8")
    rebuilt = runner._update_manifest(result_root=runner.RESULT_ROOT, run_id="evolution")
    assert rebuilt["status"] == "rebuilt"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["result_count"] == 1
    assert result_path.stat().st_mtime_ns == result_mtime
    trace.append(("rebuildable-manifest", "rebuilt-from-record"))

    machine = bounded_adaptation_projection(
        machine_observed_coverage_signals(
            [
                {
                    "declaration_kind": "proof-route-declaration",
                    "observed_addition": "API v2 declares a focused proof route.",
                    "source_refs": [".agentic-workspace/config.toml#verification"],
                    "evidence_refs": ["tests/api_v2/test_compat.py"],
                    "owner_revision": "sha256:proof-r2",
                    "proposed_delta": {"action": "upsert_domain_lane", "lane_id": "api-v2"},
                    "validation_route": ["pytest tests/api_v2/test_compat.py -q"],
                }
            ]
        )
    )
    assert machine["candidates"][0]["promotion"]["operation_id"] == "proof.report"
    trace.append(("machine-proof-addition", "canonical-proof-candidate"))

    instruction = tmp_path / ".agentic-workspace/instructions/api.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text("---\npaths:\n  - src/api/**\n---\n\n# API\n\nExisting guidance.\n", encoding="utf-8")
    revision = read_instruction(instruction, root=tmp_path).revision
    projection = bounded_adaptation_projection(
        [coverage_signal_from_observation(_coverage_observation(revision=revision))], target_root=tmp_path
    )
    decision = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=projection
    )
    assert {item["id"] for item in decision["alternatives"]} == {"admit", "update", "retain", "dismiss"}
    execution = execute_bounded_adaptation(
        admit_bounded_adaptation(
            projection["candidates"][0],
            admitted_by="api-owner",
            choice="retain",
            decision_revision=decision["decision_revision"],
        ),
        target_root=tmp_path,
    )
    assert execution["mutation_applied"] is True
    trace.append(("agent-semantic-addition", "retained-in-canonical-source"))

    fresh_revision = read_instruction(instruction, root=tmp_path).revision
    fresh = bounded_adaptation_projection(
        [coverage_signal_from_observation(_coverage_observation(revision=fresh_revision))], target_root=tmp_path
    )
    repeated = compile_context_maintenance_decision(
        context_projection={"currentness": {"decision_requirements": []}}, bounded_adaptations=fresh
    )
    assert fresh["status"] == "quiet"
    assert repeated["status"] == "not-required"
    trace.append(("equivalent-work-repeat", "quiet-from-persisted-source"))

    assert [step for step, _outcome in trace] == [item["id"] for item in json.loads(SCENARIO_PATH.read_text())["steps"]]


def test_repo_evolution_evidence_reports_zero_generic_maintenance() -> None:
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    dogfood = (REPO_ROOT / "docs/maintainer/repo-evolution-dogfood-2026-08-22.md").read_text(encoding="utf-8")
    assert scenario["expected_metrics"] == {
        "manual_aw_maintenance": 0,
        "semantic_user_decisions": 1,
        "redundant_rediscovery": 0,
        "destination_owner_class_minimum": 3,
        "stable_first_line_cost": "none",
    }
    assert "Explicit generic AW-maintenance actions: 0" in dogfood
    assert "Fresh-runtime semantic replay: quiet" in dogfood
    assert "direct checked-in Planning state edit" not in dogfood
    assert "do not extend this scenario into a maintenance framework" in scenario["failure_route"]
