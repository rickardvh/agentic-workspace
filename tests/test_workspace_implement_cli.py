from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def _write_empty_planning_state(target_root: Path) -> None:
    _write(
        target_root / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )


def _write_planning_lane_schema(target: Path) -> None:
    schema = json.loads(Path(".agentic-workspace/planning/schemas/planning-lane.schema.json").read_text(encoding="utf-8"))
    _write_json(target / ".agentic-workspace" / "planning" / "schemas" / "planning-lane.schema.json", schema)


def _implement_context(payload: dict[str, object]) -> dict[str, object]:
    context = payload.get("context")
    return context if isinstance(context, dict) else payload


def test_implement_changed_surfaces_task_posture_packet(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "def changed():\n    return True\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement #1392 in full",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["task_posture_packet"]
    assert packet["kind"] == "agentic-workspace/task-posture-packet/v1"
    assert packet["posture_adherence"]["closeout_question"].startswith("Did the work follow the task posture packet")
    assert packet["dynamic_instruction_projection"]["provenance_preserved"] is True
    assert "knowledge_gates" not in packet


def test_implement_surfaces_pre_work_knowledge_gate_for_source_authority_task(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path)]) == 0
    capsys.readouterr()
    _write(tmp_path / "docs" / "package" / "knowledge-gates.md", "# Pre-Work Knowledge Gates\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/package/knowledge-gates.md",
                "--task",
                "Implement #1395 pre-work knowledge gates",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    packet = payload["task_posture_packet"]
    gates = {gate["gate_id"]: gate for gate in packet["knowledge_gates"]}
    assert gates["source-authority-model"]["force"] == "required_before_design"
    assert gates["source-authority-model"]["resolution_state"] == "open"
    assert "blocked_claims" not in packet
    assert all("blocked_claims" not in gate for gate in packet["knowledge_gates"])
    assert "change gate vocabulary without checking source authority" in packet["blocked_actions"]
    assert "full_intent_complete" in packet["closeout_boundaries"]
    assert packet["gate_summary"]["blocking_count"] >= 1


def test_implement_command_returns_bounded_context_and_boundary_warnings(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
                "generated/workspace/python/cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context/v1"
    assert payload["inspect_files"] == [
        "packages/planning/bootstrap/repo_planning_bootstrap/installer.py",
        "generated/workspace/python/cli.py",
    ]
    assert payload["required_validation_commands"] == [
        "agentic-workspace defaults --section root_cli_authority --format json",
        "uv run python scripts/check/check_generated_command_packages.py",
        "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
        "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
        "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q",
    ]
    freshness = payload["proof"]["generated_cli_freshness"]
    assert freshness["status"] == "required"
    assert freshness["obligation"] == "required"
    assert freshness["freshness_check_command"] == "uv run python scripts/generate/generate_command_packages.py --check"
    assert freshness["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert freshness["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert "uv run python scripts/check/check_generated_command_packages.py" in freshness["required_commands"]
    parity = freshness["generated_target_parity"]
    assert parity["status"] == "required"
    assert parity["target_families"] == ["python", "typescript"]
    assert "Python-only proof" in parity["claim_rule"]
    proof_tiers = {tier["id"]: tier["commands"] for tier in payload["proof"]["proof_command_tiers"]["tiers"]}
    assert proof_tiers["generated_contract"][0]["command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert any(item["command"].endswith("--require-docker") for item in proof_tiers["environmental"])
    retry = payload["proof"]["transient_validation_retry"]
    assert retry["status"] == "available"
    assert retry["retry_limit"] == 1
    assert "uv run python scripts/check/check_generated_command_packages.py --python-conformance" in retry["applies_to"]
    assert payload["proof"]["unavailable_commands"] == []
    assert payload["proof"]["cli_authority_review"]["classifications"][0]["role"] == "projection"
    trust = payload["generated_surface_trust"]
    assert trust["status"] == "present"
    assert trust["direct_edit_blocked_paths"] == ["generated/workspace/python/cli.py"]
    assert trust["items"][0]["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert trust["items"][0]["freshness_status"] == "validation-required"
    assert trust["items"][0]["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert trust["items"][0]["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert trust["items"][0]["direct_edit_allowed"] is False
    assert "Do not hand-edit generated/workspace/python/cli.py" in trust["items"][0]["direct_edit_policy"]
    assert payload["orientation"]["status"] == "changed-path-context"
    assert "preflight" in payload["orientation"]["preflight_command"]
    assert "lowers continuation and review trust" in payload["orientation"]["trust_note"]
    assert "unstated intent" in payload["inference_limits"]["rule"]
    assert payload["execution_posture"]["kind"] == "agentic-workspace/execution-posture/v1"
    assert payload["execution_posture"]["delegation_control"]["effective_mode"] in {"suggest", "auto"}
    assert payload["execution_posture"]["delegation_control"]["execution_permitted"] is (
        payload["execution_posture"]["delegation_control"]["effective_mode"] == "auto"
    )
    assert payload["delegation_decision"]["status"] == "evaluated"
    assert payload["delegation_decision"] == payload["execution_posture"]["delegation_decision"]
    assert payload["delegation_decision"]["mode"] in {"suggest", "auto"}
    assert payload["acceptance_reconciliation"]["requested_outcomes"] == []
    assert payload["acceptance"]["status"] == "unavailable"
    assert payload["objective_drift"]["status"] == "unavailable"
    assert "safer path" in payload["execution_posture"]["quality_tradeoff"].lower()
    assert "token" in payload["execution_posture"]["token_tradeoff"].lower()
    assert payload["durable_intent"]["kind"] == "agentic-workspace/durable-intent-decision/v1"
    assert payload["durable_intent"]["subsystem_intent"]["surface"] == ".agentic-workspace/system-intent/subsystems.toml"
    assert (
        "whether proof commands were actually executed unless evidence is recorded elsewhere" in payload["inference_limits"]["cannot_infer"]
    )
    assert payload["path_boundaries"][0]["authority"] == "payload"
    assert payload["path_boundaries"][0]["requires_attention"] is True
    assert payload["authority_markers"][0]["safe_to_edit"] is False
    assert payload["next_allowed_action"] == "Resolve boundary warnings before editing."
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["gate_result"] == "agent-work-shape-decision-required"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["planning_safety_gate"]["work_shape_guidance"]["hard_blockers"] == []


def test_implement_selects_active_assurance_requirements_from_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
authority_refs = ["docs/compliance/privacy.md"]
required_evidence = ["authority_consulted"]
proof_profile = "privacy"
force = "required-before-closeout"
blocking_claims = ["claim-work-complete", "close-parent-lane"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "db/migrations/001_privacy.sql",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    selected = json.loads(capsys.readouterr().out)
    requirements = selected["values"]["assurance_requirements"]
    assert requirements["status"] == "attention"
    assert requirements["active"][0]["id"] == "privacy_data"
    assert requirements["active"][0]["applies_because"] == ["changed path matched db/migrations/**"]
    assert requirements["evidence_status"][0]["missing_evidence"] == ["authority_consulted"]


def test_implement_keeps_unmatched_assurance_requirements_out_of_tiny_output(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.privacy_data]
level = "high"
applies_to_paths = ["db/migrations/**"]
required_evidence = ["authority_consulted"]
force = "required-before-closeout"
""",
    )

    assert cli.main(["implement", "--target", str(tmp_path), "--changed", "README.md", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "assurance_requirements" not in payload


def test_implement_routine_work_context_reports_memory_use_when_as_learned_evidence(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "index.md", "# Memory index\n")
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "domains" / "parser.md", "# Parser\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/parser.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/parser.md"
authority = "learned"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
use_when = ["parser refactor"]
evidence = ["Memory fixture"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/parser.py",
                "--task",
                "Plan parser refactor safely",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    review = routine["knowledge_authority_review"]
    source = review["matched_sources"][0]
    assert source["owner_surface"] == ".agentic-workspace/memory/repo/domains/parser.md"
    assert source["authority"] == "learned"
    assert source["applies_because"] == ["task text matched parser refactor"]
    assert "Memory manifest metadata" in source["authority_boundary"]["observed_by_aw"]
    assert "semantically relevant" in source["authority_boundary"]["agent_owned_decisions"][0]
    assert "does not classify user intent" in source["authority_boundary"]["reporting_rule"]
    assert "does not make semantic task classifications" in review["authority_boundary"]["reporting_rule"]


def test_implement_verification_task_marker_reports_configured_protocol_authority(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "verification" / "manifest.toml",
        """
schema_version = "agentic-workspace/verification-manifest/v1"

[scenarios.privacy_walkthrough]
protocol_id = "privacy_review"
title = "Privacy walkthrough"
steps = ["Inspect privacy handling"]
expected_observations = ["Authority and evidence labels are visible"]
pass_evidence_labels = ["privacy_reviewed"]
fail_evidence_labels = ["privacy_gap"]

[protocols.privacy_review]
title = "Privacy review"
purpose = "Configured privacy verification protocol."
applies_to_task_markers = ["privacy"]
scenario_refs = ["privacy_walkthrough"]
expected_evidence = ["privacy_reviewed"]
review_owner = "privacy-review"
authority_refs = ["docs/compliance/privacy.md"]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update privacy handling",
                "--select",
                "verification",
                "--format",
                "json",
            ]
        )
        == 0
    )

    verification = json.loads(capsys.readouterr().out)["values"]["verification"]
    protocol = verification["active_protocols"][0]
    assert protocol["id"] == "privacy_review"
    assert protocol["applies_because"] == ["task marker matched privacy"]
    assert "configured verification protocol privacy_review" in protocol["authority_boundary"]["observed_by_aw"]
    assert "semantically relevant" in protocol["authority_boundary"]["agent_owned_decisions"][0]
    assert "does not classify user intent" in protocol["authority_boundary"]["reporting_rule"]
    assert "does not decide the user's semantic intent" in verification["authority_boundary"]["reporting_rule"]


def test_implement_matches_non_code_assurance_requirement(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.runbook_change]
level = "medium"
applies_to_paths = ["docs/runbooks/**"]
authority_refs = ["docs/ops/runbook-authority.md"]
required_evidence = ["operator_review"]
force = "recommended"
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/runbooks/restart-service.md",
                "--select",
                "assurance_requirements",
                "--format",
                "json",
            ]
        )
        == 0
    )

    requirements = json.loads(capsys.readouterr().out)["values"]["assurance_requirements"]
    assert requirements["active"][0]["id"] == "runbook_change"
    assert requirements["active"][0]["authority_refs"] == ["docs/ops/runbook-authority.md"]
    assert requirements["evidence_status"][0]["missing_evidence"] == ["operator_review"]


def test_implement_planning_source_includes_typecheck_ci_parity(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / "Makefile",
        "test-planning:\n\tpytest packages/planning/tests\n\n"
        "lint-planning:\n\truff check packages/planning\n\n"
        "typecheck-planning:\n\tmypy packages/planning/src\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["proof"]["required_commands"] == [
        "make test-planning",
        "make lint-planning",
        "make typecheck-planning",
    ]
    assert payload["next"]["commands"] == [
        "make test-planning",
        "make lint-planning",
        "make typecheck-planning",
    ]


def test_implement_groups_generated_reuse_pressure_under_source_owner(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "generated" / "workspace" / "python" / "command_package.json", "{}")
    _write(tmp_path / "generated" / "workspace" / "python" / "adapter_commands.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/command_package.json",
                "generated/workspace/python/adapter_commands.json",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    aggregation = payload["generated_artifact_aggregation"]
    assert aggregation["status"] == "present"
    assert aggregation["owner_group_count"] == 1
    finding = aggregation["findings"][0]
    assert finding["kind"] == "generated_artifact_source_owner"
    assert finding["changed_path"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert finding["generated_artifact_count"] == 2
    assert [item["kind"] for item in payload["findings"]] == ["generated_artifact_source_owner"]


def test_implement_compact_reuse_pressure_collapses_large_generated_file_sets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    changed_paths = [f"generated/workspace/typescript/resources/operations/generated-{index}.json" for index in range(12)]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    route_command = reuse_pressure["memory_signals"]["route_command"]
    assert "--target ." in route_command
    assert "<collapsed-changed-paths>" in route_command
    assert changed_paths[-1] not in route_command
    summary = reuse_pressure["memory_signals"]["path_argument_summary"]
    assert summary["status"] == "collapsed"
    assert summary["generated_groups"] == [{"root": "generated/workspace/typescript/resources", "count": 12}]
    assert reuse_pressure["recording_options"]["path_argument_summary"]["status"] == "collapsed"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                *changed_paths,
                "--verbose",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )
    verbose_reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert changed_paths[-1] in verbose_reuse_pressure["memory_signals"]["route_command"]
    assert "<collapsed-changed-paths>" not in verbose_reuse_pressure["memory_signals"]["route_command"]


def test_implement_selector_surfaces_changed_path_impact_map(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "OWNERSHIP.toml",
        "schema_version = 1\n\n"
        "[[authority_surfaces]]\n"
        'concern = "startup-instructions"\n'
        'surface = "AGENTS.md"\n'
        'owner = "repo"\n'
        'ownership = "repo_owned"\n'
        'authority = "primary"\n'
        'summary = "startup"\n\n'
        "[[module_roots]]\n"
        'module = "planning"\n'
        'path = ".agentic-workspace/planning/"\n'
        'ownership = "module_managed"\n'
        'uninstall_policy = "remove-managed-files-only"\n\n'
        "[[subsystems]]\n"
        'id = "workspace-runtime"\n'
        'paths = ["src/agentic_workspace/**"]\n'
        'owns = ["workspace runtime behavior"]\n'
        'does_not_own = ["planning state semantics"]\n'
        'proof = ["uv run pytest tests/test_workspace_implement_cli.py -q"]\n'
        'escalate_when = ["runtime contract changes"]\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "generated/workspace/python/command_package.json",
                ".agentic-workspace/planning/state.toml",
                "scratch/unknown.adapter",
                "--select",
                "change_impact",
                "--format",
                "json",
            ]
        )
        == 0
    )

    impact = json.loads(capsys.readouterr().out)["values"]["change_impact"]
    by_path = {item["path"]: item for item in impact["paths"]}
    source = by_path["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert source["owner"] == "subsystem:workspace-runtime"
    assert source["surface_origin"] == "source-authored"
    assert source["related"]["subsystems"][0]["id"] == "workspace-runtime"
    assert "subsystem:workspace-runtime" in source["related"]["proof_lanes"]

    generated = by_path["generated/workspace/python/command_package.json"]
    assert generated["surface_origin"] == "generated"
    assert generated["signal"] == "hard_blocker"
    assert generated["safe_to_edit"] is False
    assert generated["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert generated["refresh_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert "cli_authority" in generated["related"]["proof_lanes"]

    managed = by_path[".agentic-workspace/planning/state.toml"]
    assert managed["owner"] == "planning"
    assert managed["surface_origin"] == "managed"
    assert managed["matched_by"] == "module_root"
    assert managed["signal"] == "warning"
    assert managed["safe_to_edit"] is True
    assert any("command-owned mutation" in warning for warning in managed["warnings"])

    unknown = by_path["scratch/unknown.adapter"]
    assert unknown["owner"] == "unknown"
    assert unknown["ownership_matched"] is False
    assert unknown["signal"] == "warning"
    assert "No explicit ownership ledger match" in unknown["warnings"][0]

    assert impact["generated_path_count"] == 1
    assert impact["managed_path_count"] == 1
    assert impact["unknown_path_count"] == 1
    assert impact["hard_blocker_count"] == 1
    assert impact["proof_impact"]["required_commands"]


def test_implement_selector_surfaces_generated_surface_trust(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/command_package.json",
                "--select",
                "generated_surface_trust",
                "--format",
                "json",
            ]
        )
        == 0
    )

    trust = json.loads(capsys.readouterr().out)["values"]["generated_surface_trust"]
    assert trust["kind"] == "agentic-workspace/generated-surface-trust/v1"
    assert trust["status"] == "present"
    assert trust["changed_path_count"] == 1
    assert trust["rule"].startswith("Generated surfaces are derived artifacts")
    item = trust["items"][0]
    assert item["path"] == "generated/workspace/python/command_package.json"
    assert item["classification_id"] == "generated-command-package-output"
    assert item["role"] == "projection"
    assert item["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert item["canonical_source_status"] == "present"
    assert item["freshness_status"] == "validation-required"
    assert item["refresh_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert item["validation_command"] == "uv run python scripts/check/check_generated_command_packages.py"
    assert item["direct_edit_allowed"] is False
    assert "Do not hand-edit generated command package outputs" in item["direct_edit_policy"]


def test_implement_readme_change_omits_generated_cli_freshness(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "generated_cli_freshness" not in payload["proof"]
    assert all("generated_cli_freshness" not in signal for signal in payload["action_signals"]["changed_signals"])
    assert payload["context"]["generated_surface_trust"]["status"] == "not-applicable"


def test_implement_selector_surfaces_task_contract_view(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--select",
                "task_contract",
                "--format",
                "json",
            ]
        )
        == 0
    )

    contract = json.loads(capsys.readouterr().out)["values"]["task_contract"]
    assert contract["kind"] == "agentic-workspace/task-contract/v1"
    assert contract["status"] == "present"
    assert contract["authority"] == "assembled-view"
    assert contract["changed_paths"] == ["README.md"]
    assert "task_intent" in contract["source_fields"]
    assert contract["intent"]["status"] == "present"
    assert contract["intent"]["missing_fields"] == []
    assert contract["acceptance"]["closeout_required"] is True
    assert contract["acceptance"]["item_count"] == 3
    assert contract["autonomy_and_escalation"]["recommended_route"] in {
        "execute-locally",
        "stay-local",
        "suggest-delegation",
        "manual-handoff",
        "clarify-first",
    }
    assert contract["proof_expectations"]["status"] == "present"
    assert contract["proof_expectations"]["required_commands"]
    assert contract["proof_expectations"]["intent_proof_status"] in {"prompt-required", "needs-agent-judgment"}
    assert contract["stop_conditions"]["status"] == "present"
    assert "proof.escalate_when" in contract["stop_conditions"]["source_fields"]


def test_implement_task_contract_names_missing_task_inputs(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "README.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--select",
                "task_contract",
                "--format",
                "json",
            ]
        )
        == 0
    )

    contract = json.loads(capsys.readouterr().out)["values"]["task_contract"]
    assert contract["status"] == "present-with-gaps"
    assert contract["intent"]["status"] == "absent"
    assert contract["intent"]["missing_fields"] == ["task_intent.task_text"]
    assert "task_intent.task_text" in contract["missing_fields"]
    assert "acceptance.items" in contract["missing_fields"]
    assert contract["proof_expectations"]["status"] == "present"
    assert contract["changed_paths"] == ["README.md"]


