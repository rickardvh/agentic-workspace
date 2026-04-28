from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_structured_file_inventory.py"
_SPEC = importlib.util.spec_from_file_location("check_structured_file_inventory", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_structured_file_inventory = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check_structured_file_inventory
_SPEC.loader.exec_module(check_structured_file_inventory)


def test_inventory_shape_is_valid() -> None:
    inventory = check_structured_file_inventory.load_inventory()

    assert check_structured_file_inventory.validate_inventory_shape(inventory) == []


def test_current_tracked_structured_files_are_classified() -> None:
    assert check_structured_file_inventory.inventory_findings() == []


def test_unmatched_structured_file_fails() -> None:
    inventory = check_structured_file_inventory.load_inventory()

    findings = check_structured_file_inventory.unmatched_structured_files(["docs/new-machine-state.json"], inventory)

    assert len(findings) == 1
    assert findings[0].path == "docs/new-machine-state.json"
    assert "not classified" in findings[0].message


def test_unstructured_files_are_ignored() -> None:
    inventory = check_structured_file_inventory.load_inventory()

    findings = check_structured_file_inventory.unmatched_structured_files(["docs/note.md"], inventory)

    assert findings == []


def test_inventory_routes_known_schema_gaps() -> None:
    inventory = check_structured_file_inventory.load_inventory()
    gap_entries = [entry for entry in inventory["entries"] if entry["status"] == "freeform-prohibited-gap"]

    assert {entry["routed_to"] for entry in gap_entries} >= {"#504", "#505", "#508", "#509"}
    assert all(entry["generated"] is False for entry in gap_entries)


def test_inventory_routes_reconstructable_storage_cleanup_children() -> None:
    inventory = check_structured_file_inventory.load_inventory()

    assert check_structured_file_inventory.routed_storage_cleanup_issues(inventory) >= {"#538", "#539", "#540"}


def test_generated_adapter_requires_regeneration_source() -> None:
    inventory = {
        "entries": [
            {
                "pattern": "tools/agent-manifest.json",
                "format": "json",
                "owner": "planning-payload",
                "status": "generated-derived",
                "schema_or_validator": "planning payload render/check surfaces",
                "storage_class": "generated-required-adapter",
                "checked_in_justification": "compatibility",
                "editable_by_agents": False,
                "generated": True,
                "notes": "Generated manifest.",
            }
        ]
    }

    findings = check_structured_file_inventory.storage_policy_findings(["tools/agent-manifest.json"], inventory)

    assert len(findings) == 1
    assert "reconstructable_from" in findings[0].message


def test_reconstructable_snapshot_requires_size_or_count_guardrail() -> None:
    inventory = {
        "entries": [
            {
                "pattern": ".agentic-workspace/planning/external-intent-evidence.json",
                "format": "json",
                "owner": "planning-evidence",
                "status": "freeform-prohibited-gap",
                "schema_or_validator": "external intent evidence schema pending",
                "storage_class": "reconstructable-external-snapshot",
                "checked_in_justification": "temporary snapshot",
                "reconstructable_from": ["provider query"],
                "editable_by_agents": True,
                "generated": False,
                "routed_to": "#506",
                "storage_routed_to": "#536",
                "notes": "External evidence.",
            }
        ]
    }

    findings = check_structured_file_inventory.storage_policy_findings(
        [".agentic-workspace/planning/external-intent-evidence.json"],
        inventory,
    )

    assert len(findings) == 1
    assert "max_items or max_bytes" in findings[0].message


def test_storage_guardrail_reports_matching_file_size_breach() -> None:
    inventory = {
        "entries": [
            {
                "pattern": "pyproject.toml",
                "format": "toml",
                "owner": "planning-review",
                "status": "typed-validator-backed",
                "schema_or_validator": "test validator",
                "storage_class": "historical-audit-distillation",
                "checked_in_justification": "test guardrail",
                "editable_by_agents": True,
                "generated": False,
                "storage_routed_to": "#538",
                "guardrails": {"max_bytes": 1, "routed_to": "#538"},
                "notes": "Artificial guardrail entry.",
            }
        ]
    }

    findings = check_structured_file_inventory.storage_policy_findings(["pyproject.toml"], inventory)

    assert len(findings) == 1
    assert "max_bytes=1" in findings[0].message
