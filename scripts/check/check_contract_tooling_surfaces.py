from __future__ import annotations

import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

from agentic_workspace import cli
from agentic_workspace.contract_tooling import (
    compact_contract_manifest,
    contract_inventory_manifest,
    contract_schema,
    proof_routes_manifest,
    report_contract_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _validator(schema_name: str) -> Draft202012Validator:
    schema = contract_schema(schema_name)
    return Draft202012Validator(schema)


def _validate(instance: object, schema_name: str) -> list[str]:
    validator = _validator(schema_name)
    return [error.message for error in validator.iter_errors(instance)]


def _sample_compact_answer() -> dict[str, object]:
    return cli._compact_contract_answer(  # type: ignore[attr-defined]
        surface="defaults",
        selector={"section": "proof_selection"},
        answer={"id": "workspace_proof"},
        refs=[".agentic-workspace/docs/compact-contract-profile.md", "agentic-workspace defaults --format json"],
    )


def _sample_report_payload() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "repo"
        target.mkdir()
        (target / ".git").mkdir(exist_ok=True)
        descriptors = cli._module_operations()  # type: ignore[attr-defined]
        config = cli._load_workspace_config(target_root=target, descriptors=descriptors)  # type: ignore[attr-defined]
        selected_modules, resolved_preset = cli._selected_modules(  # type: ignore[attr-defined]
            command_name="report",
            preset_name=None,
            module_arg=None,
            target_root=target,
            descriptors=descriptors,
            config=config,
        )
        return cli._run_report_command(  # type: ignore[attr-defined]
            target_root=target,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )


def _sample_workspace_config_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "workspace": {
            "default_preset": "full",
            "agent_instructions_file": "AGENTS.md",
            "workflow_artifact_profile": "repo-owned",
            "improvement_latitude": "balanced",
            "optimization_bias": "agent-efficiency",
        },
        "update": {
            "modules": {
                "planning": {
                    "source_type": "git",
                    "source_ref": "git+https://example.invalid/planning",
                    "source_label": "planning source",
                    "recommended_upgrade_after_days": 30,
                },
                "memory": {
                    "source_type": "local",
                    "source_ref": "../packages/memory",
                    "source_label": "local memory source",
                    "recommended_upgrade_after_days": 7,
                },
            }
        },
        "workflow_obligations": {
            "adapter_surface_refresh": {
                "summary": "Refresh adapter surfaces when structured routing changes.",
                "stage": "before-claiming-completion",
                "scope_tags": ["workspace", "adapter-surfaces"],
                "commands": ["make maintainer-surfaces"],
                "review_hint": "Use when startup routing, llms, or generated agent docs changed.",
            }
        },
    }


def _sample_workspace_local_override_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "runtime": {
            "supports_internal_delegation": True,
            "strong_planner_available": True,
            "cheap_bounded_executor_available": True,
        },
        "handoff": {
            "prefer_internal_delegation_when_available": False,
        },
        "safety": {
            "safe_to_auto_run_commands": False,
            "requires_human_verification_on_pr": True,
        },
        "delegation_targets": {
            "mini_impl": {
                "strength": "weak",
                "confidence": 0.62,
                "task_fit": ["bounded-docs", "narrow-tests"],
                "execution_methods": ["cli"],
            }
        },
    }


def _sample_delegation_outcomes_payload() -> dict[str, object]:
    return {
        "kind": "agentic-workspace/delegation-outcomes/v1",
        "records": [
            {
                "recorded_at": "2026-04-17",
                "delegation_target": "mini_impl",
                "task_class": "bounded-docs",
                "outcome": "success",
                "handoff_sufficiency": "sufficient",
                "review_burden": "light",
                "escalation_required": False,
            }
        ],
    }


def _sample_setup_findings_payload() -> dict[str, object]:
    return {
        "kind": "workspace-setup-findings/v1",
        "findings": [
            {
                "class": "repo_friction_evidence",
                "summary": "Large shared workspace CLI surface is still a hotspot.",
                "confidence": 0.91,
                "path": "src/agentic_workspace/cli.py",
                "refs": [".agentic-workspace/docs/reporting-contract.md"],
                "why": "Would reduce rediscovery during later repo work.",
            },
            {
                "class": "planning_candidate",
                "summary": "One module-reporting follow-on still needs promotion.",
                "confidence": 0.82,
                "next_action": "Promote the next bounded reporting slice into TODO.md when current setup work finishes.",
            },
        ],
    }