def test_implement_selector_surfaces_routine_work_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.docs_review]
level = "medium"
applies_to_paths = ["docs/**"]
required_evidence = ["reviewed_docs_authority"]
force = "required-before-closeout"
""",
    )
    _write(tmp_path / "docs" / "guide.md", "hello\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "docs/guide.md",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    assert routine["surface"] == "implement"
    assert routine["categories"]["authority"]["signals"]["active_assurance_requirements"] == 1
    assert routine["categories"]["evidence_proof"]["signals"]["missing_required_assurance_evidence"] == 1
    assert routine["activation"]["small_work_rule"].startswith("If no category is attention")


def test_implement_separates_required_proof_from_recommended_confidence_checks(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / "Makefile",
        (
            "test-planning:\n\tpytest packages/planning/tests\n\n"
            "lint-planning:\n\truff check packages/planning\n\n"
            "typecheck-planning:\n\tpyright packages/planning\n\n"
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "packages/planning/src/repo_planning_bootstrap/installer.py",
                "--task",
                "Update planning package installer",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    proof = payload["proof"]
    obligations = proof["proof_obligations"]
    adequacy = proof["proof_adequacy"]
    assert "make test-planning" in proof["required_commands"]
    assert "make lint-planning" in proof["required_commands"]
    assert "make typecheck-planning" in proof["required_commands"]
    assert obligations["required_proof"]["commands"] == proof["required_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] == proof["optional_commands"]
    assert obligations["recommended_confidence_checks"]["commands"] != proof["required_commands"]
    assert obligations["agent_selected_extra_validation"]["status"] == "agent-owned"
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    assert adequacy["protocol"] == "Proof Adequacy"
    assert adequacy["required_evidence"]["commands"] == proof["required_commands"]
    assert "completion permission without closeout" in adequacy["claim_boundary"]["does_not_authorize"]
    assert "semantic intent satisfaction" in adequacy["claim_boundary"]["does_not_authorize"]
    assert payload["required_validation_commands"] == proof["required_commands"]


def test_implement_routine_context_surfaces_memory_freshness_and_promotion_pressure(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write(target / ".agentic-workspace" / "memory" / "repo" / "domains" / "token-policy.md", "# Token policy\n")
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/token-policy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/token-policy.md"
authority = "advisory"
audience = "human+agent"
canonicality = "candidate_for_promotion"
task_relevance = "required"
subsystems = ["auth"]
surfaces = ["token"]
routes_from = ["src/auth/**"]
stale_when = ["src/auth/**"]
evidence = ["docs/security/token-policy.md"]
memory_role = "improvement_signal"
promotion_target = "assurance.requirements.token_policy"
promotion_trigger = "Promote when token handling is next touched."
preferred_remediation = "validation"
improvement_note = "Create a reusable token-policy assurance gate."
elimination_target = "promote"
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(target),
                "--changed",
                "src/auth/token.py",
                "--task",
                "Update token handling",
                "--select",
                "routine_work_context",
                "--format",
                "json",
            ]
        )
        == 0
    )

    routine = json.loads(capsys.readouterr().out)["values"]["routine_work_context"]
    review = routine["knowledge_authority_review"]
    assert review["status"] == "attention"
    assert review["stale_source_count"] == 1
    assert review["promotion_candidate_count"] == 1
    assert routine["categories"]["durable_knowledge"]["status"] == "attention"
    assert routine["categories"]["promotion_residue"]["status"] == "attention"
    source = review["matched_sources"][0]
    assert source["owner_surface"] == ".agentic-workspace/memory/repo/domains/token-policy.md"
    assert source["freshness"]["status"] == "needs-review"
    assert source["promotion_pressure"]["target"] == "assurance.requirements.token_policy"
    assert "route promotion or dismissal during closeout" in source["claim_effect"]["advises"]


def test_implement_tiny_profile_does_not_compute_change_impact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    def fail_change_impact(**_: object) -> dict[str, object]:
        raise AssertionError("ordinary tiny implement output should not build change_impact")

    monkeypatch.setattr(cli, "_change_impact_payload", fail_change_impact)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert "change_impact" not in payload
    assert "change_impact" not in payload["context"]


def test_implement_tiny_profile_does_not_compute_task_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    def fail_task_contract(**_: object) -> dict[str, object]:
        raise AssertionError("ordinary tiny implement output should not build task_contract")

    monkeypatch.setattr(cli, "_task_contract_payload", fail_task_contract)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert "task_contract" not in payload
    assert "task_contract" not in payload["context"]
    assert "task_contract" in payload["drill_down"]["available_selectors"]


def test_implement_tiny_profile_does_not_compute_routine_work_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "README.md", "hello\n")

    def fail_routine_context(**_: object) -> dict[str, object]:
        raise AssertionError("ordinary tiny implement output should not build routine_work_context")

    monkeypatch.setattr(cli, "_routine_work_context_payload", fail_routine_context)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert "routine_work_context" not in payload
    assert "routine_work_context" in payload["drill_down"]["available_selectors"]


def test_implement_tiny_profile_does_not_compute_assurance_requirements(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(
        tmp_path / ".agentic-workspace/config.toml",
        """
