"""Measure the ordinary module-extension route without requiring a live model provider."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.module_contract import discover_module_contracts, invoke_module_operation

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = REPO_ROOT / "tools/model-cli-harness/external-agent-evaluation/module-extension-scenario-matrix.json"
RESULT_PATH = REPO_ROOT / "tools/model-cli-harness/external-agent-evaluation/module-extension-scenario-measurements.json"
FIXTURE_PATH = REPO_ROOT / "tests/fixtures/external_signals_module/src/external_signals/__init__.py"


class _EntryPoint:
    module = "external_signals"
    attr = "provider"

    def __init__(self, name: str, provider: Any) -> None:
        self.name = name
        self._provider = provider

    def load(self) -> Any:
        return self._provider


def _fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("aw_external_signals_measurement_fixture", FIXTURE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module fixture: {FIXTURE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _provider_with(*, provider: Any, name: str | None = None, read_only: bool = False) -> dict[str, Any]:
    payload = copy.deepcopy(provider())
    contract = payload["contract"]
    if name:
        contract["name"] = name
        for fact in contract.get("facts", []):
            fact["source"]["owner"] = name
        if name == "planning-scenario":
            contract["relevance"]["task_terms"] = ["current execution plan"]
    if read_only:
        contract["capabilities"]["operations"] = []
        contract["compatibility"]["required_capabilities"] = ["module-facts-v1", "module-resources-v1"]
        payload["operations"] = {}
    return payload


def _entry_points_for(scenario: dict[str, Any], fixture: Any) -> tuple[list[_EntryPoint], bool]:
    state_class = scenario["state_class"]
    if state_class == "base":
        return [], False
    if state_class == "first-party":

        def provider() -> dict[str, Any]:
            return _provider_with(provider=fixture.provider, name="planning-scenario")

        return [_EntryPoint("planning-scenario", provider)], False
    if state_class == "partial-capability":

        def provider() -> dict[str, Any]:
            return _provider_with(provider=fixture.provider, name="external-signals-read-only", read_only=True)

        return [_EntryPoint("external-signals-read-only", provider)], False
    if state_class == "conflicting":
        return [
            _EntryPoint("external-signals", fixture.provider),
            _EntryPoint("external-signals-conflict", fixture.conflicting_provider),
        ], False
    if state_class == "incompatible":
        return [_EntryPoint("external-signals-future", fixture.future_provider)], False
    if state_class == "removed":
        return [_EntryPoint("external-signals", fixture.provider)], True
    return [_EntryPoint("external-signals", fixture.provider)], False


def _canonical_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _measure_scenario(*, scenario: dict[str, Any], fixture: Any, repo_root: Path) -> dict[str, Any]:
    entry_points, remove_after_discovery = _entry_points_for(scenario, fixture)
    discovered = discover_module_contracts(entry_points=entry_points)
    trace: list[dict[str, Any]] = [{"event": "discover", "observed": [item.status for item in discovered]}]
    residue: list[str] = []
    descriptors = {item.name: runtime._external_module_descriptor(item) for item in discovered}
    selected = list(descriptors)

    if remove_after_discovery:
        discovered = discover_module_contracts(entry_points=[])
        descriptors = {}
        selected = []
        residue.append("explicit-missing-owner-disposition")
        trace.append({"event": "restart-after-removal", "observed": "no-discovered-module"})

    try:
        runtime._validate_selected_module_contract(selected_modules=selected, descriptors=descriptors)
    except runtime.ModuleSelectionError as exc:
        residue.append("kernel-owned-conflict" if scenario["state_class"] == "conflicting" else "kernel-owned-incompatibility")
        trace.append({"event": "selection-rejected", "observed": type(exc).__name__})
        descriptors = {}
        selected = []

    config = replace(runtime._load_workspace_config(target_root=repo_root), enabled_modules=tuple(selected))
    with patch.object(runtime, "_module_operations", return_value=descriptors):
        packet = runtime._task_posture_packet_payload(
            config=config,
            surface="startup",
            task_text=scenario["ordinary_prompt"],
            changed_paths=[],
            compact=True,
        )
    contributions = packet["module_contributions"]
    trace.append({"event": "start-task-posture", "observed": len(contributions), "class": "aw-command"})

    if contributions and "refresh" in scenario["ordinary_prompt"].lower():
        selected_module = next(item for item in discovered if item.name == contributions[0]["module"])
        operation_id = contributions[0]["operations"][0]["id"]
        result = invoke_module_operation(selected_module, operation_id=operation_id, arguments={"revision": "measured"})
        trace.append({"event": "invoke-module-operation", "observed": result["result"]["status"], "class": "aw-command"})

    first_line = {
        "kind": "agentic-workspace/module-extension-first-line/v1",
        "scenario": scenario["id"],
        "module_contributions": contributions,
        "recovery": residue,
    }
    output = _canonical_bytes(first_line)
    metrics = {
        "aw_command_count": sum(item.get("class") == "aw-command" for item in trace),
        "first_line_context_units": len(contributions),
        "first_line_output_bytes": len(output),
        "raw_workspace_or_module_reads": sum(item.get("class") == "raw-read" for item in trace),
        "route_reversals": sum(item.get("event") == "route-reversal" for item in trace),
        "wrong_owner_actions": sum(item.get("event") == "wrong-owner-action" for item in trace),
        "proof_or_claim_errors": sum(item.get("event") == "proof-or-claim-error" for item in trace),
        "residue_items": len(residue),
        "requests_to_completion": 1,
    }
    return {
        "id": scenario["id"],
        "state_class": scenario["state_class"],
        "metrics": metrics,
        "trace": trace,
        "first_line_sha256": hashlib.sha256(output).hexdigest(),
    }


def collect_measurements(*, matrix: dict[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    results = [_measure_scenario(scenario=scenario, fixture=_fixture_module(), repo_root=repo_root) for scenario in matrix["scenarios"]]
    return {
        "kind": "agentic-workspace/module-extension-scenario-measurements/v1",
        "matrix_kind": matrix["kind"],
        "matrix_version": matrix["version"],
        "producer": "scripts/model_cli_harness/module_extension_scenarios.py",
        "provider_mode": "deterministic-ordinary-route",
        "live_provider_status": matrix["selective_live_evidence"]["status"],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    measured = collect_measurements(matrix=matrix)
    if args.check:
        expected = json.loads(args.check.read_text(encoding="utf-8"))
        if measured != expected:
            raise SystemExit(f"{args.check} is stale; rerun the module-extension scenario measurement collector")
    print(json.dumps(measured, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
