from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import date
from pathlib import Path

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

    policy = json.loads((ROOT / "src/agentic_workspace/contracts/runtime_implementation_ownership.json").read_text(encoding="utf-8"))
    decompositions = policy["review_scale"]["representative_decompositions"]
    by_symbol = {item["symbol"]: item for item in decompositions}
    assert by_symbol["_report_closeout_trust_payload"]["after"]["lines"] < by_symbol["_report_closeout_trust_payload"]["before"]["lines"]
    assert (
        by_symbol["archive_execplan"]["after"]["largest_policy_effect_segment_lines"]
        < by_symbol["archive_execplan"]["before"]["largest_policy_effect_segment_lines"]
    )
    assert {item["continuation_owner"] for item in decompositions} == {"#2480"}


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
    policy["review_scale"]["exception_lifecycle"]["removal_owner"] = "#2455"
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")

    report = _checker().ownership_report(root)

    assert report["status"] == "blocked"
    assert any("durable post-#2455 removal owner" in item["detail"] for item in report["findings"])