schema_version = 1

[assurance.requirements.docs_review]
level = "high"
applies_to_paths = ["docs/**"]
required_evidence = ["review_recorded"]
force = "required-before-closeout"
blocking_claims = ["claim-work-complete"]
""",
    )
    _write(tmp_path / "README.md", "hello\n")

    def fail_assurance_requirements(**_: object) -> dict[str, object]:
        raise AssertionError("ordinary tiny implement output should not build assurance_requirements")

    monkeypatch.setattr(cli, "_assurance_requirements_report_payload", fail_assurance_requirements)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert "assurance_requirements" not in payload
    assert "assurance_requirements" not in payload["context"]
    assert "assurance_requirements" in payload["drill_down"]["available_selectors"]


def test_implement_tiny_profile_returns_next_decision_without_diagnostics(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--task",
                "implement output profile policy",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    encoded = json.dumps(payload)
    assert payload["kind"] == "implementer-context-tiny/v1"
    assert set(payload) <= {
        "kind",
        "target",
        "action_signals",
        "next",
        "proof",
        "generated_surface_trust",
        "reuse_pressure",
        "context",
        "drill_down",
    }
    signals = payload["action_signals"]
    assert signals["kind"] == "agentic-workspace/action-signals/v1"
    assert signals["order"] == [
        "hard_blockers",
        "allowed_next_action",
        "proof_required",
        "changed_signals",
        "advisory_detail",
        "agent_judgment",
    ]
    assert signals["allowed_next_action"] == payload["next"]["action"]
    assert signals["proof_required"] is True
    assert signals["proof_commands"] == payload["proof"]["required_commands"]
    assert "generated_surface_trust=present" in signals["changed_signals"]
    assert "generated_cli_freshness=required" in signals["changed_signals"]
    assert "context.reuse_pressure" in signals["advisory_detail"]["selectors"]
    adaptive = context["adaptive_routing"]
    assert adaptive["current_need"] == "changed-path-next-action"
    assert adaptive["read_budget"]["profile"] == "tiny"
    assert adaptive["detail_commands"]["task_scoped_state"].startswith("agentic-workspace summary --changed")
    assert "raw workspace files" in adaptive["not_needed_now"]
    assert payload["next"]["action"] == "Inspect only the listed files and run the required validation commands."
    assert payload["next"]["command"] == "make test-workspace"
    assert payload["next"]["run"] == payload["next"]["command"]
    assert "make lint-workspace" in payload["next"]["commands"]
    assert context["scope"]["inspect_files"] == ["generated/workspace/python/cli.py"]
    assert "make test-workspace" in payload["proof"]["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in payload["proof"]["required_commands"]
    assert payload["proof"]["generated_cli_freshness"]["status"] == "required"
    assert payload["proof"]["generated_cli_freshness"]["refresh_command"] == "uv run python scripts/generate/generate_command_packages.py"
    assert payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["target_families"] == ["python", "typescript"]
    assert "Python-only proof" in payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["claim_rule"]
    obligations = payload["proof"]["proof_obligations"]
    assert obligations["required_proof"]["commands"] == payload["proof"]["required_commands"]
    assert obligations["recommended_confidence_checks"]["status"] == "available"
    assert "do not replace or relax required proof" in obligations["recommended_confidence_checks"]["rule"]
    assert "Completion claims remain blocked" in obligations["completion_claim_rule"]
    trust = payload["generated_surface_trust"]
    assert trust["status"] == "present"
    assert trust["items"][0]["path"] == "generated/workspace/python/cli.py"
    assert trust["items"][0]["canonical_source"] == "src/agentic_workspace/contracts/command_package_ir.json"
    assert trust["items"][0]["direct_edit_allowed"] is False
    assert context["generated_surface_trust"] == {
        "status": "present",
        "changed_path_count": 1,
        "detail_selector": "generated_surface_trust",
    }
    assert payload["proof"]["acceptance_guidance"]["status"] == "present"
    guidance = context["guidance"]
    assert guidance["rule"].startswith("AW exposes facts")
    assert guidance["work_shape_guidance"]["agent_decision_required"] is True
    guidance_boundary = guidance["work_shape_guidance"]["authority_boundary"]
    assert guidance_boundary["kind"] == "agentic-workspace/authority-boundary/v1"
    assert guidance_boundary["surface"] == "work_shape_guidance"
    assert "semantic work shape" in guidance_boundary["agent_owned_decisions"]
    assert any(item.startswith("dirty_shape=") for item in guidance_boundary["observed_by_aw"])
    assert "intent_acknowledgement" not in context
    intent_evidence = context["intent_evidence"]
    assert intent_evidence["source_class"] == "direct-user-text"
    assert intent_evidence["assumption_state"] == "low-risk-direct"
    assert intent_evidence["required_next_action"] == "continue-direct"
    assert intent_evidence["proceed_without_question"] is True
    assert context["delegation_decision"]["status"] == "evaluated"
    assert context["delegation_decision"]["mode"] in {"suggest", "auto"}
    delegation_boundary = context["delegation_decision"]["authority_boundary"]
    assert delegation_boundary["surface"] == "delegation_decision"
    assert "delegation fit without lowering proof" in delegation_boundary["agent_owned_decisions"]
    assert context["acceptance_reconciliation"]["task_text_available"] is True
    assert context["acceptance"]["status"] == "inferred"
    assert context["acceptance"]["closeout_required"] is True
    assert context["objective_drift"]["status"] in {"clear", "not-enough-explicit-outcomes"}
    assert "package_boundary" not in payload
    assert "authority_markers" not in payload
    assert "durable_intent" not in payload
    assert "inference_limits" not in payload
    assert "generated_surface_trust" in payload["drill_down"]["available_selectors"]
    assert len(json.dumps(payload["generated_surface_trust"])) < 700
    assert len(encoded) < 15500


def test_implement_surfaces_runtime_source_edit_review_for_generated_cli_boundary(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Fix an existing primitive bug under the generated CLI boundary.",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    review = payload["proof"]["runtime_source_edit_review"]
    assert review["kind"] == "agentic-workspace/runtime-source-edit-review/v1"
    assert review["status"] == "classification-required"
    assert review["changed_paths"] == ["src/agentic_workspace/workspace_runtime_primitives.py"]
    assert review["accepted_direct_edit_reasons"] == ["existing-primitive-bugfix", "new-primitive-implementation"]
    assert "package-domain boundary" in review["rejected_vague_reasons"]
    assert "final report states the edit reason" in review["completion_claim_rule"]
    assert "proof.runtime_source_edit_review" in payload["drill_down"]["available_selectors"]


def test_implement_keeps_active_intent_packets_selector_only(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "workspace_runtime_primitives.py", "VALUE = 1\n")

    task = (
        "Previously convert some tests, but now replace most existing tests with contract-owned tests; "
        "do not claim the parent lane complete unless the replacement is representative."
    )
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                task,
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    assert "active_intent_contract" not in context
    assert "intent_satisfaction_matrix" not in context
    assert "active_intent_contract" in payload["drill_down"]["available_selectors"]
    assert "intent_satisfaction_matrix" in payload["drill_down"]["available_selectors"]

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                task,
                "--select",
                "active_intent_contract,intent_satisfaction_matrix",
                "--format",
                "json",
            ]
        )
        == 0
    )
    selected = json.loads(capsys.readouterr().out)
    contract = selected["values"]["active_intent_contract"]
    assert contract["kind"] == "agentic-workspace/active-intent-contract/v1"
    assert contract["status"] == "present"
    assert contract["source_count"] == 1
    assert "supersede" in contract["update_relationship_options"]
    matrix = selected["values"]["intent_satisfaction_matrix"]
    assert matrix["kind"] == "agentic-workspace/intent-satisfaction-matrix/v1"
    assert matrix["status"] == "required-before-completion-claim"
    assert "full-intent-complete" in matrix["claim_levels"]


def test_implement_detail_commands_use_resolved_cli_invoke(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "Makefile", "test-workspace:\n\tpytest tests\n\nlint-workspace:\n\truff check src tests\n")
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        'schema_version = 1\n\n[workspace]\ncli_invoke = "uv run agentic-workspace"\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "README.md",
                "--task",
                "Update README wording",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    detail_commands = payload["drill_down"]["detail_commands"]
    assert detail_commands["full_context"].startswith("uv run agentic-workspace implement ")
    assert detail_commands["proof_detail"].startswith("uv run agentic-workspace proof ")
    assert detail_commands["task_scoped_state"].startswith("uv run agentic-workspace summary ")
    assert detail_commands["takeover_or_recovery"].startswith("uv run agentic-workspace preflight ")
    assert payload["proof"]["detail_command"].startswith("uv run agentic-workspace proof ")
    assert payload["context"]["reuse_pressure"]["status"] == "checked"


def test_implement_accumulates_repeated_changed_flags(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--changed",
                "tests/test_workspace_implement_cli.py",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]
    assert payload["proof"]["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]
    compatibility_review = payload["proof"]["tiny_surface_compatibility_review"]
    assert compatibility_review["status"] == "required"
    assert compatibility_review["changed_paths"] == [
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "tests/test_workspace_implement_cli.py",
    ]
    assert "focused tiny/default payload shape tests" in compatibility_review["expected_proof"]


def test_implement_package_cli_edits_select_generated_command_package_gate(capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--changed",
                "generated/memory/python/cli.py",
                "--task",
                "change package cli runtime adapter",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "make test-memory" in payload["proof"]["required_commands"]
    assert "uv run python scripts/check/check_generated_command_packages.py" in payload["proof"]["required_commands"]
    assert payload["proof"]["generated_cli_freshness"]["generated_target_parity"]["target_families"] == ["python", "typescript"]


def test_implement_uses_available_target_makefile_targets(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Remove `llms.txt`",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["next"]["commands"] == ["make test", "make lint"]
    assert payload["proof"]["required_commands"] == ["make test", "make lint"]
    assert "make test-workspace" not in json.dumps(payload)


def test_cli_invoke_rewrites_package_sibling_commands_when_repo_local() -> None:
    assert (
        cli._command_with_cli_invoke(
            command="agentic-workspace planning handoff --target . --format json",
            cli_invoke="uv run agentic-workspace",
        )
        == "uv run agentic-workspace planning handoff --target . --format json"
    )


def test_implement_task_file_preserves_task_intent_for_acceptance_checks(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "sample_app" / "text.py", "def normalize_cli_text(value):\n    return value.strip()\n")
    task_file = tmp_path / ".agentic-workspace" / "local" / "scratch" / "task-intent.txt"
    _write(task_file, "Implement normalize_whitespace(text) and sentence_summary(text)\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task-file",
                ".agentic-workspace/local/scratch/task-intent.txt",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    context = _implement_context(payload)
    assert context["acceptance"]["items"][0]["id"] == "A1"
    assert "normalize_whitespace" in context["acceptance"]["items"][0]["expectation"]
    assert payload["proof"]["acceptance_guidance"]["acceptance_item_count"] >= 2
    assert context["acceptance_reconciliation"]["task_text_available"] is True
    assert context["acceptance_reconciliation"]["requested_outcomes"] == ["normalize_whitespace", "sentence_summary"]
    assert context["acceptance_reconciliation"]["acceptance_item_count"] >= 2
    assert context["objective_drift"]["missing_from_changed_surface"] == ["normalize_whitespace", "sentence_summary"]
    intent_proof = payload["proof"]["intent_proof"]
    assert intent_proof["status"] == "needs-agent-judgment"
    assert intent_proof["regression_only_risk"] == "possible"
    assert {"normalize_whitespace", "sentence_summary"} <= set(intent_proof["intended_behavior"])


def test_implement_task_text_does_not_route_broad_issue_ingestion_to_planning(tmp_path: Path, capsys) -> None:
    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--task",
                "ingest and implement all open GitHub issues",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "clear"
    assert payload["planning_safety_gate"]["work_shape_guidance"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."
    assert payload["handoff_requirements"]["stop_when"][0] != "task routing status is needs-planning for broad external-work ingestion"


def test_implement_task_allows_narrow_single_issue_context(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)

    assert cli.main(["implement", "--target", str(tmp_path), "--task", "implement issue #424", "--verbose", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["gate_result"] == "external-issue-scope-unknown"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["planning_safety_gate"]["issue_scope_evidence"]["missing_issue_refs"] == ["#424"]
    assert payload["planning_safety_gate"]["work_shape_guidance"]["scope_factors"]["issue_refs"] == ["#424"]
    assert payload["planning_safety_gate"]["work_shape_guidance"]["agent_decision_required"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."


def test_implement_allows_completed_archived_plan_residue_with_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/completed-slice.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "completed-slice",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "yes"},
                "closure_check": {
                    "larger-intent status": "satisfied",
                    "closure decision": "archive-and-close",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert gate["gate_result"] == "direct-work-allowed"
    assert gate["implementation_allowed"] is True
    facts = gate["changed_path_facts"]
    assert facts["dirty_shape"] == "implementation-with-archived-planning-residue"
    assert facts["planning_paths"] == []
    assert facts["archived_planning_residue"]["status"] == "completed-closeout-residue"
    assert facts["archived_planning_residue_paths"] == [archive_path]
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is True
    assert facts["archived_planning_residue"]["records"][0]["status"] == "completed"
    assert gate["work_shape_guidance"]["scope_factors"]["ancillary_paths"] == [archive_path]
    assert any("archived closeout residue" in reason for reason in gate["work_shape_guidance"]["direct_work_is_reasonable_when"])


def test_implement_allows_completed_archived_plan_residue_with_routed_continuation(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/partial-slice.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "partial-slice",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "canonical_core": {"continuation_owner": "GitHub #1278"},
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "owner surface": "GitHub #1278",
                    "activation trigger": "implement the next bounded slice",
                },
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert gate["gate_result"] == "direct-work-allowed"
    facts = gate["changed_path_facts"]
    assert facts["archived_planning_residue"]["status"] == "completed-closeout-residue"
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is True
    assert facts["archived_planning_residue"]["records"][0]["larger_intent_status"] == "open"
    assert facts["archived_planning_residue"]["records"][0]["closure_decision"] == "archive-but-keep-lane-open"


def test_implement_context_surfaces_parent_intent_for_active_slice(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    plan = tmp_path / ".agentic-workspace" / "planning" / "execplans" / "generated-runtime-boundary.plan.json"
    _write(
        plan,
        json.dumps(
            {
                "kind": "planning-execplan/v1",
                "title": "Generated Runtime Boundary",
                "active_milestone": {
                    "id": "generated-runtime-boundary",
                    "status": "active",
                    "scope": "Refresh one generated adapter.",
                },
                "delegated_judgment": {"requested outcome": "Refresh one generated adapter."},
                "parent_acceptance": {
                    "original_intent": "all runtime code should be generated from IR representations as a single source of truth",
                    "parent_acceptance": "runtime behavior cannot be changed outside generated IR or declared primitive implementation boundaries",
                    "current_slice": "generated parser adapter freshness",
                    "residual_parent_intent": "runtime behavior can still be changed outside generated IR/primitive implementation boundaries",
                    "proof_boundary": "slice-only",
                },
                "intent_continuity": {
                    "larger intended outcome": "all runtime code should be generated from IR representations as a single source of truth",
                    "this slice completes the larger intended outcome": "no",
                    "continuation surface": "#1318",
                },
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "owner surface": "#1318",
                },
                "proof_report": {
                    "validation proof": "pending",
                    "intent_proof": {"status": "needs_review", "claim_boundary": "slice"},
                },
            },
            indent=2,
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        "[todo]\n"
        "active_items = [\n"
        "  { id = 'generated-runtime-boundary', title = 'Generated runtime boundary', surface = '.agentic-workspace/planning/execplans/generated-runtime-boundary.plan.json' },\n"
        "]\n"
        "queued_items = []\n\n"
        "[roadmap]\nlanes = []\ncandidates = []\n",
    )
    _write(tmp_path / "generated" / "workspace" / "python" / "parser_adapter.py", "# generated\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/parser_adapter.py",
                "--task",
                "Refresh the generated parser adapter without closing the full runtime-generation boundary.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    parent = payload["parent_intent_status"]
    assert parent["status"] == "open"
    assert parent["original_intent"] == "all runtime code should be generated from IR representations as a single source of truth"
    assert parent["current_slice"] == "generated parser adapter freshness"
    assert parent["proof_is_slice_only"] is True
    assert "runtime behavior can still be changed outside generated IR" in parent["residual_parent_intent"]


def test_implement_preserves_unplanned_parent_intent_for_generated_surface_slice(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json", "{}\n")
    _write(tmp_path / "generated" / "workspace" / "python" / "parser_adapter.py", "# generated\n")
    task = "all runtime code should be generated from IR representations as a single source of truth"

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/parser_adapter.py",
                "--task",
                task,
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    parent = payload["parent_intent_status"]
    assert parent["status"] == "needs-planning"
    assert parent["original_intent"] == task
    assert parent["parent_acceptance_target"] == task
    assert parent["current_slice"] == "changed generated surface(s): generated/workspace/python/parser_adapter.py"
    assert parent["proof_boundary"] == "changed-path/generated-surface proof only"
    assert parent["proof_is_slice_only"] is True
    assert parent["larger_intent_status"] == "not-recorded"
    assert parent["closure_decision"] == "not-recorded"
    assert parent["required_next_action"].startswith("Preserve the raw task")
    assert "generated-surface freshness" in parent["must_not_claim"][0]
    assert parent["source_fields"] == [
        "task_intent.task_excerpt",
        "changed_paths",
        "generated_surface_trust",
        "planning.active.planning_record.parent_acceptance",
    ]
    authority = parent["authority_boundary"]
    assert authority["surface"] == "parent_intent_status"
    assert "active_parent_acceptance=False" in authority["observed_by_aw"]
    assert "semantic work-shape judgment" in parent["rule"]
    assert "does not semantically classify the prompt" in authority["reporting_rule"]
    assert payload["generated_surface_trust"]["status"] == "present"


def test_implement_rejects_archived_plan_residue_with_only_activation_trigger(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/trigger-only.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "trigger-only",
                "machine_readable_contract": {"execution": {"status": "completed"}},
                "required_continuation": {
                    "required follow-on for the larger intended outcome": "yes",
                    "activation trigger": "when the next slice starts",
                },
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "violation"
    facts = gate["changed_path_facts"]
    assert facts["archived_planning_residue"]["status"] == "incomplete-or-stale"
    record = facts["archived_planning_residue"]["records"][0]
    assert record["eligible"] is False
    assert record["closure_decision"] == "archive-but-keep-lane-open"
    assert "closure decision is not archive-and-close or routed continuation" in record["reason"]
    assert "larger intent remains open without routed continuation" in record["reason"]
    assert "intent satisfaction is incomplete" in record["reason"]


def test_implement_allows_closeout_evidence_and_state_cleanup_publication_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    state_path = ".agentic-workspace/planning/state.toml"
    closeout_path = ".agentic-workspace/planning/closeout-evidence/partial-slice.closeout.json"
    _write(
        tmp_path / closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "slice status": "completed",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
                "durable_residue": {"canonical owner now": "GitHub #1278"},
                "execution_summary": {"follow-on routed to": "GitHub #1278"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                closeout_path,
                state_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "clear"
    assert gate["gate_result"] == "direct-work-allowed"
    facts = gate["changed_path_facts"]
    assert facts["planning_paths"] == []
    assert facts["archived_planning_residue"]["status"] == "completed-closeout-residue"
    assert facts["archived_planning_residue_paths"] == [closeout_path]
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is True
    assert set(gate["work_shape_guidance"]["scope_factors"]["ancillary_paths"]) == {closeout_path, state_path}


def test_implement_closeout_publication_residue_suppresses_unrelated_candidate_pressure(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "deferred.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Deferred lane",
                "status": "partially-promoted",
                "lanes": [
                    {
                        "lane_id": "future-lane",
                        "title": "Future lane",
                        "readiness": "deferred",
                        "owner_surface": "later",
                        "proof": "later",
                        "candidate_route": "delegate-exploration",
                    }
                ],
            }
        ),
    )
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    closeout_path = ".agentic-workspace/planning/closeout-evidence/partial-slice.closeout.json"
    _write(
        tmp_path / closeout_path,
        json.dumps(
            {
                "kind": "planning-closeout-evidence/v1",
                "active_milestone": {"status": "completed"},
                "execution_run": {"run status": "completed"},
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "closeout scope": "slice",
                    "slice status": "completed",
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
                "durable_residue": {"canonical owner now": "GitHub #1278"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                closeout_path,
                "--task",
                "Implement issue #1278",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] in {"clear", "attention"}
    assert gate["gate_result"] != "candidate-lane-promotion-required"
    assert gate["implementation_allowed"] is True
    assert gate["changed_path_facts"]["archived_planning_residue"]["status"] == "completed-closeout-residue"


def test_implement_keeps_planning_gate_for_unfinished_archived_plan_residue(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_empty_planning_state(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    archive_path = ".agentic-workspace/planning/execplans/archive/open-slice.plan.json"
    _write(
        tmp_path / archive_path,
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "open-slice",
                "status": "completed",
                "intent_satisfaction": {"was original intent fully satisfied?": "no"},
                "closure_check": {
                    "larger-intent status": "open",
                    "closure decision": "archive-but-keep-lane-open",
                },
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                archive_path,
                "--task",
                "Publish the completed slice.",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["planning_safety_gate"]
    assert gate["status"] == "violation"
    assert gate["gate_result"] == "implementation-owner-missing"
    assert gate["implementation_allowed"] is False
    facts = gate["changed_path_facts"]
    assert facts["dirty_shape"] == "planning-plus-implementation"
    assert facts["archived_planning_residue"]["status"] == "incomplete-or-stale"
    assert facts["archived_planning_residue"]["records"][0]["eligible"] is False


def test_implement_blocks_epic_work_with_multiple_roadmap_candidates(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = []
queued_items = []

[roadmap]
lanes = []
candidates = [
  { id = "github-1201-command-package", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1201", title = "Command package extraction", outcome = "Extract the command package.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape a bounded lane." },
  { id = "github-1202-runtime-parity", maturity = "candidate", status = "next", priority = "P1", refs = "GitHub #1202", title = "Runtime parity", outcome = "Prove generated runtime parity.", reason = "Open issue.", promotion_signal = "Promote before implementation.", suggested_first_slice = "Shape a bounded lane." },
]
""",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/workspace_runtime_primitives.py",
                "--task",
                "Implement the command generation extraction epic",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "candidate-lane-promotion-required"
    assert gate["implementation_allowed"] is False
    assert gate["candidate_pressure"]["candidate_ids"] == [
        "github-1201-command-package",
        "github-1202-runtime-parity",
    ]
    assert payload["context"]["workflow_sufficiency"]["sufficiency_result"] == "candidate-lane-promotion-required"


