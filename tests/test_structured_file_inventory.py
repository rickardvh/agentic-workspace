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

    assert {entry["routed_to"] for entry in gap_entries} >= {"#504", "#505", "#506", "#508", "#509"}
    assert all(entry["generated"] is False for entry in gap_entries)
