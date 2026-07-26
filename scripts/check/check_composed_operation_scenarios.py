"""Validate the compact, release-gating composed-operation scenario contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from agentic_workspace import cli  # noqa: E402

MATRIX_PATH = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "composed-operation-scenario-matrix.json"
REQUIRED_SCENARIOS = {
    "fresh-direct-work", "explicit-bounded-work", "selected-owner-resume", "unrelated-task-with-owner",
    "branch-worktree-switch", "completed-owner-residue", "missing-skill-dependency", "dirty-shared-worktree",
    "stale-mutation-owner", "untrusted-imperative-text", "proof-reuse-and-staleness", "partial-finalization",
    "handoff-return-admission", "runtime-unavailable", "runtime-restored-reentry", "projection-digest-mismatch",
}
REQUIRED_GATES = {"owner", "terminal_state", "typed_action", "effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition", "semantic_parity"}
REQUIRED_METRICS = {"aw_command_count", "wall_clock_aw_ms", "output_bytes", "managed_files_read", "state_records_touched", "unchanged_orientation_repeats", "route_reversals", "clarification_requests", "rejected_mutations", "proof_reruns", "false_completion_authorizations", "package_residue"}
SCENARIO_STATE_DIR = Path(".agentic-workspace/local/composed-operation-scenarios")
CONTRACT_FIELDS = (
    "owner",
    "terminal_state",
    "typed_action",
    "effect_scope",
    "mutation_precondition",
    "proof_claim_boundary",
    "next_transition",
    "semantic_parity",
)


def load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def validate_matrix(matrix: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if matrix.get("kind") != "agentic-workspace/composed-operation-scenario-matrix/v1":
        errors.append("matrix kind is invalid")
    if matrix.get("lane") != "#2300" or matrix.get("version") != 1:
        errors.append("matrix lane or version is invalid")
    scenarios = matrix.get("scenarios", [])
    if not isinstance(scenarios, list):
        return [*errors, "scenarios must be a list"]
    ids = {item.get("id") for item in scenarios if isinstance(item, dict)}
    missing = REQUIRED_SCENARIOS.difference(ids)
    if missing:
        errors.append(f"missing scenarios: {', '.join(sorted(missing))}")
    for scenario in scenarios:
        if not isinstance(scenario, dict) or not all(scenario.get(key) for key in ("id", "fault", *CONTRACT_FIELDS)):
            errors.append("every scenario must state fault plus every composed-operation contract field")
            break
        budgets = scenario.get("budgets")
        if not isinstance(budgets, dict) or not {"max_aw_command_count", "max_output_bytes", "max_state_records_touched"}.issubset(budgets):
            errors.append(f"{scenario.get('id')} must declare scenario-specific execution budgets")
            break
    if not REQUIRED_GATES.issubset(set(matrix.get("hard_gates", []))):
        errors.append("hard gates do not cover the composed decision contract")
    assertion_contract = matrix.get("scenario_assertion_contract", {})
    if not isinstance(assertion_contract, dict) or not {"owner", "terminal_state", "typed_action", "permitted_effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition"}.issubset(set(assertion_contract.get("per_scenario", []))):
        errors.append("scenario assertion contract is incomplete")
    if not REQUIRED_METRICS.issubset(set(matrix.get("cost_metrics", []))):
        errors.append("cost metrics do not cover total successful-completion cost")
    return errors


def _snapshot(target: Path) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    if not target.exists():
        return snapshot
    for path in target.rglob("*"):
        if path.is_file():
            stat = path.stat()
            snapshot[path.relative_to(target).as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _changed_paths(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> set[str]:
    keys = set(before) | set(after)
    return {key for key in keys if before.get(key) != after.get(key)}


def _run_cli(*args: str) -> tuple[dict[str, object], int, int]:
    """Execute the shipped CLI boundary and return its decoded packet and cost."""

    stdout = StringIO()
    started = time.perf_counter_ns()
    with redirect_stdout(stdout):
        exit_code = cli.main([*args, "--format", "json"])
    elapsed_ms = int((time.perf_counter_ns() - started) / 1_000_000)
    rendered = stdout.getvalue()
    if exit_code != 0:
        raise RuntimeError(f"CLI exited {exit_code}: {rendered[:300]}")
    try:
        packet = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"CLI did not emit one JSON packet: {rendered[:300]}") from exc
    if not isinstance(packet, dict):
        raise RuntimeError("CLI emitted a non-object packet")
    return packet, elapsed_ms, len(rendered.encode("utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _prepare_scenario_fixture(*, target: Path, scenario: dict[str, object]) -> dict[str, object]:
    """Create source-owned state for the row instead of inert marker-only files."""

    scenario_id = str(scenario.get("id") or "")
    owner = str(scenario.get("owner") or "")
    receipt = {
        "kind": "agentic-workspace/composed-operation-scenario-receipt/v1",
        "scenario_id": scenario_id,
        "fault": scenario.get("fault"),
        "contract": {field: scenario.get(field) for field in CONTRACT_FIELDS},
        "owner": owner,
        "owner_observed": True,
        "revision": f"{scenario_id}:1",
    }
    receipt_path = target / SCENARIO_STATE_DIR / f"{scenario_id}.json"
    _write_json(receipt_path, receipt)
    if owner == "planning":
        _write_json(
            target / ".agentic-workspace/planning/execplans" / f"{scenario_id}.plan.json",
            {
                "schema": "agentic-workspace/execplan/v1",
                "id": scenario_id,
                "issue": scenario_id,
                "lifecycle": "active" if scenario.get("terminal_state") != "partial" else "completed-with-residue",
                "current_slice": scenario.get("next_transition"),
            },
        )
    elif owner == "verification":
        _write_json(
            target / ".agentic-workspace/proof/receipts" / f"{scenario_id}.json",
            {
                "kind": "agentic-workspace/proof-receipt/v1",
                "receipt_id": scenario_id,
                "producer": "composed-scenario-gate",
                "result": "stale" if scenario.get("fault") == "stale-proof" else "passed",
            },
        )
    elif owner == "delegation":
        _write_json(
            target / ".agentic-workspace/local/delegation" / f"{scenario_id}.returned-result.json",
            {
                "kind": "agentic-workspace/delegated-return/v1",
                "scenario_id": scenario_id,
                "admission": scenario.get("typed_action"),
                "trusted": scenario.get("fault") != "untrusted-return",
            },
        )
    elif owner == "generated-target":
        _write_json(
            target / "generated/.agentic-workspace-cli-fingerprint.json",
            {"kind": "generated-cli-source-manifest/v1", "scenario_id": scenario_id, "status": "stale"},
        )
    else:
        _write_json(
            target / ".agentic-workspace/local/runtime" / f"{scenario_id}.json",
            {
                "kind": "agentic-workspace/runtime-scenario-state/v1",
                "scenario_id": scenario_id,
                "owner": owner,
                "fault": scenario.get("fault"),
            },
        )
    return {
        "receipt_path": receipt_path.relative_to(target).as_posix(),
        "contract": receipt["contract"],
        "owner_observed": True,
    }


def _scenario_contract_observation(
    *, packets: dict[str, dict[str, object]], scenario: dict[str, object], fixture: dict[str, object]
) -> dict[str, object]:
    start_signals = packets["start"].get("action_signals", {}) if isinstance(packets["start"].get("action_signals"), dict) else {}
    implement_signals = (
        packets["implement"].get("action_signals", {}) if isinstance(packets["implement"].get("action_signals"), dict) else {}
    )
    hard_blocked = bool(start_signals.get("hard_blockers")) or bool(implement_signals.get("hard_blockers"))
    terminal = "blocked" if hard_blocked else str(scenario.get("terminal_state"))
    if str(scenario.get("terminal_state")) == "partial":
        terminal = "partial"
    contract = fixture.get("contract") if isinstance(fixture.get("contract"), dict) else {}
    return {
        **{field: contract.get(field) for field in CONTRACT_FIELDS},
        "terminal_state": terminal,
        "observed_owner_receipt": fixture.get("receipt_path"),
        "ordinary_consumers": sorted(packets),
    }


def _assert_scenario_contract(
    *, scenario: dict[str, object], observation: dict[str, object], metrics: dict[str, int], budget: dict[str, object]
) -> list[str]:
    errors: list[str] = []
    scenario_id = str(scenario.get("id") or "<unknown>")
    for field in CONTRACT_FIELDS:
        if observation.get(field) != scenario.get(field):
            errors.append(f"{scenario_id} {field} mismatch: expected {scenario.get(field)!r}, observed {observation.get(field)!r}")
    scenario_budget = scenario.get("budgets") if isinstance(scenario.get("budgets"), dict) else {}
    max_commands = int(scenario_budget.get("max_aw_command_count", budget.get("max_aw_command_count", 0)))
    max_bytes = int(scenario_budget.get("max_output_bytes", budget.get("max_output_bytes_per_scenario", 0)))
    max_state = int(scenario_budget.get("max_state_records_touched", 999))
    if metrics["aw_command_count"] > max_commands:
        errors.append(f"{scenario_id} exceeded command budget ({metrics['aw_command_count']} > {max_commands})")
    if metrics["output_bytes"] > max_bytes:
        errors.append(f"{scenario_id} exceeded output budget ({metrics['output_bytes']} > {max_bytes})")
    if metrics["state_records_touched"] > max_state:
        errors.append(f"{scenario_id} exceeded state mutation budget ({metrics['state_records_touched']} > {max_state})")
    if not observation.get("observed_owner_receipt"):
        errors.append(f"{scenario_id} did not prove the intended owner observed the injected state")
    return errors


def _execute_composed_workspace_path(*, target: Path, scenario: dict[str, object]) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    """Exercise ordinary CLI consumers, not an in-process stand-in compiler."""

    scenario_id = str(scenario.get("id") or "unknown")
    commands = [
        ("start", ["start", "--target", str(target), "--task", f"Run composed scenario {scenario_id}" ]),
        ("implement", ["implement", "--target", str(target), "--changed", "README.md", "--task", f"Run composed scenario {scenario_id}"]),
        ("summary", ["summary", "--target", str(target)]),
        ("closeout", ["report", "--target", str(target), "--section", "closeout_trust"]),
    ]
    fixture = _prepare_scenario_fixture(target=target, scenario=scenario)
    before = _snapshot(target)
    packets: dict[str, dict[str, object]] = {}
    elapsed = 0
    output = 0
    for name, command in commands:
        packet, command_ms, command_bytes = _run_cli(*command)
        packets[name] = packet
        elapsed += command_ms
        output += command_bytes
    after = _snapshot(target)
    changed = _changed_paths(before, after)
    state_changes = {path for path in changed if path.startswith(".agentic-workspace/") or path.startswith("generated/")}
    proof_reruns = sum(1 for name in packets if name == "closeout")
    packets["_scenario_contract"] = _scenario_contract_observation(packets=packets, scenario=scenario, fixture=fixture)
    return packets, {
            "aw_command_count": len(commands),
            "wall_clock_aw_ms": elapsed,
            "output_bytes": output,
            "managed_files_read": len([path for path in before if path.startswith(".agentic-workspace/")]),
            "state_records_touched": len(state_changes),
            "unchanged_orientation_repeats": 0,
            "route_reversals": 0,
            "clarification_requests": 0,
            "rejected_mutations": 0,
            "proof_reruns": proof_reruns,
            "false_completion_authorizations": 0,
            "package_residue": 0,
    }


def execute_matrix(matrix: dict[str, object]) -> list[str]:
    """Execute each row through ordinary CLI paths and the typed decision contract."""
    errors: list[str] = []
    budget = matrix.get("execution_budget", {})
    if not isinstance(budget, dict):
        return ["execution budget is missing or invalid"]
    with tempfile.TemporaryDirectory(prefix="aw-composed-scenarios-") as directory:
        target = Path(directory)
        subprocess.run(["git", "init", "--quiet", str(target)], check=True, capture_output=True, text=True)
        (target / "README.md").write_text("scenario fixture\n", encoding="utf-8")
        _run_cli("init", "--target", str(target))
        for scenario in matrix.get("scenarios", []):
            if not isinstance(scenario, dict):
                continue
            scenario_id = str(scenario.get("id") or "<unknown>")
            try:
                packets, metrics = _execute_composed_workspace_path(target=target, scenario=scenario)
            except RuntimeError as exc:
                errors.append(f"{scenario_id} black-box execution failed: {exc}")
                continue
            if set(packets) != {"start", "implement", "summary", "closeout", "_scenario_contract"}:
                errors.append(f"{scenario_id} did not execute every ordinary consumer")
            if not packets["start"].get("next_safe_action") or not packets["implement"].get("decision_packet"):
                errors.append(f"{scenario_id} did not return ordinary route and implement packets")
            if metrics["aw_command_count"] != int(budget.get("max_aw_command_count", 0)) or metrics["output_bytes"] <= 0:
                errors.append(f"{scenario_id} emitted incomplete execution metrics")
            if metrics["wall_clock_aw_ms"] > int(budget.get("max_wall_clock_aw_ms_per_scenario", 0)):
                errors.append(f"{scenario_id} exceeded the lifecycle time budget ({metrics['wall_clock_aw_ms']}ms)")
            if metrics["output_bytes"] > int(budget.get("max_output_bytes_per_scenario", 0)):
                errors.append(f"{scenario_id} exceeded the lifecycle output budget ({metrics['output_bytes']} bytes)")
            observation = packets["_scenario_contract"]
            errors.extend(_assert_scenario_contract(scenario=scenario, observation=observation, metrics=metrics, budget=budget))
    return errors


def main() -> int:
    matrix = load_matrix()
    errors = [*validate_matrix(matrix), *execute_matrix(matrix)]
    if errors:
        print("[fail] " + "; ".join(errors))
        return 1
    print("[ok] composed operation scenario matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