def test_implement_blocks_parent_lane_slice_without_lane_owner_artifact(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "agentic_workspace" / "runtime.py", "VALUE = 1\n")
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "slice-one", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/slice-one.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "slice-one.plan.json",
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "slice-one",
                "status": "active",
                "parent_lane": {"id": "parent-lane", "label": "Parent lane"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--task",
                "Continue the active planning work",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "lane-owner-artifact-required"
    assert gate["implementation_allowed"] is False
    owner = gate["hierarchy_owner_requirement"]
    assert owner["status"] == "missing-lane-owner-artifact"
    assert owner["lane_id"] == "parent-lane"
    assert ".agentic-workspace/planning/lanes/parent-lane.lane.json" in owner["required_before_implementation"][0]
    assert "planning lane-create --id parent-lane --target ." in owner["command"]


def test_implement_blocks_active_parent_lane_slice_with_invalid_lane_owner_artifact(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write_planning_lane_schema(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "slice-one", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/slice-one.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write_json(
        tmp_path / ".agentic-workspace" / "planning" / "lanes" / "parent-lane.lane.json",
        {
            "kind": "planning-lane/v1",
            "id": "parent-lane",
            "title": "Malformed parent lane",
            "status": "active",
            "parent_close_permission": "not-allowed",
        },
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "execplans" / "slice-one.plan.json",
        json.dumps(
            {
                "schema_version": "execplan/v1",
                "id": "slice-one",
                "status": "active",
                "parent_lane": {"id": "parent-lane", "label": "Parent lane"},
            }
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/runtime.py",
                "--task",
                "Continue the active planning work",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    gate = payload["context"]["planning_safety_gate"]
    assert gate["status"] == "blocked"
    assert gate["gate_result"] == "lane-owner-artifact-required"
    assert gate["implementation_allowed"] is False
    owner = gate["hierarchy_owner_requirement"]
    assert owner["status"] == "missing-or-invalid-lane-owner-artifact"
    assert owner["lane_id"] == "parent-lane"
    assert owner["invalid_lane_record"] == ".agentic-workspace/planning/lanes/parent-lane.lane.json"
    assert owner["validation_errors"]
    assert any("parent_close_permission" in error for error in owner["validation_errors"])
    assert "planning lane-create --id parent-lane --target ." in owner["command"]


def test_implement_with_explicit_target_ignores_checkout_active_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    active_checkout = tmp_path / "active-checkout"
    isolated_target = tmp_path / "isolated-target"
    active_checkout.mkdir()
    isolated_target.mkdir()
    _init_git_repo(active_checkout)
    _init_git_repo(isolated_target)
    _write_empty_planning_state(isolated_target)
    _write(
        active_checkout / ".agentic-workspace/planning/state.toml",
        """
kind = "agentic-planning-state"
schema_version = "planning-state/v1"

[todo]
active_items = [
  { id = "live-plan", status = "active", maturity = "active", surface = ".agentic-workspace/planning/execplans/live-plan.plan.json" }
]
queued_items = []

[roadmap]
lanes = []
candidates = []
""",
    )
    _write(
        active_checkout / ".agentic-workspace/planning/execplans/live-plan.plan.json",
        '{"schema_version":"execplan/v1","id":"live-plan","status":"active"}\n',
    )
    monkeypatch.chdir(active_checkout)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(isolated_target),
                "--task",
                "implement issue #424",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert "task_routing" not in payload
    assert payload["planning_safety_gate"]["status"] == "attention"
    assert payload["planning_safety_gate"]["gate_result"] == "external-issue-scope-unknown"
    assert payload["planning_safety_gate"]["implementation_allowed"] is True
    assert payload["next_allowed_action"] == "Provide --changed paths or use start/preflight before broad implementation."


def test_implement_task_specific_acceptance_warns_on_objective_drift(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(tmp_path / "src" / "sample_app" / "text.py", "def normalize_cli_text(value):\n    return value.strip()\n")

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement normalize_whitespace(text) and sentence_summary(text)",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    acceptance = payload["acceptance_reconciliation"]
    assert acceptance["task_text_available"] is True
    assert acceptance["requested_outcomes"] == ["normalize_whitespace", "sentence_summary"]
    assert acceptance["acceptance_items"][0]["status"] == "unchecked"
    assert "acceptance/requested" in acceptance["compact_closeout_prompt"]
    drift = payload["objective_drift"]
    assert drift["status"] == "warning"
    assert drift["missing_from_changed_surface"] == ["normalize_whitespace", "sentence_summary"]
    assert drift["acceptance_item_count"] >= 2
    assert "self-authored tests alone" in acceptance["compact_closeout_prompt"]


def test_implement_objective_drift_does_not_accept_deleted_outcome_from_prompt_keywords(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Remove `llms.txt` and replace it with install docs",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    drift = _implement_context(payload)["objective_drift"]
    assert drift["status"] == "warning"
    assert drift["requested_outcomes"] == ["llms.txt"]
    assert drift["removed_or_retired_outcomes"] == []
    assert drift["missing_from_changed_surface"] == ["llms.txt"]
    assert "does not infer removal or retirement intent from prompt keywords" in drift["heuristic"]
    assert "whether a missing requested outcome was intentionally removed" in drift["agent_owned_decisions"][0]


def test_implement_objective_drift_keeps_missing_path_without_removal_intent(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "llms.txt",
                "--task",
                "Document `llms.txt` behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    drift = _implement_context(payload)["objective_drift"]
    assert drift["status"] == "warning"
    assert drift["removed_or_retired_outcomes"] == []
    assert drift["missing_from_changed_surface"] == ["llms.txt"]


def test_implement_command_surfaces_reasoning_heavy_execution_posture(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[runtime]",
                "strong_planner_available = true",
                "cheap_bounded_executor_available = true",
                "",
                "[delegation]",
                'mode = "manual"',
                "",
                "[delegation_targets.planner]",
                'strength = "strong"',
                'location = "local"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy"]',
                'execution_methods = ["internal"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/agentic_workspace/contracts/schemas/workspace_local_override.schema.json",
                "--task",
                "update delegation config schema",
                "--verbose",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    posture = payload["execution_posture"]
    assert posture["capability_posture"]["posture"]["execution class"] == "boundary-shaping"
    assert posture["capability_posture"]["scope_evidence"]["scope_signal"] == "bounded"
    assert posture["capability_posture"]["scope_evidence"]["agent_decision_required"] is True
    assert posture["capability_posture"]["proof_factors"]["proof_pressure"] == "high"
    assert "schema" in posture["capability_posture"]["risk_flags"]
    assert "proof route" in posture["capability_posture"]["inspection_evidence_required"]
    assert posture["capability_posture"]["self_assessment_authority"] == "advisory-only"
    assert posture["runtime_resolution"]["recommendation"] == "stronger-reasoning"
    assert posture["runtime_resolution"]["self_assessment"]["authority"] == "advisory-only"
    assert posture["delegation_control"]["effective_mode"] == "manual"
    assert posture["delegation_control"]["execution_permitted"] is False
    assert posture["selected_target"]["name"] == "planner"
    assert posture["capability_handoff_packets"]["packet_types"]["manual_human_clarification"]
    assert posture["ready_handoff"]["kind"] == "agentic-workspace/capability-handoff-packet/v1"
    assert posture["ready_handoff"]["mode"] == "manual"
    assert posture["ready_handoff"]["packet_type"] == "manual_human_clarification"
    assert "quality" in posture["ready_handoff"]["prompt"]
    assert posture["delegation_decision"]["recommended_route"] == "suggest-escalation"
    assert posture["delegation_decision"]["required_next_action"] == "prepare-handoff"
    assert posture["delegation_decision"]["route_obligation"]["must"].startswith("Prepare the handoff packet")
    assert "report why" in posture["delegation_decision"]["route_obligation"]["report_if_skipped"]
    assert posture["delegation_decision"]["config_effect"]["source_path"] == ".agentic-workspace/config.local.toml"
    assert posture["delegation_decision"]["config_effect"]["delegation_mode"] == "manual"
    assert posture["delegation_decision"]["config_effect"]["execution_authority"] == "suggest-or-handoff-only"
    assert posture["delegation_decision"]["handoff_command"] == "agentic-workspace planning handoff --target . --format json"
    assert posture["delegation_decision"]["handoff_surface"]["required_packet_fields"] == [
        "intent",
        "constraints",
        "read_first_refs",
        "owned_scope",
        "proof_expectations",
        "stop_conditions",
        "return_contract",
        "target_posture",
    ]
    assert "active execplan" in posture["delegation_decision"]["handoff_surface"]["fallback_when_unavailable"]
    assert payload["delegation_decision"] == posture["delegation_decision"]
    assert "work_shape_hint" not in json.dumps(posture["delegation_decision"])
    assert "quality_factors" not in posture["delegation_decision"]
    assert posture["delegation_decision"]["route_evidence"]["scope_signal"] == "bounded"
    assert "semantic task classification" in posture["delegation_decision"]["route_evidence"]["rule"]


def test_implement_auto_delegation_exposes_bounded_slice_handoff(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[runtime]",
                "supports_internal_delegation = true",
                "cheap_bounded_executor_available = true",
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.mini]",
                'strength = "medium"',
                'location = "local"',
                "confidence = 0.8",
                'task_fit = ["bounded implementation", "validation"]',
                'capability_classes = ["mixed", "mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement bounded text helper behavior",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["recommended_route"] == "delegate-bounded-slice"
    assert decision["target"] == "mini"
    assert decision["required_next_action"] == "execute-when-safe"
    assert decision["token_savings_guidance"]["signal"] == "likely"
    assert decision["route_evidence"]["scope_signal"] == "bounded"
    assert decision["route_evidence"]["agent_judgment_required"] is True
    effort = decision["effort_guidance"]
    assert effort["cost_posture"] == "save-tokens-where-safe"
    assert effort["orchestrator"] == "medium"
    assert effort["implementer"] == "medium delegate"
    assert decision["route_obligation"]["must"].startswith("Execute only when local auto mode")
    assert decision["config_effect"]["authority"] == "local-config"
    assert decision["config_effect"]["execution_authority"] == "auto-execution-permitted"
    assert decision["handoff_command"] == "agentic-workspace planning handoff --target . --format json"
    assert decision["delegation_next_step"]["status"] == "executable"
    assert decision["delegation_next_step"]["must_report_if_not_run"] is True
    assert decision["delegation_next_step"]["execution_methods"] == ["cli"]
    assert "bounded work" in decision["reason"]


def test_implement_epic_decomposition_prefers_reusable_worker_over_manual_relay(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )
    _write(
        tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "codegen.decomposition.json",
        json.dumps(
            {
                "kind": "planning-decomposition/v1",
                "title": "Codegen epic",
                "status": "shaping",
                "larger_intended_outcome": "Use decomposed artifacts to finish an epic cheaply.",
                "non_goals": [],
                "candidate_lanes": [
                    {
                        "id": "black-box-harness",
                        "title": "Black-box harness",
                        "readiness": "needs-shaping",
                        "outcome": "Choose the next bounded conformance slice.",
                        "owner_surface": "",
                        "proof": "Report likely changed files and validation.",
                        "depends_on": [],
                        "parallel_with": [],
                    }
                ],
                "dependency_assumptions": [],
                "parallelization_assumptions": [],
                "proof_expectations": ["Focused proof remains unchanged."],
                "promotion_rule": "Promote only bounded slices.",
                "references": [],
                "notes": "",
            },
            indent=2,
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "generated/workspace/python/cli.py",
                "--task",
                "Continue the codegen epic and evaluate reusable-worker delegation",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["recommended_route"] == "suggest-delegation"
    assert decision["target"] == "reusable-worker"
    assert decision["required_next_action"] == "select-or-promote-bounded-lane"
    assert decision["token_savings_guidance"]["signal"] == "possible"
    assert decision["config_effect"]["execution_authority"] == "auto-execution-permitted"
    assert "handoff_command" not in decision
    assert decision["delegation_next_step"]["status"] == "prepare-or-report"
    assert decision["delegation_next_step"]["action"] == "select-or-promote-bounded-lane"
    assert decision["delegation_next_step"]["command"] is None
    assert decision["delegation_next_step"]["execution_methods"] == ["internal", "cli"]
    assert decision["delegation_next_step"]["must_report_if_not_run"] is False
    assert decision["delegation_next_step"]["handoff_contract_status"] == "unavailable-without-active-planning"
    assert "proof run and result" in decision["delegation_next_step"]["return_contract"]
    assert decision["decomposition_delegation"]["status"] == "available-without-active-planning"
    assert decision["delegation_candidates"][0]["candidate_route"] == "delegate-exploration"
    assert "reuse an existing worker" in decision["reason"]
    assert "auto_delegation_audit" not in decision


def test_implement_suppresses_manual_external_relay_for_code_local_changed_paths(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.chatgpt]",
                'strength = "strong"',
                'location = "external"',
                'capability_classes = ["boundary-shaping", "reasoning-heavy", "mixed"]',
                'execution_methods = ["manual"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/package/feature.py",
                "--task",
                "Implement schema and CLI behavior for the feature",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    decision = _implement_context(payload)["delegation_decision"]
    assert decision["recommended_route"] == "stay-local"
    assert decision["required_next_action"] == "continue-local"
    assert decision["effort_guidance"]["orchestrator"] == "medium"
    assert decision["effort_guidance"]["implementer"] == "medium"
    assert decision["effort_guidance"]["validator"] == "high"
    assert decision["effort_guidance"]["cost_posture"] == "quality-first"
    assert "target" not in decision["effort_guidance"]
    assert "manual_external_relay" not in decision
    assert "config_effect" not in decision
    assert "manual_prompt" not in decision
    assert "handoff_command" not in decision


def test_implement_supports_selector_drilldown(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "config.local.toml",
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[delegation]",
                'mode = "auto"',
                "",
                "[safety]",
                "safe_to_auto_run_commands = true",
                "",
                "[delegation_targets.mini]",
                'strength = "medium"',
                'location = "local"',
                'task_fit = ["bounded implementation"]',
                'capability_classes = ["mechanical-follow-through"]',
                'execution_methods = ["cli"]',
            ]
        ),
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Implement bounded text helper behavior",
                "--select",
                "context.delegation_decision.required_next_action,context.delegation_decision.delegation_next_step.must_report_if_not_run,context.delegation_decision.effort_guidance.cost_posture",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert "missing" not in payload
    assert "available_selectors" not in payload
    assert payload["values"]["context.delegation_decision.required_next_action"] == "execute-when-safe"
    assert payload["values"]["context.delegation_decision.delegation_next_step.must_report_if_not_run"] is True
    assert payload["values"]["context.delegation_decision.effort_guidance.cost_posture"] == "save-tokens-where-safe"


def test_implement_selector_surfaces_reuse_pressure_without_blocking_direct_work(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "helpers.py",
        "def normalize_text(value):\n    return value.strip()\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--task",
                "Add a text normalization helper",
                "--select",
                "reuse_pressure,context.workflow_sufficiency",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "existing_helper_candidate"
    assert reuse_pressure["findings"][0]["symbol"] == "normalize_text"
    assert reuse_pressure["findings"][0]["candidate_paths"] == ["src/sample_app/helpers.py"]
    assert "accept-duplication-with-reason" in reuse_pressure["allowed_outcomes"]
    assert payload["values"]["context.workflow_sufficiency"]["sufficiency_result"] == "enough-for-bounded-implementation"


def test_implement_reuse_pressure_ignores_dependency_cache_definitions(tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / "packages" / "planning" / ".uv-cache" / "archive-v0" / "dependency" / "text.py",
        "def normalize_text(value):\n    return value\n",
    )
    _write(
        tmp_path / ".venv" / "Lib" / "site-packages" / "dependency" / "text.py",
        "def normalize_text(value):\n    return value\n",
    )

    original_is_file = Path.is_file

    def fail_if_dependency_tree_is_inspected(path: Path) -> bool:
        relative_parts = path.relative_to(tmp_path).parts if path.is_relative_to(tmp_path) else path.parts
        assert ".venv" not in relative_parts
        assert ".uv-cache" not in relative_parts
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_if_dependency_tree_is_inspected)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []


def test_implement_reuse_pressure_honors_gitignore_for_ordinary_scan(tmp_path: Path, capsys) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _write(tmp_path / ".gitignore", "src/sample_app/ignored_helper.py\n")
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "ignored_helper.py",
        "def normalize_text(value):\n    return value\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []
    assert reuse_pressure["weak_hints"] == []


def test_implement_reuse_pressure_skips_workspace_local_scratch(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )
    _write(
        tmp_path / ".agentic-workspace" / "local" / "scratch" / "external-repo" / "helpers.py",
        "def normalize_text(value):\n    return value\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []


def test_implement_reuse_pressure_surfaces_repeated_special_case(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "legacy_a.py",
        'def route_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )
    _write(
        tmp_path / "src" / "sample_app" / "legacy_b.py",
        'def display_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )
    _write(
        tmp_path / "src" / "sample_app" / "legacy_c.py",
        'def save_mode(mode):\n    if mode == "legacy":\n        return "old"\n    return "new"\n',
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/legacy_c.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "similar_pattern_candidate"
    finding = next(item for item in reuse_pressure["findings"] if item["kind"] == "repeated_special_case")
    assert finding["evidence_confidence"] == "medium"
    assert finding["kind"] == "repeated_special_case"
    assert finding["candidate_paths"] == ["src/sample_app/legacy_a.py", "src/sample_app/legacy_b.py"]


def test_implement_reuse_pressure_exposes_recording_and_routing_options(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "helpers.py",
        "def normalize_text(value):\n    return value.strip()\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["record-duplication-accepted"]["resulting_state"] == "duplication_accepted_with_reason"
    assert "reason" in options["record-duplication-accepted"]["requires"]
    assert options["route-extraction-follow-up"]["resulting_state"] == "extraction_deferred_with_owner"
    assert "owner" in options["route-extraction-follow-up"]["requires"]
    recording_options = reuse_pressure["recording_options"]
    assert any("memory capture-note" in command for command in recording_options["accept_duplication"]["commands"])
    assert any("planning new-plan" in command for command in recording_options["route_extraction"]["commands"])
    assert any("memory capture-note" in command for command in recording_options["route_extraction"]["commands"])


def test_implement_reuse_pressure_surfaces_memory_boundary_notes(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/decisions/helper-boundaries.md"]
note_type = "decision"
surfaces = ["abstraction", "reuse"]
routes_from = ["src/sample_app/*.py"]
""",
    )
    _write(
        tmp_path / "src" / "sample_app" / "text.py",
        "def normalize_text(value):\n    return ' '.join(value.split())\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["memory_signals"]["status"] == "matched"
    assert reuse_pressure["memory_signals"]["matches"][0]["path"] == ".agentic-workspace/memory/repo/decisions/helper-boundaries.md"
    assert "memory route" in reuse_pressure["memory_signals"]["route_command"]
    assert "--target ." in reuse_pressure["memory_signals"]["route_command"]


def test_implement_reuse_pressure_keeps_small_direct_task_unblocked(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "single.py",
        "def parse_one(value):\n    return int(value)\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/single.py",
                "--select",
                "reuse_pressure,context.workflow_sufficiency",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    reuse_pressure = payload["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["findings"] == []
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["continue-direct"]["allowed"] is True
    assert options["route-extraction-follow-up"]["allowed"] is False
    assert payload["values"]["context.workflow_sufficiency"]["sufficiency_result"] == "enough-for-bounded-implementation"


def test_implement_reuse_pressure_demotes_generic_sibling_helpers_to_weak_hints(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "alpha.py",
        "def build_invoice(total):\n    return total\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "beta.py",
        "def render_dashboard(rows):\n    return rows\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/alpha.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "none_found"
    assert reuse_pressure["finding_count"] == 0
    assert reuse_pressure["weak_hint_count"] == 1
    assert reuse_pressure["weak_hints"][0]["kind"] == "sibling_helper_hint"
    options = {option["id"]: option for option in reuse_pressure["next_decision_options"]}
    assert options["route-extraction-follow-up"]["allowed"] is False


def test_implement_reuse_pressure_promotes_token_matched_sibling_helper(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    _write(
        tmp_path / "src" / "sample_app" / "invoice_format.py",
        "def invoice_currency(total):\n    return f'${total}'\n",
    )
    _write(
        tmp_path / "src" / "sample_app" / "invoice_parse.py",
        "def parse_invoice_total(raw):\n    return int(raw)\n",
    )

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/invoice_format.py",
                "--select",
                "reuse_pressure",
                "--format",
                "json",
            ]
        )
        == 0
    )

    reuse_pressure = json.loads(capsys.readouterr().out)["values"]["reuse_pressure"]
    assert reuse_pressure["state"] == "similar_pattern_candidate"
    assert reuse_pressure["findings"][0]["kind"] == "sibling_helper_hint"
    assert "invoice" in reuse_pressure["findings"][0]["matched_tokens"]
    assert reuse_pressure["weak_hint_count"] == 0


def test_implement_selector_reports_available_fields_for_missing_selector(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)

    assert (
        cli.main(
            [
                "implement",
                "--target",
                str(tmp_path),
                "--changed",
                "src/sample_app/text.py",
                "--select",
                "does_not_exist",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["missing"] == ["does_not_exist"]
    assert "context.delegation_decision" in payload["available_selectors"]
    assert "next" in payload["available_selectors"]
    assert "context.scope" in payload["available_selectors"]
    assert "proof" in payload["available_selectors"]
    assert "reuse_pressure" in payload["available_selectors"]
