from __future__ import annotations

import importlib.util
import inspect
import json
import shutil
from datetime import date
from pathlib import Path

from repo_planning_bootstrap import installer

from agentic_workspace import workspace_runtime_core

ROOT = Path(__file__).resolve().parents[1]


def _checker():
    path = ROOT / "scripts/check/check_runtime_implementation_ownership.py"
    spec = importlib.util.spec_from_file_location("runtime_ownership_checker", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path: Path) -> Path:
    for relative in (
        "src/agentic_workspace/workspace_runtime_core.py",
        "src/agentic_workspace/workspace_runtime_primitives.py",
        "src/agentic_workspace/contracts/runtime_implementation_ownership.json",
        "packages/planning/src/repo_planning_bootstrap/installer.py",
        "tests/test_workspace_cli.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def test_current_runtime_has_one_implementation_owner() -> None:
    report = _checker().ownership_report(ROOT)

    assert report["status"] == "ready"
    assert report["metrics"]["before"]["ast_identical_shared_bodies"] == 967
    assert report["metrics"]["after"]["shared_top_level_definitions"] == 0
    assert report["metrics"]["after"]["primitive_module_lines"] <= 80
    working_set = report["metrics"]["representative_working_set"]
    assert working_set["after"]["runtime_owner_files"] < working_set["before"]["runtime_owner_files"]
    assert working_set["after"]["shared_symbols"] < working_set["before"]["shared_symbols"]
    assert working_set["after"]["largest_audited_segment_lines"] <= 320
    extraction = report["metrics"]["candidate_extraction"]
    assert extraction["before"]["authority_owner_files"] == 2
    assert extraction["after"] == {
        "authority_owner_files": 1,
        "facade_imported_owner_symbols": 7,
        "facade_alternate_assembler_symbols": 0,
    }
    assert extraction["alternate_assembler_symbols"] == []

    policy = json.loads((ROOT / "src/agentic_workspace/contracts/runtime_implementation_ownership.json").read_text(encoding="utf-8"))
    decompositions = policy["review_scale"]["representative_decompositions"]
    by_symbol = {item["symbol"]: item for item in decompositions}
    assert by_symbol["_report_closeout_trust_payload"]["after"]["lines"] < by_symbol["_report_closeout_trust_payload"]["before"]["lines"]
    assert (
        by_symbol["archive_execplan"]["after"]["largest_policy_effect_segment_lines"]
        < by_symbol["archive_execplan"]["before"]["largest_policy_effect_segment_lines"]
    )
    assert by_symbol["closeout_execplan"]["after"]["lines"] < by_symbol["closeout_execplan"]["before"]["lines"]
    assert by_symbol["closeout_execplan"]["after"]["branch_nodes"] < by_symbol["closeout_execplan"]["before"]["branch_nodes"]
    assert {item["continuation_owner"] for item in decompositions} == {"runtime-implementation-ownership-contract"}
    assert [item["rank"] for item in policy["review_scale"]["candidate_inventory"]] == [1, 2, 3]
    assert policy["review_scale"]["candidate_inventory"][0]["canonical_owner"] == "src/agentic_workspace/operating_decision.py"
    assert {item["path"] for item in report["metrics"]["file_ratchets"]} == {
        "src/agentic_workspace/workspace_runtime_core.py",
        "packages/planning/src/repo_planning_bootstrap/installer.py",
        "tests/test_workspace_cli.py",
    }

    removed_exception_symbols = {
        "_applicable_intent_source_projection_payload",
        "_record_proof_receipt_payload",
        "_planning_reconciliation_transaction",
        "_intent_validation_contract",
        "_apply_pending_integration_proposals",
        "apply_integration_proposal",
        "targeted_execplan_write",
    }
    assert removed_exception_symbols.isdisjoint({item["symbol"] for item in policy["review_scale"]["exceptions"]})

    for symbol in removed_exception_symbols:
        owner = workspace_runtime_core if hasattr(workspace_runtime_core, symbol) else installer
        lines, _start = inspect.getsourcelines(getattr(owner, symbol))
        assert len(lines) <= policy["review_scale"]["default_max_function_lines"], symbol


def test_facade_definition_is_rejected(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    facade = root / "src/agentic_workspace/workspace_runtime_primitives.py"
    facade.write_text(facade.read_text(encoding="utf-8") + "\ndef copied_behavior():\n    return True\n", encoding="utf-8")

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    assert any(item["control"] == "compatibility-facade" for item in report["findings"])


def test_review_scale_exception_is_a_non_growth_ratchet(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    policy_path = root / "src/agentic_workspace/contracts/runtime_implementation_ownership.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    exception = next(item for item in policy["review_scale"]["exceptions"] if item["symbol"] == "_report_closeout_trust_payload")
    exception["max_lines"] -= 1
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    assert any("grew beyond its ratchet" in item["detail"] for item in report["findings"])


def test_review_scale_exceptions_expire(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    report = _checker().ownership_report(root, today=date(2027, 1, 1))

    assert report["status"] == "blocked"
    assert any("exception expired" in item["detail"] for item in report["findings"])


def test_review_scale_exceptions_require_durable_continuation_owner(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    policy_path = root / "src/agentic_workspace/contracts/runtime_implementation_ownership.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["review_scale"]["exception_lifecycle"]["removal_owner"] = ""
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    assert any("durable post-#2455 removal owner" in item["detail"] for item in report["findings"])


def test_hotspot_file_ratchets_reject_line_symbol_and_fan_out_growth(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    policy_path = root / "src/agentic_workspace/contracts/runtime_implementation_ownership.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    ratchet = next(item for item in policy["review_scale"]["file_ratchets"] if item["path"] == "tests/test_workspace_cli.py")
    ratchet["max_lines"] -= 1
    ratchet["max_top_level_symbols"] -= 1
    ratchet["max_direct_policy_fan_out"] -= 1
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    details = {item["detail"] for item in report["findings"] if item["control"] == "file-ratchet"}
    assert any("lines grew" in detail for detail in details)
    assert any("top_level_symbols grew" in detail for detail in details)
    assert any("direct_policy_fan_out grew" in detail for detail in details)


def test_extracted_authority_cannot_regrow_an_alternate_facade_assembler(tmp_path: Path) -> None:
    root = _fixture(tmp_path)
    facade = root / "src/agentic_workspace/workspace_runtime_core.py"
    facade.write_text(
        facade.read_text(encoding="utf-8")
        + "\ndef alternate_decision_assembler():\n"
        + "    return {'decision_id': 'alternate', 'projection_input_revision': 'alternate'}\n",
        encoding="utf-8",
    )

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    assert any(
        item["control"] == "candidate-extraction-proof" and "alternate_decision_assembler" in item["detail"] for item in report["findings"]
    )