def main() -> int:
    checks: list[tuple[str, list[str]]] = [
        ("compact_contract_profile.json", _validate(compact_contract_manifest(), "selector_contracts_manifest.schema.json")),
        ("proof_routes.json", _validate(proof_routes_manifest(), "proof_routes_manifest.schema.json")),
        ("report_contract.json", _validate(report_contract_manifest(), "report_contract_manifest.schema.json")),
        ("contract_inventory.json", _validate(contract_inventory_manifest(), "contract_inventory.schema.json")),
        ("compact answer sample", _validate(_sample_compact_answer(), "compact_contract_answer.schema.json")),
        ("workspace report sample", _validate(_sample_report_payload(), "workspace_report.schema.json")),
        ("workspace config sample", _validate(_sample_workspace_config_payload(), "workspace_config.schema.json")),
        (
            "workspace local override sample",
            _validate(_sample_workspace_local_override_payload(), "workspace_local_override.schema.json"),
        ),
        (
            "delegation outcomes sample",
            _validate(_sample_delegation_outcomes_payload(), "delegation_outcomes.schema.json"),
        ),
        (
            "setup findings sample",
            _validate(_sample_setup_findings_payload(), "setup_findings.schema.json"),
        ),
    ]

    defaults_payload = cli._defaults_payload()  # type: ignore[attr-defined]
    if defaults_payload["compact_contract_profile"]["answer_shape"] != compact_contract_manifest()["answer_shape"]:
        checks.append(("defaults compact profile parity", ["defaults payload answer_shape drifted from compact_contract_profile.json"]))
    if defaults_payload["proof_surfaces"]["default_routes"] != proof_routes_manifest()["default_routes"]:
        checks.append(("proof routes parity", ["defaults payload proof routes drifted from proof_routes.json"]))
    if cli._reporting_schema_payload() != report_contract_manifest():  # type: ignore[attr-defined]
        checks.append(("report contract parity", ["reporting schema payload drifted from report_contract.json"]))
    workspace_config_schema = contract_schema("workspace_config.schema.json")
    local_override_schema = contract_schema("workspace_local_override.schema.json")
    if workspace_config_schema["properties"]["workspace"]["properties"]["agent_instructions_file"]["enum"] != list(
        cli.SUPPORTED_AGENT_INSTRUCTIONS_FILES
    ):
        checks.append(("workspace config schema parity", ["agent_instructions_file enum drifted from cli supported files"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["workflow_artifact_profile"]["enum"] != list(
        cli.SUPPORTED_WORKFLOW_ARTIFACT_PROFILES
    ):
        checks.append(("workspace config schema parity", ["workflow_artifact_profile enum drifted from cli supported profiles"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["improvement_latitude"]["enum"] != list(
        cli.SUPPORTED_IMPROVEMENT_LATITUDES
    ):
        checks.append(("workspace config schema parity", ["improvement_latitude enum drifted from cli supported modes"]))
    if workspace_config_schema["properties"]["workspace"]["properties"]["optimization_bias"]["enum"] != list(
        cli.SUPPORTED_OPTIMIZATION_BIASES
    ):
        checks.append(("workspace config schema parity", ["optimization_bias enum drifted from cli supported modes"]))
    workflow_obligation_schema = workspace_config_schema["$defs"][
        workspace_config_schema["properties"]["workflow_obligations"]["patternProperties"]["^.+$"]["$ref"].split("/")[-1]
    ]
    if workflow_obligation_schema["properties"]["stage"]["enum"] != list(cli.SUPPORTED_WORKFLOW_OBLIGATION_STAGES):
        checks.append(("workspace config schema parity", ["workflow obligation stages drifted from cli supported values"]))
    local_runtime_properties = local_override_schema["properties"]["runtime"]["properties"]
    expected_runtime = {
        "supports_internal_delegation",
        "strong_planner_available",
        "cheap_bounded_executor_available",
    }
    if set(local_runtime_properties) != expected_runtime:
        checks.append(("workspace local override schema parity", ["runtime properties drifted from supported local override fields"]))
    if set(local_override_schema["properties"]["handoff"]["properties"]) != {"prefer_internal_delegation_when_available"}:
        checks.append(("workspace local override schema parity", ["handoff properties drifted from supported local override fields"]))
    if set(local_override_schema["properties"]["safety"]["properties"]) != {
        "safe_to_auto_run_commands",
        "requires_human_verification_on_pr",
    }:
        checks.append(("workspace local override schema parity", ["safety properties drifted from supported local override fields"]))
    delegation_target_schema = local_override_schema["properties"]["delegation_targets"]["patternProperties"]["^.+$"]
    if delegation_target_schema["properties"]["strength"]["enum"] != list(cli.SUPPORTED_DELEGATION_TARGET_STRENGTHS):
        checks.append(
            ("workspace local override schema parity", ["delegation target strengths drifted from supported local override fields"])
        )
    if delegation_target_schema["properties"]["execution_methods"]["items"]["enum"] != list(
        cli.SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS
    ):
        checks.append(
            ("workspace local override schema parity", ["delegation target execution methods drifted from supported local override fields"])
        )
    delegation_outcome_schema = contract_schema("delegation_outcomes.schema.json")
    record_schema = delegation_outcome_schema["properties"]["records"]["items"]
    if record_schema["properties"]["outcome"]["enum"] != list(cli.SUPPORTED_DELEGATION_OUTCOMES):
        checks.append(("delegation outcomes schema parity", ["delegation outcome enums drifted from cli supported values"]))
    if record_schema["properties"]["handoff_sufficiency"]["enum"] != list(cli.SUPPORTED_HANDOFF_SUFFICIENCY):
        checks.append(("delegation outcomes schema parity", ["handoff sufficiency enums drifted from cli supported values"]))
    if record_schema["properties"]["review_burden"]["enum"] != list(cli.SUPPORTED_REVIEW_BURDENS):
        checks.append(("delegation outcomes schema parity", ["review burden enums drifted from cli supported values"]))
    setup_findings_schema = contract_schema("setup_findings.schema.json")
    if setup_findings_schema["properties"]["kind"]["const"] != cli.SETUP_FINDINGS_KIND:
        checks.append(("setup findings schema parity", ["setup findings kind drifted from cli supported value"]))
    finding_schema = setup_findings_schema["properties"]["findings"]["items"]
    if finding_schema["properties"]["class"]["enum"] != list(cli.SUPPORTED_SETUP_FINDING_CLASSES):
        checks.append(("setup findings schema parity", ["setup findings classes drifted from cli supported values"]))

    failures = [(name, errors) for name, errors in checks if errors]
    if failures:
        print("Contract tooling health report")
        for name, errors in failures:
            for error in errors:
                print(f"- [{name}] {error}")
        return 1
    print("Contract tooling health report")
    print("- No contract-tooling drift warnings detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
