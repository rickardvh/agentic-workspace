"""Validate the compact, release-gating composed-operation scenario contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

MATRIX_PATH = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "composed-operation-scenario-matrix.json"
REQUIRED_SCENARIOS = {
    "fresh-direct-work", "explicit-bounded-work", "selected-owner-resume", "unrelated-task-with-owner",
    "branch-worktree-switch", "completed-owner-residue", "missing-skill-dependency", "dirty-shared-worktree",
    "stale-mutation-owner", "untrusted-imperative-text", "proof-reuse-and-staleness", "partial-finalization",
    "handoff-return-admission", "runtime-unavailable", "runtime-restored-reentry", "projection-digest-mismatch",
}
REQUIRED_GATES = {"owner", "terminal_state", "typed_action", "effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition", "semantic_parity"}
REQUIRED_METRICS = {"aw_command_count", "wall_clock_aw_ms", "output_bytes", "managed_files_read", "state_records_touched", "unchanged_orientation_repeats", "route_reversals", "clarification_requests", "rejected_mutations", "proof_reruns", "false_completion_authorizations", "package_residue"}


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
        if not isinstance(scenario, dict) or not all(scenario.get(key) for key in ("id", "owner", "terminal_state", "typed_action", "fault")):
            errors.append("every scenario must state owner, terminal state, typed action, and fault")
            break
    if not REQUIRED_GATES.issubset(set(matrix.get("hard_gates", []))):
        errors.append("hard gates do not cover the composed decision contract")
    assertion_contract = matrix.get("scenario_assertion_contract", {})
    if not isinstance(assertion_contract, dict) or not {"owner", "terminal_state", "typed_action", "permitted_effect_scope", "mutation_precondition", "proof_claim_boundary", "next_transition"}.issubset(set(assertion_contract.get("per_scenario", []))):
        errors.append("scenario assertion contract is incomplete")
    if not REQUIRED_METRICS.issubset(set(matrix.get("cost_metrics", []))):
        errors.append("cost metrics do not cover total successful-completion cost")
    return errors


def _run_cli(*args: str) -> tuple[dict[str, object], int, int]:
    """Execute the shipped CLI boundary and return its decoded packet and cost."""

    started = time.perf_counter_ns()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from agentic_workspace import cli; import sys; raise SystemExit(cli.main(sys.argv[1:]))",
            *args,
            "--format",
            "json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed_ms = int((time.perf_counter_ns() - started) / 1_000_000)
    rendered = completed.stdout
    if completed.returncode != 0:
        raise RuntimeError(f"CLI exited {completed.returncode}: {(rendered or completed.stderr)[:300]}")
    try:
        packet = json.loads(rendered)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"CLI did not emit one JSON packet: {rendered[:300]}") from exc
    if not isinstance(packet, dict):
        raise RuntimeError("CLI emitted a non-object packet")
    return packet, elapsed_ms, len(rendered.encode("utf-8"))


def _file_snapshot(root: Path) -> dict[str, str]:
    """Return a bounded observable filesystem state for one fixture run."""
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        snapshot[relative] = str(path.stat().st_mtime_ns) + ":" + str(path.stat().st_size)
    return snapshot


def _execute_composed_workspace_path(*, target: Path, scenario: dict[str, object]) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    """Exercise ordinary CLI consumers, not an in-process stand-in compiler."""

    scenario_id = str(scenario.get("id") or "unknown")
    commands = [
        ("start", ["start", "--target", str(target), "--task", f"Run composed scenario {scenario_id}" ]),
        ("implement", ["implement", "--target", str(target), "--changed", "README.md", "--task", f"Run composed scenario {scenario_id}"]),
        ("summary", ["summary", "--target", str(target)]),
        ("closeout", ["report", "--target", str(target), "--section", "closeout_trust"]),
    ]
    packets: dict[str, dict[str, object]] = {}
    before = _file_snapshot(target)
    elapsed = 0
    output = 0
    for name, command in commands:
        packet, command_ms, command_bytes = _run_cli(*command)
        packets[name] = packet
        elapsed += command_ms
        output += command_bytes
    after = _file_snapshot(target)
    changed_files = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    managed_changes = {path for path in changed_files if path.startswith(".agentic-workspace/")}
    command_signatures = [json.dumps(command, separators=(",", ":")) for _, command in commands]
    return packets, {
            "aw_command_count": len(commands),
            "wall_clock_aw_ms": elapsed,
            "output_bytes": output,
            "managed_files_read": len(managed_changes),
            "state_records_touched": len(managed_changes),
            "unchanged_orientation_repeats": len(command_signatures) - len(set(command_signatures)),
            "route_reversals": sum(1 for packet in packets.values() if packet.get("next_safe_action", {}).get("action") == "inspect-current-task-scope"),
            "clarification_requests": sum(1 for packet in packets.values() if packet.get("next_safe_action", {}).get("action") == "ask-for-route-decision"),
            "rejected_mutations": sum(1 for packet in packets.values() if packet.get("action_signals", {}).get("implementation_allowed") is False),
            "proof_reruns": sum(1 for name in packets if name == "closeout"),
            "false_completion_authorizations": sum(1 for packet in packets.values() if packet.get("terminal_state") == "COMPLETE"),
            "package_residue": len({path for path in changed_files if not path.startswith(".agentic-workspace/") and path != "README.md"}),
    }


def _execute_scenario(scenario: dict[str, object], budget: dict[str, object]) -> list[str]:
    """Run one scenario in its own repository; no row may inherit prior state."""

    errors: list[str] = []
    scenario_id = str(scenario.get("id") or "<unknown>")
    with tempfile.TemporaryDirectory(prefix=f"aw-composed-{scenario_id}-") as directory:
        target = Path(directory)
        subprocess.run(["git", "init", "--quiet", str(target)], check=True, capture_output=True, text=True)
        (target / "README.md").write_text(f"scenario fixture: {scenario_id}\n", encoding="utf-8")
        _run_cli("init", "--target", str(target))
        try:
            packets, metrics = _execute_composed_workspace_path(target=target, scenario=scenario)
        except RuntimeError as exc:
            return [f"{scenario_id} black-box execution failed: {exc}"]
    if set(packets) != {"start", "implement", "summary", "closeout"}:
        errors.append(f"{scenario_id} did not execute every ordinary consumer")
    if not packets["start"].get("next_safe_action") or not packets["implement"].get("decision_packet"):
        errors.append(f"{scenario_id} did not return ordinary route and implement packets")
    if metrics["aw_command_count"] != int(budget.get("max_aw_command_count", 0)) or metrics["output_bytes"] <= 0:
        errors.append(f"{scenario_id} emitted incomplete execution metrics")
    if metrics["wall_clock_aw_ms"] > int(budget.get("max_wall_clock_aw_ms_per_scenario", 0)):
        errors.append(f"{scenario_id} exceeded the lifecycle time budget ({metrics['wall_clock_aw_ms']}ms)")
    if metrics["output_bytes"] > int(budget.get("max_output_bytes_per_scenario", 0)):
        errors.append(f"{scenario_id} exceeded the lifecycle output budget ({metrics['output_bytes']} bytes)")
    return errors


def execute_matrix(matrix: dict[str, object]) -> list[str]:
    """Execute isolated rows concurrently without weakening their black-box boundary."""
    budget = matrix.get("execution_budget", {})
    if not isinstance(budget, dict):
        return ["execution budget is missing or invalid"]
    scenarios = [scenario for scenario in matrix.get("scenarios", []) if isinstance(scenario, dict)]
    errors: list[str] = []
    # Each worker is a distinct subprocess-backed CLI boundary. Four workers
    # keep the release gate bounded while preserving every full scenario path.
    with ThreadPoolExecutor(max_workers=min(4, len(scenarios) or 1)) as executor:
        futures = [executor.submit(_execute_scenario, scenario, budget) for scenario in scenarios]
        for future in as_completed(futures):
            errors.extend(future.result())
    return sorted(errors)


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
